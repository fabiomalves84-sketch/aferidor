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

USER_AGENT = "aferidor/0.1"


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
    def ask(self, prompt: str) -> str:
        """Send one prompt and return the reply text."""

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
    the runner's retry path gets exercised without a network.
    """

    def __init__(
        self,
        name: str = "falso",
        replies: dict[str, str] | None = None,
        default: str = "sem resposta",
        failures: int = 0,
    ) -> None:
        self.name = name
        self.replies = dict(replies or {})
        self.default = default
        self.failures = failures
        self.prompts: list[str] = []

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.failures > 0:
            self.failures -= 1
            raise ProviderError("falha simulada", retryable=True)
        for needle, reply in self.replies.items():
            if needle in prompt:
                return reply
        return self.default


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

    def ask(self, prompt: str) -> str:
        data = _post_json(
            self.ENDPOINT,
            {"authorization": f"Bearer {self.api_key}"},
            {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            self.timeout,
        )
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"resposta da OpenAI sem texto: {str(data)[:300]}") from None

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

    def ask(self, prompt: str) -> str:
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
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (KeyError, TypeError):
            raise ProviderError(f"resposta da Anthropic sem texto: {str(data)[:300]}") from None

    def available_models(self) -> list[str]:
        data = _request_json(
            "https://api.anthropic.com/v1/models?limit=100",
            {"x-api-key": self.api_key, "anthropic-version": self.VERSION},
            None,
            self.timeout,
        )
        return sorted(str(m.get("id", "")) for m in data.get("data", []) if m.get("id"))


__all__ = [
    "Provider",
    "ProviderError",
    "FakeProvider",
    "OpenAIProvider",
    "AnthropicProvider",
]
