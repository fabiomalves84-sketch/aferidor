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
icon and a written label: a state is never shown by colour alone. The page
follows the system's light or dark setting, and a switch in the header
changes it; the switch is CSS alone, so the no-script promise holds.
"""

from __future__ import annotations

import contextvars
import html as _html
import re
from datetime import date

from .grading import (
    CASE_RULES,
    DEFAULT_CASE_RULE,
    Consistency,
    ConsistencyState,
    ConsistencySummary,
    Tally,
    compare_critical,
    consistency_by_case,
    consistency_by_model,
    critical_by_category,
    expected_samples,
    missing_samples,
    pairs_by_case,
    right_cases_by_model,
    states_by_model,
    tally_by_model,
    wilson_interval,
    worst_examples,
)
from .lingua import LanguageSummary, language_by_model, language_line
from .models import Answer, Case, Verdict
from .protocolo import Protocol
from .report import (
    HEADER_NOTE,
    conditions_rows,
    format_missing,
    format_missing_samples,
    in_bank,
    interval_text,
    protocol_findings,
)
from .risk import FailureType, Risk
from .traducao import HTML_LANG, NAMES, decimal, t as _translate

# The language the page being built is written in. Set by `build`, read by
# every helper through `_t`, so the helpers keep their signatures.
_LANG: contextvars.ContextVar[str] = contextvars.ContextVar("lingua", default="pt")


def _t(text: str, **values: object) -> str:
    """Interface text in the language of the page being built."""
    return _translate(text, _LANG.get(), **values)

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
    return f"{n} {_t(one) if n == 1 else _t(many)}"


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
    "gemini": ("Gemini", "Google"),
}
_HOW = {
    "local": "executado localmente através do Ollama",
    "gemini": "acedido por API",
    "openai": "acedido por API",
    "anthropic": "acedido por API",
}


def model_label(model_id: str) -> tuple[str, str]:
    """A readable name and a one-line description for a model identifier.

    "local:llama3.1:8b" reads as ("Llama 3.1", "Meta · 8 mil milhões de
    parâmetros · executado localmente através do Ollama"). The identifier itself is
    always shown next to it, small, so the name never replaces what was
    actually run.
    """
    provider, _, rest = model_id.partition(":")
    if provider not in _HOW and provider != "falso":
        provider, rest = "", model_id
    if provider == "falso":
        return _t("Fornecedor de teste"), _t("respostas fixas, sem modelo real")
    base, _, tag = rest.partition(":")
    details: list[str] = []
    name = base or model_id
    match = re.match(r"([a-z]+)[-_]?(.*)$", base.lower())
    if match and match.group(1) in _FAMILIES:
        family, maker = _FAMILIES[match.group(1)]
        words: list[str] = []
        for token in match.group(2).replace("-", " ").split():
            if re.fullmatch(r"20\d{6}", token) or token == "it":
                continue  # a release date or the "instruction tuned" suffix is not part of the name
            if re.fullmatch(r"\d+(?:\.\d+)?b", token) and not tag:
                tag = token  # "gemma-4-31b-it": the size is in the name, not after a colon
                continue
            if token.isdigit() and words and words[-1].replace(".", "").isdigit():
                words[-1] += "." + token
            else:
                words.append(token.capitalize() if token.isalpha() else token)
        version = " ".join(words)
        name = f"{family}-{version}" if family == "GPT" and version else f"{family} {version}".strip()
        details.append(maker)
    size = re.match(r"(\d+(?:\.\d+)?)b\b", tag.lower())
    if size:
        details.append(_t("{n} mil milhões de parâmetros", n=decimal(size.group(1), _LANG.get())))
    elif tag:
        details.append(tag)
    if provider in _HOW:
        details.append(_t(_HOW[provider]))
    return name, " · ".join(details)


def _model_heading(model_id: str, tag: str = "h3", css: str = "modelo", show_id: bool = True) -> str:
    _, description = model_label(model_id)
    name = _model_short(model_id)
    sub = (
        f'<span class="modelo-desc">{_gloss(_esc(description), ("Ollama", "parâmetros"))}</span>'
        if description else ""
    )
    return (
        f'<div class="{css}"><{tag} class="modelo-nome">{_esc(name)}</{tag}>{sub}'
        + (f'<code class="modelo-id">{_esc(model_id)}</code>' if show_id else "")
        + "</div>"
    )


# Short names of the models on the page being built, made unique by `build`.
_SHORT: contextvars.ContextVar[dict[str, str]] = contextvars.ContextVar("nomes", default={})


def _model_short(model_id: str) -> str:
    return _SHORT.get().get(model_id) or model_label(model_id)[0]


def unique_names(models: list[str]) -> dict[str, str]:
    """A readable name per model, with the tag added where two would read the same.

    "local:llama3.1:8b" and "local:llama3.1:70b" both read "Llama 3.1"; side by
    side they become "Llama 3.1 (8b)" and "Llama 3.1 (70b)".
    """
    names = {m: model_label(m)[0] for m in models}
    taken: dict[str, int] = {}
    for name in names.values():
        taken[name] = taken.get(name, 0) + 1
    return {
        m: f"{name} ({m.rsplit(':', 1)[-1] if m.count(':') > 1 else m})" if taken[name] > 1 else name
        for m, name in names.items()
    }


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
            text = _t(sentence) + text[len(prefix):]
            break
    return text.replace(" em: ", _t(" no trecho: "))


_CATEGORY_LABEL = {
    "dose": "Dose",
    "alergia": "Alergia",
    "duracao": "Duração do tratamento",
    "esquema": "Esquema de tratamento",
    "criterio": "Critério de tratamento",
    "pediatria": "Pediatria",
    "interacao": "Interações",
    "formato": "Formato pedido",
    "ajuste": "Ajuste de dose",
    "gravidez": "Gravidez",
}


def _category(name: str) -> str:
    return _t(_CATEGORY_LABEL[name]) if name in _CATEGORY_LABEL else name[:1].upper() + name[1:]


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


# Terms a reader may not know, with a one-line definition. The report marks
# them where they appear (a dotted underline; the definition shows on hover,
# on keyboard focus and on tap), and lists the ones used at the end. Model
# answers are never marked: they are evidence and stay exactly as they came.
GLOSSARY: dict[str, str] = {
    "DGS": "Direção-Geral da Saúde. Publica as normas de orientação clínica em Portugal.",
    "Infarmed": "Autoridade Nacional do Medicamento e Produtos de Saúde.",
    "RCM": "Resumo das Características do Medicamento: o documento oficial de cada medicamento, com doses, contraindicações e interações.",
    "APMGF": "Associação Portuguesa de Medicina Geral e Familiar, autora do Guia de Bolso de Antibioterapia em Ambulatório.",
    "EMA": "Agência Europeia de Medicamentos.",
    "FDA": "Agência do medicamento dos Estados Unidos.",
    "ESC": "Sociedade Europeia de Cardiologia, autora de diretrizes clínicas.",
    "ADA": "Associação Americana de Diabetes, autora dos Standards of Care.",
    "NICE": "Instituto britânico que publica diretrizes clínicas.",
    "SNS": "Serviço Nacional de Saúde.",
    "PNV": "Programa Nacional de Vacinação.",
    "DPOC": "Doença pulmonar obstrutiva crónica.",
    "TFG": "Taxa de filtração glomerular: mede a função dos rins.",
    "AVC": "Acidente vascular cerebral.",
    "HbA1c": "Hemoglobina glicada: reflete a média da glicemia nos últimos dois a três meses.",
    "INR": "Medida da coagulação do sangue, usada para ajustar a dose de varfarina.",
    "IECA": "Inibidor da enzima de conversão da angiotensina: uma classe de anti-hipertensores.",
    "ECA": "Enzima de conversão da angiotensina.",
    "ARA II": "Antagonista dos recetores da angiotensina II: uma classe de anti-hipertensores.",
    "DOAC": "Anticoagulante oral direto (apixabano, rivaroxabano, edoxabano, dabigatrano).",
    "TSN": "Terapêutica de substituição de nicotina: adesivos, pastilhas, gomas ou spray.",
    "SGLT2": "Inibidores do SGLT2: uma classe de antidiabéticos orais (por exemplo, dapagliflozina).",
    "CYP3A4": "Enzima do fígado que elimina muitos medicamentos; bloqueá-la faz subir os níveis de outros.",
    "MAPA": "Monitorização ambulatória da pressão arterial, durante 24 horas.",
    "AMPA": "Automedição da pressão arterial, no domicílio.",
    "TA": "Tensão arterial.",
    "IM": "Via intramuscular.",
    "IV": "Via intravenosa.",
    "SCORE2": "Instrumento europeu que estima o risco cardiovascular a 10 anos.",
    "SCORE": "Versão anterior do SCORE2, usada pela norma da DGS de 2013.",
    "IC 95%": "Intervalo de confiança a 95%: a faixa onde o valor real provavelmente está. Com poucos casos, é larga.",
    "SHA-256": "Impressão digital de um ficheiro: muda se o ficheiro mudar uma única vírgula. Serve para provar que nada foi alterado.",
    "Ollama": "Programa que corre modelos de linguagem abertos no próprio computador, sem enviar nada para fora.",
    "parâmetros": "Medida do tamanho de um modelo de linguagem. Mais parâmetros costuma querer dizer mais capacidade.",
    "tokens_max": "Limite de tamanho da resposta que o modelo podia dar.",
    "Acordo Ortográfico": "O Acordo Ortográfico de 1990, em vigor em Portugal: escreve-se infeção e não infecção.",
    "amostra": "Uma das respostas do modelo à mesma pergunta. Cada caso é perguntado várias vezes, porque o modelo não responde sempre igual.",
    "sempre correto": "Todas as amostras do caso cumpriram todos os critérios.",
    "parcialmente correto": "Parte das amostras cumpriu os critérios e parte não: o resultado dependeu da tentativa.",
    "nunca correto": "Nenhuma amostra cumpriu os critérios. Não implica falha crítica: a falha pode ser apenas uma resposta incompleta.",
    "falha crítica": "Erro de dose, interação ou contraindicação omitida, encaminhamento urgente omitido, ou facto inventado.",
    "respostas corretas": "Contagem de respostas (casos × amostras), não de casos. Uma taxa alta pode ocultar casos nunca corretos.",
    "casos corretos": "Veredicto binário por caso, segundo a regra indicada no relatório. Por omissão, um caso é correto apenas se todas as amostras forem corretas.",
}
# The report's own vocabulary: marked where the report uses it, never in case texts.
_REPORT_TERMS = (
    "amostra", "sempre correto", "parcialmente correto", "nunca correto", "falha crítica",
    "casos corretos", "respostas corretas",
)
# Clinical and source abbreviations marked automatically in case texts.
_CASE_TERMS = tuple(
    k for k in GLOSSARY
    if k not in ("IC 95%", "SHA-256", "Ollama", "parâmetros", "tokens_max", "Acordo Ortográfico")
    + _REPORT_TERMS
)


# The parts a case code is made of: area, then topic, then a number.
# "ATB-PAC-001" reads as antibiotic therapy, community-acquired pneumonia, case 1.
_CODE_PARTS = {
    "ATB": "Antibioterapia", "COV": "COVID-19", "INT": "Interação medicamentosa",
    "FMT": "Formato de resposta imposto", "AJU": "Ajuste de dose", "PED": "Pediatria",
    "GRA": "Gravidez", "DOS": "Dose", "ADU": "Adulto", "TAB": "Cessação tabágica",
    "PAC": "Pneumonia adquirida na comunidade", "DPOC": "Doença pulmonar obstrutiva crónica",
    "CIST": "Cistite", "FAR": "Faringite", "PIEL": "Pielonefrite", "HP": "Helicobacter pylori",
    "DEX": "Dexametasona", "TOC": "Tocilizumab", "JAN": "Janela para iniciar o antivírico",
    "CLA": "Claritromicina", "COL": "Colquicina", "MET": "Metformina",
    "OMA": "Otite média aguda", "IECA": "Inibidor da enzima de conversão da angiotensina",
    "VPA": "Valproato", "APX": "Apixabano", "MTX": "Metotrexato",
    "HTA": "Hipertensão arterial", "DM": "Diabetes", "CV": "Risco cardiovascular",
    "FA": "Fibrilhação auricular", "AVC": "Acidente vascular cerebral",
}
_CODE_ENTRY = "Código do caso"
GLOSSARY[_CODE_ENTRY] = (
    "Cada caso tem um código com a área, o tema e o número: ATB-PAC-001 é antibioterapia, "
    "pneumonia adquirida na comunidade, caso n.º 1. Passe o rato por cima de um código para o ler."
)


def case_code_meaning(case_id: str) -> str:
    """A case code spelled out; a part this report does not know is left as it is."""
    words = []
    for part in case_id.split("-"):
        if part.isdigit():
            words.append(_t("caso n.º {n}", n=int(part)))
        else:
            words.append(_t(_CODE_PARTS[part]) if part in _CODE_PARTS else part)
    return " · ".join(words)


def _case_code(case_id: str, side: bool = False) -> str:
    """A case code that spells itself out on hover, focus and tap."""
    css = "termo caso-cod lado" if side else "termo caso-cod"
    meaning = case_code_meaning(case_id)
    return (
        f'<abbr class="{css}" tabindex="0" data-def="{_esc(meaning)}" '
        f'aria-label="{_esc(case_id)}: {_esc(meaning)}">{_esc(case_id)}</abbr>'
    )


def _slug(term: str) -> str:
    return "g-" + re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")


def _term(term: str, shown: str | None = None) -> str:
    """One glossary term, marked for hover, focus and tap.

    `term` is the glossary key, always the Portuguese form; what the reader
    sees is `shown`, or the key in the page's language.
    """
    return (
        f'<abbr class="termo" tabindex="0" data-termo="{_esc(term)}" '
        f'data-def="{_esc(_t(GLOSSARY[term]))}" aria-describedby="{_slug(term)}">'
        f"{_esc(shown or _t(term))}</abbr>"
    )


def _gloss(escaped: str, terms: tuple[str, ...] = _CASE_TERMS) -> str:
    """Mark glossary terms in text that is already escaped.

    One pass with every term in the alternation, longest first, so "ARA II"
    wins over a shorter term and nothing inserted is scanned again. Terms
    match whole words and case exactly: "MAPA" is the blood pressure
    monitoring, "mapa" is just a map.
    """
    shown = {_esc(_t(term)): term for term in terms}
    ordered = sorted(shown, key=len, reverse=True)
    pattern = re.compile(
        r"(?<![\w-])(" + "|".join(re.escape(s) for s in ordered) + r")(?![\w-])"
    )
    return pattern.sub(lambda m: _term(shown[m.group(1)]), escaped)


def _glossary_section(page: str) -> str:
    """The glossary, listing only the terms the page actually marks."""
    found = set(re.findall(r'data-termo="([^"]+)"', page))
    if 'class="termo caso-cod' in page:
        found.add(_CODE_ENTRY)
    keys = [_html.unescape(term) for term in found]
    used = sorted(keys, key=lambda k: _t(k).casefold())
    if not used:
        return ""
    items = "".join(
        f'<div><dt id="{_slug(key)}">{_esc(_t(key))}</dt>'
        f"<dd>{_esc(_t(GLOSSARY[key]))}</dd></div>"
        for key in used
    )
    return (
        f'<div class="glossario" id="glossario"><h3>{_t("Glossário")}</h3>'
        f"<dl>{items}</dl></div>"
    )


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
        f'{_esc(_t(_FAILURE_LABEL[failure]))}<span class="chip-risco">{_esc(_risk_text(risk))}</span></span>'
    )


def _risk_text(risk: Risk) -> str:
    return _t("risco " + _RISK_LABEL[risk])


def _interval(successes: int, total: int) -> str:
    """The 95% Wilson interval, in the page's language, glossary term marked."""
    low, high = wilson_interval(successes, total)
    text = _t("IC 95% {low} a {high}", low=_pct(low), high=_pct(high))
    return _gloss(_esc(text), ("IC 95%",))


def _aviso(title: str, body: str) -> str:
    """A notice box; `body` must already be escaped."""
    return (
        '<div class="aviso" role="note"><span class="aviso-icone" aria-hidden="true">!</span>'
        f"<div><strong>{title}</strong> {body}</div></div>"
    )


# ---------------------------------------------------------------- opening


def _intro(cases: list[Case], models: list[str], answers: list[Answer], how_counted: str) -> str:
    samples = max(expected_samples(answers).values(), default=0)
    facts = [
        _plural(len(cases), "caso clínico", "casos clínicos"),
        _plural(len(models), "modelo", "modelos"),
    ]
    if samples:
        facts.append(_plural(samples, "amostra por caso", "amostras por caso"))
    fact_items = "".join(f"<li>{_esc(f)}</li>" for f in facts)
    reading = _t(
        "<li><strong>O valor em destaque</strong> indica os casos com pelo menos uma "
        "{falha}. Na prática clínica é observada uma única resposta; uma falha crítica é "
        "suficiente.</li><li><strong>A barra de estados</strong> indica a consistência de "
        "cada modelo: casos {sempre}, {parcial} e {nunca}.</li><li><strong>A secção Casos "
        "com falha</strong> apresenta, para cada caso, a pergunta, a referência, a resposta "
        "do modelo e o critério não cumprido, para que cada veredicto possa ser verificado.</li>",
        falha=_term("falha crítica"),
        sempre=_term("sempre correto", _t("sempre corretos")),
        parcial=_term("parcialmente correto", _t("parcialmente corretos")),
        nunca=_term("nunca correto", _t("nunca corretos")),
    )
    return f"""
<section class="intro" aria-labelledby="sobre">
  <h2 id="sobre" class="vh">{_t("Sobre este relatório")}</h2>
  <p class="lead">{_t("O <strong>Aferidor</strong> avalia a exatidão de modelos de linguagem em perguntas clínicas em português europeu e classifica os erros pelo risco clínico.")}</p>
  <p class="triagem">{_t("Os veredictos são a triagem automática do corretor; a validação por um especialista faz-se à parte, numa folha cega ({comando}).", comando="<code>aferidor revisao</code>")}</p>
  <ul class="factos">{fact_items}</ul>
  <details class="recolhe ler">
    <summary>{_t("Como interpretar este relatório")}</summary>
    <p>{_t("Cada pergunta tem uma resposta de referência com fonte pública (normas da {dgs}, {infarmed}, diretrizes europeias) e critérios de aceitação definidos antes do ensaio. Cada pergunta é colocada várias vezes a cada modelo, uma vez que as respostas variam; cada resposta constitui uma {amostra}. A correção é automática e determinista. Como a média de respostas corretas oculta os erros relevantes, o relatório apresenta primeiro as falhas críticas.", dgs=_term("DGS"), infarmed=_term("Infarmed"), amostra=_term("amostra"))}</p>
    <ol class="como-ler">{reading}</ol>
    {how_counted}
  </details>
</section>"""


def _notices(
    cases: list[Case],
    answers: list[Answer],
    missing: list[str] | None,
    reasons: dict[str, str] | None,
    sources_verified: bool,
) -> list[str]:
    out: list[str] = []
    if _LANG.get() != "pt":
        out.append(_aviso(
            _t("Língua dos casos."),
            _t("As perguntas, as respostas de referência e as respostas dos modelos são "
               "apresentadas no original, em português europeu: são o objeto da avaliação."),
        ))
    if not sources_verified:
        out.append(_aviso(
            _t("Aviso."),
            _t("Nem todas as fontes destes casos foram confirmadas por uma pessoa. Até essa "
               "confirmação, os resultados medem o modelo contra valores transcritos "
               "automaticamente. Ver {ficheiro}.", ficheiro="<code>casos/VERIFICACAO.md</code>"),
        ))
    if missing:
        out.append(_aviso(
            _t("Casos sem resposta."),
            _esc(format_missing(missing, reasons))
            + " " + _t("Não entram em nenhuma contagem deste relatório."),
        ))
    gaps = missing_samples(cases, answers)
    if gaps:
        out.append(_aviso(
            _t("Amostras em falta."),
            _esc(format_missing_samples(gaps, expected_samples(answers), _LANG.get()))
            + " " + _t("Não muda nenhuma contagem abaixo; só nomeia o que já era invisível nelas."),
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
            f"{icon} {_term(state.label)} <strong>{n}</strong></li>"
        )
        if n:
            segments.append(
                f'<span class="seg {css}" style="flex-grow:{n}" '
                f'title="{_esc(_t(state.label))}: {_esc(_t("{n} de {total} casos", n=n, total=total))}"></span>'
            )
    description = ", ".join(f"{counts.get(s, 0)} {_t(s.label)}" for s in _STATE_ORDER)
    return (
        f'<div class="barra" role="img" aria-label="{_esc(_model_short(model))}: {_esc(description)}, '
        f'{_esc(_t("em {total} casos", total=total))}">{"".join(segments)}</div>'
        f'<ul class="legenda-estados">{"".join(legend)}</ul>'
    )


def _dots(pairs: list[tuple[Answer, Verdict]], expected: int) -> str:
    """One dot per sample, in sample order: passed, failed, or never answered.

    The shape carries the result, not only the colour: a filled dot passed, a
    cross failed, an empty ring was never answered.
    """
    by_sample = {answer.sample: verdict.passed for answer, verdict in pairs}
    marks, words = [], []
    for n in range(1, max(expected, max(by_sample, default=0)) + 1):
        if n not in by_sample:
            marks.append('<span class="pt falta">○</span>')
            words.append(_t("{n} sem resposta", n=n))
        elif by_sample[n]:
            marks.append('<span class="pt certa">●</span>')
            words.append(_t("{n} correta", n=n))
        else:
            marks.append('<span class="pt errada">✕</span>')
            words.append(_t("{n} incorreta", n=n))
    label = _esc(_t("Amostras: {lista}", lista=", ".join(words)))
    return f'<span class="pontos" role="img" aria-label="{label}" title="{label}">{"".join(marks)}</span>'


def _how_counted(samples: int, rule: str) -> str:
    """The report's vocabulary, each state shown with an example row of dots."""
    n = max(samples, 1)

    def row(pattern: str) -> str:
        return "".join(
            f'<span class="pt {"certa" if c == "●" else "errada"}">{c}</span>' for c in pattern
        )
    half = max(1, n // 2)
    patterns = [
        ("ok", "✓", "sempre correto", "●" * n, "todas as amostras corretas"),
        ("instavel", "◐", "parcialmente correto", ("●" * (n - half) + "✕" * half) if n > 1 else "●",
         "algumas amostras corretas"),
        ("erro", "✕", "nunca correto", "✕" * n, "nenhuma amostra correta"),
    ]
    items = "".join(
        f'<li><span class="pontos" aria-hidden="true">{row(pattern)}</span>'
        f'<span class="swatch {css}" aria-hidden="true"></span>{icon} {_term(name)}: {_esc(_t(meaning))}</li>'
        # With one sample a case cannot be partly right, so that state is left out.
        for css, icon, name, pattern, meaning in (patterns if n > 1 else patterns[::2])
    )
    times = _plural(n, "vez", "vezes")
    return f"""
<div class="como-se-conta" id="como-se-conta">
  <h3>{_t("Método de contagem")}</h3>
  <p>{_t("Cada caso foi colocado {vezes} a cada modelo; cada resposta é uma {amostra}. Na grelha, cada ponto representa uma amostra, pela ordem de execução: {certa} correta, {errada} incorreta, {falta} sem resposta.", vezes=_esc(times), amostra=_term("amostra"), certa='<span class="pt certa">●</span>', errada='<span class="pt errada">✕</span>', falta='<span class="pt falta">○</span>')}</p>
  <ul>{items}</ul>
  <p>{_t("{casos}: veredicto binário por caso. Regra deste relatório: um caso é correto quando {regra}.", casos="<strong>" + _term("casos corretos", _t("Casos corretos")) + "</strong>", regra=_esc(_t(CASE_RULES[rule])))}</p>
  <p>{_t("<strong>Um caso nunca correto não tem necessariamente uma {falha}</strong>, e um caso parcialmente correto pode ter uma. Por esse motivo, as falhas críticas são contadas à parte.", falha=_term("falha crítica"))}</p>
</div>"""


def _model_card(
    model: str,
    summary: ConsistencySummary,
    tally: Tally,
    states: dict[ConsistencyState, int],
    verdict: bool | None,
    right: tuple[int, int],
) -> str:
    badge = ""
    if verdict is not None:
        badge = (
            f'<span class="selo aprovado">✓ {_t("aprovado pelo protocolo")}</span>'
            if verdict
            else f'<span class="selo reprovado">✕ {_t("reprovado pelo protocolo")}</span>'
        )
    legend = _t(
        "de {total} casos com {falha} em alguma amostra ({ic})",
        total=summary.cases, falha=_term("falha crítica"),
        ic=_interval(summary.critical_cases, summary.cases),
    )
    line = _t(
        "{casos}: <strong>{a} de {b}</strong> · {respostas}: <strong>{c} de {d}</strong>",
        casos=_term("casos corretos", _t("Casos corretos")), a=right[0], b=right[1],
        respostas=_term("respostas corretas", _t("Respostas corretas")),
        c=tally.passed, d=tally.total,
    )
    return f"""
<article class="cartao-modelo">
  <header>{_model_heading(model, show_id=False)}{badge}</header>
  <p class="numero-principal"><span class="destaque">{summary.critical_cases}</span><span class="legenda">{legend}</span></p>
  {_state_bar(model, states, summary.cases)}
  <p class="card-linha">{line}</p>
</article>"""


def _context_note(models: list[str]) -> str:
    """Say plainly when the models measured are small local ones.

    A reader who sees 22 critical cases out of 27 without knowing the models
    are 8-billion-parameter models on a laptop may blame the bench. This
    states what they are; it does not interpret the results.
    """
    local = [m for m in models if m.startswith("local:")]
    if not local:
        return ""
    shorts = [_model_short(m) for m in local]
    names = shorts[0] if len(shorts) == 1 else ", ".join(shorts[:-1]) + _t(" e ") + shorts[-1]
    sentence = _t(
        "{nomes} foi executado localmente, num computador portátil, através do Ollama. São "
        "modelos abertos de pequena dimensão; os resultados não são extrapoláveis para os "
        "modelos comerciais disponibilizados por API." if len(local) == 1 else
        "{nomes} foram executados localmente, num computador portátil, através do Ollama. São "
        "modelos abertos de pequena dimensão; os resultados não são extrapoláveis para os "
        "modelos comerciais disponibilizados por API.",
        nomes=_esc(names),
    )
    return f'<p class="contexto"><strong>{_t("Contexto.")}</strong> {sentence}</p>'


def _p_value(p: float) -> str:
    """A p-value as a reader expects it, in the page's decimal notation."""
    shown = "< 0.001" if p < 0.001 else f"= {p:.3f}"
    return "p " + decimal(shown, _LANG.get())


def _comparison(summaries: dict[str, ConsistencySummary], consistency=None) -> str:
    """Which model had the fewest critical cases, and whether that could be chance.

    With the cases known, the two best models are compared on the cases both
    answered, with the exact McNemar test: they answered the same questions,
    so the comparison is paired, which two separate intervals cannot see.
    """
    result = compare_critical(summaries, consistency)
    if len(result.rows) < 2:
        return ""
    best, second = result.rows[0], result.rows[1]
    if best[1] * second[2] == second[1] * best[2]:
        sentence = _t(
            "{a} e {b} tiveram a mesma proporção de casos com falha crítica.",
            a=_esc(_model_short(best[0])), b=_esc(_model_short(second[0])),
        )
    else:
        values = dict(
            melhor=f"<strong>{_esc(_model_short(best[0]))}</strong>", a=best[1], n=best[2],
            b=second[1], m=second[2], outro=_esc(_model_short(second[0])),
        )
        if result.p_value is not None:
            sentence = _t(
                "{melhor} teve menos casos com falha crítica ({a} de {n}, contra {b} de {m} de "
                "{outro}). Nos casos em que só um dos dois teve falha crítica ({x} contra {y}), a "
                "diferença é estatisticamente significativa (teste de McNemar exato, {p})."
                if result.p_value < 0.05 else
                "{melhor} teve menos casos com falha crítica ({a} de {n}, contra {b} de {m} de "
                "{outro}). Nos casos em que só um dos dois teve falha crítica ({x} contra {y}), a "
                "diferença pode dever-se ao acaso (teste de McNemar exato, {p}).",
                x=result.only_first, y=result.only_second, p=_p_value(result.p_value), **values,
            )
        else:
            sentence = _t(
                "{melhor} teve menos casos com falha crítica ({a} de {n}, contra {b} de {m} de "
                "{outro}), mas os intervalos de confiança sobrepõem-se: com {n} casos, a diferença "
                "pode dever-se ao acaso."
                if result.overlap else
                "{melhor} teve menos casos com falha crítica ({a} de {n}, contra {b} de {m} de "
                "{outro}), e os intervalos de confiança não se sobrepõem.",
                **values,
            )
    rows = []
    for model, critical, cases_n, low, high in result.rows:
        share = critical / cases_n
        label = _t(
            "{modelo}: {a} de {n} casos com falha crítica, intervalo de {low} a {high}",
            modelo=_model_short(model), a=critical, n=cases_n, low=_pct(low), high=_pct(high),
        )
        rows.append(
            f'<li><span class="comp-nome">{_esc(_model_short(model))}</span>'
            f'<span class="comp-pista" role="img" aria-label="{_esc(label)}">'
            f'<span class="comp-ic" style="left:{low * 100:.2f}%;width:{(high - low) * 100:.2f}%"></span>'
            f'<span class="comp-ponto" style="left:{share * 100:.2f}%"></span></span>'
            f'<span class="comp-valor">{_esc(_t("{a} de {n}", a=critical, n=cases_n))} · {_pct(share)}</span></li>'
        )
    ticks = "".join(f'<span style="left:{v}%">{v}%</span>' for v in (0, 25, 50, 75, 100))
    note = _t(
        "Percentagem de casos com falha crítica em alguma amostra. O ponto é o observado; a "
        "linha, o intervalo de confiança a 95%."
    )
    return (
        f'<div class="comparacao"><p class="comp-frase">{sentence}</p>'
        f'<ul class="comp-lista">{"".join(rows)}</ul>'
        f'<div class="comp-eixo" aria-hidden="true"><span></span><span class="comp-ticks">{ticks}</span><span></span></div>'
        f'<p class="comp-nota">{note}</p></div>'
    )


def _failure_chart(model: str, tally: Tally, top: int) -> str:
    """One model's failures by type, on a scale shared by every model.

    `top` is the largest count across all models, not this model's own: two
    charts side by side on their own scales make 42 look as long as 58.
    """
    rows = tally.worst_first()
    if not rows:
        return (
            f'<div class="falhas-modelo">{_model_heading(model)}'
            f"<p>{_t('Nenhuma falha registada.')}</p></div>"
        )
    out = [f'<div class="falhas-modelo">{_model_heading(model)}<ul class="barras-falhas">']
    for failure, n in rows:
        risk = failure.risk
        name = _esc(_t(_FAILURE_LABEL[failure]))
        out.append(
            f'<li><span class="rotulo">{name}'
            f'<span class="sub">{_esc(_risk_text(risk))}</span></span>'
            f'<span class="pista"><span class="fill {_RISK_CLASS[risk]}" '
            f'style="flex-basis:calc({n} / {top} * 100%)" '
            f'title="{name}: {_esc(_t("{n} respostas", n=n))}"></span></span>'
            f'<span class="valor">{n}</span></li>'
        )
    out.append("</ul></div>")
    return "".join(out)


def _risk_legend() -> str:
    items = "".join(
        f'<li><span class="swatch {_RISK_CLASS[r]}" aria-hidden="true"></span>{_esc(_risk_text(r))}</li>'
        for r in (Risk.CRITICO, Risk.ALTO, Risk.MEDIO, Risk.BAIXO)
    )
    return f'<ul class="legenda-riscos">{items}</ul>'


def _plain(text: str) -> str:
    """A model answer with its Markdown marks taken out, for a short excerpt.

    Only for the excerpt in the gravest-mistakes cards: in the full case the
    answer is shown exactly as it came, because there it is the evidence.
    """
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text.strip(), flags=re.M)
    text = text.replace("**", "").replace("__", "")
    return re.sub(r"\n{3,}", "\n\n", text)


def _worst(cases, consistency, pairs) -> str:
    examples = worst_examples(cases, consistency, pairs)
    if not examples:
        return ""
    out = [
        f'<section id="erros"><h2>{_t("Erros mais graves")}</h2>',
        '<p class="seccao-intro">'
        + _t("Casos em que todas as amostras falharam, com pelo menos uma falha de risco "
             "crítico. Selecionados por regra fixa: os primeiros casos que a cumprem, "
             "alternando entre modelos.")
        + '</p><div class="erros">',
    ]
    for case, answer, verdict in examples:
        text = _plain(answer.text)
        short = text if len(text) <= 240 else text[:240].rsplit(" ", 1)[0] + " …"
        chips = "".join(_risk_chip(f) for f in verdict.failures)
        out.append(
            '<article class="erro-cartao">'
            f'<p class="erro-topo"><span class="caso-id">{_case_code(case.case_id)}</span>'
            f'<span class="erro-modelo">{_esc(_model_short(answer.model))}</span></p>'
            f'<p class="erro-pergunta" lang="pt-PT">{_gloss(_esc(case.question))}</p>'
            f'<div class="erro-par"><div><p class="erro-rotulo">{_t("O modelo respondeu")}</p>'
            f'<blockquote lang="pt-PT">{_esc(short)}</blockquote></div>'
            f'<div><p class="erro-rotulo">{_t("A referência diz")}</p>'
            f'<p class="erro-ref" lang="pt-PT">{_gloss(_esc(case.reference))}</p>'
            f'<p class="fonte">{_gloss(_esc(case.source.name))}, {_esc(case.source.reference)}</p></div></div>'
            f'<p class="erro-chips">{chips}</p>'
            f'<p><a href="#caso-{_esc(case.case_id)}">{_t("Ver o caso completo")}</a></p></article>'
        )
    out.append("</div></section>")
    return "".join(out)


def _areas(cases, models, consistency) -> str:
    categories, table = critical_by_category(cases, consistency)
    head = "".join(f'<th scope="col">{_esc(_model_short(m))}</th>' for m in models)
    rows = []
    for category in categories:
        cells = []
        for model in models:
            critical, answered = table.get(model, {}).get(category, (0, 0))
            if not answered:
                cells.append(f'<td class="area-cel vazio">{_t("sem resposta")}</td>')
                continue
            share = critical / answered
            cells.append(
                f'<td class="area-cel" style="--a:{0.08 + 0.62 * share:.3f}" '
                f'title="{_esc(_category(category))}, {_esc(_model_short(model))}: '
                f'{_esc(_t("{a} de {n}", a=critical, n=answered))}">'
                + _t("<strong>{a}</strong> de {n}", a=critical, n=answered) + "</td>"
            )
        rows.append(f'<tr><th scope="row">{_esc(_category(category))}</th>{"".join(cells)}</tr>')
    return (
        f'<section id="areas"><h2>{_t("Falhas críticas por área clínica")}</h2>'
        '<p class="seccao-intro">'
        + _t("Casos com falha crítica em pelo menos uma amostra, por área. Um resultado médio "
             "aceitável pode ocultar uma área de risco. A intensidade da cor é proporcional à "
             "fração de casos com falha crítica.")
        + "</p>"
        f'<div class="grade-wrap"><table class="areas"><thead><tr><th scope="col">{_t("Área")}</th>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></section>'
    )


# ---------------------------------------------------------------- grid


def _cell(entry: Consistency | None, dots: str) -> tuple[str, str]:
    if entry is None:
        return "sem-resposta", f'<span class="ic" aria-hidden="true">○</span> {_t("sem resposta")}'
    css, icon = _STATE_STYLE[entry.state]
    # The state is written out for screen readers; sighted readers get the
    # icon, the dots and the legend above the table.
    label = (
        f'<span class="ic" aria-hidden="true">{icon}</span>'
        f'<span class="vh">{_esc(_t(entry.state.label))}</span>{dots}'
    )
    if entry.state is ConsistencyState.ESTAVEL_CERTO or not entry.worst_failure:
        return css, label
    return css, f'{label}<br><span class="cel-falha">{_esc(_t(_FAILURE_LABEL[entry.worst_failure]))}</span>'


def _grid(
    cases: list[Case],
    models: list[str],
    consistency: dict[tuple[str, str], Consistency],
    pairs: dict[tuple[str, str], list[tuple[Answer, Verdict]]],
    expected: dict[str, int],
) -> str:
    out = ['<div class="grade-wrap"><table class="grade">']
    out.append(
        f'<thead><tr><th scope="col">{_t("Caso")}</th>'
        + "".join(f'<th scope="col"><span class="modelo-nome">{_esc(_model_short(model))}</span></th>' for model in models)
        + "</tr></thead>"
    )
    out.append("<tbody>")
    shown = [c for c in cases if not _always_right(c, models, consistency, expected)]
    for category, group in _grouped_cases(shown):
        out.append(
            f'<tr class="categoria"><td colspan="{len(models) + 1}">{_esc(_category(category))}</td></tr>'
        )
        for case in group:
            out.append(
                f'<tr><th scope="row"><span class="caso-id">{_case_code(case.case_id, side=True)}</span>'
                f'<span class="caso-pergunta" lang="pt-PT" title="{_esc(case.question)}">{_esc(case.question)}</span></th>'
            )
            for model in models:
                key = (case.case_id, model)
                css_class, text = _cell(
                    consistency.get(key), _dots(pairs.get(key, []), expected.get(model, 0))
                )
                out.append(f'<td class="cel {css_class}">{text}</td>')
            out.append("</tr>")
    out.append("</tbody></table></div>")
    if not shown:
        out = [f"<p>{_t('Nenhum caso com falha.')}</p>"]
    right = [c for c in cases if _always_right(c, models, consistency, expected)]
    if right:
        items = "".join(
            f'<li>{_case_code(c.case_id)} <span lang="pt-PT">{_esc(c.question)}</span></li>' for c in right
        )
        out.append(
            f'<details class="recolhe"><summary>{_esc(_plural(len(right), "caso sempre correto em todos os modelos", "casos sempre corretos em todos os modelos"))}'
            f'</summary><ul class="lista-certos">{items}</ul></details>'
        )
    return "".join(out)


def _always_right(case: Case, models: list[str], consistency, expected: dict[str, int]) -> bool:
    """Every model answered every sample of this case, and every one was right."""
    entries = [(consistency.get((case.case_id, m)), expected.get(m, 0)) for m in models]
    return all(
        e is not None and e.state is ConsistencyState.ESTAVEL_CERTO and e.samples >= n
        for e, n in entries
    )


def _grid_legend() -> str:
    items = [
        f'<li><span class="swatch {css}" aria-hidden="true"></span>{icon} {_term(state.label)}</li>'
        for state, (css, icon) in _STATE_STYLE.items()
    ]
    items.append(
        f'<li><span class="swatch sem-resposta" aria-hidden="true"></span>○ {_t("sem resposta")}</li>'
    )
    return f'<ul class="legenda-estados">{"".join(items)}</ul>'


# ---------------------------------------------------------------- detail


def _sample_block(answer: Answer, verdict: Verdict) -> str:
    out = ['<div class="amostra">']
    if verdict.passed:
        out.append(
            f'<p class="passou">✓ {_esc(_t("amostra {n}: cumpre todos os critérios", n=answer.sample))}</p>'
        )
        out.append(f'<blockquote lang="pt-PT">{_esc(answer.text)}</blockquote></div>')
        return "".join(out)
    alternative = (
        " " + _t("(corrigida contra: {alternativa})", alternativa=_esc(verdict.alternative))
        if verdict.alternative else ""
    )
    out.append(f'<p class="amostra-numero">✕ {_esc(_t("amostra {n}", n=answer.sample))}{alternative}</p>')
    out.append(f'<blockquote lang="pt-PT">{_esc(answer.text)}</blockquote>')
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
        f'<section class="detalhe" id="casos-com-falha"><h2>{_t("Casos com falha")}</h2>',
        '<p class="seccao-intro">'
        + _t("Cada caso apresenta a pergunta, a resposta de referência com a fonte e cada "
             "resposta distinta do modelo, com o critério não cumprido e a evidência encontrada "
             "pelo corretor. Os círculos à direita indicam o estado do caso em cada modelo, por "
             "esta ordem: {modelos}.", modelos=_esc(", ".join(_model_short(m) for m in models)))
        + "</p>",
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
                f'<span class="mini {css}" title="{_esc(_model_short(model))}: {_esc(_t(entry.state.label))}">{icon}</span>'
            )
        out.append("<details>")
        out.append(
            f'<summary id="caso-{_esc(case.case_id)}"><span class="caso-id">{_case_code(case.case_id)}</span>'
            f'<span class="resumo-pergunta" lang="pt-PT">{_esc(case.question)}</span>'
            f'<span class="minis" aria-hidden="true">{"".join(minis)}</span></summary>'
        )
        out.append('<div class="detalhe-corpo">')
        out.append(
            f'<p><strong>{_t("Pergunta.")}</strong> <span lang="pt-PT">{_gloss(_esc(case.question))}</span></p>'
        )
        out.append(
            f'<div class="referencia"><p><strong>{_t("Resposta de referência.")}</strong> '
            f'<span lang="pt-PT">{_gloss(_esc(case.reference))}</span></p>'
            f'<p class="fonte"><strong>{_t("Fonte.")}</strong> {_gloss(_esc(case.source.name))}, '
            f"{_esc(case.source.reference)}</p></div>"
        )
        for model in failing_models:
            entry = consistency[(case.case_id, model)]
            css, icon = _STATE_STYLE[entry.state]
            out.append(
                f'<h4><span class="mini {css}" aria-hidden="true">{icon}</span> {_esc(_model_short(model))} '
                f'<span class="h4-sub">{_esc(_t(entry.state.label))}, '
                f'{_esc(_t("{a} de {n} amostras corretas", a=entry.passed, n=entry.samples))}</span></h4>'
            )
            seen: set[str] = set()
            for answer, verdict in pairs.get((case.case_id, model), []):
                if answer.text in seen:
                    continue
                seen.add(answer.text)
                out.append(_sample_block(answer, verdict))
        out.append("</div></details>")
    if not any_case:
        out.append(f"<p>{_t('Nenhum caso com falha.')}</p>")
    out.append("</section>")
    return "".join(out)


# ---------------------------------------------------------------- style

# Colour tokens, written once per theme and placed three times in the CSS:
# the system preference, the header switch, and print (always light).
_LIGHT_TOKENS = """
  --page: #f9f9f7; --surface: #ffffff; --surface-2: #f3f2ee;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #6f6d68;
  --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
  --accent: #1f5fbf;
  --good: #0ca30c; --warning: #fab219; --serious: #ec835a; --critical: #d03b3b; --neutral: #a9a79f;
  --good-bg: rgba(12,163,12,0.12); --warning-bg: rgba(250,178,25,0.18);
  --critical-bg: rgba(208,59,59,0.12); --neutral-bg: rgba(137,135,129,0.14);
  --success-text: #006300; --critical-text: #b42a2a;
  --tooltip-shadow: rgba(0,0,0,0.18);
"""
_DARK_TOKENS = """
  --page: #121211; --surface: #1c1c1a; --surface-2: #272724;
  --ink: #f2f1ec; --ink-2: #cbc9bf; --muted: #a5a399;
  --grid: #34332f; --border: rgba(242,241,236,0.12);
  --accent: #8db4f5;
  --good: #0ca30c; --warning: #fab219; --serious: #ec835a; --critical: #d03b3b; --neutral: #6c6a64;
  --good-bg: rgba(12,163,12,0.20); --warning-bg: rgba(250,178,25,0.16);
  --critical-bg: rgba(208,59,59,0.24); --neutral-bg: rgba(137,135,129,0.18);
  --success-text: #5fd35f; --critical-text: #ff8f86;
  --tooltip-shadow: rgba(0,0,0,0.55);
"""
# Only CSS decides the theme: no radio is checked, so the page follows the
# system until the reader picks one; `:has()` lets the choice reach :root.
_THEME_CSS = (
    ":root { color-scheme: light;" + _LIGHT_TOKENS + "}\n"
    "@media (prefers-color-scheme: dark) {\n"
    "  :root:not(:has(#tema-claro:checked)) { color-scheme: dark;" + _DARK_TOKENS + "}\n}\n"
    ":root:has(#tema-escuro:checked) { color-scheme: dark;" + _DARK_TOKENS + "}\n"
    "@media print {\n"
    "  :root, :root:has(#tema-escuro:checked) { color-scheme: light;" + _LIGHT_TOKENS + "}\n}\n"
)
_STYLE = _THEME_CSS + """
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
.topo { padding: 2rem 0 1rem; position: relative; }
.controlos { position: absolute; top: 1.6rem; right: 0; display: flex; gap: 0.5rem; align-items: flex-start; }
.linguas { position: relative; }
.linguas > summary { list-style: none; cursor: pointer; padding: 0.35rem 0.75rem; border-radius: 999px; font-size: 0.85rem;
  color: var(--ink-2); background: var(--surface-2); border: 1px solid var(--border); user-select: none; }
.linguas > summary::-webkit-details-marker { display: none; }
.linguas > summary:hover { color: var(--ink); }
.linguas > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.linguas ul { position: absolute; right: 0; top: calc(100% + 6px); z-index: 30; list-style: none; margin: 0; padding: 0.35rem;
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 4px 14px var(--tooltip-shadow); min-width: 9rem; }
.linguas a { display: block; padding: 0.35rem 0.6rem; border-radius: 6px; color: var(--ink); text-decoration: none; font-size: 0.9rem; }
.linguas a:hover, .linguas a:focus-visible { background: var(--surface-2); }
.linguas a[aria-current="page"] { font-weight: 650; }
.linguas a[aria-current="page"]::after { content: " ✓"; color: var(--success-text); }
.tema { display: inline-flex; padding: 3px; gap: 2px;
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; }
.tema input { position: absolute; opacity: 0; width: 1px; height: 1px; margin: 0; }
.tema label { cursor: pointer; padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.85rem;
  color: var(--ink-2); user-select: none; }
.tema label:hover { color: var(--ink); }
.tema input:focus-visible + label { outline: 2px solid var(--accent); outline-offset: 1px; }
/* The highlighted half is the theme in force: the one picked, or the system's. */
.tema label[for="tema-claro"], :root:has(#tema-claro:checked) .tema label[for="tema-claro"],
:root:has(#tema-escuro:checked) .tema label[for="tema-escuro"] {
  background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px var(--border); }
:root:has(#tema-escuro:checked) .tema label[for="tema-claro"] { background: none; color: var(--ink-2); box-shadow: none; }
@media (prefers-color-scheme: dark) {
  :root:not(:has(#tema-claro:checked)) .tema label[for="tema-escuro"] {
    background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px var(--border); }
  :root:not(:has(#tema-claro:checked)) .tema label[for="tema-claro"] { background: none; color: var(--ink-2); box-shadow: none; }
}
.marca { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.topo h1 { font-size: 2rem; margin: 0.25rem 0 0.4rem; }
.subtitulo { color: var(--ink-2); margin: 0; }
.data { color: var(--muted); font-size: 0.9rem; margin: 0.35rem 0 0; }
nav.indice { position: sticky; top: 0; z-index: 2; background: var(--page);
  border-top: 1px solid var(--grid); border-bottom: 1px solid var(--grid); padding: 0.6rem 0; }
nav.indice ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.35rem 1.1rem; }
nav.indice a { color: var(--ink-2); text-decoration: none; font-size: 0.92rem; }
nav.indice a:hover, nav.indice a:focus-visible { color: var(--accent); text-decoration: underline; }
.intro { margin-top: 1.5rem;
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }
.lead { font-size: 1.12rem; }
.triagem { color: var(--ink-2); font-size: 0.9rem; margin-top: -0.25rem; }
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
.cartao-modelo header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 0.5rem; min-height: 3.5rem; }
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
.metricas dd.unidade { font-weight: 400; font-size: 0.78rem; color: var(--muted); }
.pontos { display: inline-flex; gap: 2px; margin-left: 0.4rem; font-size: 0.72rem; letter-spacing: 0; vertical-align: 0.05rem; }
.pt.certa { color: var(--success-text); }
.pt { display: inline-block; width: 0.85em; text-align: center; }
.pt.errada { color: var(--critical-text); font-weight: 800; font-size: 1.2em; line-height: 1; }
.pt.falta { color: var(--muted); }
.como-se-conta { background: var(--surface-2); border-radius: 10px; padding: 0.9rem 1.1rem; margin: 1.25rem 0 0.5rem; }
.como-se-conta h3 { margin: 0 0 0.4rem; font-size: 1rem; }
.como-se-conta p { margin: 0.4rem 0; }
.como-se-conta ul { list-style: none; padding: 0; margin: 0.5rem 0; }
.como-se-conta li { margin: 0.25rem 0; }
.como-se-conta li .pontos { display: inline-flex; min-width: 5.5rem; margin: 0 0.6rem 0 0; }
.lingua-linha { font-size: 0.86rem; color: var(--ink-2); margin: 0; }
.protocolo .cartao { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
.protocolo ul { padding-left: 1.2rem; margin-bottom: 0; }
.contexto { background: var(--surface-2); border-radius: 10px; padding: 0.75rem 1rem; max-width: 48rem; font-size: 0.92rem; color: var(--ink-2); }
.contexto strong { color: var(--ink); }
.comparacao { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; }
.comp-frase { font-size: 1.05rem; }
.comp-lista, .comp-eixo { list-style: none; margin: 0; padding: 0; }
.comp-lista li, .comp-eixo { display: grid; grid-template-columns: 9rem 1fr 8.5rem; align-items: center; gap: 0.75rem; padding: 0.45rem 0; }
.comp-nome { font-weight: 600; }
.comp-pista { position: relative; height: 22px; border-left: 1px solid var(--grid); border-right: 1px solid var(--grid);
  background: linear-gradient(var(--grid), var(--grid)) center / 100% 1px no-repeat; }
.comp-ic { position: absolute; top: 9px; height: 4px; border-radius: 2px; background: var(--critical); opacity: 0.45; }
.comp-ponto { position: absolute; top: 3px; width: 16px; height: 16px; margin-left: -8px; border-radius: 50%;
  background: var(--critical); box-shadow: 0 0 0 2px var(--surface); }
.comp-valor { font-variant-numeric: tabular-nums; font-size: 0.9rem; color: var(--ink-2); }
.comp-eixo { padding-top: 0; }
.comp-ticks { position: relative; height: 1.1rem; font-size: 0.72rem; color: var(--muted); }
.comp-ticks span { position: absolute; transform: translateX(-50%); }
.comp-ticks span:first-child { transform: none; } .comp-ticks span:last-child { transform: translateX(-100%); }
.comp-nota { font-size: 0.82rem; color: var(--muted); margin: 0.4rem 0 0; }
.erros { display: grid; grid-template-columns: repeat(auto-fit, minmax(30rem, 1fr)); gap: 1rem; }
.erro-cartao { background: var(--surface); border: 1px solid var(--border); border-left: 4px solid var(--critical); border-radius: 12px; padding: 1.1rem 1.25rem; }
.erro-topo { display: flex; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.3rem; }
.erro-modelo { font-size: 0.85rem; color: var(--ink-2); font-weight: 600; }
.erro-pergunta { font-weight: 600; }
.erro-par { display: grid; grid-template-columns: 1fr 1fr; gap: 0.9rem; }
.erro-rotulo { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin: 0 0 0.25rem; font-weight: 600; }
.erro-par blockquote { max-height: 12rem; font-size: 0.84rem; }
.erro-ref { background: var(--good-bg); border-radius: 6px; padding: 0.6rem 0.8rem; font-size: 0.88rem; margin-bottom: 0.4rem; }
.erro-chips { margin: 0.6rem 0 0.3rem; }
.erro-cartao a, .rodape a { color: var(--accent); }
table.areas { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
table.areas th, table.areas td { border-bottom: 1px solid var(--grid); padding: 0.5rem 0.75rem; text-align: left; }
table.areas thead th { font-size: 0.85rem; }
table.areas tbody th { font-weight: 500; }
.area-cel { background: rgba(208, 59, 59, var(--a)); font-variant-numeric: tabular-nums; min-width: 7rem; }
.area-cel.vazio { background: var(--neutral-bg); color: var(--ink-2); }
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
.caso-pergunta { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; color: var(--ink-2); font-size: 0.82rem; line-height: 1.35; margin-top: 0.15rem; }
tr.categoria td { background: var(--surface-2); font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-2); }
td.cel { white-space: nowrap; }
td.cel.ok { background: var(--good-bg); }
td.cel.erro { background: var(--critical-bg); }
td.cel.instavel { background: var(--warning-bg); }
td.cel.sem-resposta { background: var(--neutral-bg); color: var(--ink-2); }
.cel-falha { font-size: 0.8rem; color: var(--ink-2); }
.ic { font-weight: 700; }
td.cel.ok .ic { color: var(--success-text); }
td.cel.erro .ic { color: var(--critical-text); }
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
abbr.termo { text-decoration: none; border-bottom: 1px dotted var(--muted); cursor: help; position: relative; }
abbr.termo:focus { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
abbr.termo:hover::after, abbr.termo:focus::after {
  content: attr(data-def); position: absolute; left: 0; top: calc(100% + 6px); z-index: 20;
  width: max-content; max-width: min(20rem, 80vw); padding: 0.5rem 0.65rem; border-radius: 6px;
  background: var(--ink); color: var(--page); font-size: 0.8rem; line-height: 1.4; font-weight: 400;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  text-transform: none; letter-spacing: normal; white-space: normal; text-align: left;
  box-shadow: 0 4px 14px var(--tooltip-shadow); pointer-events: none; }
abbr.termo.lado:hover::after, abbr.termo.lado:focus::after { left: calc(100% + 8px); top: -0.3rem; }
.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
details.recolhe { margin-top: 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; scroll-margin-top: 3.5rem; }
details.recolhe > summary { cursor: pointer; padding: 0.8rem 1.25rem; font-weight: 650; }
details.recolhe[open] > summary { border-bottom: 1px solid var(--grid); }
details.recolhe > :not(summary) { margin-left: 1.25rem; margin-right: 1.25rem; }
details.recolhe > :last-child { margin-bottom: 1rem; }
details.mais, details.tecnico { margin-top: 2.5rem; }
details.recolhe h3 { margin-top: 1.25rem; }
.intro details.ler { margin-top: 1rem; background: var(--surface-2); }
.card-linha { font-size: 0.9rem; color: var(--ink-2); margin: 0.75rem 0 0; }
.card-linha strong { color: var(--ink); }
.lista-certos { list-style: none; padding: 0; margin: 0.75rem 1.25rem 1rem; font-size: 0.88rem; color: var(--ink-2); }
.lista-certos li { margin: 0.3rem 0; }
.glossario dl { margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); gap: 0.4rem 1.5rem; }
.glossario dt { font-weight: 650; font-size: 0.9rem; }
.glossario dd { margin: 0 0 0.5rem; color: var(--ink-2); font-size: 0.86rem; }
footer.rodape { margin-top: 3rem; padding-top: 1.25rem; border-top: 1px solid var(--grid); color: var(--ink-2); font-size: 0.88rem; scroll-margin-top: 3.5rem; }
footer.rodape h2 { font-size: 1rem; color: var(--ink); }
@media (max-width: 46rem) {
  .intro { grid-template-columns: 1fr; }
  .detalhe summary { grid-template-columns: 1fr auto; }
  .resumo-pergunta { display: none; }
  .barras-falhas li { grid-template-columns: 8.5rem 1fr 2rem; }
  .destaque { font-size: 2.6rem; }
  .topo h1 { font-size: 1.6rem; }
  .controlos { position: static; margin-top: 0.75rem; }
  .metricas { grid-template-columns: 1fr; }
  .erros { grid-template-columns: 1fr; }
  .erro-par { grid-template-columns: 1fr; }
  .comp-lista li, .comp-eixo { grid-template-columns: 6rem 1fr 6.5rem; }
}
@media print {
  nav.indice { position: static; }
  .controlos { display: none; }
  details { break-inside: avoid; }
}
"""


# ---------------------------------------------------------------- page


def _protocol_section(
    protocol: Protocol, answers: list[Answer], summaries: dict, cases_source, case_ids: list[str]
) -> tuple[str, dict[str, bool]]:
    found_warnings, outcomes = protocol_findings(
        protocol, answers, summaries, cases_source, case_ids, _LANG.get()
    )
    parts = [
        f'<section class="protocolo" id="criterio"><h2>{_t("Critério de aprovação")}</h2><div class="cartao">'
    ]
    parts.append("<p>" + _t(
        "Protocolo {nome}, escrito a {data} ({ficheiro}, {sha} {resumo}).",
        nome=f"<strong>{_esc(protocol.name)}</strong>", data=_esc(protocol.written_on.isoformat()),
        ficheiro=f"<code>{_esc(protocol.path)}</code>", sha=_term("SHA-256"),
        resumo=_esc(protocol.sha256[:12]),
    ) + "</p>")
    for warning in found_warnings:
        parts.append(_aviso(_t("Aviso."), _esc(warning) + "."))
    parts.append("<ul>")
    for outcome in outcomes:
        result = _t("aprovado") if outcome.approved else _t("reprovado")
        details = "; ".join(
            f"{c.label}: {c.observed} ({c.limit}{'' if c.met else _t(', não cumpre')})"
            for c in outcome.checks
        )
        parts.append(
            f"<li><strong>{_esc(_model_short(outcome.model))}: {result}</strong> "
            f"<code>{_esc(outcome.model)}</code>. {_esc(details)}.</li>"
        )
    parts.append("</ul></div></section>")
    return "".join(parts), {o.model: o.approved for o in outcomes}


def _language_menu(alternates: dict[str, str]) -> str:
    """A 🌐 menu linking to the same report in the other languages.

    A `<details>` element, so it opens and closes without a script. Each
    language is written in itself, and the current one is marked.
    """
    current = _LANG.get()
    items = "".join(
        f'<li><a href="{_esc(href)}" hreflang="{HTML_LANG[lang]}" lang="{HTML_LANG[lang]}"'
        + (' aria-current="page"' if lang == current else "")
        + f">{_esc(NAMES[lang])}</a></li>"
        for lang, href in alternates.items()
    )
    return (
        f'<details class="linguas"><summary aria-label="{_esc(_t("Língua"))}: {_esc(NAMES[current])}">'
        f'<span aria-hidden="true">🌐</span> {current.upper()}</summary><ul>{items}</ul></details>'
    )


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
    lingua: str = "pt",
    alternates: dict[str, str] | None = None,
) -> str:
    """Write the whole report as one self contained HTML file.

    `lingua` is the language of the interface; the cases and the answers are
    always shown in the original Portuguese. `alternates` maps each language
    to the address of the same report in it, for the language menu; without
    it, the page has no menu.
    """
    if lingua not in HTML_LANG:
        raise ValueError(f"língua desconhecida {lingua!r}; esperava uma de {', '.join(HTML_LANG)}")
    token = _LANG.set(lingua)
    names = _SHORT.set(unique_names(list(tally_by_model(verdicts))))
    try:
        return _build(
            cases, answers, verdicts, missing, reasons, sources_verified, today,
            cases_source, protocol, alternates,
        )
    finally:
        _SHORT.reset(names)
        _LANG.reset(token)


