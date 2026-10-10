"""Builders shared by the test modules."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from aferidor.models import Alternative, Answer, Case, Criterion, Source
from aferidor.risk import FailureType
from aferidor.storage import case_to_dict


def an_answer(text: str, case_id: str = "C1", model: str = "falso", sample: int = 1) -> Answer:
    return Answer(
        case_id=case_id, model=model, text=text, asked_at=datetime(2026, 9, 14), sample=sample
    )


def write_cases(cases: list[Case], path: Path) -> int:
    """A case file for a test to read. The program itself only reads the bank."""
    payload = [case_to_dict(c) for c in cases]
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(payload)


def a_case(case_id: str = "C1", category: str = "dose") -> Case:
    return Case(
        case_id=case_id,
        category=category,
        question="Que dose de amoxicilina?",
        reference="Amoxicilina 1000 mg de 8/8h",
        source=Source(name="Guia ATB", reference="p. 17"),
        criteria=(
            Criterion(kind="contem", terms=("1000 mg", "1 g"), failure=FailureType.DOSE_INCORRETA),
        ),
    )


def a_two_regimen_case() -> Case:
    """Like ATB-FAR-013: ten days of amoxicillin, or one dose of benzathine penicillin."""
    return Case(
        case_id="AMIG",
        category="pediatria",
        question="Amigdalite estreptocócica numa criança de 30 kg. Primeira linha?",
        reference="Amoxicilina 50 mg/kg/dia 12/12h durante 10 dias, ou penicilina G benzatínica 1.200.000 U IM em dose única.",
        source=Source(name="DGS", reference="Norma 020/2012, ponto 10"),
        criteria=(
            Criterion(
                kind="nao_prescreve", terms=("azitromicina",),
                failure=FailureType.RESPOSTA_INCOMPLETA,
            ),
        ),
        alternatives=(
            Alternative(
                description="amoxicilina 10 dias",
                reference="Amoxicilina 50 mg/kg/dia de 12/12h durante 10 dias.",
                criteria=(
                    Criterion(kind="contem", terms=("amoxicilina",), failure=FailureType.RESPOSTA_INCOMPLETA),
                    Criterion(kind="valor_numerico", terms=("50", "mg/kg/dia"), failure=FailureType.DOSE_INCORRETA),
                    Criterion(kind="contem", terms=("10 dias",), failure=FailureType.RESPOSTA_INCOMPLETA),
                ),
            ),
            Alternative(
                description="penicilina benzatínica em dose única",
                reference="Penicilina G benzatínica 1.200.000 U IM em dose única.",
                criteria=(
                    Criterion(kind="contem", terms=("benzatinica",), failure=FailureType.RESPOSTA_INCOMPLETA),
                    Criterion(kind="contem", terms=("1.200.000", "1 200 000"), failure=FailureType.DOSE_INCORRETA),
                    Criterion(kind="contem", terms=("dose unica", "toma unica"), failure=FailureType.DOSE_INCORRETA),
                ),
            ),
        ),
    )
