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

    def test_tokens_max_defaults_high_enough_for_a_reasoning_model(self):
        self.assertEqual(parse_args(["executar"]).tokens_max, 4096)
        self.assertEqual(parse_args(["ensaio"]).tokens_max, 4096)

    def test_tokens_max_can_be_overridden(self):
        self.assertEqual(parse_args(["executar", "--tokens-max", "8192"]).tokens_max, 8192)


class TestBuildProvider(unittest.TestCase):
    def test_the_fake_provider_needs_no_key(self):
        self.assertIsInstance(build_provider("falso", None), FakeProvider)

    def test_the_model_name_travels_into_the_fake(self):
        self.assertEqual(build_provider("falso", "ensaio").name, "falso:ensaio")

    def test_an_unknown_provider_is_refused(self):
        with self.assertRaises(ValueError):
            build_provider("inventado", None)

    def test_tokens_max_travels_into_a_real_provider(self):
        self.assertEqual(build_provider("local", "llama3", max_tokens=8192).max_tokens, 8192)

    def test_without_tokens_max_the_providers_own_default_holds(self):
        self.assertEqual(build_provider("local", "llama3").max_tokens, 1024)

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


def _write_wide_case(path: Path) -> None:
    """A case whose reference passes but whose criterion cannot fail."""
    path.write_text(json.dumps([{
        "id": "LARGO", "categoria": "dose", "pergunta": "Que dose?",
        "referencia": "Amoxicilina 1000 mg",
        "fonte": {"nome": "Guia", "referencia": "p. 1"},
        "criterios": [{
            "tipo": "valor_numerico", "termos": ["1000", "mg", "5000"],
            "falha": "dose_incorreta",
        }],
    }], ensure_ascii=False), encoding="utf-8")


class TestVerificarControlos(unittest.TestCase):
    def test_the_shipped_cases_catch_every_negative_control(self):
        code, out, _ = run("verificar", "--casos", str(REAL_CASES))
        self.assertEqual(code, 0)
        self.assertIn("controlos negativos apanhados", out)

    def test_a_criterion_that_cannot_fail_exits_with_failure_and_names_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "casos.json"
            _write_wide_case(path)
            code, out, err = run("verificar", "--casos", str(path))
            self.assertEqual(code, 1)
            self.assertIn("1/1 casos coerentes", out)
            self.assertIn("0/1 controlos negativos apanhados", out)
            self.assertIn("LARGO", err)

    def test_ensaio_refuses_to_run_a_case_whose_criterion_cannot_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            _write_wide_case(f / "casos.json")
            code, _, err = run(
                "ensaio", "--fornecedor", "falso", "--casos", str(f / "casos.json"),
                "--saida", str(f / "r.jsonl"), "--vereditos", str(f / "v.json"),
                "--relatorio", str(f / "r.md"),
            )
            self.assertEqual(code, 2)
            self.assertIn("LARGO", err)
            self.assertFalse((f / "r.jsonl").exists(), "nada pode ser perguntado")


