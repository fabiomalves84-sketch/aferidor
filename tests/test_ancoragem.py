"""Rules U1 to U3 as the grader follows them: a dose or an interval counts only if it belongs to the anchor drug
and is not inside an adjustment, and it counts whatever the way it is written."""

from __future__ import annotations

import unittest
from dataclasses import replace

from aferidor.checks import check
from aferidor.grading import anchors_missing, negative_controls
from aferidor.models import Case, Criterion, Source
from aferidor.risk import FailureType
from aferidor.storage import case_from_dict, case_to_dict, read_cases
from tests.html_support import ROOT


def dose(terms=("500 mg",), anchors=("amoxicilina",), kind="contem", adjustment=False):
    return Criterion(kind=kind, terms=tuple(terms), failure=FailureType.DOSE_INCORRETA, ancora=tuple(anchors), em_ajuste=adjustment)


def passes(criterion: Criterion, text: str) -> bool:
    return check(criterion, text).passed


class TestTheCriterionWithAnAnchor(unittest.TestCase):
    def test_only_a_contem_or_a_valor_numerico_can_be_anchored(self):
        with self.assertRaisesRegex(ValueError, "contem ou valor_numerico"):
            Criterion(kind="nao_contem", terms=("500 mg",), failure=FailureType.DOSE_INCORRETA, ancora=("amoxicilina",))

    def test_every_term_must_be_a_dose_or_an_interval_the_function_can_read(self):
        with self.assertRaisesRegex(ValueError, "dose diaria unica"):
            dose(terms=("24/24", "dose diaria unica"))
        dose(terms=("12/12", "duas vezes por dia", "bid"))

    def test_the_case_is_about_an_adjustment_only_with_an_anchor(self):
        with self.assertRaisesRegex(ValueError, "em_ajuste"):
            Criterion(kind="contem", terms=("500 mg",), failure=FailureType.DOSE_INCORRETA, em_ajuste=True)

    def test_the_anchor_and_the_adjustment_survive_the_case_file(self):
        criterion = dose(terms=("2,5", "mg"), anchors=("apixabano",), kind="valor_numerico", adjustment=True)
        case = Case(case_id="X", category="ajuste", question="q", reference="Apixabano 2,5 mg.", source=Source(name="s", reference="r"), criteria=(criterion,))
        again = case_from_dict(case_to_dict(case), "teste")
        self.assertEqual(again.criteria[0].ancora, ("apixabano",))
        self.assertTrue(again.criteria[0].em_ajuste)


