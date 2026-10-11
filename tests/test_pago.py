"""The paid-call guard wired into the runner: ledger, ceiling, provenance, served-model check, backoff. A scripted
provider and temporary folders; no network."""

from __future__ import annotations

import json
import socket
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from aferidor.catalogo import parse_catalog
from aferidor.custos import Ledger
from aferidor.providers import Provider, ProviderError, Reply, Usage
from aferidor.proveniencia import FILE_NAME, catalog_sha256, read_records
from aferidor.runner import RunConfig, run
from aferidor.storage import read_answers
from tests.helpers import a_case
from tests.test_catalogo import catalog as catalog_dict
from tests.test_catalogo import model as model_dict
from tests.test_custos import DAY, a_model_dict

REQUESTED = "modelo-falso"  # the id of the catalogue model (made up) in `tests.test_catalogo.model`
GOOD = "Amoxicilina 1000 mg de 8 em 8 horas"


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


class Scripted(Provider):
    """Answers from a list, one item per call: a Reply is returned, an exception is raised, a callable is called."""

    def __init__(self, script, name="openai:modelo-falso", temperature=1.0, max_tokens=1000):
        self.name, self.temperature, self.max_tokens = name, temperature, max_tokens
        self.script = list(script)
        self.calls = 0

    def ask(self, prompt: str) -> Reply:
        self.calls += 1
        step = self.script.pop(0) if self.script else Reply(GOOD)
        if isinstance(step, BaseException):
            raise step
        return step() if callable(step) else step


def ok(served="", usage=None, text=GOOD, finish="stop") -> Reply:
    return Reply(text, finish, served, usage)


class WithAPaidFolder(unittest.TestCase):
    ACCEPTED: list[str] = []

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.folder = Path(self._dir.name)
        self.answers = self.folder / "respostas.jsonl"
        self.catalog_file = self.folder / "catalogo.json"
        self.catalog_file.write_text(json.dumps(catalog_dict(
            modelos={"pago": model_dict(parametros=a_model_dict()["parametros"], ids_servidos_aceites=self.ACCEPTED)},
            usd_para_eur={"valor": 0.5, "fonte": "https://exemplo.test/bce", "lido_em": "2026-10-11"},
        )), encoding="utf-8")
        self.catalog = parse_catalog(self.catalog_file.read_text(encoding="utf-8"))
        self.ledger = Ledger(self.folder / "custos.jsonl")
        self.sleeps: list[float] = []

    def paid(self, ceiling="1", key="pago", ledger=None):
        from aferidor.pago import PaidCalls
        return PaidCalls(
            catalog=self.catalog, model_key=key, ledger=ledger or self.ledger, provenance_file=self.folder / FILE_NAME,
            ensaio="e1", ceiling_eur=Decimal(ceiling), catalog_path=self.catalog_file, day=DAY,
        )

    def config(self, **over):
        return RunConfig(attempts=over.pop("attempts", 3), backoff_s=2.0, sleep=self.sleeps.append, **over)

    def go(self, provider, cases=2, repetitions=1, ceiling="1", **config):
        found = [a_case(f"C{i}") for i in range(1, cases + 1)]
        return run(found, provider, path=self.answers, run_id="r1", config=self.config(**config),
                   repetitions=repetitions, paid=self.paid(ceiling))

    def lines(self, name="custos.jsonl") -> list[dict]:
        path = self.folder / name
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


