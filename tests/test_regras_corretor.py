"""The rules U1 to U6 of `docs/METODO.md` ("Regras do corretor em correção"), written before the corrector obeys them.

Each test describes a rule with answers built from what the stored runs showed (the examples of the sweeps of
11 October). U1, U2, U3 and U5 are followed by the grader, and their tests are plain tests (U5 since ATB-FAR-014
was anchored). U4 still carries `expectedFailure`: it needs the stem declared in the case, a change to the terms of
a criterion and not an anchor. Removing the decorator must make that test fail, and on the first assertion, which is
the one that states the rule. U6 is a rule about how the criteria
change, not about any answer, so it has no test.
"""

from __future__ import annotations

import unittest

from aferidor.grading import grade
from aferidor.storage import read_cases
from tests.helpers import an_answer
from tests.html_support import ROOT


def case(case_id: str):
    for name in ("casos.json", "consulta.json"):
        for found in read_cases(ROOT / "casos" / name):
            if found.case_id == case_id:
                return found
    raise KeyError(case_id)


def verdict(case_id: str, text: str):
    return grade(case(case_id), an_answer(text, case_id=case_id))


class TestRulesOfTheCorrector(unittest.TestCase):
    def test_u1_an_interval_written_another_way_is_the_same_interval(self):
        for written in ("a cada 8 horas", "8-8h", "3x/dia", "3 vezes por dia"):
            with self.subTest(escrito=written):
                self.assertTrue(
                    verdict("ATB-PAC-001", f"Amoxicilina 500 mg por via oral, durante 5 dias, {written}.").passed
                )
        self.assertFalse(verdict("ATB-PAC-001", "Amoxicilina 500 mg por via oral, durante 5 dias, 2x/dia.").passed)

    def test_u1_a_dose_in_grams_is_the_same_dose_and_a_different_dose_is_not(self):
        self.assertTrue(verdict("ATB-PAC-001", "Amoxicilina 0,5 g por via oral, de 8 em 8 horas, durante 5 dias.").passed)
        self.assertFalse(verdict("ATB-PAC-001", "Amoxicilina 1 g por via oral, de 8 em 8 horas, durante 5 dias.").passed)

    def test_u2_a_dose_counts_only_if_it_belongs_to_the_drug_of_the_criterion(self):
        wrong = "Amoxicilina 1 g por via oral, de 8 em 8 horas, durante 5 dias. Para a febre, paracetamol 500 mg."
        self.assertFalse(verdict("ATB-PAC-001", wrong).passed)
        right = "Amoxicilina 500 mg por via oral, de 8 em 8 horas, durante 5 dias. Para a febre, paracetamol 1 g."
        self.assertTrue(verdict("ATB-PAC-001", right).passed)

    def test_u3_a_value_inside_a_renal_adjustment_is_not_the_dose_of_the_case(self):
        hidden = (
            "Amoxicilina. Dose: 1 g por via oral, de 8 em 8 horas, durante 5 dias. "
            "Em ajuste renal (ClCr < 10 mL/min): 500 mg de 24 em 24 horas."
        )
        self.assertFalse(verdict("ATB-PAC-001", hidden).passed)
        kept = (
            "Amoxicilina 500 mg por via oral, de 8 em 8 horas, durante 5 dias. "
            "Em ajuste renal (ClCr < 10 mL/min): 250 mg de 24 em 24 horas."
        )
        self.assertTrue(verdict("ATB-PAC-001", kept).passed)

    @unittest.expectedFailure
    def test_u4_a_variant_of_the_stem_the_case_declares_is_the_same_word(self):
        text = "Penicilina G benzatina 1 200 000 UI por via intramuscular, em dose única."
        self.assertTrue(verdict("ATB-FAR-013", text).passed)
        other = "Penicilina G procaína 1 200 000 UI por via intramuscular, em dose única."
        self.assertFalse(verdict("ATB-FAR-013", other).passed)

    def test_u5_a_drug_the_answer_excludes_does_not_anchor_a_dose(self):
        excluded = "Não usar cefuroxima 250 mg de 12 em 12 horas durante 10 dias; dar amoxicilina."
        self.assertFalse(verdict("ATB-FAR-014", excluded).passed)
        given = "Cefuroxima 250 mg por via oral, de 12 em 12 horas, durante 10 dias."
        self.assertTrue(verdict("ATB-FAR-014", given).passed)


if __name__ == "__main__":
    unittest.main()
