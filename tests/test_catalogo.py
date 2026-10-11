"""The catalogue of models: what it accepts, what it refuses, and that no price lives in the code."""

from __future__ import annotations

import copy
import json
import re
import socket
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

from aferidor.catalogo import (
    DEFAULT_PATH,
    CatalogError,
    EurosUnavailable,
    load_catalog,
    parse_catalog,
)

PACKAGE = Path(__file__).resolve().parent.parent / "aferidor"


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def period(**over) -> dict:
    base = {
        "entrada_por_milhao": 2, "saida_por_milhao": 10, "valido_de": None, "valido_ate": None,
        "prompt_tokens_ate": None, "origem": "pagina_oficial", "fonte": "https://exemplo.test/precos",
        "lido_em": "2026-10-11",
    }
    return {**base, **over}


def model(**over) -> dict:
    base = {
        "fornecedor": "openai", "id_pedido": "modelo-falso", "verificado_em_execucao": False, "moeda": "USD",
        "precos": [period()],
        "parametros": {"campo_tokens": "max_tokens", "temperatura": "desconhecido", "tokens_raciocinio": "desconhecido",
                       "esforco_raciocinio": None, "tokens_max": 8192},
        "tempo_limite_s": 60, "ritmo_min_s": 0, "chave_env": "CHAVE_FALSA", "base_url": None,
    }
    return {**base, **over}


def catalog(**over) -> dict:
    base = {
        "lido_em": "2026-10-11",
        "usd_para_eur": {"valor": None, "fonte": "", "lido_em": None},
        "modelos": {"m": model()},
    }
    return {**base, **over}


def parse(data: dict):
    return parse_catalog(json.dumps(data))


class TestAValidCatalogue(unittest.TestCase):
    def test_a_model_comes_back_with_everything_the_runner_will_need(self):
        found = parse(catalog()).model("m")
        self.assertEqual((found.provider, found.requested_id, found.token_field), ("openai", "modelo-falso", "max_tokens"))
        self.assertEqual((found.temperature, found.reasoning_effort, found.tokens_max), ("desconhecido", None, 8192))
        self.assertEqual((found.timeout_s, found.min_interval_s, found.key_variable), (60.0, 0.0, "CHAVE_FALSA"))
        price = found.price_on(date(2026, 10, 11))
        self.assertEqual((price.input_per_million, price.output_per_million, price.currency), (Decimal(2), Decimal(10), "USD"))
        self.assertEqual((price.source, price.read_on), ("https://exemplo.test/precos", date(2026, 10, 11)))

    def test_prices_are_exact_decimals_not_floats(self):
        raw = json.dumps(catalog()).replace('"entrada_por_milhao": 2', '"entrada_por_milhao": 0.10')
        self.assertEqual(parse_catalog(raw).model("m").prices[0].input_per_million, Decimal("0.10"))

    def test_the_cost_of_a_call_is_tokens_times_the_price_per_million(self):
        cost = parse(catalog()).cost_usd("m", date(2026, 10, 11), 1_000_000, 500_000)
        self.assertEqual(cost, Decimal(2) + Decimal(5))

    def test_the_key_variables_are_the_ones_the_models_declare(self):
        data = catalog(modelos={"a": model(chave_env="UMA"), "b": model(chave_env="OUTRA"), "c": model(chave_env=None)})
        self.assertEqual(parse(data).key_variables(), frozenset({"UMA", "OUTRA"}))

    def test_a_model_is_resolved_by_its_id_or_by_its_key(self):
        data = catalog(modelos={"chave": model(id_pedido="id-do-fornecedor")})
        found = parse(data)
        self.assertEqual(found.resolve("openai", "id-do-fornecedor").key, "chave")
        self.assertEqual(found.resolve("openai", "chave").key, "chave")
        self.assertIsNone(found.resolve("anthropic", "chave"))

    def test_a_fixed_temperature_has_to_say_which_and_a_model_with_only_zero_prices_is_free(self):
        parametros = {**model()["parametros"], "temperatura": "fixa_pelo_fornecedor"}
        with self.assertRaisesRegex(CatalogError, "temperatura_fixa"):
            parse(catalog(modelos={"m": model(parametros=parametros)}))
        self.assertEqual(parse(catalog(modelos={"m": model(parametros={**parametros, "temperatura_fixa": 1})})).model("m").fixed_temperature, 1)
        self.assertFalse(parse(catalog()).model("m").is_free)
        self.assertTrue(parse(catalog(modelos={"m": model(precos=[period(entrada_por_milhao=0, saida_por_milhao=0)])})).model("m").is_free)
        with self.assertRaisesRegex(CatalogError, "por_confirmar"):
            parse(catalog(modelos={"m": model(por_confirmar="x")}))

    def test_a_model_is_found_by_provider_and_requested_id_and_only_by_both(self):
        found = parse(catalog())
        self.assertEqual(found.find("openai", "modelo-falso").key, "m")
        self.assertIsNone(found.find("anthropic", "modelo-falso"))
        self.assertIsNone(found.find("openai", "outro"))

    def test_the_served_ids_a_person_accepted_are_read_and_default_to_none(self):
        self.assertEqual(parse(catalog()).model("m").accepted_served_ids, ())
        data = catalog(modelos={"m": model(ids_servidos_aceites=["modelo-falso-20261001"])})
        self.assertEqual(parse(data).model("m").accepted_served_ids, ("modelo-falso-20261001",))
        for bad in ("modelo", [1], [""], {"a": 1}):
            with self.subTest(valor=bad), self.assertRaisesRegex(CatalogError, "ids_servidos_aceites"):
                parse(catalog(modelos={"m": model(ids_servidos_aceites=bad)}))

    def test_an_unknown_model_says_which_ones_exist(self):
        with self.assertRaisesRegex(CatalogError, "não está no catálogo.*m"):
            parse(catalog()).model("outro")


