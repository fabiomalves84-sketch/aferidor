"""Verdicts and counts: what the bench concludes, and what it refuses to hide."""

from __future__ import annotations

import unittest
from datetime import datetime

from aferidor.grading import grade, grade_all, self_check, tally, tally_by_model
from aferidor.models import Answer, Case, Criterion, Source
from aferidor.risk import FailureType, Risk


def a_case(case_id: str = "C1") -> Case:
    return Case(
        case_id=case_id,
        category="dose",
        question="Que dose?",
        reference="Amoxicilina 1000 mg 8/8h",
        source=Source(name="Guia", reference="p. 17"),
        criteria=(
            Criterion(kind="contem", terms=("amoxicilina",), failure=FailureType.RESPOSTA_INCOMPLETA),
            Criterion(kind="contem", terms=("1000 mg", "1 g"), failure=FailureType.DOSE_INCORRETA),
        ),
    )


def an_answer(text: str, case_id: str = "C1", model: str = "falso") -> Answer:
    return Answer(case_id=case_id, model=model, text=text, asked_at=datetime(2026, 9, 14))


class TestGrade(unittest.TestCase):
    def test_an_answer_meeting_every_criterion_passes(self):
        verdict = grade(a_case(), an_answer("Amoxicilina 1000 mg de 8/8h"))
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.failures, ())
        self.assertIsNone(verdict.worst_risk)

    def test_a_wrong_dose_is_classified_as_a_dose_failure(self):
        verdict = grade(a_case(), an_answer("Amoxicilina 500 mg"))
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failures, (FailureType.DOSE_INCORRETA,))
        self.assertEqual(verdict.worst_risk, Risk.CRITICO)

    def test_the_worst_failure_is_reported_first(self):
        verdict = grade(a_case(), an_answer("nao sei"))
        self.assertEqual(verdict.failures[0], FailureType.DOSE_INCORRETA)

    def test_every_criterion_leaves_a_result_with_evidence(self):
        verdict = grade(a_case(), an_answer("Amoxicilina 500 mg"))
        self.assertEqual(len(verdict.results), 2)
        self.assertTrue(all(r.evidence for r in verdict.results))

    def test_grading_an_answer_against_the_wrong_case_is_refused(self):
        with self.assertRaises(ValueError):
            grade(a_case("C1"), an_answer("qualquer", case_id="C2"))

    def test_the_model_travels_from_the_answer_to_the_verdict(self):
        verdict = grade(a_case(), an_answer("Amoxicilina 1 g", model="openai:gpt-4o"))
        self.assertEqual(verdict.model, "openai:gpt-4o")


class TestGradeAll(unittest.TestCase):
    def test_a_case_that_was_never_answered_is_reported_not_ignored(self):
        cases = [a_case("C1"), a_case("C2")]
        verdicts, missing = grade_all(cases, [an_answer("Amoxicilina 1 g", case_id="C1")])
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(missing, ["C2"])

    def test_an_answer_to_an_unknown_case_is_reported_too(self):
        verdicts, missing = grade_all([a_case("C1")], [an_answer("x", case_id="C9")])
        self.assertEqual(verdicts, [])
        self.assertIn("C9", missing)
        self.assertIn("C1", missing)


class TestTally(unittest.TestCase):
    def test_counts_split_by_failure_and_by_risk(self):
        verdicts = [
            grade(a_case("C1"), an_answer("Amoxicilina 1 g", case_id="C1")),
            grade(a_case("C2"), an_answer("Amoxicilina 500 mg", case_id="C2")),
            grade(a_case("C3"), an_answer("nao sei", case_id="C3")),
        ]
        counts = tally(verdicts)
        self.assertEqual(counts.total, 3)
        self.assertEqual(counts.passed, 1)
        self.assertEqual(counts.failed, 2)
        self.assertAlmostEqual(counts.accuracy, 1 / 3)
        self.assertEqual(counts.by_failure[FailureType.DOSE_INCORRETA], 2)
        self.assertEqual(counts.by_failure[FailureType.RESPOSTA_INCOMPLETA], 1)
        self.assertEqual(counts.critical, 2)

    def test_the_worst_risk_is_listed_first(self):
        verdicts = [grade(a_case("C1"), an_answer("nao sei", case_id="C1"))]
        first = tally(verdicts).worst_first()[0][0]
        self.assertEqual(first.risk, Risk.CRITICO)

    def test_failed_cases_are_named_with_their_failures(self):
        verdicts = [grade(a_case("C2"), an_answer("Amoxicilina 500 mg", case_id="C2"))]
        self.assertEqual(tally(verdicts).failed_cases["C2"], ("dose_incorreta",))

    def test_an_empty_tally_does_not_divide_by_zero(self):
        self.assertEqual(tally([]).accuracy, 0.0)

    def test_mixing_two_models_in_one_tally_is_refused(self):
        verdicts = [
            grade(a_case("C1"), an_answer("x", case_id="C1", model="um")),
            grade(a_case("C2"), an_answer("x", case_id="C2", model="dois")),
        ]
        with self.assertRaises(ValueError):
            tally(verdicts)

    def test_tally_by_model_keeps_each_model_apart(self):
        verdicts = [
            grade(a_case("C1"), an_answer("Amoxicilina 1 g", case_id="C1", model="um")),
            grade(a_case("C2"), an_answer("nao sei", case_id="C2", model="dois")),
        ]
        counts = tally_by_model(verdicts)
        self.assertEqual(sorted(counts), ["dois", "um"])
        self.assertEqual(counts["um"].passed, 1)
        self.assertEqual(counts["dois"].passed, 0)


class TestSelfCheck(unittest.TestCase):
    def test_a_case_whose_reference_meets_its_criteria_is_not_reported(self):
        self.assertEqual(self_check([a_case()]), [])

    def test_a_case_whose_own_reference_fails_is_reported(self):
        broken = Case(
            case_id="MAU",
            category="dose",
            question="Que dose?",
            reference="Amoxicilina 500 mg",
            source=Source(name="Guia", reference="p. 1"),
            criteria=(
                Criterion(
                    kind="contem", terms=("1000 mg",), failure=FailureType.DOSE_INCORRETA
                ),
            ),
        )
        found = self_check([broken])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0].case_id, "MAU")
        self.assertFalse(found[0][1].passed)

    def test_the_real_case_file_is_checked_by_this_test_suite(self):
        from pathlib import Path as _Path

        from aferidor.storage import read_cases

        path = _Path(__file__).resolve().parent.parent / "casos" / "casos.json"
        if not path.exists():
            self.skipTest("sem ficheiro de casos")
        broken = self_check(read_cases(path))
        names = [case.case_id for case, _ in broken]
        self.assertEqual(
            names, [], f"a referencia destes casos nao passa nos proprios criterios: {names}"
        )


if __name__ == "__main__":
    unittest.main()
