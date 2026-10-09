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
shared drive or a laptop without internet. The only addresses in it are a
link to the project and the preview image that link previews show
(`REPO_URL`, `PREVIEW_IMAGE_URL`); opening the report fetches neither. Colour always travels with an
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
from .html_estilo import STYLE
from .lingua import LanguageSummary, language_by_model, language_line
from .models import Answer, Case, Verdict
from .protocolo import REFERENCE_CRITICAL_LIMIT, Protocol
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
from .traducao import HTML_LANG, NAMES, OG_LOCALE, decimal, t as _translate

# The language the page being built is written in. Set by `build`, read by
# every helper through `_t`, so the helpers keep their signatures.
_LANG: contextvars.ContextVar[str] = contextvars.ContextVar("lingua", default="pt")

# The only addresses on the page: a link to the project, and the image a link preview (a
# chat, LinkedIn) shows. Opening the report fetches neither; a crawler reads the second.
REPO_URL = "https://github.com/fabiomalves84-sketch/aferidor"
PREVIEW_IMAGE_URL = "https://fabiomalves84-sketch.github.io/aferidor/imagens/resumo.png"
PREVIEW_IMAGE_SIZE = (1327, 896)
# Where the "sources not yet confirmed" notice can be linked to from the top of the page.
SOURCES_NOTICE_ID = "aviso-fontes"


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


def _aviso(title: str, body: str, anchor: str = "") -> str:
    """A notice box; `body` must already be escaped. `anchor` gives it an id to link to."""
    ident = f' id="{anchor}"' if anchor else ""
    return (
        f'<div class="aviso"{ident} role="note"><span class="aviso-icone" aria-hidden="true">!</span>'
        f"<div><strong>{title}</strong> {body}</div></div>"
    )


def _preview_meta(title: str) -> str:
    """The description and the Open Graph tags a link preview reads. No og:url: a report
    generated locally does not know where it will be published."""
    description = _t(
        "Respostas clínicas de modelos de linguagem, medidas contra casos de referência com fonte pública."
    )
    width, height = PREVIEW_IMAGE_SIZE
    tags = (
        ("name", "description", description),
        ("property", "og:type", "website"),
        ("property", "og:title", title),
        ("property", "og:description", description),
        ("property", "og:locale", OG_LOCALE[_LANG.get()]),
        ("property", "og:image", PREVIEW_IMAGE_URL),
        ("property", "og:image:width", str(width)),
        ("property", "og:image:height", str(height)),
        (
            "property", "og:image:alt",
            _t("Resumo do relatório: modelos comparados pelo número de casos com falha crítica"),
        ),
    )
    return "".join(f'<meta {kind}="{name}" content="{_esc(value)}">' for kind, name, value in tags)


def _repo_link() -> str:
    return f'<a href="{REPO_URL}" rel="noopener">{_t("Código, método e casos no GitHub")}</a>'


# ---------------------------------------------------------------- opening


def _intro(
    cases: list[Case], models: list[str], answers: list[Answer], how_counted: str,
    sources_pending: bool = False,
) -> str:
    samples = max(expected_samples(answers).values(), default=0)
    facts = [
        _plural(len(cases), "caso clínico", "casos clínicos"),
        _plural(len(models), "modelo", "modelos"),
    ]
    if samples:
        facts.append(_plural(samples, "amostra por caso", "amostras por caso"))
    fact_items = "".join(f"<li>{_esc(f)}</li>" for f in facts)
    if sources_pending:
        # The full notice follows the model cards; this keeps it in sight at the top.
        fact_items += f'<li><a href="#{SOURCES_NOTICE_ID}">{_t("fontes por confirmar")}</a></li>'
    reading = _t(
        "<li><strong>O valor em destaque</strong> indica os casos com pelo menos uma "
        "{falha}. Na prática clínica é observada uma única resposta; uma falha crítica é "
        "suficiente.</li><li><strong>A barra de estados</strong> indica a consistência de "
        "cada modelo: casos {sempre}, {parcial} e {nunca}.</li><li><strong>A secção Casos "
        "com falha</strong> apresenta, para cada caso, a pergunta, a referência, a resposta "
        "do modelo e o critério não cumprido, para que cada veredicto possa ser verificado.</li>",
        falha=_term("falha crítica", _t("falha crítica", form="com artigo")),
        sempre=_term("sempre correto", _t("sempre corretos")),
        parcial=_term("parcialmente correto", _t("parcialmente corretos")),
        nunca=_term("nunca correto", _t("nunca corretos")),
    )
    return f"""
<section class="intro" aria-labelledby="sobre">
  <h2 id="sobre" class="vh">{_t("Sobre este relatório")}</h2>
  <p class="lead">{_t("O <strong>Aferidor</strong> avalia a exatidão de modelos de linguagem em perguntas clínicas em português europeu e classifica os erros pelo risco clínico.")}</p>
  <p class="repo">{_repo_link()}</p>
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
) -> tuple[list[str], list[str]]:
    """The notices, by where they go. `early` qualifies the counts themselves (cases or samples
    that never came back) and stays above the summary; `late` is background (the language of the
    cases, sources not yet confirmed) and follows the model cards, so the first result comes first."""
    early: list[str] = []
    late: list[str] = []
    if _LANG.get() != "pt":
        late.append(_aviso(
            _t("Língua dos casos."),
            _t("As perguntas, as respostas de referência e as respostas dos modelos são "
               "apresentadas no original, em português europeu: são o objeto da avaliação."),
        ))
    if not sources_verified:
        late.append(_aviso(
            _t("Aviso."),
            _t("Nem todas as fontes destes casos foram confirmadas por uma pessoa. Até essa "
               "confirmação, os resultados medem o modelo contra valores transcritos "
               "automaticamente. Ver {ficheiro}.", ficheiro="<code>casos/VERIFICACAO.md</code>"),
            anchor=SOURCES_NOTICE_ID,
        ))
    if missing:
        early.append(_aviso(
            _t("Casos sem resposta."),
            _esc(format_missing(missing, reasons))
            + " " + _t("Não entram em nenhuma contagem deste relatório."),
        ))
    gaps = missing_samples(cases, answers)
    if gaps:
        early.append(_aviso(
            _t("Amostras em falta."),
            _esc(format_missing_samples(gaps, expected_samples(answers), _LANG.get()))
            + " " + _t("Não muda nenhuma contagem abaixo; só nomeia o que já era invisível nelas."),
        ))
    return early, late


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
  <p>{_t("<strong>Um caso nunca correto não tem necessariamente uma {falha}</strong>, e um caso parcialmente correto pode ter uma. Por esse motivo, as falhas críticas são contadas à parte.", falha=_term("falha crítica", _t("falha crítica", form="com artigo")))}</p>
</div>"""


