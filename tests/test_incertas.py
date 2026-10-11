"""A paid run that can finish: asking again what is uncertain, orphan reservations, restarting with the ledger
intact, the spend in view, and the provider's own finish reason. No network; made-up prices; temporary folders."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import unittest
from decimal import Decimal
from unittest import mock

from aferidor import cli
from aferidor.custos import AlreadyAsked, CeilingReached, Ledger, LedgerError
from aferidor.providers import (
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
    ProviderError,
    Reply,
)
from aferidor.proveniencia import FILE_NAME, read_records
from aferidor.runner import run
from aferidor.storage import read_answers
from tests.helpers import a_case
from tests.test_cli_pago import CASES, PAID, WithACli
from tests.test_custos import CATALOG, ROOT, WORST_EUR, WithAFolder, a_model_dict, reserve
from tests.test_pago import Scripted, WithAPaidFolder, ok
from tests.test_providers_http import replying

URLOPEN = "aferidor.providers.urllib.request.urlopen"


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def settle(ledger, reservation, state):
    return ledger.settle(reservation.intent_id, catalog=CATALOG, state=state)


class TestAskingAgainWhatIsUncertain(WithAFolder):
    def asked(self, state):
        first = reserve(self.ledger)
        if state != "sem_resultado":
            settle(self.ledger, first, state)
        return first

    def test_an_uncertain_sample_is_asked_again_as_a_new_reservation_linked_to_the_first(self):
        for state in ("sem_resultado", "resultado_desconhecido", "resposta"):
            with self.subTest(estado=state):
                ledger = Ledger(self.folder / f"{state}.jsonl")
                first = reserve(ledger)
                if state != "sem_resultado":
                    settle(ledger, first, state)
                second = reserve(ledger, retry_uncertain=True)
                self.assertNotEqual(second.intent_id, first.intent_id)
                self.assertEqual((second.attempt, second.previous_id), (2, first.intent_id))
                line = [json.loads(x) for x in (self.folder / f"{state}.jsonl").read_text().splitlines()][-1]
                self.assertEqual((line["t"], line["tentativa"], line["tentativa_anterior"], line["repeticao"]),
                                 ("intencao", 2, first.intent_id, True))

    def test_the_first_attempt_keeps_its_cost_and_the_total_counts_both(self):
        first = reserve(self.ledger)  # never settled: worst case
        reserve(self.ledger, retry_uncertain=True)
        self.assertEqual(self.ledger.summary("e1")["gasto_eur"], WORST_EUR * 2)
        lines = [json.loads(x) for x in self.path.read_text().splitlines()]
        self.assertEqual(lines[0]["id"], first.intent_id)  # the first line is where it was, untouched

    def test_a_timeout_that_is_repeated_costs_its_worst_case_plus_the_new_call(self):
        first = reserve(self.ledger)
        settle(self.ledger, first, "resultado_desconhecido")
        second = reserve(self.ledger, retry_uncertain=True)
        settle(self.ledger, second, "resposta")
        self.assertEqual(self.ledger.summary("e1")["gasto_eur"], WORST_EUR * 2)

    def test_the_ceiling_counts_the_first_attempt_and_the_repetition(self):
        reserve(self.ledger, ceiling=str(WORST_EUR * Decimal("1.5")))
        with self.assertRaises(CeilingReached):
            reserve(self.ledger, retry_uncertain=True, ceiling=str(WORST_EUR * Decimal("1.5")))
        reserve(self.ledger, retry_uncertain=True, ceiling=str(WORST_EUR * 2))
        self.assertEqual(len([x for x in self.path.read_text().splitlines() if '"t":"intencao"' in x]), 2)

    def test_without_the_flag_it_is_still_refused_as_before_and_says_how_to_ask(self):
        reserve(self.ledger)
        with self.assertRaisesRegex(AlreadyAsked, "pedido explícito.*--repetir-incertas"):
            reserve(self.ledger)

    def test_a_truncated_refused_or_empty_reply_is_not_repeated_even_with_the_flag(self):
        for state in ("truncada", "recusa_api", "vazia"):
            with self.subTest(estado=state):
                ledger = Ledger(self.folder / f"{state}.jsonl")
                settle(ledger, reserve(ledger), state)
                with self.assertRaises(AlreadyAsked) as caught:
                    reserve(ledger, retry_uncertain=True)
                self.assertNotIn("--repetir-incertas", str(caught.exception))

    def test_only_the_last_attempt_decides_and_a_free_error_before_it_does_not_matter(self):
        first = reserve(self.ledger)
        settle(self.ledger, first, "erro")
        second = reserve(self.ledger)
        settle(self.ledger, second, "resultado_desconhecido")
        self.assertEqual(reserve(self.ledger, retry_uncertain=True).attempt, 3)
        other = Ledger(self.folder / "outro.jsonl")
        settle(other, reserve(other), "resultado_desconhecido")
        settle(other, reserve(other, retry_uncertain=True), "truncada")
        with self.assertRaises(AlreadyAsked):
            reserve(other, retry_uncertain=True)

    def test_after_a_free_error_the_next_attempt_is_linked_too_but_is_not_a_repetition(self):
        settle(self.ledger, reserve(self.ledger), "erro")
        reserve(self.ledger)
        line = [json.loads(x) for x in self.path.read_text().splitlines()][-1]
        self.assertEqual((line["repeticao"], line["tentativa_anterior"] is not None), (False, True))


class TestAnOrphanReservation(WithAFolder):
    """A reservation with no settlement: the process died between `reserve` and `settle`."""

    def die_after_reserving(self):
        catalog_file = self.folder / "catalogo.json"
        from tests.test_catalogo import catalog as catalog_dict
        from tests.test_catalogo import model as model_dict
        catalog_file.write_text(json.dumps(catalog_dict(
            modelos={"pago": model_dict(parametros=a_model_dict()["parametros"])},
            usd_para_eur={"valor": 0.5, "fonte": "https://x.test", "lido_em": "2026-10-11"})), encoding="utf-8")
        script = (
            f"import os, sys\nsys.path.insert(0, {str(ROOT)!r})\n"
            "from datetime import date\nfrom pathlib import Path\n"
            "from aferidor.catalogo import load_catalog\nfrom aferidor.custos import Ledger\n"
            "Ledger(sys.argv[1]).reserve(catalog=load_catalog(Path(sys.argv[2])), ensaio='e1', run_id='r', model_key='pago',\n"
            "    case_id='C1', sample=1, prompt='x' * 300, tokens_max=1000, day=date(2026, 10, 11), ceiling_eur='1')\n"
            "os._exit(137)\n"
        )
        child = subprocess.run([sys.executable, "-I", "-c", script, str(self.path), str(catalog_file)], capture_output=True,
                               text=True, timeout=60, cwd=ROOT)
        self.assertEqual(child.returncode, 137, child.stderr)

    def test_a_reservation_that_was_never_settled_is_an_orphan_counts_at_the_worst_case_and_is_shown(self):
        self.die_after_reserving()
        summary = Ledger(self.path).summary("e1")
        self.assertEqual((summary["chamadas"], summary["sem_resultado"]), (1, 1))
        self.assertEqual((summary["gasto_eur"], summary["por_liquidar_eur"]), (WORST_EUR, WORST_EUR))

    def test_the_dead_process_left_no_lock_behind_and_the_orphan_blocks_its_sample_until_asked_for(self):
        self.die_after_reserving()
        ledger = Ledger(self.path)
        reserve(ledger, case="C2")  # the lock was released with the process: this does not hang
        with self.assertRaises(AlreadyAsked):
            reserve(ledger)
        again = reserve(ledger, retry_uncertain=True)
        self.assertEqual(again.attempt, 2)
        summary = ledger.summary("e1")
        self.assertEqual((summary["sem_resultado"], summary["chamadas"]), (3, 3))  # the orphan stays unsettled, and counted

    def test_an_orphan_that_is_settled_later_stops_being_one(self):
        first = reserve(self.ledger)
        self.assertEqual(self.ledger.summary("e1")["sem_resultado"], 1)
        settle(self.ledger, first, "resposta")
        self.assertEqual(self.ledger.summary("e1")["sem_resultado"], 0)

    def test_looking_at_a_ledger_that_does_not_exist_creates_nothing(self):
        summary = Ledger(self.folder / "nao-existe" / "custos.jsonl").summary("e1")
        self.assertEqual((summary["gasto_eur"], summary["chamadas"], summary["por_liquidar_eur"]), (0, 0, 0))
        self.assertFalse((self.folder / "nao-existe").exists())


class TestRestartingWithTheLedgerIntact(WithAFolder):
    def spend(self, n):
        for i in range(n):
            settle(self.ledger, reserve(self.ledger, case=f"C{i}"), "resposta")

    def test_the_old_lines_are_untouched_and_a_restart_line_is_added_with_a_reason_and_a_date(self):
        self.spend(2)
        before = self.path.read_bytes()
        self.ledger.restart("e1", "pago", "mudei o limite de tokens")
        after = self.path.read_bytes()
        self.assertTrue(after.startswith(before))
        (extra,) = after[len(before):].decode().splitlines()
        line = json.loads(extra)
        self.assertEqual((line["t"], line["ensaio"], line["modelo"], line["razao"]), ("recomeco", "e1", "pago", "mudei o limite de tokens"))
        self.assertEqual(Decimal(line["gasto_anterior_eur"]), WORST_EUR * 2)
        self.assertRegex(line["quando"], r"^\d{4}-\d{2}-\d{2}T")

    def test_what_was_spent_stays_in_the_total_and_is_shown_apart_from_what_comes_after(self):
        self.spend(2)
        self.ledger.restart("e1", "pago", "razão")
        settle(self.ledger, reserve(self.ledger, case="C0"), "resposta")
        summary = self.ledger.summary("e1")
        self.assertEqual((summary["anterior_eur"], summary["novo_eur"], summary["gasto_eur"]), (WORST_EUR * 2, WORST_EUR, WORST_EUR * 3))
        self.assertEqual(summary["chamadas"], 3)

    def test_after_a_restart_the_samples_are_free_to_ask_again(self):
        self.spend(1)
        with self.assertRaises(AlreadyAsked):
            reserve(self.ledger, case="C0")
        self.ledger.restart("e1", "pago", "razão")
        again = reserve(self.ledger, case="C0")
        self.assertEqual((again.attempt, again.previous_id), (1, None))

    def test_the_ceiling_counts_the_total_before_and_after_a_restart(self):
        self.spend(2)
        self.ledger.restart("e1", "pago", "razão")
        with self.assertRaises(CeilingReached) as caught:
            reserve(self.ledger, case="N", ceiling=str(WORST_EUR * 2))
        self.assertEqual(caught.exception.summary["gasto_eur"], WORST_EUR * 2)
        reserve(self.ledger, case="N", ceiling=str(WORST_EUR * 3))

    def test_an_orphan_from_before_a_restart_still_counts_as_spent_and_as_unsettled(self):
        reserve(self.ledger)
        self.ledger.restart("e1", "pago", "razão")
        summary = self.ledger.summary("e1")
        self.assertEqual((summary["anterior_eur"], summary["sem_resultado"]), (WORST_EUR, 1))

    def test_it_only_archives_the_model_and_the_trial_it_names(self):
        reserve(self.ledger, key="pago")
        reserve(self.ledger, key="pago2")
        reserve(self.ledger, key="pago", ensaio="e2")
        self.ledger.restart("e1", "pago", "razão")
        with self.assertRaises(AlreadyAsked):
            reserve(self.ledger, key="pago2")
        with self.assertRaises(AlreadyAsked):
            reserve(self.ledger, key="pago", ensaio="e2")
        reserve(self.ledger, key="pago")

    def test_a_restart_needs_a_written_reason(self):
        for reason in ("", "   "):
            with self.assertRaisesRegex(LedgerError, "razão escrita"):
                self.ledger.restart("e1", "pago", reason)
        self.assertFalse(self.path.exists() and self.path.read_text())

    def test_a_malformed_restart_line_is_refused_like_any_other(self):
        reserve(self.ledger)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write('{"t":"recomeco","ensaio":"e1"}\n')
        with self.assertRaisesRegex(LedgerError, "linha 2"):
            self.ledger.summary("e1")


class TestTheRunnerAskingAgain(WithAPaidFolder):
    def with_flag(self, ceiling="1", flag=True):
        paid = self.paid(ceiling)
        paid.retry_uncertain = flag
        return paid

    def second_run(self, provider, flag=True, cases=1):
        found = [a_case(f"C{i}") for i in range(1, cases + 1)]
        return run(found, provider, path=self.answers, run_id="r2", config=self.config(), paid=self.with_flag(flag=flag))

    def test_a_timed_out_sample_is_asked_again_in_a_later_run_and_both_costs_are_kept(self):
        self.go(Scripted([ProviderError("excedeu 60s", retryable=True)]), cases=1)
        again = Scripted([])
        result = self.second_run(again)
        self.assertEqual((again.calls, len(result.answers), result.complete), (1, 1, True))
        intents = [x for x in self.lines() if x["t"] == "intencao"]
        self.assertEqual((len(intents), intents[1]["tentativa_anterior"], intents[1]["repeticao"]), (2, intents[0]["id"], True))
        results = [x for x in self.lines() if x["t"] == "resultado"]
        self.assertEqual([x["estado"] for x in results], ["resultado_desconhecido", "resposta"])
        self.assertEqual(self.ledger.summary("e1")["gasto_eur"], sum(Decimal(x["custo_eur"]) for x in results))
        self.assertGreater(Decimal(results[0]["custo_eur"]), 0)  # the timed out call did not vanish from the account
        self.assertEqual([r.state for r in read_records(self.folder / FILE_NAME)], ["resultado_desconhecido", "resposta"])

    def test_without_the_flag_the_second_run_does_what_it_always_did(self):
        self.go(Scripted([ProviderError("excedeu 60s", retryable=True)]), cases=1)
        again = Scripted([])
        result = self.second_run(again, flag=False)
        self.assertEqual((again.calls, result.answers), (0, []))
        self.assertIn("já foi pedida", result.errors["C1"])

    def test_a_call_that_times_out_in_this_run_is_not_asked_again_in_this_run_even_with_the_flag(self):
        provider = Scripted([ProviderError("excedeu 60s", retryable=True), ok()])
        result = run([a_case("C1"), a_case("C2")], provider, path=self.answers, run_id="r1", config=self.config(),
                     paid=self.with_flag())
        self.assertEqual((provider.calls, [a.case_id for a in result.answers]), (2, ["C2"]))

    def test_an_answer_lost_between_the_call_and_the_file_is_asked_again_on_request(self):
        provider = Scripted([])
        with mock.patch("aferidor.runner.append_answer", side_effect=OSError("disco cheio")):
            with self.assertRaises(OSError):
                self.go(provider, cases=1)
        self.assertEqual([x["estado"] for x in self.lines() if x["t"] == "resultado"], ["resposta"])
        self.assertFalse(self.answers.exists() and read_answers(self.answers))
        blocked = self.second_run(Scripted([]), flag=False)
        self.assertIn("já foi pedida", blocked.errors["C1"])
        again = self.second_run(Scripted([]))
        self.assertEqual(len(again.answers), 1)
        self.assertEqual(len(read_answers(self.answers)), 1)

    def test_a_reservation_orphaned_by_a_dead_run_is_asked_again_on_request(self):
        self.ledger.reserve(catalog=self.catalog, ensaio="e1", run_id="r0", model_key="pago", case_id="C1", sample=1,
                            prompt="x" * 300, tokens_max=1000, day=self.paid().day, ceiling_eur=1)
        again = Scripted([])
        result = self.second_run(again)
        self.assertEqual((again.calls, len(result.answers)), (1, 1))
        self.assertEqual(self.ledger.summary("e1")["sem_resultado"], 1)  # the orphan is still there, still counted

    def test_the_repetition_stops_at_the_ceiling_like_any_call(self):
        self.go(Scripted([ProviderError("excedeu 60s", retryable=True)]), cases=1)
        again = Scripted([])
        result = run([a_case("C1")], again, path=self.answers, run_id="r2", config=self.config(), paid=self.with_flag("0.006"))
        self.assertEqual(again.calls, 0)
        self.assertIn("teto", result.stopped)


class TestTheProvidersOwnFinishReason(WithAPaidFolder):
    def test_openai_and_the_compatible_servers_keep_the_word_they_were_given(self):
        for raw, normalized in (("stop", "stop"), ("length", "length"), ("content_filter", "filtered"), ("tool_calls", "unknown")):
            payload = {"choices": [{"message": {"content": "x"}, "finish_reason": raw}]}
            with self.subTest(razao=raw), mock.patch(URLOPEN, replying(payload)):
                reply = OpenAIProvider(model="m", api_key="k").ask("p")
                self.assertEqual((reply.finish_reason, reply.finish_reason_original), (normalized, raw))

    def test_anthropic_keeps_its_stop_reason(self):
        for raw, normalized in (("end_turn", "stop"), ("max_tokens", "length"), ("refusal", "filtered"), ("pause_turn", "unknown")):
            payload = {"content": [{"type": "text", "text": "x"}], "stop_reason": raw}
            with self.subTest(razao=raw), mock.patch(URLOPEN, replying(payload)):
                reply = AnthropicProvider(model="m", api_key="k").ask("p")
                self.assertEqual((reply.finish_reason, reply.finish_reason_original), (normalized, raw))

    def test_gemini_keeps_it_when_it_takes_the_thoughts_out(self):
        payload = {"choices": [{"message": {"content": "<thought>a</thought>b"}, "finish_reason": "stop"}]}
        with mock.patch(URLOPEN, replying(payload)):
            reply = GeminiProvider(model="m", api_key="k", min_interval_s=0).ask("p")
        self.assertEqual((reply.text, reply.finish_reason_original), ("b", "stop"))

    def test_a_provider_that_says_nothing_or_something_that_is_not_text_has_none(self):
        for payload in ({"choices": [{"message": {"content": "x"}}]}, {"choices": [{"message": {"content": "x"}, "finish_reason": 7}]},
                        {"choices": [{"message": {"content": "x"}, "finish_reason": ""}]}):
            with mock.patch(URLOPEN, replying(payload)):
                self.assertIsNone(OpenAIProvider(model="m", api_key="k").ask("p").finish_reason_original)
        self.assertIsNone(Reply("x").finish_reason_original)

    def test_the_normalized_reason_and_everything_else_in_the_reply_is_what_it_was(self):
        payload = {"model": "s", "choices": [{"message": {"content": "x"}, "finish_reason": "length"}], "usage": {"prompt_tokens": 3}}
        with mock.patch(URLOPEN, replying(payload)):
            reply = OpenAIProvider(model="m", api_key="k").ask("p")
        self.assertEqual((reply.text, reply.finish_reason, reply.served_model, reply.usage.input_tokens), ("x", "length", "s", 3))

    def test_the_provenance_line_keeps_both_the_original_and_the_normalized_word(self):
        self.go(Scripted([Reply("Amoxicilina 1 g", "stop", "", None, "end_turn")]), cases=1)
        (line,) = read_records(self.folder / FILE_NAME)
        self.assertEqual((line.finish_reason, line.finish_reason_original), ("stop", "end_turn"))

    def test_a_call_that_got_no_reply_has_no_original_word(self):
        self.go(Scripted([ProviderError("503", retryable=False, maybe_billed=False)]), cases=1)
        (line,) = read_records(self.folder / FILE_NAME)
        self.assertIsNone(line.finish_reason_original)


class TestTheCommandLine(WithACli):
    def paid_args(self, *extra, ceiling="100"):
        limit = [] if "--piloto" in extra else ["--limite", "2"]
        return ["executar", *PAID, "--casos", str(CASES), "--saida", str(self.saida), *limit, "--tokens-max", "4096",
                "--teto-eur", ceiling, *extra]

    def ledger_lines(self):
        path = self.saida.with_name("custos.jsonl")
        return path.read_bytes()

    def test_the_restart_shows_what_was_spent_asks_in_writing_and_keeps_the_ledger(self):
        self.main(*self.paid_args())
        before = self.ledger_lines()
        with mock.patch("builtins.input", side_effect=["RECOMECAR", "mudei o limite de tokens"]):
            code, out, err = self.main(*self.paid_args("--recomecar"))
        self.assertEqual(code, 0, err)
        self.assertIn("já se gastaram 0.1473 EUR em 2 chamadas", out)
        self.assertIn("O livro não se apaga", out)
        after = self.ledger_lines()
        self.assertTrue(after.startswith(before))
        restart = [json.loads(x) for x in after.decode().splitlines() if '"recomeco"' in x]
        self.assertEqual([(r["modelo"], r["razao"]) for r in restart], [("claude-opus-5-5", "mudei o limite de tokens")])
        self.assertIn("antes de um recomeço", out)
        self.assertIn("0.1473 EUR são de antes de um recomeço e 0.1473 EUR de depois", out)
        self.assertIn("gasto do ensaio: 0.2946 EUR em 4 chamadas", out)
        self.assertEqual(len(read_answers(self.saida)), 2)
        self.assertEqual(self.provider.calls, 4)

    def test_without_the_written_confirmation_nothing_is_thrown_away(self):
        self.main(*self.paid_args())
        before = self.ledger_lines()
        answers = self.saida.read_bytes()
        for typed, why in ((["nao"], "não confirmado"), (["RECOMECAR", "   "], "sem razão"), (EOFError(), "sem onde ler")):
            with self.subTest(caso=why), mock.patch("builtins.input", side_effect=typed):
                code, _, err = self.main(*self.paid_args("--recomecar"))
            self.assertEqual(code, 2)
            self.assertIn("nada foi apagado", err)
            self.assertEqual((self.saida.read_bytes(), self.ledger_lines()), (answers, before))
        self.assertEqual(self.provider.calls, 2)

    def test_a_restart_with_nothing_to_lose_does_not_ask(self):
        with mock.patch("builtins.input", side_effect=AssertionError("pediu confirmação sem haver nada")):
            code, _, err = self.main(*self.paid_args("--recomecar"))
        self.assertEqual(code, 0, err)

    def test_a_model_that_is_not_paid_restarts_as_before_without_asking(self):
        saida = self.folder / "livre" / "respostas.jsonl"
        args = ["executar", "--fornecedor", "falso", "--casos", str(CASES), "--saida", str(saida), "--limite", "2"]
        self.main(*args)
        with mock.patch("builtins.input", side_effect=AssertionError("pediu confirmação")):
            code, out, _ = self.main(*args, "--recomecar")
        self.assertEqual(code, 0)
        self.assertIn("descartadas 2 respostas anteriores", out)
        self.assertEqual(sorted(p.name for p in saida.parent.iterdir()), ["respostas.jsonl"])

    def test_the_flag_asks_again_a_timed_out_sample_from_the_command_line(self):
        self.provider.script = [ProviderError("excedeu 60s", retryable=True)]
        code, _, err = self.main(*self.paid_args())
        self.assertEqual(code, 1)
        self.assertIn("pode ter sido cobrada", err)
        code, _, err = self.main(*self.paid_args())
        self.assertEqual(code, 1)
        self.assertIn("já foi pedida", err)
        code, out, err = self.main(*self.paid_args("--repetir-incertas"))
        self.assertEqual(code, 0, err)
        self.assertEqual(len(read_answers(self.saida)), 2)
        intents = [json.loads(x) for x in self.ledger_lines().decode().splitlines() if '"t":"intencao"' in x]
        self.assertEqual(len(intents), 3)
        self.assertIsNotNone(intents[2]["tentativa_anterior"])

    def test_orphans_are_shown_as_to_settle_with_how_they_are_repeated(self):
        from datetime import date
        from aferidor.catalogo import load_catalog
        from aferidor.runner import build_prompt
        from aferidor.storage import read_cases
        first = read_cases(CASES)[0]
        Ledger(self.saida.with_name("custos.jsonl")).reserve(
            catalog=load_catalog(), ensaio="ensaio", run_id="r0", model_key="claude-opus-5-5", case_id=first.case_id, sample=1,
            prompt=build_prompt(first), tokens_max=4096, day=date.today(), ceiling_eur=100)
        code, out, _ = self.main(*self.paid_args("--repetir-incertas"))
        self.assertEqual(code, 0)
        self.assertIn("por liquidar: 1 chamadas reservadas e nunca liquidadas", out)
        self.assertIn("--repetir-incertas", out)

    def test_the_flag_on_a_model_that_is_not_paid_says_it_does_nothing(self):
        saida = self.folder / "livre" / "respostas.jsonl"
        code, _, err = self.main("executar", "--fornecedor", "falso", "--casos", str(CASES), "--saida", str(saida), "--limite", "1",
                                 "--repetir-incertas")
        self.assertEqual(code, 0)
        self.assertIn("só tem efeito num modelo pago", err)

    def test_the_summary_shows_the_trial_the_pilot_and_their_sum_and_each_ceiling_apart(self):
        code, out, err = self.main(*self.paid_args("--piloto"))
        self.assertEqual(code, 0, err)
        pilot_cost = [x for x in out.splitlines() if x.startswith("gasto do ensaio")][0]
        self.assertIn("gasto do ensaio: 0.0000 EUR em 0 chamadas; do piloto: ", pilot_cost)
        self.assertIn("em 6 chamadas; soma: ", pilot_cost)
        self.assertIn("o teto de 100 EUR conta cada livro por si: o gasto efetivo máximo dos dois é o dobro, 200 EUR", out)
        self.assertFalse(self.saida.with_name("custos.jsonl").exists())  # looking at the trial's ledger did not create it
        code, out, _ = self.main(*self.paid_args())
        line = [x for x in out.splitlines() if x.startswith("gasto do ensaio")][0]
        self.assertIn("gasto do ensaio: 0.1473 EUR em 2 chamadas; do piloto: ", line)
        self.assertIn("em 6 chamadas; soma: ", line)

    def test_the_two_ledgers_stay_separate(self):
        self.main(*self.paid_args("--piloto"))
        self.main(*self.paid_args())
        self.assertEqual(len([x for x in self.ledger_lines().decode().splitlines() if '"t":"intencao"' in x]), 2)
        pilot = (self.saida.parent / "piloto" / "custos.jsonl").read_text().splitlines()
        self.assertEqual(len([x for x in pilot if '"t":"intencao"' in x]), 6)


class TestNothingChangesWithoutTheFlags(unittest.TestCase):
    def test_the_defaults_are_off(self):
        found = cli.parse_args(["executar"])
        self.assertEqual((found.repetir_incertas, found.recomecar, found.a_seco, found.piloto), (False, False, False, False))


if __name__ == "__main__":
    unittest.main()
