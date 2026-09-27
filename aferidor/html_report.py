"""The HTML report: the same numbers as the Markdown one, laid out to scan at a glance.

This module computes nothing. Every count comes from `grading`; this file only
decides how to lay it out and how to escape it. That boundary is what lets
`relatorio --formato html` and the Markdown report agree by construction
instead of by discipline between two hand written documents.

Everything that came out of a model is untrusted text and is escaped before it
reaches the page. A model that writes `<script>` into an answer must not get
to run it in whoever opens this file.

The page is written for someone who has never heard of the Aferidor: it
opens by saying what the bench is and how to read the page, before any
number. It is one self contained file with no script and nothing loaded
from the network, so it opens the same way from an email attachment, a
shared drive or a laptop without internet. Colour always travels with an
icon and a written label: a state is never shown by colour alone.
"""

from __future__ import annotations

import html as _html
import re
from datetime import date

from .grading import (
    Consistency,
    ConsistencyState,
    ConsistencySummary,
    Tally,
    consistency_by_case,
    consistency_by_model,
    expected_samples,
    missing_samples,
    pairs_by_case,
    states_by_model,
    tally_by_model,
)
from .lingua import LanguageSummary, language_by_model, language_line
from .models import Answer, Case, Verdict
from .protocolo import Protocol
from .report import (
    HEADER_NOTE,
    conditions_rows,
    format_missing,
    format_missing_samples,
    interval_text,
    protocol_findings,
)
from .risk import FailureType, Risk

# Each consistency state: css class and icon; the written label comes from the state.
_STATE_STYLE = {
    ConsistencyState.ESTAVEL_CERTO: ("ok", "✓"),
    ConsistencyState.INSTAVEL: ("instavel", "◐"),
    ConsistencyState.ESTAVEL_ERRADO: ("erro", "✕"),
}
_STATE_ORDER = (
    ConsistencyState.ESTAVEL_CERTO,
    ConsistencyState.INSTAVEL,
    ConsistencyState.ESTAVEL_ERRADO,
)
_RISK_CLASS = {
    Risk.CRITICO: "r-critico",
    Risk.ALTO: "r-alto",
    Risk.MEDIO: "r-medio",
    Risk.BAIXO: "r-baixo",
}
_RISK_LABEL = {Risk.CRITICO: "crítico", Risk.ALTO: "alto", Risk.MEDIO: "médio", Risk.BAIXO: "baixo"}
_FAILURE_LABEL = {
    FailureType.DOSE_INCORRETA: "Dose incorreta",
    FailureType.INTERACAO_OMITIDA: "Interação omitida",
    FailureType.CONTRAINDICACAO_OMITIDA: "Contraindicação omitida",
    FailureType.ALUCINACAO: "Facto ou fonte inventados",
    FailureType.ENCAMINHAMENTO_OMITIDO: "Encaminhamento urgente omitido",
    FailureType.AJUSTE_OMITIDO: "Ajuste de dose omitido",
    FailureType.RESPOSTA_INCOMPLETA: "Resposta incompleta",
    FailureType.RECUSA_INDEVIDA: "Recusa indevida",
    FailureType.FORMATO_INVALIDO: "Formato inválido",
}


def _esc(value: object) -> str:
    return _html.escape(str(value), quote=True)


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


# Model families this report knows how to name, and who makes them. A model
# outside this list is shown by its identifier, never guessed at.
_FAMILIES = {
    "llama": ("Llama", "Meta"),
    "qwen": ("Qwen", "Alibaba"),
    "mistral": ("Mistral", "Mistral AI"),
    "mixtral": ("Mixtral", "Mistral AI"),
    "gemma": ("Gemma", "Google"),
    "phi": ("Phi", "Microsoft"),
    "deepseek": ("DeepSeek", "DeepSeek"),
    "gpt": ("GPT", "OpenAI"),
    "claude": ("Claude", "Anthropic"),
}
_HOW = {
    "local": "corrido localmente, pelo Ollama",
    "openai": "pela API da OpenAI",
    "anthropic": "pela API da Anthropic",
}


def model_label(model_id: str) -> tuple[str, str]:
    """A readable name and a one-line description for a model identifier.

    "local:llama3.1:8b" reads as ("Llama 3.1", "Meta · 8 mil milhões de
    parâmetros · corrido localmente, pelo Ollama"). The identifier itself is
    always shown next to it, small, so the name never replaces what was
    actually run.
    """
    provider, _, rest = model_id.partition(":")
    if provider not in _HOW and provider != "falso":
        provider, rest = "", model_id
    if provider == "falso":
        return "Fornecedor de teste", "respostas fixas, sem modelo real (ensaio a seco)"
    base, _, tag = rest.partition(":")
    details: list[str] = []
    name = base or model_id
    match = re.match(r"([a-z]+)[-_]?(.*)$", base.lower())
    if match and match.group(1) in _FAMILIES:
        family, maker = _FAMILIES[match.group(1)]
        words: list[str] = []
        for token in match.group(2).replace("-", " ").split():
            if token.isdigit() and words and words[-1].replace(".", "").isdigit():
                words[-1] += "." + token
            else:
                words.append(token.capitalize() if token.isalpha() else token)
        version = " ".join(words)
        name = f"{family}-{version}" if family == "GPT" and version else f"{family} {version}".strip()
        details.append(maker)
    size = re.match(r"(\d+(?:\.\d+)?)b\b", tag.lower())
    if size:
        amount = size.group(1).replace(".", ",")
        details.append(f"{amount} mil milhões de parâmetros")
    elif tag:
        details.append(tag)
    if provider in _HOW:
        details.append(_HOW[provider])
    return name, " · ".join(details)


