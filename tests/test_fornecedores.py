"""The providers of the catalogue, read from hand-written replies in the shape of their documentation (see
`tests/fixtures_fornecedores.py`: none of them is a real reply). No network: `urlopen` is replaced by a router."""

from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import tempfile
import time
import unittest
import urllib.error
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import formatdate
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (a importação fixa a raiz das chaves numa pasta vazia)
from aferidor import cli, providers
from aferidor.catalogo import load_catalog
from aferidor.chaves import REPOSITORY_ROOT, Secret
from aferidor.providers import (
    AnthropicProvider,
    GeminiProvider,
    GoogleProvider,
    OpenAICompatible,
    OpenAIProvider,
    ProviderError,
    _retry_after,
    normalize_finish_reason,
)
from aferidor.proveniencia import FILE_NAME, read_records
from aferidor.storage import read_answers
from tests import fixtures_fornecedores as fx
from tests.test_providers_http import FakeResponse

URLOPEN = "aferidor.providers.urllib.request.urlopen"
SENTINEL = "sentinela-falsa-7f3a9c1e5b2d4f60"
ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "casos" / "casos.json"


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


class Net:
    """Stands in for `urlopen`: answers by what the URL contains and keeps what each request carried."""

    def __init__(self, *routes):
        self.routes = [[needle, list(reply) if isinstance(reply, list) else reply] for needle, reply in routes]
        self.requests: list[dict] = []

    def __call__(self, request, timeout):
        body = json.loads(request.data.decode()) if request.data else None
        self.requests.append({"url": request.full_url, "headers": {k.lower(): v for k, v in request.header_items()},
                              "body": body, "timeout": timeout, "method": request.get_method()})
        for needle, reply in self.routes:
            if needle in request.full_url:
                step = reply.pop(0) if isinstance(reply, list) else reply
                if isinstance(step, BaseException):
                    raise step
                return FakeResponse(json.dumps(step).encode())
        raise AssertionError(f"pedido inesperado a {request.full_url}")

    def bodies(self, needle=""):
        return [r["body"] for r in self.requests if needle in r["url"]]


def http_error(code: int, body: object = None, headers: dict | None = None) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://exemplo.test", code, "erro", headers or {},
                                  io.BytesIO(json.dumps(body if body is not None else {"erro": code}).encode()))


def ask(provider, net) -> providers.Reply:
    with mock.patch(URLOPEN, net):
        return provider.ask("pergunta")


