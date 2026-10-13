"""The reports of a paid run: what was not answered, the conditions per model, the cost. Temporary folders, hand-made
provenance lines, no network. And that a trial without those files reports exactly as it always did."""

from __future__ import annotations

import contextlib
import functools
import io
import json
import os
import re
import socket
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (a importação fixa a raiz das chaves numa pasta vazia)
from aferidor import cli, execucao, html_report, traducao
from aferidor import report as markdown
from aferidor.custos import Ledger
from aferidor.execucao import UNANSWERED_LIMIT_PERCENT, Files, analyse
from aferidor.grading import grade_all
from aferidor.proveniencia import FILE_NAME, append_record
from aferidor.storage import append_answer, case_to_dict, read_answers
from tests.helpers import a_case, an_answer
from tests.html_support import panel_html, visible
from tests.test_custos import CATALOG, DAY
from tests.test_fornecedores import Net, fx
from tests.test_proveniencia import record

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 10, 10)
CASES20 = [a_case(f"C{i:02d}") for i in range(1, 21)]
ANSWER = "Amoxicilina 1000 mg de 8 em 8 horas"
REFUSAL = "Lamento, mas não posso fornecer essa informação."


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


PERIOD = {"entrada_por_milhao": "2", "saida_por_milhao": "10", "moeda": "USD", "valido_de": None, "valido_ate": None,
          "prompt_tokens_ate": None, "origem": "pagina_oficial", "fonte": "https://exemplo.test/precos", "lido_em": "2026-10-11"}


def rec(model, case, sample, state="resposta", **over):
    return record(model=model, case_id=case, sample=sample, state=state, run_id="r1", **{"price_period": PERIOD, **over})


def scenario(model, answered, api=0, truncated=0, empty=0, text=0, applied=1.0, mode="pior_caso", cost="0.01"):
    """Answers and provenance for one model over 20 cases x 5 samples: `answered` kept (the first `text` of them
    refusals in the text), then `api`, `truncated` and `empty` replies that are not answers."""
    keys = [(c.case_id, s) for c in CASES20 for s in range(1, 6)]
    answers, records = [], []
    for i, (case, sample) in enumerate(keys[:answered]):
        answers.append(an_answer(REFUSAL if i < text else ANSWER, case_id=case, model=model, sample=sample))
        records.append(rec(model, case, sample, applied_params={"temperatura": applied, "tokens_max": 8192, "campo_tokens": "max_tokens"},
                           count_mode=mode, cost_eur=Decimal(cost)))
    rest = keys[answered:]
    for state, n in (("recusa_api", api), ("truncada", truncated), ("vazia", empty)):
        for case, sample in rest[:n]:
            records.append(rec(model, case, sample, state, applied_params={"temperatura": applied},
                               count_mode=mode, cost_eur=Decimal(cost)))
        rest = rest[n:]
    return answers, records


def without_notices(page: str) -> str:
    """The page without its notices (`<div class="aviso">`, nested divs and all)."""
    marker = '<div class="aviso" role="note">'
    while marker in page:
        start = page.index(marker)
        depth, i = 0, start
        for tag in re.finditer(r"<div\b|</div>", page[start:]):
            depth += 1 if tag.group(0).startswith("<div") else -1
            if depth == 0:
                i = start + tag.end()
                break
        page = page[:start] + page[i:]
    return page


def two_models(a_kw, b_kw):
    first_answers, first_records = scenario("anthropic:modelo-a", **a_kw)
    second_answers, second_records = scenario("openai:modelo-b", **b_kw)
    return first_answers + second_answers, Files(records=tuple(first_records + second_records))


def reports(answers, files):
    verdicts, missing = grade_all(CASES20, answers)
    md = markdown.build(CASES20, answers, verdicts, missing=missing, today=TODAY, execution=files)
    out = {lang: html_report.build(CASES20, answers, verdicts, missing=missing, today=TODAY, lingua=lang, execution=files)
           for lang in ("pt", "en", "es", "fr", "de")}
    return md, out


