"""The real case set is data, and data breaks. These tests guard it."""

import unittest
from pathlib import Path

from aferidor.risk import FailureType
from aferidor.storage import read_cases

CASES = Path(__file__).resolve().parent.parent / "casos" / "casos.json"
BANK = Path(__file__).resolve().parent.parent / "casos" / "consulta.json"


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

    def test_every_failure_type_in_the_taxonomy_is_measured_by_some_case(self):
        """A taxonomy that names a failure nobody can trigger is a promise the bench
        does not keep, and it fails silently: the report shows zero of that failure
        whether the models are clean or the cases simply never ask."""
        # The taxonomy is shared by both banks, so coverage is measured across them.
        both = self.cases + read_cases(BANK)
        measured = {cr.failure for c in both for cr in c.all_criteria}
        missing = sorted(f.value for f in FailureType if f not in measured)
        self.assertEqual(missing, [], f"tipos de falha sem nenhum caso: {missing}")

    # Critical failure types measured by a single case, known and waiting for a
    # second one. A second case is a clinical decision, not a code change; when
    # it is added, the type comes off this list and the test holds it there.
    ONE_CASE_ONLY = {"encaminhamento_omitido"}

    def test_every_critical_failure_is_measured_by_more_than_one_case(self):
        """One case per critical type makes that type's count hinge on a single question."""
        from collections import Counter

        both = self.cases + read_cases(BANK)
        counts = Counter(f for c in both for f in {cr.failure for cr in c.all_criteria})
        thin = {
            f.value for f in FailureType if f.risk.name == "CRITICO" and counts[f] < 2
        }
        self.assertEqual(thin, self.ONE_CASE_ONLY)

    def test_every_criterion_catches_its_negative_control(self):
        from aferidor.grading import uncaught_controls

        _, uncaught = uncaught_controls(self.cases)
        self.assertEqual([(c.case_id, c.change) for c, _ in uncaught], [])

    def test_every_case_appears_in_the_verification_table(self):
        table = (CASES.parent / "VERIFICACAO.md").read_text(encoding="utf-8")
        for case in self.cases:
            with self.subTest(case=case.case_id):
                self.assertIn(case.case_id, table)


class TestAnnotatedBank(unittest.TestCase):
    """The 30-case bank with risk levels, review state and source sections."""

    @classmethod
    def setUpClass(cls):
        import json

        cls.raw = json.loads(BANK.read_text(encoding="utf-8"))
        cls.cases = read_cases(BANK)

    def test_it_loads_every_case(self):
        self.assertEqual(len(self.cases), len(self.raw["casos"]))
        self.assertGreaterEqual(len(self.cases), 30)

    def test_every_reference_passes_its_own_criteria(self):
        from aferidor.grading import self_check

        broken = [case.case_id for case, _ in self_check(self.cases)]
        self.assertEqual(broken, [])

    def test_every_criterion_catches_its_negative_control(self):
        from aferidor.grading import uncaught_controls

        _, uncaught = uncaught_controls(self.cases)
        self.assertEqual([(c.case_id, c.change) for c, _ in uncaught], [])

    def test_every_case_appears_in_the_verification_table_with_an_unmarked_box(self):
        """The person who confirms the source needs a row to confirm it in. The box
        is only ever marked by that person, so a test cannot require it marked;
        it only requires the row to exist."""
        table = (BANK.parent / "VERIFICACAO.md").read_text(encoding="utf-8")
        section = table[table.index("## Banco de consulta"):]
        for item in self.raw["casos"]:
            with self.subTest(case=item["id"]):
                self.assertRegex(section, rf"\| {item['id']} \|.*\| \[[ x]\] \|")

    def test_every_case_records_a_source_a_type_and_a_verification_date(self):
        for item in self.raw["casos"]:
            with self.subTest(case=item["id"]):
                self.assertTrue(item["fonte"].strip())
                self.assertIn(item["fonte_tipo"], ("primaria", "secundaria"))
                self.assertTrue(item["data_verificacao"])

    def test_every_high_risk_case_has_a_critical_error_listed(self):
        for item in self.raw["casos"]:
            if item["risco"] == "alto":
                with self.subTest(case=item["id"]):
                    self.assertTrue(item["erros_criticos"])


if __name__ == "__main__":
    unittest.main()