class TestPricesWithAnExpiryDate(unittest.TestCase):
    def two_periods(self):
        return catalog(modelos={"m": model(precos=[
            period(entrada_por_milhao=1, saida_por_milhao=4, valido_ate="2026-12-31"),
            period(entrada_por_milhao=2, saida_por_milhao=8, valido_de="2027-01-01"),
        ])})

    def test_the_price_is_the_one_in_force_on_the_day_asked(self):
        found = parse(self.two_periods()).model("m")
        self.assertEqual(found.price_on(date(2026, 12, 31)).input_per_million, Decimal(1))
        self.assertEqual(found.price_on(date(2027, 1, 1)).input_per_million, Decimal(2))
        self.assertEqual(found.price_on(date(2026, 1, 1)).input_per_million, Decimal(1))

    def test_a_period_that_ends_on_a_day_still_covers_that_day(self):
        cost = parse(self.two_periods()).cost_usd("m", date(2026, 12, 31), 1_000_000, 0)
        self.assertEqual(cost, Decimal(1))

    def test_a_gap_between_periods_has_no_price_and_says_so(self):
        data = catalog(modelos={"m": model(precos=[period(valido_ate="2026-06-30"), period(valido_de="2026-08-01")])})
        with self.assertRaisesRegex(CatalogError, "não tem preço de m para 2026-07-15"):
            parse(data).model("m").price_on(date(2026, 7, 15))

    def test_two_periods_covering_the_same_days_are_refused(self):
        data = catalog(modelos={"m": model(precos=[period(valido_ate="2026-12-31"), period(valido_de="2026-12-01")])})
        with self.assertRaisesRegex(CatalogError, "mesmos dias"):
            parse(data)

    def test_the_price_depends_on_the_size_of_the_prompt_when_the_catalogue_says_so(self):
        data = catalog(modelos={"m": model(precos=[period(prompt_tokens_ate=200_000)])})
        found = parse(data).model("m")
        self.assertEqual(found.price_on(date(2026, 10, 11), 200_000).input_per_million, Decimal(2))
        with self.assertRaisesRegex(CatalogError, "não tem preço"):
            found.price_on(date(2026, 10, 11), 200_001)

    def test_a_period_that_ends_before_it_starts_is_refused(self):
        with self.assertRaisesRegex(CatalogError, "depois de 'valido_ate'"):
            parse(catalog(modelos={"m": model(precos=[period(valido_de="2027-01-01", valido_ate="2026-01-01")])}))


