"""Deciding whether one answer meets one criterion.

Every check here is textual and deterministic. That is a deliberate limit: a
bench whose grader is itself a language model has two systems under test and no
way to tell which one was wrong. The price is that a criterion has to be
written carefully, and that price is paid once, when the case is written.

Two matching rules earn their complexity:

* Accents and spacing are normalised, so `tres vezes` matches `três vezes` and
  `1000mg` matches `1000 mg`. A model is not wrong for typing a space.
* A term that is only digits matches on word boundaries. Without that, the term
  `5` is found inside `500 mg` and a wrong dose passes as a right duration.
"""

from __future__ import annotations

import re
import unicodedata

from .models import Criterion, CriterionResult

UNITS = (
    "mg/kg", "mcg/kg", "g/kg", "mg", "mcg", "ug", "g", "kg",
    "ml", "l", "ui", "mmol", "mmhg", "dias", "dia", "horas", "hora", "h", "semanas",
)

_SPACING = re.compile(r"(\d)\s*(" + "|".join(UNITS) + r")\b")
_WHITESPACE = re.compile(r"\s+")
_BARE_NUMBER = re.compile(r"^\d+([.,]\d+)?$")


def normalize(text: str) -> str:
    """Lowercase, strip accents, tidy spacing, and separate numbers from units."""
    without_accents = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )
    lowered = without_accents.lower().replace("–", "-").replace("—", "-")
    collapsed = _WHITESPACE.sub(" ", lowered).strip()
    return _SPACING.sub(r"\1 \2", collapsed)


def find_term(haystack: str, term: str) -> int:
    """Position of `term` in already normalised text, or -1.

    Bare numbers match only as whole words, so `5` is not found inside `500`.
    """
    needle = normalize(term)
    if not needle:
        return -1
    if _BARE_NUMBER.match(needle):
        match = re.search(rf"(?<!\d){re.escape(needle)}(?!\d)", haystack)
        return match.start() if match else -1
    return haystack.find(needle)


def snippet(haystack: str, position: int, width: int = 60) -> str:
    """A short window of text around a match, for the report to quote."""
    if position < 0:
        return ""
    start = max(0, position - width // 2)
    end = min(len(haystack), position + width)
    return ("..." if start > 0 else "") + haystack[start:end].strip() + (
        "..." if end < len(haystack) else ""
    )


def _numbers_before(haystack: str, unit: str) -> list[float]:
    """Every number that is written immediately before `unit`."""
    pattern = re.compile(rf"(\d+(?:[.,]\d+)?)\s*{re.escape(normalize(unit))}\b")
    return [float(m.group(1).replace(",", ".")) for m in pattern.finditer(haystack)]


def check(criterion: Criterion, text: str) -> CriterionResult:
    """Run one criterion against one answer."""
    haystack = normalize(text)

    if criterion.kind == "contem":
        for term in criterion.terms:
            at = find_term(haystack, term)
            if at >= 0:
                return CriterionResult(criterion, True, f"{term!r} em: {snippet(haystack, at)}")
        wanted = ", ".join(repr(t) for t in criterion.terms)
        return CriterionResult(criterion, False, f"nenhum de: {wanted}")

    if criterion.kind == "nao_contem":
        for term in criterion.terms:
            at = find_term(haystack, term)
            if at >= 0:
                return CriterionResult(
                    criterion, False, f"encontrou {term!r} em: {snippet(haystack, at)}"
                )
        return CriterionResult(criterion, True, "nenhum termo proibido")

    if criterion.kind == "contem_todos":
        missing = [t for t in criterion.terms if find_term(haystack, t) < 0]
        if missing:
            return CriterionResult(
                criterion, False, "faltou: " + ", ".join(repr(t) for t in missing)
            )
        return CriterionResult(criterion, True, "todos presentes")

    if criterion.kind == "valor_numerico":
        return _check_number(criterion, haystack)

    raise ValueError(f"criterio de tipo desconhecido {criterion.kind!r}")


def _check_number(criterion: Criterion, haystack: str) -> CriterionResult:
    """`termos` is (valor, unidade) and optionally (valor, unidade, tolerancia)."""
    if len(criterion.terms) < 2:
        raise ValueError("valor_numerico precisa de valor e unidade em 'termos'")
    expected = float(criterion.terms[0].replace(",", "."))
    unit = criterion.terms[1]
    tolerance = float(criterion.terms[2].replace(",", ".")) if len(criterion.terms) > 2 else 0.0

    seen = _numbers_before(haystack, unit)
    if not seen:
        return CriterionResult(criterion, False, f"nenhum valor em {unit}")
    for value in seen:
        if abs(value - expected) <= tolerance:
            return CriterionResult(criterion, True, f"{value:g} {unit}")
    written = ", ".join(f"{v:g}" for v in seen)
    return CriterionResult(
        criterion, False, f"esperava {expected:g} {unit}, encontrou {written} {unit}"
    )


__all__ = ["check", "normalize", "find_term", "snippet"]
