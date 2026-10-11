"""The catalogue of models that can be measured: which provider serves each, under which id, at what
price and with which parameters. Read from `catalogo.json` at run time, never written into the code.

Prices change and ids are retired, so none of them lives in a `.py` file: a test fails if one does.
Every price carries the page it was read from and the day it was read, and every model says whether its
id was confirmed against the provider's own model listing (`verificado_em_execucao`). Nothing here
talks to a network and nothing here reads a key; see `chaves.py` for that.

Where a fact is not known the catalogue says "desconhecido" instead of guessing: the pilot run is what
finds out, and the catalogue is corrected from what it saw.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("catalogo.json")

CURRENCIES = ("USD", "EUR")
UNKNOWN = "desconhecido"
# How a model treats the temperature: "aceita" (sent as asked), "fixa_pelo_fornecedor" (not sent: the provider runs
# at one value, `temperatura_fixa`, and a different one asked is refused), "nao_aceita" (not sent, and the
# provenance says asked X, applied absent), "fixa_por_recomendacao" (the provider accepts others and recommends one:
# `temperatura_fixa`, which is sent as it is, and a different one asked is refused), "ignorada" (sent and ignored), or
# not known yet.
TEMPERATURE_POLICIES = ("aceita", "fixa_pelo_fornecedor", "fixa_por_recomendacao", "nao_aceita", "ignorada", UNKNOWN)
TOKEN_FIELDS = ("max_tokens", "max_completion_tokens", "maxOutputTokens", UNKNOWN)
# How the output token count relates to the reasoning tokens. "por_confirmar" is "desconhecido" for the sums: the
# documentation was read and does not settle it, so a call is counted at its worst case until someone confirms it.
FIXED_TEMPERATURES = ("fixa_pelo_fornecedor", "fixa_por_recomendacao")  # the ones that name a value in `temperatura_fixa`
POR_CONFIRMAR = "por_confirmar"
REASONING_COUNTS = ("incluidos_na_saida", "separados_da_saida", POR_CONFIRMAR, UNKNOWN)
PROVIDERS = ("openai", "anthropic", "gemini", "openai_compativel", "local")
PRICE_ORIGINS = ("pagina_oficial", "declarado_pelo_fabio")
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class CatalogError(ValueError):
    """The catalogue cannot be used: unreadable, malformed, or missing something it must have."""


class EurosUnavailable(CatalogError):
    """A cost in euros was asked for and the catalogue has no USD to EUR rate."""


@dataclass(frozen=True)
class PricePeriod:
    """What one million tokens cost over a stretch of days, for prompts up to a size."""

    input_per_million: Decimal
    output_per_million: Decimal
    currency: str
    valid_from: date | None
    valid_until: date | None  # inclusive
    prompt_tokens_up_to: int | None  # None: any size
    origin: str
    source: str
    read_on: date
    note: str

    def covers(self, day: date, prompt_tokens: int) -> bool:
        if self.valid_from is not None and day < self.valid_from:
            return False
        if self.valid_until is not None and day > self.valid_until:
            return False
        return self.prompt_tokens_up_to is None or prompt_tokens <= self.prompt_tokens_up_to


@dataclass(frozen=True)
class Model:
    key: str
    provider: str
    requested_id: str
    verified_at_run_time: bool
    prices: tuple[PricePeriod, ...]
    token_field: str
    temperature: str
    fixed_temperature: Decimal | None  # the value a provider that does not take one runs at
    reasoning_tokens: str  # whether the output count includes the reasoning tokens
    reasoning_effort: str | None
    tokens_max: int | None
    timeout_s: float
    min_interval_s: float
    key_variable: str | None
    base_url: str | None
    accepted_served_ids: tuple[str, ...]  # served ids a person looked at and allowed, besides the requested one
    to_confirm: tuple[str, ...]  # what here was not found in an official page: names of fields, to say so in a report
    note: str

    @property
    def is_free(self) -> bool:
        """Whether every price period is zero: a model on one's own server, say. It needs no ceiling to run."""
        return all(p.input_per_million == 0 and p.output_per_million == 0 for p in self.prices)

    def price_on(self, day: date, prompt_tokens: int = 0) -> PricePeriod:
        found = [p for p in self.prices if p.covers(day, prompt_tokens)]
        if not found:
            raise CatalogError(
                f"o catálogo não tem preço de {self.key} para {day.isoformat()} com um prompt de "
                f"{prompt_tokens} tokens; acrescentar o período em catalogo.json"
            )
        return found[0]


