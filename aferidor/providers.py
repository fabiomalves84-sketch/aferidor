"""Talking to a model under test, behind one narrow interface.

A provider receives a prompt and returns text. It never sees the reference
answer or the acceptance criteria: a bench that shows the model what counts as
correct is not measuring the model, it is measuring the prompt.

No third-party client libraries. The two adapters here speak HTTP directly, so
the bench has no dependency that can change under it between runs.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from .chaves import REPOSITORY_ROOT, KeysError, Secret, read_key

USER_AGENT = "aferidor/0.1"
# Where a key may be read from when it is not in the environment: the `.env` at the root of the repository. A test
# points this at an empty folder, so no test opens the real file.
KEYS_ROOT = REPOSITORY_ROOT
# The request headers that carry a key. Their values are scrubbed out of any message built from a reply or an error.
_SECRET_HEADERS = ("authorization", "x-api-key", "x-goog-api-key")


@dataclass(frozen=True)
class Usage:
    """Tokens a provider says a call used. A figure the provider did not give is None, never zero.

    `reasoning_tokens` is the reasoning the provider reports, whether it lies inside `output_tokens` (Anthropic:
    `output_tokens_details.thinking_tokens`, a part of the billed output) or beside it (Gemini: `thoughtsTokenCount`).
    Which of the two it is, for billing, is the catalogue's `tokens_raciocinio`, not something read from here.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass(frozen=True)
class Reply:
    """What a provider got back: the text, and why it stopped.

    `finish_reason` is normalized across vendors to one of "stop" (the model
    finished on its own), "length" (cut off by `max_tokens`), or "unknown"
    (anything else, kept rather than guessed at).

    `served_model` is the model id the provider says it answered with, which is not always the one
    asked for (an alias can point at a snapshot), and `usage` the tokens it counted. Both are
    empty when the provider did not say; nothing here changes how a reply is read or graded.
    `finish_reason_original` is the provider's own word for why it stopped, before `finish_reason` folded it
    into one vocabulary; None when it did not say.
    """

    text: str
    finish_reason: str = "stop"
    served_model: str = ""
    usage: Usage | None = None
    finish_reason_original: str | None = None
    # What the reply itself says was applied (a temperature, say), when it says. None of the replies read so far
    # echoes a parameter, so nothing fills this yet; it is where a provider that does would put it.
    echoed_params: dict[str, Any] | None = None


def _count(value: object) -> int | None:
    """A token count as the provider wrote it, or None if it is not a plain non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def usage_from(data: object, input_key: str, output_key: str, reasoning: tuple[str, ...] = ()) -> Usage | None:
    """The `usage` object of a decoded reply, read defensively; None when there is nothing usable.

    `reasoning` is the path to the reasoning-token count inside the object, if the vendor has one.
    """
    if not isinstance(data, dict):
        return None
    found = Usage(
        input_tokens=_count(data.get(input_key)),
        output_tokens=_count(data.get(output_key)),
        reasoning_tokens=_count(_dig(data, reasoning)) if reasoning else None,
    )
    return found if found != Usage() else None


def _dig(data: object, path: tuple[str, ...]) -> object:
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _served(data: object) -> str:
    """The `model` field of a decoded reply, if it is a string."""
    value = data.get("model") if isinstance(data, dict) else None
    return value if isinstance(value, str) else ""


def _original(raw: object) -> str | None:
    """The provider's own finish reason, as written, if it is text."""
    return raw if isinstance(raw, str) and raw else None


def normalize_finish_reason(raw: str | None) -> str:
    """Fold every vendor's own vocabulary into "stop", "length", "filtered" or "unknown".

    OpenAI's chat completions and Ollama's compatible layer say "stop" or
    "length"; Anthropic says "end_turn"/"stop_sequence" or "max_tokens". A
    caller that only needs to know "did the model run out of room" should
    never have to know which vendor it is talking to.
    """
    if raw in ("stop", "end_turn", "stop_sequence"):
        return "stop"
    if raw in ("length", "max_tokens"):
        return "length"
    if raw in ("content_filter", "refusal"):
        return "filtered"
    # Google's own `finishReason` values (https://ai.google.dev/api/generate-content, read 2026-10-11). Only the
    # ones that say the content was withheld are folded into "filtered"; the rest stay "unknown", never guessed at.
    if raw == "STOP":
        return "stop"
    if raw == "MAX_TOKENS":
        return "length"
    if raw in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY"):
        return "filtered"
    return "unknown"


