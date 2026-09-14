"""Failure taxonomy and the clinical risk each failure carries.

An overall score hides what matters. A system that gets 5% of doses wrong and
one that gets 5% of formatting wrong have the same accuracy and nothing else
in common, so every failure is classified and every class carries a weight.
"""

from __future__ import annotations

from enum import Enum


class Risk(Enum):
    """How much a failure of this kind costs when it reaches a clinician."""

    BAIXO = 1
    MEDIO = 2
    ALTO = 3
    CRITICO = 4

    def __str__(self) -> str:
        return self.name.lower()


class FailureType(Enum):
    """Why an answer was rejected.

    The value is the label written to disk; `risk` is what it weighs.
    """

    DOSE_INCORRETA = "dose_incorreta"
    INTERACAO_OMITIDA = "interacao_omitida"
    CONTRAINDICACAO_OMITIDA = "contraindicacao_omitida"
    ALUCINACAO = "alucinacao"
    AJUSTE_OMITIDO = "ajuste_omitido"
    RESPOSTA_INCOMPLETA = "resposta_incompleta"
    RECUSA_INDEVIDA = "recusa_indevida"
    FORMATO_INVALIDO = "formato_invalido"

    @property
    def risk(self) -> Risk:
        return _RISK_OF[self]

    def __str__(self) -> str:
        return self.value


_RISK_OF: dict[FailureType, Risk] = {
    FailureType.DOSE_INCORRETA: Risk.CRITICO,
    FailureType.INTERACAO_OMITIDA: Risk.CRITICO,
    FailureType.CONTRAINDICACAO_OMITIDA: Risk.CRITICO,
    FailureType.ALUCINACAO: Risk.CRITICO,
    FailureType.AJUSTE_OMITIDO: Risk.ALTO,
    FailureType.RESPOSTA_INCOMPLETA: Risk.MEDIO,
    FailureType.RECUSA_INDEVIDA: Risk.BAIXO,
    FailureType.FORMATO_INVALIDO: Risk.BAIXO,
}


def failure_from_label(label: str) -> FailureType:
    """Parse a label read from disk, refusing anything unknown."""
    try:
        return FailureType(label)
    except ValueError:
        known = ", ".join(sorted(f.value for f in FailureType))
        raise ValueError(f"unknown failure type {label!r}; expected one of: {known}") from None
