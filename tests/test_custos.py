"""The dry run, the ledger and the ceiling. No network, temporary files only, made-up prices."""

from __future__ import annotations

import ast
import json
import re
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from aferidor import custos
from aferidor.catalogo import CatalogError, EurosUnavailable, load_catalog, parse_catalog
from aferidor.custos import (
    AlreadyAsked,
    CeilingReached,
    JsonlError,
    Ledger,
    LedgerError,
    estimate,
    estimate_tokens,
    format_estimate,
)
from aferidor.runner import build_prompt
from aferidor.storage import read_cases
from tests.test_catalogo import catalog as catalog_dict
from tests.test_catalogo import model as model_dict
from tests.test_catalogo import period

ROOT = Path(__file__).resolve().parent.parent
DAY = date(2026, 10, 11)
PROMPT = "x" * 300  # 100 tokens by the estimate
WORST_USD = Decimal("0.0102")  # 100 in at 2, 1000 out at 10, per million
WORST_EUR = Decimal("0.0051")  # at the rate of 0.5 EUR per USD used here


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def a_catalog(rate: float | None = 0.5):
    def reasoning(value):
        return model_dict(parametros={"campo_tokens": "max_tokens", "temperatura": "desconhecido", "tokens_raciocinio": value,
                                      "esforco_raciocinio": None, "tokens_max": 1000})
    models = {
        "pago": reasoning("desconhecido"),
        "pago2": reasoning("desconhecido"),
        "uso": reasoning("incluidos_na_saida"),
        "sep": reasoning("separados_da_saida"),
        "outro": {**reasoning("desconhecido"), "fornecedor": "anthropic"},
        "gratis": {**reasoning("desconhecido"), "precos": [period(entrada_por_milhao=0, saida_por_milhao=0)]},
        "curto": {**reasoning("desconhecido"), "precos": [period(prompt_tokens_ate=10)]},
        "sem_limite": model_dict(parametros={"campo_tokens": "max_tokens", "temperatura": "desconhecido",
                                             "tokens_raciocinio": "desconhecido", "esforco_raciocinio": None, "tokens_max": None}),
    }
    data = catalog_dict(modelos=models)
    data["usd_para_eur"] = ({"valor": rate, "fonte": "https://exemplo.test/bce", "lido_em": "2026-10-11"}
                            if rate is not None else {"valor": None, "fonte": "", "lido_em": None})
    return parse_catalog(json.dumps(data))


CATALOG = a_catalog()


def reserve(ledger: Ledger, *, key="pago", case="C1", sample=1, ceiling="1", ensaio="e1", repeat=False, catalog=None):
    return ledger.reserve(catalog=catalog or CATALOG, ensaio=ensaio, run_id="r1", model_key=key, case_id=case,
                          sample=sample, prompt=PROMPT, tokens_max=1000, day=DAY, ceiling_eur=ceiling, repeat=repeat)


class WithAFolder(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.folder = Path(self._dir.name)
        self.path = self.folder / "custos.jsonl"
        self.ledger = Ledger(self.path)

    def lines(self) -> list[dict]:
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines()] if self.path.exists() else []


