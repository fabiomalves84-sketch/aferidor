"""One simulated run, the same before and after the paid-calls wiring, written down in a golden file.

`scenario()` exercises everything the runner does for a model that is not paid (retries, an unfinished reply, a
resume, repetitions) plus the `executar` command with the fake provider, and returns what came out with only the
fields that vary by nature (time, latency, the build hash, temporary paths) replaced. The golden file was made by
running it on the code as it was before the wiring."""

from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
from pathlib import Path

from aferidor import cli, grader_id
from aferidor.providers import FakeProvider
from aferidor.runner import RunConfig, run
from tests.helpers import a_case

GOLDEN = Path(__file__).with_name("golden_runner_sem_flags.json")
ROOT = Path(__file__).resolve().parent.parent


def _lines(path: Path) -> list[dict]:
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        data = json.loads(line)
        data["perguntada_em"] = "T"
        data["latencia_ms"] = 0
        data["versao"] = "B"
        if data.get("corretor") == grader_id():
            data["corretor"] = "G"  # the grader id, which changes whenever the grader does; it must be the live one
        data["execucao"] = "<id>"
        found.append(data)
    return found


def _result(result) -> dict:
    return {
        "run_id": result.run_id, "model": result.model, "skipped": result.skipped, "errors": result.errors,
        "notes": result.notes, "complete": result.complete,
        "answers": [(a.case_id, a.sample, a.text, a.temperature, a.max_tokens, a.finish_reason) for a in result.answers],
    }


def scenario() -> dict:
    out: dict = {}
    cases = [a_case("C1"), a_case("C2"), a_case("C3")]
    quiet = RunConfig(attempts=3, backoff_s=0.0, sleep=lambda s: None)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "respostas.jsonl"
        provider = FakeProvider(name="falso:g", replies={"Que dose": "Amoxicilina 1000 mg de 8 em 8 horas"},
                                failures=2, temperature=1.0)
        provider.max_tokens = 8192
        out["primeira"] = _result(run(cases, provider, path=path, run_id="g1", config=quiet, repetitions=2))
        out["ficheiro"] = _lines(path)
        provider2 = FakeProvider(name="falso:g", replies={"Que dose": "outra"}, temperature=1.0)
        provider2.max_tokens = 8192
        out["retoma"] = _result(run(cases, provider2, path=path, run_id="g2", config=quiet, repetitions=3))
        out["ficheiro_retoma"] = _lines(path)
        out["prompts"] = provider.prompts[:2]
        out["so_o_ficheiro_de_respostas"] = sorted(p.name for p in Path(folder).iterdir())

        truncated = FakeProvider(name="falso:t", finish_reason="length", temperature=1.0)
        out["truncada"] = _result(run(cases[:1], truncated, path=Path(folder) / "t.jsonl", run_id="g3", config=quiet))
        flaky = FakeProvider(name="falso:f", failures=9, temperature=1.0)
        out["sempre_a_falhar"] = _result(run(cases[:1], flaky, path=None, run_id="g4", config=quiet))

        saida = Path(folder) / "cli.jsonl"
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(["executar", "--fornecedor", "falso", "--casos", str(ROOT / "casos" / "casos.json"),
                             "--limite", "3", "--repeticoes", "2", "--saida", str(saida), "--temperatura", "1.0"])
        out["cli"] = {
            "codigo": code,
            "stdout": re.sub(r"execução [0-9a-f]{12}", "execução <id>", stdout.getvalue().replace(str(saida), "<saida>").replace(folder, "<pasta>")),
            "stderr": stderr.getvalue().replace(folder, "<pasta>"),
            "ficheiro": _lines(saida),
            "pasta": sorted(p.name for p in Path(folder).iterdir()),
        }
    return out


if __name__ == "__main__":
    GOLDEN.write_text(json.dumps(scenario(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