def _model_heading(model_id: str, tag: str = "h3", css: str = "modelo") -> str:
    name, description = model_label(model_id)
    sub = f'<span class="modelo-desc">{_esc(description)}</span>' if description else ""
    return (
        f'<div class="{css}"><{tag} class="modelo-nome">{_esc(name)}</{tag}>{sub}'
        f'<code class="modelo-id">{_esc(model_id)}</code></div>'
    )


def _model_short(model_id: str) -> str:
    return model_label(model_id)[0]


_EVIDENCE = (
    ("nenhum de: ", "Não encontrou nenhum destes termos: "),
    ("faltou: ", "Faltou: "),
    ("encontrou ", "Encontrou o que não devia aparecer: "),
    ("prescreve ", "Receita o que o caso exclui: "),
    ("nenhum valor em ", "Não indica nenhum valor em "),
    ("esperava ", "Esperava "),
)


def _evidence(text: str) -> str:
    """The grader's evidence as a sentence; the quoted text itself is left as it is."""
    for prefix, sentence in _EVIDENCE:
        if text.startswith(prefix):
            text = sentence + text[len(prefix):]
            break
    return text.replace(" em: ", " no trecho: ")


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


def _risk_chip(failure: FailureType) -> str:
    risk = failure.risk
    return (
        f'<span class="chip {_RISK_CLASS[risk]}"><span class="dot" aria-hidden="true"></span>'
        f'{_esc(_FAILURE_LABEL[failure])}<span class="chip-risco">risco {_RISK_LABEL[risk]}</span></span>'
    )


def _aviso(title: str, body: str) -> str:
    """A notice box; `body` must already be escaped."""
    return (
        '<div class="aviso" role="note"><span class="aviso-icone" aria-hidden="true">!</span>'
        f"<div><strong>{title}</strong> {body}</div></div>"
    )


# ---------------------------------------------------------------- opening


def _intro(cases: list[Case], models: list[str], answers: list[Answer]) -> str:
    samples = max(expected_samples(answers).values(), default=0)
    facts = [
        _plural(len(cases), "caso clínico", "casos clínicos"),
        _plural(len(models), "modelo", "modelos"),
    ]
    if samples:
        facts.append(_plural(samples, "amostra por caso", "amostras por caso"))
    fact_items = "".join(f"<li>{_esc(f)}</li>" for f in facts)
    return f"""
<section class="intro" aria-labelledby="o-que-e">
  <div class="intro-texto">
    <h2 id="o-que-e">O que é isto</h2>
    <p class="lead">O <strong>Aferidor</strong> mede com que frequência um modelo de
    linguagem responde certo a perguntas clínicas em português europeu, e que tipo de
    erro comete quando erra.</p>
    <p>Cada pergunta tem uma resposta de referência com fonte pública (normas da DGS,
    Infarmed, diretrizes europeias) e critérios de aceitação escritos antes do ensaio.
    A mesma pergunta é feita várias vezes a cada modelo, porque um modelo não responde
    sempre igual: cada uma dessas respostas é uma <em>amostra</em>. Cada amostra é
    corrigida de forma automática e determinista, e cada falha é classificada pelo risco
    clínico que carrega. Uma média de respostas certas esconde o que importa; por isso
    este relatório começa pelos erros graves.</p>
    <ul class="factos">{fact_items}</ul>
  </div>
  <ol class="como-ler" aria-label="Como ler este relatório">
    <li><strong>O número grande</strong> é o de casos em que o modelo cometeu, pelo menos
    uma vez, um erro de risco crítico. Um médico só vê uma resposta, por isso basta uma.</li>
    <li><strong>A barra</strong> mostra a consistência: em quantos casos o modelo acertou
    sempre, falhou sempre, ou mudou de resposta entre tentativas.</li>
    <li><strong>Em baixo</strong>, cada caso com falha mostra a pergunta, a referência, o que
    o modelo respondeu e o critério que falhou, para qualquer veredito poder ser contestado.</li>
  </ol>
</section>"""


