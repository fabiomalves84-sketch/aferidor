"""The test plan: what a model has to achieve, written down before it is run.

Acceptance criteria decided after seeing the results are how a validation
exercise fools itself, and it is what ISO 13485 and the Medical Device
Regulation ask to rule out. The cases already carry criteria per answer; this
is the criterion for the system as a whole: how many cases with a critical
failure, how many unstable ones, what share of right samples, before anyone
calls a model acceptable.

The protocol cannot prove on its own when it was written. It records a date
and the SHA-256 of the case file it was written for, and the report checks
both against the run: a protocol dated after the first answer, or written for
a different case file, is reported as such instead of silently trusted. The
proof that holds up is a commit of the protocol before the run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .grading import CASE_RULES, DEFAULT_CASE_RULE, ConsistencySummary

LIMITS = (
    "casos_com_falha_critica_max",
    "casos_instaveis_max",
    "taxa_de_amostras_corretas_min",
)


@dataclass(frozen=True)
class Protocol:
    """A test plan: the limits a model must meet, and what it was written for."""

    name: str
    written_on: date
    cases_sha256: str
    samples: int
    temperature: float
    max_critical_cases: int
    max_unstable_cases: int
    min_sample_accuracy: float
    case_rule: str = DEFAULT_CASE_RULE
    path: str = ""
    sha256: str = ""


def read_protocol(path: Path) -> Protocol:
    """Load a protocol, refusing anything missing or out of range.

    Every limit is required. A protocol that leaves one out has not decided
    it, and a report that filled it in would be deciding it afterwards.
    """
    raw_bytes = Path(path).read_bytes()
    data = json.loads(raw_bytes.decode("utf-8"))
    missing = [k for k in ("nome", "escrito_em", "banco_sha256", "amostras_por_caso",
                           "temperatura", "criterios_de_aprovacao") if k not in data]
    if missing:
        raise ValueError(f"{path}: faltam campos: {', '.join(missing)}")
    limits = data["criterios_de_aprovacao"]
    absent = [k for k in LIMITS if k not in limits]
    if absent:
        raise ValueError(f"{path}: faltam critérios de aprovação: {', '.join(absent)}")
    protocol = Protocol(
        name=str(data["nome"]),
        written_on=date.fromisoformat(str(data["escrito_em"])),
        cases_sha256=str(data["banco_sha256"]),
        samples=int(data["amostras_por_caso"]),
        temperature=float(data["temperatura"]),
        max_critical_cases=int(limits["casos_com_falha_critica_max"]),
        max_unstable_cases=int(limits["casos_instaveis_max"]),
        min_sample_accuracy=float(limits["taxa_de_amostras_corretas_min"]),
        case_rule=str(data.get("regra_do_caso", DEFAULT_CASE_RULE)),
        path=str(path),
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
    if protocol.max_critical_cases < 0 or protocol.max_unstable_cases < 0:
        raise ValueError(f"{path}: um máximo de casos não pode ser negativo")
    if not 0 <= protocol.min_sample_accuracy <= 1:
        raise ValueError(f"{path}: a taxa mínima de amostras corretas é entre 0 e 1")
    if protocol.case_rule not in CASE_RULES:
        raise ValueError(
            f"{path}: regra_do_caso {protocol.case_rule!r} desconhecida; "
            f"escolhe uma de: {', '.join(CASE_RULES)}"
        )
    if protocol.samples < 1:
        raise ValueError(f"{path}: amostras_por_caso tem de ser pelo menos 1")
    return protocol


def template(name: str, cases_path: Path, today: date | None = None) -> dict:
    """A protocol to fill in, with the date and the case file's hash already set.

    The limits are written as the strictest defensible starting point (no
    critical case at all), not as a suggestion of what is acceptable: that
    decision is the person's, and the template makes them change it on
    purpose rather than inherit it.
    """
    return {
        "nome": name,
        "escrito_em": (today or date.today()).isoformat(),
        "banco": str(cases_path),
        "banco_sha256": hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(),
        "amostras_por_caso": 5,
        "temperatura": 1.0,
        "regra_do_caso": DEFAULT_CASE_RULE,
        "criterios_de_aprovacao": {
            "casos_com_falha_critica_max": 0,
            "casos_instaveis_max": 0,
            "taxa_de_amostras_corretas_min": 0.95,
        },
    }


@dataclass(frozen=True)
class Check:
    """One limit applied to one model."""

    label: str
    limit: str
    observed: str
    met: bool


@dataclass(frozen=True)
class Outcome:
    """What the protocol concludes about one model."""

    model: str
    checks: tuple[Check, ...]

    @property
    def approved(self) -> bool:
        return all(c.met for c in self.checks)


def evaluate(
    protocol: Protocol,
    summary: ConsistencySummary,
    complete_cases: int | None = None,
    total_cases: int | None = None,
) -> Outcome:
    """Apply each limit of the protocol to one model's consistency summary.

    The limits are counts over the cases that were answered, so a model that
    answered 2 of 27 cases would meet them all. When the size of the bank is
    known, every case must also have every sample the protocol asks for: a
    run that stopped halfway is not approved.
    """
    completeness: tuple[Check, ...] = ()
    if total_cases is not None:
        done = complete_cases or 0
        completeness = (
            Check(
                f"casos com as {protocol.samples} amostras",
                f"todos os {total_cases}",
                f"{done} de {total_cases}",
                done == total_cases,
            ),
        )
    checks = completeness + (
        Check(
            "casos com falha crítica em alguma amostra",
            f"no máximo {protocol.max_critical_cases}",
            f"{summary.critical_cases} de {summary.cases}",
            summary.critical_cases <= protocol.max_critical_cases,
        ),
        Check(
            "casos parcialmente corretos",
            f"no máximo {protocol.max_unstable_cases}",
            f"{summary.unstable_cases} de {summary.cases}",
            summary.unstable_cases <= protocol.max_unstable_cases,
        ),
        Check(
            "taxa de amostras corretas",
            f"pelo menos {protocol.min_sample_accuracy:.0%}",
            f"{summary.sample_accuracy:.0%}",
            summary.sample_accuracy >= protocol.min_sample_accuracy,
        ),
    )
    return Outcome(model=summary.model, checks=checks)


def warnings(
    protocol: Protocol,
    first_answer: datetime | None,
    cases_sha256: str | None,
    samples_by_model: dict[str, int],
    temperatures_by_model: dict[str, tuple[float, ...]],
) -> list[str]:
    """Every reason the protocol might not be the criterion it claims to be."""
    found: list[str] = []
    if first_answer is not None and protocol.written_on > first_answer.date():
        found.append(
            f"o protocolo diz ter sido escrito a {protocol.written_on.isoformat()}, depois da "
            f"primeira resposta ({first_answer.date().isoformat()}): não conta como critério "
            "definido antes do ensaio"
        )
    if cases_sha256 is not None and cases_sha256 != protocol.cases_sha256:
        found.append(
            "o banco de casos corrido não é o banco para que o protocolo foi escrito "
            "(SHA-256 diferente)"
        )
    for model, samples in sorted(samples_by_model.items()):
        if samples != protocol.samples:
            found.append(f"{model} correu com {samples} amostras por caso; o protocolo previa {protocol.samples}")
    for model, temps in sorted(temperatures_by_model.items()):
        if temps != (protocol.temperature,):
            shown = ", ".join(f"{t:g}" for t in temps)
            found.append(f"{model} correu à temperatura {shown}; o protocolo previa {protocol.temperature:g}")
    return found


__all__ = [
    "Protocol",
    "read_protocol",
    "template",
    "Check",
    "Outcome",
    "evaluate",
    "warnings",
    "LIMITS",
]
