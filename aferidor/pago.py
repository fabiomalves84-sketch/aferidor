"""One paid call, from the reservation to the provenance line: the guard the runner puts around a provider.

The runner asks a model case by case and knows nothing about money. When the model is in the catalogue, it hands
each attempt to `PaidCalls`, which does what has to happen around a call that costs something, in this order:

1. reserve the call in the ledger (the ceiling and the "already asked" rule are decided here, before the call);
2. make the call;
3. settle it: what it cost, by the safe rule of `custos`, with the declared usage kept beside;
4. write the provenance line, with the catalogue hash and the price period it was priced from;
5. check that the model that served it is the one asked for.

A stop is a `RunStopped`: the ceiling would be passed, or another model served the call. It carries the reason, and
nothing already kept is touched. Nothing here imports the runner (the runner imports this); the pieces of the run
configuration it needs are passed in.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from . import build_id, grader_id
from .catalogo import DEFAULT_PATH, Catalog
from .custos import AlreadyAsked, CeilingReached, Ledger, estimate_tokens
from .providers import Provider, ProviderError, Reply
from .proveniencia import ProvenanceRecord, append_record, catalog_sha256, check_served, period_snapshot, status_of

if TYPE_CHECKING:
    from .runner import RunConfig


class RunStopped(RuntimeError):
    """The run must not make another call. The message says why; what was already kept stays."""


@dataclass
class PaidCalls:
    """Everything the guard needs for one paid model in one trial."""

    catalog: Catalog
    model_key: str
    ledger: Ledger
    provenance_file: Path
    ensaio: str
    ceiling_eur: Decimal
    catalog_path: Path = DEFAULT_PATH
    day: date = field(default_factory=date.today)
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    monotonic: Callable[[], float] = time.monotonic

    def ask_with_retry(
        self,
        provider: Provider,
        prompt: str,
        *,
        case_id: str,
        sample: int,
        run_id: str,
        config: RunConfig,
        check_reply: Callable[[Reply], None],
    ) -> tuple[Reply, int]:
        """The paid counterpart of the runner's retry loop: the reply and its latency in milliseconds.

        Every attempt goes through the ledger. A rate limit waits what the server asked (`Retry-After`) or the usual
        backoff, within a longest single wait and a longest total wait; an attempt that may have been charged and
        has no answer is not repeated. A reply that is truncated, refused or empty is not repeated either: it was
        paid for, it is written down, and the runner treats it as before (an error, not an answer).
        """
        model = self.catalog.model(self.model_key)
        waited = 0.0
        last: ProviderError | None = None
        for attempt in range(1, config.attempts + 1):
            try:
                reservation = self.ledger.reserve(
                    catalog=self.catalog, ensaio=self.ensaio, run_id=run_id, model_key=self.model_key,
                    case_id=case_id, sample=sample, prompt=prompt,
                    tokens_max=provider.max_tokens or model.tokens_max or 0, day=self.day, ceiling_eur=self.ceiling_eur,
                )
            except CeilingReached as stop:
                raise RunStopped(f"{stop}. Nada do que já estava guardado foi apagado.") from None
            except AlreadyAsked as again:
                raise ProviderError(str(again), retryable=False, maybe_billed=False) from None

            started_at, t0 = self.now(), self.monotonic()
            try:
                reply = provider.ask(prompt)
            except ProviderError as error:
                state = "resultado_desconhecido" if error.maybe_billed else "erro"
                self._settle_and_write(reservation.intent_id, state, None, provider, prompt, case_id, sample, run_id,
                                       attempt, started_at, t0, None)
                last = error
                if error.maybe_billed:
                    raise ProviderError(
                        f"{error}; a chamada pode ter sido cobrada e não se repete sem pedido explícito",
                        retryable=False,
                    ) from None
                if not error.retryable or attempt == config.attempts:
                    break
                wait = self._wait(error, attempt, config)
                if wait is None or waited + wait > config.max_total_wait_s:
                    break
                config.sleep(wait)
                waited += wait
                continue

            latency_ms = int((self.monotonic() - t0) * 1000)
            check = check_served(model.requested_id, reply.served_model, model.accepted_served_ids)
            self._settle_and_write(reservation.intent_id, status_of(reply.finish_reason, reply.text), reply.usage,
                                   provider, prompt, case_id, sample, run_id, attempt, started_at, t0, reply)
            if check.stop:
                raise RunStopped(
                    f"o fornecedor serviu {check.served!r} em vez de {check.requested!r} ({case_id}, amostra {sample}); "
                    "a resposta não foi guardada e a corrida parou. Nada do que já estava guardado foi apagado."
                )
            check_reply(reply)
            return reply, latency_ms
        raise last if last else ProviderError("falhou sem erro registado")

    @staticmethod
    def _wait(error: ProviderError, attempt: int, config: RunConfig) -> float | None:
        """Seconds to wait before the next attempt, or None if the server asked for more than is allowed."""
        if error.retry_after is None:
            return min(config.backoff_s * attempt, config.max_wait_s)
        return error.retry_after if error.retry_after <= config.max_wait_s else None

    def _settle_and_write(
        self, intent_id: str, state: str, usage, provider: Provider, prompt: str, case_id: str, sample: int,
        run_id: str, attempt: int, started_at: datetime, t0: float, reply: Reply | None,
    ) -> None:
        model = self.catalog.model(self.model_key)
        outcome = self.ledger.settle(intent_id, catalog=self.catalog, state=state, usage=usage)
        check = check_served(model.requested_id, reply.served_model if reply else "", model.accepted_served_ids)
        period = model.price_on(self.day, estimate_tokens(prompt))
        applied = {"temperatura": provider.temperature, "tokens_max": provider.max_tokens, "campo_tokens": model.token_field,
                   "confirmado_pelo_fornecedor": False}
        append_record(self.provenance_file, ProvenanceRecord(
            run_id=run_id, model=provider.name, case_id=case_id, sample=sample, attempt=attempt, catalog_key=self.model_key,
            requested_model=model.requested_id, served_model=reply.served_model if reply else "", served_check=check.status,
            requested_params={"temperatura": provider.temperature, "tokens_max": provider.max_tokens,
                              "campo_tokens": model.token_field},
            applied_params=applied,
            input_tokens=getattr(usage, "input_tokens", None), output_tokens=getattr(usage, "output_tokens", None),
            reasoning_tokens=getattr(usage, "reasoning_tokens", None),
            finish_reason=reply.finish_reason if reply else "unknown", finish_reason_original=None,
            started_at=started_at.isoformat(timespec="seconds"), ended_at=self.now().isoformat(timespec="seconds"),
            latency_s=max(0.0, self.monotonic() - t0), cost_usd=outcome.usd, cost_eur=outcome.eur,
            count_mode=outcome.count_mode, count_reason=outcome.reason, state=state,
            catalog_sha256=catalog_sha256(self.catalog_path), price_period=period_snapshot(period),
            usd_to_eur=self.catalog.usd_to_eur, usd_to_eur_source=self.catalog.usd_to_eur_source,
            build=build_id(), grader=grader_id(),
        ))


__all__ = ["PaidCalls", "RunStopped"]
