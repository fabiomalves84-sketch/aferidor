"""The Gemini 3.x models of the catalogue run at 1.0, and nothing else is accepted for them. The Google pages say to keep
the default (https://ai.google.dev/gemini-api/docs/gemini-3 and .../prompting-strategies, read whole on 2026-10-11)."""

from __future__ import annotations

import json
import socket
import unittest
from decimal import Decimal
from unittest import mock

import tests  # noqa: F401  (a importação fixa a raiz das chaves numa pasta vazia)
from aferidor import cli, execucao
from aferidor.catalogo import load_catalog
from aferidor.execucao import analyse
from aferidor.grading import grade_all
from aferidor.proveniencia import FILE_NAME, read_records
from aferidor.storage import read_answers
from tests import fixtures_fornecedores as fx
from tests.test_fornecedores import Net, WithTheCommandLine

GEMINI_3 = ("gemini-3.1-pro-preview", "gemini-3.8-flash")


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def google(model):
    return {**fx.GOOGLE_OK, "modelVersion": model}


class TestTheCatalogue(unittest.TestCase):
    def test_every_gemini_3_entry_is_fixed_at_1_0_by_recommendation_with_its_source_and_day(self):
        catalog = load_catalog()
        gemini = {k: m for k, m in catalog.models.items() if m.provider == "gemini"}
        self.assertEqual(sorted(gemini), sorted(GEMINI_3))  # no Gemini entry outside the 3 series exists, so none was left alone
        for key, found in gemini.items():
            with self.subTest(modelo=key):
                self.assertEqual((found.temperature, found.fixed_temperature), ("fixa_por_recomendacao", Decimal("1.0")))
                for word in ("https://ai.google.dev/gemini-api/docs/gemini-3", "https://ai.google.dev/gemini-api/docs/prompting-strategies",
                             "2026-10-11", "recomenda", "não por imposição"):
                    self.assertIn(word, found.note)
                self.assertNotIn("temperatura", found.to_confirm)  # now documented

    def test_the_anthropic_entries_keep_their_own_policy_and_the_rest_is_untouched(self):
        catalog = load_catalog()
        for key in ("claude-fable-5-1", "claude-opus-5-5"):
            self.assertEqual(catalog.model(key).temperature, "fixa_pelo_fornecedor")
        for key, found in catalog.models.items():
            if found.provider not in ("gemini", "anthropic"):
                self.assertEqual(found.temperature, "desconhecido", key)

    def test_a_recommended_fixed_temperature_has_to_say_which(self):
        from aferidor.catalogo import CatalogError, parse_catalog
        from tests.test_catalogo import catalog, model
        parametros = {**model()["parametros"], "temperatura": "fixa_por_recomendacao"}
        with self.assertRaisesRegex(CatalogError, "temperatura_fixa"):
            parse_catalog(json.dumps(catalog(modelos={"m": model(parametros=parametros)})))


class TestWhatIsSent(WithTheCommandLine):
    def go(self, net, kind, model, *extra, env=None):
        return self.main(net, "executar", "--fornecedor", kind, "--modelo", model, "--casos", str(self.cases()), "--saida", str(self.saida),
                         "--limite", "2", "--tokens-max", "8192", "--teto-eur", "100", *extra, env=env)

    def cases(self):
        from tests.test_fornecedores import CASES
        return CASES

    def test_google_gemini_3_gets_1_0_without_being_asked_for_it(self):
        for model in GEMINI_3:
            with self.subTest(modelo=model):
                net = Net((":generateContent", google(model)))
                self.saida = self.folder / model / "respostas.jsonl"
                code, _, err = self.go(net, "google", model)
                self.assertEqual(code, 0, err)
                self.assertEqual({r["body"]["generationConfig"]["temperature"] for r in net.requests}, {1.0})

    def test_the_old_compatible_endpoint_sends_1_0_for_them_too(self):
        net = Net(("/openai/chat/completions", {**fx.OPENAI_OK, "model": "gemini-3.8-flash"}))
        code, _, err = self.go(net, "gemini", "gemini-3.8-flash")
        self.assertEqual(code, 0, err)
        self.assertEqual({r["body"]["temperature"] for r in net.requests}, {1.0})

    def test_asking_for_1_0_in_so_many_words_is_the_same(self):
        net = Net((":generateContent", google("gemini-3.8-flash")))
        code, _, _ = self.go(net, "google", "gemini-3.8-flash", "--temperatura", "1.0")
        self.assertEqual(code, 0)
        self.assertEqual({r["body"]["generationConfig"]["temperature"] for r in net.requests}, {1.0})

    def test_the_answers_and_the_provenance_say_1_0_was_asked_and_applied(self):
        self.go(Net((":generateContent", google("gemini-3.8-flash"))), "google", "gemini-3.8-flash")
        self.assertEqual({a.temperature for a in read_answers(self.saida)}, {1.0})
        lines = read_records(self.saida.with_name(FILE_NAME))
        self.assertEqual({(r.requested_params["temperatura"], r.applied_params["temperatura"]) for r in lines}, {(1.0, 1.0)})

    def test_the_report_shows_1_0_per_model_and_not_0_0(self):
        self.go(Net((":generateContent", google("gemini-3.8-flash"))), "google", "gemini-3.8-flash")
        answers = read_answers(self.saida)
        from aferidor.storage import read_cases
        cases = [c for c in read_cases(self.cases()) if c.case_id in {a.case_id for a in answers}]
        files = execucao.load(self.saida)
        analysis = analyse(files, cases, answers, grade_all(cases, answers)[0])
        self.assertIn("temperatura pedida 1,0; temperatura aplicada 1,0 (não confirmada pelo fornecedor)", "\n".join(execucao.condition_lines(analysis.models[0])))
        from aferidor.condicoes import conditions_rows
        rows = conditions_rows(answers, None)
        self.assertIn("temperatura (grau de aleatoriedade) 1,0", rows[0][1])
        self.assertNotIn("0,0", rows[0][1])