class ProviderError(RuntimeError):
    """A call to a model failed.

    `retryable` separates a transient condition (rate limit, timeout, server
    error) from a permanent one (bad key, unknown model). Retrying a permanent
    failure ten times just wastes the run. `retry_after` is how long the server
    asked to wait, in seconds, when it said so.
    """

    def __init__(
        self, message: str, *, retryable: bool = False, retry_after: float | None = None, maybe_billed: bool = True
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        # Whether the provider may have processed, and so charged for, the request that failed. False only
        # when it is certain it did not: an error status came back, or the request never left. A timeout, a
        # connection cut mid-reply or an unreadable reply may have been paid for, so that is the default.
        self.maybe_billed = maybe_billed
        # Seconds the server asked to wait (`Retry-After`), when it said; the runner does not read it yet.
        self.retry_after = retry_after


class Provider(ABC):
    """One model under test.

    `name` is written to every answer, so it must identify the model precisely
    enough to compare two runs months apart.
    """

    name: str
    # The conditions the runner writes to every answer; a provider sets them in `__init__`, and the
    # defaults are those of one that does not ask for either.
    temperature: float = 0.0
    max_tokens: int | None = None

    @abstractmethod
    def ask(self, prompt: str) -> Reply:
        """Send one prompt and return the reply, text and finish reason."""

    def applied_params(self) -> dict[str, Any] | None:
        """What this provider actually puts in the request, for the provenance line; None if it does not say.

        The conditions the runner records (`temperature`, `max_tokens`) are what was asked for. A provider that
        leaves one out, or sends it under another name, says so here: asked 1.0, applied "ausente", never silently.
        """
        return None

    def available_models(self) -> list[str]:
        """Model identifiers this provider currently offers.

        Asked of the provider rather than written down. A list of model names in
        documentation is wrong within months, and a bench that points at a
        retired model fails for a reason that has nothing to do with the bench.
        """
        raise ProviderError(f"{self.name} não sabe listar modelos")


class FakeProvider(Provider):
    """A provider that answers from a script. For tests and dry runs.

    `replies` maps a prompt to its reply; anything unscripted gets `default`.
    `failures` makes the first N calls raise a retryable error, which is how
    the runner's retry path gets exercised without a network. `finish_reason`
    lets a test simulate a model that ran out of `max_tokens`.
    """

    def __init__(
        self,
        name: str = "falso",
        replies: dict[str, str] | None = None,
        default: str = "sem resposta",
        failures: int = 0,
        temperature: float = 0.0,
        finish_reason: str = "stop",
    ) -> None:
        self.name = name
        self.replies = dict(replies or {})
        self.default = default
        self.failures = failures
        self.temperature = temperature
        self.finish_reason = finish_reason
        self.prompts: list[str] = []

    def ask(self, prompt: str) -> Reply:
        self.prompts.append(prompt)
        if self.failures > 0:
            self.failures -= 1
            raise ProviderError("falha simulada", retryable=True)
        for needle, reply in self.replies.items():
            if needle in prompt:
                return Reply(text=reply, finish_reason=self.finish_reason)
        return Reply(text=self.default, finish_reason=self.finish_reason)


def _retry_after(raw: object, now: Callable[[], datetime] | None = None) -> float | None:
    """`Retry-After` as seconds from now: a number of seconds, or an HTTP date (RFC 9110, section 10.2.3).

    Both forms are the standard's; whether a given provider sends either is for its own documentation, which the
    Anthropic errors page (https://platform.claude.com/docs/en/api/errors, read 2026-10-11) says only for the header
    itself. Anything else, a negative number, a date already past, more than a day, is None.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    try:
        seconds = float(text)
    except ValueError:
        try:
            when = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        seconds = (when - (now or (lambda: datetime.now(timezone.utc)))()).total_seconds()
    return seconds if 0 <= seconds < 86400 else None


def _secrets_in(headers: dict[str, str]) -> list[str]:
    """The key values in these request headers, so they can be taken out of anything written from a reply."""
    found = []
    for name, value in headers.items():
        if name.lower() in _SECRET_HEADERS and value:
            token = value.split(" ", 1)[-1].strip()
            if len(token) >= 6:
                found.append(token)
    return found


def _scrub(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        text = text.replace(secret, "<chave omitida>")
    return text


def _request_json(
    url: str, headers: dict[str, str], payload: dict | None, timeout: float
) -> dict:
    """Call an endpoint and return the decoded reply, classifying every failure.

    Anything a message says about the reply or the error has the key taken out first: a provider may echo the key it
    was sent in an error body, and a message that reaches a log or a file must not carry it.
    """
    secrets = _secrets_in(headers)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=body, method="POST" if body is not None else "GET"
    )
    if body is not None:
        request.add_header("content-type", "application/json")
    request.add_header("user-agent", USER_AGENT)
    for key, value in headers.items():
        request.add_header(key, value)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        waited = error.headers.get("Retry-After") if error.headers is not None else None
        try:
            detail = _scrub(error.read().decode("utf-8", "replace")[:400], secrets)
        finally:
            error.close()
        raise ProviderError(
            f"{url} respondeu {error.code}: {detail}",
            retryable=error.code == 429 or error.code >= 500,
            retry_after=_retry_after(waited),
            maybe_billed=False,
        ) from None
    except urllib.error.URLError as error:
        if isinstance(error.reason, ssl.SSLCertVerificationError):
            raise ProviderError(f"{url}: certificado recusado: {_scrub(str(error.reason), secrets)}", retryable=False, maybe_billed=False) from None
        raise ProviderError(f"{url} inacessível: {_scrub(str(error.reason), secrets)}", retryable=True, maybe_billed=False) from None
    except ssl.SSLCertVerificationError as error:
        raise ProviderError(f"{url}: certificado recusado: {_scrub(str(error), secrets)}", retryable=False, maybe_billed=False) from None
    except TimeoutError:
        raise ProviderError(f"{url} excedeu {timeout}s", retryable=True) from None
    except (OSError, http.client.HTTPException) as error:
        # Reset, abort, broken pipe, SSL error, hang-up or short read mid-reply:
        # whatever the socket raises, the call did not finish and may be repeated.
        raise ProviderError(f"{url} desligou a meio da leitura: {_scrub(str(error), secrets)}", retryable=True) from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ProviderError(f"{url} devolveu uma resposta que não é JSON", retryable=True) from None


def _sorted_names(items: list, field: str, strip: str = "") -> list[str]:
    """The `field` of each listed model that has one, sorted; `strip` is a prefix the API adds."""
    return sorted(str(m.get(field, "")).removeprefix(strip) for m in items if m.get(field))


def _key_from_env(variable: str, given: Secret | str | None) -> Secret:
    """The key a provider will use: the one given, else the environment variable, else the `.env` of the repository.

    The value only ever lives in a `Secret`. The error names the variable and never a value.
    """
    if given is not None and (given.reveal() if isinstance(given, Secret) else given).strip():
        return given if isinstance(given, Secret) else Secret(given.strip())
    try:
        found = read_key(variable, [variable], KEYS_ROOT)
    except KeysError as error:
        raise ProviderError(str(error)) from None
    if found is None:
        raise ProviderError(
            f"falta a chave de API: definir {variable} no ambiente ou no ficheiro .env da raiz do repositório, "
            "ou passá-la ao construtor"
        )
    return found


def _chat_completion(
    endpoint: str,
    headers: dict[str, str],
    model: str,
    prompt: str,
    temperature: float | None,
    max_tokens: int,
    timeout: float,
    who: str,
    *,
    tokens_param: str = "max_tokens",
) -> Reply:
    """One call to any endpoint that speaks the OpenAI chat completions shape.

    OpenAI's own API and Ollama's compatibility layer both take this payload
    and answer with the same `choices[0].message.content` shape, so the two
    providers that talk to them share this instead of each repeating it.

    `tokens_param` is the field name for the token limit: OpenAI's reasoning
    models (o1, o3, gpt-5, ...) reject `max_tokens` outright and want
    `max_completion_tokens` instead, while Ollama's compatibility layer only
    understands `max_tokens`. The caller picks the right one; this function
    does not guess.

    A `temperature` of None is left out of the request, for a model that does not take one.
    """
    payload: dict[str, Any] = {"model": model}
    if temperature is not None:
        payload["temperature"] = temperature
    payload[tokens_param] = max_tokens
    payload["messages"] = [{"role": "user", "content": prompt}]
    data = _request_json(endpoint, headers, payload, timeout)
    try:
        choice = data["choices"][0]
        text = choice["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise ProviderError(f"resposta {who} sem texto: {str(data)[:300]}") from None
    return Reply(
        text=text,
        finish_reason=normalize_finish_reason(choice.get("finish_reason")),
        served_model=_served(data),
        usage=usage_from(
            data.get("usage"), "prompt_tokens", "completion_tokens",
            ("completion_tokens_details", "reasoning_tokens"),
        ),
        finish_reason_original=_original(choice.get("finish_reason")),
    )


class OpenAICompatible(Provider):
    """Any server that speaks OpenAI's Chat Completions: OpenAI itself, a vLLM server, another local one.

    `base_url` ends where the versioned path starts (for OpenAI, `https://api.openai.com/v1`); the calls go to
    `{base_url}/chat/completions` and `{base_url}/models`. The key is optional, because a local server may not ask
    for one; when there is one it goes in the `Authorization: Bearer` header and nowhere else.

    Read from the providers' documentation on 2026-10-11, and what could not be read is marked "por confirmar" in
    `catalogo.json` rather than assumed here:
    - https://developers.openai.com/api/docs/guides/migrate-to-responses: Chat Completions "remains supported",
      Responses "is recommended for all new projects"; GPT-6 Astra and Sol "require the Responses API for tool
      calling". This provider asks a plain text question, with no tools, so it uses Chat Completions, which is
      also what the compatible servers speak. The page does not state the usage fields, the token-limit parameter
      or the temperature rule for these models.
    - https://platform.openai.com/docs/api-reference/chat/create (HTTP 403) and
      https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create (HTTP 404)
      could not be opened, so the request and response fields below (`model`, `messages`, `temperature`, the
      token-limit field, `choices[].message.content`, `choices[].finish_reason`, `model`, `usage.prompt_tokens`,
      `usage.completion_tokens`, `usage.completion_tokens_details.reasoning_tokens`) are the ones the earlier
      providers already used and are unconfirmed against the official page.
    - https://docs.vllm.ai/en/latest/serving/online_serving/ lists `/v1/chat/completions` and `/v1/models`, and says
      nothing on the key, the token-limit parameter, the temperature or the reply fields.

    `confirm_model` asks `/models` which models the server has loaded; the id found there is then used as the served
    model when a reply does not carry its own `model` field.
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str,
        api_key: Secret | str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 300.0,
        tokens_param: str = "max_tokens",
        send_temperature: bool = True,
        name_prefix: str = "compativel",
        who: str = "do servidor compatível",
    ) -> None:
        self.name = f"{name_prefix}:{model}"
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key: Secret | None = (
            None if api_key is None or not (api_key.reveal() if isinstance(api_key, Secret) else api_key).strip()
            else (api_key if isinstance(api_key, Secret) else Secret(api_key.strip()))
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.tokens_param = tokens_param
        self.send_temperature = send_temperature
        self.who = who
        self.loaded_model = ""

    def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.api_key.reveal()}"} if self.api_key else {}

    def ask(self, prompt: str) -> Reply:
        reply = _chat_completion(
            f"{self.base_url}/chat/completions", self._headers(), self.model, prompt,
            self.temperature if self.send_temperature else None, self.max_tokens, self.timeout, self.who,
            tokens_param=self.tokens_param,
        )
        if not reply.served_model and self.loaded_model:
            reply = replace(reply, served_model=self.loaded_model)
        return reply

    def available_models(self) -> list[str]:
        data = _request_json(f"{self.base_url}/models", self._headers(), None, self.timeout)
        return _sorted_names(data.get("data", []), "id")

    def confirm_model(self) -> str:
        """Ask the server which models it has loaded and check that the one wanted is among them."""
        names = self.available_models()
        if self.model not in names:
            have = ", ".join(names) if names else "nenhum"
            raise ProviderError(
                f"o servidor em {self.base_url} não tem o modelo {self.model}; tem: {have}. "
                "Num vLLM, o nome vem de --served-model-name",
                retryable=False, maybe_billed=False,
            )
        self.loaded_model = self.model
        return self.loaded_model

    def applied_params(self) -> dict[str, Any]:
        return {
            "temperatura": self.temperature if self.send_temperature else "ausente",
            "tokens_max": self.max_tokens,
            "campo_tokens": self.tokens_param,
            "confirmado_pelo_fornecedor": False,
        }