class TestWhatWasNotAnswered(unittest.TestCase):
    def test_a_model_over_the_limit_is_marked_not_comparable_and_one_under_it_is_not(self):
        answers, files = two_models(dict(answered=88, api=7, truncated=3, empty=2), dict(answered=97, api=1, truncated=1, empty=1))
        run_a, run_b = analyse(files, CASES20, answers, grade_all(CASES20, answers)[0]).models
        self.assertEqual((run_a.received, run_a.unanswered, run_a.over_limit), (100, 12, True))
        self.assertEqual((run_b.received, run_b.unanswered, run_b.over_limit), (100, 3, False))
        md, html = reports(answers, files)
        self.assertIn("anthropic:modelo-a: 12,0% das respostas do fornecedor ficaram sem resposta (12 de 100), acima do limite de 10%: "
                      "não comparável com os restantes.", md)
        self.assertEqual(md.count("não comparável com os restantes"), 1)
        self.assertIn("anthropic:modelo-a: 12 de 100 respostas do fornecedor sem resposta (12,0%): 7 recusadas pelo fornecedor, "
                      "0 recusadas no texto, 3 truncadas, 2 vazias.", md)
        self.assertIn("openai:modelo-b: 3 de 100 respostas do fornecedor sem resposta (3,0%)", md)
        text = visible(html["pt"])
        self.assertEqual(text.count("não comparável com os restantes"), 1)
        self.assertIn("Não comparável.", text)

    def test_the_limit_is_a_named_constant_and_it_is_more_than_ten_percent_not_ten(self):
        self.assertEqual(UNANSWERED_LIMIT_PERCENT, 10)
        answers, files = two_models(dict(answered=90, api=10), dict(answered=89, api=11))
        run_a, run_b = analyse(files, CASES20, answers, grade_all(CASES20, answers)[0]).models
        self.assertEqual((run_a.over_limit, run_b.over_limit), (False, True))  # exactly 10% is not more than 10%
        import inspect
        self.assertIn("UNANSWERED_LIMIT_PERCENT", inspect.getsource(execucao.ModelRun.over_limit.fget))

    def test_refusals_in_the_text_count_as_unanswered_here_and_stay_failures_in_the_counts(self):
        answers, files = two_models(dict(answered=90, api=5, text=5), dict(answered=100))
        verdicts, _ = grade_all(CASES20, answers)
        run_a = analyse(files, CASES20, answers, verdicts).models[0]
        self.assertEqual((run_a.text_refusals, run_a.api_refusals, run_a.unanswered, run_a.received), (5, 5, 10, 95))
        failed_in_text = sum(1 for v in verdicts if v.model == "anthropic:modelo-a" and "recusa_indevida" in {f.value for f in v.failures})
        self.assertEqual(failed_in_text, 5)  # the grader's own classification, untouched

    def test_the_denominator_of_the_counts_is_what_it_was_and_the_report_only_adds(self):
        answers, files = two_models(dict(answered=88, api=7, truncated=3, empty=2), dict(answered=97, api=1, truncated=1, empty=1))
        verdicts, missing = grade_all(CASES20, answers)
        old = markdown.build(CASES20, answers, verdicts, missing=missing, today=TODAY)
        new = markdown.build(CASES20, answers, verdicts, missing=missing, today=TODAY, execution=files)
        old_lines, new_lines = old.splitlines(), new.splitlines()
        position = 0
        for line in old_lines:
            position = new_lines.index(line, position) + 1  # every old line is there, in order
        self.assertGreater(len(new_lines), len(old_lines))
        html_old = html_report.build(CASES20, answers, verdicts, missing=missing, today=TODAY)
        html_new = html_report.build(CASES20, answers, verdicts, missing=missing, today=TODAY, execution=files)
        notices = without_notices
        for page in ("inicio", "resultados", "areas", "casos", "conclusoes"):
            self.assertEqual(notices(panel_html(html_new, page)), notices(panel_html(html_old, page)), page)
        self.assertIn("Amostras não respondidas.", panel_html(html_new, "resultados"))

    def test_the_report_says_they_were_not_repeated_and_count_as_neither_right_nor_wrong(self):
        answers, files = two_models(dict(answered=88, api=12), dict(answered=100))
        md, _ = reports(answers, files)
        self.assertIn("não foram repetidas e não contam como certas nem como erradas", md)

    def test_a_sample_that_was_refused_and_then_answered_is_an_answer(self):
        answers, records = scenario("openai:modelo-b", answered=100)
        records.insert(0, rec("openai:modelo-b", "C01", 1, "recusa_api"))
        run_b = analyse(Files(records=tuple(records)), CASES20, answers, grade_all(CASES20, answers)[0]).models[0]
        self.assertEqual((run_b.api_refusals, run_b.received), (0, 100))

    def test_a_model_all_of_whose_replies_were_refused_is_named_all_the_same(self):
        answers, records = scenario("anthropic:modelo-a", answered=0, api=50)
        other, other_records = scenario("openai:modelo-b", answered=100)
        files = Files(records=tuple(records + other_records))
        md, _ = reports(other, files)
        self.assertIn("anthropic:modelo-a: 50 de 50 respostas do fornecedor sem resposta (100,0%)", md)
        self.assertIn("não comparável com os restantes", md)

    def test_a_model_without_provenance_gets_one_neutral_line(self):
        paid, records = scenario("openai:modelo-b", answered=100)
        local = [an_answer(ANSWER, case_id=c.case_id, model="local:gemma", sample=s) for c in CASES20 for s in range(1, 6)]
        md, _ = reports(paid + local, Files(records=tuple(records)))
        self.assertIn("Sem registo de proveniência: local:gemma.", md)
        self.assertNotIn("local:gemma: ", md.split("Sem registo")[0].split("Amostras não respondidas")[-1])


