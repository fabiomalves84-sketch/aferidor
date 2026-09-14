"""The report: what it must say, and what it must never quietly leave out."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from aferidor import report
from aferidor.grading import grade
from aferidor.models import Answer, Case, Criterion, Source
from aferidor.risk import FailureType


def a_case(case_id: str = "C1") -> Case:
    return Case(
        case_id=case_id,
        category="dose",
        question="Que dose de amoxicilina?",
        reference="Amoxicilina 1000 mg de 8/8h",
        source=Source(name="Guia ATB", reference="p. 17"),
        criteria=(
            Criterion(kind="contem", terms=("1000 mg", "1 g"), failure=FailureType.DOSE_INCORRETA),
        ),
    )


def an_answer(text: str, case_id: str = "C1", model: str = "falso") -> Answer:
    return Answer(case_id=case_id, model=model, text=text, asked_at=datetime(2026, 9, 14))


def build(cases, answers, **kwargs) -> str:
    verdicts = [grade({c.case_id: c for c in cases}[a.case_id], a) for a in answers]
    return report.build(cases, answers, verdicts, today=date(2026, 9, 14), **kwargs)


class TestHeader(unittest.TestCase):
    def test_it_states_it_is_not_a_medical_device(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertIn("não substitui julgamento clínico", text)

    def test_it_carries_the_date(self):
        self.assertIn("2026-09-14", build([a_case()], [an_answer("1 g")]))

    def test_unverified_sources_are_warned_about_by_default(self):
        self.assertIn("ainda não foram confirmadas", build([a_case()], [an_answer("1 g")]))

    def test_the_warning_goes_away_only_when_told_so(self):
        text = build([a_case()], [an_answer("1 g")], sources_verified=True)
        self.assertNotIn("ainda não foram confirmadas", text)


class TestCounts(unittest.TestCase):
    def test_critical_failures_are_stated_before_the_percentage(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertLess(text.index("risco crítico"), text.index("passaram em todos"))

    def test_a_clean_run_says_so_plainly(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertIn("Nenhuma falha de risco crítico", text)
        self.assertIn("1 de 1", text)

    def test_the_failure_table_names_the_type_and_its_risk(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("`dose_incorreta`", text)
        self.assertIn("critico", text)


class TestDetail(unittest.TestCase):
    def test_a_failed_case_shows_question_reference_and_source(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("Que dose de amoxicilina?", text)
        self.assertIn("Amoxicilina 1000 mg de 8/8h", text)
        self.assertIn("Guia ATB", text)

    def test_it_quotes_what_the_model_actually_said(self):
        text = build([a_case()], [an_answer("dar 500 mg de amoxicilina")])
        self.assertIn("> dar 500 mg de amoxicilina", text)

    def test_it_shows_the_evidence_behind_each_failed_criterion(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("1000 mg", text)

    def test_a_passing_run_lists_no_failures(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertIn("Todas as respostas passaram", text)


class TestMissing(unittest.TestCase):
    def test_cases_never_answered_are_named(self):
        text = build([a_case("C1")], [an_answer("1 g", case_id="C1")], missing=["C2"])
        self.assertIn("C2", text)
        self.assertIn("Não entram em nenhuma contagem", text)


class TestComparison(unittest.TestCase):
    def test_two_models_get_a_comparison_table(self):
        cases = [a_case("C1")]
        answers = [
            an_answer("1 g", case_id="C1", model="um"),
            an_answer("500 mg", case_id="C1", model="dois"),
        ]
        verdicts = [grade(cases[0], a) for a in answers]
        text = report.build(cases, answers, verdicts, today=date(2026, 9, 14))
        self.assertIn("## Comparação", text)
        self.assertIn("Falhas críticas", text)

    def test_one_model_gets_no_comparison_table(self):
        self.assertNotIn("## Comparação", build([a_case()], [an_answer("1 g")]))


class TestEmpty(unittest.TestCase):
    def test_no_verdicts_says_so_instead_of_reporting_zero_percent(self):
        text = report.build([a_case()], [], [], today=date(2026, 9, 14))
        self.assertIn("Não há vereditos", text)
        self.assertNotIn("0%", text)


if __name__ == "__main__":
    unittest.main()
