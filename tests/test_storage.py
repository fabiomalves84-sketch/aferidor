import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from aferidor.models import Answer, Case, Criterion, Source
from aferidor.risk import FailureType
from aferidor.storage import (
    read_answers,
    read_cases,
    write_answers,
)
from tests.helpers import a_two_regimen_case, an_answer, write_cases


def a_case(case_id: str = "C-001") -> Case:
    return Case(
        case_id=case_id,
        category="dose",
        question="Qual a dose habitual de amoxicilina oral no adulto?",
        reference="500 mg de 8 em 8 horas",
        source=Source("Infarmed", "RCM Amoxicilina, secção 4.2",
                      url="https://extranet.infarmed.pt", consulted=date(2026, 9, 14)),
        criteria=(
            Criterion("contem", ("500 mg",), FailureType.DOSE_INCORRETA, "a dose tem de aparecer"),
            Criterion("nao_contem", ("consulte o seu médico",), FailureType.RECUSA_INDEVIDA),
        ),
        notes="caso de arranque",
    )


class TestCaseRoundTrip(unittest.TestCase):
    def test_a_case_survives_a_write_and_a_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "casos.json"
            write_cases([a_case()], path)
            recovered = read_cases(path)
        self.assertEqual(recovered, [a_case()])

    def test_the_file_is_readable_portuguese_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "casos.json"
            write_cases([a_case()], path)
            text = path.read_text(encoding="utf-8")
        self.assertIn("pergunta", text)
        self.assertIn("secção 4.2", text)


class TestCaseValidation(unittest.TestCase):
    def _write(self, folder: str, payload) -> Path:
        path = Path(folder) / "casos.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_duplicate_ids_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            from aferidor.storage import case_to_dict
            path = self._write(folder, [case_to_dict(a_case()), case_to_dict(a_case())])
            with self.assertRaises(ValueError) as caught:
                read_cases(path)
        self.assertIn("repetido", str(caught.exception))

    def test_an_empty_file_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._write(folder, [])
            with self.assertRaises(ValueError):
                read_cases(path)

    def test_a_missing_field_names_the_case(self):
        with tempfile.TemporaryDirectory() as folder:
            from aferidor.storage import case_to_dict
            broken = case_to_dict(a_case())
            del broken["referencia"]
            path = self._write(folder, [broken])
            with self.assertRaises(ValueError) as caught:
                read_cases(path)
        self.assertIn("C-001", str(caught.exception))

    def test_an_unknown_failure_label_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            from aferidor.storage import case_to_dict
            broken = case_to_dict(a_case())
            broken["criterios"][0]["falha"] = "quase_certo"
            path = self._write(folder, [broken])
            with self.assertRaises(ValueError):
                read_cases(path)


