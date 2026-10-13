"""The published example says what the correction did, in five languages, with the same numbers, and every number is worked out."""

from __future__ import annotations

import dataclasses
import re
import unittest
from html import unescape
from types import SimpleNamespace

from aferidor import correcao, html_estilo, html_report
from aferidor.traducao import LANGS
from tests.html_support import ROOT

EXAMPLE = ROOT / "docs" / "exemplo"
FILES = {"pt": "index.html", "en": "index.en.html", "es": "index.es.html", "fr": "index.fr.html", "de": "index.de.html"}
PAGES = {lang: (EXAMPLE / name).read_text(encoding="utf-8") for lang, name in FILES.items()}
READING = ROOT / "docs" / "LEITURA_MUDANCAS_2026-10-13.md"
CORRECTION = correcao.compute(EXAMPLE / "antes-8edda161.json", ROOT / "ensaios", ROOT, READING)


def block(page: str, ident: str) -> str:
    start = page.index(f'id="{ident}"')
    return page[start:page.index("</div>", page.index("</table>", start) if ident == "publicado-e-corrigido" else start)]


def words(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def table_numbers(page: str) -> list[tuple[int, int, int]]:
    """(cases, published, corrected) of every row of the table of the Results page."""
    start = page.index('class="areas tabela-correcao"')
    table = page[start:page.index("</table>", start)]
    rows = re.findall(r"<tr><th scope=\"row\">[^<]*</th><td>.*?</td><td>(\d+)</td><td>(\d+)</td><td><strong>(\d+)</strong></td></tr>", table)
    return [tuple(map(int, row)) for row in rows]


class TestTheTableIsTheComputedOne(unittest.TestCase):
    def test_every_row_of_the_table_is_what_the_correction_computes(self):
        expected = [(r.cases, r.before, r.after) for bank in ("principal", "consulta")
                    for r in sorted((r for r in CORRECTION.rows if r.bank == bank), key=lambda r: (r.frozen, html_report._model_sized(r.model)))]
        self.assertEqual(table_numbers(PAGES["pt"]), expected)

    def test_the_five_languages_carry_the_same_numbers(self):
        reference = table_numbers(PAGES["pt"])
        self.assertEqual(len(reference), len(CORRECTION.rows))
        for lang in LANGS:
            with self.subTest(lingua=lang):
                self.assertEqual(table_numbers(PAGES[lang]), reference)

    def test_the_best_model_the_mcnemar_and_the_counts_of_the_method_page_are_the_same_in_the_five_languages(self):
        def figures(page: str) -> list[str]:
            start = page.index('id="publicado-e-corrigido"')
            text = words(page[start:page.index('class="comparacao"', start)])
            start = page.index('id="normas-citadas"')
            text += " " + words(page[start:page.index("</ul>", start)])
            text = re.sub(r"12[./]10\.?", "", text)
            return [n.replace(",", ".") for n in re.findall(r"\d+(?:[.,]\d+)?", text)]

        reference = figures(PAGES["pt"])
        self.assertIn("0.375", reference)
        self.assertIn("0.250", reference)
        for lang in LANGS:
            with self.subTest(lingua=lang):
                self.assertEqual(figures(PAGES[lang]), reference)

    def test_the_figures_of_the_method_page_are_computed_not_written(self):
        text = words(PAGES["pt"][PAGES["pt"].index('id="normas-citadas"'):][:3500])
        n1, c1 = CORRECTION.equivalent_forms
        n2, c2 = CORRECTION.all_corrections
        self.assertIn(f"altera {n1} critérios em {c1} casos; todas as correções, {n2} critérios em {c2} casos", text)
        for model, n, total in CORRECTION.cephalexin:
            self.assertIn(f"{html_report._model_sized(model)}: {n} de {total} respostas", text)

    def test_the_best_pair_and_its_p_values_are_the_computed_ones(self):
        text = words(PAGES["pt"][PAGES["pt"].index('id="publicado-e-corrigido"'):][:5000])
        before, after = CORRECTION.best_before, CORRECTION.best_after
        self.assertIn(f"{before.first_critical} de {before.cases} casos com falha crítica", text)
        self.assertIn(f"{after.first_critical} de {after.cases}", text)
        self.assertIn(f"p = {before.p_value:.3f}".replace(".", ","), text)
        self.assertIn(f"p = {after.p_value:.3f}".replace(".", ","), text)


class TestWhatTheTextSaysAndDoesNotSay(unittest.TestCase):
    def test_it_says_nobody_fell_only_because_nobody_did(self):
        self.assertEqual(CORRECTION.fell, ())
        self.assertIn("nenhuma tem menos", words(PAGES["pt"]))

    def test_with_a_model_that_fell_the_page_says_so_and_not_the_other_thing(self):
        row = dataclasses.replace(CORRECTION.rows[0], before=5, after=3)
        changed = dataclasses.replace(CORRECTION, rows=(row, *CORRECTION.rows[1:]))
        text = words(html_report._correction_results(SimpleNamespace(correction=changed)))
        self.assertIn("têm menos", text)
        self.assertNotIn("nenhuma tem menos", text)

    def test_the_26b_is_marked_a_later_reclassification_and_no_threshold_is_applied_to_it(self):
        text = words(PAGES["pt"])
        self.assertIn("reclassificação posterior, fora do protocolo", text)
        self.assertIn("não se lhe aplica o limiar do protocolo", text)

    def test_ciprofloxacin_disagrees_with_the_cited_standard_of_2011_and_is_never_called_wrong_or_counted(self):
        for lang, page in PAGES.items():
            standards = page[page.index('id="normas-citadas"'):][:4500]
            paragraph = [p for p in re.findall(r"<p>(.*?)</p>", standards, flags=re.S) if "iprofloxacin" in p or "iprofloxacine" in p][0]
            with self.subTest(lingua=lang):
                self.assertIn("2011", paragraph)
                self.assertNotRegex(re.sub(r"ATB-[A-Z]+-\d+|015/2011|2011", "", words(paragraph)), r"\d")
        paragraph = words(PAGES["pt"][PAGES["pt"].index('id="normas-citadas"'):][:4500])
        self.assertIn("discorda da norma citada", paragraph)
        cipro = paragraph[paragraph.index("Ciprofloxacina (ATB-PIEL-006"):]
        for banned in ("errado", "errada", "dose incorreta", "incorreta"):
            self.assertNotIn(banned, cipro)

    def test_cephalexin_is_counted_as_a_mention_and_the_case_stays_in_the_total(self):
        text = words(PAGES["pt"][PAGES["pt"].index('id="normas-citadas"'):][:4500])
        self.assertIn("Mencionar não é recomendar", text)
        self.assertIn("continua no total", text)
        self.assertIn("cefuroxima", text)

    def test_the_limitations_are_listed_in_every_language_and_nothing_in_them_says_validated(self):
        for lang, page in PAGES.items():
            start = page.index('id="limitacoes"')
            listing = page[start:page.index("</ul>", start)]
            with self.subTest(lingua=lang):
                self.assertEqual(listing.count("<li>"), 9)
        text = words(PAGES["pt"][PAGES["pt"].index('id="limitacoes"'):][:6500])
        for expected in ("nomeia mais de um fármaco", "ClCr", "sem âncora", "ATB-PIEL-006 passa com a ciprofloxacina", "«Evitar cefuroxima 250 mg 12/12 h» passa",
                         "controlos negativos", "cefaclor", "uma só pessoa", "não foram amostrados", "ATB-FAR-013, PED-OMA-019, 020 e 021, COV-TOC-009"):
            with self.subTest(limite=expected):
                self.assertIn(expected, text)
        self.assertNotRegex(text.lower(), r"\bvalidad[oa]s?\b(?! clínica)")

    def test_the_rules_and_the_post_hoc_ones_are_described_on_the_method_page(self):
        text = words(PAGES["pt"][PAGES["pt"].index('id="verificacao-corretor"'):][:6000])
        for expected in ("U1:", "U2:", "U3:", "U5:", "P1,", "P2,", "P3,", "âncora, tirada do texto de referência do caso e nunca de uma resposta",
                         "não foi escolhida nem ajustada pelo efeito num modelo", "docs/METODO.md"):
            with self.subTest(regra=expected):
                self.assertIn(expected, text)

    def test_the_menu_of_the_method_page_has_the_two_new_sections(self):
        for lang, page in PAGES.items():
            with self.subTest(lingua=lang):
                self.assertIn('href="#limitacoes"', page)
                self.assertIn('href="#normas-citadas"', page)


class TestTheFactualSentenceTheReadingAndTheLabel(unittest.TestCase):
    def test_the_sentence_about_the_rows_is_only_a_count_and_the_count_is_computed(self):
        text = words(PAGES["pt"])
        expected = (f"Com o corretor corrigido, {len(CORRECTION.rose)} das {len(CORRECTION.rows)} linhas da tabela têm mais casos com falha "
                    "crítica e nenhuma tem menos.")
        self.assertIn(expected, text)
        self.assertNotIn("deixava passar demais", text)

    def test_the_sentence_has_the_same_numbers_in_the_five_languages(self):
        for lang, page in PAGES.items():
            start = page.index('id="publicado-e-corrigido"')
            text = words(page[start:page.index('class="comparacao"', start)])
            with self.subTest(lingua=lang):
                self.assertIn(str(len(CORRECTION.rose)), text)
                self.assertIn(str(len(CORRECTION.rows)), text)

    def test_the_limitation_gives_the_numbers_of_the_reading_in_the_five_languages_and_points_to_the_file(self):
        n, a, b, c = CORRECTION.reading
        for lang, page in PAGES.items():
            start = page.index('id="limitacoes"')
            text = words(page[start:page.index("</ul>", start)])
            numbers = re.findall(rf"(?<!\d){n}(?!\d)[^.]*?(?<!\d){a}(?!\d)[^.]*?(?<!\d){b}(?!\d)[^.]*?(?<!\d){c}(?!\d)", text)
            with self.subTest(lingua=lang):
                self.assertTrue(numbers, text[-900:])
                self.assertIn("docs/LEITURA_MUDANCAS_2026-10-13.md", text)

    def test_without_a_false_failure_there_is_no_sentence_about_what_the_table_would_be_without_it(self):
        self.assertIsNone(CORRECTION.sensitivity)
        for lang, page in PAGES.items():
            start = page.index('id="limitacoes"')
            text = words(page[start:page.index("</ul>", start)])
            with self.subTest(lingua=lang):
                self.assertNotIn("→", text)

    def test_the_sentence_of_the_sensitivity_is_worked_out_from_the_data_when_a_false_failure_moves_the_table(self):
        import dataclasses

        moved = correcao.Sensitivity(
            2, (("t", "gemini:gemini-3.5-flash-lite", "principal", 13, 12), ("t", "gemini:gemma-4-31b-it", "principal", 10, 9)),
            CORRECTION.best_after, dataclasses.replace(CORRECTION.best_after, p_value=0.5),
        )
        text = words(html_report._limitations_block(dataclasses.replace(CORRECTION, sensitivity=moved)))
        self.assertIn("Sem estes 2 casos lidos como falsos falhanços ou falsos passes, a tabela mudaria assim", text)
        self.assertIn("Gemini 3.5 Flash Lite: 13 → 12", text)
        self.assertIn("daria p = 0,500 em vez de p = 0,250", text)

    def test_the_failure_type_of_a_dose_or_an_interval_has_a_neutral_label_in_every_language(self):
        new = {"pt": "Dose ou intervalo diferente da referência", "en": "Dose or interval different from the reference",
               "es": "Dosis o intervalo distintos de la referencia", "fr": "Dose ou intervalle différents de la référence",
               "de": "Dosis oder Intervall weichen von der Referenz ab"}
        old = {"pt": "Dose errada", "en": "Wrong dose", "es": "Dosis errónea", "fr": "Dose erronée", "de": "Falsche Dosis"}
        for lang, page in PAGES.items():
            with self.subTest(lingua=lang):
                self.assertIn(new[lang], page)
                self.assertNotIn(old[lang], page)

    def test_the_case_of_ciprofloxacin_does_not_say_wrong_dose_and_the_standards_block_does_not_say_wrong(self):
        page = PAGES["pt"]
        start = page.index('id="corpo-ATB-PIEL-006"')
        block = words(page[start:page.index("</section>", start)] if "</section>" in page[start:] else page[start:start + 20000])
        self.assertNotIn("Dose errada", block)
        self.assertNotIn("dose incorreta", block.lower())


class TestTheGridDoesNotWidenThePage(unittest.TestCase):
    """The cells of the grid hold visually hidden text, positioned absolutely; without a positioned wrapper it escaped the
    scroll of the grid and made the page wider than the window (measured at 320, 360 and 375 px)."""

    def test_the_wrapper_of_the_grid_is_the_containing_block_of_what_is_hidden_in_it(self):
        css = html_estilo.STYLE
        rule = css[css.index(".grade-wrap {"):css.index("}", css.index(".grade-wrap {"))]
        self.assertIn("position: relative", rule)
        self.assertIn("overflow-x: auto", rule)
        self.assertIn(".vh {", css)
        self.assertIn("position: absolute", css[css.index(".vh {"):css.index("}", css.index(".vh {"))])
        for lang, page in PAGES.items():
            self.assertIn("position: relative; overflow-x: auto", page, lang)


if __name__ == "__main__":
    unittest.main()
