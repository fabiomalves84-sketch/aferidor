"""What the files of a paid run say, for the reports: what was not answered, under which conditions each model ran,
and what it cost. Read from the provenance file, the cost ledger and the pilot's own, beside the answers.

None of this changes what the grader measures or the denominators of the counts. It is shown next to them. A
trial with none of these files (a local model, every trial kept in `ensaios/`) has no `Files`, and the reports come
out exactly as they did before.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from .checks import REFUSAL_CRITERION
from .grading import match_answers
from .models import Answer, Case, Verdict
from .providers import ERROR_CLASSES, UNAVAILABLE_CLASSES
from .proveniencia import ProvenanceRecord, provenance_path, read_records
from .traducao import decimal, t

# A model with more than this share of its replies not answered (refused by the provider, refused in the text, cut
# off or empty) is marked as not comparable with the others: it was measured on the easier part of the bank, or
# on fewer samples than the rest. 10%, set before any model was measured, and a constant so that it is named.
UNANSWERED_LIMIT_PERCENT = 10

PILOT_FOLDER = "piloto"
LEDGER_NAME = "custos.jsonl"
_UNANSWERED_STATES = ("recusa_api", "truncada", "vazia")
# The category of an attempt that failed in a line written before the class was recorded. It is not a class of
# `providers.ERROR_CLASSES`: nothing is known about those attempts, so they are never filed as "outro".
NO_CLASS = "sem_classe"
_FAILED_STATES = ("erro", "resultado_desconhecido")  # attempts with no reply: the provider said no, or said nothing


def ensaio_ids(trial_dir: Path) -> tuple[str, str]:
    """The ledger's name for a trial and for its pilot: the folder's name, and that name with `/piloto`."""
    name = Path(trial_dir).resolve().name
    return name, f"{name}/{PILOT_FOLDER}"


def ledger_paths(trial_dir: Path) -> tuple[Path, Path]:
    """The ledger of a trial folder and the ledger of its pilot."""
    return Path(trial_dir) / LEDGER_NAME, Path(trial_dir) / PILOT_FOLDER / LEDGER_NAME


@dataclass(frozen=True)
class Files:
    """What was read from beside the answers; each part is empty or None when its file is not there."""

    records: tuple[ProvenanceRecord, ...] = ()
    ledger: dict[str, Any] | None = None
    pilot_records: tuple[ProvenanceRecord, ...] = ()
    pilot_ledger: dict[str, Any] | None = None
    is_pilot: bool = False  # the answers file is the pilot's own, read from inside the pilot folder


def load(answers_path: Path) -> Files | None:
    """The paid-run files that sit beside an answers file, or None if there are none: then nothing is added.

    Read from the pilot folder itself, the files are the pilot's: its ledger names the trial `<folder>/piloto`,
    so that is the id it is read under, and the report says it is the pilot's cost.
    """
    from .custos import Ledger  # kept apart: custos is the writer of these files, the reports only read them

    here = Path(answers_path).parent
    if here.name == PILOT_FOLDER:
        _, pilot_id = ensaio_ids(here.parent)
        ledger_path = here / LEDGER_NAME
        found = Files(
            records=tuple(read_records(provenance_path(answers_path))),
            ledger=Ledger(ledger_path).summary(pilot_id) if ledger_path.exists() else None,
            is_pilot=True,
        )
        return found if (found.records or found.ledger) else None
    trial_id, pilot_id = ensaio_ids(here)
    trial_ledger, pilot_ledger = ledger_paths(here)
    found = Files(
        records=tuple(read_records(provenance_path(answers_path))),
        ledger=Ledger(trial_ledger).summary(trial_id) if trial_ledger.exists() else None,
        pilot_records=tuple(read_records(provenance_path(here / PILOT_FOLDER / Path(answers_path).name))),
        pilot_ledger=Ledger(pilot_ledger).summary(pilot_id) if pilot_ledger.exists() else None,
    )
    if not (found.records or found.ledger or found.pilot_records or found.pilot_ledger):
        return None
    return found


@dataclass(frozen=True)
class ModelRun:
    """One model of the report that has provenance."""

    model: str
    answered: int
    api_refusals: int
    truncated: int
    empty: int
    text_refusals: int
    records: tuple[ProvenanceRecord, ...]
    # Attempts that failed, by class (`providers.ERROR_CLASSES`), and the samples left with no answer because the
    # last thing that happened to them was a failure: by the provider being unavailable, or by any other error.
    failures: dict[str, int] = field(default_factory=dict)
    unanswered_unavailable: int = 0
    unanswered_other_error: int = 0
    unanswered_unknown_cause: int = 0  # the last attempt is from before the class was recorded: the cause is not known

    @property
    def received(self) -> int:
        """Replies the provider gave: the answers kept and the ones it gave and that are not answers."""
        return self.answered + self.api_refusals + self.truncated + self.empty

    @property
    def unanswered(self) -> int:
        return self.api_refusals + self.truncated + self.empty + self.text_refusals

    @property
    def percent(self) -> Decimal:
        return Decimal(100) * self.unanswered / self.received if self.received else Decimal(0)

    @property
    def over_limit(self) -> bool:
        return self.received > 0 and self.unanswered * 100 > UNANSWERED_LIMIT_PERCENT * self.received


@dataclass(frozen=True)
class Analysis:
    models: tuple[ModelRun, ...]
    without_provenance: tuple[str, ...]
    applied_by_model: dict[str, tuple[str, ...]]  # the temperature each model ran under, as a text
    files: Files
    notes: tuple[str, ...] = field(default_factory=tuple)


def _is_text_refusal(verdict: Verdict) -> bool:
    return any(r.criterion == REFUSAL_CRITERION and not r.passed for r in verdict.results)


def _temperature_text(value: Any, lang: str) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return decimal(f"{float(value):.1f}", lang)
    return t("ausente (corre à temperatura do próprio fornecedor)", lang)


def analyse(files: Files, cases: list[Case], answers: list[Answer], verdicts: list[Verdict], lang: str = "pt") -> Analysis | None:
    """Put the provenance next to the answers of this bank. None if no model of the report has any provenance."""
    ids = {c.case_id for c in cases}
    pairs = match_answers(cases, answers, verdicts)
    answered_models = list(dict.fromkeys(a.model for a in answers if a.case_id in ids))
    by_model: dict[str, list[ProvenanceRecord]] = {}
    for record in files.records:
        if record.case_id in ids:
            by_model.setdefault(record.model, []).append(record)
    # A model whose every reply was refused has no answer and no section in the report: it is named here all the same.
    models_in_report = list(dict.fromkeys([*answered_models, *by_model]))

    runs = []
    for model in models_in_report:
        records = by_model.get(model)
        if not records:
            continue
        answered_keys = {(a.case_id, a.sample) for a, _ in pairs if a.model == model}
        last: dict[tuple[str, int], str] = {}
        for record in records:
            if record.state in ("resposta",) + _UNANSWERED_STATES:
                last[(record.case_id, record.sample)] = record.state
        left = [state for key, state in last.items() if key not in answered_keys and state in _UNANSWERED_STATES]
        failing = [r for r in records if r.state in _FAILED_STATES]
        final: dict[tuple[str, int], ProvenanceRecord] = {}
        for record in records:
            final[(record.case_id, record.sample)] = record
        stuck = [r for key, r in final.items() if key not in answered_keys and r.state in _FAILED_STATES]
        unavailable = sum(1 for r in stuck if r.error_class in UNAVAILABLE_CLASSES)
        unknown = sum(1 for r in stuck if r.error_class is None)
        runs.append(ModelRun(
            model=model, answered=len(answered_keys),
            api_refusals=left.count("recusa_api"), truncated=left.count("truncada"), empty=left.count("vazia"),
            text_refusals=sum(1 for a, v in pairs if a.model == model and _is_text_refusal(v)),
            records=tuple(records),
            failures=dict(Counter(r.error_class or NO_CLASS for r in failing)),
            unanswered_unavailable=unavailable, unanswered_other_error=len(stuck) - unavailable - unknown,
            unanswered_unknown_cause=unknown,
        ))
    if not runs:
        return None
    applied: dict[str, tuple[str, ...]] = {}
    for run_ in runs:
        values = {_temperature_text(r.applied_params.get("temperatura"), lang) for r in run_.records}
        applied[run_.model] = tuple(sorted(values))
    graded = {run_.model for run_ in runs}
    for answer in answers:
        if answer.model not in graded and answer.case_id in ids:
            applied.setdefault(answer.model, ())
            if _temperature_text(answer.temperature, lang) not in applied[answer.model]:
                applied[answer.model] = tuple(sorted({*applied[answer.model], _temperature_text(answer.temperature, lang)}))
    return Analysis(
        models=tuple(runs), without_provenance=tuple(m for m in answered_models if m not in graded),
        applied_by_model=applied, files=files,
    )


def _eur(value: Decimal, lang: str) -> str:
    return decimal(f"{value:.4f}", lang)


def _percent(value: Decimal, lang: str) -> str:
    return decimal(f"{value:.1f}", lang)


def _class_order(error_class: str) -> int:
    """Where a class goes in a list: the listed ones in their order, the unrecorded last."""
    return ERROR_CLASSES.index(error_class) if error_class in ERROR_CLASSES else len(ERROR_CLASSES)


def _error_label(error_class: str, lang: str) -> str:
    """The words for a class of failed attempt."""
    labels = {
        "limite_429": t("limite de pedidos (429)", lang),
        "indisponivel_503": t("serviço indisponível (503)", lang),
        "indisponivel_5xx": t("serviço indisponível (outro erro 5xx)", lang),
        "tempo_esgotado": t("tempo esgotado", lang),
        "rede": t("falha de ligação", lang),
        "autenticacao": t("autenticação recusada", lang),
        "resposta_invalida": t("resposta ilegível", lang),
        "outro": t("outro erro", lang),
        NO_CLASS: t("sem classe registada (anterior ao registo)", lang),
    }
    return labels.get(error_class, error_class)


def notices(analysis: Analysis, lang: str = "pt") -> list[tuple[str, str]]:
    """The (label, text) notices that qualify the counts, in plain text; each report escapes or marks them its way."""
    out: list[tuple[str, str]] = []
    parts = [t(
        "As amostras que o fornecedor recusou, que vieram truncadas ou que vieram vazias não têm resposta guardada, "
        "não foram repetidas e não contam como certas nem como erradas: não entram em nenhuma contagem abaixo. "
        "As recusas no próprio texto já são falhas de risco baixo (recusa indevida), como o corretor as classifica, "
        "e continuam nas contagens; aqui só se diz quantas são.", lang,
    )]
    for run_ in analysis.models:
        parts.append(t(
            "{modelo}: {n} de {total} respostas do fornecedor sem resposta ({pct}%): {api} recusadas pelo fornecedor, "
            "{texto} recusadas no texto, {trunc} truncadas, {vazias} vazias.", lang,
            modelo=run_.model, n=run_.unanswered, total=run_.received, pct=_percent(run_.percent, lang),
            api=run_.api_refusals, texto=run_.text_refusals, trunc=run_.truncated, vazias=run_.empty,
        ))
    if analysis.without_provenance:
        parts.append(t("Sem registo de proveniência: {modelos}.", lang, modelos=", ".join(analysis.without_provenance)))
    out.append((t("Amostras não respondidas.", lang), " ".join(parts)))
    for run_ in analysis.models:
        if run_.over_limit:
            out.append((t("Não comparável.", lang), t(
                "{modelo}: {pct}% das respostas do fornecedor ficaram sem resposta ({n} de {total}), acima do limite de "
                "{limite}%: não comparável com os restantes.", lang,
                modelo=run_.model, pct=_percent(run_.percent, lang), n=run_.unanswered, total=run_.received,
                limite=UNANSWERED_LIMIT_PERCENT,
            )))
    failed = [run_ for run_ in analysis.models if run_.failures]
    if failed:
        parts = [t(
            "Quando o fornecedor está indisponível (limite de pedidos, serviço em baixo, tempo esgotado, falha de ligação) "
            "a amostra fica por responder, e isso não diz nada sobre o modelo: nunca conta como resposta errada, em "
            "nenhuma contagem. Cada tentativa que falhou fica aqui, por classe.", lang,
        )]
        for run_ in failed:
            detail = ", ".join(f"{_error_label(c, lang)} {n}" for c, n in sorted(run_.failures.items(), key=lambda item: _class_order(item[0])))
            latest = next((r.error_message for r in reversed(run_.records) if r.state in _FAILED_STATES and r.error_message), "")
            parts.append(t(
                "{modelo}: {n} tentativas falharam ({detalhe}); {k} amostras ficaram por responder por indisponibilidade "
                "do fornecedor, {m} por outro erro do pedido e {c} por responder, causa não registada.", lang,
                modelo=run_.model, n=sum(run_.failures.values()), detalhe=detail,
                k=run_.unanswered_unavailable, m=run_.unanswered_other_error, c=run_.unanswered_unknown_cause,
            ) + (" " + t("Última mensagem: {mensagem}", lang, mensagem=latest) if latest else ""))
        out.append((t("Falhas do fornecedor.", lang), " ".join(parts)))
    groups = {values for values in analysis.applied_by_model.values() if values}
    if len(groups) > 1:
        listed = "; ".join(f"{m}: {', '.join(v)}" for m, v in analysis.applied_by_model.items() if v)
        out.append((t("Temperaturas diferentes.", lang), t(
            "Os modelos não correram com a mesma temperatura aplicada ({lista}). A comparação entre fornecedores não é "
            "feita em condições idênticas.", lang, lista=listed,
        )))
    return out


def _verification(records: tuple[ProvenanceRecord, ...], lang: str) -> str:
    seen = [r for r in records if r.state in ("resposta",) + _UNANSWERED_STATES]
    same = sum(1 for r in seen if r.served_check == "igual")
    different = sum(1 for r in seen if r.served_check == "diferente")
    silent = sum(1 for r in seen if r.served_check == "nao_declarado")
    bits = []
    if same:
        bits.append(t("confirmado em {n} chamadas", lang, n=same))
    if silent:
        bits.append(t("não declarado em {n} chamadas", lang, n=silent))
    if different:
        bits.append(t("diferente do pedido em {n} chamadas", lang, n=different))
    return ", ".join(bits) or t("sem chamadas respondidas", lang)


def condition_lines(run_: ModelRun, lang: str = "pt") -> list[str]:
    """What this model was asked for and served, and how it was priced, read from its provenance lines."""
    records = run_.records
    requested = ", ".join(sorted({r.requested_model for r in records}))
    served = ", ".join(sorted({r.served_model for r in records if r.served_model})) or t("não declarado", lang)
    asked = ", ".join(sorted({_temperature_text(r.requested_params.get("temperatura"), lang) for r in records}))
    applied = ", ".join(sorted({_temperature_text(r.applied_params.get("temperatura"), lang) for r in records}))
    confirmed = any(r.applied_params.get("confirmado_pelo_fornecedor") for r in records)
    tokens = ", ".join(sorted({str(r.requested_params.get("tokens_max")) for r in records}))
    fields = ", ".join(sorted({str(r.applied_params.get("campo_tokens", "")) for r in records}))
    modes = {}
    for r in records:
        if r.state != "erro":
            modes.setdefault(r.count_mode, r.count_reason)
    count = "; ".join(
        f"{t('pelo usage declarado', lang) if mode == 'usage' else t('pelo pior caso', lang)} ({reason})"
        for mode, reason in sorted(modes.items())
    ) or t("sem custo", lang)
    periods = {(
        r.price_period.get("entrada_por_milhao"), r.price_period.get("saida_por_milhao"), r.price_period.get("moeda"),
        r.price_period.get("valido_de"), r.price_period.get("valido_ate"), r.price_period.get("lido_em"), r.price_period.get("fonte"),
    ) for r in records}
    priced = []
    for entry, exit_, currency, since, until, read, source in sorted(periods, key=str):
        priced.append(t(
            "{moeda}, por cada milhão de tokens: entrada {entrada}, saída {saida}; válido de {de} até {ate}; lido em {lido} ({fonte})", lang,
            moeda=currency, entrada=decimal(str(entry), lang), saida=decimal(str(exit_), lang),
            de=since or "-", ate=until or "-", lido=read, fonte=source,
        ))
    rates = {(r.usd_to_eur, r.usd_to_eur_source) for r in records}
    rate_text = "; ".join(
        t("taxa de câmbio {taxa} EUR por cada USD ({fonte})", lang, taxa=decimal(str(rate), lang) if rate is not None else "-", fonte=source or "-")
        for rate, source in sorted(rates, key=str)
    )
    catalogs = ", ".join(sorted({r.catalog_sha256[:12] for r in records}))
    totals = [r for r in records if r.total_tokens is not None and r.total_difference is not None]
    total_line = ""
    if totals:
        total_line = t(
            "total de tokens declarado pelo fornecedor em {n} chamadas; a diferença para entrada mais saída é igual aos "
            "tokens de pensamento em {k}, zero em {z} e outra em {o}", lang,
            n=len(totals), k=sum(1 for r in totals if r.total_difference == r.reasoning_tokens and r.total_difference),
            z=sum(1 for r in totals if r.total_difference == 0),
            o=sum(1 for r in totals if r.total_difference not in (0, r.reasoning_tokens)),
        )
    return [
        t("modelo pedido {pedido}; modelo servido {servido} ({verificacao})", lang,
          pedido=requested, servido=served, verificacao=_verification(records, lang)),
        t("temperatura pedida {pedida}; temperatura aplicada {aplicada}", lang, pedida=asked, aplicada=applied)
        + (" " + t("(confirmada pelo fornecedor)", lang) if confirmed else " " + t("(não confirmada pelo fornecedor)", lang)),
        t("limite de tokens {n}, no campo {campo}", lang, n=tokens, campo=fields),
        t("custo contado {modo}", lang, modo=count),
        *priced,
        rate_text,
        t("catálogo de modelos e preços, SHA-256 {sha}", lang, sha=catalogs),
        *([total_line] if total_line else []),
    ]


def _cost_sums(records: tuple[ProvenanceRecord, ...]) -> tuple[Decimal, Decimal]:
    usage = sum((r.cost_eur for r in records if r.count_mode == "usage"), Decimal(0))
    worst = sum((r.cost_eur for r in records if r.count_mode == "pior_caso"), Decimal(0))
    return usage, worst


def cost_lines(analysis: Analysis, lang: str = "pt") -> list[str]:
    """The cost, in euros: per model, and the trial's total; the pilot's apart. Worst-case figures say what they are."""
    files = analysis.files
    out: list[str] = []

    def block(records: tuple[ProvenanceRecord, ...], ledger: dict[str, Any] | None, title: str) -> list[str]:
        if not records and not ledger:
            return []
        usage, worst = _cost_sums(records)
        unsettled = ledger["por_liquidar_eur"] if ledger else Decimal(0)
        total = ledger["gasto_eur"] if ledger else usage + worst
        line = t(
            "{titulo}: {total} EUR, dos quais {usage} EUR pelo usage declarado e {pior} EUR pelo pior caso", lang,
            titulo=title, total=_eur(total, lang), usage=_eur(usage, lang), pior=_eur(worst, lang),
        )
        if unsettled:
            line += t(", e {pl} EUR de chamadas por liquidar, também no pior caso", lang, pl=_eur(unsettled, lang))
        line += "."
        lines = [line]
        if worst or unsettled:
            lines.append(t(
                "O pior caso é um máximo, não a fatura: o que o fornecedor cobrou é igual ou menor, e só se confirma na "
                "consola de faturação.", lang,
            ))
        return lines

    title = t("Custo do piloto, contado à parte do ensaio", lang) if files.is_pilot else t("Custo do ensaio", lang)
    out += block(files.records, files.ledger, title)
    if files.pilot_records or files.pilot_ledger:
        out += block(files.pilot_records, files.pilot_ledger, t("Custo do piloto, contado à parte do ensaio", lang))
    for run_ in analysis.models:
        usage, worst = _cost_sums(run_.records)
        out.append(t("{modelo}: {usage} EUR pelo usage declarado, {pior} EUR pelo pior caso", lang,
                     modelo=run_.model, usage=_eur(usage, lang), pior=_eur(worst, lang)))
    return out


__all__ = [
    "UNANSWERED_LIMIT_PERCENT", "Analysis", "Files", "ModelRun", "analyse", "condition_lines", "cost_lines",
    "ensaio_ids", "ledger_paths", "load", "notices",
]
