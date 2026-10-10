"""Builders shared by the test modules."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from aferidor.models import Answer, Case
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
