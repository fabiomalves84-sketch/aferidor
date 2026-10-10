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

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import build_id
from .models import Answer, Case
from .providers import Provider, ProviderError, Reply
from .storage import append_answer, discard_truncated_tail, read_answers

# The instruction is written in correct European Portuguese, accents
# included. Until 27/09/2026 it went out without a single accent ("Responde
# em portugues europeu a esta pergunta clinica"), which asked for European
# Portuguese in a way no European Portuguese text is written. Changing it
# changed the measurement; answers keep the hash of the exact text sent
# (`prompt_digest`), so answers to the old and new wording never mix, and a
# run cannot resume across the change.
INSTRUCTION = (
    "Responde em português europeu a esta pergunta clínica, dirigida a um médico.\n"
    "Se a resposta envolver um fármaco, indica a dose, o intervalo e a duração.\n"
    "Assinala as interações, as contraindicações e os ajustes relevantes.\n"
    "Não inventes referências. Se não souberes, di-lo.\n\n"
    "Pergunta: {question}"
)


def build_prompt(case: Case) -> str:
    """The exact text sent to the model.

    Built from the question alone. The reference answer, the criteria and the
    source stay on this side of the wall.
    """
    return INSTRUCTION.format(question=case.question)


def prompt_digest(prompt: str) -> str:
    """SHA-256 of the exact text sent, written on the answer it produced."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RunConfig:
    """How hard to try before giving up on a case."""

    attempts: int = 3
    backoff_s: float = 2.0
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("uma execução precisa de pelo menos uma tentativa por caso")


@dataclass
class RunResult:
    """What one run produced: answers kept, cases skipped, cases lost."""

    run_id: str
    model: str
    answers: list[Answer] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        parts = [f"execução {self.run_id}", f"modelo {self.model}", f"{len(self.answers)} respostas"]
        if self.skipped:
            parts.append(f"{len(self.skipped)} já existentes")
        if self.errors:
            parts.append(f"{len(self.errors)} por responder")
        return ", ".join(parts)


class ConditionsMismatch(ValueError):
    """A resumed run would add answers obtained under different conditions.

    Resuming is only safe while it is the same measurement. An answer asked
    at another temperature, with another token limit, or with another prompt
    for the same case is a different measurement, and mixing the two in one
    file leaves a result that describes neither.
    """


def _check_same_conditions(
    path: Path | None,
    provider: Provider,
    cases: list[Case],
    temperature: float,
    max_tokens: int | None,
) -> None:
    """Refuse to resume onto answers of this model obtained differently.

    A field an older answer never recorded is not compared, with one
    exception: the hash of the text sent. It was recorded from the same day
    the instruction changed, so an answer without it is known to have been
    given to the old instruction, and resuming onto it would mix the two.
    """
    if path is None or not Path(path).exists():
        return
    prompts = {case.case_id: prompt_digest(build_prompt(case)) for case in cases}
    differences: list[str] = []
    for answer in read_answers(Path(path)):
        if answer.model != provider.name:
            continue
        where = f"{answer.case_id} amostra {answer.sample}"
        if answer.temperature != temperature:
            differences.append(f"{where}: temperatura {answer.temperature:g}, agora {temperature:g}")
        if answer.max_tokens is not None and answer.max_tokens != max_tokens:
            differences.append(f"{where}: tokens_max {answer.max_tokens}, agora {max_tokens}")
        wanted = prompts.get(answer.case_id)
        if not answer.prompt_sha256:
            differences.append(f"{where}: sem registo do texto enviado (instrução anterior a 27/09)")
        elif wanted and answer.prompt_sha256 != wanted:
            differences.append(f"{where}: o texto enviado ao modelo mudou")
    if differences:
        shown = "; ".join(differences[:5])
        more = f" (e mais {len(differences) - 5})" if len(differences) > 5 else ""
        raise ConditionsMismatch(
            f"{path} tem respostas de {provider.name} obtidas noutras condições: "
            f"{shown}{more}"
        )


def _answered_already(path: Path | None, model: str) -> set[tuple[str, int]]:
    """Which (case, sample) pairs this model already has an answer for.

    The key includes the sample number, not just the case, so a run
    interrupted partway through its repetitions resumes at the missing
    sample instead of skipping the whole case or repeating what is done.
    """
    if path is None or not Path(path).exists():
        return set()
    return {(a.case_id, a.sample) for a in read_answers(Path(path)) if a.model == model}


def _check_reply(reply: Reply) -> None:
    """Refuse a reply that the model never actually finished giving.

    A reply cut off by `max_tokens` (`finish_reason` "length") or that came
    back with no text at all is not a wrong answer, it is a question the
    model never got to answer. Grading it would count a dose the model never
    stated as a dose it got wrong. This is deliberately not retryable: the
    same `max_tokens` would just cut it off again, and retrying with a
    different budget mid-run would leave two different measurements in the
    same file.
    """
    if reply.finish_reason == "filtered":
        raise ProviderError("resposta cortada pelo filtro do fornecedor", retryable=False)
    if reply.finish_reason == "length":
        raise ProviderError("resposta truncada no limite de tokens", retryable=False)
    if not reply.text.strip():
        raise ProviderError("resposta sem texto", retryable=False)


def _ask_with_retry(
    provider: Provider, prompt: str, config: RunConfig
) -> tuple[Reply, int]:
    last: ProviderError | None = None
    for attempt in range(1, config.attempts + 1):
        started = time.monotonic()
        try:
            reply = provider.ask(prompt)
            _check_reply(reply)
        except ProviderError as error:
            last = error
            if not error.retryable or attempt == config.attempts:
                break
            config.sleep(config.backoff_s * attempt)
            continue
        return reply, int((time.monotonic() - started) * 1000)
    raise last if last else ProviderError("falhou sem erro registado")


def run(
    cases: list[Case],
    provider: Provider,
    *,
    path: Path | None = None,
    run_id: str | None = None,
    config: RunConfig | None = None,
    repetitions: int = 1,
    progress: Callable[[Case, Answer | None, str], None] | None = None,
) -> RunResult:
    """Ask every case and keep what came back.

    `path` is a JSONL file appended to as answers arrive; when it already holds
    answers from this same model, those (case, sample) pairs are skipped.

    `repetitions` asks each case that many times, numbered from 1, so a
    consistency check can see whether the model answers the same way twice.

    Resuming onto answers of this model obtained under other conditions
    raises `ConditionsMismatch` before anything is asked.
    """
    config = config or RunConfig()
    temperature = provider.temperature
    max_tokens = provider.max_tokens
    result = RunResult(run_id=run_id or uuid.uuid4().hex[:12], model=provider.name)
    if path is not None and path.exists():
        repaired = discard_truncated_tail(path)
        if repaired:
            result.notes.append(repaired)
    _check_same_conditions(path, provider, cases, temperature, max_tokens)
    done = _answered_already(path, provider.name)
    build = build_id()

    for case in cases:
        prompt = build_prompt(case)  # the same for every sample of the case
        for sample in range(1, repetitions + 1):
            if (case.case_id, sample) in done:
                result.skipped.append(case.case_id)
                if progress:
                    progress(case, None, "já respondido")
                continue

            try:
                reply, latency_ms = _ask_with_retry(provider, prompt, config)
            except ProviderError as error:
                message = f"amostra {sample}: {error}"
                previous = result.errors.get(case.case_id)
                result.errors[case.case_id] = f"{previous}; {message}" if previous else message
                if progress:
                    progress(case, None, f"erro: {error}")
                continue

            answer = Answer(
                case_id=case.case_id,
                model=provider.name,
                text=reply.text,
                asked_at=datetime.now(),
                latency_ms=latency_ms,
                run_id=result.run_id,
                sample=sample,
                temperature=temperature,
                finish_reason=reply.finish_reason,
                prompt_sha256=prompt_digest(prompt),
                max_tokens=max_tokens,
                build=build,
            )
            if path is not None:
                append_answer(answer, path)
            result.answers.append(answer)
            if progress:
                progress(case, answer, "ok")

    return result


__all__ = [
    "run",
    "build_prompt",
    "prompt_digest",
    "ConditionsMismatch",
    "RunConfig",
    "RunResult",
    "INSTRUCTION",
]