class TestEveryCallGoesThroughTheLedger(WithAPaidFolder):
    def test_each_call_is_reserved_before_and_settled_after_and_the_answers_are_kept(self):
        provider = Scripted([])
        result = self.go(provider, cases=2, repetitions=2)
        self.assertEqual((provider.calls, len(result.answers), result.complete, result.stopped), (4, 4, True, None))
        kinds = [x["t"] for x in self.lines()]
        self.assertEqual((kinds.count("intencao"), kinds.count("resultado")), (4, 4))
        self.assertEqual(kinds[:2], ["intencao", "resultado"])  # one call is finished before the next is reserved
        self.assertEqual(len(read_answers(self.answers)), 4)

    def test_a_model_that_hides_its_reasoning_is_counted_at_the_worst_case_not_by_the_usage(self):
        self.go(Scripted([ok(usage=Usage(input_tokens=50, output_tokens=10))]), cases=1)
        result_line = [x for x in self.lines() if x["t"] == "resultado"][0]
        self.assertEqual((result_line["modo"], result_line["usage"]), ("pior_caso", {"entrada": 50, "saida": 10, "raciocinio": None}))
        self.assertGreater(Decimal(result_line["custo_usd"]), Decimal("0.01"))

    def test_the_provenance_line_has_what_was_asked_served_and_counted(self):
        self.go(Scripted([ok(served=REQUESTED, usage=Usage(120, 900, None))]), cases=1)
        (line,) = read_records(self.folder / FILE_NAME)
        self.assertEqual((line.requested_model, line.served_model, line.served_check, line.state), (REQUESTED, REQUESTED, "igual", "resposta"))
        self.assertEqual((line.input_tokens, line.output_tokens, line.reasoning_tokens), (120, 900, None))
        self.assertEqual((line.model, line.case_id, line.sample, line.run_id, line.attempt), ("openai:modelo-falso", "C1", 1, "r1", 1))
        self.assertEqual(line.catalog_sha256, catalog_sha256(self.catalog_file))
        self.assertEqual((line.usd_to_eur, line.price_period["fonte"]), (Decimal("0.5"), "https://exemplo.test/precos"))
        self.assertEqual((line.requested_params["temperatura"], line.requested_params["tokens_max"]), (1.0, 1000))
        self.assertEqual(line.count_mode, "pior_caso")

    def test_the_provenance_links_to_every_saved_answer(self):
        from aferidor.proveniencia import unmatched
        self.go(Scripted([]), cases=3, repetitions=2)
        self.assertEqual(unmatched(read_answers(self.answers), read_records(self.folder / FILE_NAME)), ([], []))

    def test_without_a_declared_served_model_it_says_so_and_carries_on(self):
        provider = Scripted([])
        result = self.go(provider, cases=2)
        self.assertEqual((provider.calls, len(result.answers)), (2, 2))
        self.assertEqual({r.served_check for r in read_records(self.folder / FILE_NAME)}, {"nao_declarado"})
        self.assertEqual({r.served_model for r in read_records(self.folder / FILE_NAME)}, {""})


class TestTheCeiling(WithAPaidFolder):
    def test_the_run_stops_before_the_call_that_would_pass_the_ceiling_and_keeps_what_it_has(self):
        provider = Scripted([])
        result = self.go(provider, cases=5, ceiling="0.011")  # 0.0051 per call at the worst case: two fit
        self.assertEqual((provider.calls, len(result.answers)), (2, 2))
        self.assertIn("teto de 0.0110 EUR", result.stopped)
        self.assertIn("Nada do que já estava guardado foi apagado", result.stopped)
        self.assertFalse(result.complete)
        self.assertEqual(len(read_answers(self.answers)), 2)
        self.assertEqual(len([x for x in self.lines() if x["t"] == "intencao"]), 2)  # none written for the refused call

    def test_the_ceiling_is_shared_by_every_model_of_the_trial(self):
        other = dict(parametros=a_model_dict()["parametros"])
        self.catalog_file.write_text(json.dumps(catalog_dict(
            modelos={"pago": model_dict(**other), "outro": {**model_dict(**other), "id_pedido": "outro-modelo"}},
            usd_para_eur={"valor": 0.5, "fonte": "https://exemplo.test/bce", "lido_em": "2026-10-11"},
        )), encoding="utf-8")
        self.catalog = parse_catalog(self.catalog_file.read_text(encoding="utf-8"))
        first = Scripted([], name="openai:modelo-falso")
        run([a_case("C1"), a_case("C2")], first, path=self.answers, run_id="r1", config=self.config(), paid=self.paid("0.011"))
        second = Scripted([], name="openai:outro-modelo")
        result = run([a_case("C1")], second, path=self.folder / "outro.jsonl", run_id="r2", config=self.config(),
                     paid=self.paid("0.011", key="outro"))
        self.assertEqual((second.calls, len(result.answers)), (0, 0))
        self.assertIn("teto", result.stopped)

    def test_a_stopped_run_is_not_a_complete_one_and_says_so_in_its_summary(self):
        result = self.go(Scripted([]), cases=3, ceiling="0.006")
        self.assertIn("parada antes do fim", result.summary())
        self.assertFalse(result.complete)


