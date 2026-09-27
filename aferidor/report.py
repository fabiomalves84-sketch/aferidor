"""The report: what the run found, written for someone who does not read code.

Three rules shape what goes in and in what order.

The headline is never the overall score. A single percentage is the one number
that hides the thing worth knowing, so the count of critical failures is put
where the eye lands first and the percentage comes after it.

Nothing is claimed that the run did not observe. Cases that were never answered
are named. Sources not yet confirmed by a person are stated at the top, because
a bench built on an unverified reference measures the model against a mistake
and calls it the model's.

Every failure is shown with the text that caused it. A reader who disagrees
with a verdict has to be able to see what the grader saw and say so.
"""

from __future__ import annotations

from datetime import date

from .grading import (
    Tally,
    consistency_by_case,
    consistency_by_model,
    expected_samples,
    match_answers,
    missing_samples,
    run_conditions,
    tally_by_model,
)
from .models import Answer, Case, Verdict
from .protocolo import Outcome, Protocol, evaluate, warnings as protocol_warnings
from .risk import Risk

HEADER_NOTE = (
    "Este documento mede um sistema, não um doente. Não aconselha, não trata e "
    "não substitui julgamento clínico."
)


def _percent(value: float) -> str:
    return f"{value * 100:.0f}%"


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
    gaps: dict[tuple[str, str], tuple[int, ...]], expected: dict[str, int]
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
        parts.append(f"{case_id} ({model}, {have} de {wanted} amostras)")
    return ", ".join(parts)


def conditions_rows(
    answers: list[Answer], cases_source: tuple[str, str] | None = None
) -> list[tuple[str, str]]:
    """What was measured, with what, and when, as (label, value) rows.

    Shared by the Markdown and the HTML report, so both identify the run the
    same way. The date a report is written says nothing about when the
    answers were obtained, and a report that cannot say under what
    conditions its answers were obtained cannot be compared with any other.
    """
    rows: list[tuple[str, str]] = []
    if cases_source:
        path, digest = cases_source
        rows.append(("Banco de casos", f"{path} (SHA-256 {digest[:12]})"))
    for model, found in run_conditions(answers).items():
        period = found.first_asked.strftime("%Y-%m-%d %H:%M")
        if found.last_asked.date() == found.first_asked.date():
            period += found.last_asked.strftime(" a %H:%M")
        else:
            period += found.last_asked.strftime(" a %Y-%m-%d %H:%M")
        temperatures = ", ".join(f"{v:.1f}".replace(".", ",") for v in found.temperatures)
        tokens = ", ".join("não registado" if v is None else str(v) for v in found.max_tokens)
        builds = ", ".join(b or "não registada" for b in found.builds)
        rows.append((
            model,
            f"{found.answers} respostas, recolhidas {period}; temperatura {temperatures};"
            f" tokens_max {tokens}; versão {builds}",
        ))
    return rows


def protocol_findings(
    protocol: Protocol,
    answers: list[Answer],
    summaries: dict,
    cases_source: tuple[str, str] | None,
) -> tuple[list[str], list[Outcome]]:
    """The protocol's warnings and its verdict per model, shared by both reports."""
    found = run_conditions(answers)
    found_warnings = protocol_warnings(
        protocol,
        min((a.asked_at for a in answers), default=None),
        cases_source[1] if cases_source else None,
        expected_samples(answers),
        {model: c.temperatures for model, c in found.items()},
    )
    return found_warnings, [evaluate(protocol, summaries[m]) for m in sorted(summaries)]


def _risk_line(critical_cases: int, total_cases: int) -> str:
    """The headline number: cases, not samples.

    Um caso conta como falha crítica se qualquer amostra a produziu. Um médico
    só vê uma resposta e não escolhe qual das amostras lhe calha.
    """
    if critical_cases:
        return (
            f"**{critical_cases} de {total_cases} casos com falha de risco crítico em "
            "pelo menos uma amostra.** Uma falha crítica é um erro de dose, uma interação "
            "ou contraindicação omitida, um encaminhamento urgente omitido, ou um facto "
            "inventado."
        )
    return "**Nenhum caso com falha de risco crítico em nenhuma amostra.**"


