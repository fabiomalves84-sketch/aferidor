"""What a failed attempt leaves behind (status, class, a short clean message), how the report tells the provider
being unavailable from the model being wrong, and the provider's total of tokens. Simulated replies only."""

from __future__ import annotations

import http.client
import io
import json
import socket
import unittest
import urllib.error
from dataclasses import replace
from decimal import Decimal
from unittest import mock

import tests  # noqa: F401  (a importação fixa a raiz das chaves numa pasta vazia)
from aferidor import execucao, traducao
from aferidor.execucao import Files, analyse
from aferidor.grading import grade_all
from aferidor.providers import (
    ERROR_CLASSES,
    UNAVAILABLE_CLASSES,
    AnthropicProvider,
    GoogleProvider,
    OpenAICompatible,
    ProviderError,
    Usage,
    clean_message,
    usage_from,
)
from aferidor.proveniencia import FILE_NAME, ProvenanceError, read_records
from aferidor.runner import run
from tests import fixtures_fornecedores as fx
from tests.helpers import a_case
from tests.test_execucao import CASES20, rec, reports, scenario
from tests.test_fornecedores import SENTINEL, Net, http_error
from tests.test_pago import WithAPaidFolder

URLOPEN = "aferidor.providers.urllib.request.urlopen"
REQUESTED = "modelo-falso"


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def failure(error, make=lambda: AnthropicProvider(model="m", api_key=SENTINEL, max_tokens=10)) -> ProviderError:
    with mock.patch(URLOPEN, mock.MagicMock(side_effect=error)), unittest.TestCase().assertRaises(ProviderError) as caught:
        make().ask("p")
    return caught.exception


def body(message: str, **extra) -> dict:
    return {"type": "error", "error": {"type": "overloaded_error", "message": message}, **extra}


class TestWhatAFailedAttemptSays(unittest.TestCase):
    def test_a_503_is_unavailable_with_its_status_and_the_words_of_the_error(self):
        error = failure(http_error(503, body("The model is overloaded. Please try again later.")))
        self.assertEqual((error.http_status, error.error_class), (503, "indisponivel_503"))
        self.assertEqual(error.short_message, "HTTP 503: The model is overloaded. Please try again later.")

    def test_a_429_is_the_request_limit(self):
        error = failure(http_error(429, body("Quota exceeded for this model."), {"Retry-After": "7"}))
        self.assertEqual((error.http_status, error.error_class, error.retry_after), (429, "limite_429", 7.0))
        self.assertEqual(error.short_message, "HTTP 429: Quota exceeded for this model.")

    def test_the_other_statuses_each_have_their_class(self):
        for code, expected in ((500, "indisponivel_5xx"), (502, "indisponivel_5xx"), (529, "indisponivel_5xx"), (504, "indisponivel_5xx"),
                               (401, "autenticacao"), (403, "autenticacao"), (400, "outro"), (404, "outro")):
            with self.subTest(estado=code):
                error = failure(http_error(code, body("x")))
                self.assertEqual((error.http_status, error.error_class), (code, expected))

    def test_a_timeout_a_cut_connection_and_a_refused_connection_are_not_http(self):
        cases = ((TimeoutError(), "tempo_esgotado"), (http.client.RemoteDisconnected("cortada"), "rede"),
                 (urllib.error.URLError("sem rede"), "rede"), (ConnectionResetError("x"), "rede"),
                 (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "x"), "resposta_invalida"))
        for raised, expected in cases:
            with self.subTest(erro=type(raised).__name__):
                error = failure(raised)
                self.assertEqual((error.http_status, error.error_class), (None, expected))
                self.assertTrue(error.short_message)

    def test_every_class_the_providers_use_is_one_of_the_listed_and_the_unavailable_ones_are_the_first_five(self):
        self.assertEqual(UNAVAILABLE_CLASSES, ("limite_429", "indisponivel_503", "indisponivel_5xx", "tempo_esgotado", "rede"))
        self.assertEqual(ProviderError("x", error_class="inventada").error_class, "outro")
        self.assertIn("outro", ERROR_CLASSES)

    def test_the_short_message_has_no_json_body_no_url_no_header_and_at_most_200_characters(self):
        long_text = "Muito longa. " * 60
        for message in (long_text, f"falhou em https://api.exemplo.test/v1/models/x:generate?key={SENTINEL}&alt=json por favor"):
            error = failure(http_error(503, body(message)))
            self.assertLessEqual(len(error.short_message), 200)
            self.assertNotIn("http", error.short_message)
            self.assertNotIn(SENTINEL, error.short_message)
            self.assertNotIn("{", error.short_message)
        self.assertIn("<url>", clean_message("ver https://exemplo.test/x?key=abc"))

    def test_a_body_that_is_not_json_or_has_no_message_gives_only_the_status(self):
        for raw in (io.BytesIO(b"<html>Service Unavailable</html>"), io.BytesIO(b'{"outro": "campo"}'), io.BytesIO(b"")):
            error = failure(urllib.error.HTTPError("https://x.test", 503, "x", {}, raw))
            self.assertEqual(error.short_message, "HTTP 503")

    def test_a_key_echoed_by_the_provider_never_reaches_any_of_the_fields(self):
        providers = (
            lambda: AnthropicProvider(model="m", api_key=SENTINEL, max_tokens=10),
            lambda: GoogleProvider(model="m", api_key=SENTINEL, max_tokens=10, min_interval_s=0),
            lambda: OpenAICompatible(model="m", base_url="http://127.0.0.1:8000/v1", api_key=SENTINEL),
        )
        for make in providers:
            for raised in (http_error(401, body(f"chave inválida {SENTINEL}")), urllib.error.URLError(f"ligação com {SENTINEL}"),
                           http_error(503, {"error": f"{SENTINEL} sobrecarregado"})):
                with self.subTest(fornecedor=type(make()).__name__, erro=type(raised).__name__):
                    error = failure(raised, make)
                    fields = [str(error.short_message), str(error.http_status), error.error_class, str(error)]
                    self.assertNotIn(SENTINEL, " ".join(fields))


