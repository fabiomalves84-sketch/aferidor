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
    tally_by_model,
)
from .models import Answer, Case, Verdict
from .risk import Risk

HEADER_NOTE = (
    "Este documento mede um sistema, não um doente. Não aconselha, não trata e "
    "não substitui julgamento clínico."
)


def _percent(value: float) -> str:
    return f"{value * 100:.0f}%"


def _risk_line(critical_cases: int, total_cases: int) -> str:
    """The headline number: cases, not samples.

    Um caso conta como falha crítica se qualquer amostra a produziu. Um médico
    só vê uma resposta e não escolhe qual das amostras lhe calha.
    """
    if critical_cases:
        return (
            f"**{critical_cases} de {total_cases} casos com falha de risco crítico em "
            "pelo menos uma amostra.** Uma falha crítica é um erro de dose, uma interação "
            "ou contraindicação omitida, ou um facto inventado."
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
    sources_verified: bool = False,
    today: date | None = None,
) -> str:
    """Write the whole report as Markdown."""
    by_case = {c.case_id: c for c in cases}
    known_ids = {c.case_id for c in cases}
    matched_answers = [a for a in answers if a.case_id in known_ids]
    pairs = list(zip(matched_answers, verdicts))
    per_model = tally_by_model(verdicts)
    consistency = consistency_by_case(cases, answers, verdicts)
    consistency_per_model = consistency_by_model(consistency)

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


__all__ = ["build", "HEADER_NOTE"]
