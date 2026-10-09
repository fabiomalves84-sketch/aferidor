"""Whether an answer is written in European Portuguese, kept apart from the clinical grading.

The bench asks for answers in European Portuguese and, until this module,
never checked. It is measured here as an indicator, not as a failure type:
the headline count of critical failures only means something while it means
clinical risk, and a Brazilian spelling is not a wrong dose.

The check is a short, explicit list of forms that current European
Portuguese does not use, matched with accents kept (unlike the grader, which
strips them): here the difference often is the accent, "crônico" against
"crónico". Two groups are counted separately, because they say different
things:

* Brazilian forms, which European Portuguese never uses ("você" addressed to
  a doctor, "equipe", "estar fazendo", "crônico").
* Spellings from before the 1990 Spelling Agreement, which Brazil still uses
  and Portugal used until 2009 ("infecção", "contracepção"). An answer with
  these may be old European Portuguese rather than Brazilian; the DGS itself
  follows the Agreement.

Left out on purpose: words European Portuguese also uses, even if less
("paciente", "efeitos colaterais"), and "antibioticoterapia", which the DGS
writes (Norma 020/2012). A list like this under-counts; it is a floor, not a
measurement of how Portuguese an answer reads.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from .models import Answer
from .traducao import t

BRAZILIAN = "formas do Brasil"
PRE_AGREEMENT = "grafia anterior ao Acordo Ortográfico"

# (group, what it is and what European Portuguese says instead, pattern)
MARKERS: tuple[tuple[str, str, str], ...] = (
    (BRAZILIAN, "estar + gerúndio (PT: estar a + infinitivo)",
     r"\b(?:est[áa]|estão|estou|estamos|esteja|estejam|estar|estava|estavam)\s+\w+[aei]ndo\b"),
    (BRAZILIAN, "você", r"\bvocês?\b"),
    (BRAZILIAN, "contato (PT: contacto)", r"\bcontatos?\b"),
    (BRAZILIAN, "de fato (PT: de facto)", r"\bde fato\b"),
    (BRAZILIAN, "equipe (PT: equipa)", r"\bequipes?\b"),
    (BRAZILIAN, "registrar, registro (PT: registar, registo)",
     r"\bregistr(?:ar|o|os|e|ado|ada|ados|adas)\b"),
    (BRAZILIAN, "ô antes de m ou n (PT: ó, como em crónico)",
     r"\b(?!estômago|cônjuge)\w*ô[mn]\w*"),
    (BRAZILIAN, "câncer (PT: cancro)", r"\bcâncer\b"),
    (BRAZILIAN, "usuário (PT: utilizador, utente)", r"\busuári[oa]s?\b"),
    (BRAZILIAN, "-éia (PT: -eia, como em diarreia)", r"\w+éias?\b"),
    (PRE_AGREEMENT, "infecção (PT: infeção)", r"\binfecç\w*"),
    (PRE_AGREEMENT, "contracepção (PT: contraceção)", r"\bcontracep\w*"),
    (PRE_AGREEMENT, "detecção (PT: deteção)", r"\bdetecç\w*"),
    (PRE_AGREEMENT, "aspecto (PT: aspeto)", r"\baspectos?\b"),
)
_COMPILED = tuple((group, label, re.compile(pattern)) for group, label, pattern in MARKERS)


def markers_in(text: str) -> list[tuple[str, str]]:
    """Every (group, marker) found in the text, each marker once."""
    lowered = unicodedata.normalize("NFC", text).lower()
    return [(group, label) for group, label, rx in _COMPILED if rx.search(lowered)]


@dataclass(frozen=True)
class LanguageSummary:
    """How one model's answers fare against the list."""

    model: str
    answers: int
    brazilian: int
    pre_agreement: int
    by_marker: tuple[tuple[str, int], ...]


def language_by_model(answers: list[Answer]) -> dict[str, LanguageSummary]:
    """One summary per model, sorted by name; markers most frequent first."""
    grouped: dict[str, list[Answer]] = {}
    for answer in answers:
        grouped.setdefault(answer.model, []).append(answer)
    result: dict[str, LanguageSummary] = {}
    for model, group in sorted(grouped.items()):
        counts: Counter = Counter()
        brazilian = pre_agreement = 0
        for answer in group:
            found = markers_in(answer.text)
            brazilian += any(g == BRAZILIAN for g, _ in found)
            pre_agreement += any(g == PRE_AGREEMENT for g, _ in found)
            counts.update(label for _, label in found)
        result[model] = LanguageSummary(
            model=model,
            answers=len(group),
            brazilian=brazilian,
            pre_agreement=pre_agreement,
            by_marker=tuple(counts.most_common()),
        )
    return result


def language_line(summary: LanguageSummary, lang: str = "pt") -> str:
    """The indicator in one sentence, for either report.

    The marker labels stay in Portuguese in every language: they name
    Portuguese spellings.
    """
    line = t(
        "{a} de {n} respostas com formas do português do Brasil, e {b} com grafia anterior "
        "ao Acordo Ortográfico.",
        lang, a=summary.brazilian, n=summary.answers, b=summary.pre_agreement,
    )
    if summary.by_marker:
        top = "; ".join(f"{label}: {count}" for label, count in summary.by_marker[:5])
        line += " " + t("Mais frequentes: {lista}.", lang, lista=top)
    return line


__all__ = [
    "MARKERS",
    "BRAZILIAN",
    "PRE_AGREEMENT",
    "markers_in",
    "LanguageSummary",
    "language_by_model",
    "language_line",
]
