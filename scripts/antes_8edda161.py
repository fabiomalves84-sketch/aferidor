"""Writes `docs/exemplo/antes-8edda161.json`: what the corrector of the published example (grader_id 0.1.0+corretor.8edda161bd4e,
commit e272ab9) said about every stored answer, so the page can put it beside what the current corrector says.

Run it with the package of that commit, in a read-only worktree, and with the stored answers of this repository:

    git worktree add --detach /tmp/aferidor-e272ab9 e272ab9
    python3 scripts/antes_8edda161.py /tmp/aferidor-e272ab9 docs/exemplo/antes-8edda161.json
    git worktree remove --force /tmp/aferidor-e272ab9

It uses nothing but what that commit already had (reading cases and answers, grading), grades every `respostas.jsonl` of
`ensaios/` against the case files of that commit, and records the SHA-256 of each answers file it read. Nothing is written
into `ensaios/`.
"""

from __future__ import annotations

import glob
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def main(worktree: str, output: str) -> int:
    repo = Path(__file__).resolve().parent.parent
    sys.path.insert(0, worktree)
    import aferidor
    from aferidor.grading import grade_all, match_answers
    from aferidor.risk import Risk
    from aferidor.storage import read_answers, read_cases

    banks = {"principal": read_cases(Path(worktree) / "casos" / "casos.json"),
             "consulta": read_cases(Path(worktree) / "casos" / "consulta.json")}
    ids = {name: {c.case_id for c in cases} for name, cases in banks.items()}
    commit = subprocess.run(["git", "-C", worktree, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    ensaios = {}
    for path in sorted(glob.glob(str(repo / "ensaios" / "*" / "respostas.jsonl"))):
        folder = Path(path).parent.name
        answers = read_answers(Path(path))
        bank = "principal" if answers[0].case_id in ids["principal"] else "consulta"
        verdicts, _ = grade_all(banks[bank], answers)
        rows = []
        for answer, verdict in match_answers(banks[bank], answers, verdicts):
            critical = any(failure.risk is Risk.CRITICO for failure in verdict.failures)
            flags = "".join("1" if result.passed else "0" for result in verdict.results)
            rows.append([answer.model, answer.case_id, answer.sample, int(verdict.passed), int(critical), flags, verdict.alternative])
        ensaios[folder] = {
            "banco": bank,
            "respostas_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "respostas": rows,
        }
    data = {
        "o_que_e": "veredictos do corretor publicado, por resposta guardada; cada linha é [modelo, caso, amostra, passou, falha crítica, critérios, alternativa]",
        "commit": commit,
        "grader_id": aferidor.grader_id(),
        "build_id": aferidor.build_id(),
        "ensaios": ensaios,
    }
    Path(output).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{output}: {sum(len(e['respostas']) for e in ensaios.values())} respostas de {len(ensaios)} ensaios, corretor {data['grader_id']}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("uso: antes_8edda161.py <worktree> <ficheiro de saída>")
    sys.exit(main(sys.argv[1], sys.argv[2]))
