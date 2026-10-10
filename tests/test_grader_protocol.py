"""A protocol that freezes the correction (`corretor_id`): what it writes, reads, warns and refuses.

Everything is written in temporary folders: no real protocol is made here, and the registered ones are
only read."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from pathlib import Path

from aferidor import grader_id
from aferidor.cli import main
from aferidor.condicoes import conditions_rows, graders_by_model, protocol_findings
from aferidor.grading import ConsistencySummary
from aferidor.models import Answer
from aferidor.protocolo import read_protocol, template, warnings

ROOT = Path(__file__).resolve().parent.parent
REAL_CASES = ROOT / "casos" / "casos.json"
FIXED = "0.1.0+corretor.3f9a1c7e2b64"
OTHER = "0.1.0+corretor.9d41c0a77e12"
WITHOUT_RECORD = "respondeu sem registo da versão do corretor"


def protocol_with(folder: str, **extra):
    data = {**template("x", REAL_CASES, today=date(2026, 9, 1)), **extra}
    path = Path(folder) / "protocolo.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return read_protocol(path)


class TestWritingAndReading(unittest.TestCase):
    def test_freezing_the_correction_writes_corretor_id_and_not_the_package_version(self):
        data = template("x", REAL_CASES, freeze_correction=True)
        self.assertEqual(data["corretor_id"], grader_id())
        self.assertNotIn("versao_corretor", data)

    def test_freezing_the_package_still_writes_versao_corretor_only(self):
        data = template("x", REAL_CASES, freeze_grader=True)
        self.assertIn("versao_corretor", data)
        self.assertNotIn("corretor_id", data)

    def test_an_unfrozen_protocol_has_neither(self):
        data = template("x", REAL_CASES)
        self.assertNotIn("corretor_id", data)
        self.assertNotIn("versao_corretor", data)

    def test_both_keys_are_read_and_a_protocol_without_the_new_one_reads_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(protocol_with(folder, corretor_id=FIXED).grader_id, FIXED)
            old = protocol_with(folder, versao_corretor="0.1.0+aaaaaaaaaaaa")
            self.assertEqual((old.grader_build, old.grader_id), ("0.1.0+aaaaaaaaaaaa", ""))

    def test_the_registered_protocols_are_still_read_with_no_corretor_id(self):
        paths = sorted((ROOT / "protocolos").glob("*.json"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(protocolo=path.name):
                self.assertEqual(read_protocol(path).grader_id, "")


class TestWarnings(unittest.TestCase):
    def found(self, protocol, graders, grading=None):
        return warnings(protocol, None, None, {}, {}, "pt", None, None, graders, grading)

    def test_answers_and_grading_with_the_fixed_version_raise_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol = protocol_with(folder, corretor_id=FIXED)
        self.assertEqual(self.found(protocol, {"m": (FIXED,)}, FIXED), [])

    def test_a_grader_changed_after_the_protocol_is_named(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol = protocol_with(folder, corretor_id=FIXED)
        found = self.found(protocol, {"m": (FIXED,)}, OTHER)
        self.assertEqual(len(found), 1)
        self.assertIn("o corretor mudou depois do protocolo", found[0])

    def test_answers_with_another_version_are_named_with_the_existing_sentence(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol = protocol_with(folder, corretor_id=FIXED)
        found = self.found(protocol, {"m": (OTHER,)}, FIXED)
        self.assertEqual(found, [f"m respondeu com a versão {OTHER}; o protocolo fixou o corretor na versão {FIXED}"])

    def test_answers_recorded_before_the_field_existed_get_one_warning_per_model_and_no_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol = protocol_with(folder, corretor_id=FIXED)
        found = self.found(protocol, {"a": ("",), "b": ("",), "c": (FIXED,)}, FIXED)
        self.assertEqual(
            found,
            [f"a {WITHOUT_RECORD}; o protocolo fixou o corretor na versão {FIXED}",
             f"b {WITHOUT_RECORD}; o protocolo fixou o corretor na versão {FIXED}"],
        )
        self.assertFalse(any("mudou" in w for w in found))

    def test_old_and_new_answers_of_one_model_give_the_no_record_warning_only_when_the_new_ones_match(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol = protocol_with(folder, corretor_id=FIXED)
        self.assertEqual(len(self.found(protocol, {"m": ("", FIXED)}, FIXED)), 1)
        both = self.found(protocol, {"m": ("", OTHER)}, FIXED)
        self.assertEqual(len(both), 2)
        self.assertIn(WITHOUT_RECORD, both[0])
        self.assertIn(f"respondeu com a versão {OTHER}", both[1])

    def test_a_protocol_without_corretor_id_ignores_the_grader_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol = protocol_with(folder)
        self.assertEqual(self.found(protocol, {"m": ("", OTHER)}, OTHER), [])

    def test_the_old_key_is_judged_as_before_whatever_the_new_arguments_say(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol = protocol_with(folder, versao_corretor="0.1.0+aaaaaaaaaaaa")
        found = warnings(protocol, None, None, {}, {}, "pt", {"m": ("0.1.0+aaaaaaaaaaaa",)}, "0.1.0+aaaaaaaaaaaa",
                         {"m": ("",)}, OTHER)
        self.assertEqual(found, [])


class TestApprovalIsNotTouched(unittest.TestCase):
    def test_the_warning_for_answers_without_a_record_never_changes_who_is_approved(self):
        summaries = {"m": ConsistencySummary(model="m", cases=1, critical_cases=0, unstable_cases=0, sample_accuracy=1.0)}
        answers = [Answer(case_id="C1", model="m", text="x", asked_at=datetime(2026, 10, 11), sample=s)
                   for s in range(1, 6)]
        with tempfile.TemporaryDirectory() as folder:
            with_key = protocol_with(folder, corretor_id=FIXED)
            without_key = protocol_with(folder)
        warned, approved_with = protocol_findings(with_key, answers, summaries, None, ["C1"])
        unwarned, approved_without = protocol_findings(without_key, answers, summaries, None, ["C1"])
        self.assertTrue(any(WITHOUT_RECORD in w for w in warned))
        self.assertEqual([o.approved for o in approved_with], [o.approved for o in approved_without])
        self.assertEqual([o.approved for o in approved_with], [True])
        self.assertFalse(any(WITHOUT_RECORD in w for w in unwarned))


class TestConditionsSuffix(unittest.TestCase):
    def answers(self, *graders: str):
        return [
            Answer(case_id=f"C{i}", model="m", text="x", asked_at=datetime(2026, 10, 11, 10, 0),
                   sample=1, build="0.1.0+abcdef012345", grader=g)
            for i, g in enumerate(graders)
        ]

    def row(self, *graders: str) -> str:
        return conditions_rows(self.answers(*graders))[0][1]

    def test_the_suffix_only_appears_when_an_answer_has_the_field(self):
        self.assertNotIn("corretor", self.row("", ""))
        self.assertTrue(self.row("", FIXED).endswith(f"; corretor {FIXED}"))
        self.assertTrue(self.row(FIXED, FIXED).endswith(f"; corretor {FIXED}"))

    def test_with_old_and_new_answers_the_suffix_lists_only_the_known_versions(self):
        row = self.row("", FIXED, "")
        self.assertEqual(row.count(FIXED), 1)
        self.assertIn("3 respostas", row)

    def test_graders_are_collected_per_model_and_an_old_answer_counts_as_empty(self):
        found = graders_by_model(self.answers("", FIXED))
        self.assertEqual(found, {"m": ("", FIXED)})


def run(*argv: str):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as stop:
            code = stop.code
    return code, out.getvalue(), err.getvalue()


class TestCommandLine(unittest.TestCase):
    def test_congelar_correcao_writes_a_protocol_with_the_new_key_in_a_temporary_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.json"
            code, out, _ = run("protocolo", "--nome", "x", "--saida", str(path), "--congelar-correcao")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(data["corretor_id"], grader_id())
        self.assertNotIn("versao_corretor", data)
        self.assertIn(f"correção fixada na versão {grader_id()}", out)

    def test_the_two_freezing_options_cannot_be_used_together(self):
        with tempfile.TemporaryDirectory() as folder:
            code, _, err = run("protocolo", "--nome", "x", "--saida", str(Path(folder) / "p.json"),
                               "--congelar-corretor", "--congelar-correcao")
        self.assertEqual(code, 2)
        self.assertIn("not allowed with argument", err)

    def ensaio(self, folder: Path, protocol: dict, *extra: str):
        (folder / "p.json").write_text(json.dumps(protocol), encoding="utf-8")
        return run(
            "ensaio", "--fornecedor", "falso", "--casos", str(REAL_CASES),
            "--saida", str(folder / "r.jsonl"), "--vereditos", str(folder / "v.json"),
            "--relatorio", str(folder / "rel.md"), "--protocolo", str(folder / "p.json"), *extra,
        )

    def test_a_run_is_refused_before_asking_when_the_correction_changed_and_the_message_says_so(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            code, _, err = self.ensaio(f, {**template("x", REAL_CASES), "corretor_id": FIXED})
            self.assertEqual(code, 2)
            self.assertIn(
                f"o protocolo fixou o corretor na versão {FIXED}, mas esta é a {grader_id()} "
                "(mudou um dos seis ficheiros que decidem a correção ou a aprovação; ver docs/METODO.md)",
                err,
            )
            self.assertFalse((f / "r.jsonl").exists(), "nothing may be asked")

    def test_a_run_with_the_current_correction_is_not_stopped_by_it(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            protocol = {**template("x", REAL_CASES), "amostras_por_caso": 1, "temperatura": 0.0,
                        "corretor_id": grader_id()}
            _, _, err = self.ensaio(f, protocol, "--repeticoes", "1", "--temperatura", "0")
            self.assertNotIn("corrigir antes de gastar", err)
            self.assertTrue((f / "r.jsonl").exists())

    def test_the_old_key_keeps_its_old_message(self):
        with tempfile.TemporaryDirectory() as folder:
            code, _, err = self.ensaio(Path(folder), {**template("x", REAL_CASES), "versao_corretor": "0.0.0+aaaaaaaaaaaa"})
        self.assertEqual(code, 2)
        self.assertIn("fixou o corretor na versão 0.0.0+aaaaaaaaaaaa", err)
        self.assertNotIn("seis ficheiros", err)

    def test_the_help_of_the_two_options_says_what_each_fixes(self):
        out = run("protocolo", "--help")[1]
        flat = " ".join(out.split())
        self.assertIn("[--congelar-corretor | --congelar-correcao]", flat)
        self.assertIn("a versão do pacote inteiro (qualquer edição ao código a muda", flat)
        self.assertIn("a versão só dos ficheiros que decidem a correção", flat)
        self.assertNotIn("—", out)
        self.assertNotIn("–", out)


if __name__ == "__main__":
    unittest.main()
