"""Nothing in the documents or in the page promises a clinical reviewer that does not exist."""

from __future__ import annotations

import html
import unittest
from pathlib import Path

from aferidor.traducao import LANGS
from tests.html_support import _Example

ROOT = Path(__file__).resolve().parent.parent


class TestNothingPromisesAReviewer(unittest.TestCase):
    PROMISES = ("o especialista valida", "concentra o tempo do especialista", "falta um clínico disponível",
                "Prepara a validação pelo especialista", "Preparar a validação por um especialista", "revisão clínica de uma amostra de respostas reais",
                "triagem pela ferramenta, validação pelo especialista")

    def test_no_document_says_a_specialist_validates_or_that_one_is_about_to(self):
        for name in ("README.md", "docs/APRESENTACAO.md", "docs/METODO.md", "docs/COMO_CORRER.md", "docs/QUALIDADE.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for phrase in self.PROMISES:
                with self.subTest(documento=name, frase=phrase):
                    self.assertNotIn(phrase, text)

    def test_the_documents_say_there_is_no_reviewer_and_that_the_sheet_waits_for_one(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Não há\nrevisor clínico", readme)
        self.assertIn("sem validação clínica", readme)
        self.assertIn("estão\npreparadas para o dia em que houver um revisor", readme)
        presentation = (ROOT / "docs" / "APRESENTACAO.md").read_text(encoding="utf-8")
        self.assertIn("Não há validação clínica nem revisor", presentation)
        method = (ROOT / "docs" / "METODO.md").read_text(encoding="utf-8")
        self.assertIn("Não há revisor clínico e não há data.", method)

    def test_the_page_does_not_say_it_in_any_language_and_says_the_sheet_is_ready_if_there_is_a_reviewer(self):
        old = {"pt": "Preparar a validação por um especialista", "en": "Prepare validation by a specialist", "es": "Preparar la validación por un especialista",
               "fr": "Préparer la validation par un spécialiste", "de": "Die Validierung durch eine Fachperson vorbereiten"}
        new = {"pt": "Ter a folha cega pronta, se houver revisor.", "en": "Have the blind sheet ready, if there is a reviewer.",
               "es": "Tener lista la hoja ciega, si hay revisor.", "fr": "Avoir la feuille en aveugle prête, s'il y a un relecteur.",
               "de": "Den verblindeten Bogen bereithalten, falls es eine Gutachterin oder einen Gutachter gibt."}
        for lang in LANGS:
            with self.subTest(lingua=lang):
                page = html.unescape(_Example.page(lingua=lang))
                self.assertNotIn(old[lang], page)
                self.assertIn(new[lang], page)

    def test_the_markdown_triage_note_says_there_is_no_reviewer(self):
        from aferidor import report
        self.assertIn("sem validação clínica: não há revisor", report.TRIAGE_NOTE)
        self.assertNotIn("faz-se à parte", report.TRIAGE_NOTE)


if __name__ == "__main__":
    unittest.main()
