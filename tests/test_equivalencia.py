"""Rule U1 as a function: when two written doses, or two written intervals, are the same one."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

from aferidor.equivalencia import (
    Dose,
    find_doses,
    find_intervals,
    parse_dose,
    parse_interval,
    same_dose,
    same_interval,
)
from aferidor.storage import read_cases
from tests.html_support import ROOT

EIGHT_HOURS = (
    "8/8", "8/8h", "8-8h", "8 – 8 h", "8 em 8", "de 8 em 8 horas", "de oito em oito horas", "a cada 8 horas",
    "cada 8 h", "q8h", "3x/dia", "3 x dia", "3 vezes por dia", "três vezes por dia", "tres vezes ao dia", "tid",
)
TWELVE_HOURS = ("12/12", "12 em 12 horas", "doze em doze horas", "a cada 12 horas", "2x/dia", "duas vezes por dia", "bid")


class TestIntervals(unittest.TestCase):
    def test_every_way_of_writing_eight_hours_is_eight_hours(self):
        for written in EIGHT_HOURS:
            with self.subTest(escrito=written):
                self.assertEqual(parse_interval(written), 8.0)
        for a in EIGHT_HOURS:
            self.assertTrue(same_interval("8 em 8 horas", a), a)

    def test_the_others_are_what_they_say(self):
        for written in TWELVE_HOURS:
            with self.subTest(escrito=written):
                self.assertEqual(parse_interval(written), 12.0)
        for written, hours in (("24/24", 24.0), ("1x/dia", 24.0), ("uma vez por dia", 24.0), ("qd", 24.0),
                               ("4x/dia", 6.0), ("qid", 6.0), ("6/6h", 6.0), ("uma vez por semana", 168.0), ("semanal", 168.0)):
            with self.subTest(escrito=written):
                self.assertEqual(parse_interval(written), hours)

    def test_a_different_interval_is_not_the_same_in_either_direction(self):
        for other in TWELVE_HOURS + ("6/6", "24/24", "2x/dia"):
            with self.subTest(outro=other):
                self.assertFalse(same_interval("8/8", other))
                self.assertFalse(same_interval(other, "8/8"))

    def test_a_duration_a_range_or_a_date_is_not_an_interval(self):
        for written in ("durante 8 horas", "5 dias", "8 horas", "8-12h", "a cada 6 a 8 horas", "3 vezes", "dose única", "1/2", ""):
            with self.subTest(escrito=written):
                self.assertIsNone(parse_interval(written))
                self.assertFalse(same_interval(written, written))

    def test_it_finds_the_intervals_in_a_sentence_with_their_place(self):
        text = "Amoxicilina 500 mg, de 8 em 8 horas, durante 5 dias. Se ClCr < 30: a cada 12 horas."
        found = find_intervals(text)
        self.assertEqual([i.hours for i in found], [8.0, 12.0])
        self.assertEqual([i.written for i in found], ["de 8 em 8 horas", "a cada 12 horas"])
        for item in found:
            self.assertEqual(text[item.start:item.end], item.written)

    def test_accents_and_case_do_not_matter_and_positions_stay_those_of_the_text(self):
        text = "TRÊS VEZES POR DIA, depois Às 12/12h"
        found = find_intervals(text)
        self.assertEqual([i.hours for i in found], [8.0, 12.0])
        self.assertEqual(text[found[0].start:found[0].end], "TRÊS VEZES POR DIA")

    def test_a_number_inside_a_longer_one_or_a_word_is_not_an_interval(self):
        for text in ("a data 18/8/2026", "mantida", "intidade", "1128/128", "duodenal"):
            with self.subTest(texto=text):
                self.assertEqual(find_intervals(text), [])


class TestDoses(unittest.TestCase):
    def test_grams_and_milligrams_are_the_same_mass_and_a_different_amount_is_not(self):
        self.assertTrue(same_dose("500 mg", "0,5 g"))
        self.assertTrue(same_dose("1 g", "1000 mg"))
        self.assertTrue(same_dose("1 g", "1.000 mg"))
        self.assertTrue(same_dose("1000 mg", "1 000 mg"))
        self.assertTrue(same_dose("500mg", "500 mg"))
        self.assertTrue(same_dose("0,5 mg", "500 mcg"))
        self.assertFalse(same_dose("500 mg", "1 g"))
        self.assertFalse(same_dose("500 mg", "50 mg"))
        self.assertFalse(same_dose("2,5 mg", "25 mg"))
        self.assertFalse(same_dose("2,5 mg", "5 mg"))

    def test_a_dose_per_kilo_per_day_or_per_volume_is_never_the_plain_dose(self):
        for other in ("500 mg/kg", "500 mg/dia", "500 mg/5 ml", "500 mg/ml", "500 mg/kg/dia"):
            with self.subTest(outro=other):
                self.assertFalse(same_dose("500 mg", other))
        self.assertTrue(same_dose("50 mg/kg/dia", "50 mg/kg/d"))
        self.assertFalse(same_dose("250 mg/5 ml", "250 mg/ml"))
        self.assertFalse(same_dose("50 mg/kg", "50 mg/kg/dia"))

    def test_units_of_activity_are_not_mass(self):
        self.assertTrue(same_dose("1 200 000 UI", "1.200.000 ui"))
        self.assertFalse(same_dose("1200 mg", "1 200 000 UI"))

    def test_it_reads_a_number_the_way_a_portuguese_text_writes_it(self):
        self.assertEqual(parse_dose("1 000 mg"), Dose(1000.0, "mg"))
        self.assertEqual(parse_dose("1.000 mg"), Dose(1000.0, "mg"))
        self.assertEqual(parse_dose("2,5 mg"), Dose(2.5, "mg"))
        self.assertEqual(parse_dose("1,500 g"), Dose(1500.0, "mg"))
        self.assertIsNone(parse_dose("500"))
        self.assertIsNone(parse_dose("500 mg de amoxicilina"))

    def test_it_finds_the_doses_in_a_sentence_with_their_place_and_skips_ranges(self):
        text = "Amoxicilina 1 g, de 8 em 8 horas. Paracetamol 500 mg. Alternativa: 5 a 10 mg/kg."
        found = find_doses(text)
        self.assertEqual([d.dose for d in found], [Dose(1000.0, "mg"), Dose(500.0, "mg")])
        for item in found:
            self.assertEqual(text[item.start:item.end], item.written)

    def test_a_digit_inside_a_longer_number_is_not_a_dose(self):
        self.assertEqual([d.dose.amount for d in find_doses("25 mg")], [25.0])
        self.assertEqual([d.dose.amount for d in find_doses("2,5 mg")], [2.5])
        self.assertEqual([d.dose.amount for d in find_doses("a dose de 2,5 mg e de 25 mg")], [2.5, 25.0])
        self.assertEqual(find_doses("500mgs de gente"), [])


class TestAgainstTheBank(unittest.TestCase):
    """The function agrees with what the bank already accepts: written from the cases, not from any answer."""

    def criteria(self):
        for name in ("casos.json", "consulta.json"):
            for case in read_cases(ROOT / "casos" / name):
                for criterion in case.all_criteria:
                    yield case.case_id, criterion

    def test_every_other_form_a_criterion_accepts_is_one_of_the_intervals_it_writes_out(self):
        """A criterion may accept two intervals (erythromycin, 6/6 or 8/8), but each form it lists
        ("tres vezes por dia", "cada 8 h") must be the hours of one of its explicit "n/n" or "n em n" terms."""
        checked = 0
        for case_id, criterion in self.criteria():
            if criterion.kind != "contem":
                continue
            explicit = {
                parse_interval(term) for term in criterion.terms if re.fullmatch(r"\d+\s*(?:/|em)\s*\d+", term)
            }
            others = {parse_interval(term) for term in criterion.terms if not re.fullmatch(r"\d+\s*(?:/|em)\s*\d+", term)} - {None}
            if explicit:
                checked += 1
                with self.subTest(caso=case_id, termos=criterion.terms[:3]):
                    self.assertLessEqual(others, explicit)
        self.assertGreaterEqual(checked, 15)

    def test_the_forms_of_one_dose_in_the_bank_are_the_same_dose(self):
        checked = 0
        for case_id, criterion in self.criteria():
            if criterion.kind != "contem":
                continue
            for a, b in (("1000 mg", "1 g"), ("3000 mg", "3 g")):
                if a in criterion.terms and b in criterion.terms:
                    checked += 1
                    with self.subTest(caso=case_id, a=a, b=b):
                        self.assertTrue(same_dose(a, b))
        self.assertGreaterEqual(checked, 3)


class TestItIsIsolated(unittest.TestCase):
    def test_the_module_imports_nothing_of_the_package_so_the_grader_can_use_it_later_without_a_cycle(self):
        tree = ast.parse((Path(__file__).resolve().parent.parent / "aferidor" / "equivalencia.py").read_text(encoding="utf-8"))
        imported = {
            (node.module or "") if isinstance(node, ast.ImportFrom) else alias.name
            for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (node.names if isinstance(node, ast.Import) else [None])
        }
        for name in imported:
            self.assertFalse(name.startswith("aferidor") or name.startswith("."), name)


if __name__ == "__main__":
    unittest.main()
