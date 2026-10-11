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


def side_column(css: str) -> str:
    """The rules that apply from 62rem: the side column."""
    start = css.index("@media (min-width: 62rem)")
    return css[start:css.index("@media print", start)]


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

    def test_the_subsections_are_hidden_unless_the_side_column_shows_them_for_the_current_page(self):
        css = html_estilo.STYLE
        self.assertIn("nav.indice ul.sub { display: none; }", css)
        side = side_column(css)
        for ident in ("casos", "metodo"):
            for inside in (":target", " :target"):
                self.assertIn(f'body:has(main #{ident}{inside}) nav.indice li:has(> a[href="#{ident}"]) > ul.sub', side)
        self.assertRegex(side, r"ul\.sub[^{]*\{ display: block; \}")
        self.assertEqual(tuple(SUBPAGES), html_estilo.SUBPAGE_IDS)

    def test_the_subsections_hold_no_glossary_term_and_the_glossary_is_unchanged_by_them(self):
        page = _Example.page(protocol=_Example.protocol())
        nav = re.search(r'<nav class="indice".*?</nav>', page, flags=re.S).group(0)
        self.assertNotIn("data-termo", nav)


class TestTheSideColumn(unittest.TestCase):
    """From 62rem the pages are a column fixed on the left and the bar over the text only has the notice."""

    def test_the_column_is_fixed_14rem_wide_and_the_text_keeps_room_for_it(self):
        side = side_column(html_estilo.STYLE)
        self.assertIn("body { max-width: 88rem; padding-left: 17rem; }", side)
        self.assertRegex(side, r"\.topo-linha \{ position: fixed; top: 0; bottom: 0; left: calc\(max\(0px, 50% - 44rem\) \+ 1rem\); width: 14rem;")
        self.assertIn("overflow-y: auto", side)

    def test_the_phone_menu_ends_where_the_column_begins(self):
        css = html_estilo.STYLE
        self.assertIn("@media (max-width: 61.99rem) {\n  .topo-linha { flex-wrap: wrap;", css)
        self.assertNotIn("@media (max-width: 62rem)", css)
        self.assertIn("@media (max-width: 61.99rem) { html { --barra: 7rem; } }", html_estilo.BAR_HEIGHT)

    def test_in_the_column_the_pages_do_not_scroll_sideways_and_the_shadows_are_off(self):
        side = side_column(html_estilo.STYLE)
        self.assertRegex(side, r"nav\.indice ul \{ flex-direction: column; overflow: visible; background: none;")

    def test_the_language_menu_opens_inwards_so_the_column_does_not_cut_it(self):
        self.assertIn(".linguas ul { left: 0; right: auto; }", side_column(html_estilo.STYLE))

    def test_the_bar_over_the_text_has_two_declared_heights_before_the_phone_ones(self):
        bar = html_estilo.BAR_HEIGHT
        self.assertLess(bar.index("--barra: 2.6rem"), bar.index("max-width: 68rem"))
        self.assertLess(bar.index("max-width: 68rem"), bar.index("max-width: 61.99rem"))

    def test_the_controls_come_before_the_pages_in_the_markup_and_no_rule_reorders_them(self):
        """The focus follows the markup: the controls are first on the page, so they are first in it."""
        page = _Example.page()
        line = page[page.index('<div class="topo-linha">'):page.index("</header>")]
        self.assertLess(line.index('class="controlos"'), line.index('<nav class="indice"'))
        self.assertIsNone(re.search(r"(?<![\w-])order\s*:", html_estilo.STYLE))

    def test_what_the_model_answered_in_the_gravest_errors_has_no_height_limit_and_never_scrolls(self):
        """The text is cut to 240 characters in the data; the CSS must not hide any more of it."""
        css = html_estilo.STYLE
        self.assertIn(".erro-par blockquote { max-height: none; overflow: visible;", css)
        self.assertNotIn("max-height: 12rem", css)

    def test_a_long_word_in_the_result_breaks_instead_of_running_out_of_the_box(self):
        self.assertIn(".resultado { overflow-wrap: anywhere; }", html_estilo.STYLE)

    def test_the_column_does_not_print_and_the_text_takes_the_width_of_the_sheet(self):
        css = html_estilo.STYLE
        printing = css[css.index("@media print {", css.index("@media (min-width: 62rem)")):]
        self.assertIn(".topo-linha { display: none; }", printing)
        self.assertIn("body { max-width: 72rem; padding-left: 1rem; }", printing)


class TestTheSkipLink(unittest.TestCase):
    """One link per page that takes the focus to that page's heading: the address decides which page is
    shown, so a single link to "the content" would reopen the first page."""

    def test_the_skip_links_are_the_first_things_in_the_page_to_take_the_focus(self):
        page = _Example.page()
        header = page[page.index('<header class="topo">'):page.index("</header>")]
        self.assertTrue(header.startswith('<header class="topo"><a class="saltar"'))
        self.assertLess(header.index('class="saltar"'), header.index('class="controlos"'))
        self.assertLess(header.rindex('class="saltar"'), header.index('<nav class="indice"'))

    def test_there_is_one_per_page_and_each_points_to_the_heading_of_its_page(self):
        page = _Example.page()
        links = re.findall(r'<a class="saltar" href="#([^"]+)">([^<]*)</a>', page)
        # The first page has the title of the report for a heading; the others an <h2> of their own.
        expected = ["titulo-relatorio"] + [f"t-{p}" for p in PAGES[1:]]
        self.assertEqual([a for a, _ in links], expected)
        for anchor, label in links:
            with self.subTest(pagina=anchor):
                self.assertEqual(label, "Saltar para o conteúdo")
                self.assertEqual(len(re.findall(rf'<h[12] id="{anchor}" tabindex="-1">', page)), 1)

    def test_a_report_without_verdicts_skips_only_to_the_pages_it_has(self):
        page = build([a_case()], [])
        self.assertEqual(len(re.findall(r'class="saltar"', page)), len(navigation(page)))

    def test_it_hides_itself_without_ever_taking_itself_out_of_the_tab_order_when_it_is_the_current_one(self):
        css = html_estilo.STYLE
        rule = css[css.index(".saltar { position: absolute;"):css.index(".saltar:focus")]
        self.assertNotIn("visibility", css[css.index(".saltar {"):css.index("@supports selector(:has(*)) {\n  .saltar")])
        self.assertIn("clip: rect(0 0 0 0)", rule)
        shown = css[css.index("@supports selector(:has(*)) {\n  .saltar"):]
        shown = shown[:shown.index("}\n}") + 1]
        self.assertIn('body:not(:has(main :target)) .saltar[href="#titulo-relatorio"]', shown)
        self.assertIn("{ display: block; }", shown)
        self.assertNotIn("visibility", shown)

    def test_the_heading_can_take_the_focus_but_is_not_a_stop_of_the_tab_key(self):
        self.assertEqual(_Example.page().count('tabindex="-1"'), len(PAGES))

    def test_it_does_not_print(self):
        css = html_estilo.STYLE
        printing = css[css.index("@media print {", css.index("@media (min-width: 62rem)")):]
        self.assertIn(".saltar { display: none !important; }", printing)

    def test_the_text_is_in_the_catalogue_in_every_language_without_dashes(self):
        entry = CATALOG["Saltar para o conteúdo"]
        self.assertEqual(sorted(entry), ["de", "en", "es", "fr"])
        for text in [*entry.values(), "Saltar para o conteúdo"]:
            self.assertNotIn("\u2014", text)
            self.assertNotIn("\u2013", text)


if __name__ == "__main__":
    unittest.main()
