"""Where the cases come from and how far their sources are confirmed, read from VERIFICACAO.md by id."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from aferidor import fontes
from aferidor.storage import read_cases

ROOT = Path(__file__).resolve().parent.parent
VERIFICATION = ROOT / "casos" / "VERIFICACAO.md"

TABLE = """# Verificação

| Caso | Fonte | Página | Valor | 2.ª leitura | Pessoa |
|---|---|---|---|---|---|
| AAA-01 | x | 1 | y | bate | [x] |
| AAA-02 | x | 1 | y | bate | [x] |
| AAA-03 | x | 1 | y | bate | [ ] |
| BBB-01 | x | 1 | y | bate | [x] |

### Confirmações registadas

**27/09/2026.** Marcadas as linhas de AAA-01 e BBB-01. Fontes: x.
"""


def a_folder_with(text: str) -> tuple[tempfile.TemporaryDirectory, Path]:
    folder = tempfile.TemporaryDirectory()
    path = Path(folder.name) / "VERIFICACAO.md"
    path.write_text(text, encoding="utf-8")
    return folder, path


class TestCountingByIdFromTheTable(unittest.TestCase):
    def test_marked_and_unmarked_are_read_from_the_last_column(self):
        folder, path = a_folder_with(TABLE)
        self.addCleanup(folder.cleanup)
        self.assertEqual(fontes.read_table(path), {"AAA-01": True, "AAA-02": True, "AAA-03": False, "BBB-01": True})

    def test_the_marked_ones_split_into_one_by_one_and_in_group_by_the_list(self):
        table = {"AAA-01": True, "AAA-02": True, "AAA-03": False, "ATB-PAC-001": True}
        counts = fontes.count(["AAA-01", "AAA-02", "AAA-03", "ATB-PAC-001"], table)
        self.assertEqual((counts.total, counts.one_by_one, counts.in_group, counts.pending), (4, 1, 2, 1))

    def test_a_case_with_no_row_is_named_and_counted_as_nothing(self):
        counts = fontes.count(["AAA-01", "ZZZ-99"], {"AAA-01": True})
        self.assertEqual(counts.without_row, ("ZZZ-99",))
        self.assertEqual((counts.total, counts.in_group, counts.pending), (2, 1, 0))

    def test_only_the_cases_of_the_report_are_counted_for_the_bank(self):
        table = {"AAA-01": True, "AAA-02": False, "AAA-03": False}
        result = fontes.confirmation(["AAA-01"], table)
        self.assertEqual((result.bank.total, result.project.total), (1, 3))

    def test_without_a_verification_file_next_to_the_cases_there_is_nothing_to_show(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(fontes.read_confirmation(Path(folder) / "casos.json", ["AAA-01"]))

    def test_reading_never_changes_the_file_or_adds_one(self):
        folder, path = a_folder_with(TABLE)
        self.addCleanup(folder.cleanup)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        fontes.read_confirmation(Path(folder.name) / "casos.json", ["AAA-01"])
        fontes.divergences(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
        self.assertEqual(sorted(p.name for p in Path(folder.name).iterdir()), ["VERIFICACAO.md"])


class TestTheRealFile(unittest.TestCase):
    """The counts the report shows, from the file in the repository."""

    @classmethod
    def setUpClass(cls):
        cls.table = fontes.read_table(VERIFICATION)

    def counts(self, bank: str) -> fontes.Counts:
        ids = [c.case_id for c in read_cases(ROOT / "casos" / bank)]
        return fontes.count(ids, self.table)

    def test_the_main_bank_has_nine_one_by_one_eleven_in_group_and_seven_to_confirm(self):
        c = self.counts("casos.json")
        self.assertEqual((c.total, c.one_by_one, c.in_group, c.pending), (27, 9, 11, 7))

    def test_the_consultation_bank_has_one_thirteen_and_seventeen(self):
        c = self.counts("consulta.json")
        self.assertEqual((c.total, c.one_by_one, c.in_group, c.pending), (31, 1, 13, 17))

    def test_the_project_has_ten_twenty_four_and_twenty_four(self):
        c = fontes.confirmation([], self.table).project
        self.assertEqual((c.total, c.one_by_one, c.in_group, c.pending), (58, 10, 24, 24))

    def test_no_case_of_either_bank_is_missing_from_the_table(self):
        for bank in ("casos.json", "consulta.json"):
            with self.subTest(banco=bank):
                self.assertEqual(self.counts(bank).without_row, ())

    def test_the_two_banks_add_up_to_the_project(self):
        a, b, project = self.counts("casos.json"), self.counts("consulta.json"), fontes.confirmation([], self.table).project
        self.assertEqual(a.total + b.total, project.total)
        self.assertEqual(a.one_by_one + b.one_by_one, project.one_by_one)
        self.assertEqual(a.in_group + b.in_group, project.in_group)
        self.assertEqual(a.pending + b.pending, project.pending)


class TestTheListOfTenIsHeldAgainstTheFile(unittest.TestCase):
    """The list counts the cases confirmed one by one, and the file only says it in prose. If the list,
    the table and the paragraph of 27/09 ever differ, this fails and asks the person who confirms the
    sources to look. Nothing is corrected here, and no box of VERIFICACAO.md is touched."""

    def test_the_list_agrees_with_the_table_and_with_the_paragraph_of_27_09(self):
        problems = fontes.divergences(VERIFICATION)
        self.assertEqual(
            problems, [],
            "A lista dos 10 casos confirmados um a um (ONE_BY_ONE, aferidor/fontes.py) diverge do "
            "casos/VERIFICACAO.md: " + "; ".join(problems) + ". A lista tem de ser revista pelo Fábio; "
            "nada foi corrigido, nem o código nem o ficheiro.",
        )

    def test_there_are_ten_and_all_different(self):
        self.assertEqual(len(fontes.ONE_BY_ONE), 10)
        self.assertEqual(len(set(fontes.ONE_BY_ONE)), 10)

    def test_a_box_that_is_not_marked_is_a_divergence(self):
        text = VERIFICATION.read_text(encoding="utf-8").replace(
            "| ATB-PAC-001 | DGS Norma 045/2011; duração: DGS Norma 006/2014 | 1 (ponto 4 a)); 20 | Amoxicilina 500 mg 8/8h, 3-7 dias (mudou a 27/09: era APMGF, 1000 mg) | não | [x] |",
            "| ATB-PAC-001 | DGS Norma 045/2011; duração: DGS Norma 006/2014 | 1 (ponto 4 a)); 20 | Amoxicilina 500 mg 8/8h, 3-7 dias (mudou a 27/09: era APMGF, 1000 mg) | não | [ ] |", 1,
        )
        self.assertNotEqual(text, VERIFICATION.read_text(encoding="utf-8"))
        folder, path = a_folder_with(text)
        self.addCleanup(folder.cleanup)
        self.assertIn("ATB-PAC-001 está na lista mas a caixa não está marcada", fontes.divergences(path))

    def test_an_id_the_paragraph_names_and_the_list_lacks_is_a_divergence(self):
        text = VERIFICATION.read_text(encoding="utf-8").replace("e PED-08 (banco de consulta)", "PED-08 e TAB-01 (banco de consulta)", 1)
        folder, path = a_folder_with(text)
        self.addCleanup(folder.cleanup)
        self.assertIn("TAB-01 está no parágrafo de 27/09 mas não na lista", fontes.divergences(path))

    def test_an_id_the_list_has_and_the_paragraph_lacks_is_a_divergence(self):
        text = VERIFICATION.read_text(encoding="utf-8").replace("FMT-CIST-017, ", "", 1)
        folder, path = a_folder_with(text)
        self.addCleanup(folder.cleanup)
        self.assertIn("FMT-CIST-017 está na lista mas não no parágrafo de 27/09", fontes.divergences(path))


class TestSourcesCited(unittest.TestCase):
    def test_the_main_bank_cites_five_sources_in_this_order(self):
        cases = read_cases(ROOT / "casos" / "casos.json")
        self.assertEqual(fontes.by_source(cases), [("DGS", 16), ("RCM", 8), ("APMGF", 5), ("Infarmed", 4), ("EMA", 3)])

    def test_the_consultation_bank_cites_ten_and_six_cases_cite_none_of_the_first_five(self):
        cases = read_cases(ROOT / "casos" / "consulta.json")
        pairs = fontes.by_source(cases)
        self.assertEqual(len(pairs), 10)
        shown = [body for body, _ in pairs[:fontes.SHOWN]]
        self.assertEqual(shown, ["DGS", "ESC", "Infarmed", "RCM", "NICE"])
        self.assertEqual(fontes.left_out(cases, shown), 6)

    def test_a_source_is_a_word_not_a_piece_of_one(self):
        from aferidor.models import Case, Criterion, Source
        from aferidor.risk import FailureType

        def case(name: str) -> Case:
            return Case("C", "dose", "q", "r", Source(name=name, reference="p"),
                        (Criterion(kind="contem", terms=("x",), failure=FailureType.DOSE_INCORRETA),))

        self.assertEqual(fontes.by_source([case("DGS Norma 1"), case("ESCADA do Infarmed")]), [("DGS", 1), ("Infarmed", 1)])


if __name__ == "__main__":
    unittest.main()