class TestEuros(unittest.TestCase):
    def test_without_a_rate_the_catalogue_refuses_to_count_in_euros_and_says_why(self):
        with self.assertRaisesRegex(EurosUnavailable, "não tem taxa de USD para EUR.*não inventa"):
            parse(catalog()).cost_eur("m", date(2026, 10, 11), 1000, 1000)

    def test_usd_costs_do_not_need_the_rate(self):
        self.assertGreater(parse(catalog()).cost_usd("m", date(2026, 10, 11), 1000, 1000), 0)

    def test_with_a_rate_the_euros_follow(self):
        data = catalog(usd_para_eur={"valor": 0.5, "fonte": "https://exemplo.test/bce", "lido_em": "2026-10-11"})
        self.assertEqual(parse(data).cost_eur("m", date(2026, 10, 11), 1_000_000, 0), Decimal(1))

    def test_a_price_already_in_euros_is_not_converted_twice(self):
        data = catalog(usd_para_eur={"valor": 0.5, "fonte": "https://exemplo.test/bce", "lido_em": "2026-10-11"},
                       modelos={"m": model(moeda="EUR", precos=[period(moeda="EUR")])})
        found = parse(data)
        self.assertEqual(found.cost_eur("m", date(2026, 10, 11), 1_000_000, 0), Decimal(2))
        self.assertEqual(found.cost_usd("m", date(2026, 10, 11), 1_000_000, 0), Decimal(4))

    def test_a_rate_of_zero_or_negative_is_refused(self):
        for value in (0, -0.9):
            with self.subTest(valor=value):
                with self.assertRaises(CatalogError):
                    parse(catalog(usd_para_eur={"valor": value, "fonte": "https://x.test", "lido_em": "2026-10-11"}))

    def test_the_rate_field_has_to_exist_even_when_it_is_empty(self):
        data = catalog()
        del data["usd_para_eur"]
        with self.assertRaisesRegex(CatalogError, "falta o campo 'usd_para_eur'"):
            parse(data)


