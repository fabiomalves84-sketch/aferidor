"""The report's interface in five languages; the cases and the answers never translated."""

from __future__ import annotations

import ast
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

from aferidor import html_report, traducao
from aferidor.cli import main
from aferidor.grading import CASE_RULES, ConsistencyState, grade_all
from aferidor.protocolo import read_protocol, template
from aferidor.storage import read_answers, read_cases
from aferidor.traducao import CATALOG, LANGS, t
from tests.test_html_report import a_case, an_answer, build as page_of

ROOT = Path(__file__).resolve().parent.parent
TRIAL = ROOT / "ensaios" / "2026-09-16-comparacao-local"


def placeholders(text: str) -> list[str]:
    return sorted(re.findall(r"\{(\w+)\}", text))


def interface_strings() -> set[str]:
    """Every Portuguese string the code hands to the catalogue, found in the source."""
    found: set[str] = set()
    for name in ("html_report", "report", "protocolo", "lingua"):
        tree = ast.parse((ROOT / "aferidor" / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or getattr(node.func, "id", None) not in ("_t", "t", "_plural"):
                continue
            args = node.args[1:] if node.func.id == "_plural" else node.args[:1]
            for arg in args:
                options = [arg.body, arg.orelse] if isinstance(arg, ast.IfExp) else [arg]
                found.update(o.value for o in options if isinstance(o, ast.Constant) and isinstance(o.value, str))
    tables = (html_report._FAILURE_LABEL, html_report._CATEGORY_LABEL, html_report._CODE_PARTS, html_report._HOW)
    for table in tables:
        found.update(table.values())
    found.update("risco " + v for v in html_report._RISK_LABEL.values())
    found.update(html_report.GLOSSARY)
    found.update(html_report.GLOSSARY.values())
    found.update(sentence for _, sentence in html_report._EVIDENCE)
    found.update(CASE_RULES.values())
    found.update(state.label for state in ConsistencyState)
    found.update(label for _, label in html_report.PANELS)
    found.add(traducao.UNREVIEWED_NOTICE)
    return found


class TestCatalogue(unittest.TestCase):
    def test_every_interface_string_is_translated_into_every_language(self):
        missing = [
            (lang, text) for text in interface_strings() for lang in LANGS[1:]
            if lang not in CATALOG.get(text, {})
        ]
        self.assertEqual(missing, [])

    def test_every_translation_keeps_the_placeholders(self):
        for text, versions in CATALOG.items():
            for lang, translated in versions.items():
                with self.subTest(text=text[:40], lang=lang):
                    self.assertEqual(placeholders(translated), placeholders(text))

    def test_portuguese_is_the_source_and_never_looked_up(self):
        self.assertEqual(t("Resumo"), "Resumo")
        self.assertEqual(t("{n} respostas", n=3), "3 respostas")

    def test_a_missing_translation_falls_back_to_portuguese_and_is_recorded(self):
        traducao.MISSING.clear()
        self.assertEqual(t("texto que não existe no catálogo", "en"), "texto que não existe no catálogo")
        self.assertIn(("en", "texto que não existe no catálogo"), traducao.MISSING)
        traducao.MISSING.clear()


# Strings the catalogue translates that the analyser cannot see being asked for, because the code
# hands them to `_t` through a variable. Each one says where.
DYNAMIC_STRINGS = {
    "Banco de casos": "html_report: `_t(label)` over the rows of the conditions list",
    "todas as amostras corretas": "html_report: `_t(meaning)` in the legend of the grid",
    "algumas amostras corretas": "html_report: `_t(meaning)` in the legend of the grid",
    "nenhuma amostra correta": "html_report: `_t(meaning)` in the legend of the grid",
    "Este documento mede um sistema, não um doente. Não aconselha, não trata e não substitui julgamento clínico.":
        "html_report: `_t(HEADER_NOTE)` in the footer",
}


class TestNoDeadStrings(unittest.TestCase):
    """The catalogue keeps no translation nobody asks for, outside a short, explicit list."""

    def test_every_string_of_the_catalogue_is_used_or_is_a_listed_dynamic_one(self):
        asked = interface_strings()  # once: it parses the sources, and the catalogue has hundreds of entries
        unused = sorted(s for s in CATALOG if s not in asked and s not in DYNAMIC_STRINGS)
        self.assertEqual(
            unused, [],
            "cadeias do catálogo que o código já não pede e que não estão na lista de exceções dinâmicas "
            f"({len(unused)}): " + " | ".join(s[:70] for s in unused)
            + ". Quem as apaga é o Fábio: nada foi apagado.",
        )

    def test_the_dynamic_ones_are_in_the_catalogue_and_are_really_not_found_by_the_analyser(self):
        """So the list of exceptions does not rot: a string the analyser now finds leaves it."""
        asked = interface_strings()
        for text, where in DYNAMIC_STRINGS.items():
            with self.subTest(cadeia=text[:40], onde=where):
                self.assertIn(text, CATALOG)
                self.assertNotIn(text, asked, "o analisador já a encontra: sai da lista de exceções")


class TestNoDashes(unittest.TestCase):
    """The text of the interface is written without em or en dashes, in every language."""

    def test_no_translation_has_an_em_or_en_dash(self):
        offenders = [
            (lang, text) for text, by_lang in CATALOG.items()
            for lang, translated in {"pt": text, **by_lang}.items()
            if "\u2014" in translated or "\u2013" in translated
        ]
        self.assertEqual(offenders, [])

    def test_the_visible_interface_of_a_page_has_none_either(self):
        for lang in LANGS:
            with self.subTest(lingua=lang):
                page = page_of([a_case()], [an_answer("500 mg")], lingua=lang)
                shown = re.sub(r"<(blockquote|style)[^>]*>.*?</\\1>", "", page, flags=re.S)
                self.assertNotIn("\u2014", shown)
                self.assertNotIn("\u2013", shown)


class TestNoOverclaimAboutWhenCriteriaWereSet(unittest.TestCase):
    """The criteria of a case are in code and have a history; only a protocol written before the trial is a
    prior criterion. No interface string may say otherwise, whatever the language."""

    FORBIDDEN = (
        "critérios de aceitação definidos antes",
        "critérios definidos previamente",
        "acceptance criteria defined before",
        "criterios de aceptación definidos antes",
        "critères d'acceptation définis avant",
        "vor dem Test festgelegte Akzeptanzkriterien",
    )

    def test_no_interface_string_says_the_criteria_were_defined_before_the_trial(self):
        texts = set(interface_strings()) | {s for s in CATALOG} | {v for row in CATALOG.values() for v in row.values()}
        for text in texts:
            for phrase in self.FORBIDDEN:
                with self.subTest(frase=phrase):
                    self.assertNotIn(phrase, text)


class TestOneTermForTrial(unittest.TestCase):
    """"Ensaio" is one thing in the report, so it has one name in each language. ("Banco de ensaio" is
    another thing, a test bench, and is left out.)"""

    TERMS = {"en": ("trial", "test"), "es": ("ensayo", "prueba"), "fr": ("essai", None), "de": ("Versuch", "Test")}

    def test_every_string_that_says_trial_uses_the_same_word_in_each_language(self):
        strings = [s for s in interface_strings() if "ensaio" in s.lower() and "banco de ensaio" not in s.lower()]
        self.assertTrue(strings)
        for text in strings:
            row = CATALOG[text]
            for lang, (word, other) in self.TERMS.items():
                with self.subTest(lingua=lang, cadeia=text[:50]):
                    self.assertIn(word.lower(), row[lang].lower())
                    if other:
                        self.assertNotRegex(row[lang], rf"\b{other}", f"{lang} diz '{other}' onde as outras cadeias dizem '{word}'")


class TestMachineTranslation(unittest.TestCase):
    def test_only_languages_the_report_has_can_be_unreviewed_and_portuguese_never_is(self):
        self.assertTrue(set(traducao.UNREVIEWED) <= set(LANGS))
        self.assertNotIn("pt", traducao.UNREVIEWED)

    def test_every_language_but_portuguese_is_unreviewed_until_a_native_speaker_has_read_it(self):
        self.assertEqual(set(traducao.UNREVIEWED), set(LANGS) - {"pt"})


class TestGrammaticalForms(unittest.TestCase):
    """German changes the adjective with the case, so one translation of "falha crítica" cannot
    serve "mit mindestens einem ...", "einen ..." and "mit ... in einer ..." at once."""

    def page(self, lang: str) -> str:
        return page_of([a_case()], [an_answer("500 mg")], lingua=lang)

    def test_german_declines_the_term_where_the_sentence_needs_it(self):
        text = self.page("de")
        # "... zeigt die Fälle mit mindestens einem kritischen Fehler"
        self.assertRegex(text, r"mit mindestens einem <abbr[^>]*>kritischen Fehler</abbr>")
        # "... hat nicht unbedingt einen kritischen Fehler"
        self.assertRegex(text, r"nicht unbedingt einen <abbr[^>]*>kritischen Fehler</abbr>")
        # "von 1 Fällen mit kritischem Fehler in mindestens einer Stichprobe"
        self.assertRegex(text, r"Fällen mit <abbr[^>]*>kritischem Fehler</abbr> in mindestens einer Stichprobe")

    def test_the_nominative_is_kept_where_the_sentence_has_the_term_alone(self):
        self.assertRegex(self.page("de"), r"in dem ein <abbr[^>]*>kritischer Fehler</abbr> auftritt")

    def test_the_other_languages_read_the_same_in_every_form(self):
        for lang in ("pt", "en", "es", "fr"):
            for form in ("", "com artigo", "sem artigo"):
                with self.subTest(lingua=lang, form=form):
                    self.assertEqual(t("falha crítica", lang, form=form), t("falha crítica", lang))

    def test_a_form_falls_back_to_the_plain_entry_without_counting_as_missing(self):
        traducao.MISSING.clear()
        self.assertEqual(t("falha crítica", "en", form="com artigo"), "critical failure")
        self.assertEqual(traducao.MISSING, set())

    def test_every_form_belongs_to_a_catalogue_term_and_a_known_language(self):
        for (term, form), versions in traducao.FORMS.items():
            with self.subTest(term=term, form=form):
                self.assertIn(term, CATALOG)
                self.assertTrue(form)
                self.assertTrue(set(versions) <= set(LANGS[1:]))
                self.assertTrue(all(v.strip() for v in versions.values()))

    def test_the_glossary_key_stays_portuguese_whatever_the_form(self):
        self.assertIn('data-termo="falha crítica"', self.page("de"))


class TestReportInEveryLanguage(unittest.TestCase):
    """A real trial, with a protocol, built in each language, uses no string the catalogue lacks."""

    @classmethod
    def setUpClass(cls):
        cls.cases = read_cases(TRIAL / "casos.json")
        cls.answers = read_answers(TRIAL / "respostas.jsonl")
        cls.verdicts, cls.missing = grade_all(cls.cases, cls.answers)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.json"
            path.write_text(json.dumps(template("x", TRIAL / "casos.json", today=date(2026, 9, 1))), encoding="utf-8")
            cls.protocol = read_protocol(path)
        alternates = {lang: f"index.{lang}.html" for lang in LANGS}
        traducao.MISSING.clear()
        cls.pages = {
            lang: html_report.build(
                cls.cases, cls.answers, cls.verdicts, missing=cls.missing,
                today=date(2026, 9, 28), protocol=cls.protocol, lingua=lang, alternates=alternates,
            )
            for lang in LANGS
        }

    def test_no_string_was_left_untranslated(self):
        self.assertEqual(traducao.MISSING, set())

    def test_the_page_declares_its_language(self):
        self.assertIn('<html lang="en">', self.pages["en"])
        self.assertIn('<html lang="pt-PT">', self.pages["pt"])

    def test_the_interface_is_in_the_chosen_language(self):
        self.assertIn("Aims.", self.pages["en"])
        self.assertNotIn("Objetivos.", self.pages["en"])
        self.assertIn("Objectifs.", self.pages["fr"])
        self.assertIn("Ziele.", self.pages["de"])

    def test_the_answers_and_the_cases_stay_in_portuguese(self):
        answer = html_report._esc(self.answers[0].text)
        question = html_report._esc(self.cases[0].question)
        for lang, page in self.pages.items():
            with self.subTest(lang=lang):
                self.assertIn(question, page)
        self.assertIn(answer[:80], self.pages["pt"])
        self.assertIn("Language of the cases.", self.pages["en"])

    def test_the_menu_links_every_language_and_marks_the_current_one(self):
        page = self.pages["fr"]
        for lang in LANGS:
            self.assertIn(f'href="index.{lang}.html"', page)
        self.assertIn('lang="fr" aria-current="page"', page)

    def test_still_no_script_in_any_language(self):
        for page in self.pages.values():
            self.assertNotIn("<script", page)

    def test_the_count_of_cases_is_said_in_the_language_of_the_page(self):
        """"a de n" is a sentence fragment, not a name: it was once listed as the same in every
        language, so the chart of the Results page and the maps said "8 de 27" in English, French and German."""
        joiner = {"pt": "de", "en": "of", "es": "de", "fr": "sur", "de": "von"}
        for lang, page in self.pages.items():
            counts = re.findall(r'class="comp-valor">(\d+ \S+ \d+) ', page)
            with self.subTest(lang=lang):
                self.assertTrue(counts)
                self.assertEqual({c.split()[1] for c in counts}, {joiner[lang]})
                if lang != "pt":
                    self.assertEqual(CATALOG["{a} de {n}"][lang], f"{{a}} {joiner[lang]} {{n}}")


class TestSingleLanguage(unittest.TestCase):
    def test_without_alternates_there_is_no_menu(self):
        page = page_of([a_case()], [an_answer("1 g")])
        self.assertNotIn('class="linguas"', page)

    def test_an_unknown_language_is_refused(self):
        with self.assertRaises(ValueError):
            page_of([a_case()], [an_answer("1 g")], lingua="xx")


class TestCommand(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_one_file_per_language_next_to_the_first(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "index.html"
            code, _, _ = self.run_cli(
                "relatorio", "--formato", "html", "--casos", str(TRIAL / "casos.json"),
                "--respostas", str(TRIAL / "respostas.jsonl"), "--saida", str(out),
                "--linguas", "pt,en,de",
            )
            self.assertEqual(code, 0)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()),
                             ["index.de.html", "index.en.html", "index.html"])
            self.assertIn('href="index.html"', (Path(folder) / "index.de.html").read_text(encoding="utf-8"))

    def test_languages_are_refused_for_markdown(self):
        code, _, err = self.run_cli("relatorio", "--linguas", "en", "--respostas", str(TRIAL / "respostas.jsonl"),
                                    "--casos", str(TRIAL / "casos.json"))
        self.assertEqual(code, 2)
        self.assertIn("só se aplica ao formato html", err)


if __name__ == "__main__":
    unittest.main()
