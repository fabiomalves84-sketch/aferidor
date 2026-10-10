"""The HTML report: the document, escaping, the case detail, the grid, the glossary."""

from __future__ import annotations

import re
import unittest
from datetime import date
from pathlib import Path

from aferidor import html_estilo, html_report, report
from aferidor.grading import consistency_by_case, consistency_by_model, grade_all
from aferidor.models import Case, Criterion, Source
from aferidor.risk import FailureType
from tests.helpers import a_case, an_answer
from tests.html_support import (
    build,
    panel_html,
    visible,
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
        first = panel_html(text, "inicio")
        self.assertNotIn(link, first)
        method = panel_html(text, "metodo")
        self.assertIn(link, method)
        self.assertIn(link, text[text.index('<footer class="rodape">'):])

    def test_the_link_text_follows_the_language_of_the_page(self):
        from aferidor.traducao import LANGS, t

        for lang in LANGS:
            with self.subTest(lingua=lang):
                self.assertIn(f'rel="noopener">{t(self.LINK_TEXT, lang)}</a>', self.page(lingua=lang))


class TestHeadline(unittest.TestCase):
    def test_the_critical_case_count_is_shown_per_model(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn('<span class="destaque">1</span>', text)
        self.assertIn("de 1 casos com falha crítica em alguma amostra", visible(text))


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


if __name__ == "__main__":
    unittest.main()
