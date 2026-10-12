"""Two defects of the grader that were corrected on 12 October 2026, kept in view because the Method page tells the reader about them."""

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
    def test_the_two_ways_the_grader_was_wrong_in_atb_pac_001_are_fixed(self):
        """The two defects the Método page still describes, fixed by rules U1 and U2/U3 of docs/METODO.md: an
        interval written «a cada 8 horas» now meets the criterion, and a dose that is only inside a renal
        adjustment no longer does. The Método page, in the block «Como se verifica e se afina o corretor»,
        and its four translations still say the grader errs in these two ways: they are corrected, with the
        page regenerated, in the commit that publishes the reclassification, and not before, by decision of
        the project (nothing is regenerated until the table of verdicts has been seen). This test then keeps
        the fix in view, and the paragraph and `test_the_method_page_gives_the_same_two_examples...` below
        are edited together."""
        case = the_case()
        written_another_way = grade(case, an_answer(FALSE_FAILURE, case_id=CASE_ID))
        self.assertTrue(written_another_way.passed, "«a cada 8 horas» voltou a falhar o critério do intervalo")
        right = grade(case, an_answer(f"Amoxicilina 500 mg por via oral, durante 5 dias, {WRITTEN_AS_THE_CRITERION_WANTS}.", case_id=CASE_ID))
        self.assertTrue(right.passed, "a resposta de controlo, escrita como o critério quer, deixou de passar")
        hidden = grade(case, an_answer(FALSE_PASS, case_id=CASE_ID))
        self.assertIn(FailureType.DOSE_INCORRETA, hidden.failures, "a dose certa escondida no ajuste renal voltou a passar")

    def test_the_method_page_now_says_the_two_defects_were_corrected_and_by_which_rules(self):
        """The paragraph that described the two defects as still there was rewritten on 12 October 2026, as the commit
        that regenerated the example said it would."""
        method = panel_html(_Example.page(), "metodo")
        block = method[method.index('id="verificacao-corretor"'):]
        block = block[:block.index("</details>")]
        for quoted in (WRITTEN_ANOTHER_WAY, "0,5 g", "12/10/2026", "U1:", "U2:", "U3:", "U5:", "P1,", "P2,", "P3,", "docs/METODO.md",
                       "não foi escolhida nem ajustada pelo efeito num modelo"):
            with self.subTest(citado=quoted):
                self.assertIn(quoted, block)
        for gone in ("erra nos dois sentidos", "Ainda não se mediu com que frequência"):
            self.assertNotIn(gone, block)

    def test_the_paragraph_is_in_every_language(self):
        from aferidor.traducao_catalogo import CATALOG

        pt = next(k for k in CATALOG if k.startswith("Em 12/10/2026 corrigiu-se o corretor"))
        for lang in ("en", "es", "fr", "de"):
            with self.subTest(lingua=lang):
                self.assertNotEqual(CATALOG[pt][lang], pt)
                self.assertIn(WRITTEN_ANOTHER_WAY, CATALOG[pt][lang])


if __name__ == "__main__":
    unittest.main()