class TestItIsWrittenInTheProvenance(WithAPaidFolder):
    def real(self):
        return AnthropicProvider(model=REQUESTED, api_key=SENTINEL, send_temperature=False, max_tokens=1000)

    def lines(self):
        return read_records(self.folder / FILE_NAME)

    def test_each_failed_attempt_has_its_status_class_message_and_attempt_and_the_good_one_has_none(self):
        net = Net(("/v1/messages", [http_error(503, body("overloaded"), {}), http_error(429, body("slow down"), {"Retry-After": "1"}),
                                    {**fx.ANTHROPIC_OK, "model": REQUESTED}]))
        with mock.patch(URLOPEN, net):
            result = run([a_case("C1")], self.real(), path=self.answers, run_id="r1", config=self.config(), paid=self.paid())
        self.assertEqual(len(result.answers), 1)
        first, second, third = self.lines()
        self.assertEqual((first.attempt, first.state, first.http_status, first.error_class, first.error_message),
                         (1, "erro", 503, "indisponivel_503", "HTTP 503: overloaded"))
        self.assertEqual((second.attempt, second.state, second.http_status, second.error_class, second.error_message),
                         (2, "erro", 429, "limite_429", "HTTP 429: slow down"))
        self.assertEqual((third.attempt, third.state, third.http_status, third.error_class, third.error_message),
                         (3, "resposta", None, None, ""))

    def test_a_timeout_that_may_have_been_billed_is_filed_with_its_class_too(self):
        with mock.patch(URLOPEN, Net(("/v1/messages", TimeoutError()))):
            run([a_case("C1")], self.real(), path=self.answers, run_id="r1", config=self.config(), paid=self.paid())
        (only,) = self.lines()
        self.assertEqual((only.state, only.error_class, only.http_status), ("resultado_desconhecido", "tempo_esgotado", None))

    def test_nothing_that_was_written_carries_the_key_even_when_the_provider_echoes_it(self):
        net = Net(("/v1/messages", [http_error(503, body(f"erro com {SENTINEL} e https://x.test/?key={SENTINEL}")),
                                    urllib.error.URLError(f"falha {SENTINEL}"), {**fx.ANTHROPIC_OK, "model": REQUESTED}]))
        with mock.patch(URLOPEN, net):
            run([a_case("C1")], self.real(), path=self.answers, run_id="r1", config=self.config(), paid=self.paid())
        written = "".join(p.read_text(encoding="utf-8") for p in self.folder.iterdir() if p.is_file() and p.suffix == ".jsonl")
        self.assertNotIn(SENTINEL, written)
        self.assertIn("<chave omitida>", written)

    def test_lines_written_before_these_fields_existed_still_read(self):
        old = rec("m", "C01", 1).to_dict()
        for key in ("http_status", "classe_erro", "mensagem_erro", "total_tokens", "total_diferenca"):
            del old[key]
        (self.folder / FILE_NAME).write_text(json.dumps(old) + "\n", encoding="utf-8")
        (line,) = self.lines()
        self.assertEqual((line.http_status, line.error_class, line.error_message, line.total_tokens, line.total_difference),
                         (None, None, "", None, None))

    def test_a_class_that_does_not_exist_or_a_message_too_long_is_refused_when_the_line_is_made(self):
        with self.assertRaises(ProvenanceError):
            rec("m", "C01", 1, error_class="inventada")
        with self.assertRaises(ProvenanceError):
            rec("m", "C01", 1, error_message="x" * 201)


