"""The HTML report: same numbers as the Markdown one, escaped and self contained."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from datetime import date

from aferidor import html_estilo, html_report, report
from aferidor.grading import consistency_by_case, consistency_by_model, grade_all
from aferidor.models import Case, Criterion, Source
from aferidor.risk import FailureType
from tests.helpers import an_answer


def a_case(case_id: str = "C1", category: str = "dose") -> Case:
    return Case(
        case_id=case_id,
        category=category,
        question="Que dose de amoxicilina?",
        reference="Amoxicilina 1000 mg de 8/8h",
        source=Source(name="Guia ATB", reference="p. 17"),
        criteria=(
            Criterion(kind="contem", terms=("1000 mg", "1 g"), failure=FailureType.DOSE_INCORRETA),
        ),
    )


def visible(page: str) -> str:
    """The page as a reader sees it: tags out, whitespace collapsed."""
    import html as _h
    text = " ".join(_h.unescape(re.sub(r"<[^>]+>", " ", page)).split())
    return re.sub(r" ([:;,.)])", r"\1", text)


def build(cases, answers, **kwargs) -> str:
    verdicts, missing = grade_all(cases, answers)
    return html_report.build(
        cases, answers, verdicts, missing=kwargs.pop("missing", missing),
        today=date(2026, 9, 14), **kwargs
    )


class TestDocument(unittest.TestCase):
    def test_it_is_a_complete_self_contained_document(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertTrue(text.startswith("<!DOCTYPE html>"))
        self.assertIn("<title>Relatório do Aferidor</title>", text)
        self.assertIn("</html>", text)

    def test_it_loads_nothing_from_the_network(self):
        """Opening the report fetches nothing: no resource attribute, no stylesheet link, no
        script, no import. The only addresses are a link the reader may follow and the preview
        image that link previews read (see the next test)."""
        text = build([a_case()], [an_answer("1 g")])
        self.assertNotIn("http://", text)
        for forbidden in ("<link ", "<script", "<img", "<iframe", "<object", "<embed", " src=", "@import", "url("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_the_only_addresses_in_attributes_are_the_project_link_and_the_preview_image(self):
        """What a model wrote is untrusted text: an address in an answer, even a whole <a> tag,
        stays escaped text and never becomes a link, an image or a resource."""
        from html.parser import HTMLParser

        answer = '500 mg. Ver https://exemplo.pt/x e <a href="https://mau.pt">aqui</a>'
        text = build([a_case()], [an_answer(answer)])
        found = []

        class Attributes(HTMLParser):
            def handle_starttag(self, tag, attrs):
                for name, value in attrs:
                    if value and value.startswith(("http://", "https://")):
                        found.append((tag, name, value))

        Attributes().feed(text)
        self.assertEqual(
            sorted(found),
            sorted([
                ("a", "href", html_report.REPO_URL),
                ("a", "href", html_report.REPO_URL),
                ("a", "href", html_report.COMO_CORRER_URL),
                ("meta", "content", html_report.PREVIEW_IMAGE_URL),
            ]),
        )
        for _, _, address in found:  # nothing but the repository, and the preview image
            self.assertTrue(address.startswith(html_report.REPO_URL) or address == html_report.PREVIEW_IMAGE_URL, address)
        self.assertIn("https://exemplo.pt/x", text)  # the answer is still shown, as text

    def test_it_works_in_dark_mode(self):
        self.assertIn("prefers-color-scheme: dark", build([a_case()], [an_answer("1 g")]))

    def test_it_carries_the_date(self):
        self.assertIn("2026-09-14", build([a_case()], [an_answer("1 g")]))

    def test_the_content_sits_in_one_main_landmark_between_the_navigation_and_the_footer(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertEqual(text.count("<main>"), 1)
        self.assertEqual(text.count("</main>"), 1)
        self.assertLess(text.index("</nav>"), text.index("<main>"))
        self.assertLess(text.index("</main>"), text.index("<footer"))

    def test_the_header_the_navigation_and_the_footer_stay_outside_main_and_the_sections_inside(self):
        from html.parser import HTMLParser

        outside: set[str] = set()
        inside: set[str] = set()

        class Landmarks(HTMLParser):
            depth = 0

            def handle_starttag(self, tag, attrs):
                if tag == "main":
                    self.depth += 1
                    return
                a = dict(attrs)
                where = inside if self.depth else outside
                if (tag, a.get("class")) in (("header", "topo"), ("nav", "indice"), ("footer", "rodape")):
                    where.add(f"{tag}.{a['class']}")
                if tag == "section":
                    where.add(f"section#{a.get('id') or a.get('class')}")

            def handle_endtag(self, tag):
                if tag == "main":
                    self.depth -= 1

        Landmarks().feed(build([a_case()], [an_answer("500 mg")]))
        self.assertEqual(outside, {"header.topo", "nav.indice", "footer.rodape"})
        self.assertIn("section#resultados", inside)
        self.assertIn("section#inicio", inside)

    def test_there_is_a_main_in_every_language_and_in_a_page_without_verdicts(self):
        from aferidor.traducao import LANGS

        for lang in LANGS:
            with self.subTest(lingua=lang):
                self.assertEqual(build([a_case()], [an_answer("1 g")], lingua=lang).count("<main>"), 1)
        self.assertEqual(build([a_case()], []).count("<main>"), 1)


class TestEscaping(unittest.TestCase):
    def test_a_scripted_answer_is_escaped_not_executed(self):
        text = build(
            [a_case()], [an_answer("<script>alert(1)</script>", sample=1)]
        )
        self.assertNotIn("<script>alert", text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", text)


class TestEveryFieldIsEscaped(unittest.TestCase):
    """Hostile text in every field that reaches the page, not only the answer.

    The model id, the case id, the question, the reference, the source and the
    criteria are all written into the HTML; the safety of the page rests on
    each of them being escaped at its own point of use."""

    HOSTILE = '"><img src=x onerror=alert(1)><script>alert(2)</script>'

    def hostile_case(self) -> Case:
        h = self.HOSTILE
        return Case(
            case_id="C" + h,
            category="dose" + h,
            question="Que dose?" + h,
            reference="Amoxicilina 1000 mg" + h,
            source=Source(name="Guia" + h, reference="p. 17" + h),
            criteria=(
                Criterion(kind="contem", terms=("1000 mg" + h,), failure=FailureType.DOSE_INCORRETA,
                          description="descrição" + h),
            ),
        )

    def assert_inert(self, page: str) -> None:
        """Parse the page as a browser would: the hostile text may appear as
        text or inside an attribute value, but never as a tag or an attribute."""
        from html.parser import HTMLParser

        found: list[str] = []

        class Watcher(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag in ("img", "script", "iframe", "object"):
                    found.append(f"<{tag}>")
                found.extend(f"{tag}[{name}]" for name, _ in attrs if name.startswith("on"))

        Watcher().feed(page)
        self.assertEqual(found, [], "the hostile text became markup")

    def test_hostile_case_fields_model_and_answer_are_inert(self):
        case = self.hostile_case()
        answers = [
            an_answer("500 mg" + self.HOSTILE, case_id=case.case_id, model="modelo" + self.HOSTILE, sample=n)
            for n in (1, 2)
        ]
        self.assert_inert(build([case], answers))

    def test_the_language_links_are_escaped_too(self):
        page = build(
            [a_case()], [an_answer("1 g")],
            alternates={"en": '"><img src=x onerror=alert(1)>', "pt": "relatorio.html"},
        )
        self.assert_inert(page)


class TestCaseSummaryNamesTheModels(unittest.TestCase):
    """A closed case is announced with who failed it and how, not only its code and question.

    The coloured circles at the end of each case line used to be hidden from
    assistive technology as a whole, so a screen reader heard which case it was
    but never which models got it wrong."""

    def page(self, **kwargs) -> str:
        answers = [
            an_answer("500 mg", model="falso"),
            an_answer("1 g", model="local:llama3.1:8b"),
        ]
        return build([a_case()], answers, **kwargs)

    def summary(self, text: str) -> str:
        start = text.index('<summary id="caso-C1">')
        return text[start:text.index("</summary>", start)]

    def spoken(self, summary: str) -> str:
        """The summary's text without what is marked aria-hidden, as a reader hears it."""
        import html as _h

        kept = re.sub(r'<span aria-hidden="true">.*?</span>', "", summary)
        return " ".join(_h.unescape(re.sub(r"<[^>]+>", " ", kept)).split())

    def test_the_circles_are_no_longer_hidden_as_a_group(self):
        summary = self.summary(self.page())
        self.assertIn('<span class="minis">', summary)
        self.assertNotIn('class="minis" aria-hidden', summary)

    def test_each_circle_says_the_model_and_its_state_and_hides_only_the_glyph(self):
        summary = self.summary(self.page())
        self.assertIn('<span aria-hidden="true">✕</span><span class="vh">Fornecedor de teste: nunca correto. </span>', summary)
        self.assertIn('<span aria-hidden="true">✓</span><span class="vh">Llama 3.1: sempre correto. </span>', summary)

    def test_what_a_screen_reader_hears_ends_with_every_model_in_circle_order(self):
        spoken = self.spoken(self.summary(self.page()))
        self.assertTrue(
            spoken.endswith("Fornecedor de teste: nunca correto. Llama 3.1: sempre correto."), spoken
        )

    def test_the_mouse_tooltip_is_kept(self):
        self.assertIn('title="Fornecedor de teste: nunca correto"', self.summary(self.page()))

    def test_the_state_is_spoken_in_the_language_of_the_page(self):
        import html as _h
        from aferidor.traducao import LANGS, t

        for lang in LANGS:
            with self.subTest(lingua=lang):
                said = f"{t('Fornecedor de teste', lang)}: {t('nunca correto', lang)}. "
                self.assertIn(f'<span class="vh">{_h.escape(said)}</span>', self.summary(self.page(lingua=lang)))


