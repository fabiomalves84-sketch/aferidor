"""The quality document cites tests; every test it cites must exist."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from aferidor.grading import negative_controls
from aferidor.storage import read_cases

ROOT = Path(__file__).resolve().parent.parent


class TestTraceability(unittest.TestCase):
    def test_every_test_named_in_the_quality_document_exists(self):
        cited = set(re.findall(r"`(test_[a-z0-9_]+)`", (ROOT / "docs" / "QUALIDADE.md").read_text(encoding="utf-8")))
        defined = {
            name
            for path in (ROOT / "tests").glob("test_*.py")
            for name in re.findall(r"def (test_[a-z0-9_]+)", path.read_text(encoding="utf-8"))
        }
        self.assertTrue(cited)
        self.assertEqual(sorted(cited - defined), [])

    def test_every_risk_points_to_requirements_that_exist(self):
        text = (ROOT / "docs" / "QUALIDADE.md").read_text(encoding="utf-8")
        requirements = set(re.findall(r"^\| (R\d\d) \|", text, flags=re.M))
        risks = [line for line in text.splitlines() if re.match(r"^\| P\d\d \|", line)]
        self.assertTrue(risks)
        for line in risks:
            with self.subTest(risk=line[:6]):
                self.assertTrue(set(re.findall(r"\bR\d\d\b", line)) <= requirements)


class TestNumbersWrittenInTheDocuments(unittest.TestCase):
    """CLAUDE.md: the test count written in the documents has to be the real one. The other numbers the
    documents repeat (cases, negative controls, requirements, risks) are held against what the code computes."""

    DOCUMENTS = ("README.md", "docs/APRESENTACAO.md", "CLAUDE.md")

    def read(self, name: str) -> str:
        return (ROOT / name).read_text(encoding="utf-8")

    def test_every_test_count_in_the_documents_is_the_real_one(self):
        real = unittest.TestLoader().discover(str(ROOT / "tests")).countTestCases()
        for name in self.DOCUMENTS:
            written = [int(n) for n in re.findall(r"\b(\d{3}) testes", self.read(name))]
            with self.subTest(documento=name):
                self.assertTrue(written, "o documento já não diz quantos testes tem")
                self.assertEqual(set(written), {real}, f"a bateria tem {real} testes; atualizar o número em {name}")

    def test_the_cases_and_negative_controls_written_are_the_ones_the_banks_have(self):
        main, consultation = (read_cases(ROOT / "casos" / f) for f in ("casos.json", "consulta.json"))
        controls = [sum(len(negative_controls(c)) for c in cases) for cases in (main, consultation)]
        for name in ("README.md", "CLAUDE.md", "docs/APRESENTACAO.md"):
            text = self.read(name)
            with self.subTest(documento=name):
                self.assertIn(f"{len(main)}/{len(main)}", text)
                self.assertIn(f"{controls[0]}/{controls[0]}", text)
        self.assertIn(f"{len(main) + len(consultation)} casos", self.read("README.md"))
        self.assertIn(f"{controls[1]}/{controls[1]}", self.read("README.md"))

    def test_the_requirements_and_risks_counted_in_the_presentation_are_the_ones_the_quality_document_has(self):
        quality = self.read("docs/QUALIDADE.md")
        requirements = len(re.findall(r"^\| R\d\d \|", quality, flags=re.M))
        risks = len(re.findall(r"^\| P\d\d \|", quality, flags=re.M))
        presentation = self.read("docs/APRESENTACAO.md")
        self.assertIn(f"{requirements} requisitos ligados", presentation)
        self.assertIn(f"{risks} riscos do instrumento", presentation)


if __name__ == "__main__":
    unittest.main()
