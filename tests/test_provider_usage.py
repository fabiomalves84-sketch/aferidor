"""What a provider says about a call besides the text: the model that served it, the tokens it
counted, and how long the server asked to wait. None of it changes how a reply is read, run or graded."""

from __future__ import annotations

import tests  # noqa: F401  (a importação fixa a raiz das chaves numa pasta vazia)
import io
import json
import socket
import unittest
import urllib.error
from unittest import mock

from aferidor.models import Case, Criterion, Source
from aferidor.providers import (
    AnthropicProvider,
    FakeProvider,
    GeminiProvider,
    LocalProvider,
    OpenAIProvider,
    Provider,
    ProviderError,
    Reply,
    Usage,
)
from aferidor.risk import FailureType
from aferidor.runner import RunConfig, run
from tests.test_providers_http import FakeResponse, replying

URLOPEN = "aferidor.providers.urllib.request.urlopen"


def setUpModule() -> None:
    """These tests talk to no server: a real connection attempt is a failure, not a slow test."""
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def chat(content: str = "x", **extra) -> dict:
    return {"choices": [{"message": {"content": content}, "finish_reason": "stop"}], **extra}


def http_error(code: int, headers: dict | None = None) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://exemplo", code, "erro", headers or {}, io.BytesIO(b"detalhe"))


