"""The figures the README gives "à data" are the ones the trial itself published."""

from __future__ import annotations

import re
import unittest

from tests.html_support import ROOT

# Row of the README table (by the model it starts with) and column (1 main bank, 2 consultation bank)
# -> the trial whose own report published the figure that day, and the number of cases it had.
TRIAL_OF = {
    ("Gemma 4 31B", 1): ("2026-09-29-gemma4-31b-casos", 27),
    ("Gemini 3.5 Flash Lite", 2): ("2026-09-29-gemini-consulta", 30),
    ("Gemma 3 12B", 1): ("2026-09-27-locais-12-14b", 27),
}

DATED = re.compile(r"(\d+) \((\d+)% a (\d+)%\); à data: (\d+) \((\d+)% a (\d+)%\)")


class TestTheDatedFiguresOfTheReadme(unittest.TestCase):
    def test_every_dated_figure_in_the_readme_is_in_the_report_of_its_trial(self):
        """Only reads files. The "à data" number and its interval must be written in the `relatorio.md`
        of the trial folder, as that report published them; nothing is recomputed here, so a figure
        cannot be corrected by recalculating it. The current figure of the same cell has to differ,
        or there would be nothing to say "à data" about."""
        rows = [
            line for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
            if line.startswith("| ") and "à data:" in line
        ]
        self.assertEqual(len(rows), 3, "a tabela do README tem três valores «à data»; se mudou, atualizar TRIAL_OF")
        seen = set()
        for row in rows:
            cells = [c.strip() for c in row.strip("|").split("|")]
            column = next(i for i, c in enumerate(cells) if "à data:" in c)
            model = next(m for (m, col) in TRIAL_OF if cells[0].startswith(m) and col == column)
            trial, cases = TRIAL_OF[(model, column)]
            seen.add((model, column))
            with self.subTest(modelo=model):
                found = DATED.search(cells[column])
                self.assertIsNotNone(found, cells[column])
                g = [int(x) for x in found.groups()]
                now, then, low, high = g[0], g[3], g[4], g[5]
                self.assertNotEqual(now, then)
                report = (ROOT / "ensaios" / trial / "relatorio.md").read_text(encoding="utf-8")
                published = f"**{then} de {cases} casos com falha de risco crítico em pelo menos uma amostra** (IC 95% {low}% a {high}%)"
                self.assertIn(published, report)
        self.assertEqual(seen, set(TRIAL_OF))


if __name__ == "__main__":
    unittest.main()