class TestTheConditionsPerModel(unittest.TestCase):
    def setUp(self):
        answers, records = scenario("anthropic:modelo-a", answered=100, applied="ausente", mode="usage")
        self.answers, self.files = answers, Files(records=tuple(records))
        self.run = analyse(self.files, CASES20, answers, grade_all(CASES20, answers)[0]).models[0]

    def test_it_says_asked_served_confirmation_temperature_tokens_counting_price_rate_and_catalogue(self):
        lines = execucao.condition_lines(self.run)
        joined = "\n".join(lines)
        self.assertIn("modelo pedido modelo-falso; modelo servido modelo-falso (confirmado em 100 chamadas)", joined)
        self.assertIn("temperatura pedida 1,0; temperatura aplicada ausente (corre à temperatura do próprio fornecedor) "
                      "(não confirmada pelo fornecedor)", joined)
        self.assertIn("limite de tokens 8192, no campo max_tokens", joined)
        self.assertIn("custo contado pelo usage declarado (catálogo sem contagem)", joined)
        self.assertIn("USD, por cada milhão de tokens: entrada 2, saída 10; válido de - até -; lido em 2026-10-11 "
                      "(https://exemplo.test/precos)", joined)
        self.assertIn("taxa de câmbio 0,5 EUR por cada USD (teste)", joined)
        self.assertIn("catálogo de modelos e preços, SHA-256 " + "a" * 12, joined)

    def test_the_served_model_that_was_not_declared_or_that_differs_is_said(self):
        _, records = scenario("anthropic:modelo-a", answered=3)
        records[0] = rec("anthropic:modelo-a", "C01", 1, served_model="", served_check="nao_declarado")
        records[1] = rec("anthropic:modelo-a", "C01", 2, served_model="outro", served_check="diferente")
        run_ = execucao.ModelRun("anthropic:modelo-a", 3, 0, 0, 0, 0, tuple(records))
        line = execucao.condition_lines(run_)[0]
        self.assertIn("não declarado em 1 chamadas", line)
        self.assertIn("diferente do pedido em 1 chamadas", line)
        self.assertIn("confirmado em 1 chamadas", line)

    def test_the_provider_confirming_the_temperature_is_said(self):
        _, records = scenario("anthropic:modelo-a", answered=2)
        records = [rec("anthropic:modelo-a", "C01", n, applied_params={"temperatura": 1.0, "confirmado_pelo_fornecedor": True}) for n in (1, 2)]
        line = execucao.condition_lines(execucao.ModelRun("m", 2, 0, 0, 0, 0, tuple(records)))[1]
        self.assertIn("(confirmada pelo fornecedor)", line)

    def test_the_conditions_are_in_both_reports_and_in_every_language_without_a_missing_translation(self):
        traducao.MISSING.clear()
        md, html = reports(self.answers, self.files)
        self.assertIn("## Proveniência e custo", md)
        self.assertIn("modelo servido modelo-falso", md)
        for lang, page in html.items():
            with self.subTest(lingua=lang):
                self.assertIn('id="proveniencia"', page)
                block = page[page.index('id="proveniencia"'):]
                block = block[:block.index("</div>")]
                self.assertNotRegex(block, r"\{\w+\}")
        self.assertEqual(sorted(traducao.MISSING), [])
        self.assertIn("Proveniência e custo", html["pt"])
        self.assertIn("Provenance and cost", html["en"])