def _reference_verdict(summaries: dict[str, ConsistencySummary]) -> str:
    """What a report without a protocol can still say: whether any model reached the reference
    threshold. It is not an approval, and the text says so."""
    meeting = sum(1 for s in summaries.values() if s.critical_cases <= REFERENCE_CRITICAL_LIMIT)
    line = _t("Modelos que cumprem o limiar de referência: {k} de {n}.", k=meeting, n=len(summaries))
    best = ""
    if meeting == 0:
        rows = compare_critical(summaries).rows  # fewest critical cases first
        if rows:
            _, critical, cases_n, _, _ = rows[0]
            best = " " + _t(
                "Melhor resultado: {a} de {b} casos com {falha}.",
                a=critical, b=cases_n, falha=_term("falha crítica"),
            )
    why = _t(
        "Limiar de referência: nenhum caso com {falha}, o limiar usado nos protocolos do projeto. "
        "Não é um protocolo escrito antes do ensaio.",
        falha=_term("falha crítica"),
    )
    return f'<p class="veredicto"><strong>{line}</strong>{best}</p><p class="seccao-intro">{why}</p>'


def _model_card(
    model: str,
    summary: ConsistencySummary,
    tally: Tally,
    states: dict[ConsistencyState, int],
    verdict: bool | None,
    right: tuple[int, int],
    reference: bool | None = None,
) -> str:
    badge = ""
    if verdict is not None:
        badge = (
            f'<span class="selo aprovado">✓ {_t("aprovado pelo protocolo")}</span>'
            if verdict
            else f'<span class="selo reprovado">✕ {_t("reprovado pelo protocolo")}</span>'
        )
    elif reference is not None:
        badge = (
            f'<span class="selo aprovado">✓ {_t("cumpre o limiar de referência")}</span>'
            if reference
            else f'<span class="selo reprovado">✕ {_t("não cumpre o limiar de referência")}</span>'
        )
    legend = _t(
        "de {total} casos com {falha} em alguma amostra ({ic})",
        total=summary.cases, falha=_term("falha crítica", _t("falha crítica", form="sem artigo")),
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
            # Points into the case's body, not at its <summary>: a browser opens the
            # <details> that holds a fragment target, but not one whose target is the
            # always-visible <summary>, so the reader would land on a closed case.
            f'<p><a href="#corpo-{_esc(case.case_id)}">{_t("Ver o caso completo")}</a></p></article>'
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
            said = f"{_model_short(model)}: {_t(entry.state.label)}"
            # The glyph is decoration; the model and its state are written out for
            # screen readers, which otherwise hear which case failed but not for whom.
            minis.append(
                f'<span class="mini {css}" title="{_esc(said)}">'
                f'<span aria-hidden="true">{icon}</span><span class="vh">{_esc(said)}. </span></span>'
            )
        out.append("<details>")
        out.append(
            f'<summary id="caso-{_esc(case.case_id)}"><span class="caso-id">{_case_code(case.case_id)}</span>'
            f'<span class="resumo-pergunta" lang="pt-PT">{_esc(case.question)}</span>'
            f'<span class="minis">{"".join(minis)}</span></summary>'
        )
        out.append(f'<div class="detalhe-corpo" id="corpo-{_esc(case.case_id)}">')
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
        f"<title>{title}</title>{_preview_meta(title)}<style>{STYLE}</style></head><body>",
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
    early, late = _notices(cases, answers, missing, reasons, sources_verified)
    out.append(_intro(
        cases, models, answers, _how_counted(samples_n, rule) if models else "",
        sources_pending=not sources_verified,
    ))
    out.extend(early)

    if not models:
        out.append(f'<section id="resumo"><p>{_t("Não há veredictos para relatar.")}</p></section>')
        out.extend(late)
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

        reference = (
            {m: summaries[m].critical_cases <= REFERENCE_CRITICAL_LIMIT for m in models}
            if protocol is None else {}
        )

        out.append(f'<section id="resumo"><h2>{_t("Resumo")}</h2>')
        if protocol is None:
            out.append(_reference_verdict(summaries))
        out.append(_comparison(summaries, consistency))
        out.append('<div class="cartoes">')
        for model in models:
            out.append(
                _model_card(
                    model, summaries[model], per_model[model], states[model],
                    approved.get(model), right[model], reference=reference.get(model),
                )
            )
        out.append("</div>")
        out.append(_context_note(models))
        out.extend(late)
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
        f'<footer class="rodape"><p>{_esc(_t(HEADER_NOTE))}</p><p class="repo">{_repo_link()}</p></footer>'
    )
    out.append("</body></html>")
    return "".join(out)

__all__ = ["build", "model_label", "case_code_meaning", "GLOSSARY"]
