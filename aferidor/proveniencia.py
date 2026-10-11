"""What was actually asked and served, one line per paid call, beside the answers and not inside them.

`Answer` and its file format are among the files that decide the grader's identity, so a new field there would
change it. The provenance therefore goes to `respostas.proveniencia.jsonl`, a sibling file, linked to each answer
by what the answer already carries: (model, case, sample, run). A line says which model was asked for and which
the provider says served it, the parameters asked for and the ones that were applied, the tokens as declared, how
the cost was counted, and which catalogue and price period it was priced from (`build_id` does not cover
`catalogo.json`, so the line has to keep its hash).

Nothing here talks to a provider. `check_served` only says whether the served id is the one asked for; stopping a
run on that is the runner's decision.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from .catalogo import DEFAULT_PATH, PricePeriod
from .custos import BILLED_STATES, COUNT_MODES, FREE_STATES, JsonlError, JsonlFile

FILE_NAME = "respostas.proveniencia.jsonl"
STATES = BILLED_STATES + FREE_STATES
SERVED_STATUSES = ("igual", "diferente", "nao_declarado")
NOT_SENT = "não enviado"
IMPOSED = "imposta pelo fornecedor"


class ProvenanceError(JsonlError):
    """A provenance line is not valid, or the file cannot be trusted."""


def catalog_sha256(path: Path | None = None) -> str:
    """The SHA-256 of the catalogue file as it is on disk: the prices and ids a call was priced from."""
    return hashlib.sha256((path or DEFAULT_PATH).read_bytes()).hexdigest()


def period_snapshot(period: PricePeriod) -> dict[str, Any]:
    """The price period applied, whole, so a line says what it cost per million tokens without the catalogue."""
    return {
        "entrada_por_milhao": format(period.input_per_million, "f"),
        "saida_por_milhao": format(period.output_per_million, "f"),
        "moeda": period.currency,
        "valido_de": period.valid_from.isoformat() if period.valid_from else None,
        "valido_ate": period.valid_until.isoformat() if period.valid_until else None,
        "prompt_tokens_ate": period.prompt_tokens_up_to,
        "origem": period.origin,
        "fonte": period.source,
        "lido_em": period.read_on.isoformat(),
    }


def status_of(finish_reason: str, text: str) -> str:
    """The state of a call that got a reply, from its normalized finish reason and its text."""
    if finish_reason == "filtered":
        return "recusa_api"
    if finish_reason == "length":
        return "truncada"
    if not text.strip():
        return "vazia"
    return "resposta"


@dataclass(frozen=True)
class ServedCheck:
    status: str  # one of SERVED_STATUSES
    requested: str
    served: str

    @property
    def stop(self) -> bool:
        """Whether a run should stop: the provider served another model than the one asked for."""
        return self.status == "diferente"


def check_served(requested: str, served: str | None, accepted: Iterable[str] = ()) -> ServedCheck:
    """Compare the served id with the requested one, strictly.

    An id the provider did not declare is `nao_declarado`, which is not a mismatch but is written down as such.
    An id that only differs by a date suffix or a prefix is still different, unless it is in `accepted`, a list
    of served ids a person has looked at and allowed.
    """
    given = (served or "").strip()
    if not given:
        return ServedCheck("nao_declarado", requested, "")
    if given == requested or given in set(accepted):
        return ServedCheck("igual", requested, given)
    return ServedCheck("diferente", requested, given)


_FIELDS = (
    "run_id", "modelo", "caso", "amostra", "tentativa", "modelo_catalogo", "id_pedido", "id_servido",
    "servido_declarado", "verificacao_servido", "parametros_pedidos", "parametros_aplicados", "tokens_entrada", "tokens_saida",
    "tokens_raciocinio", "finish_reason", "finish_reason_original", "inicio", "fim", "latencia_s", "custo_usd",
    "custo_eur", "modo_contagem", "motivo_contagem", "estado", "catalogo_sha256", "periodo_preco", "taxa_usd_eur",
    "taxa_fonte", "build", "grader",
)


@dataclass(frozen=True)
class ProvenanceRecord:
    """One paid (or attempted) call. `model`, `case_id`, `sample` and `run_id` are those of the `Answer`."""

    run_id: str
    model: str
    case_id: str
    sample: int
    attempt: int
    catalog_key: str
    requested_model: str
    served_model: str
    served_check: str  # "igual", "diferente" or "nao_declarado"; what `check_served` said of this call
    requested_params: dict[str, Any]
    applied_params: dict[str, Any]
    input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    finish_reason: str
    finish_reason_original: str | None
    started_at: str
    ended_at: str
    latency_s: float
    cost_usd: Decimal
    cost_eur: Decimal
    count_mode: str
    count_reason: str
    state: str
    catalog_sha256: str
    price_period: dict[str, Any]
    usd_to_eur: Decimal | None
    usd_to_eur_source: str
    build: str
    grader: str

    def __post_init__(self) -> None:
        if self.state not in STATES:
            raise ProvenanceError(f"estado {self.state!r} desconhecido; os estados são {', '.join(STATES)}")
        if self.count_mode not in COUNT_MODES:
            raise ProvenanceError(f"modo de contagem {self.count_mode!r} desconhecido")
        if self.served_check not in SERVED_STATUSES:
            raise ProvenanceError(f"verificação do modelo servido {self.served_check!r} desconhecida")
        if self.sample < 1 or self.attempt < 1:
            raise ProvenanceError("a amostra e a tentativa começam em 1")
        if self.latency_s < 0:
            raise ProvenanceError("a latência não pode ser negativa")
        if len(self.catalog_sha256) != 64:
            raise ProvenanceError("falta o sha256 do catálogo com que a chamada foi calculada")

    @property
    def link_key(self) -> tuple[str, str, int, str]:
        return (self.model, self.case_id, self.sample, self.run_id)

    @property
    def served_declared(self) -> bool:
        return bool(self.served_model)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id, "modelo": self.model, "caso": self.case_id, "amostra": self.sample,
            "tentativa": self.attempt, "modelo_catalogo": self.catalog_key, "id_pedido": self.requested_model,
            "id_servido": self.served_model, "servido_declarado": self.served_declared,
            "verificacao_servido": self.served_check,
            "parametros_pedidos": self.requested_params, "parametros_aplicados": self.applied_params,
            "tokens_entrada": self.input_tokens, "tokens_saida": self.output_tokens,
            "tokens_raciocinio": self.reasoning_tokens, "finish_reason": self.finish_reason,
            "finish_reason_original": self.finish_reason_original, "inicio": self.started_at, "fim": self.ended_at,
            "latencia_s": self.latency_s, "custo_usd": format(self.cost_usd, "f"), "custo_eur": format(self.cost_eur, "f"),
            "modo_contagem": self.count_mode, "motivo_contagem": self.count_reason, "estado": self.state,
            "catalogo_sha256": self.catalog_sha256, "periodo_preco": self.price_period,
            "taxa_usd_eur": None if self.usd_to_eur is None else format(self.usd_to_eur, "f"),
            "taxa_fonte": self.usd_to_eur_source, "build": self.build, "grader": self.grader,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ProvenanceRecord:
        try:
            if any(f not in raw for f in _FIELDS):
                raise KeyError
            rate = raw["taxa_usd_eur"]
            return cls(
                run_id=raw["run_id"], model=raw["modelo"], case_id=raw["caso"], sample=raw["amostra"],
                attempt=raw["tentativa"], catalog_key=raw["modelo_catalogo"], requested_model=raw["id_pedido"],
                served_model=raw["id_servido"], served_check=raw["verificacao_servido"], requested_params=raw["parametros_pedidos"],
                applied_params=raw["parametros_aplicados"], input_tokens=raw["tokens_entrada"],
                output_tokens=raw["tokens_saida"], reasoning_tokens=raw["tokens_raciocinio"],
                finish_reason=raw["finish_reason"], finish_reason_original=raw["finish_reason_original"],
                started_at=raw["inicio"], ended_at=raw["fim"], latency_s=raw["latencia_s"],
                cost_usd=Decimal(raw["custo_usd"]), cost_eur=Decimal(raw["custo_eur"]), count_mode=raw["modo_contagem"],
                count_reason=raw["motivo_contagem"], state=raw["estado"], catalog_sha256=raw["catalogo_sha256"],
                price_period=raw["periodo_preco"], usd_to_eur=None if rate is None else Decimal(rate),
                usd_to_eur_source=raw["taxa_fonte"], build=raw["build"], grader=raw["grader"],
            )
        except (KeyError, TypeError, ArithmeticError):
            raise ProvenanceError("uma linha de proveniência não tem a forma esperada") from None


def provenance_path(answers_file: Path | str) -> Path:
    """The provenance file that sits beside an answers file."""
    return Path(answers_file).with_name(FILE_NAME)


def append_record(path: Path | str, record: ProvenanceRecord) -> None:
    """Add one line. An unfinished last line left by an interrupted writer is dropped first."""
    with JsonlFile(path).locked() as locked:
        locked.read()
        locked.append(record.to_dict())


def read_records(path: Path | str) -> list[ProvenanceRecord]:
    """Every complete line, or an empty list if there is no file. A corrupt line in the middle is an error."""
    if not Path(path).exists():
        return []
    with JsonlFile(path).locked() as locked:
        return [ProvenanceRecord.from_dict(raw) for raw in locked.read()]


def unmatched(answers: Sequence[Any], records: Sequence[ProvenanceRecord]) -> tuple[list[Any], list[ProvenanceRecord]]:
    """(answers with no provenance, `resposta` lines with no answer).

    An answer needs a line in state `resposta` with the same (model, case, sample, run). A refused, truncated,
    empty or failed attempt has no answer by design, so it is never reported as an orphan.
    """
    answered = {r.link_key for r in records if r.state == "resposta"}
    existing = {(a.model, a.case_id, a.sample, a.run_id) for a in answers}
    return (
        [a for a in answers if (a.model, a.case_id, a.sample, a.run_id) not in answered],
        [r for r in records if r.state == "resposta" and r.link_key not in existing],
    )


__all__ = [
    "FILE_NAME", "IMPOSED", "NOT_SENT", "ProvenanceError", "ProvenanceRecord", "ServedCheck", "append_record",
    "catalog_sha256", "check_served", "period_snapshot", "provenance_path", "read_records", "status_of", "unmatched",
]