class TestWhoseDoseItIs(unittest.TestCase):
    def test_a_dose_beside_the_anchor_counts_and_the_dose_of_another_drug_does_not(self):
        c = dose()
        self.assertTrue(passes(c, "Amoxicilina 500 mg de 8 em 8 horas."))
        self.assertFalse(passes(c, "Amoxicilina 1 g de 8 em 8 horas. Paracetamol 500 mg se febre."))
        self.assertFalse(passes(c, "Paracetamol 500 mg. Amoxicilina 1 g."))

    def test_a_dose_before_its_drug_belongs_to_the_drug_named_after_it(self):
        self.assertTrue(passes(dose(), "Tomar 500 mg de amoxicilina."))
        self.assertFalse(passes(dose(), "Tomar 500 mg de paracetamol, e amoxicilina 1 g."))

    def test_a_line_with_no_drug_belongs_to_the_drug_named_above_it(self):
        c = dose()
        self.assertTrue(passes(c, "**Fármaco:** Amoxicilina\n**Dose:** 500 mg\n**Intervalo:** 8/8h"))
        self.assertFalse(passes(c, "**Fármaco:** Amoxicilina\n**Dose:** 1 g\n\nEm doentes com alergia, paracetamol:\n**Dose:** 500 mg"))

    def test_the_last_drug_named_above_is_the_owner_and_a_new_drug_takes_it_over(self):
        c = dose(anchors=("claritromicina",), terms=("500 mg",))
        self.assertTrue(passes(c, "Amoxicilina 1 g de 8 em 8 horas, associada a claritromicina\n500 mg de 12 em 12 horas"))
        self.assertFalse(passes(c, "Claritromicina 250 mg\nAmoxicilina:\n500 mg"))

    def test_a_dose_is_the_same_whatever_the_unit_it_is_written_in(self):
        self.assertTrue(passes(dose(), "Amoxicilina 0,5 g, de 8 em 8 horas."))
        self.assertTrue(passes(dose(terms=("1000 mg",)), "Amoxicilina 1 g."))
        self.assertFalse(passes(dose(terms=("500 mg",)), "Amoxicilina 500 mg/kg."))

    def test_any_of_several_anchors_will_do(self):
        c = dose(terms=("100 mg", "3000 mg"), anchors=("nitrofurantoína", "fosfomicina"))
        self.assertTrue(passes(c, "Fosfomicina 3 g em toma única."))
        self.assertTrue(passes(c, "Nitrofurantoína 100 mg."))
        self.assertFalse(passes(c, "Cefuroxima 100 mg."))

    def test_an_interval_is_anchored_the_same_way(self):
        c = dose(terms=("12/12", "duas vezes por dia"), anchors=("claritromicina",))
        self.assertTrue(passes(c, "Amoxicilina de 8 em 8 horas, claritromicina de 12 em 12 horas."))
        self.assertTrue(passes(c, "Claritromicina 500 mg, 2x/dia."))
        self.assertFalse(passes(c, "Amoxicilina 500 mg de 12 em 12 horas, claritromicina 500 mg de 8 em 8 horas."))

    def test_a_valor_numerico_is_anchored_with_its_tolerance_and_its_unit(self):
        c = dose(terms=("85", "mg/kg/dia", "5"), anchors=("amoxicilina",), kind="valor_numerico")
        self.assertTrue(passes(c, "Amoxicilina 90 mg/kg/dia."))
        self.assertFalse(passes(c, "Amoxicilina 100 mg/kg/dia."))
        self.assertFalse(passes(c, "Amoxicilina 85 mg/kg."))
        self.assertFalse(passes(c, "Azitromicina 85 mg/kg/dia."))
        grams = dose(terms=("1", "g"), anchors=("amoxicilina",), kind="valor_numerico")
        self.assertTrue(passes(grams, "Amoxicilina 1000 mg."))


class TestTheValueInsideAnAdjustment(unittest.TestCase):
    def test_a_value_after_a_renal_marker_in_its_unit_is_not_the_dose_of_the_case(self):
        c = dose()
        self.assertTrue(passes(c, "Amoxicilina 500 mg de 8 em 8 horas. Com ClCr < 30: 250 mg."))
        self.assertFalse(passes(c, "Amoxicilina 1 g de 8 em 8 horas. Com ClCr < 30: 500 mg."))
        self.assertFalse(passes(c, "Amoxicilina 1 g. Na insuficiência renal grave, reduzir para 500 mg."))

    def test_the_condition_goes_on_to_the_lines_without_a_drug_and_ends_at_a_heading_or_a_blank_line(self):
        c = dose()
        self.assertFalse(passes(c, "Amoxicilina 1 g.\n**Ajuste renal:**\n* ClCr < 30\n* 500 mg"))
        self.assertTrue(passes(c, "Amoxicilina 1 g.\nAjuste renal: reduzir.\n\nAmoxicilina 500 mg."))
        self.assertTrue(passes(c, "Amoxicilina.\n### Ajuste renal\nreduzir\n### Posologia\n500 mg"))

    def test_the_word_adjusted_alone_is_no_condition(self):
        self.assertTrue(passes(dose(), "Amoxicilina 500 mg, ajustado à resposta."))

    def test_a_case_about_an_adjustment_counts_the_value_inside_it(self):
        c = dose(terms=("1000 mg",), anchors=("metformina",), adjustment=True)
        self.assertTrue(passes(c, "Com TFG entre 30 e 44 ml/min, ajuste de dose: metformina 1000 mg por dia."))
        self.assertFalse(passes(replace(c, em_ajuste=False), "Com TFG entre 30 e 44 ml/min, ajuste de dose: metformina 1000 mg por dia."))


