"""Writes, in each registered trial, `vereditos-reclassificado-<data>.json` and `relatorio-reclassificado-<data>.md`, beside
the originals, which are never touched, and lists the two new files in the trial's manifest (nothing else in it changes).

    python3 scripts/reclassificar.py 2026-10-12
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from aferidor import correcao, manifesto  # noqa: E402


def main(day: str) -> int:
    today = date.fromisoformat(day)
    for folder in sorted((REPO / "ensaios").iterdir()):
        if not (folder / "respostas.jsonl").exists():
            continue
        stamp, verdicts, markdown = correcao.reclassify(folder, REPO, today)
        (folder / f"vereditos-reclassificado-{stamp}.json").write_text(verdicts, encoding="utf-8")
        (folder / f"relatorio-reclassificado-{stamp}.md").write_text(markdown, encoding="utf-8")
        manifesto.write_manifest(folder)
        print(f"{folder.name}: 2 ficheiros novos")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "2026-10-12"))