class TestTheTotalOfTokens(WithAPaidFolder):
    def test_the_provider_total_is_read_and_kept_and_a_bad_one_is_dropped(self):
        self.assertEqual(usage_from({"p": 10, "c": 20, "t": 45}, "p", "c", (), "t"), Usage(10, 20, None, 45))
        self.assertEqual(usage_from({"p": 10, "c": 20, "t": "45"}, "p", "c", (), "t"), Usage(10, 20, None, None))
        self.assertEqual(usage_from({"p": 10, "c": 20}, "p", "c"), Usage(10, 20, None, None))

    def test_google_gives_its_total_and_the_line_keeps_it_with_the_difference_from_input_plus_output(self):
        provider = GoogleProvider(model=REQUESTED, api_key=SENTINEL, max_tokens=1000, min_interval_s=0)
        net = Net((":generateContent", {**fx.GOOGLE_OK, "modelVersion": REQUESTED}))
        with mock.patch(URLOPEN, net):
            run([a_case("C1")], provider, path=self.answers, run_id="r1", config=self.config(), paid=self.paid())
        (line,) = read_records(self.folder / FILE_NAME)
        self.assertEqual((line.input_tokens, line.output_tokens, line.reasoning_tokens), (130, 700, 450))
        self.assertEqual((line.total_tokens, line.total_difference), (1280, 450))  # 1280 - (130 + 700) = the thinking tokens

    def test_when_the_total_equals_input_plus_output_the_difference_is_zero_and_when_it_is_missing_there_is_none(self):
        for usage, expected in (({"promptTokenCount": 130, "candidatesTokenCount": 700, "totalTokenCount": 830}, (830, 0)),
                                ({"promptTokenCount": 130, "candidatesTokenCount": 700}, (None, None))):
            provider = GoogleProvider(model=REQUESTED, api_key=SENTINEL, max_tokens=1000, min_interval_s=0)
            net = Net((":generateContent", {**fx.GOOGLE_OK, "usageMetadata": usage, "modelVersion": REQUESTED}))
            folder = self.folder / str(expected[0])
            folder.mkdir()
            from aferidor.custos import Ledger
            from aferidor.pago import PaidCalls
            paid = PaidCalls(catalog=self.catalog, model_key="pago", ledger=Ledger(folder / "custos.jsonl"), provenance_file=folder / FILE_NAME,
                             ensaio="e1", ceiling_eur=Decimal(1), catalog_path=self.catalog_file, day=self.paid().day)
            with mock.patch(URLOPEN, net):
                run([a_case("C1")], provider, path=folder / "r.jsonl", run_id="r1", config=self.config(), paid=paid)
            (line,) = read_records(folder / FILE_NAME)
            self.assertEqual((line.total_tokens, line.total_difference), expected)

    def test_the_report_says_where_the_difference_comes_from(self):
        answers, records = scenario("anthropic:modelo-a", answered=3)
        records = [replace(r, reasoning_tokens=450, total_tokens=1280, total_difference=450) for r in records]
        run_ = analyse(Files(records=tuple(records)), CASES20, answers, grade_all(CASES20, answers)[0]).models[0]
        self.assertIn("total de tokens declarado pelo fornecedor em 3 chamadas; a diferença para entrada mais saída é igual aos "
                      "tokens de pensamento em 3, zero em 0 e outra em 0", execucao.condition_lines(run_))
        records = [replace(r, total_tokens=830, total_difference=0) for r in records]
        run_ = replace(run_, records=tuple(records))
        self.assertTrue(any("zero em 3" in line for line in execucao.condition_lines(run_)))