class TestDifferentTemperatures(unittest.TestCase):
    def notice(self, a_applied, b_applied, local=None):
        first, first_records = scenario("anthropic:modelo-a", answered=100, applied=a_applied)
        second, second_records = scenario("openai:modelo-b", answered=100, applied=b_applied)
        extra = [an_answer(ANSWER, case_id=c.case_id, model="local:gemma", sample=s) for c in CASES20 for s in range(1, 6)] if local else []
        md, _ = reports(first + second + extra, Files(records=tuple(first_records + second_records)))
        return md

    def test_an_absent_temperature_next_to_an_applied_one_says_the_comparison_is_not_under_identical_conditions(self):
        md = self.notice("ausente", 1.0)
        self.assertIn("Os modelos não correram com a mesma temperatura aplicada", md)
        self.assertIn("anthropic:modelo-a: ausente (corre à temperatura do próprio fornecedor); openai:modelo-b: 1,0", md)
        self.assertIn("A comparação entre fornecedores não é feita em condições idênticas.", md)

    def test_two_different_numbers_say_it_too_and_equal_ones_do_not(self):
        self.assertIn("mesma temperatura aplicada", self.notice(1.0, 0.5))
        self.assertNotIn("mesma temperatura aplicada", self.notice(1.0, 1.0))
        self.assertNotIn("mesma temperatura aplicada", self.notice("ausente", "ausente"))

    def test_a_model_without_provenance_counts_with_the_temperature_its_answers_carry(self):
        self.assertNotIn("mesma temperatura aplicada", self.notice(0.0, 0.0, local=True))  # an_answer's own temperature is 0.0
        self.assertIn("mesma temperatura aplicada", self.notice(1.0, 1.0, local=True))

    def test_the_warning_is_in_the_html_in_every_language(self):
        first, first_records = scenario("anthropic:modelo-a", answered=100, applied="ausente")
        second, second_records = scenario("openai:modelo-b", answered=100, applied=1.0)
        _, html = reports(first + second, Files(records=tuple(first_records + second_records)))
        self.assertIn("conditions", visible(html["en"]).replace("under identical conditions", "conditions"))
        self.assertIn("Different temperatures.", html["en"])
        self.assertIn("Unterschiedliche Temperaturen.", html["de"])


