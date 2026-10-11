"""The provenance file beside the answers: what a paid call asked, was served, counted and cost, and how it
is tied to the answer it produced. No network; temporary files; made-up prices."""

from __future__ import annotations

import json
import shutil
import socket
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

from aferidor import grader_id
from aferidor.catalogo import DEFAULT_PATH, load_catalog
from aferidor.custos import JsonlError, Ledger
from aferidor.providers import FakeProvider
from aferidor.proveniencia import (
    FILE_NAME,
    ProvenanceError,
    ProvenanceRecord,
    append_record,
    catalog_sha256,
    check_served,
    period_snapshot,
    provenance_path,
    read_records,
    status_of,
    unmatched,
)
from aferidor.runner import RunConfig, run
from tests.helpers import a_case
from tests.test_custos import CATALOG, DAY, reserve

SHA = "a" * 64


def setUpModule() -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")
    patcher = mock.patch.object(socket.socket, "connect", refuse)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def record(**over) -> ProvenanceRecord:
    base = dict(
        run_id="r1", model="falso", case_id="C1", sample=1, attempt=1, catalog_key="pago", requested_model="modelo-falso",
        served_model="modelo-falso", requested_params={"temperatura": 1.0, "tokens_max": 8192, "campo_tokens": "max_tokens"},
        applied_params={"temperatura": 1.0, "tokens_max": 8192, "campo_tokens": "max_tokens"},
        input_tokens=120, output_tokens=900, reasoning_tokens=None, finish_reason="stop", finish_reason_original="end_turn",
        started_at="2026-10-11T10:00:00+00:00", ended_at="2026-10-11T10:00:04+00:00", latency_s=4.2,
        cost_usd=Decimal("0.0102"), cost_eur=Decimal("0.0051"), count_mode="pior_caso", count_reason="catálogo sem contagem",
        state="resposta", catalog_sha256=SHA, price_period={"entrada_por_milhao": "2"}, usd_to_eur=Decimal("0.5"),
        usd_to_eur_source="teste", build="0.1.0+x", grader=grader_id(),
    )
    return ProvenanceRecord(**{**base, **over})


class WithAFolder(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.folder = Path(self._dir.name)
        self.path = self.folder / FILE_NAME


class TestTheLines(WithAFolder):
    def test_a_line_keeps_everything_the_call_needs_to_be_audited(self):
        raw = record().to_dict()
        for field in ("id_pedido", "id_servido", "parametros_pedidos", "parametros_aplicados", "tokens_entrada", "tokens_saida",
                      "tokens_raciocinio", "finish_reason", "finish_reason_original", "inicio", "fim", "latencia_s", "tentativa",
                      "custo_usd", "custo_eur", "modo_contagem", "estado", "catalogo_sha256", "periodo_preco", "taxa_usd_eur",
                      "run_id", "modelo", "caso", "amostra", "build", "grader"):
            self.assertIn(field, raw)
        self.assertEqual((raw["id_pedido"], raw["id_servido"], raw["servido_declarado"]), ("modelo-falso", "modelo-falso", True))

    def test_it_round_trips_through_the_file(self):
        append_record(self.path, record())
        append_record(self.path, record(case_id="C2", reasoning_tokens=40, usd_to_eur=None))
        found = read_records(self.path)
        self.assertEqual(found, [record(), record(case_id="C2", reasoning_tokens=40, usd_to_eur=None)])

    def test_tokens_the_provider_did_not_give_stay_none_and_are_never_zero(self):
        append_record(self.path, record(input_tokens=None, output_tokens=None, reasoning_tokens=None, served_model=""))
        (found,) = read_records(self.path)
        self.assertEqual((found.input_tokens, found.output_tokens, found.reasoning_tokens), (None, None, None))
        self.assertFalse(found.served_declared)

    def test_a_missing_file_has_no_records_and_is_not_created_by_looking(self):
        self.assertEqual(read_records(self.path), [])
        self.assertFalse(self.path.exists())

    def test_the_file_sits_beside_the_answers(self):
        self.assertEqual(provenance_path("/x/ensaio/respostas.jsonl"), Path("/x/ensaio/respostas.proveniencia.jsonl"))

    def test_a_line_cut_short_is_dropped_and_a_corrupt_one_in_the_middle_is_refused(self):
        append_record(self.path, record())
        with self.path.open("ab") as handle:
            handle.write(b'{"run_id":"cort')
        self.assertEqual(len(read_records(self.path)), 1)
        append_record(self.path, record(case_id="C2"))
        self.assertEqual(len(read_records(self.path)), 2)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        lines[0] = "lixo"
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(JsonlError):
            read_records(self.path)

    def test_a_line_with_a_field_missing_is_refused(self):
        raw = record().to_dict()
        del raw["catalogo_sha256"]
        self.path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ProvenanceError, "não tem a forma esperada"):
            read_records(self.path)

    def test_invalid_values_are_refused_when_the_record_is_made(self):
        for over in ({"state": "talvez"}, {"count_mode": "adivinhado"}, {"sample": 0}, {"attempt": 0}, {"latency_s": -1},
                     {"catalog_sha256": ""}):
            with self.subTest(**over), self.assertRaises(ProvenanceError):
                record(**over)