def _failure_table(counts: Tally) -> list[str]:
    if not counts.by_failure:
        return ["Nenhuma falha registada."]
    lines = ["| Tipo de falha | Risco | Respostas |", "|---|---|---|"]
    for failure, number in counts.worst_first():
        lines.append(f"| `{failure.value}` | {failure.risk} | {number} |")
    return lines


def _case_detail(pairs: list[tuple[Answer, Verdict]], cases: dict[str, Case]) -> list[str]:
    """One block per failed case, not per failed sample.

    With repetitions, several samples of the same case can fail; showing each
    one under its own heading would repeat the question and the source for no
    reason. One representative failing sample is enough to see what went
    wrong; `relatorio --formato html` is where every distinct answer is shown.
    """
    lines: list[str] = []
    failed = [(a, v) for a, v in pairs if not v.passed]
    if not failed:
        return ["Todas as respostas passaram em todos os critérios."]

    order = {Risk.CRITICO: 0, Risk.ALTO: 1, Risk.MEDIO: 2, Risk.BAIXO: 3}
    failed.sort(key=lambda av: order.get(av[1].worst_risk, 9) if av[1].worst_risk else 9)

    seen: set[str] = set()
    for answer, verdict in failed:
        if verdict.case_id in seen:
            continue
        seen.add(verdict.case_id)
        case = cases.get(verdict.case_id)
        lines.append(f"#### {verdict.case_id}")
        lines.append("")
        if case:
            lines.append(f"**Pergunta.** {case.question}")
            lines.append("")
            lines.append(f"**Resposta de referência.** {case.reference}")
            lines.append("")
            lines.append(f"**Fonte.** {case.source.name}, {case.source.reference}")
            lines.append("")
        if verdict.alternative:
            lines.append(f"**Corrigida contra a alternativa:** {verdict.alternative}.")
            lines.append("")
        lines.append(f"**O que o modelo respondeu (amostra {answer.sample}).**")
        lines.append("")
        lines.append("> " + answer.text.strip().replace("\n", "\n> "))
        lines.append("")
        lines.append("**Critérios que falharam.**")
        lines.append("")
        for result in verdict.results:
            if not result.passed:
                lines.append(
                    f"- `{result.criterion.failure.value}` "
                    f"(risco {result.criterion.failure.risk}): {result.evidence}"
                )
        lines.append("")
    return lines


