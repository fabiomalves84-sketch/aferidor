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

from dataclasses import dataclass
from datetime import date

from . import build_id
from .comparacao import Ranking, is_significant, percent, ranking, top_tie
from .grading import (
    ConsistencySummary,
    Tally,
    consistency_by_case,
    consistency_by_model,
    expected_samples,
    match_answers,
    missing_samples,
    CASE_RULES,
    DEFAULT_CASE_RULE,
    right_cases_by_model,
    run_conditions,
    tally_by_model,
    wilson_interval,
)
from .lingua import language_by_model, language_line
from .models import Answer, Case, Verdict
from .protocolo import Outcome, Protocol, evaluate, warnings as protocol_warnings
from .risk import Risk
from .traducao import decimal, t

HEADER_NOTE = (
    "Este documento mede um sistema, não um doente. Não aconselha, não trata e "
    "não substitui julgamento clínico."
)
# Whether a specialist has reviewed a sample of the verdicts. The HTML report says "there is no
# reviewer yet" while this is False; when it becomes True the sentence stops saying so and claims
# nothing else about the review, because the report does not know which review it was. Changing it
# is a decision with a record: BRIEFING.md and the README have to say the same, and a test checks both.
CLINICAL_REVIEW_DONE = False
TRIAGE_NOTE = (
    "Os veredictos são a triagem automática do corretor; a validação por um "
    "especialista faz-se à parte, numa folha cega (`aferidor revisao`)."
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
    for model, found in run_conditions(answers).items():
        period = found.first_asked.strftime("%Y-%m-%d %H:%M")
        if found.last_asked.date() == found.first_asked.date():
            period += t(" a {fim}", lang, fim=found.last_asked.strftime("%H:%M"))
        else:
            period += t(" a {fim}", lang, fim=found.last_asked.strftime("%Y-%m-%d %H:%M"))
        temperatures = ", ".join(decimal(f"{v:.1f}", lang) for v in found.temperatures)
        tokens = ", ".join(t("não registado", lang) if v is None else str(v) for v in found.max_tokens)
        builds = ", ".join(b or t("não registada", lang) for b in found.builds)
        rows.append((
            model,
            t(
                "{n} respostas, recolhidas {periodo}; temperatura {temperatura}; tokens_max "
                "{tokens}; versão {versao}",
                lang, n=found.answers, periodo=period, temperatura=temperatures,
                tokens=tokens, versao=builds,
            ),
        ))
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
    )
    if case_ids is None:
        return found_warnings, [evaluate(protocol, summaries[m], lang=lang) for m in sorted(summaries)]
    complete = complete_cases_by_model(answers, case_ids, protocol.samples)
    return found_warnings, [
        evaluate(protocol, summaries[m], complete.get(m, 0), len(case_ids), lang)
        for m in sorted(summaries)
    ]


def interval_text(successes: int, total: int) -> str:
    """A 95% Wilson interval, written the way the report writes percentages."""
    low, high = wilson_interval(successes, total)
    return f"IC 95% {percent(low)} a {percent(high)}"


def how_counted(samples: int, rule: str) -> str:
    """How a case's samples become its state and its verdict, in plain words.

    The Markdown report's version; the HTML report has its own (`_how_counted`),
    with a row of dots for each state. Both say the same: the states and the
    right-or-wrong rule are the report's own vocabulary, and a reader who does
    not know them reads the numbers wrong.
    """
    n = samples or 1
    return (
        f"Cada caso foi colocado {n} {'vez' if n == 1 else 'vezes'} a cada modelo; cada "
        "resposta é uma amostra. Um caso é **sempre correto** quando todas as amostras são "
        "corretas, **nunca correto** quando nenhuma o é, e **parcialmente correto** nos "
        "restantes. Veredicto binário por caso: um caso é correto quando "
        f"{CASE_RULES[rule]}. Um caso nunca correto não tem necessariamente uma falha crítica, "
        "e um caso parcialmente correto pode ter uma; por isso as falhas críticas são contadas "
        "à parte."
    )


