"""The command line, which was the largest module here and the only one untested.

It is also the only part anyone actually runs. The tests that matter are not the
happy paths: they are the exit codes and the refusals. A command that fails and
returns success is worse than one that crashes, because a run that produced
nothing looks, from the outside, exactly like a run that produced everything.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from aferidor.cli import build_provider, main, parse_args
from aferidor.providers import FakeProvider, ProviderError

REAL_CASES = Path(__file__).resolve().parent.parent / "casos" / "casos.json"


def run(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TestArguments(unittest.TestCase):
    def test_a_command_is_required(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parse_args([])

    def test_the_default_provider_costs_nothing(self):
        self.assertEqual(parse_args(["executar"]).fornecedor, "falso")

    def test_every_command_parses(self):
        for comando in ("executar", "classificar", "relatorio", "verificar", "ensaio"):
            with self.subTest(comando=comando):
                self.assertEqual(parse_args([comando]).comando, comando)

    def test_listing_models_needs_a_real_provider(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parse_args(["modelos"])


class TestBuildProvider(unittest.TestCase):
    def test_the_fake_provider_needs_no_key(self):
        self.assertIsInstance(build_provider("falso", None), FakeProvider)

    def test_the_model_name_travels_into_the_fake(self):
        self.assertEqual(build_provider("falso", "ensaio").name, "falso:ensaio")

    def test_an_unknown_provider_is_refused(self):
        with self.assertRaises(ValueError):
            build_provider("inventado", None)

    def test_a_real_provider_without_a_key_raises_rather_than_asking(self):
        import os

        guardado = {k: os.environ.pop(k, None) for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")}
        try:
            for nome in ("openai", "anthropic"):
                with self.subTest(fornecedor=nome):
                    with self.assertRaises(ProviderError):
                        build_provider(nome, None)
        finally:
            for k, v in guardado.items():
                if v is not None:
                    os.environ[k] = v


class TestVerificar(unittest.TestCase):
    def test_the_shipped_cases_are_coherent(self):
        code, out, _ = run("verificar", "--casos", str(REAL_CASES))
        self.assertEqual(code, 0)
        self.assertIn("casos coerentes", out)

    def test_a_broken_case_exits_with_failure_and_names_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "casos.json"
            path.write_text(json.dumps([{
                "id": "MAU", "categoria": "dose", "pergunta": "Que dose?",
                "referencia": "Amoxicilina 500 mg",
                "fonte": {"nome": "Guia", "referencia": "p. 1"},
                "criterios": [{"tipo": "contem", "termos": ["1000 mg"], "falha": "dose_incorreta"}],
            }], ensure_ascii=False), encoding="utf-8")
            code, _, err = run("verificar", "--casos", str(path))
            self.assertEqual(code, 1)
            self.assertIn("MAU", err)


class TestClassificar(unittest.TestCase):
    def test_classifying_without_answers_refuses_instead_of_reporting_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            code, _, err = run(
                "classificar", "--casos", str(REAL_CASES),
                "--respostas", str(Path(folder) / "nao-existe.jsonl"),
                "--saida", str(Path(folder) / "v.json"),
            )
            self.assertEqual(code, 2)
            self.assertIn("nao ha respostas", err)


class TestEnsaio(unittest.TestCase):
    def test_the_whole_chain_runs_and_leaves_the_three_files(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            code, out, _ = run(
                "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--saida", str(f / "respostas.jsonl"),
                "--vereditos", str(f / "vereditos.json"),
                "--relatorio", str(f / "relatorio.md"),
            )
            self.assertEqual(code, 0)
            for nome in ("respostas.jsonl", "vereditos.json", "relatorio.md"):
                with self.subTest(ficheiro=nome):
                    self.assertTrue((f / nome).exists())
            self.assertIn("relatorio em", out)

    def test_broken_cases_stop_the_run_before_anything_is_asked(self):
        """The point of the check: a bad case must not cost a paid run."""
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            casos = f / "casos.json"
            casos.write_text(json.dumps([{
                "id": "MAU", "categoria": "dose", "pergunta": "Que dose?",
                "referencia": "Amoxicilina 500 mg",
                "fonte": {"nome": "Guia", "referencia": "p. 1"},
                "criterios": [{"tipo": "contem", "termos": ["1000 mg"], "falha": "dose_incorreta"}],
            }], ensure_ascii=False), encoding="utf-8")
            code, _, err = run(
                "ensaio", "--fornecedor", "falso", "--casos", str(casos),
                "--saida", str(f / "respostas.jsonl"),
                "--vereditos", str(f / "vereditos.json"),
                "--relatorio", str(f / "relatorio.md"),
            )
            self.assertEqual(code, 2)
            self.assertIn("MAU", err)
            self.assertFalse((f / "respostas.jsonl").exists())

    def test_the_limit_asks_only_that_many_cases(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            run(
                "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "2",
                "--saida", str(f / "respostas.jsonl"),
                "--vereditos", str(f / "vereditos.json"),
                "--relatorio", str(f / "relatorio.md"),
            )
            linhas = (f / "respostas.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(linhas), 2)


class TestExecutar(unittest.TestCase):
    def test_a_second_run_does_not_ask_again(self):
        with tempfile.TemporaryDirectory() as folder:
            saida = Path(folder) / "respostas.jsonl"
            comum = ("executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                     "--limite", "3", "--saida", str(saida))
            run(*comum)
            _, out, _ = run(*comum)
            self.assertIn("ja existentes", out)


if __name__ == "__main__":
    unittest.main()