def build(
    cases: list[Case],
    answers: list[Answer],
    verdicts: list[Verdict],
    missing: list[str] | None = None,
    reasons: dict[str, str] | None = None,
    sources_verified: bool = False,
    today: date | None = None,
    cases_source: tuple[str, str] | None = None,
    protocol: Protocol | None = None,
) -> str:
    """Write the whole report as Markdown.

    `cases_source` is the case file's path and SHA-256, when known.
    """
    by_case = {c.case_id: c for c in cases}
    pairs = match_answers(cases, answers, verdicts)
    per_model = tally_by_model(verdicts)
    consistency = consistency_by_case(cases, answers, verdicts)
    consistency_per_model = consistency_by_model(consistency)

    out: list[str] = []
    out.append("# Relatório do Aferidor")
    out.append("")
    out.append(f"Relatório escrito em {(today or date.today()).isoformat()}.")
    out.append("")
    out.append(HEADER_NOTE)
    out.append("")
    rows = conditions_rows(answers, cases_source)
    if rows:
        out.append("## Condições do ensaio")
        out.append("")
        for label, value in rows:
            out.append(f"- **{label}**: {value}")
        out.append("")

    if not sources_verified:
        out.append(
            "> **Aviso.** As fontes deste conjunto de casos ainda não foram confirmadas "
            "por uma pessoa. Até isso acontecer, os números abaixo medem o modelo contra "
            "valores transcritos automaticamente, e um valor de referência errado aparece "
            "aqui como erro do modelo. Ver `casos/VERIFICACAO.md`."
        )
        out.append("")

    if missing:
        out.append(
            "> **Casos sem resposta.** "
            + format_missing(missing, reasons)
            + ". Não entram em nenhuma contagem deste relatório."
        )
        out.append("")

    gaps = missing_samples(cases, answers)
    if gaps:
        out.append(
            "> **Amostras em falta.** "
            + format_missing_samples(gaps, expected_samples(answers))
            + ". Não muda nenhuma contagem abaixo; só nomeia o que já era invisível "
            "nelas."
        )
        out.append("")

    if not per_model:
        out.append("Não há vereditos para relatar.")
        out.append("")
        return "\n".join(out)

    if protocol is not None:
        found_warnings, outcomes = protocol_findings(
            protocol, answers, consistency_per_model, cases_source
        )
        out.append("## Critério de aprovação")
        out.append("")
        out.append(
            f"Protocolo **{protocol.name}**, escrito a {protocol.written_on.isoformat()} "
            f"(`{protocol.path}`, SHA-256 {protocol.sha256[:12]})."
        )
        out.append("")
        for warning in found_warnings:
            out.append(f"> **Aviso.** {warning[0].upper() + warning[1:]}.")
            out.append("")
        out.append("| Modelo | Resultado | " + " | ".join(c.label for c in outcomes[0].checks) + " |")
        out.append("|---|---|" + "---|" * len(outcomes[0].checks))
        for outcome in outcomes:
            cells = [
                f"{c.observed} ({c.limit}){'' if c.met else ', **não cumpre**'}"
                for c in outcome.checks
            ]
            result = "aprovado" if outcome.approved else "**reprovado**"
            out.append(f"| `{outcome.model}` | {result} | " + " | ".join(cells) + " |")
        out.append("")

    if len(per_model) > 1:
        out.append("## Comparação")
        out.append("")
        out.append(
            "| Modelo | Casos com falha crítica em alguma amostra | Casos instáveis | "
            "Taxa de amostras corretas |"
        )
        out.append("|---|---|---|---|")
        for model in per_model:
            summary = consistency_per_model[model]
            out.append(
                f"| `{model}` | {summary.critical_cases} | {summary.unstable_cases} | "
                f"{_percent(summary.sample_accuracy)} |"
            )
        out.append("")
        out.append(
            "As duas primeiras colunas pesam mais do que a terceira: uma taxa de amostras "
            "corretas alta ainda pode esconder casos que falham sempre, ou casos instáveis "
            "cuja resposta certa depende de que amostra o médico calhou a ver."
        )
        out.append("")

    for model, counts in per_model.items():
        summary = consistency_per_model[model]
        out.append(f"## {model}")
        out.append("")
        out.append(_risk_line(summary.critical_cases, summary.cases))
        out.append("")
        out.append(
            f"{counts.passed} de {counts.total} amostras passaram em todos os critérios "
            f"({_percent(counts.accuracy)})."
        )
        if summary.unstable_cases:
            out.append("")
            out.append(
                f"{summary.unstable_cases} de {summary.cases} casos deram respostas "
                "diferentes em amostras diferentes do mesmo modelo: instáveis."
            )
        out.append("")
        out.append("### Falhas por tipo")
        out.append("")
        out.extend(_failure_table(counts))
        out.append("")
        out.append("### Respostas que falharam")
        out.append("")
        model_pairs = [(a, v) for a, v in pairs if v.model == model]
        out.extend(_case_detail(model_pairs, by_case))
        out.append("")

    out.append("## Como ler isto")
    out.append("")
    out.append(
        "A taxa de respostas corretas sozinha não serve. Um sistema que erra 5% das "
        "doses e outro que erra 5% do formato tem a mesma taxa e nada em comum. Por isso "
        "cada falha é classificada por tipo e cada tipo carrega um risco clínico, e a "
        "leitura começa sempre pelas falhas críticas."
    )
    out.append("")
    return "\n".join(out)


__all__ = [
    "build",
    "conditions_rows",
    "protocol_findings",
    "format_missing",
    "format_missing_samples",
    "HEADER_NOTE",
]