class TestTheCost(unittest.TestCase):
    def files(self, records, ledger=None, pilot_records=(), pilot_ledger=None):
        return Files(records=tuple(records), ledger=ledger, pilot_records=tuple(pilot_records), pilot_ledger=pilot_ledger)

    def lines(self, files, answers):
        analysis = analyse(files, CASES20, answers, grade_all(CASES20, answers)[0])
        return execucao.cost_lines(analysis)

    def test_by_usage_and_by_worst_case_are_told_apart_per_model_and_in_total(self):
        a_answers, a_records = scenario("anthropic:modelo-a", answered=10, mode="usage", cost="0.5")
        b_answers, b_records = scenario("openai:modelo-b", answered=10, mode="pior_caso", cost="0.25")
        ledger = {"gasto_eur": Decimal("7.5"), "por_liquidar_eur": Decimal(0)}
        lines = self.lines(self.files(a_records + b_records, ledger), a_answers + b_answers)
        self.assertIn("Custo do ensaio: 7,5000 EUR, dos quais 5,0000 EUR pelo usage declarado e 2,5000 EUR pelo pior caso.", lines)
        self.assertIn("anthropic:modelo-a: 5,0000 EUR pelo usage declarado, 0,0000 EUR pelo pior caso", lines)
        self.assertIn("openai:modelo-b: 0,0000 EUR pelo usage declarado, 2,5000 EUR pelo pior caso", lines)

    def test_a_worst_case_figure_says_it_is_a_maximum_and_not_the_invoice(self):
        answers, records = scenario("openai:modelo-b", answered=10, mode="pior_caso", cost="0.25")
        lines = self.lines(self.files(records, {"gasto_eur": Decimal("2.5"), "por_liquidar_eur": Decimal(0)}), answers)
        self.assertTrue(any("é um máximo, não a fatura" in line for line in lines))

    def test_a_cost_all_by_usage_does_not_say_it(self):
        answers, records = scenario("anthropic:modelo-a", answered=10, mode="usage", cost="0.5")
        lines = self.lines(self.files(records, {"gasto_eur": Decimal(5), "por_liquidar_eur": Decimal(0)}), answers)
        self.assertFalse(any("máximo" in line for line in lines))

    def test_calls_still_to_settle_are_shown_and_are_a_maximum_too(self):
        answers, records = scenario("anthropic:modelo-a", answered=10, mode="usage", cost="0.5")
        ledger = {"gasto_eur": Decimal("5.3"), "por_liquidar_eur": Decimal("0.3")}
        lines = self.lines(self.files(records, ledger), answers)
        self.assertIn("e 0,3000 EUR de chamadas por liquidar, também no pior caso", lines[0])
        self.assertTrue(any("máximo" in line for line in lines))

    def test_the_pilot_is_counted_apart_and_not_in_the_trials_total(self):
        answers, records = scenario("anthropic:modelo-a", answered=10, mode="usage", cost="0.5")
        pilot = [rec("anthropic:modelo-a", "C01", 1, count_mode="pior_caso", cost_eur=Decimal("0.2"))]
        lines = self.lines(self.files(records, {"gasto_eur": Decimal(5), "por_liquidar_eur": Decimal(0)}, pilot,
                                      {"gasto_eur": Decimal("0.2"), "por_liquidar_eur": Decimal(0)}), answers)
        self.assertEqual(lines[0].split(",")[0], "Custo do ensaio: 5")
        pilot_line = next(line for line in lines if line.startswith("Custo do piloto, contado à parte do ensaio"))
        self.assertIn("0,2000 EUR", pilot_line)
        self.assertNotIn("0,2000", lines[0])

    def test_without_a_ledger_the_total_is_what_the_provenance_adds_up_to(self):
        answers, records = scenario("anthropic:modelo-a", answered=10, mode="usage", cost="0.5")
        self.assertIn("Custo do ensaio: 5,0000 EUR", self.lines(self.files(records), answers)[0])

    def test_the_cost_is_in_both_reports(self):
        answers, records = scenario("anthropic:modelo-a", answered=10, mode="pior_caso", cost="0.5")
        md, html = reports(answers, self.files(records, {"gasto_eur": Decimal(5), "por_liquidar_eur": Decimal(0)}))
        self.assertIn("Custo do ensaio: 5,0000 EUR", md)
        self.assertIn("Cost of the trial: 5.0000 EUR", visible(html["en"]))