class TestWhatWasServedAndCounted(unittest.TestCase):
    def test_openai_reports_the_served_model_and_the_reasoning_tokens_apart(self):
        payload = chat(
            model="modelo-servido-2026-10-01",
            usage={"prompt_tokens": 150, "completion_tokens": 900, "completion_tokens_details": {"reasoning_tokens": 600}},
        )
        with mock.patch(URLOPEN, replying(payload)):
            reply = OpenAIProvider(model="alias", api_key="k").ask("p")
        self.assertEqual(reply.served_model, "modelo-servido-2026-10-01")
        self.assertEqual(reply.usage, Usage(input_tokens=150, output_tokens=900, reasoning_tokens=600))

    def test_a_reply_that_says_nothing_about_either_has_neither(self):
        with mock.patch(URLOPEN, replying(chat())):
            reply = OpenAIProvider(model="m", api_key="k").ask("p")
        self.assertEqual(reply.served_model, "")
        self.assertIsNone(reply.usage)

    def test_a_figure_that_is_not_a_plain_count_is_dropped_and_never_turned_into_zero(self):
        payload = chat(usage={"prompt_tokens": "150", "completion_tokens": -3, "completion_tokens_details": {"reasoning_tokens": True}})
        with mock.patch(URLOPEN, replying(payload)):
            reply = OpenAIProvider(model="m", api_key="k").ask("p")
        self.assertIsNone(reply.usage)
        payload = chat(usage={"prompt_tokens": 150, "completion_tokens": None})
        with mock.patch(URLOPEN, replying(payload)):
            reply = OpenAIProvider(model="m", api_key="k").ask("p")
        self.assertEqual(reply.usage, Usage(input_tokens=150))

    def test_a_usage_object_of_the_wrong_type_is_ignored(self):
        for odd in ("muitos", 12, ["a"], None):
            with self.subTest(usage=odd), mock.patch(URLOPEN, replying(chat(usage=odd, model=["x"]))):
                reply = OpenAIProvider(model="m", api_key="k").ask("p")
                self.assertIsNone(reply.usage)
                self.assertEqual(reply.served_model, "")

    def test_anthropic_reports_input_and_output_and_leaves_reasoning_empty(self):
        payload = {
            "model": "claude-servido-x",
            "content": [{"type": "text", "text": "Amoxicilina"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 140, "output_tokens": 700},
        }
        with mock.patch(URLOPEN, replying(payload)):
            reply = AnthropicProvider(model="alias", api_key="k").ask("p")
        self.assertEqual(reply.served_model, "claude-servido-x")
        self.assertEqual(reply.usage, Usage(input_tokens=140, output_tokens=700, reasoning_tokens=None))

    def test_gemini_keeps_both_when_it_takes_the_thoughts_out(self):
        payload = chat("<thought>raciocínio</thought>1 g de 8 em 8 horas", model="gemini-servido",
                       usage={"prompt_tokens": 90, "completion_tokens": 400})
        with mock.patch(URLOPEN, replying(payload)):
            reply = GeminiProvider(model="alias", api_key="k", min_interval_s=0).ask("p")
        self.assertEqual(reply.text, "1 g de 8 em 8 horas")
        self.assertEqual(reply.served_model, "gemini-servido")
        self.assertEqual(reply.usage, Usage(input_tokens=90, output_tokens=400))

    def test_the_local_server_is_read_the_same_way(self):
        payload = chat(model="gemma3:12b", usage={"prompt_tokens": 80, "completion_tokens": 300})
        with mock.patch(URLOPEN, replying(payload)):
            reply = LocalProvider(model="gemma3:12b").ask("p")
        self.assertEqual((reply.served_model, reply.usage), ("gemma3:12b", Usage(80, 300, None)))

    def test_the_new_fields_do_not_change_what_a_reply_is(self):
        reply = Reply("texto")
        self.assertEqual((reply.text, reply.finish_reason, reply.served_model, reply.usage), ("texto", "stop", "", None))
        self.assertIsNone(FakeProvider().ask("p").usage)


class TestWhenTheServerSaysToWait(unittest.TestCase):
    def ask_failing(self, error) -> ProviderError:
        with mock.patch(URLOPEN, mock.MagicMock(side_effect=error)):
            with self.assertRaises(ProviderError) as caught:
                OpenAIProvider(model="m", api_key="k").ask("p")
        return caught.exception

    def test_a_rate_limit_carries_the_seconds_the_server_asked_for(self):
        error = self.ask_failing(http_error(429, {"Retry-After": "7"}))
        self.assertTrue(error.retryable)
        self.assertEqual(error.retry_after, 7.0)

    def test_a_server_error_can_carry_it_too(self):
        self.assertEqual(self.ask_failing(http_error(503, {"Retry-After": "2.5"})).retry_after, 2.5)

    def test_a_date_a_negative_or_absurd_number_or_nothing_is_none(self):
        for header in ("Wed, 21 Oct 2026 07:28:00 GMT", "-5", "999999", "", "abc"):
            with self.subTest(header=header):
                self.assertIsNone(self.ask_failing(http_error(429, {"Retry-After": header})).retry_after)
        self.assertIsNone(self.ask_failing(http_error(429)).retry_after)

    def test_it_changes_nothing_about_which_failures_are_retried(self):
        self.assertFalse(self.ask_failing(http_error(401, {"Retry-After": "7"})).retryable)
        self.assertTrue(self.ask_failing(urllib.error.URLError("sem rede")).retryable)
        self.assertIsNone(self.ask_failing(urllib.error.URLError("sem rede")).retry_after)

    def test_an_error_built_the_old_way_still_works(self):
        error = ProviderError("falha", retryable=True)
        self.assertEqual((error.retryable, error.retry_after), (True, None))


class TestTheKeyTravelsOnlyInAHeader(unittest.TestCase):
    KEY = "chave-de-teste-123456"

    def sent(self, provider: Provider, payload: dict) -> tuple[str, bytes, dict]:
        captured = {}

        def fake(request, timeout):
            captured["url"], captured["body"] = request.full_url, request.data
            captured["headers"] = {k.lower(): v for k, v in request.header_items()}
            return FakeResponse(json.dumps(payload).encode())

        with mock.patch(URLOPEN, fake):
            provider.ask("p")
        return captured["url"], captured["body"], captured["headers"]

    def test_never_in_the_url_nor_in_the_body(self):
        cases = (
            (OpenAIProvider(model="m", api_key=self.KEY), chat(), "authorization"),
            (AnthropicProvider(model="m", api_key=self.KEY), {"content": [{"type": "text", "text": "x"}]}, "x-api-key"),
            (GeminiProvider(model="m", api_key=self.KEY, min_interval_s=0), chat(), "authorization"),
        )
        for provider, payload, header in cases:
            with self.subTest(fornecedor=provider.name):
                url, body, headers = self.sent(provider, payload)
                self.assertNotIn(self.KEY, url)
                self.assertNotIn(self.KEY.encode(), body)
                self.assertIn(self.KEY, headers[header])


class TestTheRunnerIsNotChanged(unittest.TestCase):
    def test_a_run_with_usage_and_served_model_writes_the_same_answers(self):
        class Counting(FakeProvider):
            def ask(self, prompt: str) -> Reply:
                plain = super().ask(prompt)
                return Reply(plain.text, plain.finish_reason, served_model="servido", usage=Usage(10, 20, 5))

        case = Case(
            case_id="C1", category="dose", question="Que dose?", reference="Amoxicilina 1 g",
            source=Source(name="Guia", reference="p. 1"),
            criteria=(Criterion(kind="contem", terms=("1 g",), failure=FailureType.DOSE_INCORRETA),),
        )
        plain = run([case], FakeProvider(default="1 g"), config=RunConfig(attempts=1))
        extra = run([case], Counting(default="1 g"), config=RunConfig(attempts=1))
        strip = lambda r: [(a.case_id, a.model, a.text, a.sample, a.temperature, a.finish_reason, a.prompt_sha256) for a in r.answers]
        self.assertEqual(strip(plain), strip(extra))
        self.assertEqual(plain.errors, extra.errors)


if __name__ == "__main__":
    unittest.main()
