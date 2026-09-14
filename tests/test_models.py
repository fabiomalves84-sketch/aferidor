import unittest
from datetime import date, datetime

from aferidor.models import Answer, Case, Criterion, CriterionResult, Source, Verdict
from aferidor.risk import FailureType, Risk


def a_source() -> Source:
    return Source("Infarmed", "RCM Amoxicilina, secção 4.2", consulted=date(2026, 9, 14))


def a_case(*criteria: Criterion) -> Case:
    return Case(
        case_id="C-001",
        category="dose",
        question="Qual a dose habitual de amoxicilina oral no adulto?",
        reference="500 mg de 8 em 8 horas",
        source=a_source(),
        criteria=criteria or (Criterion("contem", ("500 mg",), FailureType.DOSE_INCORRETA),),
    )


class TestSource(unittest.TestCase):
    def test_a_source_needs_a_reference(self):
        with self.assertRaises(ValueError):
            Source("Infarmed", "   ")

    def test_a_source_needs_a_name(self):
        with self.assertRaises(ValueError):
            Source("", "RCM, secção 4.2")


class TestCriterion(unittest.TestCase):
    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            Criterion("parece_bem", ("x",), FailureType.ALUCINACAO)

    def test_a_criterion_needs_terms(self):
        with self.assertRaises(ValueError):
            Criterion("contem", (), FailureType.ALUCINACAO)


class TestCase(unittest.TestCase):
    def test_a_case_without_criteria_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            Case("C-002", "dose", "P", "R", a_source(), ())
        self.assertIn("measures nothing", str(caught.exception))

    def test_a_case_needs_a_reference_answer(self):
        with self.assertRaises(ValueError):
            Case("C-003", "dose", "P", "", a_source(),
                 (Criterion("contem", ("x",), FailureType.ALUCINACAO),))

    def test_worst_risk_is_the_heaviest_criterion(self):
        case = a_case(
            Criterion("contem", ("500 mg",), FailureType.FORMATO_INVALIDO),
            Criterion("contem", ("8/8h",), FailureType.DOSE_INCORRETA),
        )
        self.assertEqual(case.worst_risk, Risk.CRITICO)


class TestAnswer(unittest.TestCase):
    def test_latency_cannot_be_negative(self):
        with self.assertRaises(ValueError):
            Answer("C-001", "modelo-x", "texto", datetime(2026, 9, 14, 10, 0), latency_ms=-1)


class TestVerdict(unittest.TestCase):
    def test_an_answer_that_meets_every_criterion_passes(self):
        case = a_case()
        verdict = Verdict("C-001", "modelo-x", (CriterionResult(case.criteria[0], True),))
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.failures, ())
        self.assertIsNone(verdict.worst_risk)

    def test_failures_come_worst_first_and_without_repeats(self):
        light = Criterion("contem", ("mg",), FailureType.FORMATO_INVALIDO)
        heavy = Criterion("contem", ("500",), FailureType.DOSE_INCORRETA)
        also_light = Criterion("contem", ("dose",), FailureType.FORMATO_INVALIDO)
        verdict = Verdict(
            "C-001",
            "modelo-x",
            (
                CriterionResult(light, False),
                CriterionResult(heavy, False),
                CriterionResult(also_light, False),
            ),
        )
        self.assertEqual(
            verdict.failures,
            (FailureType.DOSE_INCORRETA, FailureType.FORMATO_INVALIDO),
        )
        self.assertEqual(verdict.worst_risk, Risk.CRITICO)


if __name__ == "__main__":
    unittest.main()