class TestNothingNewWhenThereIsNoNewData(unittest.TestCase):
    def test_without_files_or_with_files_of_no_model_of_the_report_the_reports_are_identical(self):
        answers = [an_answer(ANSWER, case_id=c.case_id, model="local:gemma", sample=s) for c in CASES20 for s in range(1, 3)]
        verdicts, missing = grade_all(CASES20, answers)
        plain_md = markdown.build(CASES20, answers, verdicts, missing=missing, today=TODAY)
        plain_html = {l: html_report.build(CASES20, answers, verdicts, missing=missing, today=TODAY, lingua=l) for l in ("pt", "en")}
        elsewhere = Files(records=(rec("outro:modelo", "FORA-DO-BANCO", 1),), ledger={"gasto_eur": Decimal(0), "por_liquidar_eur": Decimal(0)})
        for files in (None, Files(), elsewhere):
            with self.subTest(files=type(files).__name__):
                self.assertEqual(markdown.build(CASES20, answers, verdicts, missing=missing, today=TODAY, execution=files), plain_md)
                for lang, page in plain_html.items():
                    self.assertEqual(html_report.build(CASES20, answers, verdicts, missing=missing, today=TODAY, lingua=lang,
                                                       execution=files), page)

    def test_a_folder_of_the_old_trials_has_no_files_to_read(self):
        for folder in sorted((ROOT / "ensaios").iterdir()):
            with self.subTest(ensaio=folder.name):
                self.assertIsNone(execucao.load(folder / "respostas.jsonl"))

    def test_the_published_example_comes_out_the_same_through_the_command_line_with_the_new_code(self):
        """The recipe of docs/COMO_CORRER.md section 14, with the day it was written. The only line that differs from
        the committed file is the one that copies the test count from the README, which moves with every commit. The
        published corrector's side of the page is read from `docs/exemplo/antes-8edda161.json`, as the recipe says."""
        written = re.search(r"Relatório escrito em (\d{4})-(\d{2})-(\d{2})", (ROOT / "docs" / "exemplo" / "index.html").read_text(encoding="utf-8"))
        day = date(*map(int, written.groups()))
        with tempfile.TemporaryDirectory() as folder:
            joined = Path(folder) / "respostas.jsonl"
            joined.write_bytes(b"".join((ROOT / "ensaios" / d / "respostas.jsonl").read_bytes() for d in (
                "2026-09-29-gemma4-31b-casos", "2026-09-28-gemini-flash", "2026-09-27-locais-12-14b")))
            real = html_report.build
            before = os.getcwd()
            os.chdir(ROOT)  # the report prints the path it was given: as in the recipe, a relative one
            try:
                with mock.patch.object(html_report, "build", functools.partial(real, today=day)), \
                        contextlib.redirect_stdout(io.StringIO()):
                    code = cli.main(["relatorio", "--formato", "html", "--linguas", "pt,en,es,fr,de", "--casos", "casos/casos.json",
                                     "--respostas", str(joined), "--antes", "docs/exemplo/antes-8edda161.json",
                                     "--leitura", "docs/LEITURA_MUDANCAS_2026-10-12.md",
                                     "--saida", str(Path(folder) / "index.html")])
            finally:
                os.chdir(before)
            self.assertEqual(code, 0)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()),
                             sorted(["respostas.jsonl", "index.html", "index.en.html", "index.es.html", "index.fr.html", "index.de.html"]))
            for name in ("index.html", "index.en.html", "index.es.html", "index.fr.html", "index.de.html"):
                with self.subTest(pagina=name):
                    made = (Path(folder) / name).read_text(encoding="utf-8")
                    published = (ROOT / "docs" / "exemplo" / name).read_text(encoding="utf-8")
                    count = lambda text: re.sub(r"\b\d{3,5} testes", "N testes", text)
                    self.assertEqual(count(made), count(published))
                    self.assertNotIn('id="proveniencia"', made)


