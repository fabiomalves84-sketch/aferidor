"""The provider boundary: what a model sees, and how failures are classified."""

from __future__ import annotations

import unittest

from aferidor.providers import (
    AnthropicProvider,
    FakeProvider,
    OpenAIProvider,
    ProviderError,
)


class TestFakeProvider(unittest.TestCase):
    def test_a_scripted_prompt_gets_its_scripted_reply(self):
        provider = FakeProvider(replies={"amoxicilina": "1000 mg 8/8h"}, default="nada")
        self.assertEqual(provider.ask("dose de amoxicilina?"), "1000 mg 8/8h")

    def test_an_unscripted_prompt_gets_the_default(self):
        provider = FakeProvider(default="nao sei")
        self.assertEqual(provider.ask("qualquer coisa"), "nao sei")

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
        self.assertEqual(provider.ask("pergunta"), "ok")


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


if __name__ == "__main__":
    unittest.main()