class TestFullCaseLinkOpensTheCase(unittest.TestCase):
    """"Ver o caso completo" must point inside the case's <details>: that is what makes a
    browser open it. Checked in Brave, Firefox and Safari on 09/10/2026 (see the commit)."""

    def page(self) -> str:
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("Amoxicilina 500 mg", "C1", model="local:llama3.1:8b"),
            an_answer("Amoxicilina 500 mg", "C2", model="local:llama3.1:8b"),
        ]
        return build(cases, answers)

    def targets(self, text: str) -> list[str]:
        worst = text.split('id="erros"', 1)[1].split("</section>", 1)[0]
        return re.findall(r'href="#(corpo-[^"]+)">Ver o caso completo', worst)

    def test_every_link_points_at_an_id_that_exists_exactly_once(self):
        text = self.page()
        targets = self.targets(text)
        self.assertTrue(targets)
        for target in targets:
            with self.subTest(target=target):
                self.assertEqual(text.count(f'id="{target}"'), 1)

    def test_the_target_sits_inside_the_details_after_its_summary(self):
        text = self.page()
        for target in self.targets(text):
            with self.subTest(target=target):
                at = text.index(f'id="{target}"')
                opened = text.rfind("<details>", 0, at)
                closed_before = text.rfind("</details>", 0, at)
                summary_ends = text.rfind("</summary>", 0, at)
                self.assertGreater(opened, closed_before)  # still inside that <details>
                self.assertGreater(summary_ends, opened)  # after its <summary>

    def test_the_summary_keeps_its_old_id_so_shared_links_still_work(self):
        self.assertIn('<summary id="caso-C1">', self.page())

    def test_the_body_leaves_room_for_the_fixed_bar_and_the_summary(self):
        """The bar is cleared by the page's scroll padding (its height is `--barra`); the body
        only has to leave room for its own summary above it."""
        self.assertIn("scroll-padding-top: var(--barra)", html_estilo.STYLE)
        self.assertIn(
            ".detalhe-corpo { padding: 0.9rem 1rem 1rem; border-top: 1px solid var(--grid); scroll-margin-top: 3.5rem; }",
            html_estilo.STYLE,
        )


class TestPreviewAndRepositoryLink(unittest.TestCase):
    """What a pasted link shows, and the way back to the project."""

    LINK_TEXT = "Código, método e casos no GitHub"

    def page(self, **kwargs) -> str:
        return build([a_case()], [an_answer("1 g")], **kwargs)

    def meta(self, text: str) -> dict[str, str]:
        import html as _h

        head = text[: text.index("</head>")]
        found = re.findall(r'<meta (?:name|property)="([^"]+)" content="([^"]*)">', head)
        return {name: _h.unescape(content) for name, content in found}

    def test_the_head_carries_a_description_and_the_open_graph_tags(self):
        meta = self.meta(self.page())
        self.assertEqual(meta["og:type"], "website")
        self.assertEqual(meta["og:title"], "Relatório do Aferidor")
        self.assertEqual(meta["description"], meta["og:description"])
        self.assertIn("Respostas clínicas de modelos de linguagem", meta["og:description"])
        self.assertEqual(meta["og:locale"], "pt_PT")
        self.assertEqual(meta["og:image"], html_report.PREVIEW_IMAGE_URL)
        self.assertEqual((meta["og:image:width"], meta["og:image:height"]), ("1327", "896"))
        self.assertIn("falha crítica", meta["og:image:alt"])

    def test_there_is_no_og_url_because_a_local_report_does_not_know_its_address(self):
        self.assertNotIn("og:url", self.page())

    def test_the_tags_follow_the_language_of_the_page(self):
        from aferidor.traducao import LANGS, OG_LOCALE, t

        subtitle = "Respostas clínicas de modelos de linguagem, medidas contra casos de referência com fonte pública."
        for lang in LANGS:
            with self.subTest(lingua=lang):
                meta = self.meta(self.page(lingua=lang))
                self.assertEqual(meta["og:locale"], OG_LOCALE[lang])
                self.assertEqual(meta["og:title"], t("Relatório do Aferidor", lang))
                self.assertEqual(meta["og:description"], t(subtitle, lang))

    def test_the_link_to_the_project_is_in_the_method_page_and_in_the_footer(self):
        """Not on the first page, which has a word budget: whoever wants the code finds it where the
        method is, and at the foot of every page."""
        text = self.page()
        link = f'<a href="{html_report.REPO_URL}" rel="noopener">{self.LINK_TEXT}</a>'
        self.assertEqual(text.count(link), 2)
        first = text[text.index('<section class="painel" id="inicio"'):text.index('<section class="painel" id="sobre"')]
        self.assertNotIn(link, first)
        method = text[text.index('<section class="painel" id="metodo"'):text.index("</main>")]
        self.assertIn(link, method)
        self.assertIn(link, text[text.index('<footer class="rodape">'):])

    def test_the_link_text_follows_the_language_of_the_page(self):
        from aferidor.traducao import LANGS, t

        for lang in LANGS:
            with self.subTest(lingua=lang):
                self.assertIn(f'rel="noopener">{t(self.LINK_TEXT, lang)}</a>', self.page(lingua=lang))


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
        results = text[text.index('<section class="painel" id="resultados"'):text.index('<section class="painel" id="areas"')]
        self.assertIn('id="limiar-referencia"', results)

    def test_with_a_protocol_nothing_about_the_reference_appears(self):
        import json
        import tempfile
        from pathlib import Path

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
        first = text[text.index('<section class="painel" id="inicio"'):text.index('<section class="painel" id="sobre"')]
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