class OpenAIProvider(OpenAICompatible):
    """OpenAI chat completions."""

    ENV_KEY = "OPENAI_API_KEY"
    BASE_URL = "https://api.openai.com/v1"

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Secret | str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 60.0,
        send_temperature: bool = True,
        key_variable: str | None = None,
    ) -> None:
        super().__init__(
            model, base_url=self.BASE_URL, api_key=_key_from_env(key_variable or self.ENV_KEY, api_key),
            temperature=temperature, max_tokens=max_tokens, timeout=timeout, tokens_param="max_completion_tokens",
            send_temperature=send_temperature, name_prefix="openai", who="da OpenAI",
        )


class AnthropicProvider(Provider):
    """Anthropic messages.

    Read on 2026-10-11 from https://platform.claude.com/docs/en/api/messages/create and
    https://platform.claude.com/docs/en/api/errors:
    - headers: `X-Api-Key`, `anthropic-version: 2023-06-01`, `Content-Type: application/json` (the page's example);
    - request: `model`, `max_tokens`, `messages`; `temperature` is "Deprecated. Models released after Claude Opus 4.6
      do not support setting temperature. A value of 1.0 will be accepted for backwards compatibility, all other
      values will be rejected with a 400 error", and "Defaults to 1.0". So for such a model `send_temperature` is
      False: the call goes without one and runs at the provider's 1.0;
    - reply: `model`, `stop_reason` (`end_turn`, `max_tokens`, `stop_sequence`, `tool_use`, `pause_turn`, `refusal`,
      `model_context_window_exceeded`), `usage.input_tokens`, `usage.output_tokens` ("the inclusive, authoritative
      total used for billing") and `usage.output_tokens_details.thinking_tokens`, which "approximates" the part of
      it spent on reasoning; thinking tokens count toward `max_tokens` (the Fable 5.1 overview says thinking is
      adaptive and always on);
    - errors: 429 `rate_limit_error` (a spend-cap 429 "has no `retry-after` header"), 5xx retryable, 529 overloaded,
      the body `{"type": "error", "error": {"type", "message"}, "request_id"}`; every reply has a `request-id` header.
    """

    ENDPOINT = "https://api.anthropic.com/v1/messages"
    ENV_KEY = "ANTHROPIC_API_KEY"
    VERSION = "2023-06-01"

    def __init__(
        self,
        model: str = "claude-sonnet-4-5",
        api_key: Secret | str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 60.0,
        send_temperature: bool = True,
        key_variable: str | None = None,
    ) -> None:
        self.name = f"anthropic:{model}"
        self.model = model
        self.api_key = _key_from_env(key_variable or self.ENV_KEY, api_key)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.send_temperature = send_temperature

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key.reveal(), "anthropic-version": self.VERSION}

    def ask(self, prompt: str) -> Reply:
        payload: dict[str, Any] = {"model": self.model}
        if self.send_temperature:
            payload["temperature"] = self.temperature
        payload["max_tokens"] = self.max_tokens
        payload["messages"] = [{"role": "user", "content": prompt}]
        data = _request_json(self.ENDPOINT, self._headers(), payload, self.timeout)
        try:
            blocks = data["content"]
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (KeyError, TypeError):
            raise ProviderError(f"resposta da Anthropic sem texto: {str(data)[:300]}") from None
        return Reply(
            text=text,
            finish_reason=normalize_finish_reason(data.get("stop_reason")),
            served_model=_served(data),
            usage=usage_from(data.get("usage"), "input_tokens", "output_tokens", ("output_tokens_details", "thinking_tokens")),
            finish_reason_original=_original(data.get("stop_reason")),
        )

    def available_models(self) -> list[str]:
        data = _request_json("https://api.anthropic.com/v1/models?limit=100", self._headers(), None, self.timeout)
        return _sorted_names(data.get("data", []), "id")

    def applied_params(self) -> dict[str, Any]:
        applied: dict[str, Any] = {
            "temperatura": self.temperature if self.send_temperature else "ausente",
            "tokens_max": self.max_tokens,
            "campo_tokens": "max_tokens",
            "confirmado_pelo_fornecedor": False,
        }
        if not self.send_temperature:
            applied["nota"] = "o modelo não aceita temperatura (documentado); corre à temperatura por omissão do fornecedor, 1.0"
        return applied