class TestAnInvalidCatalogue(unittest.TestCase):
    def test_json_that_does_not_parse_says_where(self):
        with self.assertRaisesRegex(CatalogError, "JSON malformado na linha 1"):
            parse_catalog("{ isto não é json")

    def test_every_required_field_missing_is_named(self):
        required_in_model = ["fornecedor", "id_pedido", "verificado_em_execucao", "moeda", "precos", "parametros",
                             "tempo_limite_s", "ritmo_min_s", "chave_env", "base_url"]
        for name in required_in_model:
            with self.subTest(campo=name):
                data = catalog()
                del data["modelos"]["m"][name]
                with self.assertRaisesRegex(CatalogError, f"modelos.m: falta o campo '{name}'"):
                    parse(data)
        for name in ("campo_tokens", "temperatura", "tokens_raciocinio", "esforco_raciocinio", "tokens_max"):
            with self.subTest(parametro=name):
                data = catalog()
                del data["modelos"]["m"]["parametros"][name]
                with self.assertRaisesRegex(CatalogError, f"parametros: falta o campo '{name}'"):
                    parse(data)
        for name in ("entrada_por_milhao", "saida_por_milhao", "valido_de", "valido_ate", "prompt_tokens_ate",
                     "origem", "fonte", "lido_em"):
            with self.subTest(preco=name):
                data = catalog()
                del data["modelos"]["m"]["precos"][0][name]
                with self.assertRaisesRegex(CatalogError, f"precos\\[0\\]: falta o campo '{name}'"):
                    parse(data)
        for name in ("lido_em", "usd_para_eur", "modelos"):
            with self.subTest(raiz=name):
                data = catalog()
                del data[name]
                with self.assertRaisesRegex(CatalogError, f"falta o campo '{name}'"):
                    parse(data)

    def test_an_absent_price_is_an_error_and_not_a_zero(self):
        data = catalog()
        data["modelos"]["m"]["precos"] = []
        with self.assertRaisesRegex(CatalogError, "pelo menos um período"):
            parse(data)
        data = catalog()
        data["modelos"]["m"]["precos"][0]["saida_por_milhao"] = None
        with self.assertRaisesRegex(CatalogError, "'saida_por_milhao' tem de ser um número"):
            parse(data)

    def test_values_of_the_wrong_kind_are_refused(self):
        cases = {
            "preço negativo": lambda d: d["modelos"]["m"]["precos"][0].update(entrada_por_milhao=-1),
            "preço em texto": lambda d: d["modelos"]["m"]["precos"][0].update(entrada_por_milhao="2"),
            "preço booleano": lambda d: d["modelos"]["m"]["precos"][0].update(entrada_por_milhao=True),
            "data impossível": lambda d: d["modelos"]["m"]["precos"][0].update(lido_em="2026-02-30"),
            "data noutro formato": lambda d: d["modelos"]["m"]["precos"][0].update(valido_de="1/1/2027"),
            "fonte oficial sem URL": lambda d: d["modelos"]["m"]["precos"][0].update(fonte="uma página"),
            "origem desconhecida": lambda d: d["modelos"]["m"]["precos"][0].update(origem="ouvi dizer"),
            "moeda desconhecida": lambda d: d["modelos"]["m"].update(moeda="GBP"),
            "fornecedor desconhecido": lambda d: d["modelos"]["m"].update(fornecedor="outro"),
            "temperatura inventada": lambda d: d["modelos"]["m"]["parametros"].update(temperatura="talvez"),
            "campo de tokens inventado": lambda d: d["modelos"]["m"]["parametros"].update(campo_tokens="n_tokens"),
            "tokens_max zero": lambda d: d["modelos"]["m"]["parametros"].update(tokens_max=0),
            "tempo limite zero": lambda d: d["modelos"]["m"].update(tempo_limite_s=0),
            "variável com espaço": lambda d: d["modelos"]["m"].update(chave_env="TEM ESPACO"),
            "verificado em texto": lambda d: d["modelos"]["m"].update(verificado_em_execucao="não"),
            "sem modelos": lambda d: d.update(modelos={}),
        }
        for name, change in cases.items():
            with self.subTest(caso=name):
                data = copy.deepcopy(catalog())
                change(data)
                with self.assertRaises(CatalogError):
                    parse(data)

    def test_the_message_says_where_the_problem_is(self):
        data = catalog()
        data["modelos"]["m"]["precos"][0]["entrada_por_milhao"] = "2"
        with self.assertRaisesRegex(CatalogError, r"modelos\.m\.precos\[0\]"):
            parse(data)

    def test_a_missing_or_unreadable_file_is_a_catalogue_error_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(CatalogError, "não consegui ler o catálogo"):
                load_catalog(Path(folder) / "nao-existe.json")
            binary = Path(folder) / "mau.json"
            binary.write_bytes(b"\xff\xfe\x00")
            with self.assertRaisesRegex(CatalogError, "não está em UTF-8"):
                load_catalog(binary)


class TestTheShippedCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_it_loads_and_has_the_candidates(self):
        self.assertEqual(
            sorted(self.catalog.models),
            sorted(["claude-fable-5-1", "claude-opus-5-5", "gpt-6-astra", "gpt-6.1-sol", "gpt-6-luna",
                    "gemini-3.1-pro-preview", "gemini-3.8-flash", "amalia-9b-0626-dpo",
                    "amalia-9b-0626-dpo-gguf-q4km-ollama"]),
        )

    def test_none_of_them_has_an_accepted_served_id_yet(self):
        for key, found in self.catalog.models.items():
            with self.subTest(modelo=key):
                self.assertEqual(found.accepted_served_ids, ())

    def test_none_of_them_is_confirmed_at_run_time_yet(self):
        for key, found in self.catalog.models.items():
            with self.subTest(modelo=key):
                self.assertIs(found.verified_at_run_time, False)

    def test_the_rate_is_the_one_the_fabio_gave_with_its_source_and_day(self):
        self.assertEqual(self.catalog.usd_to_eur, Decimal("0.8924"))
        self.assertIn("BCE", self.catalog.usd_to_eur_source)
        self.assertIn("2026-10-09", self.catalog.usd_to_eur_source)
        self.assertIn("1,1206", self.catalog.usd_to_eur_source)
        raw = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(raw["usd_para_eur"]["lido_em"], "2026-10-09")

    def test_a_cost_in_euros_follows_the_rate(self):
        day = date(2026, 10, 11)
        usd = self.catalog.cost_usd("gpt-6-luna", day, 1_000_000, 1_000_000)
        self.assertEqual(self.catalog.cost_eur("gpt-6-luna", day, 1_000_000, 1_000_000), usd * Decimal("0.8924"))

    def test_every_commercial_price_has_its_page_and_the_day_it_was_read(self):
        for key, found in self.catalog.models.items():
            for index, price in enumerate(found.prices):
                with self.subTest(modelo=key, periodo=index):
                    self.assertEqual(price.read_on, date(2026, 10, 11))
                    if price.origin == "pagina_oficial":
                        self.assertTrue(price.source.startswith("https://"))
                    else:
                        self.assertTrue(key.startswith("amalia-9b-0626-dpo"), key)

    def test_the_prices_are_the_ones_given(self):
        expected = {
            "claude-fable-5-1": (10, 50), "claude-opus-5-5": (4, 20), "gpt-6-astra": (10, 50),
            "gpt-6.1-sol": (2, 10), "gpt-6-luna": ("0.10", "0.50"), "gemini-3.1-pro-preview": (2, 12),
            "amalia-9b-0626-dpo": (0, 0),
        }
        day = date(2026, 10, 11)
        for key, (entrada, saida) in expected.items():
            with self.subTest(modelo=key):
                price = self.catalog.model(key).price_on(day)
                self.assertEqual((price.input_per_million, price.output_per_million), (Decimal(entrada), Decimal(saida)))

    def test_gemini_flash_doubles_on_the_first_of_january(self):
        flash = self.catalog.model("gemini-3.8-flash")
        before, after = flash.price_on(date(2026, 12, 31)), flash.price_on(date(2027, 1, 1))
        self.assertEqual((before.input_per_million, before.output_per_million), (Decimal("0.75"), Decimal("3.75")))
        self.assertEqual((after.input_per_million, after.output_per_million), (Decimal("1.50"), Decimal("7.50")))

    def test_gemini_pro_has_no_price_above_200k_tokens_of_prompt(self):
        pro = self.catalog.model("gemini-3.1-pro-preview")
        self.assertEqual(pro.price_on(date(2026, 10, 11), 200_000).input_per_million, Decimal(2))
        with self.assertRaises(CatalogError):
            pro.price_on(date(2026, 10, 11), 200_001)

    def test_what_the_documentation_settled_is_written_and_the_rest_says_so_instead_of_a_guess(self):
        for key, found in self.catalog.models.items():
            with self.subTest(modelo=key):
                self.assertIsNone(found.reasoning_effort)
                if found.provider == "anthropic":
                    # https://platform.claude.com/docs/en/api/messages/create, read 2026-10-11
                    self.assertEqual((found.temperature, found.fixed_temperature), ("fixa_pelo_fornecedor", Decimal("1.0")))
                    self.assertEqual((found.reasoning_tokens, found.token_field), ("incluidos_na_saida", "max_tokens"))
                elif key == "gemini-3.8-flash":
                    # the pilot of 2026-10-11 and https://ai.google.dev/gemini-api/docs/thinking: counted apart, still to confirm
                    self.assertEqual((found.temperature, found.reasoning_tokens), ("desconhecido", "separados_da_saida"))
                    self.assertIn("tokens_raciocinio", found.to_confirm)
                    self.assertIn("2026-10-11", found.note)
                elif found.provider == "gemini":
                    self.assertEqual((found.temperature, found.reasoning_tokens), ("desconhecido", "por_confirmar"))
                else:
                    self.assertEqual((found.temperature, found.reasoning_tokens), ("desconhecido", "desconhecido"))

    def test_every_model_lists_what_was_not_found_in_an_official_page(self):
        for key, found in self.catalog.models.items():
            with self.subTest(modelo=key):
                self.assertIn("tempo_limite_s", found.to_confirm)  # copied from the code, never read from a page
        self.assertEqual(self.catalog.model("gpt-6-astra").to_confirm,
                         ("campo_tokens", "temperatura", "tokens_raciocinio", "usage", "finish_reason", "tempo_limite_s", "ritmo_min_s"))
        self.assertIn("tokens_raciocinio", self.catalog.model("gemini-3.8-flash").to_confirm)
        self.assertNotIn("campo_tokens", self.catalog.model("claude-opus-5-5").to_confirm)

    def test_only_the_two_amalia_entries_are_free_and_need_no_ceiling(self):
        self.assertEqual([k for k, m in self.catalog.models.items() if m.is_free],
                         ["amalia-9b-0626-dpo", "amalia-9b-0626-dpo-gguf-q4km-ollama"])

    def test_amalia_is_a_compatible_server_to_configure_at_4096_tokens(self):
        found = self.catalog.model("amalia-9b-0626-dpo")
        self.assertEqual((found.provider, found.requested_id, found.tokens_max), ("openai_compativel", "AMALIA-9B-0626-DPO", 4096))
        self.assertIsNone(found.base_url)

    def test_the_key_variables_are_exactly_the_three_commercial_ones(self):
        self.assertEqual(self.catalog.key_variables(), frozenset({"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"}))