def _notices(
    cases: list[Case],
    answers: list[Answer],
    missing: list[str] | None,
    reasons: dict[str, str] | None,
    sources_verified: bool,
) -> list[str]:
    out: list[str] = []
    if not sources_verified:
        out.append(_aviso(
            "Aviso.",
            "As fontes deste conjunto de casos ainda não foram todas confirmadas por uma "
            "pessoa. Até isso acontecer, os números abaixo medem o modelo contra valores "
            "transcritos automaticamente. Ver <code>casos/VERIFICACAO.md</code>.",
        ))
    if missing:
        out.append(_aviso(
            "Casos sem resposta.",
            _esc(format_missing(missing, reasons))
            + " Não entram em nenhuma contagem deste relatório.",
        ))
    gaps = missing_samples(cases, answers)
    if gaps:
        out.append(_aviso(
            "Amostras em falta.",
            _esc(format_missing_samples(gaps, expected_samples(answers)))
            + " Não muda nenhuma contagem abaixo; só nomeia o que já era invisível nelas.",
        ))
    return out


# ---------------------------------------------------------------- summary


def _state_bar(model: str, counts: dict[ConsistencyState, int], total: int) -> str:
    segments = []
    legend = []
    for state in _STATE_ORDER:
        n = counts.get(state, 0)
        css, icon = _STATE_STYLE[state]
        legend.append(
            f'<li><span class="swatch {css}" aria-hidden="true"></span>'
            f"{icon} {_esc(state.label)} <strong>{n}</strong></li>"
        )
        if n:
            segments.append(
                f'<span class="seg {css}" style="flex-grow:{n}" '
                f'title="{_esc(state.label)}: {n} de {total} casos"></span>'
            )
    description = ", ".join(f"{counts.get(s, 0)} {s.label}" for s in _STATE_ORDER)
    return (
        f'<div class="barra" role="img" aria-label="{_esc(_model_short(model))}: {_esc(description)}, '
        f'em {total} casos">{"".join(segments)}</div>'
        f'<ul class="legenda-estados">{"".join(legend)}</ul>'
    )


def _model_card(
    model: str,
    summary: ConsistencySummary,
    tally: Tally,
    states: dict[ConsistencyState, int],
    language: LanguageSummary,
    verdict: bool | None,
) -> str:
    badge = ""
    if verdict is not None:
        badge = (
            '<span class="selo aprovado">✓ aprovado pelo protocolo</span>'
            if verdict
            else '<span class="selo reprovado">✕ reprovado pelo protocolo</span>'
        )
    return f"""
<article class="cartao-modelo">
  <header>{_model_heading(model)}{badge}</header>
  <p class="numero-principal"><span class="destaque">{summary.critical_cases}</span><span class="legenda">de {summary.cases} casos com falha crítica em alguma amostra ({_esc(interval_text(summary.critical_cases, summary.cases))})</span></p>
  {_state_bar(model, states, summary.cases)}
  <dl class="metricas">
    <div><dt>Casos instáveis</dt><dd>{summary.unstable_cases} de {summary.cases}</dd></div>
    <div><dt>Respostas certas</dt><dd>{tally.passed} de {tally.total} ({_esc(interval_text(tally.passed, tally.total))})</dd></div>
  </dl>
  <p class="lingua-linha"><strong>Português europeu:</strong> {language.brazilian} de {language.answers} respostas com formas do Brasil, {language.pre_agreement} com grafia anterior ao Acordo.</p>
</article>"""


def _failure_chart(model: str, tally: Tally, top: int) -> str:
    """One model's failures by type, on a scale shared by every model.

    `top` is the largest count across all models, not this model's own: two
    charts side by side on their own scales make 42 look as long as 58.
    """
    rows = tally.worst_first()
    if not rows:
        return (
            f'<div class="falhas-modelo">{_model_heading(model)}'
            "<p>Nenhuma falha registada.</p></div>"
        )
    out = [f'<div class="falhas-modelo">{_model_heading(model)}<ul class="barras-falhas">']
    for failure, n in rows:
        risk = failure.risk
        out.append(
            f'<li><span class="rotulo">{_esc(_FAILURE_LABEL[failure])}'
            f'<span class="sub">risco {_RISK_LABEL[risk]}</span></span>'
            f'<span class="pista"><span class="fill {_RISK_CLASS[risk]}" '
            f'style="flex-basis:calc({n} / {top} * 100%)" '
            f'title="{_esc(_FAILURE_LABEL[failure])}: {n} respostas"></span></span>'
            f'<span class="valor">{n}</span></li>'
        )
    out.append("</ul></div>")
    return "".join(out)


def _risk_legend() -> str:
    items = "".join(
        f'<li><span class="swatch {_RISK_CLASS[r]}" aria-hidden="true"></span>risco {_RISK_LABEL[r]}</li>'
        for r in (Risk.CRITICO, Risk.ALTO, Risk.MEDIO, Risk.BAIXO)
    )
    return f'<ul class="legenda-riscos">{items}</ul>'


# ---------------------------------------------------------------- grid


