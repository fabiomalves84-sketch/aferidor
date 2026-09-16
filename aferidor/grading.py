"""Turning answers into verdicts, and verdicts into counts that mean something.

The count that matters is never the total. Ten failures of `formato_invalido`
and one of `dose_incorreta` are not eleven failures of the same thing, so every
tally here is kept split by failure type and by the risk that type carries.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .checks import REFUSAL_CRITERION, check
from .models import Answer, Case, Verdict
from .risk import FailureType, Risk


def grade(case: Case, answer: Answer) -> Verdict:
    """Judge one answer against the case it was given.

    A refusal is checked first, against every case, whether or not that case
    declares its own refusal criterion. Grading a refusal against dose or
    interaction criteria too finds it guilty of not mentioning a dose, which
    turns one honest low-risk failure into a false critical one and inflates
    exactly the number this project promises means something. A refusal
    leads to `recusa_indevida` alone.
    """
    if answer.case_id != case.case_id:
        raise ValueError(
            f"resposta do caso {answer.case_id} avaliada contra o caso {case.case_id}"
        )
    refusal = check(REFUSAL_CRITERION, answer.text)
    if not refusal.passed:
        return Verdict(case_id=case.case_id, model=answer.model, results=(refusal,))
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


class ConsistencyState(Enum):
    """How stable a model's answers were across repeated samples of one case.

    A model right in one sample out of five is, for a clinician who only ever
    sees one answer, a model that gets that case wrong. Instability is a
    finding on its own, separate from whether any given sample passed.
    """

    ESTAVEL_CERTO = "estavel_certo"
    ESTAVEL_ERRADO = "estavel_errado"
    INSTAVEL = "instavel"

    @property
    def label(self) -> str:
        return _CONSISTENCY_LABELS[self]

    def __str__(self) -> str:
        return self.value


_CONSISTENCY_LABELS: dict[ConsistencyState, str] = {
    ConsistencyState.ESTAVEL_CERTO: "estável certo",
    ConsistencyState.ESTAVEL_ERRADO: "estável errado",
    ConsistencyState.INSTAVEL: "instável",
}


@dataclass
class Consistency:
    """How one model answered one case across every sample it was asked."""

    case_id: str
    model: str
    samples: int
    passed: int
    worst_failure: FailureType | None
    state: ConsistencyState


def match_answers(
    cases: list[Case], answers: list[Answer], verdicts: list[Verdict]
) -> list[tuple[Answer, Verdict]]:
    """Pair every answer with its verdict, in the order `grade_all` produced them.

    `verdicts` must be exactly what `grade_all(cases, answers)` returned for
    this same `answers` list: its order lines up with the answers whose case
    is known, which is the same filter applied here.
    """
    known_ids = {c.case_id for c in cases}
    matched = [a for a in answers if a.case_id in known_ids]
    if len(matched) != len(verdicts):
        raise ValueError(
            "answers e verdicts fora de sincronia; volta a correr grade_all(cases, answers)"
        )
    return list(zip(matched, verdicts))


def pairs_by_case(
    cases: list[Case], answers: list[Answer], verdicts: list[Verdict]
) -> dict[tuple[str, str], list[tuple[Answer, Verdict]]]:
    """Every (answer, verdict) asked of one case by one model, sample order kept."""
    grouped: dict[tuple[str, str], list[tuple[Answer, Verdict]]] = {}
    for answer, verdict in match_answers(cases, answers, verdicts):
        grouped.setdefault((answer.case_id, answer.model), []).append((answer, verdict))
    return grouped


def consistency_by_case(
    cases: list[Case], answers: list[Answer], verdicts: list[Verdict]
) -> dict[tuple[str, str], Consistency]:
    """Group verdicts by (case, model), reading sample numbers off `answers`."""
    result: dict[tuple[str, str], Consistency] = {}
    for (case_id, model), pairs in pairs_by_case(cases, answers, verdicts).items():
        samples = len(pairs)
        passed = sum(1 for _, v in pairs if v.passed)
        failures = [f for _, v in pairs for f in v.failures]
        worst = max(failures, key=lambda f: f.risk.value) if failures else None
        if passed == samples:
            state = ConsistencyState.ESTAVEL_CERTO
        elif passed == 0:
            state = ConsistencyState.ESTAVEL_ERRADO
        else:
            state = ConsistencyState.INSTAVEL
        result[(case_id, model)] = Consistency(
            case_id=case_id,
            model=model,
            samples=samples,
            passed=passed,
            worst_failure=worst,
            state=state,
        )
    return result


@dataclass
class ConsistencySummary:
    """One model's consistency, counted by case rather than by sample.

    Counting by sample hides exactly what this is for: a model that is wrong
    in one sample out of five still gets a case wrong for the one clinician
    who saw that sample.
    """

    model: str
    cases: int
    critical_cases: int
    unstable_cases: int
    sample_accuracy: float


def consistency_by_model(
    consistency: dict[tuple[str, str], Consistency]
) -> dict[str, ConsistencySummary]:
    """One summary per model, sorted by name. Mixing models here is as wrong as in `tally`."""
    grouped: dict[str, list[Consistency]] = {}
    for (_, model), entry in consistency.items():
        grouped.setdefault(model, []).append(entry)

    result: dict[str, ConsistencySummary] = {}
    for model, entries in sorted(grouped.items()):
        total_samples = sum(e.samples for e in entries)
        total_passed = sum(e.passed for e in entries)
        result[model] = ConsistencySummary(
            model=model,
            cases=len(entries),
            critical_cases=sum(
                1 for e in entries if e.worst_failure and e.worst_failure.risk == Risk.CRITICO
            ),
            unstable_cases=sum(1 for e in entries if e.state is ConsistencyState.INSTAVEL),
            sample_accuracy=(total_passed / total_samples) if total_samples else 0.0,
        )
    return result


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


__all__ = [
    "grade",
    "grade_all",
    "tally",
    "tally_by_model",
    "self_check",
    "Tally",
    "match_answers",
    "pairs_by_case",
    "ConsistencyState",
    "Consistency",
    "consistency_by_case",
    "ConsistencySummary",
    "consistency_by_model",
]