class TestTheServedModel(WithAPaidFolder):
    def test_another_model_serving_the_call_stops_the_run_at_that_call(self):
        provider = Scripted([ok(served=REQUESTED), ok(served="outro-modelo"), ok(served=REQUESTED)])
        result = self.go(provider, cases=3)
        self.assertEqual((provider.calls, len(result.answers)), (2, 1))
        self.assertIn("serviu 'outro-modelo' em vez de 'modelo-falso'", result.stopped)
        self.assertEqual(len(read_answers(self.answers)), 1)  # the answer of the other model is not kept
        states = [(r.case_id, r.served_check, r.state) for r in read_records(self.folder / FILE_NAME)]
        self.assertEqual(states, [("C1", "igual", "resposta"), ("C2", "diferente", "resposta")])
        self.assertEqual(len([x for x in self.lines() if x["t"] == "resultado"]), 2)  # the call was paid, and counted

    def test_a_dated_snapshot_stops_it_too_until_the_catalogue_accepts_it(self):
        result = self.go(Scripted([ok(served=REQUESTED + "-20261001")]), cases=2)
        self.assertEqual(len(result.answers), 0)
        self.assertIsNotNone(result.stopped)


class TestAcceptedServedIds(WithAPaidFolder):
    ACCEPTED = [REQUESTED + "-20261001"]

    def test_an_id_the_catalogue_lists_as_accepted_passes(self):
        result = self.go(Scripted([ok(served=REQUESTED + "-20261001")] * 2), cases=2)
        self.assertEqual((len(result.answers), result.stopped), (2, None))
        self.assertEqual({r.served_check for r in read_records(self.folder / FILE_NAME)}, {"igual"})


class TestFailures(WithAPaidFolder):
    def test_an_error_that_was_not_processed_is_free_and_the_retry_goes_through_the_ledger_again(self):
        down = ProviderError("503", retryable=True, maybe_billed=False)
        provider = Scripted([down, ok()])
        result = self.go(provider, cases=1)
        self.assertEqual((provider.calls, len(result.answers)), (2, 1))
        self.assertEqual([x["estado"] for x in self.lines() if x["t"] == "resultado"], ["erro", "resposta"])
        self.assertEqual([x["tentativa"] for x in self.lines() if x["t"] == "intencao"], [1, 2])
        self.assertEqual([(r.attempt, r.state) for r in read_records(self.folder / FILE_NAME)], [(1, "erro"), (2, "resposta")])
        self.assertEqual(Decimal(self.lines()[1]["custo_eur"]), 0)
        self.assertEqual(self.sleeps, [2.0])

    def test_a_timeout_may_have_been_paid_so_it_counts_the_worst_case_and_is_not_repeated(self):
        provider = Scripted([ProviderError("excedeu 60s", retryable=True), ok()])
        result = self.go(provider, cases=2)
        self.assertEqual(provider.calls, 2)  # C1 once, then on to C2: the timed out call is not asked again
        self.assertEqual([a.case_id for a in result.answers], ["C2"])
        self.assertIn("pode ter sido cobrada", result.errors["C1"])
        first = [x for x in self.lines() if x["t"] == "resultado"][0]
        self.assertEqual((first["estado"], first["modo"]), ("resultado_desconhecido", "pior_caso"))
        self.assertEqual(self.sleeps, [])

    def test_a_second_run_does_not_ask_again_for_what_may_already_have_been_paid(self):
        self.go(Scripted([ProviderError("excedeu 60s", retryable=True)]), cases=1)
        again = Scripted([])
        result = run([a_case("C1")], again, path=self.answers, run_id="r2", config=self.config(), paid=self.paid())
        self.assertEqual(again.calls, 0)
        self.assertIn("já foi pedida", result.errors["C1"])

    def test_a_truncated_or_refused_or_empty_reply_is_paid_written_and_not_repeated(self):
        for finish, text, state in (("length", "a meio", "truncada"), ("filtered", "", "recusa_api"), ("stop", "  ", "vazia")):
            with self.subTest(estado=state):
                folder = self.folder / state
                folder.mkdir()
                from aferidor.pago import PaidCalls
                paid = PaidCalls(catalog=self.catalog, model_key="pago", ledger=Ledger(folder / "custos.jsonl"),
                                 provenance_file=folder / FILE_NAME, ensaio="e1", ceiling_eur=Decimal(1),
                                 catalog_path=self.catalog_file, day=DAY)
                provider = Scripted([ok(text=text, finish=finish), ok()])
                result = run([a_case("C1")], provider, path=folder / "r.jsonl", run_id="r1", config=self.config(), paid=paid)
                self.assertEqual((provider.calls, result.answers), (1, []))
                self.assertIn("C1", result.errors)
                (line,) = read_records(folder / FILE_NAME)
                self.assertEqual(line.state, state)
                billed = [x for x in (json.loads(t) for t in (folder / "custos.jsonl").read_text().splitlines()) if x["t"] == "resultado"]
                self.assertGreater(Decimal(billed[0]["custo_eur"]), 0)