def _cell(entry: Consistency | None) -> tuple[str, str]:
    if entry is None:
        return "sem-resposta", '<span class="ic" aria-hidden="true">○</span> sem resposta'
    css, icon = _STATE_STYLE[entry.state]
    label = f'<span class="ic" aria-hidden="true">{icon}</span> {_esc(entry.state.label)}'
    if entry.state is ConsistencyState.ESTAVEL_CERTO:
        return css, label
    failure = _esc(_FAILURE_LABEL[entry.worst_failure]) if entry.worst_failure else ""
    detail = (
        f" · {entry.passed} de {entry.samples} certas"
        if entry.state is ConsistencyState.INSTAVEL else ""
    )
    return css, f'{label}<br><span class="cel-falha">{failure}{detail}</span>'


def _grid(
    cases: list[Case], models: list[str], consistency: dict[tuple[str, str], Consistency]
) -> str:
    out = ['<div class="grade-wrap"><table class="grade">']
    out.append(
        '<thead><tr><th scope="col">Caso</th>'
        + "".join(f'<th scope="col">{_model_heading(model, "span", "cabecalho-modelo")}</th>' for model in models)
        + "</tr></thead>"
    )
    out.append("<tbody>")
    for category, group in _grouped_cases(cases):
        out.append(
            f'<tr class="categoria"><td colspan="{len(models) + 1}">{_esc(category)}</td></tr>'
        )
        for case in group:
            out.append(
                f'<tr><th scope="row"><span class="caso-id">{_esc(case.case_id)}</span>'
                f'<span class="caso-pergunta">{_esc(case.question)}</span></th>'
            )
            for model in models:
                css_class, text = _cell(consistency.get((case.case_id, model)))
                out.append(f'<td class="cel {css_class}">{text}</td>')
            out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _grid_legend() -> str:
    items = [
        f'<li><span class="swatch {css}" aria-hidden="true"></span>{icon} {_esc(state.label)}</li>'
        for state, (css, icon) in _STATE_STYLE.items()
    ]
    items.append('<li><span class="swatch sem-resposta" aria-hidden="true"></span>○ sem resposta</li>')
    return f'<ul class="legenda-estados">{"".join(items)}</ul>'


# ---------------------------------------------------------------- detail


def _sample_block(answer: Answer, verdict: Verdict) -> str:
    out = ['<div class="amostra">']
    if verdict.passed:
        out.append(f'<p class="passou">✓ amostra {answer.sample}: passou em todos os critérios</p>')
        out.append(f"<blockquote>{_esc(answer.text)}</blockquote></div>")
        return "".join(out)
    alternative = (
        f" (corrigida contra: {_esc(verdict.alternative)})" if verdict.alternative else ""
    )
    out.append(f'<p class="amostra-numero">✕ amostra {answer.sample}{alternative}</p>')
    out.append(f"<blockquote>{_esc(answer.text)}</blockquote>")
    out.append('<ul class="criterios-falhados">')
    for result in verdict.results:
        if not result.passed:
            out.append(
                f"<li>{_risk_chip(result.criterion.failure)}"
                f'<span class="evidencia">{_esc(_evidence(result.evidence))}</span></li>'
            )
    out.append("</ul></div>")
    return "".join(out)


def _detail(
    cases: list[Case],
    models: list[str],
    consistency: dict[tuple[str, str], Consistency],
    pairs: dict[tuple[str, str], list[tuple[Answer, Verdict]]],
) -> str:
    out = [
        '<section class="detalhe" id="casos-com-falha"><h2>Casos com falha</h2>',
        '<p class="seccao-intro">Cada caso abre para mostrar a pergunta, a resposta de '
        "referência com a fonte, e cada resposta diferente que o modelo deu, com o critério "
        "que falhou e a evidência que o corretor viu. Os círculos à direita dão o estado do "
        f"caso em cada modelo, por esta ordem: {_esc(', '.join(_model_short(m) for m in models))}.</p>",
    ]
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
        minis = []
        for model in models:
            entry = consistency.get((case.case_id, model))
            if entry is None:
                continue
            css, icon = _STATE_STYLE[entry.state]
            minis.append(
                f'<span class="mini {css}" title="{_esc(_model_short(model))}: {_esc(entry.state.label)}">{icon}</span>'
            )
        out.append("<details>")
        out.append(
            f'<summary><span class="caso-id">{_esc(case.case_id)}</span>'
            f'<span class="resumo-pergunta">{_esc(case.question)}</span>'
            f'<span class="minis" aria-hidden="true">{"".join(minis)}</span></summary>'
        )
        out.append('<div class="detalhe-corpo">')
        out.append(f"<p><strong>Pergunta.</strong> {_esc(case.question)}</p>")
        out.append(
            f'<div class="referencia"><p><strong>Resposta de referência.</strong> '
            f"{_esc(case.reference)}</p>"
            f'<p class="fonte"><strong>Fonte.</strong> {_esc(case.source.name)}, '
            f"{_esc(case.source.reference)}</p></div>"
        )
        for model in failing_models:
            entry = consistency[(case.case_id, model)]
            css, icon = _STATE_STYLE[entry.state]
            out.append(
                f'<h4><span class="mini {css}" aria-hidden="true">{icon}</span> {_esc(_model_short(model))} '
                f'<span class="h4-sub">{_esc(entry.state.label)}, {entry.passed} de '
                f"{entry.samples} amostras certas</span></h4>"
            )
            seen: set[str] = set()
            for answer, verdict in pairs.get((case.case_id, model), []):
                if answer.text in seen:
                    continue
                seen.add(answer.text)
                out.append(_sample_block(answer, verdict))
        out.append("</div></details>")
    if not any_case:
        out.append("<p>Nenhum caso com falha.</p>")
    out.append("</section>")
    return "".join(out)


