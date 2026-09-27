"""The test plan: limits written before the run, and the report holding a model to them."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from pathlib import Path

from aferidor import html_report, report
from aferidor.cli import main
from aferidor.grading import ConsistencySummary, grade
from aferidor.models import Answer
from aferidor.protocolo import evaluate, read_protocol, template, warnings
from tests.test_report import a_case

REAL_CASES = Path(__file__).resolve().parent.parent / "casos" / "casos.json"


def write_protocol(folder: str, **limits) -> Path:
    data = template("ensaio de teste", REAL_CASES, today=date(2026, 9, 1))
    data["criterios_de_aprovacao"].update(limits)
    path = Path(folder) / "protocolo.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def a_summary(critical: int = 0, unstable: int = 0, accuracy: float = 1.0) -> ConsistencySummary:
    return ConsistencySummary(
        model="modelo-x", cases=27, critical_cases=critical, unstable_cases=unstable,
        sample_accuracy=accuracy,
    )


class TestReading(unittest.TestCase):
    def test_the_template_carries_the_date_and_the_case_file_hash(self):
        data = template("x", REAL_CASES, today=date(2026, 9, 1))
        self.assertEqual(data["escrito_em"], "2026-09-01")
        self.assertEqual(len(data["banco_sha256"]), 64)

    def test_the_template_starts_from_the_strictest_limit(self):
        self.assertEqual(template("x", REAL_CASES)["criterios_de_aprovacao"]["casos_com_falha_critica_max"], 0)

    def test_a_protocol_that_leaves_a_limit_out_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_protocol(folder)
            data = json.loads(path.read_text(encoding="utf-8"))
            del data["criterios_de_aprovacao"]["casos_instaveis_max"]
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError) as raised:
                read_protocol(path)
        self.assertIn("casos_instaveis_max", str(raised.exception))

    def test_a_rate_outside_zero_and_one_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                read_protocol(write_protocol(folder, taxa_de_amostras_corretas_min=95))


class TestEvaluate(unittest.TestCase):
    def protocol(self, **limits):
        with tempfile.TemporaryDirectory() as folder:
            return read_protocol(write_protocol(folder, **limits))

    def test_a_model_within_every_limit_is_approved(self):
        outcome = evaluate(self.protocol(taxa_de_amostras_corretas_min=0.9), a_summary(accuracy=0.95))
        self.assertTrue(outcome.approved)

    def test_one_critical_case_over_the_limit_fails_the_model(self):
        outcome = evaluate(self.protocol(), a_summary(critical=1))
        self.assertFalse(outcome.approved)
        self.assertEqual([c.met for c in outcome.checks], [False, True, True])


class TestWarnings(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as folder:
            self.protocol = read_protocol(write_protocol(folder))

    def test_a_protocol_dated_after_the_first_answer_is_not_a_prior_criterion(self):
        found = warnings(self.protocol, datetime(2026, 8, 30), None, {}, {})
        self.assertTrue(any("não conta como critério" in w for w in found))

    def test_a_protocol_dated_before_the_first_answer_raises_nothing(self):
        self.assertEqual(warnings(self.protocol, datetime(2026, 9, 2), None, {}, {}), [])

    def test_a_different_case_file_is_named(self):
        found = warnings(self.protocol, None, "0" * 64, {}, {})
        self.assertTrue(any("SHA-256 diferente" in w for w in found))

    def test_other_samples_or_temperature_are_named(self):
        found = warnings(self.protocol, None, None, {"m": 3}, {"m": (0.0,)})
        self.assertEqual(len(found), 2)


class TestReports(unittest.TestCase):
    def test_both_reports_state_the_verdict_and_the_warning(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol = read_protocol(write_protocol(folder))
        case = a_case()
        answers = [Answer("C1", "falso", "Amoxicilina 500 mg", datetime(2026, 8, 30))]
        verdicts = [grade(case, answers[0])]
        text = report.build([case], answers, verdicts, today=date(2026, 9, 14), protocol=protocol)
        page = html_report.build([case], answers, verdicts, today=date(2026, 9, 14), protocol=protocol)
        self.assertIn("## Critério de aprovação", text)
        self.assertIn("**reprovado**", text)
        self.assertIn("não conta como critério", text)
        self.assertIn("Fornecedor de teste: reprovado", page)
        self.assertIn("não conta como critério", page)


class TestCommand(unittest.TestCase):
    def test_a_protocol_is_never_rewritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.json"
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                first = main(["protocolo", "--nome", "x", "--casos", str(REAL_CASES), "--saida", str(path)])
                path.write_text("limites decididos", encoding="utf-8")
                second = main(["protocolo", "--nome", "x", "--casos", str(REAL_CASES), "--saida", str(path)])
            self.assertEqual((first, second), (0, 2))
            self.assertEqual(path.read_text(encoding="utf-8"), "limites decididos")


if __name__ == "__main__":
    unittest.main()