@dataclass(frozen=True)
class Catalog:
    read_on: date
    usd_to_eur: Decimal | None
    usd_to_eur_source: str
    models: dict[str, Model]

    def model(self, key: str) -> Model:
        try:
            return self.models[key]
        except KeyError:
            raise CatalogError(f"modelo {key!r} não está no catálogo; há: {', '.join(sorted(self.models))}") from None

    def find(self, provider: str, requested_id: str) -> Model | None:
        """The model served by `provider` under this requested id, or None if the catalogue does not list it."""
        for found in self.models.values():
            if found.provider == provider and found.requested_id == requested_id:
                return found
        return None

    def resolve(self, provider: str, name: str) -> Model | None:
        """The model that `name` means for `provider`: its requested id, or its key in this catalogue."""
        return self.find(provider, name) or next(
            (m for k, m in self.models.items() if k == name and m.provider == provider), None
        )

    def key_variables(self) -> frozenset[str]:
        """The environment variables the catalogue declares for keys, and the only ones `chaves` may read."""
        return frozenset(m.key_variable for m in self.models.values() if m.key_variable)

    def cost_usd(self, key: str, day: date, input_tokens: int, output_tokens: int) -> Decimal:
        """The cost of a call in USD; a model priced in euros is converted back, which needs the rate."""
        period = self.model(key).price_on(day, input_tokens)
        amount = (period.input_per_million * input_tokens + period.output_per_million * output_tokens) / 1_000_000
        if period.currency == "EUR":
            return amount / self._rate()
        return amount

    def cost_eur(self, key: str, day: date, input_tokens: int, output_tokens: int) -> Decimal:
        period = self.model(key).price_on(day, input_tokens)
        if period.currency == "EUR":
            return (period.input_per_million * input_tokens + period.output_per_million * output_tokens) / 1_000_000
        return self.cost_usd(key, day, input_tokens, output_tokens) * self._rate()

    def _rate(self) -> Decimal:
        if self.usd_to_eur is None:
            raise EurosUnavailable(
                "o catálogo não tem taxa de USD para EUR (usd_para_eur.valor está vazio) e o Aferidor não "
                "inventa uma: preencher em catalogo.json, com a fonte e a data, para calcular em euros"
            )
        return self.usd_to_eur


def _fail(where: str, problem: str) -> CatalogError:
    return CatalogError(f"catálogo inválido em {where}: {problem}")


def _field(data: dict, name: str, where: str):
    if name not in data:
        raise _fail(where, f"falta o campo {name!r}")
    return data[name]


def _text(data: dict, name: str, where: str, *, empty_ok: bool = False) -> str:
    value = _field(data, name, where)
    if not isinstance(value, str) or (not value.strip() and not empty_ok):
        raise _fail(where, f"{name!r} tem de ser texto não vazio")
    return value


def _optional_text(data: dict, name: str, where: str) -> str | None:
    value = _field(data, name, where)
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise _fail(where, f"{name!r} tem de ser texto ou null")
    return value


def _day(value: object, name: str, where: str, *, nullable: bool = False) -> date | None:
    if value is None and nullable:
        return None
    try:
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
    except ValueError:
        pass
    raise _fail(where, f"{name!r} tem de ser uma data AAAA-MM-DD" + (" ou null" if nullable else ""))


