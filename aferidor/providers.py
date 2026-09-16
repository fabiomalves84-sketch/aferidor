"""Talking to a model under test, behind one narrow interface.

A provider receives a prompt and returns text. It never sees the reference
answer or the acceptance criteria: a bench that shows the model what counts as
correct is not measuring the model, it is measuring the prompt.

No third-party client libraries. The two adapters here speak HTTP directly, so
the bench has no dependency that can change under it between runs.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass

USER_AGENT = "aferidor/0.1"


@dataclass(frozen=True)
class Reply:
    """What a provider got back: the text, and why it stopped.

    `finish_reason` is normalized across vendors to one of "stop" (the model
    finished on its own), "length" (cut off by `max_tokens`), or "unknown"
    (anything else, kept rather than guessed at).
    """

    text: str
    finish_reason: str = "stop"


def normalize_finish_reason(raw: str | None) -> str:
    """Fold every vendor's own vocabulary into "stop", "length" or "unknown".

    OpenAI's chat completions and Ollama's compatible layer say "stop" or
    "length"; Anthropic says "end_turn"/"stop_sequence" or "max_tokens". A
    caller that only needs to know "did the model run out of room" should
    never have to know which vendor it is talking to.
    """
    if raw in ("stop", "end_turn", "stop_sequence"):
        return "stop"
    if raw in ("length", "max_tokens"):
        return "length"
    return "unknown"


class ProviderError(RuntimeError):
    """A call to a model failed.

    `retryable` separates a transient condition (rate limit, timeout, server
    error) from a permanent one (bad key, unknown model). Retrying a permanent
    failure ten times just wastes the run.
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class Provider(ABC):
    """One model under test.

    `name` is written to every answer, so it must identify the model precisely
    enough to compare two runs months apart.
    """

    name: str

    @abstractmethod
    def ask(self, prompt: str) -> Reply:
        """Send one prompt and return the reply, text and finish reason."""

    def available_models(self) -> list[str]:
        """Model identifiers this provider currently offers.

        Asked of the provider rather than written down. A list of model names in
        documentation is wrong within months, and a bench that points at a
        retired model fails for a reason that has nothing to do with the bench.
        """
        raise ProviderError(f"{self.name} nao sabe listar modelos")


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


def _request_json(
    url: str, headers: dict[str, str], payload: dict | None, timeout: float
) -> dict:
    """Call an endpoint and return the decoded reply, classifying every failure."""
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
        try:
            detail = error.read().decode("utf-8", "replace")[:400]
        finally:
            error.close()
        raise ProviderError(
            f"{url} respondeu {error.code}: {detail}",
            retryable=error.code == 429 or error.code >= 500,
        ) from None
    except urllib.error.URLError as error:
        raise ProviderError(f"{url} inacessivel: {error.reason}", retryable=True) from None
    except TimeoutError:
        raise ProviderError(f"{url} excedeu {timeout}s", retryable=True) from None
    except json.JSONDecodeError:
        raise ProviderError(f"{url} devolveu algo que nao e JSON", retryable=True) from None


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    return _request_json(url, headers, payload, timeout)


def _key_from_env(variable: str, given: str | None) -> str:
    key = given or os.environ.get(variable, "")
    if not key.strip():
        raise ProviderError(
            f"falta a chave de API: define {variable} no ambiente ou passa-a ao construtor"
        )
    return key.strip()


def _chat_completion(
    endpoint: str,
    headers: dict[str, str],
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    who: str,
) -> Reply:
    """One call to any endpoint that speaks the OpenAI chat completions shape.

    OpenAI's own API and Ollama's compatibility layer both take this payload
    and answer with the same `choices[0].message.content` shape, so the two
    providers that talk to them share this instead of each repeating it.
    """
    data = _post_json(
        endpoint,
        headers,
        {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout,
    )
    try:
        choice = data["choices"][0]
        text = choice["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise ProviderError(f"resposta {who} sem texto: {str(data)[:300]}") from None
    return Reply(text=text, finish_reason=normalize_finish_reason(choice.get("finish_reason")))


class OpenAIProvider(Provider):
    """OpenAI chat completions."""

    ENDPOINT = "https://api.openai.com/v1/chat/completions"
    ENV_KEY = "OPENAI_API_KEY"

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 60.0,
    ) -> None:
        self.name = f"openai:{model}"
        self.model = model
        self.api_key = _key_from_env(self.ENV_KEY, api_key)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def ask(self, prompt: str) -> Reply:
        return _chat_completion(
            self.ENDPOINT,
            {"authorization": f"Bearer {self.api_key}"},
            self.model,
            prompt,
            self.temperature,
            self.max_tokens,
            self.timeout,
            "da OpenAI",
        )

    def available_models(self) -> list[str]:
        data = _request_json(
            "https://api.openai.com/v1/models",
            {"authorization": f"Bearer {self.api_key}"},
            None,
            self.timeout,
        )
        return sorted(str(m.get("id", "")) for m in data.get("data", []) if m.get("id"))


class AnthropicProvider(Provider):
    """Anthropic messages."""

    ENDPOINT = "https://api.anthropic.com/v1/messages"
    ENV_KEY = "ANTHROPIC_API_KEY"
    VERSION = "2023-06-01"

    def __init__(
        self,
        model: str = "claude-sonnet-4-5",
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 60.0,
    ) -> None:
        self.name = f"anthropic:{model}"
        self.model = model
        self.api_key = _key_from_env(self.ENV_KEY, api_key)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def ask(self, prompt: str) -> Reply:
        data = _post_json(
            self.ENDPOINT,
            {"x-api-key": self.api_key, "anthropic-version": self.VERSION},
            {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            self.timeout,
        )
        try:
            blocks = data["content"]
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (KeyError, TypeError):
            raise ProviderError(f"resposta da Anthropic sem texto: {str(data)[:300]}") from None
        return Reply(text=text, finish_reason=normalize_finish_reason(data.get("stop_reason")))

    def available_models(self) -> list[str]:
        data = _request_json(
            "https://api.anthropic.com/v1/models?limit=100",
            {"x-api-key": self.api_key, "anthropic-version": self.VERSION},
            None,
            self.timeout,
        )
        return sorted(str(m.get("id", "")) for m in data.get("data", []) if m.get("id"))


def _unreachable(base_url: str, error: ProviderError) -> bool:
    """Whether `error` looks like the Ollama server itself is not running.

    `_request_json` marks a `URLError` (connection refused, name not resolved,
    ...) retryable and folds its message with "inacessivel". Retrying that
    against a local server that is simply not started wastes every attempt on
    the same failure, so it is turned into one clear, non-retryable message.
    """
    return "inacessivel" in str(error)


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
            f"o Ollama nao responde em {self.base_url}; esta instalado e aberto?",
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

    def available_models(self) -> list[str]:
        try:
            data = _request_json(f"{self.base_url}/api/tags", {}, None, self.timeout)
        except ProviderError as error:
            if _unreachable(self.base_url, error):
                raise self._not_running() from None
            raise
        return sorted(str(m.get("name", "")) for m in data.get("models", []) if m.get("name"))


__all__ = [
    "Provider",
    "ProviderError",
    "Reply",
    "normalize_finish_reason",
    "FakeProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "LocalProvider",
]
