"""The domain: a case, its source, an answer, and the verdict on that answer.

A case is a clinical question whose correct answer is known and citable. The
acceptance criteria are written before any model is run: deciding after the
fact what counts as correct is how a validation exercise fools itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .risk import FailureType, Risk


@dataclass(frozen=True)
class Source:
    """Where the reference answer comes from. No source, no case."""

    name: str
    reference: str
    url: str = ""
    consulted: date | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a source needs a name")
        if not self.reference.strip():
            raise ValueError(f"source {self.name!r} needs a reference (document, page or section)")


@dataclass(frozen=True)
class Criterion:
    """One checkable condition on an answer.

    `kind` selects the check, `terms` feeds it, and `failure` says how to
    classify the answer when the check does not pass.
    """

    kind: str
    terms: tuple[str, ...]
    failure: FailureType
    description: str = ""

    KINDS = ("contem", "nao_contem", "contem_todos", "valor_numerico", "nao_prescreve")

    def __post_init__(self) -> None:
        if self.kind not in self.KINDS:
            raise ValueError(f"unknown criterion kind {self.kind!r}; expected one of {self.KINDS}")
        if not self.terms:
            raise ValueError(f"criterion {self.kind!r} needs at least one term")


@dataclass(frozen=True)
class Case:
    """A clinical question with a known, sourced answer and explicit criteria."""

    case_id: str
    category: str
    question: str
    reference: str
    source: Source
    criteria: tuple[Criterion, ...]
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("a case needs an id")
        if not self.question.strip():
            raise ValueError(f"case {self.case_id} needs a question")
        if not self.reference.strip():
            raise ValueError(f"case {self.case_id} needs a reference answer")
        if not self.criteria:
            raise ValueError(
                f"case {self.case_id} has no acceptance criteria; "
                "a case nobody can fail measures nothing"
            )

    @property
    def worst_risk(self) -> Risk:
        """The heaviest failure this case can produce."""
        return max((c.failure.risk for c in self.criteria), key=lambda r: r.value)


@dataclass(frozen=True)
class Answer:
    """What a model replied to one case, kept exactly as it came.

    `sample` numbers repeated asks of the same case to the same model, so a
    consistency run can tell them apart. `temperature` is the value the
    provider was configured with when this answer was asked.
    """

    case_id: str
    model: str
    text: str
    asked_at: datetime
    latency_ms: int = 0
    run_id: str = ""
    sample: int = 1
    temperature: float = 0.0

    def __post_init__(self) -> None:
        if self.latency_ms < 0:
            raise ValueError("latency cannot be negative")
        if self.sample < 1:
            raise ValueError("sample numbers start at 1")


@dataclass(frozen=True)
class CriterionResult:
    """Whether one criterion held, and what was seen."""

    criterion: Criterion
    passed: bool
    evidence: str = ""


@dataclass(frozen=True)
class Verdict:
    """The judgement on one answer: every criterion, and the failures found."""

    case_id: str
    model: str
    results: tuple[CriterionResult, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> tuple[FailureType, ...]:
        """Failure types raised, worst risk first, without repeats."""
        seen: dict[FailureType, None] = {}
        for result in self.results:
            if not result.passed:
                seen[result.criterion.failure] = None
        return tuple(sorted(seen, key=lambda f: -f.risk.value))

    @property
    def worst_risk(self) -> Risk | None:
        """Heaviest risk actually incurred, or None when the answer passed."""
        failures = self.failures
        return failures[0].risk if failures else None