class TestTheCatalogueIsKept(WithAFolder):
    def test_the_hash_is_the_sha256_of_the_file_on_disk(self):
        import hashlib
        self.assertEqual(catalog_sha256(), hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest())
        self.assertEqual(catalog_sha256(), catalog_sha256())

    def test_an_edited_price_changes_the_hash(self):
        copy = self.folder / "catalogo.json"
        shutil.copy(DEFAULT_PATH, copy)
        before = catalog_sha256(copy)
        data = json.loads(copy.read_text(encoding="utf-8"))
        data["modelos"]["gpt-6-luna"]["precos"][0]["saida_por_milhao"] = 0.51
        copy.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.assertNotEqual(catalog_sha256(copy), before)
        self.assertEqual(load_catalog(copy).model("gpt-6-luna").price_on(DAY).output_per_million, Decimal("0.51"))

    def test_a_changed_rate_or_source_also_changes_it(self):
        copy = self.folder / "catalogo.json"
        shutil.copy(DEFAULT_PATH, copy)
        before = catalog_sha256(copy)
        data = json.loads(copy.read_text(encoding="utf-8"))
        data["usd_para_eur"]["valor"] = 0.9
        copy.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.assertNotEqual(catalog_sha256(copy), before)

    def test_the_period_applied_is_kept_whole(self):
        flash = load_catalog().model("gemini-3.8-flash")
        snapshot = period_snapshot(flash.price_on(date(2027, 1, 1)))
        self.assertEqual((Decimal(snapshot["entrada_por_milhao"]), Decimal(snapshot["saida_por_milhao"])), (Decimal("1.5"), Decimal("7.5")))
        self.assertEqual((snapshot["valido_de"], snapshot["valido_ate"], snapshot["moeda"]), ("2027-01-01", None, "USD"))
        self.assertTrue(snapshot["fonte"].startswith("https://"))
        self.assertEqual(snapshot["lido_em"], "2026-10-11")
        json.dumps(snapshot)  # it has to be writable as it is

    def test_a_line_made_from_a_settled_call_carries_both(self):
        ledger = Ledger(self.folder / "custos.jsonl")
        reservation = reserve(ledger)
        outcome = ledger.settle(reservation.intent_id, catalog=CATALOG, state="resposta", usage={"input_tokens": 50, "output_tokens": 10})
        period = CATALOG.model("pago").price_on(DAY, 100)
        made = record(cost_usd=outcome.usd, cost_eur=outcome.eur, count_mode=outcome.count_mode, count_reason=outcome.reason,
                      price_period=period_snapshot(period), catalog_sha256=catalog_sha256())
        append_record(self.path, made)
        (found,) = read_records(self.path)
        self.assertEqual((found.cost_usd, found.count_mode), (outcome.usd, "pior_caso"))
        self.assertEqual(found.price_period["entrada_por_milhao"], "2")
        self.assertEqual(found.catalog_sha256, catalog_sha256())