class TestHeadline(unittest.TestCase):
    def test_the_critical_case_count_is_shown_per_model(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn('<span class="destaque">1</span>', text)
        self.assertIn("de 1 casos com falha crítica em alguma amostra", visible(text))


PAGES = ("inicio", "sobre", "fontes", "resultados", "areas", "casos", "conclusoes", "metodo")


def navigation(text: str) -> list[str]:
    nav = re.search(r'<nav class="indice".*?</nav>', text, flags=re.S).group(0)
    return re.findall(r'href="#([^"]+)"', nav)


def panels(text: str) -> list[str]:
    return re.findall(r'<section class="painel" id="([^"]+)"', text)


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


class TestGrid(unittest.TestCase):
    def test_cases_are_grouped_by_category(self):
        cases = [a_case("C1", category="dose"), a_case("C2", category="interacao")]
        text = build(cases, [an_answer("500 mg", case_id="C1"), an_answer("500 mg", case_id="C2")])
        self.assertIn(">Dose<", text)
        self.assertIn(">Interações<", text)

    def test_the_grid_shows_failing_cases_and_lists_the_rest_collapsed(self):
        cases = [a_case("C1"), a_case("C2")]
        text = build(cases, [an_answer("500 mg", case_id="C1"), an_answer("1 g", case_id="C2")])
        grid = text[text.index('id="grelha"'):text.index('id="casos-com-falha"')]
        self.assertIn("C1", grid[:grid.index("<details")])
        self.assertIn("1 caso sempre correto em todos os modelos", grid)

    def test_the_state_is_written_out_not_just_shown_in_colour(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("nunca correto", text)

    def test_a_stable_pass_says_so(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertIn("sempre correto", text)

    def test_a_mixed_result_across_samples_is_unstable(self):
        text = build(
            [a_case()],
            [an_answer("1 g", sample=1), an_answer("500 mg", sample=2)],
        )
        self.assertIn("parcialmente correto", text)

    def test_a_case_never_asked_to_a_model_says_so(self):
        cases = [a_case("C1"), a_case("C2")]
        text = build(cases, [an_answer("1 g", case_id="C1")], missing=["C2"])
        self.assertIn("sem resposta", text)

    def test_a_known_reason_is_shown_next_to_the_case(self):
        cases = [a_case("C1"), a_case("C2")]
        text = build(
            cases, [an_answer("1 g", case_id="C1")],
            missing=["C2"], reasons={"C2": "resposta truncada no limite de tokens"},
        )
        self.assertIn("C2 (resposta truncada no limite de tokens)", text)


class TestHowItIsCounted(unittest.TestCase):
    """The report's own words for a case's samples, and the one verdict per case."""

    def test_each_sample_is_a_dot_in_the_order_it_was_asked(self):
        text = build(
            [a_case()],
            [an_answer("1 g", sample=1), an_answer("500 mg", sample=2), an_answer("1 g", sample=3)],
        )
        self.assertIn('aria-label="Amostras: 1 correta, 2 incorreta, 3 correta"', text)

    def test_a_sample_never_answered_is_a_dot_of_its_own(self):
        answers = [an_answer("1 g", sample=1), an_answer("1 g", sample=3)]
        text = build([a_case()], answers)
        self.assertIn("2 sem resposta", text)

    def test_the_page_explains_the_states_and_that_never_right_is_not_critical(self):
        text = build([a_case()], [an_answer("1 g", sample=1), an_answer("500 mg", sample=2)])
        self.assertIn('id="como-se-conta"', text)
        self.assertIn("Um caso nunca correto não tem necessariamente", text)
        for state in ("sempre correto", "parcialmente correto", "nunca correto"):
            with self.subTest(state=state):
                self.assertIn(f'data-termo="{state}"', text)

    def test_the_card_counts_right_cases_by_the_rule_and_names_the_rule(self):
        text = build([a_case()], [an_answer("1 g", sample=1), an_answer("500 mg", sample=2)])
        self.assertIn("Casos corretos: 0 de 1", visible(text))
        self.assertIn("um caso é correto quando todas as amostras são corretas", visible(text))

    def test_the_card_says_answers_are_cases_times_attempts(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [an_answer("1 g", case_id=c, sample=s) for c in ("C1", "C2") for s in (1, 2, 3)]
        text = build(cases, answers)
        self.assertIn("Respostas corretas: 6 de 6", visible(text))
        self.assertIn("casos × amostras", text)


class TestMissingSamples(unittest.TestCase):
    def test_a_partial_case_is_named_with_how_many_samples_came_in(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = (
            [an_answer("1 g", case_id="C1", model="qwen", sample=s) for s in (1, 2, 3)]
            + [an_answer("1 g", case_id="C2", model="qwen", sample=s) for s in range(1, 6)]
        )
        text = build(cases, answers)
        self.assertIn("Amostras em falta", text)
        self.assertIn("C1 (qwen, 3 de 5 amostras)", text)

    def test_no_gaps_means_no_section(self):
        text = build([a_case("C1")], [an_answer("1 g", case_id="C1")])
        self.assertNotIn("Amostras em falta", text)


class TestDetail(unittest.TestCase):
    def test_a_failed_case_gets_a_details_block(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("<details>", text)
        self.assertIn("Que dose de amoxicilina?", text)
        self.assertIn("Amoxicilina 1000 mg de 8/8h", text)
        self.assertIn("Guia ATB", text)

    def test_a_passing_case_gets_no_details_block(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertNotIn("<details>", text)

    def test_each_distinct_answer_appears_once(self):
        text = build(
            [a_case()],
            [
                an_answer("500 mg", sample=1),
                an_answer("500 mg", sample=2),
                an_answer("600 mg", sample=3),
            ],
        )
        detail = text.split('id="casos-com-falha"', 1)[1]
        self.assertEqual(detail.count("500 mg"), 1)
        self.assertIn("600 mg", detail)


class TestNumbersMatchMarkdown(unittest.TestCase):
    def test_the_same_verdicts_give_the_same_counts_in_both_formats(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("1 g", case_id="C1", sample=1),
            an_answer("500 mg", case_id="C1", sample=2),
            an_answer("500 mg", case_id="C2", sample=1),
        ]
        verdicts, missing = grade_all(cases, answers)
        markdown = report.build(cases, answers, verdicts, missing=missing, today=date(2026, 9, 14))
        page = html_report.build(cases, answers, verdicts, missing=missing, today=date(2026, 9, 14))

        consistency = consistency_by_case(cases, answers, verdicts)
        summary = consistency_by_model(consistency)["falso"]

        self.assertIn(f"{summary.critical_cases} de {summary.cases} casos", markdown)
        self.assertIn(f'<span class="destaque">{summary.critical_cases}</span>', page)
        self.assertIn(f"de {summary.cases} casos com falha crítica em alguma amostra", visible(page))


class TestReadableByAnOutsider(unittest.TestCase):
    """The page has to say what it is before it shows a number."""

    def test_it_opens_by_saying_what_the_aferidor_is_why_it_exists_and_what_it_aims_at(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        first = visible(text[text.index('<section class="painel" id="inicio"'):text.index('<section class="painel" id="sobre"')])
        self.assertIn("Um médico pode perguntar a um destes assistentes", first)
        self.assertIn('<a href="#sobre">Saber mais sobre o Aferidor.</a>', text)
        self.assertNotIn("Objetivos.", first)  # the aims moved to the About page
        self.assertLess(first.index("Um médico pode perguntar"), first.index("Saber mais sobre o Aferidor."))
        self.assertLess(first.index("Saber mais"), first.index("Modelos que cumprem"))
        self.assertLess(text.index('id="inicio"'), text.index('<span class="destaque">'))

    def test_how_to_read_it_is_in_the_method_page_closed(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        method = text[text.index('<section class="painel" id="metodo"'):text.index("</main>")]
        self.assertRegex(method, r'<details class="recolhe ler" id="como-ler">\s*<summary>Como interpretar este relatório</summary>')
        self.assertNotIn("Como interpretar este relatório", text[:text.index('<section class="painel" id="metodo"')])

    def test_every_section_is_reachable_from_the_index(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        for anchor in ("inicio", "fontes", "resultados", "areas", "casos", "conclusoes", "metodo"):
            with self.subTest(anchor=anchor):
                self.assertIn(f'href="#{anchor}"', text)
                self.assertIn(f'id="{anchor}"', text)

    def test_a_state_is_never_shown_by_colour_alone(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        self.assertRegex(text, r'✕ <abbr class="termo"[^>]*>nunca correto</abbr>')

    def test_the_first_screen_says_the_verdicts_are_triage_for_a_specialist(self):
        text = build([a_case()], [an_answer("1 g")])
        first = text[text.index('<section class="painel" id="inicio"'):text.index('<section class="painel" id="sobre"')]
        self.assertIn("Os veredictos são triagem automática, ainda sem validação por especialista", visible(first))
        self.assertIn("triagem automática do corretor", visible(text[:text.index("<main>")]))  # and the bar says it too

    def test_the_index_only_links_sections_that_exist(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertNotIn('href="#erros"', text)
        self.assertNotIn('id="erros"', text)
        for anchor in re.findall(r'<nav class="indice".*?</nav>', text, flags=re.S)[0].split('href="#')[1:]:
            with self.subTest(anchor=anchor[:12]):
                self.assertIn(f'id="{anchor.split(chr(34))[0]}"', text)

    def test_failure_charts_share_one_scale_across_models(self):
        """Two charts on their own scales make a smaller count look as long as a bigger one."""
        answers = [an_answer("Amoxicilina 500 mg", model="a"), an_answer("nada", model="b")]
        extra = [an_answer("Amoxicilina 500 mg", case_id="C2", model="a")]
        text = build([a_case("C1"), a_case("C2")], answers + extra)
        self.assertIn("calc(2 / 2 * 100%)", text)
        self.assertIn("calc(1 / 2 * 100%)", text)


class TestModelNames(unittest.TestCase):
    """An identifier such as local:llama3.1:8b means nothing to most readers."""

    def test_known_models_get_a_readable_name_and_a_description(self):
        from aferidor.html_report import model_label

        self.assertEqual(
            model_label("local:llama3.1:8b"),
            ("Llama 3.1", "Meta · 8 mil milhões de parâmetros · executado localmente através do Ollama"),
        )
        self.assertEqual(model_label("anthropic:claude-sonnet-4-5")[0], "Claude Sonnet 4.5")
        self.assertEqual(model_label("openai:gpt-4o")[0], "GPT-4o")
        self.assertEqual(model_label("gemini:gemini-3.5-flash-lite"), ("Gemini 3.5 Flash Lite", "Google · acedido por API"))

    def test_two_models_with_the_same_name_are_told_apart(self):
        from aferidor.html_report import unique_names

        names = unique_names(["local:llama3.1:8b", "local:llama3.1:70b", "local:qwen3:8b"])
        self.assertEqual(names["local:llama3.1:8b"], "Llama 3.1 (8b)")
        self.assertEqual(names["local:llama3.1:70b"], "Llama 3.1 (70b)")
        self.assertEqual(names["local:qwen3:8b"], "Qwen 3")

    def test_a_release_date_is_not_part_of_the_name(self):
        from aferidor.html_report import model_label

        self.assertEqual(model_label("anthropic:claude-sonnet-4-5-20250929")[0], "Claude Sonnet 4.5")

    def test_an_unknown_model_is_shown_by_its_identifier_not_guessed(self):
        from aferidor.html_report import model_label

        self.assertEqual(model_label("xpto-9"), ("xpto-9", ""))

    def test_the_identifier_is_always_shown_next_to_the_name(self):
        text = build([a_case()], [an_answer("1 g", model="local:qwen3:8b")])
        self.assertIn("Qwen 3", text)
        self.assertIn('<code class="modelo-id">local:qwen3:8b</code>', text)


class TestWhatJumpsOut(unittest.TestCase):
    """Areas, a direct comparison, the gravest mistakes and the models' context."""

    def two_models(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("Amoxicilina 500 mg", "C1", model="local:llama3.1:8b"),
            an_answer("Amoxicilina 500 mg", "C2", model="local:llama3.1:8b"),
            an_answer("Amoxicilina 1 g", "C1", model="local:qwen3:8b"),
            an_answer("Amoxicilina 500 mg", "C2", model="local:qwen3:8b"),
        ]
        return build(cases, answers)

    def test_critical_cases_are_shown_by_clinical_area(self):
        text = self.two_models()
        self.assertIn('id="areas"', text)
        self.assertIn("<th scope=\"row\">Dose</th>", text)
        self.assertIn("<strong>2</strong> de 2", text)

    def test_the_comparison_names_the_better_model_and_says_when_it_can_be_chance(self):
        text = self.two_models()
        self.assertIn("<strong>Qwen 3</strong> teve menos casos com falha crítica (1 de 2, contra 2 de 2", text)
        self.assertIn("a diferença pode dever-se ao acaso", text)

    def test_the_gravest_mistakes_are_highlighted_with_what_should_have_been_said(self):
        text = self.two_models()
        worst = text.split('id="erros"', 1)[1].split("</section>", 1)[0]
        self.assertIn("A referência diz", worst)
        self.assertIn("Dose incorreta", worst)
        self.assertIn('href="#corpo-C1"', worst)
        self.assertIn('id="corpo-C1"', text)
        self.assertIn('id="caso-C1"', text)  # the summary keeps its id, for links already shared

    def test_local_models_are_not_taken_for_the_commercial_ones(self):
        text = visible(self.two_models())
        self.assertIn("Que os modelos locais representem os comerciais.", text)
        self.assertNotIn("pequena dimensão", text)  # nothing is said about their size that was not checked

    def test_models_not_run_locally_get_no_such_line(self):
        text = build([a_case()], [an_answer("1 g", model="openai:gpt-4o")])
        self.assertNotIn("Que os modelos locais representem os comerciais.", text)


class TestGlossary(unittest.TestCase):
    """Abbreviations explained on hover, and a glossary of the ones used."""

    def page(self, answer_text="Amoxicilina 500 mg na DPOC"):
        case = Case(
            case_id="C1", category="dose",
            question="Exacerbação de DPOC: que dose? Ver no mapa da consulta.",
            reference="Amoxicilina 1000 mg de 8/8h", source=Source(name="DGS", reference="Norma"),
            criteria=(Criterion(kind="contem", terms=("1000 mg",), failure=FailureType.DOSE_INCORRETA),),
        )
        return build([case], [an_answer(answer_text)])

    def test_an_abbreviation_in_a_question_is_marked_with_its_definition(self):
        text = self.page()
        self.assertIn('data-termo="DPOC"', text)
        self.assertIn("Doença pulmonar obstrutiva crónica", text)

    def test_the_model_answer_is_never_marked(self):
        text = self.page()
        self.assertIn("<blockquote lang=\"pt-PT\">Amoxicilina 500 mg na DPOC</blockquote>", text)

    def test_a_lowercase_word_is_not_taken_for_an_abbreviation(self):
        self.assertNotIn('data-termo="MAPA"', self.page())

    def test_the_glossary_lists_only_the_terms_the_page_uses(self):
        text = self.page()
        glossary = text.split('id="glossario"', 1)[1].split("</details>", 1)[0]
        self.assertIn(">DPOC</dt>", glossary)
        self.assertNotIn(">HbA1c</dt>", glossary)

    def test_every_marked_term_points_to_its_glossary_entry(self):
        import re

        text = self.page()
        for target in re.findall(r'aria-describedby="([^"]+)"', text):
            with self.subTest(target=target):
                self.assertIn(f'id="{target}"', text)


class TestCaseCodes(unittest.TestCase):
    def test_a_case_code_is_spelled_out(self):
        from aferidor.html_report import case_code_meaning

        self.assertEqual(
            case_code_meaning("ATB-PAC-001"),
            "Antibioterapia · Pneumonia adquirida na comunidade · caso n.º 1",
        )
        self.assertEqual(case_code_meaning("TAB-03"), "Cessação tabágica · caso n.º 3")

    def test_an_unknown_part_is_left_as_it_is(self):
        from aferidor.html_report import case_code_meaning

        self.assertEqual(case_code_meaning("XYZ-9"), "XYZ · caso n.º 9")

    def test_every_case_code_in_the_banks_is_fully_spelled_out(self):
        from aferidor.html_report import case_code_meaning
        from aferidor.storage import read_cases

        root = Path(__file__).resolve().parent.parent / "casos"
        for case in read_cases(root / "casos.json") + read_cases(root / "consulta.json"):
            with self.subTest(case=case.case_id):
                for part in case_code_meaning(case.case_id).split(" · "):
                    self.assertNotIn(part, case.case_id.split("-"))

    def test_codes_carry_their_meaning_on_the_page_and_the_glossary_explains_them(self):
        text = build([a_case("ATB-PAC-001")], [an_answer("Amoxicilina 500 mg", case_id="ATB-PAC-001")])
        self.assertIn('data-def="Antibioterapia · Pneumonia adquirida na comunidade · caso n.º 1"', text)
        self.assertIn(">Código do caso</dt>", text)


class TestEmpty(unittest.TestCase):
    def test_no_verdicts_says_so_instead_of_reporting_zero_percent(self):
        text = html_report.build([a_case()], [], [], today=date(2026, 9, 14))
        body = text.split("<body>", 1)[1]
        self.assertIn("Não há veredictos", body)
        self.assertNotIn("0%", body)


def tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-f]{6})", block))


def contrast(fg: str, bg: str) -> float:
    """WCAG 2.1 contrast ratio between two #rrggbb colours."""
    def luminance(colour: str) -> float:
        channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    high, low = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (high + 0.05) / (low + 0.05)


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


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------- the first page and its word budget

import json as _json
import tempfile as _tempfile
from html.parser import HTMLParser as _HTMLParser
from unittest import mock as _mock

from aferidor import report as _report
from aferidor.protocolo import read_protocol as _read_protocol, template as _template
from aferidor.storage import read_answers as _read_answers, read_cases as _read_cases

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_TRIALS = ("2026-09-29-gemma4-31b-casos", "2026-09-28-gemini-flash", "2026-09-27-locais-12-14b")

# The most words of interface text each page may carry in Portuguese. A page is read in seconds;
# a sentence that grows past this has to say why, here, in a commit.
FIRST_PAGE_WORDS = {"reference": 148, "review_done": 143, "protocol": 157}
ABOUT_PAGE_WORDS = 270
FRAME_WORDS = 60
TRANSLATION_NOTICE_WORDS = 20


def words(text: str) -> int:
    """Words as the budget counts them: runs of characters between spaces that hold a letter or a digit."""
    return len([w for w in text.split() if re.search(r"\w", w)])


class _PanelText(_HTMLParser):
    """The text of one panel as a reader sees it, without what is data or a component.

    Left out: the cases and answers (`lang="pt-PT"`), blockquotes, code, whatever is only for screen
    readers (`.vh`), the cards, charts and tables, and the inside of a closed <details> (its
    <summary> counts). A paragraph written later counts by default: this is an exclusion list.
    """

    SKIP_TAGS = {"blockquote", "code", "style", "script", "table"}
    SKIP_CLASSES = {"vh", "cartoes", "comparacao", "legenda-estados", "legenda-riscos", "falhas-grelha", "grade-wrap"}
    VOID = {"br", "hr", "img", "input", "meta", "link"}

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.skip_from: list[int] = []
        self.details: list[int] = []
        self.in_summary = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        self.depth += 1
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        if tag in self.SKIP_TAGS or a.get("lang") == "pt-PT" or classes & self.SKIP_CLASSES:
            self.skip_from.append(self.depth)
        if tag == "details":
            self.details.append(self.depth)
        if tag == "summary":
            self.in_summary += 1

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if self.skip_from and self.skip_from[-1] == self.depth:
            self.skip_from.pop()
        if self.details and self.details[-1] == self.depth:
            self.details.pop()
        if tag == "summary":
            self.in_summary -= 1
        self.depth -= 1

    def handle_data(self, data):
        if self.skip_from:
            return
        if self.details and not self.in_summary:
            return
        self.parts.append(data)


def panel_text(page: str, ident: str) -> str:
    start = page.index(f'<section class="painel" id="{ident}"')
    following = [i for i in (page.find('<section class="painel" id="', start + 10), page.find("</main>", start)) if i > 0]
    parser = _PanelText()
    parser.feed(page[start:min(following)])
    return " ".join(" ".join(parser.parts).split())


def element_text(page: str, css_class: str) -> str:
    """The visible text of the element with this class, on the first page."""
    first = page[page.index('<section class="painel" id="inicio"'):page.index('<section class="painel" id="sobre"')]
    at = first.index(f'class="{css_class}"')
    start = first.rindex("<", 0, at)
    tag = re.match(r"<(\w+)", first[start:]).group(1)
    depth, i = 0, start
    for m in re.finditer(rf"</?{tag}\b[^>]*>", first[start:]):
        depth += -1 if m.group(0).startswith("</") else 1
        if depth == 0:
            i = start + m.end()
            break
    parser = _PanelText()
    parser.feed(first[start:i])
    return " ".join(" ".join(parser.parts).split())


class _Example:
    """The public example: the real bank and the answers of the three trials it is made from."""

    _cache: dict = {}

    @classmethod
    def data(cls):
        if not cls._cache:
            cases = _read_cases(ROOT / "casos" / "casos.json")
            answers = [a for name in EXAMPLE_TRIALS for a in _read_answers(ROOT / "ensaios" / name / "respostas.jsonl")]
            verdicts, missing = grade_all(cases, answers)
            cls._cache.update(cases=cases, answers=answers, verdicts=verdicts, missing=missing)
        return cls._cache

    @staticmethod
    def bank_sha256() -> str:
        import hashlib

        return hashlib.sha256((ROOT / "casos" / "casos.json").read_bytes()).hexdigest()

    @classmethod
    def page(cls, **kwargs) -> str:
        from aferidor import fontes

        d = cls.data()
        kwargs.setdefault(
            "confirmation", fontes.read_confirmation(ROOT / "casos" / "casos.json", [c.case_id for c in d["cases"]])
        )
        return html_report.build(
            d["cases"], d["answers"], d["verdicts"], missing=d["missing"], today=date(2026, 10, 10),
            cases_source=("casos/casos.json", cls.bank_sha256()), **kwargs,
        )

    @classmethod
    def protocol(cls, written_on: date | None = None):
        """A protocol for this bank. With a date before the first answer and the bank's own hash it
        raises no warning; the real one of 29/09 raises two with these answers."""
        if written_on is None:
            return _read_protocol(ROOT / "protocolos" / "2026-09-29-gemma4-31b-casos.json")
        with _tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.json"
            path.write_text(_json.dumps(_template("x", ROOT / "casos" / "casos.json", today=written_on)), encoding="utf-8")
            return _read_protocol(path)


def example_page_of(models: tuple[str, ...], **kwargs) -> str:
    """The example with only the answers of these models, for pages with two or one."""
    from aferidor import fontes

    d = _Example.data()
    answers = [a for a in d["answers"] if a.model in models]
    verdicts, missing = grade_all(d["cases"], answers)
    kwargs.setdefault(
        "confirmation", fontes.read_confirmation(ROOT / "casos" / "casos.json", [c.case_id for c in d["cases"]])
    )
    return html_report.build(
        d["cases"], answers, verdicts, missing=missing, today=date(2026, 10, 10),
        cases_source=("casos/casos.json", _Example.bank_sha256()), **kwargs,
    )


class _ConsultationExample:
    """The consultation bank with the answers of the trial that asked it, for the page with ten sources."""

    _cache: dict = {}

    @classmethod
    def page(cls, **kwargs) -> str:
        from aferidor import fontes

        if not cls._cache:
            cases = _read_cases(ROOT / "casos" / "consulta.json")
            answers = _read_answers(ROOT / "ensaios" / "2026-09-29-gemini-consulta" / "respostas.jsonl")
            verdicts, missing = grade_all(cases, answers)
            cls._cache.update(cases=cases, answers=answers, verdicts=verdicts, missing=missing)
        d = cls._cache
        kwargs.setdefault(
            "confirmation", fontes.read_confirmation(ROOT / "casos" / "consulta.json", [c.case_id for c in d["cases"]])
        )
        return html_report.build(
            d["cases"], d["answers"], d["verdicts"], missing=d["missing"], today=date(2026, 10, 10),
            cases_source=("casos/consulta.json", ""), **kwargs,
        )


SOURCES_PAGE_WORDS = 100


class TestFirstPageWordBudget(unittest.TestCase):
    """The first page is read in seconds, so it has a word budget, counted per element."""

    ELEMENTS = ("subtitulo", "porque", "saber-mais", "factos", "resultado", "triagem")

    def breakdown(self, page: str) -> str:
        title = words(re.search(r'<h1[^>]*>(.*?)</h1>', page).group(1))
        counts = {name: words(element_text(page, name)) for name in self.ELEMENTS}
        if 'class="remate"' in page:
            counts["remate"] = words(element_text(page, "remate"))
        return f"título {title}, " + ", ".join(f"{k} {v}" for k, v in counts.items())

    def total(self, page: str) -> int:
        return words(panel_text(page, "inicio"))

    def test_the_reference_version_fits_its_budget(self):
        page = _Example.page()
        self.assertLessEqual(self.total(page), FIRST_PAGE_WORDS["reference"], self.breakdown(page))

    def test_the_version_with_the_review_done_fits_its_budget(self):
        with _mock.patch.object(_report, "CLINICAL_REVIEW_DONE", True):
            page = _Example.page()
        self.assertLessEqual(self.total(page), FIRST_PAGE_WORDS["review_done"], self.breakdown(page))

    def test_the_versions_with_a_protocol_fit_theirs_with_and_without_the_warnings_pointer(self):
        for label, protocol in (("com avisos", _Example.protocol()), ("sem avisos", _Example.protocol(date(2020, 1, 1)))):
            with self.subTest(protocolo=label):
                page = _Example.page(protocol=protocol)
                self.assertLessEqual(self.total(page), FIRST_PAGE_WORDS["protocol"], self.breakdown(page))

    def test_every_element_of_the_first_page_is_there_in_reading_order(self):
        page = _Example.page()
        first = page[page.index('<section class="painel" id="inicio"'):page.index('<section class="painel" id="sobre"')]
        order = [first.index(f'class="{c}"') for c in ("porque", "saber-mais", "factos", "resultado", "triagem")]
        self.assertEqual(order, sorted(order))
        self.assertLess(first.index("<h1"), order[0])

    def test_the_frame_in_portuguese_fits_its_budget(self):
        """The bar, the footer: the same on every page, in the language of the report. The notice about
        a machine translation is not in this count, because Portuguese never shows it."""
        page = _Example.page()
        bar = re.search(r'<p class="faixa"[^>]*>(.*?)</p>', page, flags=re.S).group(1)
        footer = page[page.index('<footer class="rodape">'):page.index("</footer>")]
        total = words(visible(bar)) + words(visible(footer))
        self.assertLessEqual(total, FRAME_WORDS)
        self.assertNotIn('class="traducao"', page)

    def test_the_translation_notice_is_one_short_sentence_in_every_language_that_shows_it(self):
        from aferidor.traducao import UNREVIEWED, UNREVIEWED_NOTICE, t

        for lang in UNREVIEWED:
            with self.subTest(lingua=lang):
                notice = t(UNREVIEWED_NOTICE, lang)
                self.assertLessEqual(words(notice), TRANSLATION_NOTICE_WORDS)
                self.assertEqual(len(re.findall(r"[.!?](?=\s|$)", notice)), 1)
                self.assertTrue(notice.rstrip().endswith("."))


class TestFirstPageVariants(unittest.TestCase):
    """What the first page says without a protocol, with one, and once a specialist has reviewed."""

    def test_without_a_protocol_the_reference_threshold_is_defined_and_the_best_result_given(self):
        text = visible(panel_text(_Example.page(), "inicio"))
        self.assertIn("Modelos que cumprem o limiar de referência (nenhum caso com falha crítica): 0 de 4.", text)
        self.assertRegex(text, r"Melhor resultado: \d+ de 27 casos com falha crítica\.")
        self.assertNotIn("aprovados pelo protocolo", text)

    def test_with_a_protocol_the_result_names_all_four_conditions_it_applied(self):
        text = visible(panel_text(_Example.page(protocol=_Example.protocol(date(2020, 1, 1))), "inicio"))
        self.assertIn(
            "Modelos aprovados pelo protocolo (todos os casos e amostras respondidos, nenhum caso com falha "
            "crítica, nenhum parcialmente correto, pelo menos 95% de amostras corretas): 0 de 4.",
            text,
        )
        self.assertNotIn("Melhor resultado", text)
        self.assertNotIn("limiar de referência", text)

    def test_the_conditions_are_read_from_the_protocol_and_a_limit_above_zero_says_at_most(self):
        protocol = _Example.protocol(date(2020, 1, 1))
        from dataclasses import replace

        looser = replace(protocol, max_critical_cases=3, max_unstable_cases=2, min_sample_accuracy=0.9)
        text = visible(panel_text(_Example.page(protocol=looser), "inicio"))
        self.assertIn("no máximo 3 casos com falha crítica", text)
        self.assertIn("no máximo 2 parcialmente corretos", text)
        self.assertIn("pelo menos 90% de amostras corretas", text)

    def test_a_protocol_with_warnings_points_at_the_method_page_and_one_without_says_nothing(self):
        with_warnings = _Example.page(protocol=_Example.protocol())
        first = with_warnings[with_warnings.index('<section class="painel" id="inicio"'):with_warnings.index('<section class="painel" id="sobre"')]
        self.assertIn('<p class="remate">O protocolo tem avisos (ver <a href="#criterio">Método</a>).</p>', first)
        self.assertIn('id="criterio"', with_warnings[with_warnings.index('<section class="painel" id="metodo"'):])
        without = _Example.page(protocol=_Example.protocol(date(2020, 1, 1)))
        self.assertNotIn("O protocolo tem avisos", without)

    def test_the_review_sentence_is_true_while_there_is_no_reviewer(self):
        text = visible(panel_text(_Example.page(), "inicio"))
        self.assertIn("ainda sem validação por especialista: a folha cega está pronta, mas ainda não há revisor.", text)

    def test_once_the_review_is_done_the_sentence_stops_saying_there_is_no_reviewer_and_claims_nothing_else(self):
        with _mock.patch.object(_report, "CLINICAL_REVIEW_DONE", True):
            text = visible(panel_text(_Example.page(), "inicio"))
        self.assertNotIn("não há revisor", text)
        self.assertNotIn("ainda sem validação", text)
        self.assertIn("Os veredictos são triagem automática; a validação por especialista faz-se à parte, numa folha cega.", text)
        for invented in ("concordância", "kappa", "revisão por", "foi validad", "validados"):
            self.assertNotIn(invented, text)

    def test_every_variant_is_in_every_language(self):
        from aferidor.traducao import LANGS

        for lang in LANGS:
            with self.subTest(lingua=lang):
                for protocol in (None, _Example.protocol(date(2020, 1, 1)), _Example.protocol()):
                    page = _Example.page(lingua=lang, protocol=protocol)
                    self.assertIn('class="resultado"', page)
                with _mock.patch.object(_report, "CLINICAL_REVIEW_DONE", True):
                    self.assertIn('class="triagem"', _Example.page(lingua=lang))


class TestClinicalReviewFlagIsRecorded(unittest.TestCase):
    """CLINICAL_REVIEW_DONE is one constant. The README says the same thing in words, and the
    notebook (BRIEFING.md, which is not in the repository) records it, so it is not forgotten."""

    def test_the_readme_says_there_is_no_reviewer_exactly_while_the_constant_is_false(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        says_so = "ainda não tem revisor" in readme
        self.assertEqual(
            says_so, not _report.CLINICAL_REVIEW_DONE,
            "O README e CLINICAL_REVIEW_DONE (aferidor/report.py) têm de dizer o mesmo sobre a revisão clínica: "
            "se mudaste a constante, muda a frase do README no mesmo commit.",
        )

    @unittest.skipUnless((ROOT / "BRIEFING.md").exists(), "BRIEFING.md não está no repositório")
    def test_the_notebook_records_the_constant(self):
        notebook = (ROOT / "BRIEFING.md").read_text(encoding="utf-8")
        self.assertIn(
            "CLINICAL_REVIEW_DONE", notebook,
            "Falta no BRIEFING.md, nas decisões em aberto, uma linha a registar CLINICAL_REVIEW_DONE "
            "(aferidor/report.py): quando houver revisor, muda a constante e o relatório precisa de saber de que revisão se trata.",
        )


class TestSourcesPage(unittest.TestCase):
    """Which sources the cases cite, and how far they are confirmed, read from VERIFICACAO.md by id."""

    def text(self, page: str) -> str:
        return visible(panel_text(page, "fontes"))

    def test_the_main_bank_says_which_sources_and_the_three_counts(self):
        text = self.text(_Example.page())
        self.assertIn("Casos que citam cada fonte: DGS 16, RCM 8, APMGF 5, Infarmed 4, EMA 3.", text)
        self.assertIn("Estado da confirmação segundo em 2026-10-10:", text.replace("casos/VERIFICACAO.md ", ""))
        self.assertIn(
            "Neste banco (27 casos), confirmadas por uma pessoa, uma a uma, nos documentos: 9; "
            "declaradas confirmadas em grupo, sem registo de página: 11; por confirmar: 7.", text,
        )
        self.assertIn("No projeto (58 casos), pela mesma ordem: 10, 24 e 24.", text)

    def test_the_consultation_bank_has_its_own_numbers_and_the_project_the_same_ones(self):
        text = self.text(_ConsultationExample.page())
        self.assertIn("Neste banco (31 casos)", text)
        self.assertIn("uma a uma, nos documentos: 1; declaradas confirmadas em grupo, sem registo de página: 13; por confirmar: 17.", text)
        self.assertIn("No projeto (58 casos), pela mesma ordem: 10, 24 e 24.", text)

    def test_more_than_five_sources_name_the_first_five_and_say_how_many_and_how_many_cases_are_left_out(self):
        text = self.text(_ConsultationExample.page())
        self.assertIn("DGS 9, ESC 7, Infarmed 7, RCM 7, NICE 5; outras fontes: 5 (lista completa no Método); "
                      "casos que não citam nenhuma destas: 6.", text)
        self.assertNotIn("ADA 3", text)

    def test_the_full_list_is_in_the_method_page_closed_and_the_link_reaches_it(self):
        page = _ConsultationExample.page()
        method = page[page.index('<section class="painel" id="metodo"'):page.index("</main>")]
        self.assertEqual(page.count('id="fontes-por-organismo"'), 1)
        self.assertIn('id="fontes-por-organismo"', method)
        at = method.index('id="fontes-por-organismo"')
        opened = method.rfind("<details", 0, at)
        self.assertGreater(opened, method.rfind("</details>", 0, at))  # the target sits inside a <details>
        self.assertIn("<summary>Fontes por organismo</summary>", method[opened:at])
        self.assertNotIn(" open", method[opened:at])  # closed
        for body in ("ADA", "EMA", "FDA", "PNV", "SNS"):
            with self.subTest(fonte=body):
                self.assertRegex(method[at:], rf">{body}</abbr> \d+</li>")
        self.assertIn('<a href="#fontes-por-organismo">Método</a>', page)

    def test_the_page_fits_its_budget_for_either_bank(self):
        for label, page in (("principal", _Example.page()), ("consulta", _ConsultationExample.page())):
            with self.subTest(banco=label):
                self.assertLessEqual(words(panel_text(page, "fontes")), SOURCES_PAGE_WORDS)

    def test_without_the_verification_file_beside_the_cases_no_number_is_shown(self):
        page = _Example.page(confirmation=None)
        text = self.text(page)
        self.assertNotIn("Estado da confirmação", text)
        self.assertNotIn("Neste banco", text)
        self.assertNotIn("No projeto", text)
        self.assertIn("Nem todas as fontes destes casos foram confirmadas por uma pessoa.", text)
        self.assertIn('id="aviso-fontes"', page)

    def test_when_the_person_says_every_source_is_confirmed_no_state_is_shown(self):
        text = self.text(_Example.page(sources_verified=True))
        self.assertIn("Todas as fontes destes casos foram confirmadas por uma pessoa.", text)
        self.assertNotIn("Estado da confirmação", text)
        self.assertNotIn("Nem todas as fontes", text)

    def test_the_notice_and_the_bar_link_point_at_this_page(self):
        page = _Example.page()
        sources = page[page.index('<section class="painel" id="fontes"'):page.index('<section class="painel" id="resultados"')]
        self.assertIn('id="aviso-fontes"', sources)
        self.assertEqual(page.count('id="aviso-fontes"'), 1)
        self.assertIn('<a href="#fontes">Fontes por confirmar.</a>', page[:page.index("<main>")])

    def test_the_state_carries_the_date_the_report_was_made(self):
        page = _Example.page()
        sources = page[page.index('<section class="painel" id="fontes"'):page.index('<section class="painel" id="resultados"')]
        self.assertIn("em 2026-10-10:", visible(sources))

    def test_the_page_is_there_in_every_language_with_its_counts(self):
        from aferidor.traducao import LANGS

        for lang in LANGS:
            with self.subTest(lingua=lang):
                page = _Example.page(lingua=lang)
                sources = page[page.index('<section class="painel" id="fontes"'):page.index('<section class="painel" id="resultados"')]
                self.assertIn('class="estado-contagens"', sources)
                self.assertIn(">DGS</abbr> 16", sources)


CONCLUSIONS_WORDS = 140
GEMMA, PHI, GEMINI = "gemini:gemma-4-31b-it", "local:phi4:14b", "gemini:gemini-3.5-flash-lite"


def conclusions_text(page: str) -> str:
    return visible(panel_text(page, "conclusoes"))


class TestConclusionsPage(unittest.TestCase):
    """What the numbers allow saying and what they do not, all of it calculated from the report's data."""

    def test_the_example_says_what_can_and_cannot_be_concluded(self):
        text = conclusions_text(_Example.page())
        for sentence in (
            "Pode concluir-se",
            "Nenhum dos 4 modelos cumpre o limiar de referência (que não é um protocolo prévio). O melhor tem 8 de 27 casos com falha crítica.",
            "Entre os dois melhores, a diferença pode ser acaso (McNemar exato, p = 0,375).",
            "Não se pode concluir",
            "Que os modelos locais representem os comerciais.",
            "Que um veredicto seja validação clínica: é triagem, sem revisão por especialista.",
            "Que uma falha crítica seja sempre um erro real do modelo: o corretor é heurístico, com falsos passes e falsos falhanços conhecidos (ver Método).",
            "Nada de firme sobre outros casos: com 27 casos os intervalos são largos (8 de 27 é compatível com 16% a 48%).",
            "Que as fontes estejam confirmadas: neste banco, uma a uma 9, em grupo 11, por confirmar 7 (ver Fontes).",
            "Este relatório não recomenda nenhum modelo: mede, não aconselha.",
        ):
            with self.subTest(frase=sentence[:40]):
                self.assertIn(sentence, text)

    def test_the_interval_is_the_wilson_interval_of_the_best_model_rounded_like_every_other(self):
        """It is the model the first line calls the best, with its own cases, and the cards of the
        Results page show the same two numbers for it."""
        from aferidor.grading import compare_critical, consistency_by_case, consistency_by_model, wilson_interval

        d = _Example.data()
        consistency = consistency_by_case(d["cases"], d["answers"], d["verdicts"])
        best = compare_critical(consistency_by_model(consistency)).rows[0]
        low, high = wilson_interval(best[1], best[2])
        shown = f"({best[1]} de {best[2]} é compatível com {low * 100:.0f}% a {high * 100:.0f}%)"
        page = _Example.page()
        self.assertIn(shown, conclusions_text(page))
        self.assertIn(f"IC 95% {low * 100:.0f}% a {high * 100:.0f}%", visible(panel_text(page, "resultados")) + visible(page))

    def test_if_the_best_model_changes_with_the_data_the_sentence_follows(self):
        text = conclusions_text(example_page_of((GEMINI,)))
        self.assertIn("(11 de 27 é compatível com 25% a 59%)", text)

    def test_the_sources_line_names_the_three_categories_read_by_fontes(self):
        page = _Example.page()
        self.assertIn('(ver <a href="#fontes">Fontes</a>)', page[page.index('id="conclusoes"'):])

    def test_without_the_verification_file_the_sources_line_carries_no_number(self):
        text = conclusions_text(_Example.page(confirmation=None))
        self.assertIn("Que as fontes estejam confirmadas: o estado da confirmação não foi lido neste relatório.", text)
        self.assertNotIn("uma a uma", text)

    def test_when_the_person_says_every_source_is_confirmed_the_line_is_not_there(self):
        text = conclusions_text(_Example.page(sources_verified=True))
        self.assertNotIn("Que as fontes estejam confirmadas", text)

    def test_the_review_line_follows_the_constant_and_claims_nothing_once_it_is_true(self):
        with _mock.patch.object(_report, "CLINICAL_REVIEW_DONE", True):
            text = conclusions_text(_Example.page())
        self.assertIn("Que um veredicto seja validação clínica: é triagem.", text)
        self.assertNotIn("sem revisão por especialista", text)

    def test_with_a_protocol_the_first_line_counts_the_approved_and_drops_the_caveat(self):
        page = _Example.page(protocol=_Example.protocol(date(2020, 1, 1)))
        text = conclusions_text(page)
        self.assertIn("0 de 4 modelos aprovados pelo protocolo (critérios completos no Início).", text)
        self.assertIn('(critérios completos no <a href="#inicio">Início</a>)', page)
        self.assertNotIn("que não é um protocolo prévio", text)
        self.assertNotIn("O melhor tem", text)
        self.assertNotIn("O protocolo tem avisos", text)

    def test_a_protocol_with_warnings_adds_the_pointer_the_first_page_uses(self):
        page = _Example.page(protocol=_Example.protocol())
        text = conclusions_text(page)
        self.assertIn("O protocolo tem avisos (ver Método).", text)
        self.assertIn('<li class="c-remate">O protocolo tem avisos (ver <a href="#criterio">Método</a>).</li>', page)

    def test_a_significant_difference_says_so_and_a_single_model_has_no_comparison(self):
        text = conclusions_text(example_page_of((GEMMA, PHI)))
        self.assertIn("Entre os dois melhores, a diferença é estatisticamente significativa (McNemar exato, p < 0,001).", text)
        single = conclusions_text(example_page_of((GEMINI,)))
        self.assertNotIn("McNemar", single)
        self.assertIn("O modelo não cumpre o limiar de referência (que não é um protocolo prévio). Tem 11 de 27 casos com falha crítica.", single)

    def test_without_local_models_there_is_no_line_about_them(self):
        text = conclusions_text(example_page_of((GEMMA, GEMINI)))
        self.assertNotIn("modelos locais", text)

    def test_every_variant_fits_the_budget_with_or_without_a_protocol(self):
        variants = {
            "exemplo": _Example.page(),
            "sem ficheiro": _Example.page(confirmation=None),
            "fontes confirmadas": _Example.page(sources_verified=True),
            "protocolo com avisos": _Example.page(protocol=_Example.protocol()),
            "protocolo sem avisos": _Example.page(protocol=_Example.protocol(date(2020, 1, 1))),
            "significativa": example_page_of((GEMMA, PHI)),
            "sem locais": example_page_of((GEMMA, GEMINI)),
            "um modelo": example_page_of((GEMINI,)),
            "consulta": _ConsultationExample.page(),
        }
        with _mock.patch.object(_report, "CLINICAL_REVIEW_DONE", True):
            variants["revisão feita"] = _Example.page()
        for label, page in variants.items():
            with self.subTest(variante=label):
                self.assertLessEqual(words(panel_text(page, "conclusoes")), CONCLUSIONS_WORDS)

    def test_no_variant_recommends_a_model_names_a_recipient_or_uses_a_dash(self):
        for page in (_Example.page(), example_page_of((GEMINI,)), _Example.page(protocol=_Example.protocol())):
            text = conclusions_text(page)
            self.assertEqual(text.count("recomend"), 1)  # only "não recomenda nenhum modelo"
            self.assertIn("não recomenda nenhum modelo", text)
            self.assertNotIn("\u2014", text)
            self.assertNotIn("\u2013", text)

    def test_the_page_is_there_in_every_language(self):
        from aferidor.traducao import LANGS

        for lang in LANGS:
            with self.subTest(lingua=lang):
                page = _Example.page(lingua=lang)
                self.assertIn('class="conclusoes"', page)
                self.assertIn('class="fecho"', page)

    def test_the_old_note_and_triage_paragraph_are_gone_from_the_page(self):
        page = _Example.page()
        conclusions = page[page.index('id="conclusoes"'):page.index('id="metodo"')]
        self.assertNotIn('class="contexto"', conclusions)
        self.assertNotIn('class="triagem"', conclusions)


def fake_summaries(*results: tuple[str, int, int]) -> dict:
    """Summaries built by hand: (model, critical cases, cases), to reach branches the data does not."""
    from aferidor.grading import ConsistencySummary

    return {m: ConsistencySummary(model=m, cases=c, critical_cases=k, unstable_cases=0, sample_accuracy=0.5)
            for m, k, c in results}


class TestConclusionsTiesAndThresholds(unittest.TestCase):
    """Branches the real data does not reach, built with synthetic summaries."""

    def lines(self, *results, protocol=None, outcomes=None, warnings=None) -> dict[str, str]:
        summaries = fake_summaries(*results)
        token = html_report._LANG.set("pt")
        try:
            elements = html_report._conclusions_page(
                [m for m, _, _ in results], summaries, None, None, True, protocol, outcomes, warnings,
            )
        finally:
            html_report._LANG.reset(token)
        return {name: visible(html) for name, html in elements}

    def test_two_models_tied_at_the_top_are_not_called_the_best(self):
        lines = self.lines(("a", 8, 27), ("b", 8, 27), ("c", 16, 27), ("d", 22, 27))
        self.assertIn("Os dois melhores têm 8 de 27 casos com falha crítica.", lines["limiar"])
        self.assertNotIn("O melhor", lines["limiar"])
        self.assertNotIn("comparacao", lines)  # the line above already says they tie
        self.assertIn("(8 de 27 é compatível com 16% a 48%)", lines["intervalo"])  # the line above gave the numbers

    def test_with_a_protocol_a_tie_is_not_named_in_the_first_line_so_the_interval_names_it(self):
        from types import SimpleNamespace

        protocol = _Example.protocol(date(2020, 1, 1))
        outcomes = [SimpleNamespace(approved=False)] * 3
        lines = self.lines(("a", 8, 27), ("b", 8, 27), ("c", 16, 27), protocol=protocol, outcomes=outcomes)
        self.assertEqual(lines["limiar"], "0 de 3 modelos aprovados pelo protocolo (critérios completos no Início).")
        self.assertIn("(os melhores, 8 de 27, é compatível com 16% a 48%)", lines["intervalo"])

    def test_three_tied_of_four_and_all_tied_are_worded_for_their_number(self):
        self.assertIn("Os 3 melhores têm 8 de 27 casos", self.lines(("a", 8, 27), ("b", 8, 27), ("c", 8, 27), ("d", 22, 27))["limiar"])
        self.assertIn("Os dois têm 8 de 27 casos", self.lines(("a", 8, 27), ("b", 8, 27))["limiar"])
        self.assertIn("Todos têm 8 de 27 casos", self.lines(("a", 8, 27), ("b", 8, 27), ("c", 8, 27))["limiar"])

    def test_the_same_proportion_over_different_numbers_of_cases_gives_no_numbers_and_no_interval(self):
        lines = self.lines(("a", 4, 10), ("b", 8, 20), ("c", 9, 10))
        self.assertIn("Os dois melhores têm a mesma proporção de casos com falha crítica.", lines["limiar"])
        self.assertNotRegex(lines["limiar"], r"\d+ de \d+ casos")
        self.assertEqual(lines["intervalo"], "Nada de firme sobre outros casos: os intervalos são largos.")
        self.assertNotIn("(", lines["intervalo"])

    def test_the_same_proportion_for_all_with_different_numbers_is_worded_for_all(self):
        self.assertIn("Os dois têm a mesma proporção de casos com falha crítica.", self.lines(("a", 4, 10), ("b", 8, 20))["limiar"])
        self.assertIn("Todos têm a mesma proporção de casos com falha crítica.", self.lines(("a", 4, 10), ("b", 8, 20), ("c", 2, 5))["limiar"])

    def test_a_model_that_meets_the_threshold_changes_the_first_line_and_the_interval_names_it(self):
        lines = self.lines(("a", 0, 27), ("b", 8, 27), ("c", 16, 27))
        self.assertIn("Modelos que cumprem o limiar de referência (que não é um protocolo prévio): 1 de 3.", lines["limiar"])
        self.assertIn("(o melhor, 0 de 27, é compatível com 0% a 12%)", lines["intervalo"])

    def test_one_model_that_meets_it_has_no_best_result_to_give(self):
        lines = self.lines(("a", 0, 27))
        self.assertEqual(lines["limiar"], "O modelo cumpre o limiar de referência (que não é um protocolo prévio).")
        self.assertNotIn("comparacao", lines)

    def test_the_intervals_are_rounded_to_the_nearest_whole_number_as_in_the_rest_of_the_report(self):
        self.assertIn("compatível com 16% a 48%", self.lines(("a", 8, 27), ("b", 16, 27))["intervalo"])
        self.assertIn("compatível com 0% a 12%", self.lines(("a", 0, 27), ("b", 16, 27))["intervalo"])


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


class TestAboutPage(unittest.TestCase):
    """What the instrument is, what it is for and how it is run: only what is true of every report."""

    def about(self, page: str) -> str:
        return visible(page[page.index('<section class="painel" id="sobre"'):page.index('<section class="painel" id="fontes"')])

    def test_the_page_says_what_it_is_what_it_is_for_and_how_it_is_run(self):
        text = self.about(_Example.page())
        for sentence in (
            "Sobre o Aferidor", "O que é esta ferramenta", "Para que serve", "Como usar esta ferramenta",
            "O Aferidor faz perguntas clínicas a assistentes de inteligência artificial, programas que escrevem as respostas (os modelos de linguagem), e compara cada resposta com documentos clínicos públicos, como as normas da Direção-Geral da Saúde e os resumos das características dos medicamentos.",
            "Cada pergunta, com a resposta de referência e a fonte, chama-se caso.",
            "Mede, não aconselha. Não é um dispositivo médico e não contém dados de doentes.",
            "Serve para ver como um assistente responde a perguntas clínicas e que erros comete.",
            "Objetivos.", "Medir, sem aconselhar.", "Mostrar primeiro as falhas críticas, e não a média.",
            "Preparar a validação por um especialista.",
            "Para experimentar não é preciso chave nem custo:",
            "As chaves de API são lidas do ambiente e nunca do repositório.",
        ):
            with self.subTest(frase=sentence[:40]):
                self.assertIn(sentence, text)
        self.assertNotIn("folhetos", text)

    def test_the_first_line_of_what_it_is_for_comes_before_the_aims(self):
        text = self.about(_Example.page())
        self.assertLess(text.index("Serve para ver como um assistente"), text.index("Objetivos."))

    def test_the_grader_has_one_sentence_here_that_points_to_the_closed_block_of_the_method_page(self):
        page = _Example.page()
        text = self.about(page)
        self.assertIn(
            "Quem corrige as respostas é um programa, o corretor: procura no texto o que o caso exige e o que não pode aparecer, e dá sempre o mesmo resultado para a mesma resposta. É automático e imperfeito, com falsos alarmes e erros que passam (ver Método).",
            text,
        )
        self.assertIn(f'(ver <a href="#{html_report.VERIFICATION_ANCHOR}">Método</a>)', page)
        self.assertNotIn("Antes de cada ensaio", text)  # the verification and the tuning moved to the Method page
        self.assertNotIn("foi afinado", text)

    def test_the_method_page_has_the_closed_block_the_link_points_to(self):
        page = _Example.page()
        method = page[page.index('<section class="painel" id="metodo"'):page.index("</main>")]
        block = re.search(r'<details class="recolhe" id="verificacao-corretor"><summary>(.*?)</summary>(.*?)</details>', method, flags=re.S)
        self.assertIsNotNone(block)
        self.assertEqual(block.group(1), "Como se verifica e se afina o corretor")
        self.assertNotIn(" open", block.group(0)[:60])  # closed
        self.assertIn(f'<p id="{html_report.VERIFICATION_ANCHOR}">Os critérios de cada caso e o corretor estão em código, com histórico de alterações.</p>', block.group(2))
        for sentence in (
            "Antes de cada ensaio, uma corrida de perguntas a um modelo, cada critério tem de aceitar a resposta de referência e rejeitar uma resposta errada construída para o efeito.",
            "O corretor foi afinado depois de alguns ensaios, com cada afinação registada e a razão escrita; por isso os números dependem da versão do corretor.",
        ):
            self.assertIn(sentence, block.group(2))
        # what is closed does not count, and the link has a target that opens the page of the method
        self.assertEqual(page.count(f'id="{html_report.VERIFICATION_ANCHOR}"'), 1)

    def test_the_first_time_it_says_trial_it_defines_it_and_the_threshold_comes_with_its_meaning(self):
        text = self.about(_Example.page())
        self.assertIn("escrito antes do ensaio (uma corrida de perguntas a um modelo), mas é opcional.", text)
        self.assertIn("usa o limiar de referência (nenhum caso com falha crítica), que não é um protocolo prévio.", text)
        self.assertEqual(text.index("ensaio"), text.index("ensaio (uma corrida"))  # defined where it first appears

    def test_the_definition_of_a_critical_failure_is_on_the_first_page_and_only_there(self):
        page = _Example.page()
        sentence = "Falha crítica: erro que pode fazer mal a um doente, como uma dose errada ou um medicamento dado a um alérgico."
        first = visible(page[page.index('<section class="painel" id="inicio"'):page.index('<section class="painel" id="sobre"')])
        self.assertIn(sentence, first)
        self.assertGreater(first.index(sentence), first.index("Modelos que cumprem"))  # next to the result
        self.assertNotIn(sentence, self.about(page))

    def test_it_never_says_the_criteria_were_defined_before_every_trial(self):
        for page in (_Example.page(), _Example.page(protocol=_Example.protocol())):
            text = self.about(page)
            self.assertNotIn("definidos antes", text)
            self.assertNotIn("critérios de aceitação", text)

    def test_the_protocol_sentence_follows_whether_the_report_has_one(self):
        without = self.about(_Example.page())
        self.assertIn("Este relatório não tem nenhum: usa o limiar de referência (nenhum caso com falha crítica), que não é um protocolo prévio.", without)
        page = _Example.page(protocol=_Example.protocol())
        with_one = self.about(page)
        self.assertIn("Este relatório tem um; os critérios estão no Início.", with_one)
        self.assertIn("escrito antes do ensaio (uma corrida de perguntas a um modelo), mas é opcional.", with_one)
        self.assertNotIn("não tem nenhum", with_one)
        self.assertIn('os critérios estão no <a href="#inicio">Início</a>', page)

    def test_the_commands_are_the_readme_ones_without_the_line_that_counts_tests(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        shown = html_report.ABOUT_COMMANDS.splitlines()
        self.assertEqual(len(shown), 4)
        for line in shown:
            with self.subTest(linha=line[:40]):
                self.assertIn(line, readme)  # copied as it is there, comment included
        self.assertNotIn("unittest", html_report.ABOUT_COMMANDS)
        self.assertIn("<pre><code>git clone", _Example.page())

    def test_the_only_new_address_is_the_running_guide_in_the_repository(self):
        page = _Example.page()
        self.assertIn(f'<a href="{html_report.COMO_CORRER_URL}" rel="noopener"><code>COMO_CORRER.md</code></a>', page)
        self.assertTrue(html_report.COMO_CORRER_URL.startswith(html_report.REPO_URL + "/"))

    def test_the_first_page_points_to_it_and_the_navigation_has_it_second(self):
        page = _Example.page()
        self.assertEqual(navigation(page)[:2], ["inicio", "sobre"])
        self.assertIn('<p class="saber-mais"><a href="#sobre">Saber mais sobre o Aferidor.</a></p>', page)

    def test_every_variant_fits_the_budget_with_its_headings(self):
        for label, page in {
            "sem protocolo": _Example.page(),
            "com protocolo": _Example.page(protocol=_Example.protocol()),
        }.items():
            with self.subTest(variante=label):
                self.assertLessEqual(words(panel_text(page, "sobre")), ABOUT_PAGE_WORDS)

    def test_the_page_is_in_every_language_and_the_numbers_beside_the_text_start_at_80rem(self):
        from aferidor.traducao import LANGS

        for lang in LANGS:
            with self.subTest(lingua=lang):
                self.assertIn('class="sobre"', _Example.page(lingua=lang))
        css = html_estilo.STYLE
        self.assertIn("@media (min-width: 80rem)", css)
        self.assertIn("grid-template-columns: 38rem 18rem", css)
        self.assertIn(".inicio-texto, .inicio-lateral, .sobre { max-width: 38rem; }", css)

    def test_no_dash_in_what_the_about_page_says(self):
        text = self.about(_Example.page())
        self.assertNotIn("\u2014", text)
        self.assertNotIn("\u2013", text)


class TestTheExampleCase(unittest.TestCase):
    """A real case of the bank on the About page, read from the bank itself, with a guard on the choice."""

    CASE = html_report.EXAMPLE_CASE_ID

    def block(self, page: str) -> str:
        at = page.find('<div class="exemplo">')
        return "" if at < 0 else page[at:page.index("</div>", at)]

    def test_the_case_is_shown_with_its_question_the_serious_error_and_a_short_source(self):
        page = _Example.page()
        block = self.block(page)
        text = visible(block)
        self.assertIn("Um caso, como exemplo", text)
        self.assertIn("Criança de 4 anos, 16 kg, com otite média aguda e antecedente de anafilaxia à amoxicilina.", text)
        self.assertIn("Um erro grave seria propor amoxicilina ou cefuroxima: seria uma falha crítica.", text)
        self.assertIn("Fonte. DGS, Norma n.º 007/2012", text)
        self.assertNotIn("de 16/12/2012", text.split("Ver a referência")[0])  # the short source has no date, point or page

    def test_the_full_reference_and_source_are_in_a_closed_details(self):
        block = self.block(_Example.page())
        details = re.search(r"<details class=\"recolhe\"><summary>(.*?)</summary>(.*)</details>", block, flags=re.S)
        self.assertEqual(details.group(1), "Ver a referência e a fonte completa")
        self.assertIn("Um macrólido: azitromicina 10 mg/kg/dia", details.group(2))
        self.assertIn("a cefuroxima só é alternativa na hipersensibilidade não tipo I.", details.group(2))
        self.assertIn("Anexo I, quadro 2, p. 17", details.group(2))
        self.assertNotIn("Um macrólido", block.split("<details")[0])  # the reference is not open to the eye

    def test_the_serious_error_is_read_from_the_cases_own_criterion(self):
        """Not written by hand: a case whose forbidden drugs differ gives another sentence."""
        from aferidor.models import Criterion, Source
        from aferidor.risk import FailureType

        case = Case(
            case_id=self.CASE, category="alergia", question="Q?", reference="R.",
            source=Source(name="DGS", reference="Norma n.º 001/2020 de 01/01/2020, p. 1"),
            criteria=(Criterion(kind="nao_prescreve", terms=("penicilina", "amoxicilina", "cefuroxima"),
                                failure=FailureType.CONTRAINDICACAO_OMITIDA),),
        )
        text = visible(self.block(build([case], [an_answer("x")])))
        self.assertIn("Um erro grave seria propor penicilina, amoxicilina ou cefuroxima", text)
        self.assertIn("Fonte. DGS, Norma n.º 001/2020", text)

    def test_if_the_case_is_not_in_the_bank_the_block_is_not_there(self):
        page = build([a_case()], [an_answer("500 mg")])
        self.assertNotIn('class="exemplo"', page)
        self.assertNotIn("Um caso, como exemplo", page)

    def test_a_case_without_a_critical_forbidden_drug_gives_no_block(self):
        from aferidor.models import Criterion, Source
        from aferidor.risk import FailureType

        case = Case(
            case_id=self.CASE, category="x", question="Q?", reference="R.",
            source=Source(name="DGS", reference="Norma n.º 001/2020"),
            criteria=(Criterion(kind="contem", terms=("1 g",), failure=FailureType.RESPOSTA_INCOMPLETA),),
        )
        self.assertNotIn('class="exemplo"', build([case], [an_answer("x")]))

    def test_the_chosen_case_exists_has_the_criterion_and_its_source_is_marked_as_confirmed(self):
        """If this fails the page would show, as its example, a case whose source nobody has confirmed
        or that is no longer in the bank. Choosing another case is the Fábio's decision: nothing is changed here."""
        from aferidor import fontes
        from aferidor.storage import read_cases

        cases = {c.case_id: c for c in read_cases(ROOT / "casos" / "casos.json")}
        self.assertIn(self.CASE, cases, "o caso do exemplo já não está em casos/casos.json; o Fábio escolhe outro")
        case = cases[self.CASE]
        self.assertTrue(
            any(c.kind == "nao_prescreve" and c.failure.risk.name == "CRITICO" for c in case.criteria),
            "o caso do exemplo já não tem um critério nao_prescreve de risco crítico; o Fábio escolhe outro",
        )
        table = fontes.read_table(ROOT / "casos" / "VERIFICACAO.md")
        self.assertTrue(
            table.get(self.CASE),
            f"{self.CASE} não está marcado como confirmado em casos/VERIFICACAO.md; "
            "a página Sobre não deve mostrar como exemplo um caso por confirmar. O Fábio escolhe outro; nada foi corrigido.",
        )
