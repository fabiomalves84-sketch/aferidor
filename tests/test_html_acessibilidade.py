"""The phone menu keeps the current page in sight, the notice about the sources stands out without changing, smooth
scrolling gives way to reduced motion, and the skip link is there in every language."""

from __future__ import annotations

import re
import unittest

from aferidor import html_estilo
from aferidor.traducao import LANGS
from tests.html_support import PAGES, _Example, contrast

CSS = html_estilo.STYLE


def tokens(block: str) -> tuple[dict[str, str], dict[str, tuple[float, ...]]]:
    hexes = dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-f]{6})", block))
    rgba = {k: tuple(float(x) for x in v.split(",")) for k, v in re.findall(r"--([a-z0-9-]+):\s*rgba\(([^)]*)\)", block)}
    return hexes, rgba


def over(rgba: tuple[float, ...], base: str) -> str:
    """The colour of an rgba tint laid on an opaque ground."""
    r, g, b, a = rgba
    ground = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a * c + (1 - a) * g0) for c, g0 in zip((r, g, b), ground))


class TestThePhoneMenuKeepsTheCurrentPageInSight(unittest.TestCase):
    def phone_block(self) -> str:
        start = CSS.index("@media (max-width: 61.99rem) {\n  .topo-linha { flex-wrap: wrap;")
        return CSS[start:CSS.index("\n}\n", CSS.index("@supports selector(:has(*))", start)) + 3]

    def test_the_item_of_the_current_page_is_sticky_on_both_sides_for_every_page_and_only_on_the_phone(self):
        block = self.phone_block()
        self.assertIn("position: sticky; left: 0; right: 0;", block)
        for ident in PAGES:
            if ident == "inicio":
                continue
            self.assertIn(f'body:has(main #{ident}:target) nav.indice li:has(> a[href="#{ident}"])', block)
            self.assertIn(f'body:has(main #{ident} :target) nav.indice li:has(> a[href="#{ident}"])', block)
        self.assertIn('body:not(:has(main :target)) nav.indice li:has(> a[href="#inicio"])', block)
        self.assertEqual(CSS.count("position: sticky; left: 0; right: 0;"), 1)  # nowhere else, so not in the side column

    def test_it_has_a_ground_so_it_does_not_show_what_it_covers(self):
        self.assertRegex(self.phone_block(), r"position: sticky; left: 0; right: 0; z-index: 1; background: var\(--page\);")

    def test_the_menu_still_never_wraps_and_still_scrolls_with_its_shadows(self):
        rule = CSS[CSS.index("nav.indice ul {"):CSS.index("nav.indice ul::-webkit-scrollbar")]
        self.assertIn("flex-wrap: nowrap", rule)
        self.assertIn("overflow-x: auto", rule)
        self.assertEqual(rule.count("no-repeat scroll"), 2)

    def test_the_page_still_has_no_script(self):
        for lang in LANGS:
            self.assertNotIn("<script", _Example.page(lingua=lang))


class TestReducedMotion(unittest.TestCase):
    def test_smooth_scrolling_is_switched_off_for_whoever_asks_for_less_motion(self):
        self.assertIn("html { background: var(--page); scroll-behavior: smooth;", CSS)
        self.assertRegex(CSS, r"@media \(prefers-reduced-motion: reduce\) \{\s*html \{ scroll-behavior: auto; \}\s*\}")

    def test_there_is_no_transition_animation_or_keyframes_so_nothing_else_has_to_be_switched_off(self):
        for word in ("transition", "animation", "@keyframes"):
            self.assertNotIn(word, CSS)
        self.assertEqual(CSS.count("scroll-behavior"), 2)  # smooth, and the reduced-motion override


class TestTheSourcesNotice(unittest.TestCase):
    def test_the_text_of_the_notice_is_the_same_as_before_in_every_language(self):
        for lang in LANGS:
            page = _Example.page(lingua=lang)
            bar = re.search(r'<p class="faixa"[^>]*>(.*?)</p>', page, flags=re.S).group(1)
            self.assertRegex(bar, r'<a href="#fontes">[^<]+</a>$')
        pt = re.search(r'<p class="faixa"[^>]*>(.*?)</p>', _Example.page(), flags=re.S).group(1)
        self.assertEqual(pt, 'Veredictos: triagem automática do corretor, sem validação clínica. <a href="#fontes">Fontes por confirmar.</a>')

    def test_the_link_is_larger_bold_and_underlined_with_the_height_of_a_line_of_the_sentence_so_the_bar_keeps_its_height(self):
        rule = CSS[CSS.index(".faixa a {"):CSS.index("}", CSS.index(".faixa a {")) + 1]
        for part in ("font-size: 0.9rem", "line-height: 1.2", "font-weight: 650", "text-decoration: underline", "background: var(--warning-bg)"):
            self.assertIn(part, rule)
        sentence = CSS[CSS.index(".faixa {"):CSS.index("}", CSS.index(".faixa {"))]
        size, line = (float(x) for x in re.search(r"font-size: ([\d.]+)rem; line-height: ([\d.]+)", sentence).groups())
        self.assertAlmostEqual(size * line, 0.9 * 1.2)  # one line of the notice is as high with the link as without it

    def test_the_text_of_the_link_and_its_outline_have_the_contrast_in_both_themes(self):
        for name, block in (("claro", html_estilo.LIGHT_TOKENS), ("escuro", html_estilo.DARK_TOKENS)):
            hexes, rgba = tokens(block)
            pill = over(rgba["warning-bg"], hexes["page"])
            with self.subTest(tema=name):
                self.assertGreaterEqual(contrast(hexes["ink"], pill), 4.5)
                self.assertGreaterEqual(contrast(hexes["muted"], hexes["page"]), 3.0)  # the outline, against the bar

    def test_the_measured_ratios_of_the_report(self):
        light, dark = tokens(html_estilo.LIGHT_TOKENS), tokens(html_estilo.DARK_TOKENS)
        ratio = lambda t: round(contrast(t[0]["ink"], over(t[1]["warning-bg"], t[0]["page"])), 2)
        self.assertEqual((ratio(light), ratio(dark)), (14.25, 11.52))
        self.assertEqual((round(contrast(light[0]["muted"], light[0]["page"]), 2), round(contrast(dark[0]["muted"], dark[0]["page"]), 2)), (5.29, 7.25))


class TestTheSkipLinkIsInEveryLanguage(unittest.TestCase):
    WORDS = {"pt": "Saltar para o conteúdo", "en": "Skip to content", "es": "Saltar al contenido", "fr": "Aller au contenu", "de": "Zum Inhalt springen"}

    def test_it_is_the_first_thing_in_the_page_and_says_the_words_of_the_language(self):
        for lang in LANGS:
            with self.subTest(lingua=lang):
                page = _Example.page(lingua=lang)
                header = page[page.index('<header class="topo">'):]
                self.assertTrue(header.startswith('<header class="topo"><a class="saltar"'))
                links = re.findall(r'<a class="saltar" href="#([^"]+)">([^<]*)</a>', page)
                self.assertEqual(len(links), len(PAGES))
                self.assertEqual({text for _, text in links}, {self.WORDS[lang]})

    def test_it_only_shows_when_it_has_the_focus_from_the_keyboard(self):
        self.assertRegex(CSS, r"\.saltar \{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect\(0 0 0 0\)")
        self.assertIn(".saltar:focus { position: fixed;", CSS)


if __name__ == "__main__":
    unittest.main()