class TestAnotherTemperatureIsRefusedNotIgnored(WithTheCommandLine):
    def go(self, net, kind, model, *extra):
        from tests.test_fornecedores import CASES
        return self.main(net, "executar", "--fornecedor", kind, "--modelo", model, "--casos", str(CASES), "--saida", str(self.saida),
                         "--limite", "2", "--tokens-max", "8192", "--teto-eur", "100", *extra)

    def test_any_other_value_for_a_gemini_3_model_stops_the_command_before_anything_is_asked_and_says_why(self):
        for kind, model in (("google", "gemini-3.8-flash"), ("google", "gemini-3.1-pro-preview"), ("gemini", "gemini-3.8-flash")):
            for value in ("0", "0.0", "0.5", "1.5"):
                with self.subTest(fornecedor=kind, modelo=model, temperatura=value):
                    net = Net()
                    code, out, err = self.go(net, kind, model, "--temperatura", value)
                    self.assertEqual((code, net.requests), (2, []))
                    self.assertIn(f"{model}: a Google recomenda manter a temperatura em 1.0", err)
                    self.assertIn(f"foi pedida {float(value)}", err)
                    self.assertIn("--temperatura 1.0 ou não pedir nenhuma", err)
                    self.assertFalse(self.saida.parent.exists())

    def test_the_command_for_the_ensaio_also_refuses(self):
        from tests.test_fornecedores import CASES
        net = Net()
        code, _, err = self.main(net, "ensaio", "--fornecedor", "google", "--modelo", "gemini-3.8-flash", "--casos", str(CASES),
                                 "--saida", str(self.saida), "--teto-eur", "100", "--temperatura", "0.0")
        self.assertEqual((code, net.requests), (2, []))
        self.assertIn("a Google recomenda", err)

    def test_the_dry_run_does_not_ask_for_a_temperature_and_does_not_refuse(self):
        code, out, _ = self.go(Net(), "google", "gemini-3.8-flash", "--a-seco", "--temperatura", "0.0")
        self.assertEqual(code, 0)

    def test_a_model_that_is_not_fixed_keeps_the_default_of_the_project_at_0_0(self):
        saida = self.folder / "livre" / "respostas.jsonl"
        from tests.test_fornecedores import CASES
        code, _, _ = self.main(Net(), "executar", "--fornecedor", "falso", "--casos", str(CASES), "--saida", str(saida), "--limite", "1")
        self.assertEqual(code, 0)
        self.assertEqual({a.temperature for a in read_answers(saida)}, {0.0})
        self.assertEqual(cli.parse_args(["executar"]).temperatura, None)  # None means: the model's own, else 0.0

    def test_anthropic_that_runs_at_1_0_whatever_is_sent_no_longer_needs_to_be_told(self):
        net = Net(("/v1/messages", {**fx.ANTHROPIC_OK, "model": "claude-opus-5-5"}))
        code, _, err = self.go(net, "anthropic", "claude-opus-5-5")
        self.assertEqual(code, 0, err)
        self.assertTrue(all("temperature" not in r["body"] for r in net.requests))  # still sent without one
        self.assertEqual({a.temperature for a in read_answers(self.saida)}, {1.0})
        code, _, err = self.go(Net(), "anthropic", "claude-opus-5-5", "--temperatura", "0.0")
        self.assertEqual(code, 2)
        self.assertIn("não aceita temperatura", err)
