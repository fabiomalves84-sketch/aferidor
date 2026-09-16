"""The provider boundary: what a model sees, and how failures are classified."""

from __future__ import annotations

import unittest

from aferidor.providers import (
    AnthropicProvider,
    FakeProvider,
    LocalProvider,
    OpenAIProvider,
    ProviderError,
    normalize_finish_reason,
)


class TestFakeProvider(unittest.TestCase):
    def test_a_scripted_prompt_gets_its_scripted_reply(self):
        provider = FakeProvider(replies={"amoxicilina": "1000 mg 8/8h"}, default="nada")
        self.assertEqual(provider.ask("dose de amoxicilina?").text, "1000 mg 8/8h")

    def test_an_unscripted_prompt_gets_the_default(self):
        provider = FakeProvider(default="nao sei")
        self.assertEqual(provider.ask("qualquer coisa").text, "nao sei")

    def test_every_prompt_is_kept_for_inspection(self):
        provider = FakeProvider()
        provider.ask("primeira")
        provider.ask("segunda")
        self.assertEqual(provider.prompts, ["primeira", "segunda"])

    def test_scripted_failures_are_retryable_and_run_out(self):
        provider = FakeProvider(failures=1, default="ok")
        with self.assertRaises(ProviderError) as caught:
            provider.ask("pergunta")
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(provider.ask("pergunta").text, "ok")


class TestFinishReason(unittest.TestCase):
    def test_a_fake_provider_defaults_to_stop(self):
        self.assertEqual(FakeProvider(default="x").ask("p").finish_reason, "stop")

    def test_a_fake_provider_can_simulate_being_cut_off(self):
        provider = FakeProvider(default="a meio", finish_reason="length")
        self.assertEqual(provider.ask("p").finish_reason, "length")

    def test_openai_and_ollama_vocabulary_is_normalized(self):
        self.assertEqual(normalize_finish_reason("stop"), "stop")
        self.assertEqual(normalize_finish_reason("length"), "length")

    def test_anthropic_vocabulary_is_normalized(self):
        self.assertEqual(normalize_finish_reason("end_turn"), "stop")
        self.assertEqual(normalize_finish_reason("stop_sequence"), "stop")
        self.assertEqual(normalize_finish_reason("max_tokens"), "length")

    def test_anything_else_is_unknown_rather_than_guessed_at(self):
        self.assertEqual(normalize_finish_reason("tool_calls"), "unknown")
        self.assertEqual(normalize_finish_reason(None), "unknown")


class TestProviderErrors(unittest.TestCase):
    def test_a_permanent_error_is_not_retryable_by_default(self):
        self.assertFalse(ProviderError("chave invalida").retryable)

    def test_a_missing_key_names_the_variable(self):
        for cls in (OpenAIProvider, AnthropicProvider):
            with self.subTest(provider=cls.__name__):
                with self.assertRaises(ProviderError) as caught:
                    cls(api_key="   ")
                self.assertIn(cls.ENV_KEY, str(caught.exception))


class TestProviderIdentity(unittest.TestCase):
    def test_the_name_carries_vendor_and_model(self):
        self.assertEqual(OpenAIProvider(model="gpt-4o", api_key="k").name, "openai:gpt-4o")
        self.assertEqual(
            AnthropicProvider(model="claude-x", api_key="k").name, "anthropic:claude-x"
        )
        self.assertEqual(LocalProvider(model="llama3").name, "local:llama3")


class TestLocalProvider(unittest.TestCase):
    def test_no_key_is_needed(self):
        LocalProvider()  # nao levanta

    def test_the_default_address_is_ollamas_own_port(self):
        self.assertEqual(LocalProvider().base_url, "http://localhost:11434")

    def test_the_address_can_be_overridden_directly(self):
        self.assertEqual(
            LocalProvider(base_url="http://outra-maquina:11434").base_url,
            "http://outra-maquina:11434",
        )

    def test_a_trailing_slash_on_the_address_is_tolerated(self):
        self.assertEqual(
            LocalProvider(base_url="http://localhost:11434/").base_url,
            "http://localhost:11434",
        )

    def test_the_address_can_come_from_the_environment(self):
        import os

        guardado = os.environ.get(LocalProvider.ENV_URL)
        os.environ[LocalProvider.ENV_URL] = "http://outra:11434"
        try:
            self.assertEqual(LocalProvider().base_url, "http://outra:11434")
        finally:
            if guardado is None:
                os.environ.pop(LocalProvider.ENV_URL, None)
            else:
                os.environ[LocalProvider.ENV_URL] = guardado


if __name__ == "__main__":
    unittest.main()
