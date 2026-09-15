"""The HTML report: the same numbers as the Markdown one, laid out to scan at a glance.

This module computes nothing. Every count comes from `grading`; this file only
decides how to lay it out and how to escape it. That boundary is what lets
`relatorio --formato html` and the Markdown report agree by construction
instead of by discipline between two hand written documents.

Everything that came out of a model is untrusted text and is escaped before it
reaches the page. A model that writes `<script>` into an answer must not get
to run it in whoever opens this file.
"""

from __future__ import annotations

import html as _html
from datetime import date

from .grading import (
    Consistency,
    ConsistencyState,
    ConsistencySummary,
    consistency_by_case,
    consistency_by_model,
    pairs_by_case,
    tally_by_model,
)
from .models import Answer, Case, Verdict
from .report import HEADER_NOTE

_CELL_CLASS = {
    ConsistencyState.ESTAVEL_CERTO: "ok",
    ConsistencyState.ESTAVEL_ERRADO: "erro",
    ConsistencyState.INSTAVEL: "instavel",
}


def _esc(value: object) -> str:
    return _html.escape(str(value), quote=True)


def _grouped_cases(cases: list[Case]) -> list[tuple[str, list[Case]]]:
    """Cases in their original order, bucketed by category on first sight."""
    order: list[str] = []
    by_category: dict[str, list[Case]] = {}
    for case in cases:
        if case.category not in by_category:
            order.append(case.category)
            by_category[case.category] = []
        by_category[case.category].append(case)
    return [(category, by_category[category]) for category in order]


def _headline(models: list[str], summaries: dict[str, ConsistencySummary]) -> str:
    items = []
    for model in models:
        summary = summaries[model]
        items.append(
            "<li><span class=\"modelo\">" + _esc(model) + "</span>"
            "<span class=\"destaque\">" + str(summary.critical_cases) + "</span>"
            "<span class=\"legenda\">de " + str(summary.cases)
            + " casos com falha crítica em alguma amostra</span></li>"
        )
    return "<ul class=\"headline\">" + "".join(items) + "</ul>"


def _cell(entry: Consistency | None) -> tuple[str, str]:
    if entry is None:
        return "sem-resposta", "sem resposta"
    label = _esc(entry.state.label)
    if entry.state is ConsistencyState.ESTAVEL_CERTO:
        return "ok", label
    failure = _esc(entry.worst_failure.value) if entry.worst_failure else ""
    return _CELL_CLASS[entry.state], f"{label}<br>{failure}"


def _grid(
    cases: list[Case], models: list[str], consistency: dict[tuple[str, str], Consistency]
) -> str:
    out = ['<div class="grade-wrap"><table class="grade">']
    out.append(
        "<thead><tr><th>Caso</th>"
        + "".join(f"<th>{_esc(model)}</th>" for model in models)
        + "</tr></thead>"
    )
    out.append("<tbody>")
    for category, group in _grouped_cases(cases):
        out.append(
            f'<tr class="categoria"><td colspan="{len(models) + 1}">{_esc(category)}</td></tr>'
        )
        for case in group:
            out.append(f'<tr><th scope="row">{_esc(case.case_id)}</th>')
            for model in models:
                css_class, text = _cell(consistency.get((case.case_id, model)))
                out.append(f'<td class="cel {css_class}">{text}</td>')
            out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _sample_block(answer: Answer, verdict: Verdict) -> str:
    out = [f"<blockquote>{_esc(answer.text)}</blockquote>"]
    if verdict.passed:
        out.append(f'<p class="passou">amostra {answer.sample}: passou em todos os critérios</p>')
        return "".join(out)
    out.append(f'<p class="amostra-numero">amostra {answer.sample}</p>')
    out.append("<ul>")
    for result in verdict.results:
        if not result.passed:
            out.append(
                f"<li><code>{_esc(result.criterion.failure.value)}</code> "
                f"(risco {_esc(result.criterion.failure.risk)}): {_esc(result.evidence)}</li>"
            )
    out.append("</ul>")
    return "".join(out)


def _detail(
    cases: list[Case],
    models: list[str],
    consistency: dict[tuple[str, str], Consistency],
    pairs: dict[tuple[str, str], list[tuple[Answer, Verdict]]],
) -> str:
    out = ["<section class=\"detalhe\"><h2>Casos com falha</h2>"]
    any_case = False
    for case in cases:
        failing_models = [
            model
            for model in models
            if (entry := consistency.get((case.case_id, model))) is not None
            and entry.state is not ConsistencyState.ESTAVEL_CERTO
        ]
        if not failing_models:
            continue
        any_case = True
        out.append(f"<details><summary>{_esc(case.case_id)}</summary>")
        out.append(f"<p><strong>Pergunta.</strong> {_esc(case.question)}</p>")
        out.append(f"<p><strong>Resposta de referência.</strong> {_esc(case.reference)}</p>")
        out.append(
            f"<p><strong>Fonte.</strong> {_esc(case.source.name)}, "
            f"{_esc(case.source.reference)}</p>"
        )
        for model in failing_models:
            out.append(f"<h4>{_esc(model)}</h4>")
            seen: set[str] = set()
            for answer, verdict in pairs.get((case.case_id, model), []):
                if answer.text in seen:
                    continue
                seen.add(answer.text)
                out.append(_sample_block(answer, verdict))
        out.append("</details>")
    if not any_case:
        out.append("<p>Nenhum caso com falha.</p>")
    out.append("</section>")
    return "".join(out)