class TestNoPriceLivesInTheCode(unittest.TestCase):
    """Prices and ids change. They are read from `catalogo.json`; a `.py` that carries one has forked it."""

    CURRENCY = re.compile(r"\d\s*(?:USD|EUR|€)|(?:USD|EUR|€|\$)\s*\d|por milh", re.IGNORECASE)

    def sources(self):
        files = sorted(PACKAGE.glob("*.py"))
        self.assertGreater(len(files), 10)
        return {p.name: p.read_text(encoding="utf-8") for p in files}

    def test_no_price_with_a_currency_in_any_module(self):
        for name, text in self.sources().items():
            with self.subTest(modulo=name):
                self.assertIsNone(self.CURRENCY.search(text))

    def test_no_catalogue_id_is_written_in_any_module(self):
        """Not even as a default: the Gemini provider had one (`gemini-3.8-flash`) and no longer does."""
        ids = [m.requested_id for m in load_catalog().models.values()]
        for name, text in self.sources().items():
            for requested in ids:
                with self.subTest(modulo=name, id=requested):
                    self.assertNotIn(requested, text, msg="id de modelo escrito no código")

    def test_the_check_would_catch_one(self):
        self.assertTrue(self.CURRENCY.search("PRICE = 10 USD"))
        self.assertTrue(self.CURRENCY.search("custo = '$ 0.5'"))
        self.assertTrue(self.CURRENCY.search("# 3 por milhão"))

    def test_the_file_is_where_the_package_expects_it_and_is_declared_for_installation(self):
        self.assertEqual(DEFAULT_PATH, PACKAGE / "catalogo.json")
        pyproject = (PACKAGE.parent / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('aferidor = ["catalogo.json"]', pyproject)


if __name__ == "__main__":
    unittest.main()
