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

The `nao_prescreve` check is the one place where plain text matching was not
enough, and where the replacement is openly a heuristic. Its limits are stated
at the check itself rather than left for the reader to discover.
"""

from __future__ import annotations

import re
import unicodedata

from .models import Criterion, CriterionResult
from .risk import FailureType

UNITS = (
    "mg/kg", "mcg/kg", "g/kg", "mg", "mcg", "ug", "g", "kg",
    "ml", "l", "ui", "mmol", "mmhg", "dias", "dia", "horas", "hora", "h", "semanas",
)

# Phrases that, next to a drug name, mean the text is excluding it rather than
# prescribing it. The list is deliberately short and explicit: a loose marker
# such as "alergia" or "hipersensibilidade" appears in the question itself and
# would excuse a genuinely wrong prescription.
EXCLUSION_MARKERS = (
    "contraindicad", "contra-indicad", "contraindicac",
    "nao usar", "nao administrar", "nao prescrever", "nao dar", "nao utilizar",
    "nao deve", "nao pode ser usad", "nao e opcao", "nao esta indicad",
    "nao recomendad", "esta excluid", "deve ser evitad", "evitar",
)
EXCLUSION_WINDOW = 70

# Phrases that mean the model declined to answer a legitimate clinical
# question, gathered in one place instead of copied into every case that
# might see one. A model that refuses ATB-DPOC-002, which has no refusal
# criterion of its own, must not be graded against that case's dose criteria:
# a refusal obviously does not mention a dose, and grading it as one turns an
# honest low-risk failure into a false critical one.
REFUSAL_MARKERS = (
    "nao posso dar aconselhamento",
    "nao me e possivel",
    "nao posso responder",
    "nao sou um profissional de saude",
    "consulte um medico antes",
    "lamento, mas nao posso",
    "nao posso fornecer",
    "nao posso ajudar",
)

# A synthetic criterion, not tied to any one case, so `grade` can check for a
# refusal with the same `nao_contem` logic every other criterion uses instead
# of a second matching path.
REFUSAL_CRITERION = Criterion(
    kind="nao_contem",
    terms=REFUSAL_MARKERS,
    failure=FailureType.RECUSA_INDEVIDA,
    description="deteccao central de recusa, antes dos criterios do caso",
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
    A term that starts with a digit needs the same guard even when it is not
    a bare number: `5 mg` must not match inside `2,5 mg` or `25 mg`, only a
    digit or a digit followed by a decimal separator right before it rules
    that out.
    """
    needle = normalize(term)
    if not needle:
        return -1
    if _BARE_NUMBER.match(needle):
        match = re.search(rf"(?<!\d){re.escape(needle)}(?!\d)", haystack)
        return match.start() if match else -1
    if needle[0].isdigit():
        match = re.search(rf"(?<![\d])(?<![\d][.,]){re.escape(needle)}", haystack)
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

    if criterion.kind == "nao_prescreve":
        return _check_not_prescribed(criterion, haystack)

    if criterion.kind == "valor_numerico":
        return _check_number(criterion, haystack)

    raise ValueError(f"criterio de tipo desconhecido {criterion.kind!r}")


def _is_excluded_at(haystack: str, position: int, length: int) -> bool:
    """Whether the text around this mention reads as excluding the drug.

    A window either side is searched for an explicit exclusion phrase. Text
    before the name catches "nao usar amoxicilina", text after catches
    "amoxicilina esta contraindicada".

    This is a heuristic and it is wrong in both directions. It will call a
    mention excluded when an exclusion phrase nearby belongs to a different
    drug, and it will call a mention a prescription when the exclusion is
    phrased in a way this list does not contain. It is still strictly better
    than treating every mention as a prescription, which is what a plain
    `nao_contem` does, and which marks a correct answer wrong for adding a
    warning.
    """
    start = max(0, position - EXCLUSION_WINDOW)
    end = min(len(haystack), position + length + EXCLUSION_WINDOW)
    around = haystack[start:end]
    return any(marker in around for marker in EXCLUSION_MARKERS)


def _check_not_prescribed(criterion: Criterion, haystack: str) -> CriterionResult:
    """Pass unless a term is named as something to give.

    Unlike `nao_contem`, a term named in order to rule it out does not fail.
    """
    for term in criterion.terms:
        needle = normalize(term)
        at = find_term(haystack, term)
        while at >= 0:
            if not _is_excluded_at(haystack, at, len(needle)):
                return CriterionResult(
                    criterion, False, f"prescreve {term!r} em: {snippet(haystack, at)}"
                )
            following = find_term(haystack[at + len(needle):], term)
            at = at + len(needle) + following if following >= 0 else -1
    return CriterionResult(criterion, True, "nenhum farmaco excluido foi prescrito")


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


__all__ = [
    "check",
    "normalize",
    "find_term",
    "snippet",
    "EXCLUSION_MARKERS",
    "REFUSAL_MARKERS",
    "REFUSAL_CRITERION",
]
