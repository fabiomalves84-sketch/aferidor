"""What both reports say about the run before they say a result: the conditions it was made under,
the cases and samples that never came back, and what the protocol makes of it.

The Markdown report (`report`) and the HTML report (`html_report`) both read these, so the two
identify the run and judge it against the protocol the same way. Nothing here formats a page.
"""

from __future__ import annotations

from . import build_id, grader_id
from .grading import expected_samples, run_conditions
from .models import Answer, Case
from .protocolo import Outcome, Protocol, evaluate, warnings as protocol_warnings
from .traducao import decimal, t

# The sentence under the title of the Markdown report and in the footer of the HTML one.
HEADER_NOTE = (
    "Este documento mede um sistema, não um doente. Não aconselha, não trata e "
    "não substitui julgamento clínico."
)


def format_missing(missing: list[str], reasons: dict[str, str] | None = None) -> str:
    """The unanswered cases, each with its reason when one is known.

    A reason is only available for cases missed in the same process that
    also wrote this report (an `ensaio` run knows why its own model failed a
    case); a case missing from an older file, read back later, is named
    without one rather than guessed at.
    """
    reasons = reasons or {}
    parts = []
    for case_id in sorted(set(missing)):
        reason = reasons.get(case_id)
        parts.append(f"{case_id} ({reason})" if reason else case_id)
    return ", ".join(parts)


def format_missing_samples(
    gaps: dict[tuple[str, str], tuple[int, ...]], expected: dict[str, int], lang: str = "pt"
) -> str:
    """Every (caso, modelo) with fewer samples than that model was actually asked for.

    Shown as how many came in against how many were expected, for example
    "ATB-PAC-001 (local:qwen3:8b, 3 de 5 amostras)", so a partial case or a
    model that skipped a case entirely reads the same way as any other gap.
    """
    parts = []
    for case_id, model in sorted(gaps):
        wanted = expected[model]
        have = wanted - len(gaps[(case_id, model)])
        parts.append(t("{caso} ({modelo}, {a} de {n} amostras)", lang, caso=case_id, modelo=model, a=have, n=wanted))
    return ", ".join(parts)


def in_bank(cases: list[Case], answers: list[Answer]) -> list[Answer]:
    """Only the answers to cases of the bank being reported.

    A file can hold answers to another bank, or to cases left out by
    --limite; they are named as unknown elsewhere, and must not count in the
    conditions or in the language indicator of this bank.
    """
    ids = {case.case_id for case in cases}
    return [answer for answer in answers if answer.case_id in ids]


def graders_by_model(answers: list[Answer]) -> dict[str, tuple[str, ...]]:
    """The versions of the correction code the answers were asked under, per model; an answer recorded
    before the field existed counts as "" (no record)."""
    found: dict[str, set[str]] = {}
    for answer in answers:
        found.setdefault(answer.model, set()).add(answer.grader)
    return {model: tuple(sorted(graders)) for model, graders in found.items()}


def conditions_rows(
    answers: list[Answer], cases_source: tuple[str, str] | None = None, lang: str = "pt"
) -> list[tuple[str, str]]:
    """What was measured, with what, and when, as (label, value) rows.

    Shared by the Markdown and the HTML report, so both identify the run the
    same way. The date a report is written says nothing about when the
    answers were obtained, and a report that cannot say under what
    conditions its answers were obtained cannot be compared with any other.

    The label of the case-file row is always "Banco de casos", in any
    language: it is how a caller tells it from a model's row.
    """
    rows: list[tuple[str, str]] = []
    if cases_source:
        path, digest = cases_source
        rows.append(("Banco de casos", f"{path} (SHA-256 {digest[:12]})"))
    graders = graders_by_model(answers)
    for model, found in run_conditions(answers).items():
        period = found.first_asked.strftime("%Y-%m-%d %H:%M")
        if found.last_asked.date() == found.first_asked.date():
            period += t(" a {fim}", lang, fim=found.last_asked.strftime("%H:%M"))
        else:
            period += t(" a {fim}", lang, fim=found.last_asked.strftime("%Y-%m-%d %H:%M"))
        temperatures = ", ".join(decimal(f"{v:.1f}", lang) for v in found.temperatures)
        tokens = ", ".join(
            t("não registado", lang) if v is None else t("{n} tokens", lang, n=v) for v in found.max_tokens
        )
        builds = ", ".join(b or t("não registada", lang) for b in found.builds)
        row = t(
            "{n} respostas, recolhidas {periodo}; temperatura (grau de aleatoriedade) {temperatura}; "
            "limite de tamanho da resposta: {tokens}; versão {versao}",
            lang, n=found.answers, periodo=period, temperatura=temperatures,
            tokens=tokens, versao=builds,
        )
        recorded = [g for g in graders.get(model, ()) if g]
        if recorded:  # only the versions that are known; the warning says when some answers have none
            row += t("; corretor {corretor}", lang, corretor=", ".join(recorded))
        rows.append((model, row))
    return rows


def complete_cases_by_model(answers: list[Answer], case_ids: list[str], samples: int) -> dict[str, int]:
    """How many of these cases each model answered in every sample from 1 to `samples`."""
    got: dict[str, set[tuple[str, int]]] = {}
    for answer in answers:
        got.setdefault(answer.model, set()).add((answer.case_id, answer.sample))
    wanted = range(1, samples + 1)
    return {
        model: sum(1 for c in case_ids if all((c, s) in pairs for s in wanted))
        for model, pairs in got.items()
    }


def protocol_findings(
    protocol: Protocol,
    answers: list[Answer],
    summaries: dict,
    cases_source: tuple[str, str] | None,
    case_ids: list[str] | None = None,
    lang: str = "pt",
) -> tuple[list[str], list[Outcome]]:
    """The protocol's warnings and its verdict per model, shared by both reports.

    With `case_ids`, a model is only approved when it answered every case of
    the bank in every sample the protocol asks for.
    """
    found = run_conditions(answers)
    found_warnings = protocol_warnings(
        protocol,
        min((a.asked_at for a in answers), default=None),
        cases_source[1] if cases_source else None,
        expected_samples(answers),
        {model: c.temperatures for model, c in found.items()},
        lang,
        {model: c.builds for model, c in found.items()},
        build_id(),
        graders_by_model(answers),
        grader_id(),
    )
    if case_ids is None:
        return found_warnings, [evaluate(protocol, summaries[m], lang=lang) for m in sorted(summaries)]
    complete = complete_cases_by_model(answers, case_ids, protocol.samples)
    return found_warnings, [
        evaluate(protocol, summaries[m], complete.get(m, 0), len(case_ids), lang)
        for m in sorted(summaries)
    ]


__all__ = [
    "HEADER_NOTE",
    "complete_cases_by_model",
    "conditions_rows",
    "format_missing",
    "format_missing_samples",
    "graders_by_model",
    "in_bank",
    "protocol_findings",
]