_STYLE = """
:root {
  color-scheme: light dark;
  --bg: #ffffff;
  --fg: #1a1a1a;
  --muted: #5a5a5a;
  --border: #dcdcdc;
  --card: #f7f7f7;
  --ok-bg: #e3f5e8; --ok-fg: #146c2e;
  --erro-bg: #fbe6e4; --erro-fg: #9c2a20;
  --instavel-bg: #fdf1da; --instavel-fg: #8a5a00;
  --sem-bg: #eeeeee; --sem-fg: #6b6b6b;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181b;
    --fg: #e9e9e9;
    --muted: #a7a7a7;
    --border: #3a3d41;
    --card: #1f2226;
    --ok-bg: #133620; --ok-fg: #7fdb9a;
    --erro-bg: #3a1917; --erro-fg: #ff9b90;
    --instavel-bg: #3a2c0c; --instavel-fg: #ffcf70;
    --sem-bg: #26292d; --sem-fg: #9a9a9a;
  }
}
* { box-sizing: border-box; }
body {
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  line-height: 1.5;
  padding: 1rem;
  max-width: 70rem;
  margin: 0 auto;
}
h1, h2, h3, h4 { line-height: 1.25; }
.aviso {
  background: var(--instavel-bg);
  color: var(--instavel-fg);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  margin: 0.75rem 0;
}
ul.headline {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}
ul.headline li {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  min-width: 14rem;
  flex: 1 1 14rem;
}
ul.headline .modelo { display: block; font-weight: 600; word-break: break-all; }
ul.headline .destaque { display: block; font-size: 2rem; font-weight: 700; }
ul.headline .legenda { display: block; color: var(--muted); font-size: 0.85rem; }
.grade-wrap { overflow-x: auto; margin: 1rem 0; }
table.grade { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
table.grade th, table.grade td {
  border: 1px solid var(--border);
  padding: 0.4rem 0.6rem;
  text-align: left;
  white-space: nowrap;
}
table.grade tr.categoria td {
  background: var(--card);
  font-weight: 600;
  white-space: normal;
}
td.cel.ok { background: var(--ok-bg); color: var(--ok-fg); }
td.cel.erro { background: var(--erro-bg); color: var(--erro-fg); }
td.cel.instavel { background: var(--instavel-bg); color: var(--instavel-fg); }
td.cel.sem-resposta { background: var(--sem-bg); color: var(--sem-fg); }
section.detalhe details {
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 0.5rem 1rem;
  margin: 0.5rem 0;
  background: var(--card);
}
section.detalhe summary { cursor: pointer; font-weight: 600; }
blockquote {
  border-left: 3px solid var(--border);
  margin: 0.5rem 0;
  padding: 0.25rem 0.75rem;
  white-space: pre-wrap;
}
p.passou { color: var(--ok-fg); }
p.amostra-numero { color: var(--muted); margin-bottom: 0.1rem; }
code { background: var(--card); padding: 0.1rem 0.3rem; border-radius: 0.25rem; }
@media (max-width: 30rem) {
  body { padding: 0.5rem; }
  ul.headline .destaque { font-size: 1.5rem; }
}
"""


def build(
    cases: list[Case],
    answers: list[Answer],
    verdicts: list[Verdict],
    missing: list[str] | None = None,
    sources_verified: bool = False,
    today: date | None = None,
) -> str:
    """Write the whole report as one self contained HTML file."""
    per_model = tally_by_model(verdicts)
    models = list(per_model)

    out: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="pt-PT"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Relatório do Aferidor</title><style>{_STYLE}</style></head><body>",
    ]
    out.append("<h1>Relatório do Aferidor</h1>")
    out.append(f'<p class="data">Data: {_esc((today or date.today()).isoformat())}</p>')
    out.append(f"<p>{_esc(HEADER_NOTE)}</p>")

    if not sources_verified:
        out.append(
            '<div class="aviso"><strong>Aviso.</strong> As fontes deste conjunto de casos '
            "ainda não foram confirmadas por uma pessoa. Até isso acontecer, os números "
            "abaixo medem o modelo contra valores transcritos automaticamente. "
            "Ver <code>casos/VERIFICACAO.md</code>.</div>"
        )
    if missing:
        out.append(
            '<div class="aviso"><strong>Casos sem resposta.</strong> '
            + _esc(", ".join(sorted(set(missing))))
            + " Não entram em nenhuma contagem deste relatório.</div>"
        )

    if not models:
        out.append("<p>Não há vereditos para relatar.</p>")
        out.append("</body></html>")
        return "".join(out)

    consistency = consistency_by_case(cases, answers, verdicts)
    summaries = consistency_by_model(consistency)
    pairs = pairs_by_case(cases, answers, verdicts)

    out.append(_headline(models, summaries))
    out.append(_grid(cases, models, consistency))
    out.append(_detail(cases, models, consistency, pairs))
    out.append("</body></html>")

    return "".join(out)


__all__ = ["build"]