class TestExecutarConditions(unittest.TestCase):
    def test_resuming_at_another_temperature_exits_2_and_says_how_to_proceed(self):
        with tempfile.TemporaryDirectory() as folder:
            saida = str(Path(folder) / "respostas.jsonl")
            base = ("executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                    "--limite", "1", "--saida", saida)
            self.assertEqual(run(*base, "--temperatura", "1.0")[0], 0)
            code, _, err = run(*base, "--temperatura", "0")
            self.assertEqual(code, 2)
            self.assertIn("--recomecar", err)
            code, _, _ = run(*base, "--temperatura", "0", "--recomecar")
            self.assertEqual(code, 0)


class TestRelatorioCasesSource(unittest.TestCase):
    def test_the_report_names_the_bank_version_and_hash(self):
        bank = REAL_CASES.parent / "consulta.json"
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            run("executar", "--fornecedor", "falso", "--casos", str(bank), "--limite", "1",
                "--saida", str(f / "r.jsonl"))
            run("relatorio", "--casos", str(bank), "--limite", "1",
                "--respostas", str(f / "r.jsonl"), "--saida", str(f / "r.md"))
            text = (f / "r.md").read_text(encoding="utf-8")
        version = json.loads(bank.read_text(encoding="utf-8"))["versao"]
        self.assertIn(f"consulta.json, versão {version} (SHA-256 ", text)


class TestClassificar(unittest.TestCase):
    def test_classifying_without_answers_refuses_instead_of_reporting_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            code, _, err = run(
                "classificar", "--casos", str(REAL_CASES),
                "--respostas", str(Path(folder) / "nao-existe.jsonl"),
                "--saida", str(Path(folder) / "v.json"),
            )
            self.assertEqual(code, 2)
            self.assertIn("não há respostas", err)

    def test_a_file_with_the_same_sample_twice_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            run(
                "executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "1", "--saida", str(f / "respostas.jsonl"),
            )
            line = (f / "respostas.jsonl").read_text(encoding="utf-8")
            (f / "respostas.jsonl").write_text(line + line, encoding="utf-8")
            for comando, saida in (("classificar", "v.json"), ("relatorio", "r.md")):
                with self.subTest(comando=comando):
                    code, _, err = run(
                        comando, "--casos", str(REAL_CASES), "--limite", "1",
                        "--respostas", str(f / "respostas.jsonl"), "--saida", str(f / saida),
                    )
                    self.assertEqual(code, 2)
                    self.assertIn("amostras repetidas", err)

    def test_with_a_limit_matching_the_run_nothing_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            run(
                "executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "3", "--saida", str(f / "respostas.jsonl"),
            )
            _, _, err = run(
                "classificar", "--casos", str(REAL_CASES), "--limite", "3",
                "--respostas", str(f / "respostas.jsonl"), "--saida", str(f / "v.json"),
            )
            self.assertNotIn("sem resposta válida", err)

    def test_without_the_matching_limit_the_rest_shows_up_as_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            run(
                "executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "3", "--saida", str(f / "respostas.jsonl"),
            )
            _, _, err = run(
                "classificar", "--casos", str(REAL_CASES),
                "--respostas", str(f / "respostas.jsonl"), "--saida", str(f / "v.json"),
            )
            self.assertIn("sem resposta válida", err)


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
            self.assertIn("Condições do ensaio", (f / "relatorio.md").read_text(encoding="utf-8"))
            for nome in ("respostas.jsonl", "vereditos.json", "relatorio.md"):
                with self.subTest(ficheiro=nome):
                    self.assertTrue((f / nome).exists())
            self.assertIn("relatório em", out)

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

    def test_unanswered_cases_make_the_exit_code_non_zero(self):
        """The first case exhausts every retry and is never answered; the
        second succeeds. The run as a whole must not report success."""
        from unittest import mock

        from aferidor.cli import comando_ensaio, parse_args
        from aferidor.providers import FakeProvider

        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            args = parse_args([
                "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "2", "--tentativas", "1",
                "--saida", str(f / "respostas.jsonl"),
                "--vereditos", str(f / "vereditos.json"),
                "--relatorio", str(f / "relatorio.md"),
            ])
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with mock.patch(
                    "aferidor.cli.build_provider", return_value=FakeProvider(failures=1)
                ):
                    code = comando_ensaio(args)
            self.assertEqual(code, 1)

    def test_the_limit_does_not_name_cases_that_were_never_asked(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            _, _, err = run(
                "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "3",
                "--saida", str(f / "respostas.jsonl"),
                "--vereditos", str(f / "vereditos.json"),
                "--relatorio", str(f / "relatorio.md"),
            )
            self.assertNotIn("sem resposta válida", err)
            texto = (f / "relatorio.md").read_text(encoding="utf-8")
            self.assertNotIn("Casos sem resposta", texto)


class TestRelatorioHtml(unittest.TestCase):
    def test_the_default_format_stays_markdown(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            run(
                "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "2", "--saida", str(f / "respostas.jsonl"),
                "--vereditos", str(f / "vereditos.json"), "--relatorio", str(f / "relatorio.md"),
            )
            code, out, _ = run(
                "relatorio", "--casos", str(REAL_CASES),
                "--respostas", str(f / "respostas.jsonl"), "--saida", str(f / "saida"),
            )
            self.assertEqual(code, 0)
            self.assertTrue((f / "saida").exists())
            self.assertIn("Relatório do Aferidor", (f / "saida").read_text(encoding="utf-8"))

    def test_formato_html_writes_a_default_html_file(self):
        import os

        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            respostas = f / "respostas.jsonl"
            run(
                "executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "2", "--saida", str(respostas),
            )
            before = os.getcwd()
            os.chdir(folder)
            try:
                code, out, _ = run(
                    "relatorio", "--casos", str(REAL_CASES), "--respostas", str(respostas),
                    "--formato", "html",
                )
            finally:
                os.chdir(before)
            self.assertEqual(code, 0)
            self.assertTrue((f / "relatorios" / "relatorio.html").exists())

    def test_formato_html_with_an_explicit_output_path(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            respostas = f / "respostas.jsonl"
            run(
                "executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--limite", "2", "--saida", str(respostas),
            )
            code, _, _ = run(
                "relatorio", "--casos", str(REAL_CASES), "--respostas", str(respostas),
                "--formato", "html", "--saida", str(f / "r.html"),
            )
            self.assertEqual(code, 0)
            text = (f / "r.html").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("<!DOCTYPE html>"))


class TestExecutar(unittest.TestCase):
    def test_a_second_run_does_not_ask_again(self):
        with tempfile.TemporaryDirectory() as folder:
            saida = Path(folder) / "respostas.jsonl"
            comum = ("executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                     "--limite", "3", "--saida", str(saida))
            run(*comum)
            _, out, _ = run(*comum)
            self.assertIn("já existentes", out)

    def test_recomecar_keeps_the_other_models_answers(self):
        from aferidor.storage import read_answers

        with tempfile.TemporaryDirectory() as folder:
            saida = Path(folder) / "respostas.jsonl"
            run("executar", "--fornecedor", "falso", "--modelo", "llama", "--casos",
                str(REAL_CASES), "--limite", "3", "--saida", str(saida))
            run("executar", "--fornecedor", "falso", "--modelo", "qwen", "--casos",
                str(REAL_CASES), "--limite", "3", "--saida", str(saida))
            run("executar", "--fornecedor", "falso", "--modelo", "qwen", "--casos",
                str(REAL_CASES), "--limite", "3", "--saida", str(saida), "--recomecar")

            answers = read_answers(saida)
            by_model: dict[str, int] = {}
            for answer in answers:
                by_model[answer.model] = by_model.get(answer.model, 0) + 1
            self.assertEqual(by_model, {"falso:llama": 3, "falso:qwen": 3})

    def test_recomecar_says_how_many_old_answers_it_discarded(self):
        with tempfile.TemporaryDirectory() as folder:
            saida = Path(folder) / "respostas.jsonl"
            run("executar", "--fornecedor", "falso", "--modelo", "qwen", "--casos",
                str(REAL_CASES), "--limite", "3", "--saida", str(saida))
            _, out, _ = run("executar", "--fornecedor", "falso", "--modelo", "qwen", "--casos",
                             str(REAL_CASES), "--limite", "3", "--saida", str(saida), "--recomecar")
            self.assertIn("descartadas 3 respostas anteriores de falso:qwen", out)

    def test_recomecar_on_an_empty_file_says_nothing_was_discarded(self):
        with tempfile.TemporaryDirectory() as folder:
            saida = Path(folder) / "respostas.jsonl"
            _, out, _ = run("executar", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                             "--limite", "3", "--saida", str(saida), "--recomecar")
            self.assertNotIn("descartadas", out)



class TestProtocolBeforeThePaidRun(unittest.TestCase):
    """A protocol problem must stop the run before the first question is paid for."""

    def test_a_missing_protocol_stops_before_asking_anything(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            code, _, err = run(
                "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES),
                "--saida", str(f / "r.jsonl"), "--vereditos", str(f / "v.json"),
                "--relatorio", str(f / "rel.md"), "--protocolo", str(f / "nao-existe.json"),
            )
            self.assertEqual(code, 2)
            self.assertFalse((f / "r.jsonl").exists(), "nothing may be asked")

    def test_a_protocol_with_limite_is_refused(self):
        from aferidor.protocolo import template

        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            (f / "p.json").write_text(json.dumps(template("x", REAL_CASES)), encoding="utf-8")
            code, _, err = run(
                "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES), "--limite", "2",
                "--saida", str(f / "r.jsonl"), "--vereditos", str(f / "v.json"),
                "--relatorio", str(f / "rel.md"), "--protocolo", str(f / "p.json"),
            )
            self.assertEqual(code, 2)
            self.assertIn("não é compatível com --limite", err)
            self.assertFalse((f / "r.jsonl").exists())


    def _ensaio(self, f: Path, protocol: dict, *extra: str):
        (f / "p.json").write_text(json.dumps(protocol), encoding="utf-8")
        return run(
            "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES),
            "--saida", str(f / "r.jsonl"), "--vereditos", str(f / "v.json"),
            "--relatorio", str(f / "rel.md"), "--protocolo", str(f / "p.json"), *extra,
        )

    def test_a_run_that_does_not_match_the_protocol_stops_before_asking(self):
        """The report flags a different temperature, sample count, bank or grader
        build, but only after the run was paid for."""
        from aferidor.protocolo import template

        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            wrong_bank = template("x", REAL_CASES)
            wrong_bank["banco_sha256"] = "0" * 64
            for protocol, expected in (
                (template("x", REAL_CASES), "--repeticoes 1, mas o protocolo prevê 5"),
                (template("x", REAL_CASES), "--temperatura 0, mas o protocolo prevê 1"),
                (wrong_bank, "SHA-256 diferente"),
                ({**template("x", REAL_CASES), "versao_corretor": "0.0.0+aaaaaaaaaaaa"},
                 "fixou o corretor na versão 0.0.0+aaaaaaaaaaaa"),
            ):
                with self.subTest(expected=expected):
                    code, _, err = self._ensaio(f, protocol)
                    self.assertEqual(code, 2)
                    self.assertIn(expected, err)
                    self.assertFalse((f / "r.jsonl").exists(), "nothing may be asked")

    def test_a_run_that_matches_the_protocol_is_not_stopped_by_it(self):
        from aferidor import build_id
        from aferidor.protocolo import template

        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            protocol = {**template("x", REAL_CASES), "amostras_por_caso": 1,
                        "temperatura": 0.0, "versao_corretor": build_id()}
            _, _, err = self._ensaio(f, protocol, "--repeticoes", "1", "--temperatura", "0")
            self.assertNotIn("corrigir antes de gastar", err)
            self.assertTrue((f / "r.jsonl").exists())


class TestBrokenFiles(unittest.TestCase):
    """A missing or malformed file ends in a message and exit code 2, never a traceback."""

    def test_a_truncated_answers_file_is_named_not_crashed_on(self):
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "r.jsonl"
            broken.write_text('{"caso": "A"\n', encoding="utf-8")
            code, _, err = run("classificar", "--casos", str(REAL_CASES), "--respostas", str(broken),
                               "--saida", str(Path(folder) / "v.json"))
        self.assertEqual(code, 2)
        self.assertIn("ficheiro JSON inválido", err)

    def test_a_missing_case_file_is_named_not_crashed_on(self):
        code, _, err = run("verificar", "--casos", "/nao/existe/casos.json")
        self.assertEqual(code, 2)
        self.assertIn("erro:", err)

class TestEverySubcommandHasACommand(unittest.TestCase):
    """`main` looks the command up without a fallback: the parser requires a sub-command, so each
    one it accepts has to be in the table."""

    def test_the_parser_and_the_command_table_agree(self):
        import argparse

        from aferidor import cli

        (action,) = [a for a in cli.build_parser()._actions if isinstance(a, argparse._SubParsersAction)]
        self.assertEqual(set(action.choices), set(cli._COMMANDS))


if __name__ == "__main__":
    unittest.main()
