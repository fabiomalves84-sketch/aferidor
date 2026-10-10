"""Where the cases come from, and how far their sources have been confirmed by a person.

The state of confirmation is read from `casos/VERIFICACAO.md`, case by case, by id. This module only
reads that file: it never writes to it, and it never marks a box. Nobody but the person who confirms
a source marks one, and the report must not look as if it had.

Two things are counted from the table, which has one row per case and a last column with `[x]` or
`[ ]`: how many boxes are marked and how many are not. A third thing is not in the table: of the
marked ones, which were confirmed one by one, in the document, with the person looking at the
value, and which were declared confirmed together, without a page for each. That distinction exists
only in prose, in the paragraph of 27/09/2026 of the same file, so the ten cases confirmed one by
one are listed here (`ONE_BY_ONE`) and a test holds the list against both the table and the
paragraph. The list counts; it does not guard.

A confirmation made one by one in the future will not enter the list by itself: until someone adds
it, it counts as declared together. That is a limit of the file and not something a test can see.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .models import Case

# The cases whose sources were confirmed one by one in the documents, on 27/09/2026 (see the paragraph
# "Confirmações registadas" of casos/VERIFICACAO.md). It is a record, not a rule: if it and the file
# disagree, the person who confirms them has to look at it, and nothing here corrects it.
ONE_BY_ONE = (
    "ATB-PAC-001", "ATB-PAC-011", "ATB-CIST-003", "FMT-CIST-017", "GRA-CIST-022",
    "PED-OMA-019", "PED-OMA-020", "PED-OMA-021", "ATB-FAR-013", "PED-08",
)

# The sources the glossary explains. A case is said to cite one when its source names it as a word.
BODIES = ("DGS", "Infarmed", "EMA", "ESC", "ADA", "NICE", "APMGF", "SNS", "FDA", "RCM", "PNV")

# How many sources the first line of the page names before it says "and others". The rest is listed in the
# Method page, closed.
SHOWN = 5

VERIFICATION_FILE = "VERIFICACAO.md"
_ROW = re.compile(r"\| ([A-Z]+-[A-Z0-9-]+) \|")
_BOX = re.compile(r"\|\s*\[( |x)\]\s*\|\s*$")
_PARAGRAPH = re.compile(r"\*\*27/09/2026\.\*\* Marcadas as linhas de (.*?)\. Fontes:", re.S)
_ID = re.compile(r"[A-Z]+-[A-Z0-9-]+")


@dataclass(frozen=True)
class Counts:
    """How the sources of a set of cases stand."""

    total: int
    one_by_one: int
    in_group: int
    pending: int
    without_row: tuple[str, ...] = ()


@dataclass(frozen=True)
class Confirmation:
    """The state of confirmation of the report's cases, and of every case the file knows."""

    bank: Counts
    project: Counts


def read_table(path: Path) -> dict[str, bool]:
    """`{case id: box marked}` for every row of the state tables of the file. Read only."""
    rows: dict[str, bool] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        row, box = _ROW.match(line), _BOX.search(line)
        if row and box:
            rows[row.group(1)] = box.group(1) == "x"
    return rows


def one_by_one_in_paragraph(path: Path) -> list[str]:
    """The ids the file itself names as confirmed one by one, in the paragraph of 27/09/2026."""
    found = _PARAGRAPH.search(Path(path).read_text(encoding="utf-8"))
    return _ID.findall(found.group(1)) if found else []


def count(case_ids: list[str], table: dict[str, bool]) -> Counts:
    """Count these cases against the table, by id. A case with no row is named, never guessed."""
    present = [i for i in case_ids if i in table]
    marked = [i for i in present if table[i]]
    one = [i for i in marked if i in ONE_BY_ONE]
    return Counts(
        total=len(case_ids),
        one_by_one=len(one),
        in_group=len(marked) - len(one),
        pending=len(present) - len(marked),
        without_row=tuple(i for i in case_ids if i not in table),
    )


def confirmation(case_ids: list[str], table: dict[str, bool]) -> Confirmation:
    return Confirmation(bank=count(case_ids, table), project=count(list(table), table))


def read_confirmation(cases_path: Path, case_ids: list[str]) -> Confirmation | None:
    """The state of confirmation, from the verification file that sits next to the case file.

    None when there is none (the cases of a registered trial are a copy, alone in their folder): the
    report then says what it always said, and shows no number it did not read.
    """
    path = Path(cases_path).parent / VERIFICATION_FILE
    if not path.is_file():
        return None
    return confirmation(case_ids, read_table(path))


def divergences(path: Path) -> list[str]:
    """What is wrong with the list of ten, against the table and against the paragraph; empty if nothing.

    Nothing is corrected here or anywhere: the list is looked at by whoever confirms the sources.
    """
    table = read_table(path)
    problems = [f"{i} não tem linha na tabela" for i in ONE_BY_ONE if i not in table]
    problems += [f"{i} está na lista mas a caixa não está marcada" for i in ONE_BY_ONE if i in table and not table[i]]
    named = set(one_by_one_in_paragraph(path))
    problems += [f"{i} está na lista mas não no parágrafo de 27/09" for i in ONE_BY_ONE if i not in named]
    problems += [f"{i} está no parágrafo de 27/09 mas não na lista" for i in sorted(named - set(ONE_BY_ONE))]
    return problems


def cited_by(cases: list[Case], body: str) -> set[str]:
    return {c.case_id for c in cases if re.search(rf"(?<![A-Za-z]){body}(?![A-Za-z])", c.source.name)}


def by_source(cases: list[Case]) -> list[tuple[str, int]]:
    """How many cases cite each source, most cited first. A case that cites two counts in both."""
    counted = [(body, len(cited_by(cases, body))) for body in BODIES]
    return sorted((item for item in counted if item[1]), key=lambda item: (-item[1], item[0]))


def left_out(cases: list[Case], shown: list[str]) -> int:
    """How many cases cite none of the sources shown."""
    cited = set().union(*(cited_by(cases, body) for body in shown)) if shown else set()
    return len(cases) - len(cited)


__all__ = [
    "ONE_BY_ONE", "BODIES", "SHOWN", "Counts", "Confirmation", "read_table", "one_by_one_in_paragraph",
    "count", "confirmation", "read_confirmation", "divergences", "by_source", "left_out",
]
