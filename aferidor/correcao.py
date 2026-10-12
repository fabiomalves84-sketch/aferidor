"""Showing what the correction of the corrector did, without writing a number by hand.

Two things live here. `reclassify` regrades a registered trial with the current corrector, on the current case banks,
and gives the text of two new files to put beside the originals (the pattern of 27 September 2026: the originals are
never touched). The rest compares the published corrector, whose verdicts are kept in `docs/exemplo/antes-8edda161.json`,
with the current one, for the page: every figure is worked out from the stored answers and that file.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import __version__, build_id, grader_id, report
from .grading import grade_all, match_answers
from .storage import read_answers, read_cases, verdict_to_dict

BANK_FILES = {"principal": "casos/casos.json", "consulta": "casos/consulta.json"}


def _bank_of(answers, banks) -> str:
    first = answers[0].case_id
    return "principal" if any(c.case_id == first for c in banks["principal"]) else "consulta"


def reclassify(folder: Path, root: Path, today: date) -> tuple[str, str, str]:
    """(file name suffix, verdicts as JSON text, report as Markdown) for one registered trial.

    The verdicts are the current corrector's, in the shape of `vereditos.json` plus, on each entry, what the saved
    verdicts of the trial said (`passou_antes`, `falhas_antes`) and the identifier of the corrector that gives the new
    ones; the report is the usual one, with a note at the top that says what it is and what it compares.
    """
    folder, root = Path(folder), Path(root)
    banks = {name: read_cases(root / path) for name, path in BANK_FILES.items()}
    answers = read_answers(folder / "respostas.jsonl")
    bank = _bank_of(answers, banks)
    cases = banks[bank]
    verdicts, missing = grade_all(cases, answers)
    saved = json.loads((folder / "vereditos.json").read_text(encoding="utf-8"))
    pairs = match_answers(cases, answers, verdicts)
    if len(saved) != len(pairs):
        raise ValueError(f"{folder.name}: {len(saved)} veredictos guardados e {len(pairs)} respostas")
    entries = []
    for old, (_answer, verdict) in zip(saved, pairs):
        entry = verdict_to_dict(verdict)
        entry["corretor_novo"] = grader_id()
        entry["passou_antes"] = bool(old["passou"])
        entry["falhas_antes"] = list(old["falhas"])
        entries.append(entry)
    changed = sum(1 for e in entries if e["passou"] != e["passou_antes"] or e["falhas"] != e["falhas_antes"])
    builds = sorted({a.build for a in answers if a.build})
    note = (
        f"> **Reclassificação de {today.isoformat()}.** As respostas deste ensaio são as de `respostas.jsonl`, que não se alterou. "
        f"Os veredictos que se seguem são os do corretor atual (`{grader_id()}`, código `{build_id()}`), sobre o banco de casos "
        f"atual (`{BANK_FILES[bank]}`); os do ensaio, em `vereditos.json`, foram dados pelo corretor da altura "
        f"({'código ' + ', '.join(builds) if builds else 'versão não registada nas respostas'}). "
        f"Comparação: {changed} de {len(entries)} veredictos mudam de resultado ou de falhas. Os bancos e os critérios são os atuais, "
        f"não os do dia do ensaio. É triagem automática, sem validação clínica.\n"
    )
    if "26b" in folder.name:
        note += (
            "\n> Este ensaio teve um protocolo com o corretor congelado. Isto é uma **reclassificação posterior, fora do protocolo**: "
            "não se aplica o limiar do protocolo à taxa corrigida, e o resultado publicado tal como saiu fica em `relatorio.md`.\n"
        )
    text = report.build(cases, answers, verdicts, missing=missing, today=today)
    body = text.split("\n", 1)
    markdown = body[0] + "\n\n" + note + "\n" + (body[1] if len(body) > 1 else "")
    return today.isoformat(), json.dumps(entries, ensure_ascii=False, indent=2) + "\n", markdown
