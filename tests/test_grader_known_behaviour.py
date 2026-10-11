"""Two known defects of the grader, kept in view because the Method page tells the reader about them."""

from __future__ import annotations

import unittest

from aferidor.grading import grade
from aferidor.models import FailureType
from aferidor.storage import read_cases
from tests.helpers import an_answer
from tests.html_support import ROOT, _Example, panel_html

CASE_ID = "ATB-PAC-001"

# What the Method page quotes, and what the answers below are built from: one place, so the page and the
# examples cannot drift apart without a test saying so.
WRITTEN_ANOTHER_WAY = "a cada 8 horas"
WRITTEN_AS_THE_CRITERION_WANTS = "de 8 em 8 horas"
WHERE_THE_RIGHT_DOSE_HIDES = "ajuste renal"

FALSE_FAILURE = f"Amoxicilina 500 mg por via oral, durante 5 dias, {WRITTEN_ANOTHER_WAY}."
FALSE_PASS = (
    "Amoxicilina. Dose: 1 g por via oral, de 8 em 8 horas, durante 5 dias. "
    f"Em {WHERE_THE_RIGHT_DOSE_HIDES} (ClCr < 10 mL/min): 250 mg a 500 mg de 24 em 24 horas."
)


def the_case():
    """The real case, with the criteria it has in `casos/casos.json`: nothing is copied into this test."""
    return next(c for c in read_cases(ROOT / "casos" / "casos.json") if c.case_id == CASE_ID)


class TestKnownBehaviourOfTheGraderThatTheMethodPageDescribes(unittest.TestCase):
    def test_the_two_known_ways_the_grader_is_wrong_in_atb_pac_001(self):
        """Documents a KNOWN DEFECT of the grader, not a wanted behaviour. The Método page, in the block
        «Como se verifica e se afina o corretor», tells the reader that the grader errs in two ways and
        uses these two answers as examples. If this test fails, the grader has changed: correct this
        test AND that paragraph of the page (with its four translations) in the SAME commit, whose
        message must say that the grader's behaviour changed and why. It must not be edited alone, and
        it must not stop the grader from being fixed: a fix is a good reason for it to fail."""
        case = the_case()
        wrong = grade(case, an_answer(FALSE_FAILURE, case_id=CASE_ID))
        self.assertIn(FailureType.DOSE_INCORRETA, wrong.failures, "o corretor já não falha «a cada 8 horas»: ver a docstring")
        right = grade(case, an_answer(f"Amoxicilina 500 mg por via oral, durante 5 dias, {WRITTEN_AS_THE_CRITERION_WANTS}.", case_id=CASE_ID))
        self.assertTrue(right.passed, "a resposta de controlo, escrita como o critério quer, deixou de passar")
        passed = grade(case, an_answer(FALSE_PASS, case_id=CASE_ID))
        self.assertTrue(passed.passed, "o corretor já não aprova a dose errada escondida no ajuste renal: ver a docstring")

    def test_the_method_page_gives_the_same_two_examples_in_the_closed_block(self):
        method = panel_html(_Example.page(), "metodo")
        block = method[method.index('id="verificacao-corretor"'):]
        block = block[:block.index("</details>")]
        for quoted in (WRITTEN_ANOTHER_WAY, WRITTEN_AS_THE_CRITERION_WANTS, WHERE_THE_RIGHT_DOSE_HIDES):
            with self.subTest(citado=quoted):
                self.assertIn(quoted, block)
        self.assertIn("num caso de dose, isso conta como falha crítica", block)
        self.assertIn("Ainda não se mediu com que frequência", block)

    def test_the_paragraph_is_in_every_language(self):
        from aferidor.traducao_catalogo import CATALOG

        pt = next(k for k in CATALOG if k.startswith("O corretor procura palavras e erra nos dois sentidos."))
        for lang in ("en", "es", "fr", "de"):
            with self.subTest(lingua=lang):
                self.assertNotEqual(CATALOG[pt][lang], pt)
                self.assertIn(WRITTEN_ANOTHER_WAY, CATALOG[pt][lang])


if __name__ == "__main__":
    unittest.main()
