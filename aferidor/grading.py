"""Turning answers into verdicts, and verdicts into counts that mean something.

The count that matters is never the total. Ten failures of `formato_invalido`
and one of `dose_incorreta` are not eleven failures of the same thing, so every
tally here is kept split by failure type and by the risk that type carries.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from .checks import check
from .models import Answer, Case, Verdict
from .risk import FailureType, Risk


def grade(case: Case, answer: Answer) -> Verdict:
    """Judge one answer against the case it was given."""
    if answer.case_id != case.case_id:
        raise ValueError(
            f"resposta do caso {answer.case_id} avaliada contra o caso {case.case_id}"
        )
    return Verdict(
        case_id=case.case_id,
        model=answer.model,
        results=tuple(check(criterion, answer.text) for criterion in case.criteria),
    )


def grade_all(cases: list[Case], answers: list[Answer]) -> tuple[list[Verdict], list[str]]:
    """Judge every answer, and report which cases were never answered.

    The unanswered list is returned rather than ignored: a score computed over
    the cases that happened to come back is a score for a set nobody chose.
    """
    by_id = {c.case_id: c for c in cases}
    verdicts: list[Verdict] = []
    unknown: list[str] = []

    for answer in answers:
        case = by_id.get(answer.case_id)
        if case is None:
            unknown.append(answer.case_id)
            continue
        verdicts.append(grade(case, answer))

    answered = {a.case_id for a in answers}
    missing = [c.case_id for c in cases if c.case_id not in answered]
    return verdicts, missing + unknown


@dataclass
class Tally:
    """What one model scored, split the only way that is useful."""

    model: str
    total: int = 0
    passed: int = 0
    by_failure: Counter = field(default_factory=Counter)
    by_risk: Counter = field(default_factory=Counter)
    failed_cases: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def critical(self) -> int:
        """Answers carrying at least one critical failure. The number to read first."""
        return self.by_risk[Risk.CRITICO]

    def worst_first(self) -> list[tuple[FailureType, int]]:
        return sorted(self.by_failure.items(), key=lambda kv: (-kv[0].risk.value, -kv[1]))


def tally(verdicts: list[Verdict]) -> Tally:
    """Count one model's verdicts. Mixing models in one tally is refused."""
    if not verdicts:
        return Tally(model="")
    models = {v.model for v in verdicts}
    if len(models) > 1:
        raise ValueError(
            "vereditos de modelos diferentes na mesma contagem: " + ", ".join(sorted(models))
        )

    counts = Tally(model=verdicts[0].model, total=len(verdicts))
    for verdict in verdicts:
        if verdict.passed:
            counts.passed += 1
            continue
        failures = verdict.failures
        counts.failed_cases[verdict.case_id] = tuple(f.value for f in failures)
        for failure in failures:
            counts.by_failure[failure] += 1
        if verdict.worst_risk:
            counts.by_risk[verdict.worst_risk] += 1
    return counts


def tally_by_model(verdicts: list[Verdict]) -> dict[str, Tally]:
    """One tally per model, for comparing two models over the same cases."""
    grouped: dict[str, list[Verdict]] = {}
    for verdict in verdicts:
        grouped.setdefault(verdict.model, []).append(verdict)
    return {model: tally(group) for model, group in sorted(grouped.items())}


def self_check(cases: list[Case]) -> list[tuple[Case, Verdict]]:
    """Grade every case's own reference answer against its own criteria.

    A case whose reference answer fails its own criteria is broken, and it is
    broken in the direction that matters: it marks a correct model wrong. This
    costs nothing to run and catches the mistake before any model is paid for.
    """
    broken: list[tuple[Case, Verdict]] = []
    for case in cases:
        verdict = grade(
            case,
            Answer(
                case_id=case.case_id,
                model="referencia",
                text=case.reference,
                asked_at=datetime.now(),
            ),
        )
        if not verdict.passed:
            broken.append((case, verdict))
    return broken


__all__ = ["grade", "grade_all", "tally", "tally_by_model", "self_check", "Tally"]