# ---------------------------------------------------------------- style

_STYLE = """
:root {
  color-scheme: light dark;
  --page: #f9f9f7; --surface: #ffffff; --surface-2: #f3f2ee;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #6f6d68;
  --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
  --accent: #1f5fbf;
  --good: #0ca30c; --warning: #fab219; --serious: #ec835a; --critical: #d03b3b; --neutral: #a9a79f;
  --good-bg: rgba(12,163,12,0.12); --warning-bg: rgba(250,178,25,0.18);
  --critical-bg: rgba(208,59,59,0.12); --neutral-bg: rgba(137,135,129,0.14);
  --success-text: #006300;
}
@media (prefers-color-scheme: dark) {
  :root {
    --page: #0d0d0d; --surface: #1a1a19; --surface-2: #232321;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #a4a298;
    --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
    --accent: #7eaaf0; --neutral: #6c6a64;
    --good-bg: rgba(12,163,12,0.20); --warning-bg: rgba(250,178,25,0.16);
    --critical-bg: rgba(208,59,59,0.24); --neutral-bg: rgba(137,135,129,0.18);
    --success-text: #0ca30c;
  }
}
* { box-sizing: border-box; }
html { background: var(--page); scroll-behavior: smooth; }
body {
  margin: 0 auto; max-width: 72rem; padding: 0 1rem 3rem;
  background: var(--page); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.55; font-size: 16px;
}
h1, h2, h3, h4 { line-height: 1.25; margin: 0; }
h2 { font-size: 1.35rem; margin-bottom: 0.75rem; }
h3 { font-size: 1.05rem; }
p { margin: 0 0 0.75rem; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.88em;
  background: var(--surface-2); padding: 0.1rem 0.3rem; border-radius: 4px; }
section { margin-top: 2.5rem; scroll-margin-top: 3.5rem; }
.topo { padding: 2rem 0 1rem; }
.marca { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.topo h1 { font-size: 2rem; margin: 0.25rem 0 0.4rem; }
.subtitulo { color: var(--ink-2); margin: 0; }
.data { color: var(--muted); font-size: 0.9rem; margin: 0.35rem 0 0; }
nav.indice { position: sticky; top: 0; z-index: 2; background: var(--page);
  border-top: 1px solid var(--grid); border-bottom: 1px solid var(--grid); padding: 0.6rem 0; }
nav.indice ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.35rem 1.1rem; }
nav.indice a { color: var(--ink-2); text-decoration: none; font-size: 0.92rem; }
nav.indice a:hover, nav.indice a:focus-visible { color: var(--accent); text-decoration: underline; }
.intro { display: grid; grid-template-columns: 1.4fr 1fr; gap: 1.5rem; margin-top: 1.5rem;
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }
.lead { font-size: 1.12rem; }
.factos { list-style: none; padding: 0; margin: 0.5rem 0 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
.factos li { background: var(--surface-2); border-radius: 999px; padding: 0.2rem 0.75rem; font-size: 0.88rem; color: var(--ink-2); }
.como-ler { margin: 0; padding-left: 1.3rem; color: var(--ink-2); font-size: 0.95rem; }
.como-ler li { margin-bottom: 0.6rem; }
.como-ler strong { color: var(--ink); }
.aviso { display: flex; gap: 0.75rem; align-items: flex-start; margin: 0.75rem 0;
  background: var(--warning-bg); border: 1px solid var(--border); border-radius: 10px; padding: 0.8rem 1rem; }
.aviso-icone { flex: none; width: 1.5rem; height: 1.5rem; border-radius: 50%; background: var(--warning);
  color: #0b0b0b; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }
.seccao-intro { color: var(--ink-2); max-width: 48rem; }
.cartoes { display: grid; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); gap: 1rem; }
.cartao-modelo { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
.cartao-modelo header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 0.5rem; min-height: 6.5rem; }
.modelo-nome { font-size: 1.15rem; font-weight: 650; display: block; }
.modelo-desc { display: block; color: var(--ink-2); font-size: 0.85rem; margin-top: 0.1rem; }
.modelo-id { display: inline-block; margin-top: 0.3rem; font-size: 0.72rem; color: var(--muted); background: none; padding: 0; }
.cabecalho-modelo .modelo-nome { font-size: 0.95rem; }
.cabecalho-modelo .modelo-desc { font-weight: 400; font-size: 0.76rem; }
.selo { font-size: 0.8rem; font-weight: 600; border-radius: 999px; padding: 0.15rem 0.6rem; }
.selo.aprovado { background: var(--good-bg); color: var(--success-text); }
.selo.reprovado { background: var(--critical-bg); color: var(--ink); }
.numero-principal { display: flex; align-items: baseline; gap: 0.6rem; margin: 0.9rem 0 1rem; flex-wrap: wrap; }
.destaque { font-size: 3.2rem; font-weight: 650; line-height: 1; font-variant-numeric: lining-nums; }
.numero-principal .legenda { color: var(--ink-2); font-size: 0.92rem; max-width: 16rem; }
.barra { display: flex; gap: 2px; height: 16px; border-radius: 4px; overflow: hidden; }
.seg { display: block; height: 100%; flex-basis: 0; }
.seg.ok, .swatch.ok { background: var(--good); }
.seg.instavel, .swatch.instavel { background: var(--warning); }
.seg.erro, .swatch.erro { background: var(--critical); }
.swatch.sem-resposta { background: var(--neutral); }
.legenda-estados, .legenda-riscos { list-style: none; padding: 0; margin: 0.6rem 0 0.75rem; display: flex; flex-wrap: wrap; gap: 0.3rem 1rem;
  font-size: 0.85rem; color: var(--ink-2); }
.legenda-estados strong { color: var(--ink); }
.swatch { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 3px; margin-right: 0.35rem; vertical-align: -0.05rem; }
.metricas { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin: 1rem 0 0.75rem; }
.metricas div { background: var(--surface-2); border-radius: 8px; padding: 0.5rem 0.7rem; }
.metricas dt { font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.metricas dd { margin: 0.1rem 0 0; font-weight: 600; font-size: 0.95rem; }
.lingua-linha { font-size: 0.86rem; color: var(--ink-2); margin: 0; }
.protocolo .cartao { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
.protocolo ul { padding-left: 1.2rem; margin-bottom: 0; }
.falhas-grelha { display: grid; grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr)); gap: 1rem; }
.falhas-modelo { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
.falhas-modelo .modelo { margin-bottom: 0.9rem; }
.barras-falhas { list-style: none; margin: 0; padding: 0; }
.barras-falhas li { display: grid; grid-template-columns: 14rem 1fr 2.5rem; align-items: center; gap: 0.6rem; padding: 0.3rem 0; }
.rotulo { font-size: 0.88rem; line-height: 1.25; }
.rotulo .sub { display: block; color: var(--muted); font-size: 0.74rem; }
.pista { height: 14px; border-left: 1px solid var(--grid); display: flex; }
.fill { display: block; height: 14px; border-radius: 0 4px 4px 0; min-width: 3px; }
.valor { font-variant-numeric: tabular-nums; font-weight: 600; font-size: 0.9rem; text-align: right; }
.r-critico { --c: var(--critical); } .r-alto { --c: var(--serious); } .r-medio { --c: var(--warning); } .r-baixo { --c: var(--neutral); }
.fill, .swatch.r-critico, .swatch.r-alto, .swatch.r-medio, .swatch.r-baixo { background: var(--c); }
.grade-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }
table.grade { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
table.grade th, table.grade td { border-bottom: 1px solid var(--grid); padding: 0.55rem 0.75rem; text-align: left; vertical-align: top; }
table.grade thead th { font-size: 0.82rem; color: var(--ink); background: var(--surface); min-width: 12rem; }
table.grade tbody th { font-weight: 400; min-width: 16rem; max-width: 30rem; }
.caso-id { display: block; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; font-weight: 600; }
.caso-pergunta { display: block; color: var(--ink-2); font-size: 0.82rem; line-height: 1.35; margin-top: 0.15rem; }
tr.categoria td { background: var(--surface-2); font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-2); }
td.cel { white-space: nowrap; }
td.cel.ok { background: var(--good-bg); }
td.cel.erro { background: var(--critical-bg); }
td.cel.instavel { background: var(--warning-bg); }
td.cel.sem-resposta { background: var(--neutral-bg); color: var(--ink-2); }
.cel-falha { font-size: 0.8rem; color: var(--ink-2); }
.ic { font-weight: 700; }
td.cel.ok .ic { color: var(--success-text); }
td.cel.erro .ic { color: var(--critical); }
.detalhe details { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; margin: 0.5rem 0; }
.detalhe summary { cursor: pointer; padding: 0.75rem 1rem; display: grid; grid-template-columns: 9rem 1fr auto; gap: 0.75rem; align-items: center; }
.detalhe summary:hover { background: var(--surface-2); border-radius: 10px; }
.resumo-pergunta { color: var(--ink-2); font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.minis { display: inline-flex; gap: 0.25rem; }
.mini { display: inline-flex; align-items: center; justify-content: center; width: 1.35rem; height: 1.35rem; border-radius: 50%;
  font-size: 0.75rem; font-weight: 700; color: #0b0b0b; flex: none; }
.mini.ok { background: var(--good); } .mini.instavel { background: var(--warning); } .mini.erro { background: var(--critical); color: #ffffff; }
.detalhe-corpo { padding: 0.9rem 1rem 1rem; border-top: 1px solid var(--grid); }
.referencia { background: var(--surface-2); border-radius: 8px; padding: 0.75rem 0.9rem; margin: 0.5rem 0 1rem; }
.referencia p { margin: 0 0 0.35rem; } .fonte { color: var(--ink-2); font-size: 0.88rem; }
.detalhe h4 { margin: 1.1rem 0 0.4rem; font-size: 0.98rem; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.h4-sub { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-weight: 400; color: var(--muted); font-size: 0.85rem; }
.amostra { border-left: 3px solid var(--grid); padding-left: 0.9rem; margin: 0.75rem 0; }
.amostra-numero, .passou { font-size: 0.85rem; color: var(--ink-2); margin: 0 0 0.3rem; font-weight: 600; }
.passou { color: var(--success-text); }
blockquote { margin: 0 0 0.5rem; padding: 0.6rem 0.8rem; background: var(--surface-2); border-radius: 6px;
  white-space: pre-wrap; font-size: 0.88rem; max-height: 22rem; overflow: auto; }
.criterios-falhados { list-style: none; padding: 0; margin: 0; }
.criterios-falhados li { margin: 0.35rem 0; }
.chip { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.8rem; font-weight: 600;
  background: var(--surface-2); border-radius: 999px; padding: 0.1rem 0.6rem; margin-right: 0.4rem; }
.chip .dot { width: 0.55rem; height: 0.55rem; border-radius: 50%; background: var(--c); }
.chip-risco { font-weight: 400; color: var(--muted); }
.evidencia { font-size: 0.84rem; color: var(--ink-2); }
.lingua ul { padding-left: 1.2rem; }
.condicoes dl { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem; margin: 0; }
.condicoes dt { font-weight: 600; font-size: 0.9rem; word-break: break-word; }
.condicoes dd { margin: 0.1rem 0 0.8rem; color: var(--ink-2); font-size: 0.9rem; }
footer.rodape { margin-top: 3rem; padding-top: 1.25rem; border-top: 1px solid var(--grid); color: var(--ink-2); font-size: 0.88rem; scroll-margin-top: 3.5rem; }
footer.rodape h2 { font-size: 1rem; color: var(--ink); }
@media (max-width: 46rem) {
  .intro { grid-template-columns: 1fr; }
  .detalhe summary { grid-template-columns: 1fr auto; }
  .resumo-pergunta { display: none; }
  .barras-falhas li { grid-template-columns: 8.5rem 1fr 2rem; }
  .destaque { font-size: 2.6rem; }
  .topo h1 { font-size: 1.6rem; }
  .metricas { grid-template-columns: 1fr; }
}
@media print {
  nav.indice { position: static; }
  details { break-inside: avoid; }
}
"""


