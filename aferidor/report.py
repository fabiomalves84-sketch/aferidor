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

from .grading import Tally, tally_by_model
from .models import Answer, Case, Verdict
from .risk import Risk

HEADER_NOTE = (
    "Este documento mede um sistema, não um doente. Não aconselha, não trata e "
    "não substitui julgamento clínico."
)


def _percent(value: float) -> str:
    return f"{value * 100:.0f}%"


def _risk_line(counts: Tally) -> str:
    if counts.critical:
        return (
            f"**{counts.critical} de {counts.total} respostas com falha de risco crítico.** "
            "Uma falha crítica é um erro de dose, uma interação ou contraindicação omitida, "
            "ou um facto inventado."
        )
    return "**Nenhuma falha de risco crítico.**"


def _failure_table(counts: Tally) -> list[str]:
    if not counts.by_failure:
        return ["Nenhuma falha registada."]
    lines = ["| Tipo de falha | Risco | Respostas |", "|---|---|---|"]
    for failure, number in counts.worst_first():
        lines.append(f"| `{failure.value}` | {failure.risk} | {number} |")
    return lines


def _case_detail(
    verdicts: list[Verdict], cases: dict[str, Case], answers: dict[tuple[str, str], Answer]
) -> list[str]:
    lines: list[str] = []
    failed = [v for v in verdicts if not v.passed]
    if not failed:
        return ["Todas as respostas passaram em todos os critérios."]

    order = {Risk.CRITICO: 0, Risk.ALTO: 1, Risk.MEDIO: 2, Risk.BAIXO: 3}
    failed.sort(key=lambda v: order.get(v.worst_risk, 9) if v.worst_risk else 9)

    for verdict in failed:
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
        answer = answers.get((verdict.case_id, verdict.model))
        if answer:
            lines.append("**O que o modelo respondeu.**")
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
    sources_verified: bool = False,
    today: date | None = None,
) -> str:
    """Write the whole report as Markdown."""
    by_case = {c.case_id: c for c in cases}
    by_answer = {(a.case_id, a.model): a for a in answers}
    per_model = tally_by_model(verdicts)

    out: list[str] = []
    out.append("# Relatório do Aferidor")
    out.append("")
    out.append(f"Data: {(today or date.today()).isoformat()}")
    out.append("")
    out.append(HEADER_NOTE)
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
            + ", ".join(sorted(set(missing)))
            + ". Não entram em nenhuma contagem deste relatório."
        )
        out.append("")

    if not per_model:
        out.append("Não há vereditos para relatar.")
        out.append("")
        return "\n".join(out)

    if len(per_model) > 1:
        out.append("## Comparação")
        out.append("")
        out.append("| Modelo | Corretas | Falhas críticas |")
        out.append("|---|---|---|")
        for model, counts in per_model.items():
            out.append(
                f"| `{model}` | {counts.passed}/{counts.total} "
                f"({_percent(counts.accuracy)}) | {counts.critical} |"
            )
        out.append("")
        out.append(
            "Duas taxas iguais podem esconder sistemas muito diferentes. A coluna das "
            "falhas críticas pesa mais do que a das corretas."
        )
        out.append("")

    for model, counts in per_model.items():
        out.append(f"## {model}")
        out.append("")
        out.append(_risk_line(counts))
        out.append("")
        out.append(
            f"{counts.passed} de {counts.total} respostas passaram em todos os critérios "
            f"({_percent(counts.accuracy)})."
        )
        out.append("")
        out.append("### Falhas por tipo")
        out.append("")
        out.extend(_failure_table(counts))
        out.append("")
        out.append("### Respostas que falharam")
        out.append("")
        out.extend(
            _case_detail([v for v in verdicts if v.model == model], by_case, by_answer)
        )
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


__all__ = ["build", "HEADER_NOTE"]
