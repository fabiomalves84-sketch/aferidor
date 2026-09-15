"""The HTML report: same numbers as the Markdown one, escaped and self contained."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from aferidor import html_report, report
from aferidor.grading import consistency_by_case, consistency_by_model, grade_all
from aferidor.models import Answer, Case, Criterion, Source
from aferidor.risk import FailureType


def a_case(case_id: str = "C1", category: str = "dose") -> Case:
    return Case(
        case_id=case_id,
        category=category,
        question="Que dose de amoxicilina?",
        reference="Amoxicilina 1000 mg de 8/8h",
        source=Source(name="Guia ATB", reference="p. 17"),
        criteria=(
            Criterion(kind="contem", terms=("1000 mg", "1 g"), failure=FailureType.DOSE_INCORRETA),
        ),
    )


def an_answer(text: str, case_id: str = "C1", model: str = "falso", sample: int = 1) -> Answer:
    return Answer(
        case_id=case_id, model=model, text=text, asked_at=datetime(2026, 9, 14), sample=sample
    )


def build(cases, answers, **kwargs) -> str:
    verdicts, missing = grade_all(cases, answers)
    return html_report.build(
        cases, answers, verdicts, missing=kwargs.pop("missing", missing),
        today=date(2026, 9, 14), **kwargs
    )


class TestDocument(unittest.TestCase):
    def test_it_is_a_complete_self_contained_document(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertTrue(text.startswith("<!DOCTYPE html>"))
        self.assertIn("<title>Relatório do Aferidor</title>", text)
        self.assertIn("</html>", text)

    def test_it_loads_nothing_from_the_network(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertNotIn("http://", text)
        self.assertNotIn("https://", text)
        self.assertNotIn("<link ", text)
        self.assertNotIn("<script", text)

    def test_it_works_in_dark_mode(self):
        self.assertIn("prefers-color-scheme: dark", build([a_case()], [an_answer("1 g")]))

    def test_it_carries_the_date(self):
        self.assertIn("2026-09-14", build([a_case()], [an_answer("1 g")]))


class TestEscaping(unittest.TestCase):
    def test_a_scripted_answer_is_escaped_not_executed(self):
        text = build(
            [a_case()], [an_answer("<script>alert(1)</script>", sample=1)]
        )
        self.assertNotIn("<script>alert", text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", text)


class TestHeadline(unittest.TestCase):
    def test_the_critical_case_count_is_shown_per_model(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn('<span class="destaque">1</span>', text)
        self.assertIn("de 1 casos com falha crítica em alguma amostra", text)


class TestGrid(unittest.TestCase):
    def test_cases_are_grouped_by_category(self):
        cases = [a_case("C1", category="dose"), a_case("C2", category="interacao")]
        text = build(cases, [an_answer("1 g", case_id="C1"), an_answer("1 g", case_id="C2")])
        self.assertIn("dose", text)
        self.assertIn("interacao", text)

    def test_the_state_is_written_out_not_just_shown_in_colour(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("estável errado", text)

    def test_a_stable_pass_says_so(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertIn("estável certo", text)

    def test_a_mixed_result_across_samples_is_unstable(self):
        text = build(
            [a_case()],
            [an_answer("1 g", sample=1), an_answer("500 mg", sample=2)],
        )
        self.assertIn("instável", text)

    def test_a_case_never_asked_to_a_model_says_so(self):
        cases = [a_case("C1"), a_case("C2")]
        text = build(cases, [an_answer("1 g", case_id="C1")], missing=["C2"])
        self.assertIn("sem resposta", text)


class TestDetail(unittest.TestCase):
    def test_a_failed_case_gets_a_details_block(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("<details>", text)
        self.assertIn("Que dose de amoxicilina?", text)
        self.assertIn("Amoxicilina 1000 mg de 8/8h", text)
        self.assertIn("Guia ATB", text)

    def test_a_passing_case_gets_no_details_block(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertNotIn("<details>", text)

    def test_each_distinct_answer_appears_once(self):
        text = build(
            [a_case()],
            [
                an_answer("500 mg", sample=1),
                an_answer("500 mg", sample=2),
                an_answer("600 mg", sample=3),
            ],
        )
        self.assertEqual(text.count("500 mg"), 1)
        self.assertIn("600 mg", text)


class TestNumbersMatchMarkdown(unittest.TestCase):
    def test_the_same_verdicts_give_the_same_counts_in_both_formats(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("1 g", case_id="C1", sample=1),
            an_answer("500 mg", case_id="C1", sample=2),
            an_answer("500 mg", case_id="C2", sample=1),
        ]
        verdicts, missing = grade_all(cases, answers)
        markdown = report.build(cases, answers, verdicts, missing=missing, today=date(2026, 9, 14))
        page = html_report.build(cases, answers, verdicts, missing=missing, today=date(2026, 9, 14))

        consistency = consistency_by_case(cases, answers, verdicts)
        summary = consistency_by_model(consistency)["falso"]

        self.assertIn(f"{summary.critical_cases} de {summary.cases} casos", markdown)
        self.assertIn(f'<span class="destaque">{summary.critical_cases}</span>', page)
        self.assertIn(f"de {summary.cases} casos com falha crítica em alguma amostra", page)


class TestEmpty(unittest.TestCase):
    def test_no_verdicts_says_so_instead_of_reporting_zero_percent(self):
        text = html_report.build([a_case()], [], [], today=date(2026, 9, 14))
        body = text.split("<body>", 1)[1]
        self.assertIn("Não há vereditos", body)
        self.assertNotIn("0%", body)


if __name__ == "__main__":
    unittest.main()