class TestAnthropic(unittest.TestCase):
    def provider(self, **kw):
        return AnthropicProvider(model="claude-opus-5-5", api_key="chave-falsa-abcdef", temperature=1.0, max_tokens=8192, **kw)

    def test_the_headers_and_the_body_are_the_documented_ones_and_the_key_is_only_in_a_header(self):
        net = Net(("/v1/messages", fx.ANTHROPIC_OK))
        ask(self.provider(), net)
        (request,) = net.requests
        self.assertEqual(request["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual((request["headers"]["x-api-key"], request["headers"]["anthropic-version"]), ("chave-falsa-abcdef", "2023-06-01"))
        self.assertEqual(request["headers"]["content-type"], "application/json")
        self.assertEqual(sorted(request["body"]), ["max_tokens", "messages", "model", "temperature"])
        self.assertNotIn("chave-falsa-abcdef", request["url"] + json.dumps(request["body"]))

    def test_a_model_that_does_not_take_a_temperature_is_asked_without_one(self):
        net = Net(("/v1/messages", fx.ANTHROPIC_OK))
        provider = self.provider(send_temperature=False)
        ask(provider, net)
        self.assertNotIn("temperature", net.requests[0]["body"])
        self.assertEqual(provider.applied_params()["temperatura"], "ausente")
        self.assertIn("1.0", provider.applied_params()["nota"])
        self.assertFalse(provider.applied_params()["confirmado_pelo_fornecedor"])

    def test_usage_the_served_model_and_the_original_stop_reason_are_read(self):
        reply = ask(self.provider(), Net(("/v1/messages", fx.ANTHROPIC_OK)))
        self.assertEqual((reply.text, reply.served_model), (fx.ANSWER, "claude-opus-5-5"))
        self.assertEqual((reply.usage.input_tokens, reply.usage.output_tokens, reply.usage.reasoning_tokens), (140, 900, 600))
        self.assertEqual((reply.finish_reason, reply.finish_reason_original), ("stop", "end_turn"))

    def test_a_refusal_and_a_cut_reply_keep_the_providers_word(self):
        refused = ask(self.provider(), Net(("/v1/messages", fx.ANTHROPIC_REFUSAL)))
        self.assertEqual((refused.finish_reason, refused.finish_reason_original, refused.text), ("filtered", "refusal", ""))
        cut = ask(self.provider(), Net(("/v1/messages", fx.ANTHROPIC_MAX_TOKENS)))
        self.assertEqual((cut.finish_reason, cut.finish_reason_original), ("length", "max_tokens"))


class TestGoogle(unittest.TestCase):
    def provider(self, **kw):
        return GoogleProvider(model="gemini-3.8-flash", api_key="chave-falsa-abcdef", temperature=1.0, max_tokens=8192,
                              min_interval_s=0, **kw)

    def test_the_request_goes_to_the_model_with_the_key_in_a_header_and_never_in_the_url(self):
        net = Net((":generateContent", fx.GOOGLE_OK))
        ask(self.provider(), net)
        (request,) = net.requests
        self.assertEqual(request["url"], "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent")
        self.assertEqual(request["headers"]["x-goog-api-key"], "chave-falsa-abcdef")
        self.assertNotIn("key=", request["url"])
        self.assertEqual(request["body"]["contents"], [{"role": "user", "parts": [{"text": "pergunta"}]}])
        self.assertEqual(request["body"]["generationConfig"], {"temperature": 1.0, "maxOutputTokens": 8192})

    def test_the_temperature_can_be_left_out(self):
        net = Net((":generateContent", fx.GOOGLE_OK))
        provider = self.provider(send_temperature=False)
        ask(provider, net)
        self.assertEqual(net.requests[0]["body"]["generationConfig"], {"maxOutputTokens": 8192})
        self.assertEqual(provider.applied_params()["temperatura"], "ausente")

    def test_the_tokens_including_the_thinking_ones_the_model_version_and_the_finish_reason_are_read(self):
        reply = ask(self.provider(), Net((":generateContent", fx.GOOGLE_OK)))
        self.assertEqual((reply.text, reply.served_model), (fx.ANSWER, "gemini-3.8-flash"))
        self.assertEqual((reply.usage.input_tokens, reply.usage.output_tokens, reply.usage.reasoning_tokens), (130, 700, 450))
        self.assertEqual((reply.finish_reason, reply.finish_reason_original), ("stop", "STOP"))

    def test_the_finish_reasons_of_google_are_folded_without_guessing(self):
        for raw, normalized in (("STOP", "stop"), ("MAX_TOKENS", "length"), ("SAFETY", "filtered"), ("RECITATION", "filtered"),
                                ("PROHIBITED_CONTENT", "filtered"), ("OTHER", "unknown"), ("MALFORMED_FUNCTION_CALL", "unknown")):
            self.assertEqual(normalize_finish_reason(raw), normalized, raw)
        cut = ask(self.provider(), Net((":generateContent", fx.GOOGLE_MAX_TOKENS)))
        self.assertEqual((cut.finish_reason, cut.finish_reason_original, cut.text), ("length", "MAX_TOKENS", "Amoxi"))
        safety = ask(self.provider(), Net((":generateContent", fx.GOOGLE_SAFETY)))
        self.assertEqual((safety.finish_reason, safety.finish_reason_original, safety.text), ("filtered", "SAFETY", ""))

    def test_a_blocked_prompt_is_a_filtered_reply_that_says_why(self):
        reply = ask(self.provider(), Net((":generateContent", fx.GOOGLE_BLOCKED_PROMPT)))
        self.assertEqual((reply.text, reply.finish_reason, reply.finish_reason_original), ("", "filtered", "SAFETY"))
        self.assertEqual(reply.usage.input_tokens, 130)

    def test_parts_flagged_as_thoughts_are_not_part_of_the_answer(self):
        reply = ask(self.provider(), Net((":generateContent", fx.GOOGLE_WITH_THOUGHT_PARTS)))
        self.assertEqual(reply.text, fx.ANSWER)

    def test_a_reply_with_no_candidates_and_no_block_is_an_error_that_shows_what_came(self):
        with self.assertRaisesRegex(ProviderError, "sem candidatos"):
            ask(self.provider(), Net((":generateContent", {"outro": 1})))

    def test_the_models_are_listed_by_name_without_the_prefix(self):
        with mock.patch(URLOPEN, Net(("/v1beta/models", fx.GOOGLE_MODELS))):
            self.assertEqual(self.provider().available_models(), ["gemini-3.1-pro-preview", "gemini-3.8-flash"])

    def test_it_waits_between_requests_like_the_other_gemini_provider(self):
        slept = []
        clock = iter([0.0, 1.0, 1.0, 1.0])
        provider = GoogleProvider(model="m", api_key="k", min_interval_s=13, clock=lambda: next(clock), sleep=slept.append)
        net = Net((":generateContent", fx.GOOGLE_OK))
        ask(provider, net)
        ask(provider, net)
        self.assertEqual(slept, [12.0])


class TestTheCompatibleServer(unittest.TestCase):
    def provider(self, **kw):
        return OpenAICompatible(model="AMALIA-9B-0626-DPO", base_url="http://127.0.0.1:8000/v1/", temperature=1.0,
                                max_tokens=4096, **kw)

    def test_the_calls_go_under_the_base_url_and_without_a_key_there_is_no_authorization(self):
        net = Net(("/chat/completions", fx.VLLM_CHAT))
        ask(self.provider(), net)
        (request,) = net.requests
        self.assertEqual(request["url"], "http://127.0.0.1:8000/v1/chat/completions")
        self.assertNotIn("authorization", request["headers"])
        self.assertEqual(request["body"]["max_tokens"], 4096)
        self.assertEqual(request["body"]["temperature"], 1.0)

    def test_with_a_key_it_is_a_bearer_header_only(self):
        net = Net(("/chat/completions", fx.VLLM_CHAT))
        ask(self.provider(api_key="chave-falsa-abcdef"), net)
        self.assertEqual(net.requests[0]["headers"]["authorization"], "Bearer chave-falsa-abcdef")

    def test_the_token_field_and_the_temperature_follow_what_the_server_takes(self):
        net = Net(("/chat/completions", fx.VLLM_CHAT))
        provider = self.provider(tokens_param="max_completion_tokens", send_temperature=False)
        ask(provider, net)
        self.assertEqual(sorted(net.requests[0]["body"]), ["max_completion_tokens", "messages", "model"])
        self.assertEqual(provider.applied_params(), {"temperatura": "ausente", "tokens_max": 4096,
                                                     "campo_tokens": "max_completion_tokens", "confirmado_pelo_fornecedor": False})

    def test_usage_and_the_served_model_are_read_from_the_reply(self):
        reply = ask(self.provider(), Net(("/chat/completions", fx.VLLM_CHAT)))
        self.assertEqual((reply.served_model, reply.usage.input_tokens, reply.usage.output_tokens), ("AMALIA-9B-0626-DPO", 125, 400))
        self.assertEqual((reply.finish_reason, reply.finish_reason_original), ("stop", "stop"))

    def test_the_models_loaded_are_asked_and_the_one_wanted_must_be_among_them(self):
        provider = self.provider()
        net = Net(("/models", fx.VLLM_MODELS), ("/chat/completions", {**fx.VLLM_CHAT, "model": None}))
        with mock.patch(URLOPEN, net):
            self.assertEqual(provider.confirm_model(), "AMALIA-9B-0626-DPO")
            reply = provider.ask("pergunta")
        self.assertEqual(net.requests[0]["url"], "http://127.0.0.1:8000/v1/models")
        self.assertEqual(reply.served_model, "AMALIA-9B-0626-DPO")  # the id the server listed, when the reply gives none

    def test_a_server_with_another_model_loaded_is_refused_with_what_it_has(self):
        with mock.patch(URLOPEN, Net(("/models", fx.VLLM_OTHER_MODELS))), self.assertRaisesRegex(ProviderError, "tem: outro-modelo.*served-model-name"):
            self.provider().confirm_model()

    def test_the_reply_own_model_wins_over_the_listing(self):
        provider = self.provider()
        net = Net(("/models", fx.VLLM_MODELS), ("/chat/completions", {**fx.VLLM_CHAT, "model": "AMALIA-9B-0626-DPO-snapshot"}))
        with mock.patch(URLOPEN, net):
            provider.confirm_model()
            self.assertEqual(provider.ask("p").served_model, "AMALIA-9B-0626-DPO-snapshot")

    def test_openai_itself_is_this_class_with_its_own_base_url_and_token_field(self):
        net = Net(("/chat/completions", fx.OPENAI_OK))
        provider = OpenAIProvider(model="gpt-6-astra", api_key="chave-falsa-abcdef", temperature=1.0, max_tokens=8192)
        reply = ask(provider, net)
        self.assertEqual(net.requests[0]["url"], "https://api.openai.com/v1/chat/completions")
        self.assertIn("max_completion_tokens", net.requests[0]["body"])
        self.assertEqual((reply.usage.reasoning_tokens, reply.served_model), (500, "gpt-6-astra"))
        filtered = ask(provider, Net(("/chat/completions", fx.OPENAI_FILTERED)))
        self.assertEqual((filtered.finish_reason, filtered.finish_reason_original), ("filtered", "content_filter"))


class TestWhatGoesWrong(unittest.TestCase):
    PROVIDERS = {
        "anthropic": (lambda: AnthropicProvider(model="m", api_key=SENTINEL, max_tokens=10), "/v1/messages"),
        "google": (lambda: GoogleProvider(model="m", api_key=SENTINEL, max_tokens=10, min_interval_s=0), ":generateContent"),
        "openai": (lambda: OpenAIProvider(model="m", api_key=SENTINEL, max_tokens=10), "/chat/completions"),
        "compativel": (lambda: OpenAICompatible(model="m", base_url="http://127.0.0.1:8000/v1", api_key=SENTINEL), "/chat/completions"),
    }

    def failing(self, name, error):
        make, needle = self.PROVIDERS[name]
        with mock.patch(URLOPEN, Net((needle, error))), self.assertRaises(ProviderError) as caught:
            make().ask("p")
        return caught.exception

    def test_authentication_and_permission_errors_are_final_and_certainly_not_billed(self):
        for name in self.PROVIDERS:
            for code in (401, 403):
                with self.subTest(fornecedor=name, estado=code):
                    error = self.failing(name, http_error(code, fx.ANTHROPIC_ERROR))
                    self.assertEqual((error.retryable, error.maybe_billed, error.retry_after), (False, False, None))

    def test_a_rate_limit_and_the_server_errors_are_retried_and_unbilled(self):
        for name in self.PROVIDERS:
            for code in (429, 500, 503, 529):
                with self.subTest(fornecedor=name, estado=code):
                    error = self.failing(name, http_error(code, fx.ANTHROPIC_ERROR))
                    self.assertEqual((error.retryable, error.maybe_billed), (True, False))

    def test_retry_after_in_seconds_is_read(self):
        for name in self.PROVIDERS:
            with self.subTest(fornecedor=name):
                self.assertEqual(self.failing(name, http_error(429, headers={"Retry-After": "7"})).retry_after, 7.0)

    def test_retry_after_as_a_date_is_the_seconds_until_then(self):
        later = formatdate(time.time() + 30, usegmt=True)
        for name in self.PROVIDERS:
            with self.subTest(fornecedor=name):
                waited = self.failing(name, http_error(429, headers={"Retry-After": later})).retry_after
                self.assertTrue(27 <= waited <= 30, waited)

    def test_the_two_forms_of_retry_after_with_a_fixed_clock(self):
        now = lambda: datetime(2026, 10, 21, 7, 27, 0, tzinfo=timezone.utc)
        self.assertEqual(_retry_after("Wed, 21 Oct 2026 07:28:00 GMT", now), 60.0)
        self.assertEqual(_retry_after("120", now), 120.0)
        for bad in ("Wed, 21 Oct 2026 07:26:00 GMT", "Thu, 22 Oct 2026 07:28:01 GMT", "-5", "", "amanhã", None):
            self.assertIsNone(_retry_after(bad, now), bad)

    def test_a_timeout_a_cut_connection_and_a_body_that_is_not_json_may_have_been_billed(self):
        import http.client
        for name in self.PROVIDERS:
            for error in (TimeoutError(), http.client.RemoteDisconnected("cortada")):
                with self.subTest(fornecedor=name, erro=type(error).__name__):
                    failure = self.failing(name, error)
                    self.assertEqual((failure.retryable, failure.maybe_billed), (True, True))

    def test_a_reply_with_no_text_where_the_text_belongs_is_an_error_that_shows_what_came(self):
        for name in ("anthropic", "openai", "compativel"):
            with self.subTest(fornecedor=name):
                self.assertIn("sem texto", str(self.failing(name, {"inesperado": True})))

    def test_an_error_body_that_echoes_the_key_does_not_carry_it_into_the_message(self):
        for name in self.PROVIDERS:
            with self.subTest(fornecedor=name):
                error = self.failing(name, http_error(401, {"error": {"message": f"Incorrect API key provided: {SENTINEL}"}}))
                self.assertNotIn(SENTINEL, str(error) + repr(error) + repr(error.args))
                self.assertIn("<chave omitida>", str(error))

    def test_a_connection_error_that_names_the_key_does_not_carry_it_either(self):
        for name in self.PROVIDERS:
            with self.subTest(fornecedor=name):
                error = self.failing(name, urllib.error.URLError(f"falhou com {SENTINEL}"))
                self.assertNotIn(SENTINEL, str(error))


class TestTheKeys(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.root = Path(self._dir.name)
        patcher = mock.patch.object(providers, "KEYS_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def env(self, **values):
        return mock.patch.dict(os.environ, values, clear=True)

    def test_the_environment_comes_first_then_the_env_file_of_the_repository(self):
        (self.root / ".env").write_text(f"OPENAI_API_KEY={SENTINEL}-do-ficheiro\n", encoding="utf-8")
        with self.env(OPENAI_API_KEY=f"{SENTINEL}-do-ambiente"):
            self.assertEqual(OpenAIProvider(model="m").api_key.reveal(), f"{SENTINEL}-do-ambiente")
        with self.env():
            self.assertEqual(OpenAIProvider(model="m").api_key.reveal(), f"{SENTINEL}-do-ficheiro")

    def test_every_provider_reads_its_own_variable_from_it(self):
        (self.root / ".env").write_text(f"ANTHROPIC_API_KEY={SENTINEL}-a\nGEMINI_API_KEY={SENTINEL}-g\n", encoding="utf-8")
        with self.env():
            self.assertEqual(AnthropicProvider(model="m").api_key.reveal(), f"{SENTINEL}-a")
            self.assertEqual(GoogleProvider(model="m").api_key.reveal(), f"{SENTINEL}-g")
            self.assertEqual(GeminiProvider(model="m").api_key.reveal(), f"{SENTINEL}-g")

    def test_a_missing_key_says_which_variable_and_never_a_value(self):
        (self.root / ".env").write_text(f"OUTRA={SENTINEL}\n", encoding="utf-8")
        with self.env(), self.assertRaises(ProviderError) as caught:
            OpenAIProvider(model="m")
        self.assertIn("OPENAI_API_KEY", str(caught.exception))
        self.assertNotIn(SENTINEL, str(caught.exception))

    def test_only_the_variable_the_provider_asks_for_is_read_from_the_file(self):
        (self.root / ".env").write_text(f"ANTHROPIC_API_KEY={SENTINEL}\n", encoding="utf-8")
        with self.env(), self.assertRaises(ProviderError):
            OpenAIProvider(model="m")

    def test_a_key_in_a_provider_does_not_print(self):
        with self.env(OPENAI_API_KEY=SENTINEL):
            provider = OpenAIProvider(model="m")
        for text in (repr(provider.api_key), str(provider.api_key), repr(vars(provider)), repr(provider.applied_params())):
            self.assertNotIn(SENTINEL, text)
        self.assertIsInstance(provider.api_key, Secret)

    def test_the_variables_the_providers_use_are_the_ones_the_catalogue_declares(self):
        declared = load_catalog().key_variables()
        for cls in (OpenAIProvider, AnthropicProvider, GeminiProvider, GoogleProvider):
            self.assertIn(cls.ENV_KEY, declared, cls.__name__)

    def test_the_env_file_is_ignored_by_git_and_no_test_can_reach_the_real_one(self):
        ignored = [line.strip() for line in (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()]
        self.assertIn(".env", ignored)
        with mock.patch.object(providers, "KEYS_ROOT", tests.providers.KEYS_ROOT):
            self.assertNotEqual(providers.KEYS_ROOT, REPOSITORY_ROOT)


class WithTheCommandLine(unittest.TestCase):
    ENV = {"ANTHROPIC_API_KEY": SENTINEL, "OPENAI_API_KEY": SENTINEL, "GEMINI_API_KEY": SENTINEL, "AFERIDOR_GEMINI_INTERVALO": "0"}

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.folder = Path(self._dir.name)
        self.saida = self.folder / "ensaio" / "respostas.jsonl"

    def main(self, net, *argv, env=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch(URLOPEN, net), mock.patch.dict(os.environ, self.ENV if env is None else env, clear=True), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def run_cli(self, net, fornecedor, modelo, *extra, limit="2", env=None):
        return self.main(net, "executar", "--fornecedor", fornecedor, "--modelo", modelo, "--casos", str(CASES), "--saida", str(self.saida),
                         "--limite", limit, "--tokens-max", "8192", "--temperatura", "1.0", *extra, env=env)

    def everything_written(self) -> str:
        return "".join(p.read_text(encoding="utf-8") for p in self.folder.rglob("*") if p.is_file())


class TestTheCatalogueModelsFromTheCommandLine(WithTheCommandLine):
    def test_anthropic_runs_without_a_temperature_and_the_provenance_says_asked_one_applied_absent(self):
        net = Net(("/v1/messages", fx.ANTHROPIC_OK))
        code, out, err = self.run_cli(net, "anthropic", "claude-opus-5-5", "--teto-eur", "100")
        self.assertEqual(code, 0, err)
        self.assertTrue(all("temperature" not in body for body in net.bodies()))
        lines = read_records(self.saida.with_name(FILE_NAME))
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(line.requested_params["temperatura"], 1.0)
            self.assertEqual((line.applied_params["temperatura"], line.applied_params["confirmado_pelo_fornecedor"]), ("ausente", False))
            self.assertEqual((line.served_model, line.served_check, line.finish_reason_original), ("claude-opus-5-5", "igual", "end_turn"))
            self.assertEqual((line.input_tokens, line.output_tokens, line.reasoning_tokens), (140, 900, 600))

    def test_anthropic_is_counted_by_its_usage_because_the_catalogue_says_how_thinking_is_counted(self):
        self.run_cli(Net(("/v1/messages", fx.ANTHROPIC_OK)), "anthropic", "claude-opus-5-5", "--teto-eur", "100")
        (first, _) = read_records(self.saida.with_name(FILE_NAME))
        self.assertEqual(first.count_mode, "usage")
        self.assertEqual(first.cost_usd, (Decimal(140) * 4 + Decimal(900) * 20) / 1_000_000)

    def test_a_temperature_the_model_does_not_accept_is_refused_before_anything_is_asked(self):
        net = Net(("/v1/messages", fx.ANTHROPIC_OK))
        code, _, err = self.main(net, "executar", "--fornecedor", "anthropic", "--modelo", "claude-opus-5-5", "--casos", str(CASES),
                                 "--saida", str(self.saida), "--teto-eur", "100", "--temperatura", "0.0")
        self.assertEqual((code, net.requests), (2, []))
        self.assertIn("não aceita temperatura", err)
        self.assertFalse(self.saida.parent.exists())

    def test_google_runs_on_its_own_api_and_counts_the_worst_case_while_the_thinking_count_is_to_confirm(self):
        net = Net((":generateContent", fx.GOOGLE_OK))
        code, _, err = self.run_cli(net, "google", "gemini-3.8-flash", "--teto-eur", "100")
        self.assertEqual(code, 0, err)
        self.assertIn(":generateContent", net.requests[0]["url"])
        (first, _) = read_records(self.saida.with_name(FILE_NAME))
        self.assertEqual((first.count_mode, first.reasoning_tokens, first.served_model), ("pior_caso", 450, "gemini-3.8-flash"))
        self.assertEqual(first.applied_params["campo_tokens"], "maxOutputTokens")
        self.assertIn("por confirmar", first.count_reason)

    def test_the_old_gemini_choice_still_means_the_compatible_endpoint(self):
        net = Net(("/openai/chat/completions", fx.OPENAI_OK))
        code, _, err = self.run_cli(net, "gemini", "gemini-3.5-flash-lite", "--limite", "1")
        self.assertEqual(code, 0, err)
        self.assertIn("/v1beta/openai/chat/completions", net.requests[0]["url"])
        self.assertEqual(sorted(p.name for p in self.saida.parent.iterdir()), ["respostas.jsonl"])

    def test_openai_stops_when_the_served_id_is_a_dated_snapshot_nobody_accepted_yet(self):
        net = Net(("/chat/completions", {**fx.OPENAI_OK, "model": "gpt-6-astra-2026-09-01"}))
        code, _, err = self.run_cli(net, "openai", "gpt-6-astra", "--teto-eur", "100")
        self.assertEqual(code, cli.STOPPED)
        self.assertIn("serviu 'gpt-6-astra-2026-09-01' em vez de 'gpt-6-astra'", err)
        self.assertEqual(len(net.requests), 1)
        self.assertFalse(self.saida.exists() and read_answers(self.saida))

    def test_the_compatible_server_confirms_its_model_runs_free_and_records_what_it_served(self):
        net = Net(("/models", fx.VLLM_MODELS), ("/chat/completions", fx.VLLM_CHAT))
        code, out, err = self.run_cli(net, "local-compativel", "amalia-9b-0626-dpo", "--base-url", "http://127.0.0.1:8000/v1", env={})
        self.assertEqual(code, 0, err)
        self.assertIn("o servidor tem carregado: AMALIA-9B-0626-DPO", out)
        self.assertEqual(net.requests[0]["url"], "http://127.0.0.1:8000/v1/models")
        self.assertEqual(net.bodies("/chat/completions")[0]["model"], "AMALIA-9B-0626-DPO")  # the key resolved to the id
        (first, _) = read_records(self.saida.with_name(FILE_NAME))
        self.assertEqual((first.served_model, first.served_check, first.cost_eur), ("AMALIA-9B-0626-DPO", "igual", 0))
        self.assertNotIn("authorization", net.requests[1]["headers"])

    def test_the_compatible_server_needs_its_address_and_only_that_choice_takes_one(self):
        net = Net(("/models", fx.VLLM_MODELS))
        code, _, err = self.run_cli(net, "local-compativel", "amalia-9b-0626-dpo", env={})
        self.assertEqual((code, net.requests), (2, []))
        self.assertIn("--base-url", err)
        code, _, err = self.run_cli(Net(), "openai", "gpt-6-astra", "--teto-eur", "1", "--base-url", "http://x/v1")
        self.assertEqual(code, 2)
        self.assertIn("só se usa com --fornecedor local-compativel", err)

    def test_a_server_with_another_model_loaded_is_refused_before_a_single_question(self):
        net = Net(("/models", fx.VLLM_OTHER_MODELS))
        code, _, err = self.run_cli(net, "local-compativel", "amalia-9b-0626-dpo", "--base-url", "http://127.0.0.1:8000/v1", env={})
        self.assertEqual(code, 2)
        self.assertIn("não tem o modelo AMALIA-9B-0626-DPO", err)
        self.assertEqual(len(net.requests), 1)
        self.assertFalse(self.saida.exists())

    def test_a_compatible_server_the_catalogue_does_not_list_runs_without_a_ledger(self):
        net = Net(("/models", {"data": [{"id": "meu-modelo"}]}), ("/chat/completions", {**fx.VLLM_CHAT, "model": "meu-modelo"}))
        code, _, err = self.run_cli(net, "local-compativel", "meu-modelo", "--base-url", "http://127.0.0.1:9000/v1", "--limite", "1", env={})
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(p.name for p in self.saida.parent.iterdir()), ["respostas.jsonl"])

    def test_the_paid_models_still_need_a_ceiling_and_the_free_one_does_not(self):
        for kind, model in (("anthropic", "claude-fable-5-1"), ("google", "gemini-3.1-pro-preview"), ("openai", "gpt-6-luna")):
            with self.subTest(modelo=model):
                code, _, err = self.run_cli(Net(), kind, model)
                self.assertEqual(code, 2)
                self.assertIn("--teto-eur", err)

    def test_the_dry_run_of_each_new_provider_needs_no_key_and_no_network(self):
        for kind, model in (("anthropic", "claude-opus-5-5"), ("google", "gemini-3.8-flash"), ("openai", "gpt-6-astra")):
            with self.subTest(modelo=model):
                net = Net()
                code, out, _ = self.main(net, "executar", "--fornecedor", kind, "--modelo", model, "--casos", str(CASES), "--a-seco",
                                         "--saida", str(self.saida), env={})
                self.assertEqual((code, net.requests), (0, []))
                self.assertIn("Nenhum pedido foi feito", out)


class TestTheKeyNeverLeavesTheProvider(WithTheCommandLine):
    """A made-up key goes through whole runs, good and bad, and is looked for in everything they write and print."""

    def test_after_a_whole_run_the_key_is_in_no_file_no_output_and_no_provenance(self):
        for kind, model, route, reply in (("anthropic", "claude-opus-5-5", "/v1/messages", fx.ANTHROPIC_OK),
                                           ("google", "gemini-3.8-flash", ":generateContent", fx.GOOGLE_OK),
                                           ("openai", "gpt-6-luna", "/chat/completions", {**fx.OPENAI_OK, "model": "gpt-6-luna"})):
            with self.subTest(fornecedor=kind):
                net = Net((route, reply))
                code, out, err = self.run_cli(net, kind, model, "--teto-eur", "100")
                self.assertEqual(code, 0, err)
                carried = [r for r in net.requests if SENTINEL in json.dumps(r["headers"])]
                self.assertEqual(len(carried), 2)  # the key did travel, in a header
                self.assertTrue(all(SENTINEL not in r["url"] and SENTINEL not in json.dumps(r["body"]) for r in net.requests))
                self.assertNotIn(SENTINEL, out + err + self.everything_written())

    def test_after_failures_that_echo_it_nothing_written_or_printed_has_it(self):
        net = Net(("/v1/messages", [http_error(401, {"error": {"message": f"chave inválida {SENTINEL}"}}),
                                    urllib.error.URLError(f"ligação com {SENTINEL}"), fx.ANTHROPIC_OK]))
        code, out, err = self.run_cli(net, "anthropic", "claude-opus-5-5", "--teto-eur", "100", "--tentativas", "1")
        self.assertEqual(code, 1)
        self.assertNotIn(SENTINEL, out + err + self.everything_written())
        self.assertIn("<chave omitida>", err)

    def test_a_missing_key_names_the_variable_and_no_command_line_flag_takes_one(self):
        code, out, err = self.run_cli(Net(), "anthropic", "claude-opus-5-5", "--teto-eur", "100", env={})
        self.assertEqual(code, 2)
        self.assertIn("ANTHROPIC_API_KEY", err)
        parser_text = cli.build_parser().format_help() + "".join(
            sub.format_help() for action in cli.build_parser()._actions if hasattr(action, "choices") and isinstance(action.choices, dict)
            for sub in action.choices.values())
        self.assertNotRegex(parser_text.lower(), r"--(api-)?(key|chave)")


if __name__ == "__main__":
    unittest.main()
