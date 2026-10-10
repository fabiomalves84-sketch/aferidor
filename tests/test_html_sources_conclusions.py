"""The Sources page and the Conclusions page of the HTML report."""

from __future__ import annotations

import unittest
from datetime import date
from unittest import mock as _mock

from aferidor import html_report
from aferidor import report as _report
from aferidor.grading import consistency_by_case, consistency_by_model
from tests.html_support import (
    CONCLUSIONS_WORDS,
    GEMINI,
    GEMMA,
    PHI,
    SOURCES_PAGE_WORDS,
    _ConsultationExample,
    _Example,
    conclusions_text,
    example_page_of,
    fake_summaries,
    panel_html,
    panel_text,
    visible,
    words,
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
        method = panel_html(page, "metodo")
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
        sources = panel_html(page, "fontes")
        self.assertIn('id="aviso-fontes"', sources)
        self.assertEqual(page.count('id="aviso-fontes"'), 1)
        self.assertIn('<a href="#fontes">Fontes por confirmar.</a>', page[:page.index("<main>")])

    def test_the_state_carries_the_date_the_report_was_made(self):
        page = _Example.page()
        sources = panel_html(page, "fontes")
        self.assertIn("em 2026-10-10:", visible(sources))


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
        from aferidor.grading import compare_critical, wilson_interval

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

    def test_the_old_note_and_triage_paragraph_are_gone_from_the_page(self):
        page = _Example.page()
        conclusions = page[page.index('id="conclusoes"'):page.index('id="metodo"')]
        self.assertNotIn('class="triagem"', conclusions)


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


if __name__ == "__main__":
    unittest.main()