class TestTheDryRun(unittest.TestCase):
    def prompts(self):
        found = []
        for name in ("casos.json", "consulta.json"):
            found += [build_prompt(c) for c in read_cases(ROOT / "casos" / name)]
        return found

    def test_it_makes_no_request_and_does_not_even_import_the_providers(self):
        failing = mock.MagicMock(side_effect=AssertionError("pedido feito numa estimativa"))
        with mock.patch("urllib.request.urlopen", failing), mock.patch("socket.create_connection", failing):
            found = estimate(CATALOG, ["pago"], [PROMPT], day=DAY)
        failing.assert_not_called()
        imported = {n.module for n in ast.walk(ast.parse(Path(custos.__file__).read_text(encoding="utf-8")))
                    if isinstance(n, ast.ImportFrom) and n.module} | {a.name for n in ast.walk(ast.parse(Path(custos.__file__).read_text(encoding="utf-8")))
                                                                      if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse({m for m in imported if "providers" in m or "urllib" in m or "http" in m})
        self.assertEqual(found.models[0].calls, 5)

    def test_the_real_bank_is_58_cases_times_5_samples_is_290_calls_per_model(self):
        prompts = self.prompts()
        found = estimate(load_catalog(), ["claude-opus-5-5", "gpt-6-luna"], prompts, day=DAY)
        self.assertEqual((len(prompts), found.prompts, found.samples), (58, 58, 5))
        self.assertEqual([m.calls for m in found.models], [290, 290])
        self.assertEqual(found.models[0].input_tokens, sum(estimate_tokens(p) for p in prompts) * 5)

    def test_the_estimate_of_tokens_is_characters_over_three_rounded_up(self):
        self.assertEqual([estimate_tokens(t) for t in ("", "a", "abc", "abcd")], [0, 1, 1, 2])

    def test_three_scenarios_and_the_ones_above_the_limit_fold_into_it(self):
        sizes = lambda limit: [s.output_tokens_per_call for s in estimate(CATALOG, ["pago"], [PROMPT], day=DAY, tokens_max=limit).models[0].scenarios]
        self.assertEqual(sizes(8192), [1000, 4000, 8192])
        self.assertEqual(sizes(2000), [1000, 2000])
        self.assertEqual(sizes(1000), [1000])
        self.assertEqual(sizes(None), [1000])  # the model's own tokens_max is 1000

    def test_the_cost_is_calls_times_the_cost_of_one(self):
        found = estimate(CATALOG, ["pago"], [PROMPT], day=DAY, samples=10)
        scenario = found.models[0].scenarios[-1]
        self.assertEqual((scenario.usd, scenario.eur), (WORST_USD * 10, WORST_EUR * 10))

    def test_models_add_up_in_the_total(self):
        found = estimate(CATALOG, ["pago", "uso"], [PROMPT], day=DAY, samples=1)
        self.assertEqual(found.total(0), (WORST_USD * 2, WORST_EUR * 2))

    def test_a_missing_price_refuses_and_says_so(self):
        with self.assertRaisesRegex(CatalogError, "não tem preço de curto"):
            estimate(CATALOG, ["curto"], [PROMPT], day=DAY)

    def test_a_missing_rate_refuses_and_says_why(self):
        with self.assertRaisesRegex(EurosUnavailable, "não tem taxa"):
            estimate(a_catalog(rate=None), ["pago"], [PROMPT], day=DAY)

    def test_without_a_token_limit_there_is_no_worst_case_and_it_refuses(self):
        with self.assertRaisesRegex(CatalogError, "tokens_max"):
            estimate(CATALOG, ["sem_limite"], [PROMPT], day=DAY)
        self.assertEqual(estimate(CATALOG, ["sem_limite"], [PROMPT], day=DAY, tokens_max=500).models[0].scenarios[-1].output_tokens_per_call, 500)

    def test_nothing_to_estimate_is_an_error_not_a_free_run(self):
        for models, prompts in (([], [PROMPT]), (["pago"], [])):
            with self.assertRaises(LedgerError):
                estimate(CATALOG, models, prompts, day=DAY)

    def test_the_ceiling_flags_the_scenarios_that_pass_it(self):
        found = estimate(CATALOG, ["pago"], [PROMPT], day=DAY, samples=10, ceiling_eur="0.05")
        self.assertEqual([s.over_ceiling for s in found.models[0].scenarios], [WORST_EUR * 10 > Decimal("0.05")])
        text = format_estimate(found)
        self.assertIn("Nenhum pedido foi feito", text)
        self.assertIn("EXCEDE O TETO", text)
        self.assertNotIn("EXCEDE", format_estimate(estimate(CATALOG, ["pago"], [PROMPT], day=DAY, ceiling_eur="5")))

    def test_the_real_catalogue_prices_a_full_trial(self):
        found = estimate(load_catalog(), ["claude-opus-5-5"], self.prompts(), day=DAY, tokens_max=8192)
        low, high = found.models[0].scenarios[0], found.models[0].scenarios[-1]
        self.assertLess(low.eur, high.eur)
        self.assertGreater(low.eur, 0)


class TestTheLedger(WithAFolder):
    def test_an_intention_is_written_before_the_call_with_its_worst_case(self):
        reservation = reserve(self.ledger)
        (line,) = self.lines()
        self.assertEqual((line["t"], line["id"], line["modelo"], line["caso"], line["amostra"]), ("intencao", reservation.intent_id, "pago", "C1", 1))
        self.assertEqual((Decimal(line["pior_caso_usd"]), Decimal(line["pior_caso_eur"])), (WORST_USD, WORST_EUR))
        self.assertEqual((line["tokens_max"], line["entrada_estimada"], line["tentativa"], line["repeticao"]), (1000, 100, 1, False))

    def test_a_result_is_a_second_line_and_the_total_counts_the_call_once(self):
        first = reserve(self.ledger)
        self.ledger.settle(first.intent_id, catalog=CATALOG, state="resposta", usage=None)
        self.assertEqual([x["t"] for x in self.lines()], ["intencao", "resultado"])
        summary = self.ledger.summary("e1")
        self.assertEqual((summary["chamadas"], summary["sem_resultado"], summary["gasto_eur"]), (1, 0, WORST_EUR))

    def test_the_ceiling_stops_before_the_call_that_would_pass_it_and_writes_nothing(self):
        with self.assertRaises(CeilingReached) as caught:
            reserve(self.ledger, ceiling="0.005")
        self.assertFalse(self.path.exists() and self.path.read_text(encoding="utf-8"))
        self.assertIn("teto de 0.0050 EUR", str(caught.exception))
        self.assertEqual(caught.exception.summary["chamadas"], 0)

    def test_exactly_at_the_ceiling_is_allowed_one_cent_over_is_not(self):
        reserve(self.ledger, ceiling=str(WORST_EUR))
        with self.assertRaises(CeilingReached):
            reserve(self.ledger, case="C2", ceiling=str(WORST_EUR))

    def test_the_ceiling_is_the_trials_all_models_together(self):
        reserve(self.ledger, key="pago", ceiling="0.0100")
        with self.assertRaises(CeilingReached) as caught:
            reserve(self.ledger, key="outro", ceiling="0.0100")
        self.assertIn("openai 0.0051 EUR", str(caught.exception))
        self.assertEqual(len(self.lines()), 1)

    def test_another_trial_has_its_own_total(self):
        reserve(self.ledger, ceiling=str(WORST_EUR), ensaio="e1")
        reserve(self.ledger, ceiling=str(WORST_EUR), ensaio="e2")
        self.assertEqual(self.ledger.summary("e2")["chamadas"], 1)

    def test_a_stopped_ledger_works_again_after_the_refusal(self):
        with self.assertRaises(CeilingReached):
            reserve(self.ledger, ceiling="0.001")
        reserve(self.ledger, ceiling="1")
        self.assertEqual(len(self.lines()), 1)

    def test_a_free_model_never_reaches_a_ceiling_of_zero(self):
        reserve(self.ledger, key="gratis", ceiling="0")
        self.assertEqual(self.ledger.summary("e1")["gasto_eur"], 0)

    def test_the_ceiling_cannot_be_negative_and_the_numbers_must_be_positive(self):
        for kwargs in ({"ceiling": "-1"},):
            with self.assertRaises(LedgerError):
                reserve(self.ledger, **kwargs)
        with self.assertRaises(LedgerError):
            self.ledger.reserve(catalog=CATALOG, ensaio="e", run_id="r", model_key="pago", case_id="C", sample=0,
                                prompt=PROMPT, tokens_max=1000, day=DAY, ceiling_eur=1)

    def test_an_unpriceable_call_is_refused_before_anything_is_written(self):
        for key, error in (("curto", CatalogError), ("desconhecido", CatalogError)):
            with self.subTest(modelo=key), self.assertRaises(error):
                reserve(self.ledger, key=key)
        with self.assertRaises(EurosUnavailable):
            reserve(self.ledger, catalog=a_catalog(rate=None))
        self.assertFalse(self.path.exists() and self.path.read_text(encoding="utf-8"))

    def test_the_numbers_are_written_without_an_exponent(self):
        reserve(self.ledger, key="gratis")
        self.assertNotIn("E", "".join(f"{x['pior_caso_usd']}{x['pior_caso_eur']}" for x in self.lines()))


class TestAfterAnInterruption(WithAFolder):
    def test_the_total_is_rebuilt_from_the_file_by_a_new_process(self):
        done = reserve(self.ledger)
        self.ledger.settle(done.intent_id, catalog=CATALOG, state="resposta")
        reserve(self.ledger, case="C2")
        summary = Ledger(self.path).summary("e1")
        self.assertEqual((summary["chamadas"], summary["sem_resultado"], summary["gasto_eur"]), (2, 1, WORST_EUR * 2))

    def test_an_intention_without_a_result_counts_at_its_worst_case_and_is_not_repeated(self):
        reserve(self.ledger)
        fresh = Ledger(self.path)
        self.assertEqual(fresh.summary("e1")["gasto_eur"], WORST_EUR)
        with self.assertRaisesRegex(AlreadyAsked, "pedido explícito"):
            reserve(fresh)

    def test_an_explicit_repeat_goes_ahead_is_written_and_counts_again(self):
        reserve(self.ledger)
        second = reserve(self.ledger, repeat=True)
        line = self.lines()[-1]
        self.assertEqual((second.attempt, line["tentativa"], line["repeticao"]), (2, 2, True))
        self.assertEqual(self.ledger.summary("e1")["gasto_eur"], WORST_EUR * 2)

    def test_every_billed_state_blocks_a_second_ask_and_only_an_error_does_not(self):
        for state in ("resposta", "recusa_api", "truncada", "vazia", "resultado_desconhecido"):
            with self.subTest(estado=state):
                ledger = Ledger(self.folder / f"{state}.jsonl")
                first = reserve(ledger)
                ledger.settle(first.intent_id, catalog=CATALOG, state=state)
                with self.assertRaises(AlreadyAsked):
                    reserve(ledger)
        ledger = Ledger(self.folder / "erro.jsonl")
        first = reserve(ledger)
        ledger.settle(first.intent_id, catalog=CATALOG, state="erro")
        again = reserve(ledger)
        self.assertEqual(again.attempt, 2)
        self.assertEqual([x["repeticao"] for x in [json.loads(t) for t in (self.folder / "erro.jsonl").read_text().splitlines()] if x["t"] == "intencao"], [False, False])

    def test_an_error_costs_nothing_so_it_does_not_eat_the_ceiling(self):
        first = reserve(self.ledger, ceiling=str(WORST_EUR))
        self.ledger.settle(first.intent_id, catalog=CATALOG, state="erro")
        self.assertEqual(self.ledger.summary("e1")["gasto_eur"], 0)
        reserve(self.ledger, case="C2", ceiling=str(WORST_EUR))

    def test_a_line_cut_short_by_a_dead_writer_is_ignored_and_then_dropped(self):
        reserve(self.ledger)
        with self.path.open("ab") as handle:
            handle.write(b'{"t":"intencao","id":"cort')
        self.assertEqual(Ledger(self.path).summary("e1")["chamadas"], 1)
        reserve(self.ledger, case="C2")
        self.assertEqual(len(self.lines()), 2)  # every line parses again, the fragment is gone

    def test_a_complete_last_line_missing_only_its_newline_is_kept(self):
        reserve(self.ledger)
        self.path.write_bytes(self.path.read_bytes().rstrip(b"\n"))
        reserve(self.ledger, case="C2")
        self.assertEqual(len(self.lines()), 2)

    def test_a_corrupt_line_in_the_middle_is_an_error_that_names_the_line_not_its_content(self):
        reserve(self.ledger)
        reserve(self.ledger, case="C2")
        lines = self.path.read_text(encoding="utf-8").splitlines()
        lines[0] = "SEGREDO-NA-LINHA isto não é json"
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(JsonlError) as caught:
            Ledger(self.path).summary("e1")
        self.assertIn("linha 1", str(caught.exception))
        self.assertNotIn("SEGREDO", str(caught.exception))

    def test_a_line_that_is_json_but_not_a_ledger_line_is_refused(self):
        reserve(self.ledger)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write('{"t":"resultado","intencao":"nao-existe"}\n')
        with self.assertRaisesRegex(LedgerError, "linha 2"):
            Ledger(self.path).summary("e1")

    def test_a_result_is_written_once_and_only_for_a_known_intention(self):
        first = reserve(self.ledger)
        self.ledger.settle(first.intent_id, catalog=CATALOG, state="resposta")
        with self.assertRaisesRegex(LedgerError, "já tem resultado"):
            self.ledger.settle(first.intent_id, catalog=CATALOG, state="resposta")
        with self.assertRaisesRegex(LedgerError, "nenhuma intenção"):
            self.ledger.settle("inventado", catalog=CATALOG, state="resposta")
        second = reserve(self.ledger, case="C2")
        with self.assertRaisesRegex(LedgerError, "estado 'talvez' desconhecido"):
            self.ledger.settle(second.intent_id, catalog=CATALOG, state="talvez")

    def test_the_summary_adds_up_by_provider_and_model(self):
        reserve(self.ledger, key="pago")
        reserve(self.ledger, key="pago2")
        reserve(self.ledger, key="outro")
        summary = self.ledger.summary("e1")
        self.assertEqual(summary["por_fornecedor"], {"openai": WORST_EUR * 2, "anthropic": WORST_EUR})
        self.assertEqual(sorted(summary["por_modelo"]), ["outro", "pago", "pago2"])


class TestHowACallIsCounted(WithAFolder):
    calls = 0

    def settle(self, key, state, usage):
        self.calls += 1
        reservation = reserve(self.ledger, key=key, case=f"C{self.calls}")
        outcome = self.ledger.settle(reservation.intent_id, catalog=CATALOG, state=state, usage=usage)
        return outcome, self.lines()[-1]

    def test_with_reasoning_unknown_the_worst_case_is_counted_and_the_usage_sits_beside_it(self):
        outcome, line = self.settle("pago", "resposta", SimpleNamespace(input_tokens=50, output_tokens=10, reasoning_tokens=None))
        self.assertEqual((outcome.count_mode, outcome.usd), ("pior_caso", Decimal("0.0101")))  # 50 in, 1000 out at the cap
        self.assertEqual(line["usage"], {"entrada": 50, "saida": 10, "raciocinio": None})
        self.assertIn("raciocínio", line["motivo"])
        self.assertGreater(outcome.usd, Decimal(50 * 2 + 10 * 10) / 1_000_000)

    def test_without_declared_input_the_estimate_is_used_and_the_line_says_so(self):
        outcome, line = self.settle("pago", "resposta", None)
        self.assertEqual(outcome.usd, WORST_USD)
        self.assertIn("entrada estimada", line["motivo"])
        self.assertIsNone(line["usage"])

    def test_a_model_that_counts_reasoning_in_the_output_is_counted_by_the_usage(self):
        outcome, _ = self.settle("uso", "resposta", {"input_tokens": 50, "output_tokens": 10})
        self.assertEqual((outcome.count_mode, outcome.usd, outcome.eur), ("usage", Decimal("0.0002"), Decimal("0.0001")))

    def test_a_model_that_reports_reasoning_apart_has_it_added_to_the_output(self):
        outcome, _ = self.settle("sep", "resposta", SimpleNamespace(input_tokens=50, output_tokens=10, reasoning_tokens=30))
        self.assertEqual((outcome.count_mode, outcome.usd), ("usage", Decimal("0.0005")))
        outcome, _ = self.settle("sep", "resposta", SimpleNamespace(input_tokens=50, output_tokens=10, reasoning_tokens=None))
        self.assertEqual(outcome.count_mode, "pior_caso")

    def test_when_the_usage_that_would_be_trusted_is_missing_it_falls_back_to_the_worst_case(self):
        for usage in (None, {"input_tokens": 50}, {"output_tokens": 10}):
            outcome, _ = self.settle("uso", "resposta", usage)
            self.assertEqual(outcome.count_mode, "pior_caso")

    def test_an_unknown_result_is_the_worst_case_even_when_the_catalogue_would_trust_the_usage(self):
        outcome, _ = self.settle("uso", "resultado_desconhecido", {"input_tokens": 50, "output_tokens": 10})
        self.assertEqual(outcome.count_mode, "pior_caso")

    def test_a_refused_truncated_or_empty_reply_was_still_billed(self):
        for state in ("recusa_api", "truncada", "vazia"):
            outcome, _ = self.settle("pago", state, None)
            self.assertGreater(outcome.usd, 0)

    def test_an_error_costs_nothing_and_says_why(self):
        outcome, line = self.settle("pago", "erro", None)
        self.assertEqual((outcome.count_mode, outcome.usd, outcome.eur), ("sem_custo", 0, 0))
        self.assertIn("sem processar", line["motivo"])

    def test_a_garbage_usage_is_dropped_not_trusted(self):
        outcome, line = self.settle("uso", "resposta", {"input_tokens": "50", "output_tokens": -5})
        self.assertEqual((outcome.count_mode, line["usage"]), ("pior_caso", None))


class TestTwoWritersOneSample(WithAFolder):
    def race(self, jobs):
        outcomes: list[str] = []
        barrier = threading.Barrier(len(jobs))

        def work(case, sample):
            barrier.wait()
            try:
                reserve(Ledger(self.path), case=case, sample=sample, ceiling="0.0200")
                outcomes.append("ok")
            except AlreadyAsked:
                outcomes.append("ja")
            except CeilingReached:
                outcomes.append("teto")

        threads = [threading.Thread(target=work, args=job) for job in jobs]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return outcomes

    def test_eight_threads_asking_for_the_same_sample_get_it_once(self):
        outcomes = self.race([("C1", 1)] * 8)
        self.assertEqual((outcomes.count("ok"), outcomes.count("ja")), (1, 7))
        self.assertEqual(len(self.lines()), 1)

    def test_the_ceiling_holds_when_many_ask_at_once_for_different_samples(self):
        outcomes = self.race([("C1", n) for n in range(1, 11)])
        allowed = int(Decimal("0.0200") / WORST_EUR)  # 3 calls of 0.0051 fit in 0.0200
        self.assertEqual(outcomes.count("ok"), allowed)
        self.assertEqual(outcomes.count("teto"), 10 - allowed)
        self.assertLessEqual(Ledger(self.path).summary("e1")["gasto_eur"], Decimal("0.0200"))

    def test_four_separate_processes_asking_for_the_same_sample_get_it_once(self):
        catalog_file = self.folder / "catalogo.json"
        data = catalog_dict(modelos={"pago": a_model_dict()}, usd_para_eur={"valor": 0.5, "fonte": "https://x.test", "lido_em": "2026-10-11"})
        catalog_file.write_text(json.dumps(data), encoding="utf-8")
        start = self.folder / "arranque"
        script = (
            "import sys, time\n"
            f"sys.path.insert(0, {str(ROOT)!r})\n"
            "from datetime import date\n"
            "from pathlib import Path\n"
            "from aferidor.catalogo import load_catalog\n"
            "from aferidor.custos import AlreadyAsked, CeilingReached, Ledger\n"
            "catalog = load_catalog(Path(sys.argv[2]))\n"
            "while not Path(sys.argv[3]).exists():\n"
            "    time.sleep(0.001)\n"
            "try:\n"
            "    Ledger(sys.argv[1]).reserve(catalog=catalog, ensaio='e1', run_id='r', model_key='pago', case_id='C1', sample=1,\n"
            "        prompt='x' * 300, tokens_max=1000, day=date(2026, 10, 11), ceiling_eur='1')\n"
            "    print('ok')\n"
            "except AlreadyAsked:\n"
            "    print('ja')\n"
        )
        children = [subprocess.Popen([sys.executable, "-I", "-c", script, str(self.path), str(catalog_file), str(start)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT,
                                     env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}) for _ in range(4)]
        start.write_text("vai", encoding="utf-8")
        results = [c.communicate(timeout=60) for c in children]
        self.assertEqual([c.returncode for c in children], [0, 0, 0, 0], [r[1] for r in results])
        self.assertEqual(sorted(r[0].strip() for r in results), ["ja", "ja", "ja", "ok"])
        self.assertEqual(len(self.lines()), 1)


def a_model_dict():
    return model_dict(parametros={"campo_tokens": "max_tokens", "temperatura": "desconhecido", "tokens_raciocinio": "desconhecido",
                                  "esforco_raciocinio": None, "tokens_max": 1000})


class TestNoPriceInTheNewModules(unittest.TestCase):
    def test_neither_module_carries_a_price_or_a_model_id(self):
        ids = [m.requested_id for m in load_catalog().models.values()]
        for name in ("custos.py", "proveniencia.py"):
            text = (ROOT / "aferidor" / name).read_text(encoding="utf-8")
            with self.subTest(modulo=name):
                self.assertIsNone(re.search(r"\d\s*(?:USD|EUR|€)|(?:USD|EUR|€|\$)\s*\d|por milh", text, flags=re.IGNORECASE))
                for requested in ids:
                    self.assertNotIn(requested, text)


if __name__ == "__main__":
    unittest.main()