def _build(
    cases, answers, verdicts, missing, reasons, sources_verified, today, cases_source,
    protocol, alternates,
) -> str:
    per_model = tally_by_model(verdicts)
    models = list(per_model)
    written = (today or date.today()).isoformat()
    title = _t("Relatório do Aferidor")

    out: list[str] = [
        "<!DOCTYPE html>",
        f'<html lang="{HTML_LANG[_LANG.get()]}"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{title}</title><style>{_STYLE}</style></head><body>",
    ]
    menu = _language_menu(alternates) if alternates else ""
    out.append(
        f'<header class="topo"><div class="marca">{_t("Aferidor · banco de ensaio clínico")}</div>'
        '<div class="controlos">' + menu
        + f'<div class="tema" role="radiogroup" aria-label="{_esc(_t("Tema"))}">'
        '<input type="radio" name="tema" id="tema-claro"><label for="tema-claro">'
        f'<span aria-hidden="true">☀</span> {_t("Claro")}</label>'
        '<input type="radio" name="tema" id="tema-escuro"><label for="tema-escuro">'
        f'<span aria-hidden="true">☾</span> {_t("Escuro")}</label></div></div>'
        f"<h1>{title}</h1>"
        f'<p class="subtitulo">{_t("Respostas clínicas de modelos de linguagem, medidas contra casos de referência com fonte pública.")}</p>'
        f'<p class="data">{_t("Relatório escrito em {data}.", data=_esc(written))}</p></header>'
    )

    sections = []
    if models:
        consistency = consistency_by_case(cases, answers, verdicts)
        pairs = pairs_by_case(cases, answers, verdicts)
        sections.append(("resumo", "Resumo"))
        if protocol is not None:
            sections.append(("criterio", "Critério de aprovação"))
        if worst_examples(cases, consistency, pairs):
            sections.append(("erros", "Erros mais graves"))
        sections += [
            ("areas", "Por área clínica"),
            ("grelha", "Resultados por caso"),
            ("casos-com-falha", "Casos com falha"),
            ("falhas", "Mais indicadores"),
        ]
    sections.append(("detalhes", "Detalhes técnicos"))
    out.append(
        f'<nav class="indice" aria-label="{_esc(_t("Secções"))}"><ul>'
        + "".join(f'<li><a href="#{anchor}">{_esc(_t(label))}</a></li>' for anchor, label in sections)
        + "</ul></nav>"
    )

    rule = protocol.case_rule if protocol is not None else DEFAULT_CASE_RULE
    samples_n = max(expected_samples(answers).values(), default=0)
    out.append(_intro(cases, models, answers, _how_counted(samples_n, rule) if models else ""))
    out.extend(_notices(cases, answers, missing, reasons, sources_verified))

    if not models:
        out.append(f'<section id="resumo"><p>{_t("Não há veredictos para relatar.")}</p></section>')
    else:
        summaries = consistency_by_model(consistency)
        states = states_by_model(consistency)
        languages = language_by_model(in_bank(cases, answers))
        expected = expected_samples(answers)
        right = right_cases_by_model(consistency, rule)

        protocol_html, approved = ("", {})
        if protocol is not None:
            protocol_html, approved = _protocol_section(
                protocol, answers, summaries, cases_source, [c.case_id for c in cases]
            )

        out.append(f'<section id="resumo"><h2>{_t("Resumo")}</h2>')
        out.append(_context_note(models))
        out.append(_comparison(summaries, consistency))
        out.append('<div class="cartoes">')
        for model in models:
            out.append(
                _model_card(
                    model, summaries[model], per_model[model], states[model],
                    approved.get(model), right[model],
                )
            )
        out.append("</div>")
        out.append("</section>")
        out.append(protocol_html)
        out.append(_worst(cases, consistency, pairs))
        out.append(_areas(cases, models, consistency))

        out.append(f'<section id="grelha"><h2>{_t("Resultados por caso")}</h2>')
        out.append(
            '<p class="seccao-intro">'
            + _t("Casos com falha em pelo menos um modelo. Cada ponto é uma amostra (● correta, "
                 "✕ incorreta, ○ sem resposta); por baixo, o tipo de falha mais grave.")
            + "</p>"
        )
        out.append(_grid_legend())
        out.append(_grid(cases, models, consistency, pairs, expected))
        out.append("</section>")
        out.append(_detail(cases, models, consistency, pairs))

        more = [
            f'<details class="recolhe mais" id="falhas"><summary>{_t("Mais indicadores: falhas por tipo e português europeu")}</summary>',
            f"<h3>{_t('Falhas por tipo')}</h3>",
            '<p class="seccao-intro">'
            + _t("Quantas respostas tiveram cada tipo de falha, do risco mais alto para o mais "
                 "baixo. Uma resposta pode ter mais do que um tipo.")
            + "</p>",
            _risk_legend(),
            '<div class="falhas-grelha">',
        ]
        top = max((n for tally in per_model.values() for _, n in tally.worst_first()), default=1)
        for model in models:
            more.append(_failure_chart(model, per_model[model], top))
        more.append("</div>")
        more.append(
            f'<div class="lingua"><h3>{_t("Português europeu")}</h3><ul>'
            + "".join(
                f"<li><strong>{_esc(_model_short(m))}</strong> <code>{_esc(m)}</code>: "
                f"{_gloss(_esc(language_line(languages[m], _LANG.get())), ('Acordo Ortográfico',))}</li>"
                for m in models
            )
            + '</ul><p class="seccao-intro">'
            + _t("Indicador independente, baseado numa lista curta de formas alheias ao "
                 "português europeu atual. Não entra na contagem de falhas e subestima a "
                 "frequência real.")
            + "</p></div></details>"
        )
        out.extend(more)

    rows = conditions_rows(in_bank(cases, answers), cases_source, _LANG.get())
    out.append(
        f'<details class="recolhe tecnico" id="detalhes"><summary>{_t("Detalhes técnicos: condições do ensaio, glossário e método")}</summary>'
    )
    out.append(f'<div class="condicoes" id="condicoes"><h3>{_t("Condições do ensaio")}</h3>')
    if rows:
        out.append("<dl>")
        for label, value in rows:
            shown = _t(label) if label == "Banco de casos" else f"{_model_short(label)} ({label})"
            out.append(
                f"<dt>{_esc(shown)}</dt>"
                f"<dd>{_gloss(_esc(value), ('SHA-256', 'tokens_max'))}</dd>"
            )
        out.append("</dl>")
    else:
        out.append(f"<p>{_t('Sem respostas registadas.')}</p>")
    out.append("</div>")

    out.append(_glossary_section("".join(out)))
    out.append(
        f'<div class="metodo" id="metodo"><h3>{_t("Método")}</h3>'
        "<p>" + _t(
            "A correção é textual e determinista: cada critério procura termos e valores na "
            "resposta, e o mesmo texto dá sempre o mesmo veredicto. O próprio corretor é "
            "ensaiado nos dois sentidos: a resposta de referência de cada caso tem de passar, e "
            "uma resposta errada construída para cada critério tem de falhar. O modelo nunca vê "
            "a resposta de referência nem os critérios."
        ) + "</p><p>" + _t(
            "O método completo, os limites conhecidos e a confirmação das fontes estão no "
            "repositório do Aferidor, em {metodo} e {verificacao}.",
            metodo="<code>docs/METODO.md</code>", verificacao="<code>casos/VERIFICACAO.md</code>",
        ) + "</p></div></details>"
        f'<footer class="rodape"><p>{_esc(_t(HEADER_NOTE))}</p></footer>'
    )
    out.append("</body></html>")
    return "".join(out)

__all__ = ["build", "model_label", "case_code_meaning", "GLOSSARY"]
