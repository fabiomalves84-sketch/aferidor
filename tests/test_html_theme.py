"""The theme switch and the contrast of the palette."""

from __future__ import annotations

import re
import unittest

from aferidor import html_estilo
from tests.helpers import an_answer
from tests.html_support import (
    a_case,
    build,
    contrast,
    tokens,
)


class TestTheme(unittest.TestCase):
    """A light and dark switch in the header, in CSS alone, with measured contrast."""

    def setUp(self):
        self.text = build([a_case()], [an_answer("1 g")])

    def test_the_header_has_a_labelled_switch_with_both_themes(self):
        header = self.text[self.text.index('<header class="topo">'):self.text.index("</header>")]
        self.assertIn('role="radiogroup" aria-label="Tema"', header)
        for theme in ("tema-claro", "tema-escuro"):
            with self.subTest(theme=theme):
                self.assertIn(f'<input type="radio" name="tema" id="{theme}">', header)
                self.assertIn(f'<label for="{theme}">', header)

    def test_nothing_is_picked_so_the_page_starts_on_the_system_theme(self):
        self.assertNotIn("checked>", self.text)
        self.assertNotIn('checked="', self.text)

    def test_the_choice_overrides_the_system_and_print_is_always_light(self):
        self.assertIn(":root:not(:has(#tema-claro:checked))", self.text)
        self.assertIn(":root:has(#tema-escuro:checked) { color-scheme: dark;", self.text)
        self.assertRegex(self.text, r"@media print \{\s*:root, :root:has\(#tema-escuro:checked\) \{ color-scheme: light;")

    def test_both_themes_define_the_sametokens(self):
        self.assertEqual(
            set(re.findall(r"--([a-z0-9-]+):", html_estilo.LIGHT_TOKENS)),
            set(re.findall(r"--([a-z0-9-]+):", html_estilo.DARK_TOKENS)),
        )

    def test_every_text_colour_reads_on_the_page_and_on_cards_in_both_themes(self):
        """4.5:1 is the WCAG AA floor for body text; computed, not judged by eye."""
        for name, block in (("claro", html_estilo.LIGHT_TOKENS), ("escuro", html_estilo.DARK_TOKENS)):
            colours = tokens(block)
            for text in ("ink", "ink-2", "muted", "accent", "success-text", "critical-text"):
                grounds = ("page", "surface", "surface-2")
                if text in ("ink", "ink-2", "muted", "accent"):
                    grounds += ("highlight",)  # the chips and the result block of the first page
                for ground in grounds:
                    with self.subTest(theme=name, text=text, ground=ground):
                        self.assertGreaterEqual(contrast(colours[text], colours[ground]), 4.5)


class TestPaletteContrast(unittest.TestCase):
    """The petrol palette, in both themes: what is not text 3:1, the clinical colours untouched, the bar
    and its scroll shadow on the same ground. The 4.5:1 for text is in `TestTheme`."""

    THEMES = {"claro": html_estilo.LIGHT_TOKENS, "escuro": html_estilo.DARK_TOKENS}
    GROUNDS = ("page", "surface", "surface-2", "highlight")

    def test_what_is_not_text_stands_out_at_3_to_1(self):
        """The accent draws the border of the result and the underline of the current page."""
        for theme, block in self.THEMES.items():
            palette = tokens(block)
            for bg in self.GROUNDS:
                with self.subTest(tema=theme, fundo=bg):
                    self.assertGreaterEqual(contrast(palette["accent"], palette[bg]), 3.0)

    def test_the_clinical_colours_did_not_change_with_the_palette(self):
        for block in self.THEMES.values():
            palette = tokens(block)
            self.assertEqual(
                (palette["good"], palette["warning"], palette["serious"], palette["critical"]),
                ("#0ca30c", "#fab219", "#ec835a", "#d03b3b"),
            )
        self.assertEqual(tokens(html_estilo.LIGHT_TOKENS)["critical-text"], "#b42a2a")
        self.assertEqual(tokens(html_estilo.DARK_TOKENS)["critical-text"], "#ff8f86")

    def test_the_bar_background_and_the_scroll_shadow_cover_use_the_same_token(self):
        css = html_estilo.STYLE
        bar = re.search(r"\.topo \{[^}]*background: var\(--([a-z0-9-]+)\)", css).group(1)
        self.assertIn(f"linear-gradient(to right, var(--{bar}) 35%, transparent) left center", css)
        self.assertIn(f"linear-gradient(to left, var(--{bar}) 35%, transparent) right center", css)


if __name__ == "__main__":
    unittest.main()