def _comparison_text(paired: Ranking) -> str | None:
    """The sentence under the table of models: who had fewer cases with a critical failure and whether
    that could be chance, or, when the two best share the proportion, only that they do.

    With three or more tied at the top the sentence names the first two, as the HTML report does: it
    is true, and it does not mention the others. None when the cases are not known.
    """
    if paired.p_value is None:
        return None
    first, second = paired.rows[0].model, paired.rows[1].model
    if len(top_tie(paired.rows)) > 1:
        return f"`{first}` e `{second}` tiveram a mesma proporção de casos com falha crítica."
    verdict = (
        "a diferença é estatisticamente significativa" if is_significant(paired.p_value)
        else "a diferença pode dever-se ao acaso"
    )
    shown = "p < 0,001" if paired.p_value < 0.001 else f"p = {paired.p_value:.3f}".replace(".", ",")
    return (
        f"`{first}` teve menos casos com falha crítica do que `{second}`. Nos casos em "
        f"que só um dos dois teve falha crítica ({paired.only_first} contra "
        f"{paired.only_second}), {verdict} (teste de McNemar exato, {shown}). O teste "
        "é emparelhado, porque os modelos responderam aos mesmos casos."
    )


def _risk_line(critical_cases: int, total_cases: int) -> str:
    """The headline number: cases, not samples, with how far it can be trusted.

    A case counts as a critical failure if any sample produced one. A doctor
    sees one answer and does not choose which of the samples it is.

    The interval is part of the number, not a footnote. With 27 cases, zero
    critical failures is still compatible with a true rate above one in ten,
    and a reader who sees only "0" reads a certainty the bench does not have.
    """
    if not total_cases:
        return "**Sem casos avaliados.**"
    interval = interval_text(critical_cases, total_cases)
    if critical_cases:
        return (
            f"**{critical_cases} de {total_cases} casos com falha de risco crítico em "
            f"pelo menos uma amostra** ({interval}). Uma falha crítica é um erro de dose, "
            "uma interação ou contraindicação omitida, um encaminhamento urgente omitido, "
            "ou um facto inventado."
        )
    _, high = wilson_interval(0, total_cases)
    return (
        "**Nenhum caso com falha de risco crítico em nenhuma amostra.** Com "
        f"{total_cases} casos, o resultado é compatível com uma proporção real de casos com falha "
        f"crítica até {percent(high)} ({interval})."
    )


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


@dataclass(frozen=True)
class _Counts:
    """What the sections of the report share: the data and the counts made from it, once."""

    cases: list[Case]
    answers: list[Answer]
    by_case: dict[str, Case]
    pairs: list[tuple[Answer, Verdict]]
    per_model: dict[str, Tally]
    consistency: dict
    summaries: dict[str, ConsistencySummary]


def _head_md(today: date | None) -> list[str]:
    return [
        "# Relatório do Aferidor", "",
        f"Relatório escrito em {(today or date.today()).isoformat()}.", "",
        HEADER_NOTE, "",
        TRIAGE_NOTE, "",
    ]


def _conditions_md(cases: list[Case], answers: list[Answer], cases_source: tuple[str, str] | None) -> list[str]:
    rows = conditions_rows(in_bank(cases, answers), cases_source)
    if not rows:
        return []
    return ["## Condições do ensaio", "", *[f"- **{label}**: {value}" for label, value in rows], ""]