class TestFromTheFilesOnDisk(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.folder = Path(self._dir.name) / "meu-ensaio"
        self.folder.mkdir()
        self.answers_file = self.folder / "respostas.jsonl"

    def test_the_trial_and_its_pilot_are_read_from_beside_the_answers(self):
        append_record(self.folder / FILE_NAME, rec("m", "C01", 1))
        (self.folder / "piloto").mkdir()
        append_record(self.folder / "piloto" / FILE_NAME, rec("m", "C02", 1))
        trial_id, pilot_id = execucao.ensaio_ids(self.folder)
        self.assertEqual((trial_id, pilot_id), ("meu-ensaio", "meu-ensaio/piloto"))
        reserve = lambda ledger, ensaio: ledger.reserve(catalog=CATALOG, ensaio=ensaio, run_id="r", model_key="pago", case_id="C1",
                                                       sample=1, prompt="x" * 300, tokens_max=1000, day=DAY, ceiling_eur=1)
        reserve(Ledger(self.folder / "custos.jsonl"), trial_id)
        reserve(Ledger(self.folder / "piloto" / "custos.jsonl"), pilot_id)
        files = execucao.load(self.answers_file)
        self.assertEqual((len(files.records), len(files.pilot_records)), (1, 1))
        self.assertEqual((files.ledger["chamadas"], files.pilot_ledger["chamadas"], files.ledger["sem_resultado"]), (1, 1, 1))
        self.assertEqual(files.ledger["gasto_eur"], files.ledger["por_liquidar_eur"])

    def test_a_report_over_the_pilot_folder_itself_reads_the_pilots_ledger_under_its_own_id(self):
        """The pilot's ledger names its trial `<folder>/piloto`. Looking from inside the pilot folder used to ask for
        the id `piloto` and find nothing, so the cost showed as zero."""
        pilot = self.folder / "piloto"
        pilot.mkdir()
        trial_id, pilot_id = execucao.ensaio_ids(self.folder)
        Ledger(pilot / "custos.jsonl").reserve(
            catalog=CATALOG, ensaio=pilot_id, run_id="r", model_key="pago", case_id="C1", sample=1,
            prompt="x" * 300, tokens_max=1000, day=DAY, ceiling_eur=1)
        append_record(pilot / FILE_NAME, rec("m", "C01", 1, count_mode="pior_caso", cost_eur=Decimal("0.2")))
        files = execucao.load(pilot / "respostas.jsonl")
        self.assertEqual((files.ledger["chamadas"], files.ledger["sem_resultado"]), (1, 1))
        self.assertGreater(files.ledger["gasto_eur"], 0)
        self.assertTrue(files.is_pilot)
        answers, _ = scenario("m", answered=1, mode="pior_caso", cost="0.2")
        analysis = analyse(files, CASES20, answers, grade_all(CASES20, answers)[0])
        lines = execucao.cost_lines(analysis)
        self.assertTrue(lines[0].startswith("Custo do piloto, contado à parte do ensaio: 0,0"), lines[0])
        self.assertNotIn(": 0,0000 EUR", lines[0])

    def test_from_the_trial_folder_the_pilot_is_still_read_as_before(self):
        (self.folder / "piloto").mkdir()
        _, pilot_id = execucao.ensaio_ids(self.folder)
        Ledger(self.folder / "piloto" / "custos.jsonl").reserve(
            catalog=CATALOG, ensaio=pilot_id, run_id="r", model_key="pago", case_id="C1", sample=1,
            prompt="x" * 300, tokens_max=1000, day=DAY, ceiling_eur=1)
        files = execucao.load(self.answers_file)
        self.assertEqual((files.pilot_ledger["chamadas"], files.is_pilot), (1, False))

    def test_reading_creates_nothing(self):
        self.assertIsNone(execucao.load(self.answers_file))
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_a_corrupt_provenance_file_is_an_error_message_and_no_report(self):
        (self.folder / FILE_NAME).write_text("lixo\n" + json.dumps({"a": 1}) + "\n", encoding="utf-8")
        append_answer(an_answer(ANSWER), self.answers_file)
        cases_file = self.folder / "casos.json"
        cases_file.write_text(json.dumps([case_to_dict(a_case())]), encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(["relatorio", "--casos", str(cases_file), "--respostas", str(self.answers_file), "--saida", str(self.folder / "r.md")])
        self.assertEqual(code, 2)
        self.assertIn("corrompida", err.getvalue())
        self.assertFalse((self.folder / "r.md").exists())

    def test_a_run_where_every_reply_was_refused_leaves_files_that_say_so_and_no_answers(self):
        with mock.patch("aferidor.providers.urllib.request.urlopen", Net(("/v1/messages", fx.ANTHROPIC_REFUSAL))), \
                mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "chave-falsa-abcdef"}, clear=True), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cli.main(["executar", "--fornecedor", "anthropic", "--modelo", "claude-opus-5-5", "--casos", str(ROOT / "casos" / "casos.json"),
                      "--saida", str(self.answers_file), "--limite", "3", "--tokens-max", "8192", "--temperatura", "1.0",
                      "--teto-eur", "100", "--tentativas", "1"])
        self.assertFalse(self.answers_file.exists())  # nothing was an answer
        files = execucao.load(self.answers_file)
        self.assertEqual({r.state for r in files.records}, {"recusa_api"})
        self.assertEqual((len(files.records), files.ledger["chamadas"]), (3, 3))


