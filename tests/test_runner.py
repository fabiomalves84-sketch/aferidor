"""The run: what gets asked, what gets kept, and what happens when it breaks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aferidor.models import Case, Criterion, Source
from aferidor.providers import FakeProvider, Provider, ProviderError
from aferidor.risk import FailureType
from aferidor.runner import RunConfig, build_prompt, run
from aferidor.storage import read_answers


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


class TestResume(unittest.TestCase):
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


class TestConfig(unittest.TestCase):
    def test_zero_attempts_is_refused(self):
        with self.assertRaises(ValueError):
            RunConfig(attempts=0)


if __name__ == "__main__":
    unittest.main()
