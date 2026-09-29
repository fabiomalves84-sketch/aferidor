"""Checking the grader against a person: the sample, the blind sheet, the agreement."""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

from aferidor.cli import main
from aferidor.grading import grade_all, wilson_interval
from aferidor.models import Answer, Case, Criterion, Source
from aferidor.revisao import (
    Agreement,
    format_agreement,
    key_path_for,
    read_review,
    sample_for_review,
    write_review,
)
from aferidor.risk import FailureType
from aferidor.runner import build_prompt, prompt_digest
from aferidor.storage import write_answers, write_cases


def a_case(case_id: str) -> Case:
    return Case(
        case_id=case_id, category="dose", question=f"Que dose no caso {case_id}?",
        reference="Amoxicilina 1000 mg", source=Source(name="Guia", reference="p. 1"),
        criteria=(Criterion(kind="contem", terms=("1000 mg",), failure=FailureType.DOSE_INCORRETA),),
    )


def a_run(right: int, wrong: int) -> tuple[list[Case], list[Answer]]:
    cases = [a_case(f"C{i:02d}") for i in range(right + wrong)]
    answers = [
        Answer(
            case_id=c.case_id, model="modelo-x",
            text="Amoxicilina 1000 mg" if i < right else "Amoxicilina 500 mg",
            asked_at=datetime(2026, 9, 27),
        )
        for i, c in enumerate(cases)
    ]
    return cases, answers


class TestSample(unittest.TestCase):
    def test_the_sample_is_half_passed_and_half_failed(self):
        cases, answers = a_run(right=20, wrong=20)
        verdicts, _ = grade_all(cases, answers)
        items = sample_for_review(cases, answers, verdicts, n=10, seed=1)
        self.assertEqual(sum(i.grader_passed for i in items), 5)

    def test_the_short_side_is_filled_by_the_other(self):
        cases, answers = a_run(right=2, wrong=20)
        verdicts, _ = grade_all(cases, answers)
        items = sample_for_review(cases, answers, verdicts, n=10, seed=1)
        self.assertEqual(len(items), 10)
        self.assertEqual(sum(i.grader_passed for i in items), 2)

    def test_the_same_seed_gives_the_same_sample(self):
        cases, answers = a_run(right=20, wrong=20)
        verdicts, _ = grade_all(cases, answers)
        first = sample_for_review(cases, answers, verdicts, n=10, seed=7)
        second = sample_for_review(cases, answers, verdicts, n=10, seed=7)
        self.assertEqual([i.case.case_id for i in first], [i.case.case_id for i in second])

    def test_an_answer_to_a_question_worded_differently_is_left_out(self):
        """The sheet shows today's question; an answer given to another wording would be
        judged against a question the model never read."""
        cases, answers = a_run(right=2, wrong=0)
        answers[0] = Answer(
            case_id="C00", model="modelo-x", text="Amoxicilina 1000 mg",
            asked_at=datetime(2026, 9, 27), prompt_sha256="0" * 64,
        )
        answers[1] = Answer(
            case_id="C01", model="modelo-x", text="Amoxicilina 1000 mg",
            asked_at=datetime(2026, 9, 27), prompt_sha256=prompt_digest(build_prompt(cases[1])),
        )
        verdicts, _ = grade_all(cases, answers)
        items = sample_for_review(cases, answers, verdicts, n=10, seed=1)
        self.assertEqual([i.case.case_id for i in items], ["C01"])


