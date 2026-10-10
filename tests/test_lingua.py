"""European Portuguese as an indicator, kept out of the clinical counts."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from aferidor import html_report, report
from aferidor.grading import grade
from aferidor.lingua import BRAZILIAN, PRE_AGREEMENT, language_by_model, markers_in
from aferidor.models import Answer
from tests.helpers import a_case


def labels(text: str) -> list[str]:
    return [label for _, label in markers_in(text)]


class TestMarkers(unittest.TestCase):
    def test_brazilian_forms_are_found(self):
        for text in ("Doença crônica.", "Está tomando amoxicilina.", "Você deve", "A equipe",
                     "Entre em contato", "O câncer", "A diarréia"):
            with self.subTest(text=text):
                self.assertTrue(any(g == BRAZILIAN for g, _ in markers_in(text)))

    def test_decomposed_accents_are_found_like_composed_ones(self):
        """Text in NFD (a letter plus a combining accent) escaped the markers,
        while the grader, which normalises, would have read it fine."""
        import unicodedata

        for text in ("Doença crônica.", "Você deve", "O câncer"):
            decomposed = unicodedata.normalize("NFD", text)
            self.assertNotEqual(decomposed, text)
            with self.subTest(text=text):
                self.assertEqual(markers_in(decomposed), markers_in(text))
                self.assertTrue(markers_in(decomposed))

    def test_european_forms_are_not(self):
        for text in ("Doença crónica.", "Está a tomar amoxicilina.", "A equipa", "Entre em contacto",
                     "O cancro", "A diarreia", "A infeção", "Dor de estômago.", "O cônjuge"):
            with self.subTest(text=text):
                self.assertEqual(markers_in(text), [])

    def test_the_dgs_own_word_is_not_counted(self):
        """The DGS writes "antibioticoterapia" (Norma 020/2012); it cannot count as wrong."""
        self.assertEqual(markers_in("A antibioticoterapia de primeira linha"), [])

    def test_pre_agreement_spelling_is_counted_apart(self):
        self.assertEqual([g for g, _ in markers_in("Uma infecção urinária")], [PRE_AGREEMENT])


class TestSummary(unittest.TestCase):
    def test_answers_are_counted_once_per_group(self):
        answers = [
            Answer("C1", "m", "Você está tomando para a infecção crônica.", datetime(2026, 9, 27)),
            Answer("C2", "m", "Amoxicilina 1000 mg.", datetime(2026, 9, 27)),
        ]
        summary = language_by_model(answers)["m"]
        self.assertEqual((summary.answers, summary.brazilian, summary.pre_agreement), (2, 1, 1))


class TestReports(unittest.TestCase):
    def test_both_reports_show_the_indicator_without_touching_the_failure_counts(self):
        case = a_case()
        answers = [Answer("C1", "falso", "Amoxicilina 1000 mg para a infecção.", datetime(2026, 9, 14))]
        verdicts = [grade(case, answers[0])]
        text = report.build([case], answers, verdicts, today=date(2026, 9, 14))
        page = html_report.build([case], answers, verdicts, today=date(2026, 9, 14))
        self.assertTrue(verdicts[0].passed)
        self.assertIn("### Português europeu", text)
        self.assertIn("1 com grafia anterior ao Acordo", text)
        self.assertIn("Português europeu", page)


if __name__ == "__main__":
    unittest.main()