def _number(value: object, name: str, where: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise _fail(where, f"{name!r} tem de ser um número")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise _fail(where, f"{name!r} tem de ser um número") from None
    if not number.is_finite() or number < 0:
        raise _fail(where, f"{name!r} tem de ser um número finito e não negativo")
    return number


def _price_period(raw: object, where: str, default_currency: str) -> PricePeriod:
    if not isinstance(raw, dict):
        raise _fail(where, "cada período de preço tem de ser um objeto")
    origin = _text(raw, "origem", where)
    if origin not in PRICE_ORIGINS:
        raise _fail(where, f"'origem' tem de ser um de {', '.join(PRICE_ORIGINS)}")
    source = _text(raw, "fonte", where)
    if origin == "pagina_oficial" and not source.startswith("https://"):
        raise _fail(where, "'fonte' de uma página oficial tem de ser um URL https")
    up_to = _field(raw, "prompt_tokens_ate", where)
    if up_to is not None and (isinstance(up_to, bool) or not isinstance(up_to, int) or up_to <= 0):
        raise _fail(where, "'prompt_tokens_ate' tem de ser um inteiro positivo ou null")
    currency = raw.get("moeda", default_currency)
    if currency not in CURRENCIES:
        raise _fail(where, f"'moeda' tem de ser uma de {', '.join(CURRENCIES)}")
    valid_from = _day(_field(raw, "valido_de", where), "valido_de", where, nullable=True)
    valid_until = _day(_field(raw, "valido_ate", where), "valido_ate", where, nullable=True)
    if valid_from and valid_until and valid_from > valid_until:
        raise _fail(where, "'valido_de' é depois de 'valido_ate'")
    return PricePeriod(
        input_per_million=_number(_field(raw, "entrada_por_milhao", where), "entrada_por_milhao", where),
        output_per_million=_number(_field(raw, "saida_por_milhao", where), "saida_por_milhao", where),
        currency=currency,
        valid_from=valid_from,
        valid_until=valid_until,
        prompt_tokens_up_to=up_to,
        origin=origin,
        source=source,
        read_on=_day(_field(raw, "lido_em", where), "lido_em", where),
        note=raw.get("nota", "") if isinstance(raw.get("nota", ""), str) else "",
    )


def _check_no_overlap(key: str, periods: tuple[PricePeriod, ...]) -> None:
    """Two periods that cover the same day for the same prompt size would make the price ambiguous."""
    for i, a in enumerate(periods):
        for b in periods[i + 1:]:
            if a.prompt_tokens_up_to != b.prompt_tokens_up_to:
                continue
            start = max(a.valid_from or date.min, b.valid_from or date.min)
            end = min(a.valid_until or date.max, b.valid_until or date.max)
            if start <= end:
                raise _fail(f"modelos.{key}.precos", "dois períodos de preço cobrem os mesmos dias")


def _model(key: str, raw: object) -> Model:
    where = f"modelos.{key}"
    if not isinstance(raw, dict):
        raise _fail(where, "cada modelo tem de ser um objeto")
    provider = _text(raw, "fornecedor", where)
    if provider not in PROVIDERS:
        raise _fail(where, f"'fornecedor' tem de ser um de {', '.join(PROVIDERS)}")
    verified = _field(raw, "verificado_em_execucao", where)
    if not isinstance(verified, bool):
        raise _fail(where, "'verificado_em_execucao' tem de ser true ou false")
    currency = _text(raw, "moeda", where)
    if currency not in CURRENCIES:
        raise _fail(where, f"'moeda' tem de ser uma de {', '.join(CURRENCIES)}")
    raw_periods = _field(raw, "precos", where)
    if not isinstance(raw_periods, list) or not raw_periods:
        raise _fail(where, "'precos' tem de ser uma lista com pelo menos um período")
    periods = tuple(_price_period(p, f"{where}.precos[{i}]", currency) for i, p in enumerate(raw_periods))
    _check_no_overlap(key, periods)
    params = _field(raw, "parametros", where)
    pwhere = f"{where}.parametros"
    if not isinstance(params, dict):
        raise _fail(where, "'parametros' tem de ser um objeto")
    token_field = _text(params, "campo_tokens", pwhere)
    if token_field not in TOKEN_FIELDS:
        raise _fail(pwhere, f"'campo_tokens' tem de ser um de {', '.join(TOKEN_FIELDS)}")
    temperature = _text(params, "temperatura", pwhere)
    if temperature not in TEMPERATURE_POLICIES:
        raise _fail(pwhere, f"'temperatura' tem de ser um de {', '.join(TEMPERATURE_POLICIES)}")
    reasoning_tokens = _text(params, "tokens_raciocinio", pwhere)
    if reasoning_tokens not in REASONING_COUNTS:
        raise _fail(pwhere, f"'tokens_raciocinio' tem de ser um de {', '.join(REASONING_COUNTS)}")
    fixed = params.get("temperatura_fixa")
    if fixed is not None:
        fixed = _number(fixed, "temperatura_fixa", pwhere)
    if temperature in FIXED_TEMPERATURES and fixed is None:
        raise _fail(pwhere, f"uma temperatura {temperature!r} tem de dizer qual em 'temperatura_fixa'")
    tokens_max = _field(params, "tokens_max", pwhere)
    if tokens_max is not None and (isinstance(tokens_max, bool) or not isinstance(tokens_max, int) or tokens_max <= 0):
        raise _fail(pwhere, "'tokens_max' tem de ser um inteiro positivo ou null")
    timeout = _number(_field(raw, "tempo_limite_s", where), "tempo_limite_s", where)
    interval = _number(_field(raw, "ritmo_min_s", where), "ritmo_min_s", where)
    if timeout <= 0:
        raise _fail(where, "'tempo_limite_s' tem de ser maior que zero")
    variable = _optional_text(raw, "chave_env", where)
    if variable is not None and not _ENV_NAME.match(variable):
        raise _fail(where, "'chave_env' tem de ser o nome de uma variável de ambiente")
    note = raw.get("nota", "")
    accepted = raw.get("ids_servidos_aceites", [])
    if not isinstance(accepted, list) or not all(isinstance(a, str) and a.strip() for a in accepted):
        raise _fail(where, "'ids_servidos_aceites' tem de ser uma lista de textos")
    to_confirm = raw.get("por_confirmar", [])
    if not isinstance(to_confirm, list) or not all(isinstance(a, str) and a.strip() for a in to_confirm):
        raise _fail(where, "'por_confirmar' tem de ser uma lista de textos")
    return Model(
        key=key,
        provider=provider,
        requested_id=_text(raw, "id_pedido", where),
        verified_at_run_time=verified,
        prices=periods,
        token_field=token_field,
        temperature=temperature,
        fixed_temperature=fixed,
        reasoning_tokens=reasoning_tokens,
        reasoning_effort=_optional_text(params, "esforco_raciocinio", pwhere),
        tokens_max=tokens_max,
        timeout_s=float(timeout),
        min_interval_s=float(interval),
        key_variable=variable,
        base_url=_optional_text(raw, "base_url", where),
        accepted_served_ids=tuple(accepted),
        to_confirm=tuple(to_confirm),
        note=note if isinstance(note, str) else "",
    )


def parse_catalog(text: str) -> Catalog:
    """Build a catalogue from JSON text, or say exactly what is wrong with it."""
    # Raised after the `except`, so the decoder error (which keeps the whole text) is not chained to ours.
    problem = ""
    data: object = None
    try:
        data = json.loads(text, parse_float=Decimal)
    except json.JSONDecodeError as error:
        problem = f"catálogo inválido: JSON malformado na linha {error.lineno}, coluna {error.colno} ({error.msg})"
    if problem:
        raise CatalogError(problem)
    if not isinstance(data, dict):
        raise _fail("a raiz", "tem de ser um objeto")
    rate = _field(data, "usd_para_eur", "a raiz")
    if not isinstance(rate, dict):
        raise _fail("usd_para_eur", "tem de ser um objeto com 'valor', 'fonte' e 'lido_em'")
    value = _field(rate, "valor", "usd_para_eur")
    usd_to_eur = None if value is None else _number(value, "valor", "usd_para_eur")
    if usd_to_eur is not None and usd_to_eur == 0:
        raise _fail("usd_para_eur", "'valor' não pode ser zero")
    rate_source = _text(rate, "fonte", "usd_para_eur", empty_ok=usd_to_eur is None)
    if usd_to_eur is not None:
        _day(_field(rate, "lido_em", "usd_para_eur"), "lido_em", "usd_para_eur")
    raw_models = _field(data, "modelos", "a raiz")
    if not isinstance(raw_models, dict) or not raw_models:
        raise _fail("modelos", "tem de ser um objeto com pelo menos um modelo")
    return Catalog(
        read_on=_day(_field(data, "lido_em", "a raiz"), "lido_em", "a raiz"),
        usd_to_eur=usd_to_eur,
        usd_to_eur_source=rate_source,
        models={key: _model(key, raw) for key, raw in raw_models.items()},
    )


def load_catalog(path: Path | None = None) -> Catalog:
    """Read the catalogue file (the one shipped with the package by default)."""
    target = path or DEFAULT_PATH
    problem = ""
    text = ""
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as error:
        problem = f"não consegui ler o catálogo {target.name}: {error.strerror or type(error).__name__}"
    except UnicodeDecodeError:
        problem = f"o catálogo {target.name} não está em UTF-8"
    if problem:
        raise CatalogError(problem)
    return parse_catalog(text)