class TestADrugTheAnswerExcludes(unittest.TestCase):
    def test_an_anchor_named_in_order_to_exclude_it_owns_no_dose(self):
        c = dose(terms=("250 mg",), anchors=("cefuroxima",))
        self.assertTrue(passes(c, "Cefuroxima 250 mg de 12 em 12 horas."))
        self.assertFalse(passes(c, "Não usar cefuroxima 250 mg de 12 em 12 horas."))


class TestBeforeThereWasAnAnchor(unittest.TestCase):
    def test_a_criterion_without_an_anchor_still_matches_anywhere_and_now_in_every_form(self):
        plain = Criterion(kind="contem", terms=("500 mg", "500mg"), failure=FailureType.DOSE_INCORRETA)
        self.assertTrue(passes(plain, "Paracetamol 500 mg."))
        self.assertTrue(passes(plain, "Dose: 0,5 g."))
        self.assertFalse(passes(plain, "Dose: 1 g."))
        interval = Criterion(kind="contem", terms=("8/8", "8 em 8"), failure=FailureType.DOSE_INCORRETA)
        self.assertTrue(passes(interval, "a cada 8 horas"))
        self.assertFalse(passes(interval, "a cada 12 horas"))

    def test_a_term_that_is_not_a_dose_is_matched_as_before(self):
        word = Criterion(kind="contem", terms=("amoxicilina",), failure=FailureType.RESPOSTA_INCOMPLETA)
        self.assertTrue(passes(word, "Amoxicilina."))


class TestTheAnchorsOfTheBank(unittest.TestCase):
    def cases(self):
        return read_cases(ROOT / "casos" / "casos.json") + read_cases(ROOT / "casos" / "consulta.json")

    def test_every_anchor_is_written_in_the_reference_it_was_taken_from(self):
        self.assertEqual(anchors_missing(self.cases()), [])

    def test_a_criterion_anchored_to_a_drug_the_reference_does_not_name_is_reported(self):
        case = Case(
            case_id="X", category="dose", question="q", reference="Amoxicilina 500 mg.", source=Source(name="s", reference="r"),
            criteria=(dose(anchors=("paracetamol",)),),
        )
        found = anchors_missing([case])
        self.assertEqual([(c.case_id, name) for c, _, name in found], [("X", "paracetamol")])

    def test_the_alternative_is_read_against_its_own_reference(self):
        from aferidor.models import Alternative

        first = Alternative(description="a", reference="Amoxicilina 500 mg.", criteria=(dose(anchors=("amoxicilina",)),))
        second = Alternative(description="b", reference="Claritromicina 500 mg.", criteria=(dose(anchors=("claritromicina",)),))
        case = Case(
            case_id="X", category="dose", question="q", reference="Amoxicilina 500 mg; ou claritromicina 500 mg.",
            source=Source(name="s", reference="r"), criteria=(dose(anchors=("amoxicilina",)),), alternatives=(first, second),
        )
        self.assertEqual(anchors_missing([case]), [])
        wrong = replace(second, reference="Azitromicina 500 mg.")
        self.assertEqual(len(anchors_missing([replace(case, alternatives=(first, wrong))])), 1)

    def test_the_anchored_criteria_are_these_and_the_others_were_left_alone_for_a_reason_written_in_the_commit(self):
        anchored = {
            (case.case_id, criterion.terms[0])
            for case in self.cases() for criterion in case.all_criteria if criterion.ancora
        }
        self.assertEqual(len(anchored), 23)
        self.assertIn(("ATB-PAC-001", "500 mg"), anchored)
        self.assertNotIn(("ATB-FAR-014", "250 mg"), anchored)  # the four cases with another drug come in their own commits

    def test_the_reference_of_an_anchored_case_still_passes_and_the_controls_still_catch_a_wrong_dose(self):
        case = next(c for c in self.cases() if c.case_id == "ATB-PAC-001")
        controls = [c for c in negative_controls(case) if c.criterion.ancora]
        self.assertGreaterEqual(len(controls), 2)
        for control in controls:
            with self.subTest(controlo=control.change):
                self.assertFalse(check(control.criterion, control.text).passed)


if __name__ == "__main__":
    unittest.main()
