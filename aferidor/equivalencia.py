"""When two written doses, or two written intervals, are the same one (rule U1 of `docs/METODO.md`).

A dose is a quantity with a unit, a mass always in mg; an interval is the hours between two doses. Two forms are
equivalent when those canonical values are equal: "de 8 em 8 horas", "8-8h", "a cada 8 horas", "3x/dia" and "tid"
are all 8 hours, "0,5 g" is "500 mg", and "1 g" is not. The functions are pure and know nothing of criteria, cases
or answers, so one table decides in both directions: what a criterion accepts and what it must reject.

Two limits are deliberate. "N times a day" is read as 24 / N hours, which is arithmetic and not a clinical claim:
the case bank already accepts "três vezes por dia" for 8/8. And only a form that says "every": a bare "8 horas"
is a duration and is not an interval, nor is a range such as "8-12h".

`checks` uses it to read a `contem` criterion that asks for a dose or an interval, and to find the doses and
intervals an answer writes, with the places where they sit.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_TOLERANCE = 1e-9

# A number as written in Portuguese: 500, 2,5, 1.000, 1 000, 1 200 000.
_NUMBER = r"(?:[1-9]\d{0,2}(?:[.\ ]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"

_MASS = {"mg": 1.0, "g": 1000.0, "mcg": 0.001, "ug": 0.001, "µg": 0.001}
_UNIT = r"(?:miligramas?|microgramas?|gramas?|mg|mcg|ug|µg|g|ui|u)"
_SPELLED_UNIT = {"miligrama": "mg", "miligramas": "mg", "micrograma": "mcg", "microgramas": "mcg", "grama": "g", "gramas": "g"}
# What may follow the unit: per kilo, per kilo per day, per day, or a concentration (per ml), which is none of them.
_PER = r"(?:\s*/\s*kg(?:\s*/\s*(?:dia|d))?|\s*/\s*dia|\s*/\s*(?:\d+(?:[.,]\d+)?\s*)?ml)?"
_DOSE = re.compile(rf"(?<![\d.,/])(?P<number>{_NUMBER})\s*(?P<unit>{_UNIT})(?P<per>{_PER})(?![a-z0-9])")

_RANGE_END = re.compile(r"\d\s*(?:a|ate|ou|-)\s*$")
_WORD_NUMBERS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6}
_SPELLED_HOURS = {
    "seis": 6, "oito": 8, "doze": 12, "vinte e quatro": 24, "quarenta e oito": 48, "setenta e duas": 72,
}
_ACRONYMS = {"qd": 24, "od": 24, "bid": 12, "tid": 8, "qid": 6}

_EVERY = r"(?<![a-z0-9])(?:a\s+)?cada\s+(?P<every>\d+(?:[.,]\d+)?)\s*(?:horas?|hs?)(?![a-z])"
_SLASH = r"(?<![\d.,/-])(?P<n1>\d+)\s*(?:/|-|\\)\s*(?P<n2>\d+)\s*(?:horas?|hs?)?(?![\d/])"
_IN = r"(?<![a-z0-9])(?:de\s+)?(?P<m1>\d+)\s+em\s+(?P<m2>\d+)(?:\s*(?:horas?|hs?))?(?![\d])"
_SPELLED = (
    r"(?<![a-z])(?:de\s+)?(?P<s1>seis|oito|doze|vinte e quatro|quarenta e oito|setenta e duas)\s+em\s+"
    r"(?P<s2>seis|oito|doze|vinte e quatro|quarenta e oito|setenta e duas)(?:\s+horas?)?(?![a-z])"
)
_Q = r"(?<![a-z0-9])q\s*(?P<q>\d+)\s*h(?![a-z0-9])"
_TIMES = (
    r"(?<![a-z0-9])(?P<times>\d+|um|uma|dois|duas|tres|quatro|cinco|seis)\s*"
    r"(?:x\s*(?:/\s*|por\s+|ao\s+)?(?:dia|d)|(?:vez(?:es)?|tomas?)\s*(?:/\s*dia|por\s+dia|ao\s+dia|diari[ao]s?|/\s*d))"
    r"(?![a-z0-9])"
)
_ACRO = r"(?<![a-z0-9])(?P<acro>qd|od|bid|tid|qid)(?![a-z0-9])"
_WEEKLY = r"(?<![a-z0-9])(?:(?:uma\s+vez|1\s*x|1\s+vez)\s+(?:por|a|na)\s+semana|semanal(?:mente)?)(?![a-z0-9])"

_INTERVAL_FORMS = (_EVERY, _SLASH, _IN, _SPELLED, _Q, _TIMES, _ACRO, _WEEKLY)
_INTERVAL = re.compile("|".join(f"(?:{form})" for form in _INTERVAL_FORMS))


@dataclass(frozen=True)
class Dose:
    """A quantity in canonical form: mass in mg, with what it is per, if anything ("", "kg", "kg/dia", "dia", "ml")."""

    amount: float
    unit: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("uma dose não pode ser negativa")


@dataclass(frozen=True)
class DoseFound:
    dose: Dose
    start: int
    end: int
    written: str


@dataclass(frozen=True)
class IntervalFound:
    hours: float
    start: int
    end: int
    written: str


def fold(text: str) -> str:
    """Lowercase and without accents, character for character, so positions in it are positions in the text."""
    stripped = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return stripped.lower().replace("–", "-").replace("—", "-")


def _number(raw: str) -> float:
    """500, 2,5, 1.000, 1 000 and 1 200 000 as numbers. A dot or a space followed by three digits groups thousands."""
    grouped = re.fullmatch(r"([1-9]\d{0,2})((?:[.\ ]\d{3})+)(?:,(\d+))?", raw)
    if grouped:
        whole = grouped.group(1) + re.sub(r"[.\ ]", "", grouped.group(2))
        return float(f"{whole}.{grouped.group(3)}" if grouped.group(3) else whole)
    return float(raw.replace(",", "."))


def _dose_of(match: re.Match[str]) -> Dose | None:
    amount = _number(match.group("number"))
    unit = _SPELLED_UNIT.get(match.group("unit"), match.group("unit"))
    per = re.sub(r"\s+", "", match.group("per") or "")
    if unit in _MASS:
        amount, base = amount * _MASS[unit], "mg"
    else:
        base = "u" if unit in ("u", "ui") else unit
    if per:
        suffix = per.lstrip("/")
        base = f"{base}/{'kg/dia' if suffix == 'kg/d' else 'dia' if suffix == 'd' else suffix}"
    return Dose(round(amount, 9), base)


def find_doses(text: str) -> list[DoseFound]:
    """Every dose written in `text`, in order. A dose per kilo, per day or per ml is its own unit, never plain mg."""
    folded = fold(text)
    found = []
    for match in _DOSE.finditer(folded):
        if _RANGE_END.search(folded[:match.start()]):
            continue  # "5 a 10 mg/kg": a range is two doses, and neither is the one dose
        dose = _dose_of(match)
        if dose is not None:
            found.append(DoseFound(dose, match.start(), match.end(), text[match.start():match.end()]))
    return found


def parse_dose(text: str) -> Dose | None:
    """The dose that `text` is, when `text` is nothing but one dose ("500 mg", "0,5 g", "50 mg/kg/dia")."""
    folded = fold(text).strip()
    match = _DOSE.fullmatch(folded)
    return _dose_of(match) if match else None


def same_dose(a: str, b: str) -> bool:
    """Whether two written doses are the same quantity of the same thing. Unparseable text is never the same."""
    first, second = parse_dose(a), parse_dose(b)
    return first is not None and second is not None and same_quantity(first, second)


def same_quantity(a: Dose, b: Dose) -> bool:
    """Whether two parsed doses are the same amount of the same unit."""
    return a.unit == b.unit and abs(a.amount - b.amount) <= _TOLERANCE * max(1.0, abs(a.amount))


def _hours_of(match: re.Match[str]) -> float | None:
    groups = match.groupdict()
    if groups["every"]:
        return float(groups["every"].replace(",", "."))
    if groups["n1"]:
        return float(groups["n1"]) if groups["n1"] == groups["n2"] and float(groups["n1"]) > 0 else None
    if groups["m1"]:
        return float(groups["m1"]) if groups["m1"] == groups["m2"] and float(groups["m1"]) > 0 else None
    if groups["s1"]:
        return float(_SPELLED_HOURS[groups["s1"]]) if groups["s1"] == groups["s2"] else None
    if groups["q"]:
        return float(groups["q"]) if float(groups["q"]) > 0 else None
    if groups["times"]:
        raw = groups["times"]
        times = _WORD_NUMBERS[raw] if raw in _WORD_NUMBERS else int(raw)
        return 24.0 / times if times > 0 else None
    if groups["acro"]:
        return float(_ACRONYMS[groups["acro"]])
    return 168.0  # weekly


def find_intervals(text: str) -> list[IntervalFound]:
    """Every interval between doses written in `text`, in order, as the hours between two doses."""
    folded = fold(text)
    found = []
    for match in _INTERVAL.finditer(folded):
        hours = _hours_of(match)
        if hours is not None:
            found.append(IntervalFound(hours, match.start(), match.end(), text[match.start():match.end()]))
    return found


def parse_interval(text: str) -> float | None:
    """The hours between doses that `text` says, when `text` is nothing but one interval ("8/8h", "3x/dia")."""
    folded = fold(text).strip()
    found = find_intervals(folded)
    if len(found) == 1 and found[0].start == 0 and found[0].end == len(folded):
        return found[0].hours
    return None


def same_interval(a: str, b: str) -> bool:
    """Whether two written intervals are the same hours between doses. Unparseable text is never the same."""
    first, second = parse_interval(a), parse_interval(b)
    return first is not None and second is not None and abs(first - second) <= _TOLERANCE * max(1.0, first)


__all__ = [
    "Dose", "DoseFound", "IntervalFound", "fold", "find_doses", "parse_dose", "same_dose", "same_quantity",
    "find_intervals", "parse_interval", "same_interval",
]
