"""The real case set is data, and data breaks. These tests guard it."""

import unittest
from pathlib import Path

from aferidor.storage import read_cases

CASES = Path(__file__).resolve().parent.parent / "casos" / "casos.json"


class TestShippedCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = read_cases(CASES)

    def test_the_set_loads_and_is_not_empty(self):
        self.assertGreaterEqual(len(self.cases), 10)

    def test_every_case_cites_a_document_and_a_place_in_it(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                self.assertTrue(case.source.name.strip())
                self.assertTrue(case.source.reference.strip())
                self.assertTrue(case.source.url.startswith("https://"))

    def test_every_case_records_when_the_source_was_consulted(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                self.assertIsNotNone(case.source.consulted)

    def test_the_set_covers_more_than_dosing(self):
        categories = {c.category for c in self.cases}
        self.assertIn("dose", categories)
        self.assertIn("alergia", categories)
        self.assertGreaterEqual(len(categories), 4)

    def test_the_set_exercises_several_failure_types(self):
        failures = {cr.failure for c in self.cases for cr in c.criteria}
        self.assertGreaterEqual(len(failures), 4)

    def test_every_case_appears_in_the_verification_table(self):
        table = (CASES.parent / "VERIFICACAO.md").read_text(encoding="utf-8")
        for case in self.cases:
            with self.subTest(case=case.case_id):
                self.assertIn(case.case_id, table)


if __name__ == "__main__":
    unittest.main()