class TestTheGeminiResumeWithoutADefault(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.saida = Path(self._dir.name) / "respostas.jsonl"

    def cli(self, net, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("aferidor.providers.urllib.request.urlopen", net), \
                mock.patch.dict(os.environ, {"GEMINI_API_KEY": "chave-falsa-abcdef", "AFERIDOR_GEMINI_INTERVALO": "0"}, clear=True), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["executar", "--fornecedor", "gemini", "--casos", str(ROOT / "casos" / "casos.json"), "--saida", str(self.saida),
                             "--temperatura", "1.0", "--tokens-max", "4096", *argv])
        return code, out.getvalue(), err.getvalue()

    def test_answers_already_in_the_file_are_kept_and_only_the_rest_is_asked_with_the_model_said_again(self):
        first = Net(("/openai/chat/completions", fx.OPENAI_OK))
        self.assertEqual(self.cli(first, "--modelo", "gemini-3.5-flash-lite", "--limite", "2")[0], 0)
        self.assertEqual(len(first.requests), 2)
        second = Net(("/openai/chat/completions", fx.OPENAI_OK))
        code, out, _ = self.cli(second, "--modelo", "gemini-3.5-flash-lite", "--limite", "3")
        self.assertEqual((code, len(second.requests)), (0, 1))
        self.assertEqual(len(read_answers(self.saida)), 3)
        self.assertEqual({a.model for a in read_answers(self.saida)}, {"gemini:gemini-3.5-flash-lite"})
        self.assertIn("2 já existentes", out)

    def test_without_the_model_it_does_not_resume_by_guessing_one(self):
        net = Net(("/openai/chat/completions", fx.OPENAI_OK))
        self.cli(net, "--modelo", "gemini-3.5-flash-lite", "--limite", "2")
        net2 = Net()
        code, _, err = self.cli(net2, "--limite", "3")
        self.assertEqual((code, net2.requests), (2, []))
        self.assertIn("precisa de --modelo", err)
        self.assertEqual(len(read_answers(self.saida)), 2)

    def test_a_stored_trial_of_the_gemini_is_still_readable_and_resumable_as_it_was(self):
        stored = ROOT / "ensaios" / "2026-09-28-gemini-flash" / "respostas.jsonl"
        self.saida.write_bytes(stored.read_bytes())
        net = Net()
        code, out, _ = self.cli(net, "--modelo", "gemini-3.5-flash-lite", "--repeticoes", "5", "--tokens-max", "8192")
        self.assertEqual((code, net.requests), (0, []))  # everything it asks was answered already
        self.assertIn("135 já existentes", out)
        self.assertEqual(self.saida.read_bytes(), stored.read_bytes())

    def test_the_listing_of_models_asks_no_model(self):
        net = Net(("/openai/models", {"data": [{"id": "models/gemini-3.8-flash"}]}))
        out = io.StringIO()
        with mock.patch("aferidor.providers.urllib.request.urlopen", net), \
                mock.patch.dict(os.environ, {"GEMINI_API_KEY": "chave-falsa-abcdef"}, clear=True), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["modelos", "--fornecedor", "gemini"])
        self.assertEqual(code, 0)
        self.assertIn("gemini-3.8-flash", out.getvalue())


if __name__ == "__main__":
    unittest.main()
