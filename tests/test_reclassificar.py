"""The reclassification of 12 October 2026: new files beside the registered trials, the originals untouched."""

from __future__ import annotations

import json
import re
import unittest
from datetime import date

from aferidor import correcao, manifesto
from tests.html_support import ROOT

STAMP = "2026-10-13"
TRIALS = sorted(p.parent for p in (ROOT / "ensaios").glob("*/respostas.jsonl"))


class TestTheNewFilesBesideTheOriginals(unittest.TestCase):
    def test_every_trial_has_the_two_files_and_its_manifest_still_holds(self):
        self.assertEqual(len(TRIALS), 10)
        for folder in TRIALS:
            with self.subTest(ensaio=folder.name):
                self.assertTrue((folder / f"vereditos-reclassificado-{STAMP}.json").exists())
                self.assertTrue((folder / f"relatorio-reclassificado-{STAMP}.md").exists())
                self.assertTrue(manifesto.check_manifest(folder).intact)

    def test_the_manifest_lists_the_new_files_and_the_originals_with_their_hashes(self):
        for folder in TRIALS:
            lines = (folder / manifesto.MANIFEST).read_text(encoding="utf-8").splitlines()
            names = {line.split("  ", 1)[1] for line in lines}
            for name in ("respostas.jsonl", "vereditos.json", "relatorio.md", f"vereditos-reclassificado-{STAMP}.json", f"relatorio-reclassificado-{STAMP}.md"):
                self.assertIn(name, names, f"{folder.name}: {name}")

    def test_each_verdict_says_the_corrector_that_gave_it_and_what_the_trial_said(self):
        for folder in TRIALS:
            entries = json.loads((folder / f"vereditos-reclassificado-{STAMP}.json").read_text(encoding="utf-8"))
            saved = json.loads((folder / "vereditos.json").read_text(encoding="utf-8"))
            self.assertEqual(len(entries), len(saved))
            for entry, old in zip(entries, saved):
                self.assertRegex(entry["corretor_novo"], r"^0\.1\.0\+corretor\.[0-9a-f]{12}$")
                self.assertEqual(entry["passou_antes"], old["passou"])
                self.assertEqual((entry["caso"], entry["modelo"]), (old["caso"], old["modelo"]))

    def test_the_report_says_what_it_is_and_the_26b_says_it_is_outside_the_protocol(self):
        for folder in TRIALS:
            text = (folder / f"relatorio-reclassificado-{STAMP}.md").read_text(encoding="utf-8")
            self.assertIn("Reclassificação de 2026-10-13", text)
            self.assertIn("sem validação clínica", text)
            self.assertEqual("reclassificação posterior, fora do protocolo" in text, "26b" in folder.name, folder.name)


class TestTheFunctionThatMakesThem(unittest.TestCase):
    def test_it_regrades_a_small_trial_without_touching_it(self):
        folder = ROOT / "ensaios" / "2026-09-14-agente"
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        stamp, verdicts, markdown = correcao.reclassify(folder, ROOT, date(2026, 10, 13))
        self.assertEqual(stamp, STAMP)
        self.assertEqual(len(json.loads(verdicts)), 18)
        self.assertTrue(re.match(r"# Relatório do Aferidor", markdown))
        self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})


if __name__ == "__main__":
    unittest.main()
