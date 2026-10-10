"""The eight pages of the HTML report, the notices every page carries and the translation notice."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from aferidor import html_estilo
from tests.helpers import a_case, an_answer
from tests.html_support import (
    PAGES,
    _Example,
    build,
    navigation,
    panel_html,
    panels,
    visible,
)


class TestReferenceThresholdWithoutProtocol(unittest.TestCase):
    """Without a protocol there is no "approved", but the page still says whether any model
    reached the reference threshold (no case with a critical failure), and that it is only a
    reference and not a protocol written before the trial."""

    BAD = "Amoxicilina 500 mg"  # not the dose asked for: a critical failure
    GOOD = "Amoxicilina 1 g"

    def page(self, answers_by_model, **kwargs) -> str:
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer(text, case_id, model=model)
            for model, texts in answers_by_model.items()
            for case_id, text in zip(("C1", "C2"), texts)
        ]
        return build(cases, answers, **kwargs)

    def test_when_no_model_meets_it_the_best_result_is_given(self):
        text = self.page({"local:llama3.1:8b": (self.BAD, self.BAD), "local:qwen3:8b": (self.GOOD, self.BAD)})
        self.assertIn(
            "Modelos que cumprem o limiar de referência (nenhum caso com falha crítica): 0 de 2. "
            "Melhor resultado: 1 de 2 casos com falha crítica.",
            visible(text),
        )
        self.assertEqual(text.count("✕ não cumpre o limiar de referência"), 2)
        self.assertNotIn("✓ cumpre o limiar de referência", text)

    def test_when_every_model_meets_it_there_is_no_best_result_to_give(self):
        text = self.page({"local:llama3.1:8b": (self.GOOD, self.GOOD), "local:qwen3:8b": (self.GOOD, self.GOOD)})
        self.assertIn("Modelos que cumprem o limiar de referência (nenhum caso com falha crítica): 2 de 2.", visible(text))
        self.assertNotIn("Melhor resultado", text)
        self.assertEqual(text.count("✓ cumpre o limiar de referência"), 2)

    def test_when_only_some_meet_it_each_card_says_its_own(self):
        text = self.page({"local:llama3.1:8b": (self.GOOD, self.GOOD), "local:qwen3:8b": (self.BAD, self.BAD)})
        self.assertIn("Modelos que cumprem o limiar de referência (nenhum caso com falha crítica): 1 de 2.", visible(text))
        self.assertNotIn("Melhor resultado", text)
        self.assertEqual(text.count("✓ cumpre o limiar de referência"), 1)
        self.assertEqual(text.count("✕ não cumpre o limiar de referência"), 1)

    def test_a_single_model_is_counted_as_one(self):
        text = self.page({"local:llama3.1:8b": (self.BAD, self.BAD)})
        self.assertIn(
            "Modelos que cumprem o limiar de referência (nenhum caso com falha crítica): 0 de 1. "
            "Melhor resultado: 2 de 2 casos com falha crítica.",
            visible(text),
        )

    def test_the_page_says_it_is_not_a_protocol(self):
        text = self.page({"falso": (self.BAD, self.BAD)})
        self.assertIn("Não é um protocolo escrito antes do ensaio.", visible(text))
        # the result opens the report; the caveat sits next to the seals of the cards, in Resultados
        self.assertLess(text.index('class="resultado"'), text.index('class="cartoes"'))
        results = panel_html(text, "resultados")
        self.assertIn('id="limiar-referencia"', results)

    def test_with_a_protocol_nothing_about_the_reference_appears(self):
        import json
        import tempfile

        from aferidor.protocolo import read_protocol, template

        bank = Path(__file__).resolve().parent.parent / "casos" / "casos.json"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.json"
            path.write_text(json.dumps(template("x", bank)), encoding="utf-8")
            protocol = read_protocol(path)
        text = self.page({"falso": (self.BAD, self.BAD)}, protocol=protocol)
        self.assertNotIn("limiar de referência", text)
        self.assertNotIn("limiar-referencia", text)
        self.assertIn("Modelos aprovados pelo protocolo (", visible(text))
        self.assertIn("reprovado pelo protocolo", text)

    def test_the_verdict_and_the_seals_follow_the_language_of_the_page(self):
        from aferidor.traducao import LANGS, t

        for lang in LANGS:
            with self.subTest(lingua=lang):
                text = self.page({"falso": (self.BAD, self.BAD)}, lingua=lang)
                said = t(
                    "Modelos que cumprem o limiar de referência (nenhum caso com {falha}): {k} de {n}.", lang,
                    falha=t("falha crítica", lang, form="sem artigo"), k=0, n=1,
                )
                self.assertIn(visible(said), visible(text))
                self.assertIn(f"✕ {t('não cumpre o limiar de referência', lang)}</span>", text)


class TestEachNoticeLivesInItsPage(unittest.TestCase):
    """The background notices live in the page that explains them, with a pointer from the
    first page; notices that qualify the counts themselves open the page with the counts."""

    def page(self, **kwargs) -> str:
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("Amoxicilina 500 mg", "C1", model="local:llama3.1:8b"),
            an_answer("Amoxicilina 500 mg", "C2", model="local:llama3.1:8b"),
        ]
        return build(cases, answers, **kwargs)

    def test_the_sources_notice_is_in_the_sources_page(self):
        text = self.page()
        notice = text.index('id="aviso-fontes"')
        self.assertGreater(notice, text.index('<section class="painel" id="fontes"'))
        self.assertLess(notice, text.index('<section class="painel" id="resultados"'))

    def test_the_first_page_does_not_repeat_the_pointer_the_bar_already_carries(self):
        text = self.page()
        first = panel_html(text, "inicio")
        self.assertNotIn("aviso-fontes", first)
        self.assertNotIn("fontes por confirmar", first)
        self.assertIn('<a href="#fontes">Fontes por confirmar.</a>', text[:text.index("<main>")])

    def test_with_the_sources_confirmed_there_is_neither_pointer_nor_notice(self):
        text = self.page(sources_verified=True)
        self.assertNotIn("aviso-fontes", text)
        self.assertNotIn("fontes por confirmar", text)
        self.assertNotIn("Fontes por confirmar", text)
        self.assertNotIn("Nem todas as fontes", text)
        self.assertIn("Todas as fontes destes casos foram confirmadas por uma pessoa.", text)

    def test_notices_that_qualify_the_counts_open_the_results_page(self):
        answers = [an_answer("Amoxicilina 500 mg", "C1", model="local:llama3.1:8b")]  # C2 never answered
        text = build([a_case("C1"), a_case("C2")], answers)
        notice = text.index("Casos sem resposta.")
        self.assertGreater(notice, text.index('<section class="painel" id="resultados"'))
        self.assertLess(notice, text.index('class="cartoes"'))

    def test_without_verdicts_the_sources_notice_still_appears(self):
        text = build([a_case()], [])
        self.assertIn("Não há veredictos para relatar.", text)
        self.assertIn('id="aviso-fontes"', text)


class TestEightPages(unittest.TestCase):
    """Each tab is its own page of the same file, shown alone by CSS (no script)."""

    def page(self, **kwargs) -> str:
        return build([a_case()], [an_answer("500 mg")], **kwargs)

    def test_the_report_is_eight_pages_each_with_its_own_heading(self):
        text = self.page()
        self.assertEqual(panels(text), list(PAGES))
        self.assertEqual(text.count("<h1"), 1)  # the first page is titled by the report's own title
        self.assertIn('<section class="painel" id="inicio" aria-labelledby="titulo-relatorio">', text)
        for ident in PAGES[1:]:
            with self.subTest(page=ident):
                self.assertEqual(text.count(f'<h2 id="t-{ident}">'), 1)
                self.assertIn(f'aria-labelledby="t-{ident}"', text)

    def test_every_page_has_its_own_content_in_every_language(self):
        """The same pages in the five languages: each one carries what makes it that page."""
        from aferidor.traducao import LANGS

        markers = {
            "inicio": ('class="resultado"', 'class="saber-mais"'),
            "sobre": ('class="sobre"', "<pre><code>git clone"),
            "fontes": ('class="estado-contagens"', ">DGS</abbr> 16"),
            "conclusoes": ('class="conclusoes"', 'class="fecho"'),
        }
        for lang in LANGS:
            page = _Example.page(lingua=lang)
            for ident, wanted in markers.items():
                section = panel_html(page, ident)
                for marker in wanted:
                    with self.subTest(lingua=lang, pagina=ident, marca=marker):
                        self.assertIn(marker, section)

    def test_every_link_in_the_navigation_is_a_page_and_every_page_is_linked(self):
        self.assertEqual(navigation(self.page()), list(PAGES))

    def test_the_navigation_is_a_list_of_links_and_does_not_claim_a_current_page(self):
        """Without a script the state of a tab cannot be kept, and a page marked current that no
        longer is would say something false to a screen reader; the heading of the page is
        what announces where the reader is."""
        text = self.page()
        self.assertNotIn("aria-current=\"page\"", re.search(r'<nav class="indice".*?</nav>', text, flags=re.S).group(0))
        self.assertNotIn('role="tab', text)
        self.assertNotIn('role="tablist"', text)

    def test_the_first_page_comes_first_and_is_shown_when_the_address_names_none(self):
        self.assertIn("main:not(:has(:target)) > #inicio", html_estilo.STYLE)
        self.assertEqual(panels(self.page())[0], "inicio")

    def test_a_page_is_shown_when_it_is_the_target_or_holds_the_target(self):
        """`#corpo-<caso>` points inside the Casos page: that page has to open, not only the
        one whose id is in the address."""
        self.assertIn("main > .painel:target, main > .painel:has(:target)", html_estilo.STYLE)

    def test_pages_are_hidden_only_where_has_is_understood(self):
        """Otherwise every page would be hidden and nothing could be shown."""
        css = html_estilo.STYLE
        self.assertEqual(css.count("main > .painel { display: none; }"), 1)
        before = css[:css.index("main > .painel { display: none; }")]
        block = before[before.rindex("@supports selector(:has(*))"):]
        self.assertGreater(block.count("{") - block.count("}"), 0)  # still inside that @supports

    def test_printing_shows_every_page(self):
        css = html_estilo.STYLE
        printing = css[css.index("@media print"):]
        self.assertIn("main > .painel { display: block !important;", printing)

    def test_a_report_without_verdicts_has_only_the_pages_that_exist(self):
        text = build([a_case()], [])
        self.assertEqual(panels(text), ["inicio", "sobre", "fontes", "resultados", "metodo"])
        self.assertEqual(navigation(text), ["inicio", "sobre", "fontes", "resultados", "metodo"])

    def test_the_bar_is_fixed_and_the_scroll_padding_clears_it(self):
        css = html_estilo.STYLE
        self.assertIn(".topo { position: sticky; top: 0;", css)
        self.assertIn("scroll-padding-top: var(--barra)", css)
        self.assertIn("--barra:", css)

    def test_the_bar_has_the_height_it_declares_and_no_language_has_its_own(self):
        """The bar is exactly `--barra` high and the page's scroll padding leaves exactly that
        free, so the height is declared once, per width, and not measured per language."""
        css = html_estilo.STYLE
        self.assertRegex(css, r"\.topo \{[^}]*box-sizing: border-box; height: var\(--barra\);")
        self.assertEqual(re.findall(r"--barra: ([\d.]+)rem", html_estilo.BAR_HEIGHT), ["4.8", "7", "8.6", "9.4"])
        self.assertNotIn("[lang", html_estilo.BAR_HEIGHT)

    def test_the_pages_never_wrap_so_the_bar_keeps_its_height(self):
        css = html_estilo.STYLE
        rule = css[css.index("nav.indice ul {"):css.index("nav.indice ul::-webkit-scrollbar")]
        self.assertIn("flex-wrap: nowrap", rule)
        self.assertIn("overflow-x: auto", rule)

    def test_the_pages_that_scroll_sideways_show_a_shadow_where_there_is_more(self):
        """Four backgrounds, no script: two that cover the edge when there is nothing more that
        way, two that draw the shadow. The scroll bar is hidden, so the shadow is the sign."""
        css = html_estilo.STYLE
        rule = css[css.index("nav.indice ul {"):css.index("nav.indice ul::-webkit-scrollbar")]
        self.assertEqual(rule.count("no-repeat local"), 2)
        self.assertEqual(rule.count("no-repeat scroll"), 2)
        self.assertIn("scrollbar-width: none", rule)
        self.assertNotIn("url(", css)


class TestTheNoticeEveryPageCarries(unittest.TestCase):
    """What the verdicts are, and where the sources stand, stays in the fixed bar."""

    def bar(self, lang: str = "pt", **kwargs) -> str:
        text = build([a_case()], [an_answer("500 mg")], lingua=lang, **kwargs)
        return re.search(r'<header class="topo">.*?</header>', text, flags=re.S).group(0)

    def test_the_bar_says_the_verdicts_are_triage_and_links_the_sources_page(self):
        bar = self.bar()
        self.assertIn("Veredictos: triagem automática do corretor, sem validação clínica.", bar)
        self.assertIn('<a href="#fontes">Fontes por confirmar.</a>', bar)

    def test_with_the_sources_confirmed_the_bar_keeps_only_the_first_sentence(self):
        bar = self.bar(sources_verified=True)
        self.assertIn("Veredictos: triagem automática do corretor", bar)
        self.assertNotIn("Fontes por confirmar", bar)

    def test_the_notice_follows_the_language_of_the_page(self):
        from aferidor.traducao import LANGS, t

        for lang in LANGS:
            with self.subTest(lingua=lang):
                bar = self.bar(lang)
                self.assertIn(t("Veredictos: triagem automática do corretor, sem validação clínica.", lang), bar)
                self.assertIn(t("Fontes por confirmar.", lang), bar)

    def test_the_bar_never_carries_the_translation_notice_in_any_language(self):
        from aferidor.traducao import LANGS

        for lang in LANGS:
            with self.subTest(lingua=lang):
                self.assertNotIn('class="traducao"', self.bar(lang))


class TestTheTranslationNotice(unittest.TestCase):
    """Only Portuguese is the reference: every other language says, at the top of each page and in
    the footer, that it is a machine translation no native speaker has read."""

    def page(self, lang: str) -> str:
        return build([a_case()], [an_answer("500 mg")], lingua=lang)

    def test_every_other_language_says_so_at_the_top_of_every_page_and_in_the_footer(self):
        from aferidor.traducao import LANGS, UNREVIEWED, UNREVIEWED_NOTICE, t

        for lang in LANGS:
            with self.subTest(lingua=lang):
                text = self.page(lang)
                said = t(UNREVIEWED_NOTICE, lang)
                if lang in UNREVIEWED:
                    notice = f'<p class="traducao" role="note">{said}</p>'
                    self.assertEqual(text.count(notice), len(PAGES) + 1)  # eight pages and the footer
                    for ident in PAGES:
                        at = text.index(f'<section class="painel" id="{ident}"')
                        self.assertIn(notice, text[at:text.index("</h2>", at)])
                    self.assertIn(notice, text[text.index('<footer class="rodape">'):])
                else:
                    self.assertNotIn('class="traducao"', text)

    def test_the_notice_comes_before_the_title_of_each_page(self):
        text = self.page("de")
        for ident in PAGES[1:]:
            at = text.index(f'<section class="painel" id="{ident}"')
            self.assertLess(text.index('class="traducao"', at), text.index(f'<h2 id="t-{ident}">', at))

    def test_portuguese_is_the_only_reference(self):
        from aferidor.traducao import UNREVIEWED

        self.assertEqual(sorted(UNREVIEWED), ["de", "en", "es", "fr"])


    def test_the_bar_sits_outside_main_so_it_is_on_every_page(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertLess(text.index('class="faixa"'), text.index("<main>"))


if __name__ == "__main__":
    unittest.main()
