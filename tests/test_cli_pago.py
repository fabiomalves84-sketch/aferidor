"""The command line around a paid model: --teto-eur, --a-seco and --piloto, and that nothing changes without them.
`build_provider` is replaced by a scripted provider, so there is no key and no network."""

from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from aferidor import cli
from aferidor.catalogo import load_catalog
from aferidor.proveniencia import FILE_NAME, read_records
from aferidor.storage import read_answers, read_cases
from tests.compat_support import GOLDEN, scenario
from tests.test_pago import Scripted

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "casos" / "casos.json"
PAID = ["--fornecedor", "anthropic", "--modelo", "claude-opus-5-5"]


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


class WithACli(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.folder = Path(self._dir.name)
        self.saida = self.folder / "ensaio" / "respostas.jsonl"
        self.provider = Scripted([], name="anthropic:claude-opus-5-5", max_tokens=4096)
        self.build_calls: list[dict] = []

    def build(self, kind, model, **kwargs):
        self.build_calls.append({"kind": kind, "model": model, **kwargs})
        return self.provider

    def main(self, *argv, env=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(cli, "build_provider", self.build), mock.patch.dict(os.environ, env or {}, clear=bool(env is not None)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def tree(self) -> list[str]:
        return sorted(str(p.relative_to(self.folder)) for p in self.folder.rglob("*"))


class TestAPaidModelNeedsACeiling(WithACli):
    def test_it_refuses_to_start_and_says_what_to_do(self):
        code, out, err = self.main("executar", *PAID, "--casos", str(CASES), "--saida", str(self.saida), "--limite", "2")
        self.assertEqual(code, 2)
        self.assertIn("--teto-eur", err)
        self.assertIn("claude-opus-5-5 é um modelo pago", err)
        self.assertIn("--a-seco", err)
        self.assertEqual((self.build_calls, self.provider.calls, self.tree()), ([], 0, []))

    def test_a_default_model_that_the_catalogue_lists_is_paid_too(self):
        code, _, err = self.main("executar", "--fornecedor", "gemini", "--casos", str(CASES), "--saida", str(self.saida))
        self.assertEqual((code, self.provider.calls), (2, 0))
        self.assertIn("gemini-3.8-flash é um modelo pago", err)

    def test_models_the_catalogue_does_not_list_run_as_before_with_no_ledger_and_no_ceiling(self):
        for kind, model in (("gemini", "gemini-3.5-flash-lite"), ("local", "gemma3:12b"), ("falso", None)):
            with self.subTest(fornecedor=kind):
                saida = self.folder / kind / "respostas.jsonl"
                args = ["executar", "--fornecedor", kind, "--casos", str(CASES), "--saida", str(saida), "--limite", "2"]
                code, out, err = self.main(*args, *(["--modelo", model] if model else []))
                self.assertEqual(code, 0, err)
                self.assertEqual(sorted(p.name for p in saida.parent.iterdir()), ["respostas.jsonl"])
                self.assertNotIn("gasto contado", out)
                self.assertIsNone(self.build_calls[-1].get("timeout"))

    def test_the_ceiling_must_be_a_positive_amount_of_euros(self):
        for bad in ("0", "-3", "abc", "inf"):
            with self.subTest(teto=bad), self.assertRaises(SystemExit):
                with contextlib.redirect_stderr(io.StringIO()):
                    cli.parse_args(["executar", *PAID, "--teto-eur", bad])
        self.assertEqual(cli.parse_args(["executar", "--teto-eur", "12,5"]).teto_eur, Decimal("12.5"))

    def test_there_is_no_default_ceiling(self):
        self.assertIsNone(cli.parse_args(["executar"]).teto_eur)


class TestAPaidRun(WithACli):
    def run_paid(self, ceiling="100", *extra):
        return self.main("executar", *PAID, "--casos", str(CASES), "--saida", str(self.saida), "--limite", "2",
                         "--tokens-max", "4096", "--teto-eur", ceiling, *extra)

    def test_it_runs_with_a_ceiling_writes_the_ledger_and_the_provenance_beside_the_answers(self):
        code, out, err = self.run_paid()
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(p.name for p in self.saida.parent.iterdir()), sorted(["custos.jsonl", FILE_NAME, "respostas.jsonl"]))
        self.assertEqual(len(read_answers(self.saida)), 2)
        self.assertEqual(len(read_records(self.saida.with_name(FILE_NAME))), 2)
        self.assertIn("Estimativa a seco", out)  # the estimate is shown before the first call
        self.assertIn("gasto contado neste ensaio", out)

    def test_the_timeout_comes_from_the_catalogue(self):
        self.run_paid()
        self.assertEqual(self.build_calls[0]["timeout"], load_catalog().find("anthropic", "claude-opus-5-5").timeout_s)

    def test_a_ceiling_that_is_reached_stops_the_run_with_its_own_exit_code_and_the_reason(self):
        code, out, err = self.run_paid("0.05")
        self.assertEqual(code, cli.STOPPED)
        self.assertIn("parada:", err)
        self.assertIn("teto de 0.05", err)
        self.assertIn("Nada do que já estava guardado foi apagado", err)

    def test_stopping_by_the_ceiling_keeps_what_was_answered_and_a_later_run_continues_it(self):
        code, _, _ = self.run_paid("0.12")
        first = len(read_answers(self.saida)) if self.saida.exists() else 0
        self.assertEqual(code, cli.STOPPED)
        self.assertGreater(first, 0)
        code, _, err = self.run_paid("100")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(read_answers(self.saida)), 2)

    def test_a_missing_price_or_rate_is_refused_before_the_first_call(self):
        broken = json.loads((ROOT / "aferidor" / "catalogo.json").read_text(encoding="utf-8"))
        broken["usd_para_eur"] = {"valor": None, "fonte": "", "lido_em": None}
        path = self.folder / "sem-taxa.json"
        path.write_text(json.dumps(broken), encoding="utf-8")
        with mock.patch.object(cli, "load_catalog", lambda: load_catalog(path)):
            code, _, err = self.run_paid()
        self.assertEqual((code, self.provider.calls), (2, 0))
        self.assertIn("não tem taxa", err)

    def test_the_ensaio_command_also_stops_and_does_not_grade_a_half_run(self):
        code, _, err = self.main("ensaio", *PAID, "--casos", str(CASES), "--saida", str(self.saida), "--teto-eur", "0.05",
                                 "--vereditos", str(self.folder / "v.json"), "--relatorio", str(self.folder / "r.md"),
                                 "--tokens-max", "4096")
        self.assertEqual(code, cli.STOPPED)
        self.assertFalse((self.folder / "r.md").exists())
        self.assertIn("parada:", err)


class TestTheDryRun(WithACli):
    def dry(self, *extra, **kw):
        return self.main("executar", *PAID, "--casos", str(CASES), "--saida", str(self.saida), "--a-seco", *extra, **kw)

    def test_it_prints_the_estimate_and_exits_zero_without_building_a_provider_or_a_key(self):
        code, out, err = self.dry("--repeticoes", "5", "--tokens-max", "8192", env={})
        self.assertEqual((code, err), (0, ""))
        self.assertIn("27 prompts x 5 amostras. Nenhum pedido foi feito", out)
        self.assertIn("claude-opus-5-5: 135 chamadas", out)
        self.assertIn("saída de 8192 tokens por chamada", out)
        self.assertEqual(self.build_calls, [])

    def test_it_writes_nothing_not_even_the_folder(self):
        self.dry()
        self.assertEqual(self.tree(), [])

    def test_it_makes_no_request(self):
        failing = mock.MagicMock(side_effect=AssertionError("pedido feito em --a-seco"))
        with mock.patch("urllib.request.urlopen", failing), mock.patch("socket.create_connection", failing):
            code, _, _ = self.dry()
        self.assertEqual(code, 0)
        failing.assert_not_called()

    def test_it_does_not_need_a_ceiling_and_marks_the_scenarios_over_one_when_given(self):
        _, plain, _ = self.dry()
        self.assertNotIn("EXCEDE", plain)
        _, capped, _ = self.dry("--teto-eur", "0.01")
        self.assertIn("EXCEDE O TETO", capped)

    def test_a_model_that_is_not_paid_has_nothing_to_estimate(self):
        code, out, _ = self.main("executar", "--fornecedor", "local", "--a-seco", "--saida", str(self.saida))
        self.assertEqual(code, 0)
        self.assertIn("nada a estimar", out.replace("não há custo a estimar", "nada a estimar"))

    def test_the_ensaio_command_has_it_too(self):
        code, out, _ = self.main("ensaio", *PAID, "--casos", str(CASES), "--saida", str(self.saida), "--a-seco")
        self.assertEqual(code, 0)
        self.assertIn("Nenhum pedido foi feito", out)
        self.assertEqual(self.tree(), [])


class TestThePilot(WithACli):
    def pilot(self, *extra):
        return self.main("executar", *PAID, "--casos", str(CASES), "--saida", str(self.saida), "--tokens-max", "4096",
                         "--teto-eur", "100", "--piloto", *extra)

    def test_three_cases_two_samples_each_say_which_were_chosen_and_go_to_their_own_folder(self):
        code, out, err = self.pilot()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.provider.calls, 6)
        self.assertIn("ATB-PAC-001", out)
        self.assertIn("PED-OMA-021", out)
        self.assertIn("GRA-VPA-024", out)
        pilot_answers = self.saida.parent / "piloto" / "respostas.jsonl"
        self.assertEqual(sorted({(a.case_id, a.sample) for a in read_answers(pilot_answers)}),
                         [("ATB-PAC-001", 1), ("ATB-PAC-001", 2), ("GRA-VPA-024", 1), ("GRA-VPA-024", 2), ("PED-OMA-021", 1), ("PED-OMA-021", 2)])
        self.assertFalse(self.saida.exists())
        self.assertEqual(sorted(p.name for p in (self.saida.parent / "piloto").iterdir()), sorted(["custos.jsonl", FILE_NAME, "respostas.jsonl"]))

    def test_the_pilot_does_not_use_up_the_samples_of_the_trial_itself(self):
        self.pilot()
        code, _, err = self.main("executar", *PAID, "--casos", str(CASES), "--saida", str(self.saida), "--tokens-max", "4096",
                                 "--teto-eur", "100", "--limite", "3")
        self.assertEqual(code, 0, err)  # ATB-PAC-001 sample 1 is asked again: the pilot's ledger is the pilot's own

    def test_when_the_first_alternative_is_missing_it_takes_the_second_and_says_so(self):
        cases = [c for c in read_cases(CASES) if c.case_id != "PED-OMA-021"]
        chosen, said = cli._pilot_cases(cases)
        self.assertEqual([c.case_id for c in chosen], ["ATB-PAC-001", "ATB-FAR-004", "GRA-VPA-024"])
        self.assertIn("ATB-FAR-004 (e não PED-OMA-021, que o banco não tem)", said)

    def test_when_a_case_exists_in_neither_form_it_is_skipped_and_the_rest_are_asked(self):
        cases = [c for c in read_cases(CASES) if c.case_id != "GRA-VPA-024"]
        chosen, said = cli._pilot_cases(cases)
        self.assertEqual(len(chosen), 2)
        self.assertIn("nenhum de GRA-VPA-024 existe neste banco", said)

    def test_it_does_not_combine_with_a_limit_and_the_ensaio_command_does_not_take_it(self):
        code, _, err = self.pilot("--limite", "5")
        self.assertEqual((code, self.provider.calls), (2, 0))
        self.assertIn("--limite", err)
        code, _, err = self.main("ensaio", *PAID, "--saida", str(self.saida), "--teto-eur", "100", "--piloto")
        self.assertEqual((code, self.provider.calls), (2, 0))
        self.assertIn("executar --piloto", err)

    def test_the_pilot_still_needs_a_ceiling_for_a_paid_model(self):
        code, _, err = self.main("executar", *PAID, "--casos", str(CASES), "--saida", str(self.saida), "--piloto")
        self.assertEqual(code, 2)
        self.assertIn("--teto-eur", err)


class TestNothingChangesWithoutTheNewFlags(unittest.TestCase):
    def test_a_simulated_run_and_the_executar_command_are_byte_for_byte_what_they_were_before(self):
        before = json.loads(GOLDEN.read_text(encoding="utf-8"))
        now = json.loads(json.dumps(scenario()))
        self.assertEqual(now.keys(), before.keys())
        for key in before:
            with self.subTest(parte=key):
                self.assertEqual(now[key], before[key])

    def test_a_run_without_the_guard_writes_no_ledger_and_no_provenance(self):
        found = scenario()
        self.assertEqual(found["so_o_ficheiro_de_respostas"], ["respostas.jsonl"])
        self.assertFalse([n for n in found["cli"]["pasta"] if "custos" in n or "proveniencia" in n or n == "piloto"])

    def test_the_golden_file_was_made_before_the_wiring(self):
        text = GOLDEN.read_text(encoding="utf-8")
        for field in ("custos", "proveniencia", "teto", "piloto"):
            self.assertNotIn(field, text)


if __name__ == "__main__":
    unittest.main()
