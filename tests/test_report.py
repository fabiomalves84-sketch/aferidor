"""The report: what it must say, and what it must never quietly leave out."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from aferidor import report
from aferidor.grading import grade
from aferidor.models import Answer
from tests.helpers import a_case, a_two_regimen_case, an_answer


def build(cases, answers, **kwargs) -> str:
    verdicts = [grade({c.case_id: c for c in cases}[a.case_id], a) for a in answers]
    return report.build(cases, answers, verdicts, today=date(2026, 9, 14), **kwargs)


class TestConditions(unittest.TestCase):
    """The report says what was measured, with what, and when."""

    def answer(self, **kwargs) -> Answer:
        base = dict(case_id="C1", model="falso", text="1 g", asked_at=datetime(2026, 9, 16, 14, 40))
        base.update(kwargs)
        return Answer(**base)

    def test_it_says_when_the_answers_were_obtained_not_only_when_it_was_written(self):
        text = build(
            [a_case()],
            [
                self.answer(sample=1, asked_at=datetime(2026, 9, 16, 14, 40)),
                self.answer(sample=2, asked_at=datetime(2026, 9, 16, 15, 38)),
            ],
        )
        self.assertIn("Relatório escrito em 2026-09-14", text)
        self.assertIn("recolhidas 2026-09-16 14:40 a 15:38", text)

    def test_it_names_the_temperature_token_limit_and_version(self):
        text = build(
            [a_case()],
            [self.answer(temperature=1.0, max_tokens=8192, build="0.1.0+abcdef012345")],
        )
        self.assertIn("temperatura 1,0", text)
        self.assertIn("tokens_max 8192", text)
        self.assertIn("versão 0.1.0+abcdef012345", text)

    def test_a_file_mixing_conditions_shows_every_value(self):
        text = build(
            [a_case()],
            [
                self.answer(sample=1, temperature=0.0, max_tokens=4096),
                self.answer(sample=2, temperature=1.0),
            ],
        )
        self.assertIn("temperatura 0,0, 1,0", text)
        self.assertIn("tokens_max 4096, não registado", text)

    def test_it_names_the_case_file_and_its_hash(self):
        text = build([a_case()], [self.answer()], cases_source=("casos/casos.json", "ab" * 32))
        self.assertIn("casos/casos.json (SHA-256 abababababab)", text)

    def test_the_html_report_shows_the_same_conditions(self):
        from aferidor import html_report

        answers = [self.answer(temperature=1.0, max_tokens=8192)]
        rows = report.conditions_rows(answers, ("casos/casos.json", "ab" * 32))
        verdicts = [grade(a_case(), answers[0])]
        page = html_report.build(
            [a_case()], answers, verdicts, today=date(2026, 9, 14),
            cases_source=("casos/casos.json", "ab" * 32),
        )
        import re

        visible = re.sub(r"<[^>]+>", "", page)
        for label, value in rows:
            with self.subTest(label=label):
                self.assertIn(value, visible)


class TestAlternativeShown(unittest.TestCase):
    def test_a_failed_answer_says_which_regimen_it_was_judged_against(self):
        from aferidor import html_report

        case = a_two_regimen_case()
        answer = Answer(
            case_id="AMIG", model="falso", text="Penicilina G benzatínica 600.000 U IM em dose única.",
            asked_at=datetime(2026, 9, 14),
        )
        verdicts = [grade(case, answer)]
        text = report.build([case], [answer], verdicts, today=date(2026, 9, 14))
        page = html_report.build([case], [answer], verdicts, today=date(2026, 9, 14))
        self.assertIn("Corrigida contra a alternativa:** penicilina benzatínica em dose única", text)
        self.assertIn("corrigida contra: penicilina benzatínica em dose única", page)


class TestIntervals(unittest.TestCase):
    def test_the_headline_carries_its_interval(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        self.assertIn("1 de 1 casos com falha de risco crítico", text)
        self.assertIn("IC 95%", text)

    def test_zero_critical_cases_says_how_high_the_true_rate_could_be(self):
        cases = [a_case(f"C{i}") for i in range(27)]
        answers = [an_answer("1000 mg", case_id=c.case_id) for c in cases]
        text = build(cases, answers)
        self.assertIn("compatível com uma proporção real de casos com falha crítica até 12%", text)

    def test_the_html_headline_carries_the_interval_too(self):
        from aferidor import html_report

        answers = [an_answer("Amoxicilina 500 mg")]
        verdicts = [grade(a_case(), answers[0])]
        page = html_report.build([a_case()], answers, verdicts, today=date(2026, 9, 14))
        self.assertIn("IC 95%", page)


class TestHeader(unittest.TestCase):
    def test_it_states_it_is_not_a_medical_device(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertIn("não substitui julgamento clínico", text)

    def test_it_carries_the_date(self):
        self.assertIn("2026-09-14", build([a_case()], [an_answer("1 g")]))

    def test_unverified_sources_are_warned_about_by_default(self):
        self.assertIn("Nem todas as fontes destes casos foram confirmadas", build([a_case()], [an_answer("1 g")]))

    def test_the_warning_goes_away_only_when_told_so(self):
        text = build([a_case()], [an_answer("1 g")], sources_verified=True)
        self.assertNotIn("Nem todas as fontes destes casos foram confirmadas", text)


class TestCounts(unittest.TestCase):
    def test_critical_failures_are_stated_before_the_percentage(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertLess(text.index("risco crítico"), text.index("cumprem todos os critérios"))

    def test_a_clean_run_says_so_plainly(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertIn("Nenhum caso com falha de risco crítico", text)
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

    def test_a_known_reason_is_shown_next_to_the_case(self):
        text = build(
            [a_case("C1")], [an_answer("1 g", case_id="C1")],
            missing=["C2"], reasons={"C2": "resposta truncada no limite de tokens"},
        )
        self.assertIn("C2 (resposta truncada no limite de tokens)", text)

    def test_a_case_without_a_known_reason_is_named_alone(self):
        text = build(
            [a_case("C1")], [an_answer("1 g", case_id="C1")],
            missing=["C2"], reasons={"C3": "outra razao"},
        )
        self.assertIn("C2", text)
        self.assertNotIn("C2 (", text)


class TestMissingSamples(unittest.TestCase):
    def test_a_partial_case_is_named_with_how_many_samples_came_in(self):
        # qwen answers C1 three times and C2 five times, so five is what it
        # was expected to answer everywhere, and C1 is short by two.
        text = build(
            [a_case("C1"), a_case("C2")],
            [an_answer("1 g", case_id="C1", model="qwen", sample=s) for s in (1, 2, 3)]
            + [an_answer("1 g", case_id="C2", model="qwen", sample=s) for s in (1, 2, 3, 4, 5)],
        )
        self.assertIn("Amostras em falta", text)
        self.assertIn("C1 (qwen, 3 de 5 amostras)", text)

    def test_a_model_missing_a_case_entirely_is_named_too(self):
        text = build(
            [a_case("C1"), a_case("C2")],
            [an_answer("1 g", case_id="C1", model="llama")]
            + [an_answer("1 g", case_id="C2", model="qwen")],
        )
        self.assertIn("C2 (llama, 0 de 1 amostras)", text)

    def test_no_gaps_means_no_section(self):
        text = build([a_case("C1")], [an_answer("1 g", case_id="C1")])
        self.assertNotIn("Amostras em falta", text)


class TestOnlyTheBankCounts(unittest.TestCase):
    def test_answers_to_other_cases_are_left_out_of_conditions_and_language(self):
        answers = [an_answer("1 g", case_id="C1"), an_answer("infecção, você", case_id="OUTRO-1")]
        text = report.build([a_case("C1")], answers, [grade(a_case("C1"), answers[0])], today=date(2026, 9, 14))
        self.assertIn("1 respostas, recolhidas", text)
        self.assertIn("0 de 1 respostas com formas do português do Brasil", text)


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
        self.assertIn(
            "| Modelo | Casos com falha crítica em alguma amostra | Casos corretos | "
            "Casos parcialmente corretos | Amostras corretas |",
            text,
        )

    def test_two_models_are_compared_with_a_paired_test(self):
        cases = [a_case("C1")]
        answers = [
            an_answer("1 g", case_id="C1", model="um"),
            an_answer("500 mg", case_id="C1", model="dois"),
        ]
        verdicts = [grade(cases[0], a) for a in answers]
        text = report.build(cases, answers, verdicts, today=date(2026, 9, 14))
        self.assertIn("teste de McNemar exato, p = 1,000", text)

    def test_one_model_gets_no_comparison_table(self):
        self.assertNotIn("## Comparação", build([a_case()], [an_answer("1 g")]))


class TestComparisonSentence(unittest.TestCase):
    """The sentence under the table of models, built from a ranking made by hand."""

    def sentence(self, *rows, p_value=1.0):
        from aferidor.comparacao import Ranking, Row

        ranked = tuple(Row(model, critical, cases, 0.0, 1.0) for model, critical, cases in rows)
        return report._comparison_text(Ranking(ranked, True, 1, 4, p_value))

    def test_without_a_tie_it_says_who_had_fewer_and_whether_it_could_be_chance(self):
        text = self.sentence(("a", 8, 27), ("b", 11, 27), p_value=0.375)
        self.assertEqual(
            text,
            "`a` teve menos casos com falha crítica do que `b`. Nos casos em que só um dos dois teve falha "
            "crítica (1 contra 4), a diferença pode dever-se ao acaso (teste de McNemar exato, p = 0,375). "
            "O teste é emparelhado, porque os modelos responderam aos mesmos casos.",
        )

    def test_a_tie_with_the_same_numbers_says_only_that_they_share_the_proportion(self):
        text = self.sentence(("a", 8, 27), ("b", 8, 27), ("c", 16, 27))
        self.assertEqual(text, "`a` e `b` tiveram a mesma proporção de casos com falha crítica.")

    def test_a_tie_over_different_numbers_of_cases_says_the_same(self):
        text = self.sentence(("a", 4, 10), ("b", 8, 20), ("c", 9, 10))
        self.assertEqual(text, "`a` e `b` tiveram a mesma proporção de casos com falha crítica.")
        self.assertNotIn("McNemar", text)

    def test_with_three_tied_it_names_only_the_first_two(self):
        text = self.sentence(("a", 8, 27), ("b", 8, 27), ("c", 8, 27), ("d", 22, 27))
        self.assertEqual(text, "`a` e `b` tiveram a mesma proporção de casos com falha crítica.")
        self.assertNotIn("`c`", text)

    def test_without_the_cases_known_there_is_no_sentence(self):
        from aferidor.comparacao import Ranking, Row

        self.assertIsNone(report._comparison_text(Ranking((Row("a", 1, 2, 0.0, 1.0),), False, None, None, None)))

    def test_a_report_with_a_tie_at_the_top_does_not_say_one_had_fewer(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [an_answer("1000 mg", case_id=c.case_id, model=m) for c in cases for m in ("a", "b")]
        text = build(cases, answers)
        self.assertIn("`a` e `b` tiveram a mesma proporção de casos com falha crítica.", text)
        self.assertNotIn("teve menos casos com falha crítica", text)


class TestEmpty(unittest.TestCase):
    def test_no_verdicts_says_so_instead_of_reporting_zero_percent(self):
        text = report.build([a_case()], [], [], today=date(2026, 9, 14))
        self.assertIn("Não há veredictos", text)
        self.assertNotIn("0%", text)


if __name__ == "__main__":
    unittest.main()