class TestBackoff(WithAPaidFolder):
    def limited(self, seconds):
        return ProviderError("429", retryable=True, retry_after=seconds, maybe_billed=False)

    def test_it_waits_what_the_server_asked(self):
        provider = Scripted([self.limited(7.0), self.limited(3.0), ok()])
        result = self.go(provider, cases=1)
        self.assertEqual((len(result.answers), self.sleeps), (1, [7.0, 3.0]))

    def test_without_a_retry_after_it_uses_the_usual_backoff(self):
        provider = Scripted([ProviderError("429", retryable=True, maybe_billed=False)] * 2 + [ok()])
        self.go(provider, cases=1)
        self.assertEqual(self.sleeps, [2.0, 4.0])

    def test_a_wait_the_server_asks_for_beyond_the_limit_is_not_taken_the_call_is_given_up(self):
        provider = Scripted([self.limited(500.0), ok()])
        result = self.go(provider, cases=1)
        self.assertEqual((provider.calls, self.sleeps, result.answers), (1, [], []))
        self.assertIn("429", result.errors["C1"])

    def test_the_total_wait_on_one_call_is_capped(self):
        provider = Scripted([self.limited(30.0)] * 5)
        result = self.go(provider, cases=1, attempts=5, max_total_wait_s=50.0)
        self.assertEqual(self.sleeps, [30.0])
        self.assertEqual(provider.calls, 2)
        self.assertEqual(result.answers, [])

    def test_the_attempts_are_still_limited(self):
        provider = Scripted([self.limited(1.0)] * 9)
        self.go(provider, cases=1, attempts=3)
        self.assertEqual((provider.calls, self.sleeps), (3, [1.0, 1.0]))

    def test_each_attempt_that_failed_unpaid_is_in_the_ledger_and_costs_nothing(self):
        self.go(Scripted([self.limited(1.0)] * 3), cases=1, attempts=3)
        results = [x for x in self.lines() if x["t"] == "resultado"]
        self.assertEqual([x["estado"] for x in results], ["erro"] * 3)
        self.assertEqual(self.ledger.summary("e1")["gasto_eur"], 0)

    def test_a_key_or_a_model_that_does_not_exist_is_not_retried(self):
        provider = Scripted([ProviderError("401", retryable=False, maybe_billed=False), ok()])
        self.go(provider, cases=1)
        self.assertEqual((provider.calls, self.sleeps), (1, []))


class TestWhatClassifiesAFailureAsPossiblyBilled(unittest.TestCase):
    def raised(self, error) -> ProviderError:
        from aferidor.providers import OpenAIProvider
        patched = mock.MagicMock(side_effect=error)
        with mock.patch("aferidor.providers.urllib.request.urlopen", patched), self.assertRaises(ProviderError) as caught:
            OpenAIProvider(model="m", api_key="k").ask("p")
        return caught.exception

    def test_a_status_from_the_server_or_a_request_that_never_left_is_certainly_unbilled(self):
        import io
        import ssl
        import urllib.error
        for error in (urllib.error.HTTPError("u", 429, "x", {}, io.BytesIO(b"")), urllib.error.HTTPError("u", 503, "x", {}, io.BytesIO(b"")),
                      urllib.error.HTTPError("u", 401, "x", {}, io.BytesIO(b"")), urllib.error.URLError("sem rede"),
                      ssl.SSLCertVerificationError("mau")):
            with self.subTest(erro=type(error).__name__):
                self.assertFalse(self.raised(error).maybe_billed)

    def test_a_timeout_a_cut_connection_or_an_unreadable_reply_may_have_been_billed(self):
        import http.client
        for error in (TimeoutError(), ConnectionResetError("x"), http.client.RemoteDisconnected("x"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "x")):
            with self.subTest(erro=type(error).__name__):
                self.assertTrue(self.raised(error).maybe_billed)

    def test_the_default_is_the_cautious_one(self):
        self.assertTrue(ProviderError("x").maybe_billed)


if __name__ == "__main__":
    unittest.main()
