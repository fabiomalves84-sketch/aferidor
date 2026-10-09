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
            raise ValueError("uma fonte precisa de nome")
        if not self.reference.strip():
            raise ValueError(f"a fonte {self.name!r} precisa de uma referência (documento, página ou secção)")


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
            raise ValueError(f"tipo de critério desconhecido {self.kind!r}; esperava um de {self.KINDS}")
        if not self.terms:
            raise ValueError(f"criterion {self.kind!r} needs at least one term")
        if self.kind == "valor_numerico":
            self._check_numeric_terms()

    def _check_numeric_terms(self) -> None:
        """A `valor_numerico` is (value, unit) or (value, unit, tolerance).

        Refused when the case is loaded, with the terms in the message, and not
        deep inside the grader on the first answer, where a malformed one
        was a bare ValueError (and an IndexError in the negative controls).
        """
        terms = self.terms
        if not 2 <= len(terms) <= 3:
            raise ValueError(
                f"valor_numerico precisa de valor, unidade e, se quiser, tolerância; recebeu {terms!r}"
            )
        for position, label in ((0, "valor"), (2, "tolerância")):
            if position < len(terms):
                try:
                    float(terms[position].replace(",", "."))
                except ValueError:
                    raise ValueError(
                        f"valor_numerico: o {label} {terms[position]!r} não é um número (termos {terms!r})"
                    ) from None


@dataclass(frozen=True)
class Alternative:
    """One of several regimens the source accepts as correct for the same case.

    When a source gives two first-line options (amoxicillin for ten days, or a
    single dose of benzathine penicillin), each is written as its own set of
    criteria with its own reference answer. Folding them into one criterion
    ("amoxicilina" or "benzatinica") would let an answer pass with the wrong
    amoxicillin dose just by naming the other drug in passing.
    """

    description: str
    reference: str
    criteria: tuple[Criterion, ...]

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("uma alternativa precisa de descrição")
        if not self.reference.strip():
            raise ValueError(f"alternative {self.description!r} needs a reference answer")
        if not self.criteria:
            raise ValueError(f"alternative {self.description!r} has no criteria")


@dataclass(frozen=True)
class Case:
    """A clinical question with a known, sourced answer and explicit criteria.

    `criteria` always apply. `alternatives`, when there are any, are the
    regimens the source accepts: an answer must also meet every criterion of
    at least one of them.
    """

    case_id: str
    category: str
    question: str
    reference: str
    source: Source
    criteria: tuple[Criterion, ...]
    notes: str = ""
    alternatives: tuple[Alternative, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("um caso precisa de identificador")
        if not self.question.strip():
            raise ValueError(f"case {self.case_id} needs a question")
        if not self.reference.strip():
            raise ValueError(f"case {self.case_id} needs a reference answer")
        if not self.criteria and not self.alternatives:
            raise ValueError(
                f"case {self.case_id} has no acceptance criteria; "
                "a case nobody can fail measures nothing"
            )
        if len(self.alternatives) == 1:
            raise ValueError(
                f"case {self.case_id} has a single alternative; "
                "its criteria belong with the case's own"
            )

    @property
    def all_criteria(self) -> tuple[Criterion, ...]:
        """Every criterion in the case, its own and every alternative's."""
        return self.criteria + tuple(c for a in self.alternatives for c in a.criteria)

    @property
    def worst_risk(self) -> Risk:
        """The heaviest failure this case can produce."""
        return max((c.failure.risk for c in self.all_criteria), key=lambda r: r.value)


@dataclass(frozen=True)
class Answer:
    """What a model replied to one case, kept exactly as it came.

    `sample` numbers repeated asks of the same case to the same model, so a
    consistency run can tell them apart. `temperature` is the value the
    provider was configured with when this answer was asked. `finish_reason`
    is "stop" unless the provider says otherwise; a truncated or empty reply
    never reaches here at all (the runner treats it as an execution error,
    not an answer), so in practice this is almost always "stop".

    The last three fields say under what conditions the answer was obtained,
    so two answers in one file can be shown to belong to the same
    measurement: `prompt_sha256` is the hash of the exact text sent (the
    instruction and the question), `max_tokens` the limit the provider was
    given, and `build` the Aferidor version and code hash (`build_id`). They
    are empty on answers written before they existed.
    """

    case_id: str
    model: str
    text: str
    asked_at: datetime
    latency_ms: int = 0
    run_id: str = ""
    sample: int = 1
    temperature: float = 0.0
    finish_reason: str = "stop"
    prompt_sha256: str = ""
    max_tokens: int | None = None
    build: str = ""

    def __post_init__(self) -> None:
        if self.latency_ms < 0:
            raise ValueError("a latência não pode ser negativa")
        if self.sample < 1:
            raise ValueError("os números de amostra começam em 1")


@dataclass(frozen=True)
class CriterionResult:
    """Whether one criterion held, and what was seen."""

    criterion: Criterion
    passed: bool
    evidence: str = ""


@dataclass(frozen=True)
class Verdict:
    """The judgement on one answer: every criterion, and the failures found.

    `alternative` names the regimen the answer was judged against, when the
    case has more than one: the one it met, or the one it came closest to.
    """

    case_id: str
    model: str
    results: tuple[CriterionResult, ...] = field(default_factory=tuple)
    alternative: str = ""

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