class TestAnswerRoundTrip(unittest.TestCase):
    def test_answers_survive_a_write_and_a_read(self):
        answers = [
            Answer("C-001", "modelo-x", "500 mg 8/8h", datetime(2026, 9, 14, 10, 0), 812, "r1"),
            Answer("C-002", "modelo-x", "resposta\ncom quebra", datetime(2026, 9, 14, 10, 1), 640, "r1"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            self.assertEqual(write_answers(answers, path), 2)
            recovered = read_answers(path)
        self.assertEqual(recovered, answers)

    def test_a_failed_rewrite_leaves_the_file_as_it_was(self):
        """--recomecar rewrites answers that were paid for: an error halfway must
        not leave a truncated file behind."""
        good = [Answer("C-001", "m", "a", datetime(2026, 9, 14, 10, 0))]
        bad = good + [Answer("C-002", "m", object(), datetime(2026, 9, 14, 10, 1))]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            write_answers(good, path)
            before = path.read_bytes()
            with self.assertRaises(TypeError):
                write_answers(bad, path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["respostas.jsonl"])

    def test_one_answer_per_line(self):
        answers = [Answer("C-001", "m", "a\nb", datetime(2026, 9, 14, 10, 0))]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            write_answers(answers, path)
            lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1)

    def test_an_answer_written_with_sample_and_temperature_survives_a_round_trip(self):
        answers = [
            Answer("C-001", "modelo-x", "500 mg", datetime(2026, 9, 14, 10, 0), sample=3,
                   temperature=1.0),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            write_answers(answers, path)
            recovered = read_answers(path)
        self.assertEqual(recovered, answers)

    def test_an_old_file_without_sample_or_temperature_reads_as_sample_one_at_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            path.write_text(
                '{"caso": "C-001", "modelo": "m", "texto": "x", '
                '"perguntada_em": "2026-09-14T10:00:00"}\n',
                encoding="utf-8",
            )
            recovered = read_answers(path)
        self.assertEqual(recovered[0].sample, 1)
        self.assertEqual(recovered[0].temperature, 0.0)
        self.assertEqual(recovered[0].finish_reason, "stop")

    def test_a_finish_reason_survives_a_round_trip(self):
        answers = [
            Answer("C-001", "modelo-x", "a meio", datetime(2026, 9, 14, 10, 0),
                   finish_reason="length"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            write_answers(answers, path)
            recovered = read_answers(path)
        self.assertEqual(recovered, answers)


class TestAnswerConditions(unittest.TestCase):
    def test_the_conditions_survive_a_round_trip(self):
        answers = [
            Answer("C-001", "modelo-x", "500 mg", datetime(2026, 9, 14, 10, 0),
                   prompt_sha256="a" * 64, max_tokens=8192, build="0.1.0+abcdef012345"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            write_answers(answers, path)
            recovered = read_answers(path)
        self.assertEqual(recovered, answers)

    def test_an_answer_written_before_the_conditions_existed_reads_them_as_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "respostas.jsonl"
            path.write_text(
                '{"caso": "C-001", "modelo": "m", "texto": "x", '
                '"perguntada_em": "2026-09-14T10:00:00"}\n',
                encoding="utf-8",
            )
            recovered = read_answers(path)[0]
        self.assertEqual(recovered.prompt_sha256, "")
        self.assertIsNone(recovered.max_tokens)
        self.assertEqual(recovered.build, "")


class TestAlternativesOnDisk(unittest.TestCase):
    def test_a_case_with_alternatives_survives_a_write_and_a_read(self):

        case = a_two_regimen_case()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "casos.json"
            write_cases([case], path)
            [recovered] = read_cases(path)
        self.assertEqual(recovered, case)

    def test_the_verdict_on_disk_names_the_alternative(self):
        from aferidor.grading import grade
        from aferidor.storage import verdict_to_dict

        verdict = grade(
            a_two_regimen_case(),
            an_answer("Penicilina G benzatínica 1.200.000 U IM em dose única.", case_id="AMIG"),
        )
        self.assertEqual(verdict_to_dict(verdict)["alternativa"], "penicilina benzatínica em dose única")


class TestBankFormat(unittest.TestCase):
    def test_reads_the_annotated_bank_format(self):
        bank = {
            "versao": "teste",
            "casos": [{
                "id": "B-001", "area": "pediatria", "risco": "alto", "estado": "revisto_fonte",
                "pergunta": "Pode dar-se mel a um bebe de 7 meses?",
                "resposta_referencia": "Nao, risco de botulismo antes dos 12 meses.",
                "fonte": "Manual MSD", "fonte_versao": "2026", "fonte_seccao": "botulismo",
                "data_verificacao": "2026-09-26",
                "criterios": [{"tipo": "contem", "termos": ["botulismo"], "falha": "contraindicacao_omitida"}],
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "banco.json"
            path.write_text(json.dumps(bank), encoding="utf-8")
            [case] = read_cases(path)
        self.assertEqual(case.case_id, "B-001")
        self.assertEqual(case.category, "pediatria")
        self.assertEqual(case.source.reference, "2026 botulismo")
        self.assertEqual(case.source.consulted, date(2026, 9, 26))
        self.assertIn("Risco alto", case.notes)

    def bank_with(self, **changes) -> Path:
        case = {
            "id": "B-001", "area": "pediatria", "risco": "alto", "estado": "revisto_fonte",
            "pergunta": "p", "resposta_referencia": "Nao, risco de botulismo.",
            "fonte": "Manual MSD", "fonte_versao": "2026", "fonte_seccao": "botulismo",
            "criterios": [{"tipo": "contem", "termos": ["botulismo"], "falha": "contraindicacao_omitida"}],
        }
        case.update(changes)
        case = {k: v for k, v in case.items() if v is not None}
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "banco.json"
        path.write_text(json.dumps({"casos": [case]}), encoding="utf-8")
        return path

    def test_a_case_marked_por_verificar_is_refused_and_named(self):
        with self.assertRaises(ValueError) as raised:
            read_cases(self.bank_with(estado="por_verificar"))
        self.assertIn("B-001", str(raised.exception))
        self.assertIn("não pode pontuar", str(raised.exception))

    def test_an_unknown_review_state_is_refused(self):
        with self.assertRaises(ValueError) as raised:
            read_cases(self.bank_with(estado="revisto"))
        self.assertIn("'revisto'", str(raised.exception))

    def test_a_case_without_a_review_state_is_refused(self):
        with self.assertRaises(ValueError):
            read_cases(self.bank_with(estado=None))

    def test_a_case_without_version_or_section_says_so_instead_of_pointing_nowhere(self):
        [case] = read_cases(self.bank_with(fonte_versao=None, fonte_seccao=None))
        self.assertEqual(case.source.reference, "sem versão nem secção indicadas")

    def test_bank_case_without_criteria_is_refused(self):
        bank = {"casos": [{"id": "B-002", "area": "x", "pergunta": "p", "resposta_referencia": "r", "fonte": "f"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "banco.json"
            path.write_text(json.dumps(bank), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_cases(path)


if __name__ == "__main__":
    unittest.main()
