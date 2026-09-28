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

import http.client
import io
import json
import unittest
import urllib.error
from unittest import mock

from aferidor.providers import (
    AnthropicProvider,
    GeminiProvider,
    LocalProvider,
    OpenAIProvider,
    ProviderError,
)


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

    def test_a_connection_reset_mid_read_is_retryable(self):
        self.assertTrue(self.ask_with(failing(ConnectionResetError("ligacao fechada"))).retryable)

    def test_the_server_hanging_up_mid_read_is_retryable(self):
        self.assertTrue(
            self.ask_with(failing(http.client.RemoteDisconnected("sem resposta"))).retryable
        )


class TestOpenAIReplies(unittest.TestCase):
    def test_the_text_is_taken_from_the_first_choice(self):
        provider = OpenAIProvider(model="m", api_key="k")
        payload = {"choices": [{"message": {"content": "1000 mg de 8 em 8 horas"}}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p").text, "1000 mg de 8 em 8 horas")

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
            self.assertEqual(provider.ask("p").text, "")

    def test_listing_models_returns_them_sorted(self):
        provider = OpenAIProvider(model="m", api_key="k")
        payload = {"data": [{"id": "zeta"}, {"id": "alfa"}, {"sem": "id"}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.available_models(), ["alfa", "zeta"])

    def test_a_finish_reason_of_stop_is_normalized(self):
        provider = OpenAIProvider(model="m", api_key="k")
        payload = {"choices": [{"message": {"content": "x"}, "finish_reason": "stop"}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p").finish_reason, "stop")

    def test_a_finish_reason_of_length_is_normalized(self):
        provider = OpenAIProvider(model="m", api_key="k")
        payload = {"choices": [{"message": {"content": "a meio"}, "finish_reason": "length"}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p").finish_reason, "length")

    def test_an_unrecognised_finish_reason_is_unknown(self):
        provider = OpenAIProvider(model="m", api_key="k")
        payload = {"choices": [{"message": {"content": "x"}, "finish_reason": "tool_calls"}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p").finish_reason, "unknown")

    def test_the_token_limit_is_sent_as_max_completion_tokens(self):
        """OpenAI's reasoning models (o1, o3, gpt-5, ...) reject `max_tokens`
        outright with a 400; `max_completion_tokens` is what they accept."""
        provider = OpenAIProvider(model="o3", api_key="k", max_tokens=2048)
        captured = {}

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode())
            return FakeResponse(
                json.dumps({"choices": [{"message": {"content": "x"}}]}).encode()
            )

        with mock.patch("aferidor.providers.urllib.request.urlopen", fake_urlopen):
            provider.ask("p")
        self.assertEqual(captured["body"]["max_completion_tokens"], 2048)
        self.assertNotIn("max_tokens", captured["body"])


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
            self.assertEqual(provider.ask("p").text, "Amoxicilina 1000 mg")

    def test_a_stop_reason_of_max_tokens_is_normalized_to_length(self):
        provider = AnthropicProvider(model="m", api_key="k")
        payload = {"content": [{"type": "text", "text": "a meio"}], "stop_reason": "max_tokens"}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p").finish_reason, "length")

    def test_a_stop_reason_of_end_turn_is_normalized_to_stop(self):
        provider = AnthropicProvider(model="m", api_key="k")
        payload = {"content": [{"type": "text", "text": "x"}], "stop_reason": "end_turn"}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p").finish_reason, "stop")

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


class TestLocalReplies(unittest.TestCase):
    def test_it_speaks_the_same_shape_as_openai(self):
        provider = LocalProvider(model="llama3")
        payload = {"choices": [{"message": {"content": "1000 mg de 8 em 8 horas"}}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.ask("p").text, "1000 mg de 8 em 8 horas")

    def test_no_authorization_header_is_sent(self):
        provider = LocalProvider(model="llama3")
        captured = {}

        def fake_urlopen(request, timeout):
            captured["headers"] = dict(request.header_items())
            return FakeResponse(
                json.dumps({"choices": [{"message": {"content": "x"}}]}).encode()
            )

        with mock.patch("aferidor.providers.urllib.request.urlopen", fake_urlopen):
            provider.ask("p")
        self.assertNotIn("Authorization", captured["headers"])

    def test_the_token_limit_is_still_sent_as_max_tokens(self):
        """Unlike OpenAI, Ollama's compatibility layer only understands
        `max_tokens`; it must not switch to `max_completion_tokens`."""
        provider = LocalProvider(model="llama3", max_tokens=2048)
        captured = {}

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode())
            return FakeResponse(
                json.dumps({"choices": [{"message": {"content": "x"}}]}).encode()
            )

        with mock.patch("aferidor.providers.urllib.request.urlopen", fake_urlopen):
            provider.ask("p")
        self.assertEqual(captured["body"]["max_tokens"], 2048)
        self.assertNotIn("max_completion_tokens", captured["body"])

    def test_listing_models_reads_ollamas_own_tags_endpoint(self):
        provider = LocalProvider(model="llama3")
        payload = {"models": [{"name": "mixtral"}, {"name": "gemma"}, {"sem": "nome"}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(provider.available_models(), ["gemma", "mixtral"])

    def test_the_server_not_running_gets_one_clear_message(self):
        provider = LocalProvider(model="llama3", base_url="http://localhost:11434")
        with mock.patch(
            "aferidor.providers.urllib.request.urlopen",
            failing(urllib.error.URLError("[Errno 61] Connection refused")),
        ):
            with self.assertRaises(ProviderError) as caught:
                provider.ask("p")
        self.assertIn("o Ollama não responde em http://localhost:11434", str(caught.exception))
        self.assertFalse(caught.exception.retryable)

    def test_a_model_error_that_is_not_a_connection_problem_is_not_rewritten(self):
        provider = LocalProvider(model="llama3")
        with mock.patch(
            "aferidor.providers.urllib.request.urlopen",
            failing(http_error(404, "model not found")),
        ):
            with self.assertRaises(ProviderError) as caught:
                provider.ask("p")
        self.assertIn("model not found", str(caught.exception))


class TestGeminiReplies(unittest.TestCase):
    def gemini(self, **kwargs) -> GeminiProvider:
        kwargs.setdefault("min_interval_s", 0.0)
        return GeminiProvider(model="gemini-2.5-flash", api_key="k", **kwargs)

    def test_it_asks_googles_openai_compatible_endpoint_with_the_key(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            return FakeResponse(json.dumps({"choices": [{"message": {"content": "1 g"}}]}).encode())

        with mock.patch("aferidor.providers.urllib.request.urlopen", fake_urlopen):
            self.assertEqual(self.gemini().ask("p").text, "1 g")
        self.assertEqual(
            captured["url"],
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        )
        self.assertEqual(captured["headers"]["Authorization"], "Bearer k")

    def test_the_model_is_named_with_its_provider(self):
        self.assertEqual(self.gemini().name, "gemini:gemini-2.5-flash")

    def test_listing_models_drops_googles_prefix(self):
        payload = {"data": [{"id": "models/gemini-2.5-pro"}, {"id": "models/gemini-2.5-flash"}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", replying(payload)):
            self.assertEqual(self.gemini().available_models(), ["gemini-2.5-flash", "gemini-2.5-pro"])

    def test_requests_are_spaced_to_stay_under_the_free_rate_limit(self):
        """The free tier counts requests per minute; a steady pace avoids the
        rate limit instead of spending retries on it."""
        now = [100.0]
        waits: list[float] = []

        def sleep(seconds):
            waits.append(seconds)
            now[0] += seconds

        provider = self.gemini(min_interval_s=7.0, clock=lambda: now[0], sleep=sleep)
        payload = {"choices": [{"message": {"content": "x"}}]}
        with mock.patch("aferidor.providers.urllib.request.urlopen", side_effect=lambda *a, **k: FakeResponse(json.dumps(payload).encode())):
            provider.ask("p")
            now[0] += 2.0
            provider.ask("p")
            now[0] += 10.0
            provider.ask("p")
        self.assertEqual(waits, [5.0])

    def test_without_a_key_it_says_which_variable_to_set(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ProviderError) as caught:
                GeminiProvider()
        self.assertIn("GEMINI_API_KEY", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
