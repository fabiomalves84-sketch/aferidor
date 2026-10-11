"""What a paid run costs: the estimate before it, the ledger while it runs, and the ceiling that stops it.

Three separate things, all reading the prices from the catalogue and none of them calling a provider:

- `estimate` is a dry run. It counts calls and tokens from the real prompts and prices them in three
  output scenarios. It makes no request and refuses to guess: a missing price or rate is an error.
- `Ledger` is an append-only file with two kinds of line. Before a call it writes an *intention* with the
  worst case of that call; after it, a *result* with what it cost. The running total is read from the file,
  so it survives an interruption, and an intention that never got a result still counts, at its worst case.
- The ceiling is checked when the intention is written, under an exclusive file lock, against the total of
  every model in the trial. Two processes asking for the same sample cannot both get it.

The cost of a result is the worst case of the call whenever the catalogue does not say how the provider
counts reasoning tokens: input as declared plus `tokens_max` at the output price. The declared usage is kept
beside it, to be compared with the provider's own billing, but it does not reduce the bill until the catalogue
says how to read it.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import IO, Any

from .catalogo import UNKNOWN, Catalog, CatalogError

# Portuguese averages about four characters a token; three overstates on purpose, so an estimate made
# without a tokenizer errs on the side of a higher bill. The pilot run compares it with what the provider says.
CHARS_PER_TOKEN = 3
OUTPUT_SCENARIOS = (1000, 4000)

BILLED_STATES = ("resposta", "recusa_api", "truncada", "vazia", "resultado_desconhecido")
# States an earlier attempt can be in and still be asked again on request (`retry_uncertain`): the call has no
# settled result ("sem_resultado": the process died between `reserve` and `settle`), it timed out or was cut off
# ("resultado_desconhecido"), or it came back as an answer that the runner never kept ("resposta"; the runner
# only reaches `reserve` for a sample with no saved answer, so it is the caller who guarantees that). A truncated,
# refused or empty reply is not here: whether to ask those again is still the owner's decision.
REPEATABLE_STATES = ("sem_resultado", "resultado_desconhecido", "resposta")
FREE_STATES = ("erro",)
STATES = BILLED_STATES + FREE_STATES
COUNT_MODES = ("pior_caso", "usage", "sem_custo")


class JsonlError(RuntimeError):
    """A file of one-JSON-object-per-line cannot be read or trusted. Never carries the content of a line."""


class LedgerError(JsonlError):
    """The ledger is inconsistent or a request to it is not allowed."""


class AlreadyAsked(LedgerError):
    """This sample was already asked of this model in this trial, and asking again was not requested."""


class CeilingReached(LedgerError):
    """The next call could take the trial over its ceiling, so it was not made."""

    def __init__(self, message: str, summary: dict[str, Any]) -> None:
        super().__init__(message)
        self.summary = summary


def estimate_tokens(text: str) -> int:
    """An upper-leaning estimate of the tokens in `text`, with no tokenizer: characters over three, rounded up."""
    return -(-len(text) // CHARS_PER_TOKEN)


def _decimal(value: object, name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except ArithmeticError:
        raise LedgerError(f"{name} tem de ser um número") from None
    if not number.is_finite():
        raise LedgerError(f"{name} tem de ser um número finito")
    return number


def _plain(value: Decimal) -> str:
    """A decimal as text without an exponent, so the ledger reads the same everywhere."""
    return format(value, "f")


def _eur(value: Decimal) -> str:
    return f"{value:.4f}"


# ----------------------------------------------------------------------------------------------------
# The dry run.


@dataclass(frozen=True)
class ScenarioCost:
    output_tokens_per_call: int
    usd: Decimal
    eur: Decimal
    over_ceiling: bool | None  # None when no ceiling was given


@dataclass(frozen=True)
class ModelEstimate:
    model_key: str
    calls: int
    input_tokens: int
    scenarios: tuple[ScenarioCost, ...]


@dataclass(frozen=True)
class Estimate:
    models: tuple[ModelEstimate, ...]
    ceiling_eur: Decimal | None
    prompts: int
    samples: int

    def total(self, scenario_index: int) -> tuple[Decimal, Decimal]:
        """USD and EUR of every model together, in the scenario at that position (the lowest first)."""
        usd = sum((m.scenarios[scenario_index].usd for m in self.models), Decimal(0))
        eur = sum((m.scenarios[scenario_index].eur for m in self.models), Decimal(0))
        return usd, eur


def estimate(
    catalog: Catalog,
    model_keys: Iterable[str],
    prompts: Iterable[str],
    *,
    day: date,
    samples: int = 5,
    tokens_max: int | None = None,
    ceiling_eur: Decimal | int | str | None = None,
) -> Estimate:
    """Price a run without making it: every prompt, `samples` times, for each model.

    The output is estimated in three scenarios per call: 1000 tokens, 4000, and `tokens_max` (the argument,
    else the model's own in the catalogue); a scenario above the limit is folded into it. Raises
    `CatalogError` if a model has no price for `day` or no `tokens_max`, and `EurosUnavailable` if the
    catalogue has no rate. It never estimates with a missing price as if it were zero.
    """
    texts = list(prompts)
    keys = list(model_keys)
    if not texts or not keys:
        raise LedgerError("a estimativa precisa de pelo menos um modelo e um prompt")
    if samples < 1:
        raise LedgerError("as amostras por caso começam em 1")
    cap = None if ceiling_eur is None else _decimal(ceiling_eur, "o teto")
    sizes = [estimate_tokens(t) for t in texts]
    results = []
    for key in keys:
        model = catalog.model(key)
        limit = tokens_max if tokens_max is not None else model.tokens_max
        if limit is None:
            raise CatalogError(f"o catálogo não tem tokens_max para {key} e não foi dado um; sem ele não há pior caso")
        outputs = sorted({min(o, limit) for o in OUTPUT_SCENARIOS} | {limit})
        scenarios = []
        for out in outputs:
            usd = sum((catalog.cost_usd(key, day, n, out) for n in sizes), Decimal(0)) * samples
            eur = sum((catalog.cost_eur(key, day, n, out) for n in sizes), Decimal(0)) * samples
            scenarios.append(ScenarioCost(out, usd, eur, None if cap is None else eur > cap))
        results.append(ModelEstimate(key, len(texts) * samples, sum(sizes) * samples, tuple(scenarios)))
    return Estimate(tuple(results), cap, len(texts), samples)


def format_estimate(found: Estimate) -> str:
    """The estimate as text for a person: one block per model, then the total of the three scenarios."""
    lines = [f"Estimativa a seco: {found.prompts} prompts x {found.samples} amostras. Nenhum pedido foi feito."]
    for item in found.models:
        lines.append(f"{item.model_key}: {item.calls} chamadas, {item.input_tokens} tokens de entrada estimados")
        for s in item.scenarios:
            flag = "" if s.over_ceiling is None else ("  EXCEDE O TETO" if s.over_ceiling else "")
            lines.append(f"  saída de {s.output_tokens_per_call} tokens por chamada: {_eur(s.eur)} EUR ({_eur(s.usd)} USD){flag}")
    depth = min(len(m.scenarios) for m in found.models)
    for i in range(depth):
        usd, eur = found.total(i)
        flag = "" if found.ceiling_eur is None else ("  EXCEDE O TETO" if eur > found.ceiling_eur else "")
        lines.append(f"Total, cenário {i + 1} de {depth}: {_eur(eur)} EUR ({_eur(usd)} USD){flag}")
    if found.ceiling_eur is not None:
        lines.append(f"Teto: {_eur(found.ceiling_eur)} EUR")
    return "\n".join(lines)


# ----------------------------------------------------------------------------------------------------
# A file of JSON lines that more than one process may write.


def _lock(handle: IO[bytes]) -> None:
    try:
        import fcntl
    except ImportError:  # Windows
        import msvcrt

        handle.seek(0)
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
                return
            except OSError:
                continue
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock(handle: IO[bytes]) -> None:
    try:
        import fcntl
    except ImportError:  # Windows
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class LockedJsonl:
    """An open, exclusively locked file of JSON lines, read whole and appended to with an `fsync` each time."""

    def __init__(self, handle: IO[bytes], name: str) -> None:
        self._handle = handle
        self._name = name
        self._tail_start: int | None = None  # where an unfinished last line begins, if there is one
        self._needs_newline = False

    def read(self) -> list[dict[str, Any]]:
        """Every complete line. An unfinished last line is skipped (the writer died in it); a bad one in the
        middle is an error that names the line number and nothing of its content."""
        self._handle.seek(0)
        data = self._handle.read()
        records: list[dict[str, Any]] = []
        offset = 0
        line_no = 0
        self._tail_start = None
        self._needs_newline = False
        while offset < len(data):
            end = data.find(b"\n", offset)
            terminated = end != -1
            chunk = data[offset:end] if terminated else data[offset:]
            line_no += 1
            try:
                item = json.loads(chunk.decode("utf-8")) if chunk.strip() else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                item = False
            if item is False or (item is not None and not isinstance(item, dict)):
                if not terminated:
                    self._tail_start = offset
                    break
                raise JsonlError(f"{self._name}: a linha {line_no} está corrompida e o ficheiro não é de confiança")
            if item is not None:
                records.append(item)
            if not terminated:
                self._needs_newline = item is not None
                break
            offset = end + 1
        return records

    def append(self, record: dict[str, Any]) -> None:
        """Add one line after the last good one, dropping an unfinished tail first. Call `read` before."""
        if self._tail_start is not None:
            self._handle.truncate(self._tail_start)
            self._tail_start = None
        prefix = b"\n" if self._needs_newline else b""
        self._needs_newline = False
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        self._handle.write(prefix + line)
        self._handle.flush()
        os.fsync(self._handle.fileno())


class JsonlFile:
    """A file of one JSON object per line, opened under an exclusive lock for each operation."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    @contextmanager
    def locked(self) -> Iterator[LockedJsonl]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+b") as handle:
            _lock(handle)
            try:
                yield LockedJsonl(handle, self.path.name)
            finally:
                _unlock(handle)


# ----------------------------------------------------------------------------------------------------
# The ledger.


@dataclass(frozen=True)
class Reservation:
    """What `reserve` hands back: the id to settle with, and the worst case that was set aside."""

    intent_id: str
    worst_usd: Decimal
    worst_eur: Decimal
    attempt: int
    previous_id: str | None = None  # the earlier attempt this one follows, which keeps its cost in the total


@dataclass(frozen=True)
class Settlement:
    state: str
    count_mode: str
    reason: str
    usd: Decimal
    eur: Decimal


@dataclass
class _Intent:
    raw: dict[str, Any]
    result: dict[str, Any] | None = None
    archived: bool = False  # before a restart: still counted as spent, no longer blocks its sample

    @property
    def key(self) -> tuple[str, str, str, int]:
        r = self.raw
        return (r["ensaio"], r["modelo"], r["caso"], r["amostra"])

    @property
    def eur(self) -> Decimal:
        return Decimal(self.result["custo_eur"]) if self.result else Decimal(self.raw["pior_caso_eur"])

    @property
    def usd(self) -> Decimal:
        return Decimal(self.result["custo_usd"]) if self.result else Decimal(self.raw["pior_caso_usd"])

    @property
    def state(self) -> str:
        return self.result["estado"] if self.result else "sem_resultado"


_INTENT_FIELDS = ("id", "ensaio", "run_id", "modelo", "fornecedor", "caso", "amostra", "tentativa", "repeticao",
                  "tokens_max", "entrada_estimada", "dia_preco", "pior_caso_usd", "pior_caso_eur", "quando")
_RESULT_FIELDS = ("intencao", "estado", "modo", "motivo", "custo_usd", "custo_eur", "usage", "quando")
_RESTART_FIELDS = ("ensaio", "modelo", "razao", "gasto_anterior_eur", "quando")


def _usage_dict(usage: object) -> dict[str, int | None] | None:
    """The declared usage as the ledger keeps it, whatever object or mapping it came in; None if none came."""
    if usage is None:
        return None
    if isinstance(usage, dict):
        get = usage.get
        found = {"entrada": get("entrada", get("input_tokens")), "saida": get("saida", get("output_tokens")),
                 "raciocinio": get("raciocinio", get("reasoning_tokens"))}
    else:
        found = {"entrada": getattr(usage, "input_tokens", None), "saida": getattr(usage, "output_tokens", None),
                 "raciocinio": getattr(usage, "reasoning_tokens", None)}
    clean = {k: (v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None) for k, v in found.items()}
    return clean if any(v is not None for v in clean.values()) else None


def settle_cost(catalog: Catalog, intent: dict[str, Any], state: str, usage: dict[str, int | None] | None) -> Settlement:
    """What a finished call cost, by the safe rule.

    An `erro` came back without being processed and costs nothing. Every other state was billed. Unless the
    catalogue says how this model's reasoning tokens are counted, and the provider declared the figures that
    rule needs, the call counts at its worst case, and the declared usage plays no part in the sum.
    """
    if state not in STATES:
        raise LedgerError(f"estado {state!r} desconhecido; os estados são {', '.join(STATES)}")
    if state in FREE_STATES:
        return Settlement(state, "sem_custo", "o fornecedor respondeu com um erro sem processar o pedido", Decimal(0), Decimal(0))
    key, day = intent["modelo"], date.fromisoformat(intent["dia_preco"])
    model = catalog.model(key)
    declared_in = usage["entrada"] if usage else None
    out = usage["saida"] if usage else None
    reasoning = usage["raciocinio"] if usage else None

    counted: tuple[int, int] | None = None
    if state == "resultado_desconhecido":
        reason = "não se sabe se a chamada foi processada: conta o pior caso"
    elif model.reasoning_tokens == UNKNOWN:
        reason = "o catálogo não diz como este modelo conta os tokens de raciocínio: conta o pior caso"
    elif declared_in is None or out is None:
        reason = "o fornecedor não declarou a entrada e a saída: conta o pior caso"
    elif model.reasoning_tokens == "incluidos_na_saida":
        counted, reason = (declared_in, out), "usage declarado, com o raciocínio já dentro da saída"
    elif reasoning is None:
        reason = "o raciocínio vem à parte e o fornecedor não o declarou: conta o pior caso"
    else:
        counted, reason = (declared_in, out + reasoning), "usage declarado, com o raciocínio somado à saída"

    if counted is not None:
        tokens_in, tokens_out = counted
        mode = "usage"
    else:
        tokens_in = declared_in if declared_in is not None else intent["entrada_estimada"]
        tokens_out = intent["tokens_max"]
        mode = "pior_caso"
        if declared_in is None:
            reason += "; entrada estimada, o fornecedor não a declarou"
    return Settlement(
        state, mode, reason,
        catalog.cost_usd(key, day, tokens_in, tokens_out),
        catalog.cost_eur(key, day, tokens_in, tokens_out),
    )


class Ledger:
    """The cost ledger of one trial folder: `custos.jsonl`, append only.

    `reserve` is the only way to start a call and `settle` the only way to finish one. Both read the whole
    file under the lock, so what they decide is what every other process would decide from the same file.
    """

    def __init__(self, path: Path | str, *, clock: Callable[[], datetime] | None = None) -> None:
        self._file = JsonlFile(path)
        self.path = self._file.path
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> str:
        return self._clock().isoformat(timespec="seconds")

    @staticmethod
    def _load(locked: LockedJsonl) -> dict[str, _Intent]:
        intents: dict[str, _Intent] = {}
        for number, line in enumerate(locked.read(), start=1):
            kind = line.get("t")
            try:
                if kind == "intencao":
                    if any(f not in line for f in _INTENT_FIELDS) or line["id"] in intents:
                        raise KeyError
                    Decimal(line["pior_caso_eur"]), Decimal(line["pior_caso_usd"])
                    intents[line["id"]] = _Intent(line)
                elif kind == "resultado":
                    if any(f not in line for f in _RESULT_FIELDS):
                        raise KeyError
                    target = intents[line["intencao"]]
                    if target.result is not None:
                        raise KeyError
                    Decimal(line["custo_eur"]), Decimal(line["custo_usd"])
                    target.result = line
                elif kind == "recomeco":
                    if any(f not in line for f in _RESTART_FIELDS):
                        raise KeyError
                    for earlier in intents.values():
                        if earlier.raw["ensaio"] == line["ensaio"] and earlier.raw["modelo"] == line["modelo"]:
                            earlier.archived = True
                else:
                    raise KeyError
            except (KeyError, ArithmeticError, TypeError):
                raise LedgerError(f"{locked._name}: a linha {number} não é uma intenção, um resultado ou um recomeço válidos") from None
        return intents

    @staticmethod
    def _summary(intents: dict[str, _Intent], ensaio: str, cap: Decimal | None = None) -> dict[str, Any]:
        mine = [i for i in intents.values() if i.raw["ensaio"] == ensaio]
        by_provider: dict[str, Decimal] = {}
        by_model: dict[str, Decimal] = {}
        for i in mine:
            by_provider[i.raw["fornecedor"]] = by_provider.get(i.raw["fornecedor"], Decimal(0)) + i.eur
            by_model[i.raw["modelo"]] = by_model.get(i.raw["modelo"], Decimal(0)) + i.eur
        unsettled = [i for i in mine if i.result is None]
        return {
            "ensaio": ensaio,
            "teto_eur": cap,
            "gasto_eur": sum((i.eur for i in mine), Decimal(0)),
            "gasto_usd": sum((i.usd for i in mine), Decimal(0)),
            "anterior_eur": sum((i.eur for i in mine if i.archived), Decimal(0)),  # before a restart
            "novo_eur": sum((i.eur for i in mine if not i.archived), Decimal(0)),
            "chamadas": len(mine),
            "sem_resultado": len(unsettled),  # reserved and never settled: counted at the worst case
            "por_liquidar_eur": sum((i.eur for i in unsettled), Decimal(0)),
            "por_fornecedor": by_provider,
            "por_modelo": by_model,
        }

    def summary(self, ensaio: str) -> dict[str, Any]:
        """What the trial has spent, in total and by provider and model, as the file stands now.

        Reading a ledger that does not exist is not writing one: it says nothing was spent and creates nothing."""
        if not self.path.exists():
            return self._summary({}, ensaio)
        with self._file.locked() as locked:
            return self._summary(self._load(locked), ensaio)

    def reserve(
        self,
        *,
        catalog: Catalog,
        ensaio: str,
        run_id: str,
        model_key: str,
        case_id: str,
        sample: int,
        prompt: str,
        tokens_max: int,
        day: date,
        ceiling_eur: Decimal | int | str,
        repeat: bool = False,
        retry_uncertain: bool = False,
    ) -> Reservation:
        """Write the intention to make one call, or refuse. Nothing is written when it refuses.

        Raises `AlreadyAsked` if this sample was already asked of this model in this trial and `repeat` is
        not set. Two exceptions: every earlier attempt ended in `erro`, which cost nothing; or
        `retry_uncertain` is set and the sample's last attempt is one of `REPEATABLE_STATES` (the caller says
        there is no saved answer for it). A repetition is a new reservation with its own worst case, linked to
        the one before it, which keeps its cost in the total. Attempts before a restart no longer count as
        asking, but they still count as spent. Raises
        `CeilingReached` if the total so far plus the worst case of this call would pass `ceiling_eur`.
        The ceiling is the trial's, all models together. Raises `CatalogError` or `EurosUnavailable` before
        anything else if the call cannot be priced.
        """
        cap = _decimal(ceiling_eur, "o teto")
        if cap < 0:
            raise LedgerError("o teto não pode ser negativo")
        if tokens_max <= 0 or sample < 1:
            raise LedgerError("tokens_max e a amostra têm de ser positivos")
        model = catalog.model(model_key)
        estimated_in = estimate_tokens(prompt)
        worst_usd = catalog.cost_usd(model_key, day, estimated_in, tokens_max)
        worst_eur = catalog.cost_eur(model_key, day, estimated_in, tokens_max)
        with self._file.locked() as locked:
            intents = self._load(locked)
            earlier = [i for i in intents.values() if i.key == (ensaio, model_key, case_id, sample) and not i.archived]
            if earlier and not repeat and any(i.state != "erro" for i in earlier):
                found = {i.state for i in earlier} - {"erro"}
                if not (retry_uncertain and earlier[-1].state in REPEATABLE_STATES and found <= set(REPEATABLE_STATES)):
                    hint = "; pedi-la outra vez custa de novo e só se faz a pedido explícito"
                    if found <= set(REPEATABLE_STATES):
                        hint += " (o resultado é incerto: --repetir-incertas pede-a de novo e conta os dois gastos)"
                    raise AlreadyAsked(
                        f"a amostra {sample} de {case_id} já foi pedida a {model_key} neste ensaio "
                        f"(estado: {', '.join(sorted(found))}){hint}"
                    )
            summary = self._summary(intents, ensaio, cap)
            if summary["gasto_eur"] + worst_eur > cap:
                raise CeilingReached(
                    f"o teto de {_eur(cap)} EUR não deixa fazer esta chamada: já se gastaram {_eur(summary['gasto_eur'])} EUR "
                    f"em {summary['chamadas']} chamadas ({summary['sem_resultado']} sem resultado, contadas no pior caso) "
                    f"e esta custaria no pior caso {_eur(worst_eur)} EUR, "
                    f"{_eur(summary['gasto_eur'] + worst_eur - cap)} EUR acima do teto. "
                    "Por fornecedor: " + ("; ".join(f"{k} {_eur(v)} EUR" for k, v in sorted(summary["por_fornecedor"].items())) or "nada"),
                    summary,
                )
            intent_id = uuid.uuid4().hex
            locked.append({
                "t": "intencao", "id": intent_id, "ensaio": ensaio, "run_id": run_id, "modelo": model_key,
                "fornecedor": model.provider, "caso": case_id, "amostra": sample, "tentativa": len(earlier) + 1,
                "repeticao": bool(earlier) and (repeat or retry_uncertain) and any(i.state != "erro" for i in earlier),
                "tentativa_anterior": earlier[-1].raw["id"] if earlier else None,
                "tokens_max": tokens_max, "entrada_estimada": estimated_in, "dia_preco": day.isoformat(),
                "pior_caso_usd": _plain(worst_usd), "pior_caso_eur": _plain(worst_eur), "quando": self._now(),
            })
            return Reservation(intent_id, worst_usd, worst_eur, len(earlier) + 1, earlier[-1].raw["id"] if earlier else None)

    def restart(self, ensaio: str, model_key: str, reason: str) -> dict[str, Any]:
        """Record that a model's answers were thrown away to start over. The ledger keeps every line.

        What was spent before stays in the total, and the ceiling still counts it; those samples stop blocking
        a new request. Returns the trial's summary as it stood just before. Needs a reason, in a line.
        """
        if not reason.strip():
            raise LedgerError("um recomeço precisa de uma razão escrita")
        with self._file.locked() as locked:
            intents = self._load(locked)
            before = self._summary(intents, ensaio)
            mine = sum((i.eur for i in intents.values() if i.raw["ensaio"] == ensaio and i.raw["modelo"] == model_key), Decimal(0))
            locked.append({"t": "recomeco", "ensaio": ensaio, "modelo": model_key, "razao": reason.strip(),
                           "gasto_anterior_eur": _plain(mine), "quando": self._now()})
            return before

    def settle(self, intent_id: str, *, catalog: Catalog, state: str, usage: object = None) -> Settlement:
        """Write the result of a reserved call and say what it cost."""
        with self._file.locked() as locked:
            intents = self._load(locked)
            target = intents.get(intent_id)
            if target is None:
                raise LedgerError("não há nenhuma intenção com esse id neste livro")
            if target.result is not None:
                raise LedgerError("esta intenção já tem resultado; um resultado não se escreve duas vezes")
            declared = _usage_dict(usage)
            outcome = settle_cost(catalog, target.raw, state, declared)
            locked.append({
                "t": "resultado", "intencao": intent_id, "estado": state, "modo": outcome.count_mode,
                "motivo": outcome.reason, "custo_usd": _plain(outcome.usd), "custo_eur": _plain(outcome.eur),
                "usage": declared, "quando": self._now(),
            })
            return outcome


__all__ = [
    "AlreadyAsked", "CeilingReached", "Estimate", "JsonlError", "JsonlFile", "Ledger", "LedgerError", "Reservation",
    "Settlement", "estimate", "estimate_tokens", "format_estimate", "settle_cost",
]