class GeminiProvider(Provider):
    """Google Gemini, through its OpenAI-compatible endpoint.

    Google answers the same chat completions shape as OpenAI, so asking reuses
    `_chat_completion`. The free tier caps requests per minute; rather than
    spend retries on rate limits that a steady pace avoids, the provider waits
    `min_interval_s` between the start of one request and the next. The
    default, 13 seconds, fits the strictest free limit (5 requests a minute);
    lighter models allow more and the interval can be shortened from the
    environment.
    """

    BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
    ENV_KEY = "GEMINI_API_KEY"
    ENV_INTERVAL = "AFERIDOR_GEMINI_INTERVALO"
    DEFAULT_INTERVAL_S = 13.0

    def __init__(
        self,
        model: str = "gemini-3.8-flash",
        api_key: Secret | str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 300.0,
        min_interval_s: float | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        key_variable: str | None = None,
    ) -> None:
        self.name = f"gemini:{model}"
        self.model = model
        self.api_key = _key_from_env(key_variable or self.ENV_KEY, api_key)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        if min_interval_s is None:
            min_interval_s = float(os.environ.get(self.ENV_INTERVAL, self.DEFAULT_INTERVAL_S))
        self.min_interval_s = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._last_start: float | None = None

    def _pace(self) -> None:
        now = self._clock()
        if self._last_start is not None:
            wait = self.min_interval_s - (now - self._last_start)
            if wait > 0:
                self._sleep(wait)
                now = self._clock()
        self._last_start = now

    def ask(self, prompt: str) -> Reply:
        self._pace()
        reply = _chat_completion(
            f"{self.BASE}/chat/completions",
            {"authorization": f"Bearer {self.api_key.reveal()}"},
            self.model,
            prompt,
            self.temperature,
            self.max_tokens,
            self.timeout,
            "do Gemini",
        )
        return replace(reply, text=without_thoughts(reply.text))

    def available_models(self) -> list[str]:
        data = _request_json(
            f"{self.BASE}/models", {"authorization": f"Bearer {self.api_key.reveal()}"}, None, self.timeout
        )
        return _sorted_names(data.get("data", []), "id", "models/")

    def applied_params(self) -> dict[str, Any]:
        return {"temperatura": self.temperature, "tokens_max": self.max_tokens, "campo_tokens": "max_tokens",
                "confirmado_pelo_fornecedor": False}


