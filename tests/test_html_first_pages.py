"""The first page, the About page and the real case it shows, with their word budgets."""

from __future__ import annotations

import re
import unittest
from datetime import date
from unittest import mock as _mock

from aferidor import html_estilo, html_report
from aferidor import report as _report
from aferidor.models import Case, Criterion, Source
from aferidor.risk import FailureType
from tests.helpers import a_case, an_answer
from tests.html_support import (
    ABOUT_PAGE_WORDS,
    FIRST_PAGE_WORDS,
    FRAME_WORDS,
    ROOT,
    TRANSLATION_NOTICE_WORDS,
    _Example,
    build,
    element_text,
    navigation,
    panel_html,
    panel_text,
    visible,
    words,
)


class TestReadableByAnOutsider(unittest.TestCase):
    """The page has to say what it is before it shows a number."""

    def test_it_opens_by_saying_what_the_aferidor_is_why_it_exists_and_what_it_aims_at(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        first = visible(panel_html(text, "inicio"))
        self.assertIn("Um médico pode perguntar a um destes assistentes", first)
        self.assertIn('<a href="#sobre">Saber mais sobre o Aferidor.</a>', text)
        self.assertNotIn("Objetivos.", first)  # the aims moved to the About page
        self.assertLess(first.index("Um médico pode perguntar"), first.index("Saber mais sobre o Aferidor."))
        self.assertLess(first.index("Saber mais"), first.index("Modelos que cumprem"))
        self.assertLess(text.index('id="inicio"'), text.index('<span class="destaque">'))

    def test_how_to_read_it_is_in_the_method_page_closed(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        method = panel_html(text, "metodo")
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
        first = panel_html(text, "inicio")
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
        first = panel_html(page, "inicio")
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
            "crítica, nenhum inconsistente, pelo menos 95% de amostras corretas): 0 de 4.",
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
        self.assertIn("no máximo 2 inconsistentes", text)
        self.assertIn("pelo menos 90% de amostras corretas", text)

    def test_a_protocol_with_warnings_points_at_the_method_page_and_one_without_says_nothing(self):
        with_warnings = _Example.page(protocol=_Example.protocol())
        first = panel_html(with_warnings, "inicio")
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


class TestAboutPage(unittest.TestCase):
    """What the instrument is, what it is for and how it is run: only what is true of every report."""

    def about(self, page: str) -> str:
        return visible(panel_html(page, "sobre"))

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
        method = panel_html(page, "metodo")
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
        first = visible(panel_html(page, "inicio"))
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

    def test_the_numbers_beside_the_text_start_at_80rem(self):
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


if __name__ == "__main__":
    unittest.main()
