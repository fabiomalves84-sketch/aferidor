"""The entry page of the published site (docs/index.html): what a visitor sees at the base address, before any report."""

from __future__ import annotations

import re
import unittest

from tests.html_support import ROOT

PAGE = ROOT / "docs" / "index.html"


class TestTheEntryPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.text = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)\b.*?</\1>", "", cls.html, flags=re.S)).split())

    def test_it_is_a_standalone_page_without_scripts_or_outside_resources(self):
        self.assertTrue(self.html.startswith("<!doctype html>"))
        self.assertIn('lang="pt-PT"', self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertNotIn("<script", self.html)
        self.assertNotRegex(self.html, r'(?:src|href)="(?!https://github\.com/fabiomalves84-sketch/aferidor|exemplo/|#)')
        self.assertNotRegex(self.html, r"<link\b")

    def test_it_says_at_the_top_what_it_is_not(self):
        self.assertLess(self.text.index("sem validação clínica"), self.text.index("O Aferidor põe"))
        for sentence in ("Mede, não aconselha", "Não é dispositivo médico", "não contém dados de doentes"):
            self.assertIn(sentence, self.text)
        self.assertNotRegex(self.text.lower(), r"\bvalidad[oa]s?\b(?! clínica)")
        self.assertNotIn("—", self.text)
        self.assertNotIn("--", self.text)

    def test_every_local_link_points_to_a_file_that_is_published(self):
        local = re.findall(r'href="(exemplo/[^"#]+)"', self.html)
        self.assertEqual(len(local), 5)
        for link in local:
            self.assertTrue((ROOT / "docs" / link).is_file(), link)

    def test_the_links_to_the_repository_point_to_files_that_exist(self):
        for path in re.findall(r'href="https://github\.com/fabiomalves84-sketch/aferidor/blob/main/([^"]+)"', self.html):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_it_says_the_translations_are_not_reviewed_and_the_numbers_depend_on_the_grader(self):
        self.assertIn("Estas quatro traduções não foram revistas", self.text)
        self.assertIn("Os números dependem da versão do corretor", self.text)


if __name__ == "__main__":
    unittest.main()