_THOUGHT = re.compile(r"<thought>.*?(?:</thought>|\Z)", re.S)


def without_thoughts(text: str) -> str:
    """The answer without the reasoning some models write before it.

    The Gemma models served by the Gemini API put their reasoning in the
    content, inside <thought>...</thought>, and the answer after it. The
    reasoning is not what a doctor would read, and a grader that read it
    would score what the model considered instead of what it said. A block
    that never closes leaves nothing, which the runner treats as a truncated
    answer rather than as an answer.
    """
    return _THOUGHT.sub("", text).strip()


class GoogleProvider(Provider):
    """Google Gemini through its own `generateContent` API, which reports what the OpenAI-compatible one does not.

    The compatible endpoint of `GeminiProvider` has no field for the thinking tokens, the model version or the
    provider's own finish reason; this one has. Read on 2026-10-11 from https://ai.google.dev/api/generate-content
    and https://ai.google.dev/gemini-api/docs/api-key:
    - `POST {BASE}/models/{model}:generateContent`, the key in the `x-goog-api-key` header (the key page's REST
      example; the generate-content page's shell examples use `?key=`, which this provider never does);
    - request: `contents: [{"role": "user", "parts": [{"text": ...}]}]` and `generationConfig` with `temperature` and
      `maxOutputTokens` (both used in the page's examples; the page's table of their ranges and defaults was not
      in the part read, and whether `maxOutputTokens` covers thinking is stated on the thinking page, not here:
      "sets the maximum number of tokens a response can generate, including thought tokens");
    - reply: `candidates[].content.parts[].text`, `candidates[].finishReason` (`STOP`, `MAX_TOKENS`, `SAFETY`,
      `RECITATION`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `SPII`, ... listed on the same page), `modelVersion`,
      `promptFeedback.blockReason` (no candidates when the prompt itself was blocked) and `usageMetadata` with
      `promptTokenCount`, `candidatesTokenCount`, `thoughtsTokenCount`, `totalTokenCount`.
    NOT stated by the pages read, so left "por confirmar" in the catalogue: whether `candidatesTokenCount` includes
    the thought tokens (`totalTokenCount` is described as "prompt + thoughts + response candidates", which suggests
    it does not), and whether thoughts come back in `parts` flagged `thought: true`. Such parts are left out of the
    text if they appear, because the answer a doctor would read is not the reasoning.
    The listing of models (`GET {BASE}/models`, `models[].name`) is also not from a page read.
    """

    BASE = "https://generativelanguage.googleapis.com/v1beta"
    ENV_KEY = "GEMINI_API_KEY"
    ENV_INTERVAL = "AFERIDOR_GEMINI_INTERVALO"
    DEFAULT_INTERVAL_S = 13.0

    def __init__(
        self,
        model: str,
        api_key: Secret | str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 300.0,
        min_interval_s: float | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        send_temperature: bool = True,
        key_variable: str | None = None,
    ) -> None:
        self.name = f"google:{model}"
        self.model = model
        self.api_key = _key_from_env(key_variable or self.ENV_KEY, api_key)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.send_temperature = send_temperature
        if min_interval_s is None:
            min_interval_s = float(os.environ.get(self.ENV_INTERVAL, self.DEFAULT_INTERVAL_S))
        self.min_interval_s = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._last_start: float | None = None

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key.reveal()}

    def _pace(self) -> None:
        now = self._clock()
        if self._last_start is not None:
            wait = self.min_interval_s - (now - self._last_start)
            if wait > 0:
                self._sleep(wait)
                now = self._clock()
        self._last_start = now

    def ask(self, prompt: str) -> Reply:
        self._pace()
        config: dict[str, Any] = {}
        if self.send_temperature:
            config["temperature"] = self.temperature
        config["maxOutputTokens"] = self.max_tokens
        data = _request_json(
            f"{self.BASE}/models/{self.model}:generateContent", self._headers(),
            {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config}, self.timeout,
        )
        usage = usage_from(data.get("usageMetadata"), "promptTokenCount", "candidatesTokenCount", ("thoughtsTokenCount",))
        candidates = data.get("candidates") if isinstance(data, dict) else None
        if not candidates:
            block = (data.get("promptFeedback") or {}).get("blockReason") if isinstance(data, dict) else None
            if isinstance(block, str) and block:
                return Reply("", "filtered", _served_version(data), usage, block)
            raise ProviderError(f"resposta do Google sem candidatos: {str(data)[:300]}")
        first = candidates[0]
        try:
            parts = first["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
        except (KeyError, TypeError):
            text = ""  # a candidate stopped before any content: the runner counts it as a reply with no text
        raw = first.get("finishReason") if isinstance(first, dict) else None
        return Reply(text, normalize_finish_reason(raw), _served_version(data), usage, _original(raw))

    def available_models(self) -> list[str]:
        data = _request_json(f"{self.BASE}/models", self._headers(), None, self.timeout)
        return _sorted_names(data.get("models", []), "name", "models/")

    def applied_params(self) -> dict[str, Any]:
        return {
            "temperatura": self.temperature if self.send_temperature else "ausente",
            "tokens_max": self.max_tokens,
            "campo_tokens": "maxOutputTokens",
            "confirmado_pelo_fornecedor": False,
        }


def _served_version(data: object) -> str:
    """`modelVersion` of a generateContent reply, if it is text."""
    value = data.get("modelVersion") if isinstance(data, dict) else None
    return value if isinstance(value, str) else ""


def _unreachable(base_url: str, error: ProviderError) -> bool:
    """Whether `error` looks like the Ollama server itself is not running.

    `_request_json` marks a `URLError` (connection refused, name not resolved,
    ...) retryable and folds its message with "inacessível". Retrying that
    against a local server that is simply not started wastes every attempt on
    the same failure, so it is turned into one clear, non-retryable message.
    """
    return "inacessível" in str(error)


class LocalProvider(Provider):
    """A model running on this machine through Ollama.

    Nothing leaves the machine: no key, and the only address ever contacted is
    `base_url`, which defaults to Ollama's own local port. This is the shape a
    health organisation would actually run if the model, and every question
    sent to it, has to stay on its own infrastructure.

    Ollama exposes an OpenAI-compatible chat completions endpoint, so asking
    it reuses `_chat_completion`; listing models does not; that one is
    Ollama's own `/api/tags`.
    """

    ENV_URL = "AFERIDOR_LOCAL_URL"
    DEFAULT_URL = "http://localhost:11434"

    def __init__(
        self,
        model: str = "llama3",
        base_url: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 300.0,
    ) -> None:
        self.name = f"local:{model}"
        self.model = model
        self.base_url = (base_url or os.environ.get(self.ENV_URL) or self.DEFAULT_URL).rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _not_running(self) -> ProviderError:
        return ProviderError(
            f"o Ollama não responde em {self.base_url}; confirmar que está instalado e aberto",
            retryable=False,
        )

    def ask(self, prompt: str) -> Reply:
        try:
            return _chat_completion(
                f"{self.base_url}/v1/chat/completions",
                {},
                self.model,
                prompt,
                self.temperature,
                self.max_tokens,
                self.timeout,
                "do Ollama",
            )
        except ProviderError as error:
            if _unreachable(self.base_url, error):
                raise self._not_running() from None
            raise

    def applied_params(self) -> dict[str, Any]:
        return {"temperatura": self.temperature, "tokens_max": self.max_tokens, "campo_tokens": "max_tokens",
                "confirmado_pelo_fornecedor": False}

    def available_models(self) -> list[str]:
        try:
            data = _request_json(f"{self.base_url}/api/tags", {}, None, self.timeout)
        except ProviderError as error:
            if _unreachable(self.base_url, error):
                raise self._not_running() from None
            raise
        return _sorted_names(data.get("models", []), "name")


__all__ = [
    "Provider",
    "ProviderError",
    "Reply",
    "Usage",
    "normalize_finish_reason",
    "FakeProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "LocalProvider",
    "GeminiProvider",
    "GoogleProvider",
    "OpenAICompatible",
]