class TestTheReportKeepsTheProviderApartFromTheModel(unittest.TestCase):
    def build(self):
        answers, records = scenario("anthropic:modelo-a", answered=88, applied=1.0)
        # twelve samples never answered: five attempts each by an unavailable provider, one by an authentication problem
        extra = []
        keys = [(c.case_id, s) for c in CASES20 for s in range(1, 6)][88:]
        for i, (case, sample) in enumerate(keys):
            klass, status = ("limite_429", 429) if i < 6 else (("indisponivel_503", 503) if i < 10 else (("tempo_esgotado", None) if i < 11 else ("autenticacao", 401)))
            extra.append(rec("anthropic:modelo-a", case, sample, "erro", error_class=klass, http_status=status,
                             error_message=f"HTTP {status}: indisponível" if status else "sem resposta ao fim de 300 s"))
        return answers, Files(records=tuple(records + extra))

    def test_the_failures_are_counted_by_class_and_the_unanswered_samples_are_said_to_be_the_providers(self):
        answers, files = self.build()
        run_ = analyse(files, CASES20, answers, grade_all(CASES20, answers)[0]).models[0]
        self.assertEqual(run_.failures, {"limite_429": 6, "indisponivel_503": 4, "tempo_esgotado": 1, "autenticacao": 1})
        self.assertEqual((run_.unanswered_unavailable, run_.unanswered_other_error), (11, 1))
        md, _ = reports(answers, files)
        self.assertIn("> **Falhas do fornecedor.**", md)
        self.assertIn("anthropic:modelo-a: 12 tentativas falharam (limite de pedidos (429) 6, "
                      "serviço indisponível (503) 4, tempo esgotado 1, autenticação recusada 1); 11 amostras ficaram por responder por indisponibilidade "
                      "do fornecedor e 1 por outro erro do pedido.", md)
        self.assertIn("nunca conta como resposta errada, em nenhuma contagem", md)

    def test_an_unanswered_sample_for_unavailability_is_not_a_wrong_answer_nor_an_unanswered_reply_of_the_model(self):
        answers, files = self.build()
        verdicts, _ = grade_all(CASES20, answers)
        run_ = analyse(files, CASES20, answers, verdicts).models[0]
        self.assertEqual((run_.unanswered, run_.received, run_.answered), (0, 88, 88))  # not in the model's share of unanswered
        self.assertFalse(run_.over_limit)
        self.assertEqual(len(verdicts), 88)  # and not in the verdicts
        md, _ = reports(answers, files)
        self.assertNotIn("não comparável", md)

    def test_a_sample_that_failed_and_was_then_answered_is_not_left_over(self):
        answers, records = scenario("anthropic:modelo-a", answered=100)
        records.insert(0, rec("anthropic:modelo-a", "C01", 1, "erro", error_class="indisponivel_503", http_status=503, error_message="HTTP 503"))
        run_ = analyse(Files(records=tuple(records)), CASES20, answers, grade_all(CASES20, answers)[0]).models[0]
        self.assertEqual((run_.failures, run_.unanswered_unavailable, run_.unanswered_other_error), ({"indisponivel_503": 1}, 0, 0))

    def test_without_failures_the_notice_is_not_there(self):
        answers, records = scenario("anthropic:modelo-a", answered=100)
        md, _ = reports(answers, Files(records=tuple(records)))
        self.assertNotIn("Falhas do fornecedor", md)

    def test_in_every_language_without_a_missing_translation_and_the_last_message_is_shown(self):
        answers, files = self.build()
        traducao.MISSING.clear()
        md, html = reports(answers, files)
        self.assertEqual(sorted(traducao.MISSING), [])
        self.assertIn("Última mensagem: HTTP 401: indisponível", md)
        self.assertIn("Provider failures.", html["en"])
        self.assertIn("Ausfälle des Anbieters.", html["de"])
        self.assertIn("request limit (429) 6", html["en"].replace("&amp;", "&"))

    def test_lines_without_a_class_count_as_other_errors(self):
        answers, records = scenario("anthropic:modelo-a", answered=99)
        records.append(rec("anthropic:modelo-a", "C20", 5, "erro"))
        run_ = analyse(Files(records=tuple(records)), CASES20, answers, grade_all(CASES20, answers)[0]).models[0]
        self.assertEqual((run_.failures, run_.unanswered_other_error), ({"outro": 1}, 1))


if __name__ == "__main__":
    unittest.main()
