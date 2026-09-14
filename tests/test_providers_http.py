"""The HTTP layer, without a network.

These adapters are the only code here that talks to the outside world, and the
only code that had never been exercised at all: the earlier provider tests cover
the fake provider and the missing-key error, and stop there. What matters is not
that a request is well formed, it is that every way a call can fail is turned
into the right kind of error. A rate limit retried is a run that finishes; a bad
key retried three times is money and minutes spent on a failure that was never
going to clear.
"""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest import mock

from aferidor.providers import AnthropicProvider, OpenAIProvider, ProviderError


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False


def replying(payload) -> mock.MagicMock:
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return mock.MagicMock(return_value=FakeResponse(body))


def failing(error) -> mock.MagicMock:
    return mock.MagicMock(side_effect=error)


def http_error(code: int, body: str = "detalhe do erro") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://exemplo", code, "erro", {}, io.BytesIO(body.encode())
    )


class TestErrorClassification(unittest.TestCase):
    def ask_with(self, patched) -> ProviderError:
        provider = OpenAIProvider(model="m", api_key="k")
        with mock.patch("aferidor.providers.urllib.request.urlopen", patched):
            with self.assertRaises(ProviderError) as caught:
                provider.ask("pergunta")
        return caught.exception

    def test_a_rate_limit_is_retryable(self):
        self.assertTrue(self.ask_with(failing(http_error(429))).retryable)

    def test_a_server_error_is_retryable(self):
        self.assertTrue(self.ask_with(failing(http_error(503))).retryable)

    def test_a_bad_key_is_not_retryable(self):
        error = self.ask_with(failing(http_error(401, "invalid api key")))
        self.assertFalse(error.retryable)

    def test_an_unknown_model_is_not_retryable(self):
        self.assertFalse(self.ask_with(failing(http_error(404))).retryable)

    def test_a_network_failure_is_retryable(self):
        self.assertTrue(self.ask_with(failing(urllib.error.URLError("sem rede"))).retryable)

    def test_a_reply_that_is_not_json_is_retryable(self):
        self.assertTrue(self.ask_with(replying(b"<html>manutencao</html>")).retryable)

    def test_the_error_says_what_the_server_answered(self):
        self.assertIn("invalid api key", str(self.ask_with(failing(http_error(401, "invalid api key")))))


class TestOpenAIReplies(unittest.TestCase):
    def test_the_text_is_taken_from_the_first_choice(self):
        provider = OpenAIProvider(model="m", api_key="k")
        payload = {"choices": [{"message": {"content": "1000 mg de 8 em 8 horas"}}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p"), "1000 mg de 8 em 8 horas")

    def test_a_reply_without_text_is_an_error_and_shows_what_came(self):
        provider = OpenAIProvider(model="m", api_key="k")
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying({"erro": "x"})):
            with self.assertRaises(ProviderError) as caught:
                provider.ask("p")
        self.assertIn("erro", str(caught.exception))

    def test_an_empty_content_becomes_an_empty_string_not_a_crash(self):
        provider = OpenAIProvider(model="m", api_key="k")
        payload = {"choices": [{"message": {"content": None}}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p"), "")

    def test_listing_models_returns_them_sorted(self):
        provider = OpenAIProvider(model="m", api_key="k")
        payload = {"data": [{"id": "zeta"}, {"id": "alfa"}, {"sem": "id"}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.available_models(), ["alfa", "zeta"])


class TestAnthropicReplies(unittest.TestCase):
    def test_text_blocks_are_joined_and_other_blocks_ignored(self):
        provider = AnthropicProvider(model="m", api_key="k")
        payload = {
            "content": [
                {"type": "text", "text": "Amoxicilina "},
                {"type": "thinking", "text": "IGNORAR"},
                {"type": "text", "text": "1000 mg"},
            ]
        }
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p"), "Amoxicilina 1000 mg")

    def test_a_reply_without_content_is_an_error(self):
        provider = AnthropicProvider(model="m", api_key="k")
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying({"x": 1})):
            with self.assertRaises(ProviderError):
                provider.ask("p")

    def test_listing_models_returns_them_sorted(self):
        provider = AnthropicProvider(model="m", api_key="k")
        payload = {"data": [{"id": "b"}, {"id": "a"}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.available_models(), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