class TestTheLinkToTheAnswers(WithAFolder):
    def answers(self):
        result = run([a_case("C1"), a_case("C2")], FakeProvider(default="Amoxicilina 1000 mg"), run_id="runX",
                     config=RunConfig(attempts=1), repetitions=2)
        return result.answers

    def records_for(self, answers):
        return [record(run_id=a.run_id, model=a.model, case_id=a.case_id, sample=a.sample) for a in answers]

    def test_every_answer_of_a_real_run_has_its_line_and_every_line_its_answer(self):
        answers = self.answers()
        self.assertEqual(len(answers), 4)
        self.assertEqual({a.run_id for a in answers}, {"runX"})
        self.assertEqual(unmatched(answers, self.records_for(answers)), ([], []))

    def test_an_answer_without_a_line_is_reported(self):
        answers = self.answers()
        records = self.records_for(answers)[1:]
        lonely, orphans = unmatched(answers, records)
        self.assertEqual(([(a.case_id, a.sample) for a in lonely], orphans), ([(answers[0].case_id, answers[0].sample)], []))

    def test_a_line_of_an_answer_that_does_not_exist_is_reported(self):
        answers = self.answers()
        extra = record(run_id="runX", model="falso", case_id="C9", sample=1)
        lonely, orphans = unmatched(answers, [*self.records_for(answers), extra])
        self.assertEqual((lonely, orphans), ([], [extra]))

    def test_the_run_and_the_sample_are_part_of_the_link(self):
        answers = self.answers()
        wrong_run = [record(run_id="outra", model=a.model, case_id=a.case_id, sample=a.sample) for a in answers]
        lonely, orphans = unmatched(answers, wrong_run)
        self.assertEqual((len(lonely), len(orphans)), (4, 4))

    def test_an_attempt_that_has_no_answer_by_design_is_not_an_orphan(self):
        answers = self.answers()
        others = [record(state=s, run_id="runX", case_id="C1", sample=7) for s in ("recusa_api", "truncada", "vazia", "erro", "resultado_desconhecido")]
        self.assertEqual(unmatched(answers, [*self.records_for(answers), *others]), ([], []))

    def test_a_retry_after_an_error_still_links_through_its_answered_line(self):
        answers = self.answers()
        retry = [record(state="erro", attempt=1, run_id=a.run_id, model=a.model, case_id=a.case_id, sample=a.sample) for a in answers]
        self.assertEqual(unmatched(answers, [*retry, *self.records_for(answers)]), ([], []))


class TestTheServedModel(unittest.TestCase):
    def test_the_same_id_is_equal_another_one_is_different_and_none_is_not_declared(self):
        self.assertEqual(check_served("a", "a").status, "igual")
        self.assertEqual(check_served("a", "b").status, "diferente")
        for none in (None, "", "   "):
            self.assertEqual(check_served("a", none).status, "nao_declarado")

    def test_only_a_different_one_says_to_stop(self):
        self.assertTrue(check_served("a", "b").stop)
        self.assertFalse(check_served("a", "a").stop)
        self.assertFalse(check_served("a", None).stop)

    def test_it_is_strict_a_dated_snapshot_is_different_until_someone_accepts_it(self):
        self.assertTrue(check_served("claude-x", "claude-x-20261001").stop)
        self.assertTrue(check_served("gemini-x", "models/gemini-x").stop)
        accepted = check_served("claude-x", "claude-x-20261001", accepted=["claude-x-20261001"])
        self.assertEqual((accepted.status, accepted.stop, accepted.served), ("igual", False, "claude-x-20261001"))
        self.assertTrue(check_served("claude-x", "claude-x-20261002", accepted=["claude-x-20261001"]).stop)

    def test_it_says_both_ids_so_the_run_can_write_the_fact(self):
        found = check_served("pedido", "servido")
        self.assertEqual((found.requested, found.served), ("pedido", "servido"))


class TestTheStateOfACall(unittest.TestCase):
    def test_from_the_finish_reason_and_the_text(self):
        self.assertEqual(status_of("stop", "Amoxicilina"), "resposta")
        self.assertEqual(status_of("filtered", ""), "recusa_api")
        self.assertEqual(status_of("filtered", "texto"), "recusa_api")
        self.assertEqual(status_of("length", "a meio"), "truncada")
        self.assertEqual(status_of("stop", "   \n"), "vazia")
        self.assertEqual(status_of("unknown", "texto"), "resposta")


if __name__ == "__main__":
    unittest.main()