def _notices_md(
    cases: list[Case], answers: list[Answer], missing: list[str] | None,
    reasons: dict[str, str] | None, sources_verified: bool,
) -> list[str]:
    out: list[str] = []
    if not sources_verified:
        out.append(
            "> **Aviso.** Nem todas as fontes destes casos foram confirmadas por uma pessoa. "
            "Até essa confirmação, os resultados medem o modelo contra valores transcritos "
            "automaticamente, e um valor de referência errado surge como erro do modelo. "
            "Ver `casos/VERIFICACAO.md`."
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
    return out


def _protocol_md(
    protocol: Protocol, answers: list[Answer], counts: _Counts, cases_source: tuple[str, str] | None,
) -> list[str]:
    found_warnings, outcomes = protocol_findings(
        protocol, answers, counts.summaries, cases_source, [case.case_id for case in counts.cases],
    )
    out = ["## Critério de aprovação", ""]
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
    return out


def _comparison_md(counts: _Counts, right: dict[str, tuple[int, int]]) -> list[str]:
    out = ["## Comparação", ""]
    out.append(
        "| Modelo | Casos com falha crítica em alguma amostra | Casos corretos | "
        "Casos parcialmente corretos | Amostras corretas |"
    )
    out.append("|---|---|---|---|---|")
    for model in counts.per_model:
        summary = counts.summaries[model]
        tally = counts.per_model[model]
        ok, total = right[model]
        out.append(
            f"| `{model}` | {summary.critical_cases} de {summary.cases} "
            f"({interval_text(summary.critical_cases, summary.cases)}) | "
            f"{ok} de {total} ({interval_text(ok, total)}) | "
            f"{summary.unstable_cases} de {summary.cases} | "
            f"{tally.passed} de {tally.total} ({interval_text(tally.passed, tally.total)}) |"
        )
    out.append("")
    out.append(
        "As três primeiras colunas contam casos; a última conta amostras (casos × "
        "amostras por caso). Uma taxa elevada de amostras corretas pode ocultar casos "
        "nunca corretos ou casos cujo resultado depende da amostra. Intervalos de Wilson a "
        "95%; o intervalo das amostras assume independência entre amostras, que não se "
        "verifica, pelo que é mais estreito do que deveria."
    )
    out.append("")
    comparison = _comparison_text(ranking(counts.summaries, counts.consistency))
    if comparison is not None:
        out.append(comparison)
        out.append("")
    return out


def _model_md(
    model: str, counts: _Counts, rule: str, right: dict[str, tuple[int, int]], languages: dict,
) -> list[str]:
    tally = counts.per_model[model]
    summary = counts.summaries[model]
    out = [f"## {model}", ""]
    out.append(_risk_line(summary.critical_cases, summary.cases))
    out.append("")
    ok, total = right[model]
    out.append(
        f"**Casos corretos: {ok} de {total}** ({interval_text(ok, total)}), pela regra: "
        f"{CASE_RULES[rule]}."
    )
    out.append("")
    out.append(
        f"{tally.passed} de {tally.total} amostras cumprem todos os critérios "
        f"({percent(tally.accuracy)}, {interval_text(tally.passed, tally.total)})."
    )
    if summary.unstable_cases:
        out.append("")
        out.append(
            f"{summary.unstable_cases} de {summary.cases} casos parcialmente corretos: o "
            "resultado variou entre amostras."
        )
    out.append("")
    out.append("### Falhas por tipo")
    out.append("")
    out.extend(_failure_table(tally))
    out.append("")
    out.append("### Português europeu")
    out.append("")
    out.append(language_line(languages[model]))
    out.append("")
    out.append(
        "Indicador independente, baseado numa lista curta de formas alheias ao português "
        "europeu atual. Não entra na contagem de falhas e subestima a frequência real."
    )
    out.append("")
    out.append("### Respostas que falharam")
    out.append("")
    model_pairs = [(a, v) for a, v in counts.pairs if v.model == model]
    out.extend(_case_detail(model_pairs, counts.by_case))
    out.append("")
    return out


def _interpretation_md() -> list[str]:
    return [
        "## Interpretação", "",
        "A taxa de respostas corretas, isolada, é insuficiente: um sistema que erra 5% das "
        "doses e outro que erra 5% do formato têm a mesma taxa e riscos muito diferentes. "
        "Cada falha é por isso classificada por tipo e por risco clínico, e a leitura começa "
        "pelas falhas críticas.",
        "",
    ]


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
    consistency = consistency_by_case(cases, answers, verdicts)
    counts = _Counts(
        cases=cases, answers=answers, by_case={c.case_id: c for c in cases},
        pairs=match_answers(cases, answers, verdicts), per_model=tally_by_model(verdicts),
        consistency=consistency, summaries=consistency_by_model(consistency),
    )

    out: list[str] = [
        *_head_md(today),
        *_conditions_md(cases, answers, cases_source),
        *_notices_md(cases, answers, missing, reasons, sources_verified),
    ]
    if not counts.per_model:
        out.append("Não há veredictos para relatar.")
        out.append("")
        return "\n".join(out)

    if protocol is not None:
        out.extend(_protocol_md(protocol, answers, counts, cases_source))

    rule = protocol.case_rule if protocol is not None else DEFAULT_CASE_RULE
    right = right_cases_by_model(consistency, rule)
    out.append("## Método de contagem")
    out.append("")
    out.append(how_counted(max(expected_samples(answers).values(), default=0), rule))
    out.append("")

    if len(counts.per_model) > 1:
        out.extend(_comparison_md(counts, right))

    languages = language_by_model(in_bank(cases, answers))
    for model in counts.per_model:
        out.extend(_model_md(model, counts, rule, right, languages))

    out.extend(_interpretation_md())
    return "\n".join(out)


__all__ = [
    "build",
    "conditions_rows",
    "protocol_findings",
    "interval_text",
    "how_counted",
    "format_missing",
    "format_missing_samples",
    "HEADER_NOTE",
    "TRIAGE_NOTE",
    "CLINICAL_REVIEW_DONE",
]
