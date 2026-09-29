"""The manifest of a registered trial: written once, checked by anyone."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from aferidor.cli import main
from aferidor.manifesto import MANIFEST, check_manifest, write_manifest


def a_trial(folder: str) -> Path:
    root = Path(folder)
    (root / "respostas.jsonl").write_text('{"caso": "A"}\n', encoding="utf-8")
    (root / "README.md").write_text("# Ensaio\n", encoding="utf-8")
    (root / ".passagem.log").write_text("temporário", encoding="utf-8")
    return root


class TestManifest(unittest.TestCase):
    def test_it_lists_every_file_in_the_sha256sum_format(self):
        with tempfile.TemporaryDirectory() as folder:
            root = a_trial(folder)
            lines = write_manifest(root).read_text(encoding="utf-8").splitlines()
        self.assertEqual([l.split("  ")[1] for l in lines], ["README.md", "respostas.jsonl"])
        self.assertTrue(all(len(l.split("  ")[0]) == 64 for l in lines))

    def test_an_untouched_folder_is_intact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = a_trial(folder)
            write_manifest(root)
            self.assertTrue(check_manifest(root).intact)

    def test_a_changed_a_missing_and_an_added_file_are_each_named(self):
        with tempfile.TemporaryDirectory() as folder:
            root = a_trial(folder)
            write_manifest(root)
            (root / "respostas.jsonl").write_text('{"caso": "B"}\n', encoding="utf-8")
            (root / "README.md").unlink()
            (root / "novo.json").write_text("{}", encoding="utf-8")
            result = check_manifest(root)
        self.assertEqual(result.changed, ("respostas.jsonl",))
        self.assertEqual(result.missing, ("README.md",))
        self.assertEqual(result.unlisted, ("novo.json",))

    def test_the_command_fails_when_the_folder_differs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = a_trial(folder)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main(["manifesto", str(root)]), 0)
                self.assertEqual(main(["manifesto", str(root), "--verificar"]), 0)
                (root / "README.md").write_text("alterado", encoding="utf-8")
                self.assertEqual(main(["manifesto", str(root), "--verificar"]), 1)
            self.assertIn("alterado: README.md", err.getvalue())


class TestRegisteredTrials(unittest.TestCase):
    """Every registered trial carries a manifest, and matches it."""

    def test_every_trial_folder_is_intact(self):
        # A trial is registered once it has its README; one still running has not.
        trials = sorted(
            p for p in (Path(__file__).resolve().parent.parent / "ensaios").iterdir()
            if p.is_dir() and (p / "README.md").exists()
        )
        for trial in trials:
            with self.subTest(trial=trial.name):
                self.assertTrue((trial / MANIFEST).exists(), f"{trial.name} sem manifesto")
                result = check_manifest(trial)
                self.assertTrue(result.intact, result)


if __name__ == "__main__":
    unittest.main()
