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
    write_cases,
)


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
        self.assertIn("duplicate", str(caught.exception))

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


if __name__ == "__main__":
    unittest.main()
