"""Running a set of cases against one provider and keeping every answer.

Three things matter here and nothing else does:

1. The prompt carries the question and never the reference answer.
2. Every answer is written the moment it arrives, so an interrupted run is
   resumed rather than repeated. Re-asking a model costs money and gives a
   different reply, which quietly changes what the bench measured.
3. A case that fails after every attempt is recorded as an error, not dropped.
   A run that silently answers nine of ten cases reports a score for a set that
   was never asked.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from .models import Answer, Case
from .providers import Provider, ProviderError
from .storage import append_answer, read_answers

INSTRUCTION = (
    "Responde em portugues europeu a esta pergunta clinica, dirigida a um medico.\n"
    "Se a resposta envolver farmaco, indica dose, intervalo e duracao.\n"
    "Assinala interacoes, contraindicacoes e ajustes relevantes.\n"
    "Nao inventes referencias. Se nao souberes, di-lo.\n\n"
    "Pergunta: {question}"
)


def build_prompt(case: Case) -> str:
    """The exact text sent to the model.

    Built from the question alone. The reference answer, the criteria and the
    source stay on this side of the wall.
    """
    return INSTRUCTION.format(question=case.question)


@dataclass(frozen=True)
class RunConfig:
    """How hard to try before giving up on a case."""

    attempts: int = 3
    backoff_s: float = 2.0
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("a run needs at least one attempt per case")


@dataclass
class RunResult:
    """What one run produced: answers kept, cases skipped, cases lost."""

    run_id: str
    model: str
    answers: list[Answer] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        parts = [f"execucao {self.run_id}", f"modelo {self.model}", f"{len(self.answers)} respostas"]
        if self.skipped:
            parts.append(f"{len(self.skipped)} ja existentes")
        if self.errors:
            parts.append(f"{len(self.errors)} por responder")
        return ", ".join(parts)


def _answered_already(path: Path | None, model: str) -> set[str]:
    if path is None or not Path(path).exists():
        return set()
    return {a.case_id for a in read_answers(Path(path)) if a.model == model}


def _ask_with_retry(
    provider: Provider, prompt: str, config: RunConfig
) -> tuple[str, int]:
    last: ProviderError | None = None
    for attempt in range(1, config.attempts + 1):
        started = time.monotonic()
        try:
            text = provider.ask(prompt)
        except ProviderError as error:
            last = error
            if not error.retryable or attempt == config.attempts:
                break
            config.sleep(config.backoff_s * attempt)
            continue
        return text, int((time.monotonic() - started) * 1000)
    raise last if last else ProviderError("falhou sem erro registado")


def run(
    cases: list[Case],
    provider: Provider,
    *,
    path: Path | None = None,
    run_id: str | None = None,
    config: RunConfig | None = None,
    progress: Callable[[Case, Answer | None, str], None] | None = None,
) -> RunResult:
    """Ask every case and keep what came back.

    `path` is a JSONL file appended to as answers arrive; when it already holds
    answers from this same model, those cases are skipped.
    """
    config = config or RunConfig()
    result = RunResult(run_id=run_id or uuid.uuid4().hex[:12], model=provider.name)
    done = _answered_already(path, provider.name)

    for case in cases:
        if case.case_id in done:
            result.skipped.append(case.case_id)
            if progress:
                progress(case, None, "ja respondido")
            continue

        try:
            text, latency_ms = _ask_with_retry(provider, build_prompt(case), config)
        except ProviderError as error:
            result.errors[case.case_id] = str(error)
            if progress:
                progress(case, None, f"erro: {error}")
            continue

        answer = Answer(
            case_id=case.case_id,
            model=provider.name,
            text=text,
            asked_at=datetime.now(),
            latency_ms=latency_ms,
            run_id=result.run_id,
        )
        if path is not None:
            append_answer(answer, Path(path))
        result.answers.append(answer)
        if progress:
            progress(case, answer, "ok")

    return result


__all__ = ["run", "build_prompt", "RunConfig", "RunResult", "INSTRUCTION"]
