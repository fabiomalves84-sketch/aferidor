"""The subsections the side navigation lists under Casos and Método: written in the page, hidden by the CSS."""

from __future__ import annotations

import html
import re
import unittest

from aferidor import html_estilo
from aferidor.html_report import SUBPAGES
from aferidor.traducao_catalogo import CATALOG
from tests.helpers import a_case, an_answer
from tests.html_support import PAGES, _Example, build, navigation, panel_html


def sublists(page: str) -> dict[str, list[tuple[str, str]]]:
    """{page: [(anchor, label)]} for each item of the navigation that has a `ul.sub`."""
    nav = re.search(r'<nav class="indice".*?</nav>', page, flags=re.S).group(0)
    found: dict[str, list[tuple[str, str]]] = {}
    for item in re.findall(r"<li><a href=\"#([^\"]+)\">[^<]*</a>(<ul class=\"sub\">.*?</ul>)</li>", nav, flags=re.S):
        found[item[0]] = [(a, html.unescape(label)) for a, label in re.findall(r'<li><a href="#([^"]+)">([^<]*)</a></li>', item[1])]
    return found


def heading_of(page: str, anchor: str) -> str:
    """The words the page itself writes for the block a link points to: the heading or summary of the
    element with that id, or of the closed block that holds it."""
    start = page.index(f' id="{anchor}"')
    own = re.match(r'[^>]*>\s*<(?:h3|summary)[^>]*>(.*?)</(?:h3|summary)>', page[start:], flags=re.S)
    if own:
        return html.unescape(re.sub(r"<[^>]+>", "", own.group(1)))
    before = page[:start]
    opened = before.rindex("<details")
    summary = re.search(r"<summary[^>]*>(.*?)</summary>", page[opened:], flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", summary.group(1)))


class TestTheSubsectionsAreInTheNavigation(unittest.TestCase):
    def test_casos_and_metodo_list_their_subsections_and_no_other_page_does(self):
        found = sublists(_Example.page())
        self.assertEqual(sorted(found), ["casos", "metodo"])
        self.assertEqual([a for a, _ in found["casos"]], ["erros", "grelha", "casos-com-falha"])

    def test_the_list_of_pages_is_still_the_eight_pages(self):
        self.assertEqual(navigation(_Example.page()), list(PAGES))

    def test_each_subsection_points_to_something_in_the_report(self):
        page = _Example.page(protocol=_Example.protocol())
        for panel, links in sublists(page).items():
            for anchor, label in links:
                with self.subTest(panel=panel, ancora=anchor):
                    self.assertEqual(page.count(f' id="{anchor}"'), 1)
                    self.assertTrue(label)

    def test_each_link_says_what_the_page_itself_says_for_that_block(self):
        page = _Example.page(protocol=_Example.protocol())
        for links in sublists(page).values():
            for anchor, label in links:
                with self.subTest(ancora=anchor):
                    self.assertEqual(label, heading_of(page, anchor))

    def test_the_criterion_is_listed_only_when_there_is_a_protocol(self):
        with_protocol = [a for a, _ in sublists(_Example.page(protocol=_Example.protocol()))["metodo"]]
        without = [a for a, _ in sublists(_Example.page())["metodo"]]
        self.assertIn("criterio", with_protocol)
        self.assertNotIn("criterio", without)
        self.assertEqual([a for a in with_protocol if a != "criterio"], without)

    def test_the_methodo_targets_lie_inside_closed_blocks_so_the_browser_opens_them(self):
        page = _Example.page(protocol=_Example.protocol())
        method = panel_html(page, "metodo")
        for anchor in ("como-ler-texto", "como-se-verifica-o-corretor", "fontes-por-organismo", "condicoes", "glossario", "metodo-texto"):
            with self.subTest(ancora=anchor):
                before = method[:method.index(f' id="{anchor}"')]
                self.assertGreater(before.count("<details"), before.count("</details>"))

    def test_without_verdicts_there_is_no_casos_list_and_no_dead_link(self):
        page = build([a_case()], [])
        found = sublists(page)
        self.assertEqual(sorted(found), ["metodo"])
        for anchor, _ in found["metodo"]:
            self.assertIn(f' id="{anchor}"', page)

    def test_a_tiny_report_has_no_link_to_a_block_it_does_not_have(self):
        page = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        for links in sublists(page).values():
            for anchor, _ in links:
                with self.subTest(ancora=anchor):
                    self.assertIn(f' id="{anchor}"', page)

    def test_every_label_is_in_the_catalogue_for_all_four_other_languages(self):
        for links in SUBPAGES.values():
            for _, label in links:
                with self.subTest(rotulo=label):
                    self.assertIn(label, CATALOG)
                    self.assertEqual(sorted(CATALOG[label]), ["de", "en", "es", "fr"])

    def test_the_subsections_are_hidden_by_the_css_for_now(self):
        self.assertIn("nav.indice ul.sub { display: none; }", html_estilo.STYLE)

    def test_the_subsections_hold_no_glossary_term_and_the_glossary_is_unchanged_by_them(self):
        page = _Example.page(protocol=_Example.protocol())
        nav = re.search(r'<nav class="indice".*?</nav>', page, flags=re.S).group(0)
        self.assertNotIn("data-termo", nav)


if __name__ == "__main__":
    unittest.main()