# ---------------------------------------------------------------- page


def _protocol_section(
    protocol: Protocol, answers: list[Answer], summaries: dict, cases_source
) -> tuple[str, dict[str, bool]]:
    found_warnings, outcomes = protocol_findings(protocol, answers, summaries, cases_source)
    parts = ['<section class="protocolo" id="criterio"><h2>Critério de aprovação</h2><div class="cartao">']
    parts.append(
        f"<p>Protocolo <strong>{_esc(protocol.name)}</strong>, escrito a "
        f"{_esc(protocol.written_on.isoformat())} (<code>{_esc(protocol.path)}</code>, "
        f"SHA-256 {_esc(protocol.sha256[:12])}).</p>"
    )
    for warning in found_warnings:
        parts.append(_aviso("Aviso.", _esc(warning) + "."))
    parts.append("<ul>")
    for outcome in outcomes:
        result = "aprovado" if outcome.approved else "reprovado"
        details = "; ".join(
            f"{c.label}: {c.observed} ({c.limit}{'' if c.met else ', não cumpre'})"
            for c in outcome.checks
        )
        parts.append(
            f"<li><strong>{_esc(_model_short(outcome.model))}: {result}</strong> "
            f"<code>{_esc(outcome.model)}</code>. {_esc(details)}.</li>"
        )
    parts.append("</ul></div></section>")
    return "".join(parts), {o.model: o.approved for o in outcomes}


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
    """Write the whole report as one self contained HTML file."""
    per_model = tally_by_model(verdicts)
    models = list(per_model)
    written = (today or date.today()).isoformat()

    out: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="pt-PT"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Relatório do Aferidor</title><style>{_STYLE}</style></head><body>",
    ]
    out.append(
        '<header class="topo"><div class="marca">Aferidor · banco de ensaio clínico</div>'
        "<h1>Relatório do Aferidor</h1>"
        '<p class="subtitulo">Respostas clínicas de modelos de linguagem, medidas contra '
        "casos de referência com fonte pública.</p>"
        f'<p class="data">Relatório escrito em {_esc(written)}.</p></header>'
    )

    sections = [("o-que-e", "O que é isto")]
    if models:
        sections.append(("resumo", "Resumo"))
        if protocol is not None:
            sections.append(("criterio", "Critério de aprovação"))
        sections += [
            ("grelha", "Caso a caso"),
            ("falhas", "Falhas por tipo"),
            ("casos-com-falha", "Casos com falha"),
        ]
    sections += [("condicoes", "Condições do ensaio"), ("metodo", "Método")]
    out.append(
        '<nav class="indice" aria-label="Secções"><ul>'
        + "".join(f'<li><a href="#{anchor}">{_esc(label)}</a></li>' for anchor, label in sections)
        + "</ul></nav>"
    )

    out.append(_intro(cases, models, answers))
    out.extend(_notices(cases, answers, missing, reasons, sources_verified))

    if not models:
        out.append('<section id="resumo"><p>Não há vereditos para relatar.</p></section>')
    else:
        consistency = consistency_by_case(cases, answers, verdicts)
        summaries = consistency_by_model(consistency)
        states = states_by_model(consistency)
        pairs = pairs_by_case(cases, answers, verdicts)
        languages = language_by_model(answers)

        protocol_html, approved = ("", {})
        if protocol is not None:
            protocol_html, approved = _protocol_section(protocol, answers, summaries, cases_source)

        out.append('<section id="resumo"><h2>Resumo</h2>')
        out.append(
            '<p class="seccao-intro">Uma falha crítica é um erro de dose, uma interação ou '
            "contraindicação omitida, um encaminhamento urgente omitido, ou um facto inventado. "
            "Os intervalos são de confiança a 95%: com poucos casos, o número real pode estar "
            "longe do observado.</p>"
        )
        out.append('<div class="cartoes">')
        for model in models:
            out.append(
                _model_card(
                    model, summaries[model], per_model[model], states[model],
                    languages[model], approved.get(model),
                )
            )
        out.append("</div></section>")
        out.append(protocol_html)

        out.append('<section id="grelha"><h2>Caso a caso</h2>')
        out.append(
            '<p class="seccao-intro">Cada linha é um caso; cada coluna, um modelo. Estável '
            "certo: acertou em todas as tentativas. Estável errado: falhou em todas. Instável: "
            "a resposta certa dependeu da tentativa. Nas falhas aparece o tipo de falha mais "
            "grave.</p>"
        )
        out.append(_grid_legend())
        out.append(_grid(cases, models, consistency))
        out.append("</section>")

        out.append('<section id="falhas"><h2>Falhas por tipo</h2>')
        out.append(
            '<p class="seccao-intro">Quantas respostas tiveram cada tipo de falha, do risco '
            "mais alto para o mais baixo. Uma resposta pode ter mais do que um tipo.</p>"
        )
        out.append(_risk_legend())
        out.append('<div class="falhas-grelha">')
        top = max((n for tally in per_model.values() for _, n in tally.worst_first()), default=1)
        for model in models:
            out.append(_failure_chart(model, per_model[model], top))
        out.append("</div></section>")

        out.append(
            '<section class="lingua"><h2>Português europeu</h2><ul>'
            + "".join(
                f"<li><strong>{_esc(_model_short(m))}</strong> <code>{_esc(m)}</code>: {_esc(language_line(languages[m]))}</li>"
                for m in models
            )
            + '</ul><p class="seccao-intro">Indicador à parte, por uma lista curta de formas '
            "que o português europeu atual não usa: não entra em nenhuma contagem de falhas, e "
            "conta por baixo.</p></section>"
        )
        out.append(_detail(cases, models, consistency, pairs))

    rows = conditions_rows(answers, cases_source)
    out.append('<section class="condicoes" id="condicoes"><h2>Condições do ensaio</h2>')
    if rows:
        out.append("<dl>")
        for label, value in rows:
            shown = label if label == "Banco de casos" else f"{_model_short(label)} ({label})"
            out.append(f"<dt>{_esc(shown)}</dt><dd>{_esc(value)}</dd>")
        out.append("</dl>")
    else:
        out.append("<p>Sem respostas registadas.</p>")
    out.append("</section>")

    out.append(
        '<footer class="rodape" id="metodo"><h2>Método</h2>'
        f"<p>{_esc(HEADER_NOTE)}</p>"
        "<p>A correção é textual e determinista: cada critério procura termos e valores na "
        "resposta, e o mesmo texto dá sempre o mesmo veredito. O próprio corretor é ensaiado "
        "nos dois sentidos: a resposta de referência de cada caso tem de passar, e uma resposta "
        "errada construída para cada critério tem de falhar. O modelo nunca vê a resposta de "
        "referência nem os critérios.</p>"
        "<p>O método completo, os limites conhecidos e a confirmação das fontes estão no "
        "repositório do Aferidor, em <code>docs/METODO.md</code> e "
        "<code>casos/VERIFICACAO.md</code>.</p></footer>"
    )
    out.append("</body></html>")
    return "".join(out)


__all__ = ["build", "model_label"]
