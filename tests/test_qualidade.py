"""The quality document cites tests; every test it cites must exist."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
