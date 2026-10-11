"""The trial conditions of the HTML report say which grader judged the answers and when, and the Method
page states the rule for a grader frozen by a protocol. The footer names the grader too."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from aferidor import grader_id
from aferidor.protocolo import read_protocol, template
from aferidor.traducao import t
from tests.helpers import a_case, an_answer
from tests.html_support import FRAME_WORDS, ROOT, _Example, build, panel_html, panel_text, visible, words

RULE_START = "Cada relatório volta a corrigir, no momento em que é gerado"


def conditions(page: str) -> str:
    """The trial conditions block of the Method page, from its heading to the end of the block."""
    method = panel_html(page, "metodo")
    start = method.index('<div class="condicoes" id="condicoes">')
    return method[start:method.index("</div>", start)]


def frozen_protocol(freeze_to: str | None = None):
    """A protocol that froze the grader of the code running now, or another one if `freeze_to` is given."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "p.json"
        payload = template("x", ROOT / "casos" / "casos.json", today=date(2026, 9, 1), freeze_correction=True)
        if freeze_to:
            payload["corretor_id"] = freeze_to
        path.write_text(json.dumps(payload), encoding="utf-8")
        return read_protocol(path)


class TestTheConditionsNameTheGrader(unittest.TestCase):
    def line(self, page: str) -> str:
        block = conditions(page)
        return re.search(r"<p>(Respostas corrigidas.*?)</p>", block, flags=re.S).group(1)

    def test_the_conditions_say_when_the_answers_were_graded_and_with_which_grader(self):
        page = _Example.page()
        expected = (
            f"Respostas corrigidas em 2026-10-10 com o corretor <code>{grader_id()}</code>. "
            "A versão que aparece por modelo, abaixo, é a do código quando cada resposta foi recolhida."
        )
        self.assertEqual(self.line(page), expected)
        block = conditions(page)
        self.assertLess(block.index("Respostas corrigidas"), block.index("<dl>"))

    def test_the_line_is_the_same_with_a_protocol_and_the_freeze_warning_still_comes_with_it(self):
        without = self.line(_Example.page())
        for protocol in (_Example.protocol(), frozen_protocol()):
            with self.subTest(protocol=protocol.grader_id or "sem corretor congelado"):
                self.assertEqual(self.line(_Example.page(protocol=protocol)), without)
        other = "0.1.0+corretor.000000000000"
        page = _Example.page(protocol=frozen_protocol(freeze_to=other))
        self.assertEqual(self.line(page), without)  # the line says what graded now; the warning says the freeze differs
        self.assertIn(f"o protocolo fixou o corretor na versão {other}: o corretor mudou depois do protocolo", visible(page))

    def test_the_grader_it_names_is_the_one_in_use(self):
        with mock.patch("aferidor.html_report.grader_id", return_value="0.1.0+corretor.aaaaaaaaaaaa"):
            page = build([a_case()], [an_answer("Amoxicilina 1 g")])
        self.assertIn("<code>0.1.0+corretor.aaaaaaaaaaaa</code>", self.line(page))
        self.assertNotIn(grader_id(), conditions(page))

    def test_the_date_is_the_one_the_report_is_written(self):
        page = build([a_case()], [an_answer("Amoxicilina 1 g")])  # the helper writes on 2026-09-14
        self.assertIn("Respostas corrigidas em 2026-09-14 com o corretor", self.line(page))

    def test_without_answers_there_is_nothing_to_say_about_grading_but_the_rule_stays(self):
        page = build([a_case()], [])
        block = conditions(page)
        self.assertNotIn("Respostas corrigidas", block)
        self.assertIn(RULE_START, block)

    def test_the_rule_is_in_every_report_with_or_without_a_protocol(self):
        pages = {
            "exemplo": _Example.page(),
            "com protocolo": _Example.page(protocol=_Example.protocol()),
            "com corretor congelado": _Example.page(protocol=frozen_protocol()),
            "um caso": build([a_case()], [an_answer("Amoxicilina 1 g")]),
            "sem respostas": build([a_case()], []),
        }
        for name, page in pages.items():
            with self.subTest(relatorio=name):
                self.assertEqual(page.count(RULE_START), 1)
                self.assertNotIn("26B", conditions(page))  # a rule of the method, not a note about one trial

    def test_both_sit_in_the_closed_block_and_add_no_words_to_the_method_page(self):
        page = _Example.page()
        method = panel_html(page, "metodo")
        technical = method[method.index('<details class="recolhe tecnico" id="detalhes">'):]
        self.assertIn("Respostas corrigidas", technical)
        self.assertIn(RULE_START, technical)
        before = panel_text(page, "metodo")
        self.assertNotIn("Respostas corrigidas", before)
        self.assertNotIn(RULE_START, before)

    def test_the_two_texts_come_out_in_every_language_with_their_placeholders_filled(self):
        for lang in ("en", "es", "fr", "de"):
            with self.subTest(lingua=lang):
                line = t("Respostas corrigidas em {data} com o corretor {corretor}. A versão que aparece por modelo, "
                         "abaixo, é a do código quando cada resposta foi recolhida.", lang, data="2026-10-10", corretor="X")
                self.assertNotIn("{", line)
                self.assertIn("2026-10-10", line)
                self.assertNotIn("Respostas", line)  # translated, not left in Portuguese


class TestTheFooterNamesTheGrader(unittest.TestCase):
    def footer(self, page: str) -> str:
        return page[page.index('<footer class="rodape">'):page.index("</footer>")]

    def test_the_footer_has_the_identifier_beside_the_date_and_nothing_else_with_it(self):
        footer = self.footer(_Example.page())
        self.assertIn(f'<p class="data">Relatório escrito em 2026-10-10.</p><p class="data">{grader_id()}</p>', footer)

    def test_the_frame_still_fits_with_it(self):
        page = _Example.page()
        bar = re.search(r'<p class="faixa"[^>]*>(.*?)</p>', page, flags=re.S).group(1)
        skip = re.search(r'<a class="saltar"[^>]*>(.*?)</a>', page, flags=re.S).group(1)
        total = words(visible(bar)) + words(visible(self.footer(page))) + words(visible(skip))
        self.assertEqual(total, 50)
        self.assertLessEqual(total, FRAME_WORDS)


if __name__ == "__main__":
    unittest.main()
