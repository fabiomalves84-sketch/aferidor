"""`docs/exemplo/antes-8edda161.json`: what the published corrector said, kept so the page never writes a "before" by hand."""

from __future__ import annotations

import hashlib
import json
import unittest

from tests.html_support import ROOT

FILE = ROOT / "docs" / "exemplo" / "antes-8edda161.json"


class TestTheFileOfTheCorrectorThatWasPublished(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FILE.read_text(encoding="utf-8"))

    def test_it_says_which_commit_and_which_corrector_made_it(self):
        self.assertEqual(self.data["grader_id"], "0.1.0+corretor.8edda161bd4e")
        self.assertTrue(self.data["commit"].startswith("e272ab9"))

    def test_it_holds_every_stored_answers_file_and_its_hash_is_the_hash_of_the_file_today(self):
        folders = sorted(p.parent.name for p in (ROOT / "ensaios").glob("*/respostas.jsonl"))
        self.assertEqual(sorted(self.data["ensaios"]), folders)
        for folder, entry in self.data["ensaios"].items():
            with self.subTest(ensaio=folder):
                path = ROOT / "ensaios" / folder / "respostas.jsonl"
                self.assertEqual(entry["respostas_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(len(entry["respostas"]), len(path.read_text(encoding="utf-8").splitlines()))

    def test_every_row_has_the_seven_fields_and_a_critical_answer_is_a_failed_one(self):
        for folder, entry in self.data["ensaios"].items():
            for row in entry["respostas"]:
                self.assertEqual(len(row), 7, (folder, row))
                model, case, sample, passed, critical, flags, _alternative = row
                self.assertIn(passed, (0, 1))
                self.assertIn(critical, (0, 1))
                self.assertFalse(passed and critical)
                self.assertRegex(flags, r"^[01]+$")


if __name__ == "__main__":
    unittest.main()
