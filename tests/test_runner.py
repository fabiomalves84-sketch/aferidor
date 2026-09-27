"""The run: what gets asked, what gets kept, and what happens when it breaks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aferidor.models import Case, Criterion, Source
from aferidor.providers import FakeProvider, Provider, ProviderError, Reply
from aferidor.risk import FailureType
from aferidor import build_id
from aferidor.runner import ConditionsMismatch, RunConfig, build_prompt, prompt_digest, run
from aferidor.storage import read_answers, write_answers


def a_case(case_id: str = "ATB-001") -> Case:
    return Case(
        case_id=case_id,
        category="antibioterapia",
        question="Que dose de amoxicilina na pneumonia adquirida na comunidade?",
        reference="Amoxicilina 1000 mg 8/8h durante 5 a 7 dias",
        source=Source(name="Guia ATB", reference="pagina 17"),
        criteria=(
            Criterion(kind="contem", terms=("1000 mg",), failure=FailureType.DOSE_INCORRETA),
        ),
    )


class TestPrompt(unittest.TestCase):
    def test_the_prompt_carries_the_question(self):
        self.assertIn(a_case().question, build_prompt(a_case()))

    def test_the_prompt_never_carries_the_reference_answer(self):
        case = a_case()
        prompt = build_prompt(case)
        self.assertNotIn(case.reference, prompt)
        self.assertNotIn(case.source.name, prompt)
        for criterion in case.criteria:
            for term in criterion.terms:
                self.assertNotIn(term, prompt)


class TestRun(unittest.TestCase):
    def test_every_case_produces_an_answer_tagged_with_the_run(self):
        cases = [a_case("A"), a_case("B")]
        result = run(cases, FakeProvider(default="resposta"), run_id="corrida")
        self.assertEqual([an.case_id for an in result.answers], ["A", "B"])
        self.assertTrue(all(an.run_id == "corrida" for an in result.answers))
        self.assertTrue(all(an.model == "falso" for an in result.answers))
        self.assertTrue(result.complete)

    def test_a_run_id_is_invented_when_none_is_given(self):
        result = run([a_case()], FakeProvider())
        self.assertTrue(result.run_id)

    def test_latency_is_measured(self):
        result = run([a_case()], FakeProvider())
        self.assertGreaterEqual(result.answers[0].latency_ms, 0)

    def test_a_retryable_failure_is_retried(self):
        provider = FakeProvider(failures=2, default="ao fim de duas")
        result = run(
            [a_case()],
            provider,
            config=RunConfig(attempts=3, backoff_s=0, sleep=lambda _: None),
        )
        self.assertEqual(result.answers[0].text, "ao fim de duas")
        self.assertEqual(result.errors, {})

    def test_a_case_that_never_answers_is_recorded_not_dropped(self):
        provider = FakeProvider(failures=99)
        result = run(
            [a_case("A"), a_case("B")],
            provider,
            config=RunConfig(attempts=2, backoff_s=0, sleep=lambda _: None),
        )
        self.assertEqual(result.answers, [])
        self.assertEqual(sorted(result.errors), ["A", "B"])
        self.assertFalse(result.complete)

    def test_errors_from_different_samples_of_one_case_are_both_kept(self):
        provider = FakeProvider(failures=99)
        result = run(
            [a_case("A")],
            provider,
            config=RunConfig(attempts=1),
            repetitions=2,
        )
        self.assertEqual(list(result.errors), ["A"])
        self.assertIn("amostra 1: falha simulada", result.errors["A"])
        self.assertIn("amostra 2: falha simulada", result.errors["A"])
        self.assertIn("; ", result.errors["A"])

    def test_a_reply_cut_off_by_the_token_limit_is_not_an_answer(self):
        """`max_tokens` too low is an execution error, not a wrong answer.

        Reproduces the failure found running qwen3:8b at `max_tokens` 1024: the
        model spent the whole budget reasoning and the case is left unanswered,
        not graded against an answer it never gave.
        """
        provider = FakeProvider(default="a meio da frase", finish_reason="length")
        result = run([a_case("A")], provider, config=RunConfig(attempts=1))
        self.assertEqual(result.answers, [])
        self.assertEqual(list(result.errors), ["A"])
        self.assertIn("truncada", result.errors["A"])

    def test_an_empty_reply_is_not_an_answer_either(self):
        provider = FakeProvider(default="")
        result = run([a_case("A")], provider, config=RunConfig(attempts=1))
        self.assertEqual(result.answers, [])
        self.assertEqual(list(result.errors), ["A"])

    def test_a_cut_off_reply_is_not_retried(self):
        """Retrying would just hit the same `max_tokens` again.

        A caller who wants a real second attempt asks again with a higher
        `--tokens-max`; the runner never invents that retry on its own, or two
        different measurements end up mixed in the same run.
        """
        provider = FakeProvider(default="a meio", finish_reason="length")
        run([a_case("A")], provider, config=RunConfig(attempts=5, backoff_s=0, sleep=lambda _: None))
        self.assertEqual(len(provider.prompts), 1)

    def test_a_successful_answer_records_its_finish_reason(self):
        result = run([a_case()], FakeProvider(default="1000 mg"))
        self.assertEqual(result.answers[0].finish_reason, "stop")

    def test_a_permanent_failure_is_not_retried(self):
        class Broken(Provider):
            name = "partido"

            def __init__(self):
                self.calls = 0

            def ask(self, prompt: str) -> str:
                self.calls += 1
                raise ProviderError("chave invalida")

        provider = Broken()
        run([a_case()], provider, config=RunConfig(attempts=5, backoff_s=0, sleep=lambda _: None))
        self.assertEqual(provider.calls, 1)


class _CrashesAfter(Provider):
    """Answers normally, then dies without ever raising `ProviderError`.

    Stands in for the process being killed mid-run (out of memory, machine
    reboot): nothing here catches this, so it is the same as `run` itself
    stopping abruptly, which is exactly what `--recomecar` needs to survive.
    """

    name = "crasha"

    def __init__(self, survives: int) -> None:
        self.survives = survives
        self.calls = 0

    def ask(self, prompt: str) -> Reply:
        self.calls += 1
        if self.calls > self.survives:
            raise RuntimeError("morreu a meio")
        return Reply(text="Amoxicilina 1000 mg")


class TestResume(unittest.TestCase):
    def test_an_interrupted_run_leaves_on_disk_what_it_already_had(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            provider = _CrashesAfter(survives=2)
            with self.assertRaises(RuntimeError):
                run([a_case("A"), a_case("B"), a_case("C")], provider, path=path)
            self.assertEqual([an.case_id for an in read_answers(path)], ["A", "B"])

    def test_answers_are_written_as_they_arrive(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sub" / "respostas.jsonl"
            run([a_case("A"), a_case("B")], FakeProvider(default="x"), path=path)
            self.assertEqual([an.case_id for an in read_answers(path)], ["A", "B"])

    def test_a_second_run_skips_what_the_first_already_answered(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            cases = [a_case("A"), a_case("B")]
            run(cases[:1], FakeProvider(default="x"), path=path)

            provider = FakeProvider(default="y")
            result = run(cases, provider, path=path)

            self.assertEqual(result.skipped, ["A"])
            self.assertEqual([an.case_id for an in result.answers], ["B"])
            self.assertEqual(len(provider.prompts), 1)
            self.assertEqual(len(read_answers(path)), 2)

    def test_answers_from_another_model_do_not_count_as_done(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            run([a_case("A")], FakeProvider(name="modelo-um"), path=path)
            result = run([a_case("A")], FakeProvider(name="modelo-dois"), path=path)
            self.assertEqual(result.skipped, [])
            self.assertEqual(len(read_answers(path)), 2)

    def test_resuming_partway_through_the_repetitions_of_one_case(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            provider = FakeProvider(default="x")
            run([a_case("A")], provider, path=path, repetitions=2)
            self.assertEqual(len(provider.prompts), 2)

            provider2 = FakeProvider(default="y")
            result = run([a_case("A")], provider2, path=path, repetitions=5)

            self.assertEqual([an.sample for an in result.answers], [3, 4, 5])
            self.assertEqual(len(provider2.prompts), 3)
            saved = read_answers(path)
            self.assertEqual(sorted(a.sample for a in saved), [1, 2, 3, 4, 5])


class TestRepetitions(unittest.TestCase):
    def test_each_case_is_asked_once_per_repetition(self):
        result = run([a_case("A"), a_case("B")], FakeProvider(default="x"), repetitions=3)
        self.assertEqual(
            [(an.case_id, an.sample) for an in result.answers],
            [("A", 1), ("A", 2), ("A", 3), ("B", 1), ("B", 2), ("B", 3)],
        )

    def test_an_old_answer_without_a_sample_field_is_read_as_sample_one(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            path.write_text(
                '{"caso": "A", "modelo": "falso", "texto": "x", '
                '"perguntada_em": "2026-09-14T10:00:00"}\n',
                encoding="utf-8",
            )
            provider = FakeProvider(default="y")
            result = run([a_case("A")], provider, path=path, repetitions=2)
            self.assertEqual([an.sample for an in result.answers], [2])

    def test_the_temperature_asked_for_is_recorded_on_the_answer(self):
        result = run([a_case()], FakeProvider(temperature=1.0))
        self.assertEqual(result.answers[0].temperature, 1.0)


class TestConditions(unittest.TestCase):
    """What an answer says about how it was obtained."""

    def test_the_hash_of_the_exact_prompt_sent_is_recorded(self):
        provider = FakeProvider()
        result = run([a_case()], provider)
        self.assertEqual(result.answers[0].prompt_sha256, prompt_digest(provider.prompts[0]))
        self.assertEqual(len(result.answers[0].prompt_sha256), 64)

    def test_a_different_question_gives_a_different_prompt_hash(self):
        other = Case(
            case_id="B", category="x", question="Outra pergunta?", reference="r",
            source=Source(name="s", reference="p"), criteria=a_case().criteria,
        )
        result = run([a_case(), other], FakeProvider())
        self.assertNotEqual(result.answers[0].prompt_sha256, result.answers[1].prompt_sha256)

    def test_the_token_limit_given_to_the_provider_is_recorded(self):
        provider = FakeProvider()
        provider.max_tokens = 8192
        self.assertEqual(run([a_case()], provider).answers[0].max_tokens, 8192)

    def test_a_provider_without_a_token_limit_records_none(self):
        self.assertIsNone(run([a_case()], FakeProvider()).answers[0].max_tokens)

    def test_the_version_and_code_hash_are_recorded(self):
        build = run([a_case()], FakeProvider()).answers[0].build
        self.assertEqual(build, build_id())
        self.assertRegex(build, r"^\d+\.\d+\.\d+\+[0-9a-f]{12}$")


class TestResumeUnderSameConditions(unittest.TestCase):
    """Resuming is only safe while it is still the same measurement."""

    def first_run(self, folder: str, **provider_kwargs) -> Path:
        path = Path(folder) / "respostas.jsonl"
        provider = FakeProvider(**provider_kwargs)
        provider.max_tokens = 4096
        run([a_case("A")], provider, path=path)
        return path

    def test_the_same_conditions_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.first_run(folder, temperature=1.0)
            provider = FakeProvider(temperature=1.0)
            provider.max_tokens = 4096
            result = run([a_case("A"), a_case("B")], provider, path=path)
        self.assertEqual([a.case_id for a in result.answers], ["B"])

    def test_another_temperature_is_refused_before_anything_is_asked(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.first_run(folder, temperature=1.0)
            provider = FakeProvider(temperature=0.0)
            provider.max_tokens = 4096
            with self.assertRaises(ConditionsMismatch) as raised:
                run([a_case("A"), a_case("B")], provider, path=path)
        self.assertIn("temperatura 1", str(raised.exception))
        self.assertEqual(provider.prompts, [])

    def test_another_token_limit_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.first_run(folder)
            provider = FakeProvider()
            provider.max_tokens = 8192
            with self.assertRaises(ConditionsMismatch) as raised:
                run([a_case("A")], provider, path=path)
        self.assertIn("tokens_max 4096, agora 8192", str(raised.exception))

    def test_a_changed_prompt_for_the_same_case_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.first_run(folder)
            reworded = Case(
                case_id="A", category="x", question="Pergunta reescrita?", reference="r",
                source=Source(name="s", reference="p"), criteria=a_case().criteria,
            )
            provider = FakeProvider()
            provider.max_tokens = 4096
            with self.assertRaises(ConditionsMismatch) as raised:
                run([reworded], provider, path=path)
        self.assertIn("texto enviado ao modelo mudou", str(raised.exception))

    def test_another_model_in_the_same_file_is_not_compared(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.first_run(folder, temperature=1.0)
            other = FakeProvider(name="outro", temperature=0.0)
            result = run([a_case("A")], other, path=path)
        self.assertEqual(len(result.answers), 1)

    def test_an_old_answer_without_conditions_is_not_compared_on_them(self):
        from datetime import datetime

        from aferidor.models import Answer

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            write_answers(
                [Answer("A", "falso", "texto", datetime(2026, 9, 16), temperature=0.0)], path
            )
            provider = FakeProvider()
            provider.max_tokens = 8192
            result = run([a_case("A"), a_case("B")], provider, path=path)
        self.assertEqual([a.case_id for a in result.answers], ["B"])


class TestConfig(unittest.TestCase):
    def test_zero_attempts_is_refused(self):
        with self.assertRaises(ValueError):
            RunConfig(attempts=0)


if __name__ == "__main__":
    unittest.main()
