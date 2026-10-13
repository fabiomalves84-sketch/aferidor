"""What the page says about the correction is worked out, never written: the functions that work it out."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aferidor import correcao
from aferidor.grading import mcnemar_exact
from tests.html_support import ROOT

BEFORE = ROOT / "docs" / "exemplo" / "antes-8edda161.json"
READING = ROOT / "docs" / "LEITURA_MUDANCAS_2026-10-13.md"


class TestNamingADrugIsNotRecommendingIt(unittest.TestCase):
    def test_it_counts_a_mention_the_answer_does_not_exclude(self):
        for text in ("Cefalexina 500 mg de 6 em 6 horas.", "Fármaco: Cefalexina", "Alternativas quando X não é adequado: cefalexina 500 mg",
                     "A cefalexina (cefalosporina de 1.ª geração) é uma opção."):
            with self.subTest(texto=text):
                self.assertTrue(correcao.names_without_excluding(text))

    def test_it_does_not_count_one_the_answer_excludes_or_another_drug(self):
        for text in ("Não usar cefalexina.", "A cefalexina está contraindicada: usar outra.", "Cefuroxima 250 mg de 12 em 12 horas.", ""):
            with self.subTest(texto=text):
                self.assertFalse(correcao.names_without_excluding(text))


class TestTheBestPair(unittest.TestCase):
    def test_the_two_with_the_fewest_critical_cases_and_the_exact_test_between_them(self):
        by_model = {
            "a": {"c1": True, "c2": False, "c3": False, "c4": False},
            "b": {"c1": False, "c2": True, "c3": True, "c4": False},
            "c": {"c1": True, "c2": True, "c3": True, "c4": True},
        }
        pair = correcao.best_pair(by_model)
        self.assertEqual((pair.first, pair.second, pair.first_critical, pair.cases), ("a", "b", 1, 4))
        self.assertEqual((pair.only_first, pair.only_second), (1, 2))
        self.assertEqual(pair.p_value, mcnemar_exact(1, 2))

    def test_a_tie_goes_to_the_name_and_a_single_model_has_no_pair(self):
        tie = {"b": {"c1": True, "c2": False}, "a": {"c1": False, "c2": True}}
        self.assertEqual(correcao.best_pair(tie).first, "a")
        self.assertIsNone(correcao.best_pair({"a": {"c1": True}}))


class TestTheCorrectionOfThePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.correction = correcao.compute(BEFORE, ROOT / "ensaios", ROOT)

    def test_it_names_the_two_correctors_and_the_commit_of_the_published_one(self):
        c = self.correction
        self.assertEqual(c.before_grader, "0.1.0+corretor.8edda161bd4e")
        self.assertTrue(c.before_commit.startswith("e272ab9"))
        self.assertRegex(c.after_grader, r"^0\.1\.0\+corretor\.[0-9a-f]{12}$")
        self.assertNotEqual(c.before_grader, c.after_grader)

    def test_the_figures_before_are_those_of_the_file_and_not_of_the_current_code(self):
        data = json.loads(BEFORE.read_text(encoding="utf-8"))
        for row in self.correction.rows:
            cases = {}
            for model, case, _s, _p, critical, _f, _a in data["ensaios"][row.trial]["respostas"]:
                if model == row.model:
                    cases[case] = cases.get(case, False) or bool(critical)
            self.assertEqual((row.before, row.cases), (sum(cases.values()), len(cases)), row.trial)

    def test_the_page_models_are_there_in_both_banks_and_the_26b_is_marked_as_frozen(self):
        banks = {(r.bank, r.model.split(":")[-1]) for r in self.correction.rows}
        for bank in ("principal", "consulta"):
            for model in ("gemma-4-31b-it", "gemini-3.5-flash-lite", "gemma-4-26b-a4b-it"):
                self.assertIn((bank, model), banks)
        self.assertEqual({r.model for r in self.correction.rows if r.frozen}, {"gemini:gemma-4-26b-a4b-it"})

    def test_the_correction_made_no_model_better_and_the_page_may_say_so_only_because_this_is_empty(self):
        self.assertEqual(self.correction.fell, ())
        self.assertTrue(self.correction.rose)

    def test_the_best_pair_before_is_the_published_one(self):
        before = self.correction.best_before
        self.assertEqual((before.first_critical, before.cases), (8, 27))
        self.assertAlmostEqual(before.p_value, 0.375)
        self.assertGreaterEqual(self.correction.best_after.first_critical, before.first_critical)

    def test_the_cases_affected_are_counted_and_u1_alone_is_part_of_the_whole(self):
        (u1_criteria, u1_cases), (all_criteria, all_cases) = self.correction.equivalent_forms, self.correction.all_corrections
        self.assertEqual((u1_criteria, u1_cases, all_criteria, all_cases), (40, 11, 197, 18))
        self.assertLessEqual(u1_criteria, all_criteria)
        self.assertLessEqual(u1_cases, all_cases)
        self.assertEqual(self.correction.trials_counted, 10)

    def test_the_cephalexin_count_is_per_model_out_of_five_answers(self):
        counts = {m: (n, total) for m, n, total in self.correction.cephalexin}
        self.assertEqual(set(counts), {"gemini:gemma-4-31b-it", "gemini:gemini-3.5-flash-lite", "gemini:gemma-4-26b-a4b-it", "local:gemma3:12b", "local:phi4:14b"})
        for name, (n, total) in counts.items():
            self.assertEqual(total, 5, name)
            self.assertLessEqual(n, total)

    def test_a_file_whose_answers_changed_is_refused(self):
        data = json.loads(BEFORE.read_text(encoding="utf-8"))
        first = next(iter(data["ensaios"]))
        data["ensaios"][first]["respostas_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder:
            altered = Path(folder) / "antes.json"
            altered.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "já não é o que o ficheiro do corretor publicado leu"):
                correcao.compute(altered, ROOT / "ensaios", ROOT)


class TestTheReadingOfTheChanges(unittest.TestCase):
    """docs/LEITURA_MUDANCAS_2026-10-13.md says what each change of the state of critical failure is; it only counts if it matches the data."""

    @classmethod
    def setUpClass(cls):
        cls.correction = correcao.compute(BEFORE, ROOT / "ensaios", ROOT, READING)

    def test_the_changes_of_state_are_the_ones_the_data_give_and_each_is_in_the_file(self):
        computed = sorted((c.model, c.case) for c in self.correction.changes)
        written = sorted((m, k) for m, k, _c in correcao.read_rows(READING))
        self.assertEqual(computed, written)
        self.assertTrue(all(c.now_critical for c in self.correction.changes))  # none stopped having a critical failure

    def test_the_counts_of_the_summary_are_those_of_the_lines(self):
        n, a, b, c = self.correction.reading
        classes = [k for _m, _c, k in correcao.read_rows(READING)]
        self.assertEqual((n, a, b, c), (len(classes), classes.count("a"), classes.count("b"), classes.count("c")))
        self.assertEqual(n, len(self.correction.changes))
        text = READING.read_text(encoding="utf-8")
        self.assertIn(f"Classes: (a) {a}, (b) {b}, (c) {c}", text)
        self.assertIn(f"{n} mudanças de estado", text)

    def test_the_samples_written_are_the_samples_that_cause_the_change(self):
        for change in self.correction.changes:
            lines = [line for line in READING.read_text(encoding="utf-8").splitlines() if f"`{change.model}`" in line and change.case in line]
            self.assertEqual(len(lines), 1)
            self.assertIn(", ".join(map(str, change.samples)), lines[0], (change.model, change.case))

    def test_the_reading_of_13_october_has_no_false_failure_so_the_table_depends_on_none(self):
        self.assertEqual(self.correction.reading, (9, 9, 0, 0))
        self.assertIsNone(self.correction.sensitivity)

    def test_the_sensitivity_is_worked_out_from_the_reading_and_says_which_numbers_depend_on_the_false_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            marked = Path(folder) / "leitura.md"
            text = READING.read_text(encoding="utf-8")
            for model, case in (("gemini:gemini-3.5-flash-lite", "ATB-FAR-014"), ("gemini:gemma-4-31b-it", "ATB-PAC-001")):
                line = next(l for l in text.splitlines() if f"`{model}`" in l and case in l)
                text = text.replace(line, line.replace("| a |", "| b |"))
            marked.write_text(text, encoding="utf-8")
            s = correcao.compute(BEFORE, ROOT / "ensaios", ROOT, marked).sensitivity
        self.assertEqual(s.count, 2)
        rows = {(r.trial, r.model): r.after for r in self.correction.rows}
        for trial, model, _bank, after, without in s.items:
            self.assertEqual(after, rows[(trial, model)])
            self.assertEqual(without, after - 1)  # each false failure is the only cause of its case
        self.assertEqual({model for _t, model, *_ in s.items}, {"gemini:gemini-3.5-flash-lite", "gemini:gemma-4-31b-it"})
        self.assertGreaterEqual(s.pair_without.p_value, s.pair_after.p_value)

    def test_the_method_document_says_the_numbers_of_the_reading_and_the_rule_that_treated_the_pattern(self):
        n, a, b, c = self.correction.reading
        method = " ".join((ROOT / "docs" / "METODO.md").read_text(encoding="utf-8").split())
        self.assertIn(f"Li as {n} mudanças de estado de falha crítica", method)
        self.assertIn(f"{a} corretas, {b} falsos falhanços ou falsos passes e {c} ambíguas", method)
        self.assertIn("(P4)", method)
        self.assertNotIn("O padrão (i) é o próximo a tratar", method)

    def test_the_heading_rule_changes_three_criteria_in_the_stored_answers_and_the_documents_say_so(self):
        changed = []
        for new_path in sorted((ROOT / "ensaios").glob("*/vereditos-reclassificado-2026-10-13.json")):
            new = json.loads(new_path.read_text(encoding="utf-8"))
            old = json.loads(new_path.with_name("vereditos-reclassificado-2026-10-12.json").read_text(encoding="utf-8"))
            self.assertEqual([(x["caso"], x["modelo"]) for x in new], [(x["caso"], x["modelo"]) for x in old])
            for x, y in zip(new, old):
                if x["alternativa"] != y["alternativa"] or len(x["criterios"]) != len(y["criterios"]):
                    continue  # another alternative of the case was the one reported: the criteria are not the same ones
                changed += [(p["passou"], q["passou"]) for p, q in zip(x["criterios"], y["criterios"]) if p["passou"] != q["passou"]]
        self.assertEqual(len(changed), 3)
        self.assertTrue(all(was_new and not was_old for was_new, was_old in changed))  # all three went from fail to pass
        method = " ".join((ROOT / "docs" / "METODO.md").read_text(encoding="utf-8").split())
        self.assertIn("a P4 altera 3 critérios", method)
        self.assertIn("favorece os modelos", method)
        self.assertIn("medida com o corretor `8404de4a7c95`, anterior à P4", method)

    def test_a_reading_that_no_longer_matches_the_data_is_refused(self):
        text = READING.read_text(encoding="utf-8").replace("`local:phi4:14b` | ATB-PIEL-006", "`local:phi4:14b` | ATB-PAC-001")
        with tempfile.TemporaryDirectory() as folder:
            altered = Path(folder) / "leitura.md"
            altered.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "não corresponde às mudanças que os dados dão hoje"):
                correcao.compute(BEFORE, ROOT / "ensaios", ROOT, altered)


if __name__ == "__main__":
    unittest.main()