class TestSheet(unittest.TestCase):
    def write(self, folder: str):
        cases, answers = a_run(right=3, wrong=3)
        verdicts, _ = grade_all(cases, answers)
        items = sample_for_review(cases, answers, verdicts, n=6, seed=1)
        source = Path(folder) / "respostas.jsonl"
        write_answers(answers, source)
        sheet = Path(folder) / "revisao.csv"
        write_review(items, sheet, key_path_for(sheet), source)
        return sheet, items

    def test_the_sheet_is_blind_to_the_verdict_and_the_model(self):
        with tempfile.TemporaryDirectory() as folder:
            sheet, _ = self.write(folder)
            text = sheet.read_text(encoding="utf-8-sig")
        self.assertNotIn("modelo-x", text)
        self.assertNotIn("corretor", text)
        self.assertIn("juizo", text.splitlines()[0])

    def test_an_answer_that_looks_like_a_formula_is_written_as_text(self):
        """A spreadsheet evaluates "=..." and reads "- item" as a formula; the reviewer must see text."""
        cases = [a_case("C1")]
        answers = [
            Answer("C1", "modelo-x", "=HYPERLINK(\"http://x\")", datetime(2026, 9, 1), sample=1),
            Answer("C1", "modelo-x", "- Amoxicilina 1000 mg", datetime(2026, 9, 1), sample=2),
        ]
        verdicts, _ = grade_all(cases, answers)
        items = sample_for_review(cases, answers, verdicts, n=2, seed=1)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "respostas.jsonl"
            write_answers(answers, source)
            sheet = Path(folder) / "revisao.csv"
            write_review(items, sheet, key_path_for(sheet), source)
            with sheet.open(encoding="utf-8-sig", newline="") as handle:
                cells = [row["resposta_do_modelo"] for row in csv.DictReader(handle, delimiter=";")]
        self.assertTrue(all(c.startswith("'") for c in cells), cells)

    def test_the_key_records_the_verdict_and_the_answers_file_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            sheet, items = self.write(folder)
            key = json.loads(key_path_for(sheet).read_text(encoding="utf-8"))
        self.assertEqual(len(key["respostas_sha256"]), 64)
        self.assertEqual(
            key["itens"][items[0].review_id]["corretor"],
            "certa" if items[0].grader_passed else "errada",
        )

    def fill(self, sheet: Path, judge) -> None:
        with sheet.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        for row in rows:
            row["juizo"] = judge(row)
        with sheet.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    def test_a_reviewer_who_agrees_everywhere_gives_full_agreement(self):
        with tempfile.TemporaryDirectory() as folder:
            sheet, _ = self.write(folder)
            self.fill(sheet, lambda r: "certa" if "1000 mg" in r["resposta_do_modelo"] else "errada")
            result = read_review(sheet, key_path_for(sheet))
        self.assertEqual((result.agreement, result.false_pass, result.false_fail), (1.0, 0, 0))
        self.assertEqual(result.kappa, 1.0)

    def test_a_wrong_answer_the_grader_passed_is_a_false_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            sheet, _ = self.write(folder)
            self.fill(sheet, lambda r: "errada")
            result = read_review(sheet, key_path_for(sheet))
        self.assertEqual(result.false_pass, 3)
        self.assertEqual(result.false_pass_rate, 0.5)

    def test_blank_rows_are_counted_as_not_yet_judged(self):
        with tempfile.TemporaryDirectory() as folder:
            sheet, _ = self.write(folder)
            self.fill(sheet, lambda r: "" if r["revisao"] == "R001" else "Certa")
            result = read_review(sheet, key_path_for(sheet))
        self.assertEqual(result.unjudged, ("R001",))
        self.assertEqual(result.judged, 5)

    def test_an_unknown_judgement_is_refused_with_its_row(self):
        with tempfile.TemporaryDirectory() as folder:
            sheet, _ = self.write(folder)
            self.fill(sheet, lambda r: "talvez")
            with self.assertRaises(ValueError) as raised:
                read_review(sheet, key_path_for(sheet))
        self.assertIn("R00", str(raised.exception))


class TestAgreementNumbers(unittest.TestCase):
    def test_kappa_on_a_known_table(self):
        # 20 both right, 15 both wrong, 5 false passes, 10 false fails.
        result = Agreement(both_right=20, both_wrong=15, false_pass=5, false_fail=10, unjudged=())
        self.assertAlmostEqual(result.agreement, 0.70)
        self.assertAlmostEqual(result.kappa, 0.40, places=2)

    def test_the_false_pass_comes_first_in_the_text(self):
        result = Agreement(both_right=20, both_wrong=15, false_pass=5, false_fail=10, unjudged=())
        self.assertTrue(format_agreement(result).startswith("Passagens falsas: 5 de 20"))

    def test_nothing_judged_says_so(self):
        result = Agreement(0, 0, 0, 0, unjudged=("R001",))
        self.assertIn("Nenhuma resposta julgada", format_agreement(result))

    def test_the_wilson_interval_matches_known_values(self):
        low, high = wilson_interval(5, 10)
        self.assertAlmostEqual(low, 0.2366, places=3)
        self.assertAlmostEqual(high, 0.7634, places=3)
        self.assertEqual(wilson_interval(0, 27)[0], 0.0)
        self.assertAlmostEqual(wilson_interval(0, 27)[1], 0.1246, places=3)


class TestCommands(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_an_existing_sheet_is_never_overwritten_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            cases, answers = a_run(right=3, wrong=3)
            write_cases(cases, f / "casos.json")
            write_answers(answers, f / "r.jsonl")
            base = ("revisao", "--casos", str(f / "casos.json"), "--respostas", str(f / "r.jsonl"),
                    "--n", "4", "--saida", str(f / "rev.csv"))
            self.assertEqual(self.run_cli(*base)[0], 0)
            (f / "rev.csv").write_text("trabalho da médica", encoding="utf-8")
            code, _, err = self.run_cli(*base)
            self.assertEqual(code, 2)
            self.assertEqual((f / "rev.csv").read_text(encoding="utf-8"), "trabalho da médica")
            self.assertIn("--substituir", err)

    def test_old_answers_without_a_prompt_hash_are_flagged(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            cases, answers = a_run(right=2, wrong=2)
            write_cases(cases, f / "casos.json")
            write_answers(answers, f / "r.jsonl")
            code, _, err = self.run_cli(
                "revisao", "--casos", str(f / "casos.json"), "--respostas", str(f / "r.jsonl"),
                "--n", "4", "--saida", str(f / "rev.csv"),
            )
        self.assertEqual(code, 0)
        self.assertIn("não guardaram o texto", err)

    def test_concordancia_with_nothing_judged_exits_1(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)
            cases, answers = a_run(right=2, wrong=2)
            write_cases(cases, f / "casos.json")
            write_answers(answers, f / "r.jsonl")
            self.run_cli("revisao", "--casos", str(f / "casos.json"), "--respostas",
                         str(f / "r.jsonl"), "--n", "4", "--saida", str(f / "rev.csv"))
            code, out, _ = self.run_cli("concordancia", "--revisao", str(f / "rev.csv"))
        self.assertEqual(code, 1)
        self.assertIn("Nenhuma resposta julgada", out)


if __name__ == "__main__":
    unittest.main()
