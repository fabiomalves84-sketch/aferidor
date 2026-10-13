"""Showing what the correction of the corrector did, without writing a number by hand.

Two things live here. `reclassify` regrades a registered trial with the current corrector, on the current case banks,
and gives the text of two new files to put beside the originals (the pattern of 27 September 2026: the originals are
never touched). The rest compares the published corrector, whose verdicts are kept in `docs/exemplo/antes-8edda161.json`,
with the current one, for the page: every figure is worked out from the stored answers and that file.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import dataclasses
import hashlib
import re
from dataclasses import dataclass

from . import build_id, grader_id, report
from .checks import _excluded_in_its_clause, _units, fold
from .grading import grade_all, match_answers, mcnemar_exact
from .risk import Risk
from .storage import read_answers, read_cases, verdict_to_dict

BANK_FILES = {"principal": "casos/casos.json", "consulta": "casos/consulta.json"}


def _bank_of(answers, banks) -> str:
    first = answers[0].case_id
    return "principal" if any(c.case_id == first for c in banks["principal"]) else "consulta"


def reclassify(folder: Path, root: Path, today: date) -> tuple[str, str, str]:
    """(file name suffix, verdicts as JSON text, report as Markdown) for one registered trial.

    The verdicts are the current corrector's, in the shape of `vereditos.json` plus, on each entry, what the saved
    verdicts of the trial said (`passou_antes`, `falhas_antes`) and the identifier of the corrector that gives the new
    ones; the report is the usual one, with a note at the top that says what it is and what it compares.
    """
    folder, root = Path(folder), Path(root)
    banks = {name: read_cases(root / path) for name, path in BANK_FILES.items()}
    answers = read_answers(folder / "respostas.jsonl")
    bank = _bank_of(answers, banks)
    cases = banks[bank]
    verdicts, missing = grade_all(cases, answers)
    saved = json.loads((folder / "vereditos.json").read_text(encoding="utf-8"))
    pairs = match_answers(cases, answers, verdicts)
    if len(saved) != len(pairs):
        raise ValueError(f"{folder.name}: {len(saved)} veredictos guardados e {len(pairs)} respostas")
    entries = []
    for old, (_answer, verdict) in zip(saved, pairs):
        entry = verdict_to_dict(verdict)
        entry["corretor_novo"] = grader_id()
        entry["passou_antes"] = bool(old["passou"])
        entry["falhas_antes"] = list(old["falhas"])
        entries.append(entry)
    changed = sum(1 for e in entries if e["passou"] != e["passou_antes"] or e["falhas"] != e["falhas_antes"])
    builds = sorted({a.build for a in answers if a.build})
    note = (
        f"> **Reclassificação de {today.isoformat()}.** As respostas deste ensaio são as de `respostas.jsonl`, que não se alterou. "
        f"Os veredictos que se seguem são os do corretor atual (`{grader_id()}`, código `{build_id()}`), sobre o banco de casos "
        f"atual (`{BANK_FILES[bank]}`); os do ensaio, em `vereditos.json`, foram dados pelo corretor da altura "
        f"({'código ' + ', '.join(builds) if builds else 'versão não registada nas respostas'}). "
        f"Comparação: {changed} de {len(entries)} veredictos mudam de resultado ou de falhas. Os bancos e os critérios são os atuais, "
        f"não os do dia do ensaio. É triagem automática, sem validação clínica.\n"
    )
    if "26b" in folder.name:
        note += (
            "\n> Este ensaio teve um protocolo com o corretor congelado. Isto é uma **reclassificação posterior, fora do protocolo**: "
            "não se aplica o limiar do protocolo à taxa corrigida, e o resultado publicado tal como saiu fica em `relatorio.md`.\n"
        )
    text = report.build(cases, answers, verdicts, missing=missing, today=today)
    body = text.split("\n", 1)
    markdown = body[0] + "\n\n" + note + "\n" + (body[1] if len(body) > 1 else "")
    return today.isoformat(), json.dumps(entries, ensure_ascii=False, indent=2) + "\n", markdown


# --- What the page shows: the published corrector against the current one --------------------------------------------

# The trials whose models the page puts side by side. A trial that is invalid, older or not a comparison of models the
# page talks about (the 14 and 16 September ones) still counts for how many criteria changed, but has no row in the table.
TABLE_TRIALS = (
    "2026-09-27-locais-12-14b", "2026-09-28-gemini-flash", "2026-09-29-gemma4-31b-casos",
    "2026-10-01-gemma4-26b-casos", "2026-09-29-gemini-consulta", "2026-09-29-gemma4-31b-consulta",
    "2026-10-01-gemma4-26b-consulta",
)
# The case about which the cited standard is silent on cephalexin, and the stem the page counts.
CEPHALEXIN_CASE = "ATB-FAR-014"
CEPHALEXIN = "cefalexin"


def is_after_the_protocol(trial: str) -> bool:
    """The 26B trials had a protocol with the corrector frozen; what the page shows for them is a later reclassification."""
    return "26b" in trial


@dataclass(frozen=True)
class Row:
    """One model of one bank: cases with a critical failure under the published corrector and under the current one."""

    bank: str
    trial: str
    model: str
    cases: int
    before: int
    after: int
    frozen: bool


@dataclass(frozen=True)
class BestPair:
    """The two models with the fewest critical cases, and the exact McNemar test between them."""

    first: str
    second: str
    first_critical: int
    cases: int
    only_first: int
    only_second: int
    p_value: float


@dataclass(frozen=True)
class Change:
    """A model and a case whose state of critical failure differs between the published corrector and the current one."""

    trial: str
    bank: str
    model: str
    case: str
    now_critical: bool
    samples: tuple[int, ...]  # the samples whose own state differs


@dataclass(frozen=True)
class Correction:
    """Everything the page says about the correction, worked out from the stored answers and `antes-8edda161.json`."""

    before_grader: str
    before_commit: str
    after_grader: str
    rows: tuple[Row, ...]
    best_before: BestPair | None
    best_after: BestPair | None
    cephalexin: tuple[tuple[str, int, int], ...]  # model, answers that name it without excluding it, answers
    equivalent_forms: tuple[int, int]  # criteria changed by U1 alone, cases touched
    all_corrections: tuple[int, int]  # criteria changed by every correction, cases touched
    trials_counted: int
    changes: tuple[Change, ...] = ()
    reading: tuple[int, int, int, int] | None = None  # changes read, then how many (a), (b), (c)

    @property
    def fell(self) -> tuple[Row, ...]:
        """The rows where the count of critical cases went down with the correction."""
        return tuple(row for row in self.rows if row.after < row.before)

    @property
    def rose(self) -> tuple[Row, ...]:
        return tuple(row for row in self.rows if row.after > row.before)


def names_without_excluding(text: str, stem: str = CEPHALEXIN) -> bool:
    """Whether an answer names a drug (by the stem of its name) somewhere the answer does not exclude it.

    A mention is excluded when an exclusion marker stands in the same clause (rule U5: a clause ends at a colon, a
    semicolon or the end of a line or list item). Naming it is not recommending it: this counts mentions, and says so.
    """
    for start, end, _fresh in _units(text):
        segment = fold(text[start:end])
        for match in re.finditer(r"(?<![a-z0-9])" + re.escape(stem), segment):
            if not _excluded_in_its_clause(segment, match.start(), match.end()):
                return True
    return False


def _critical_by_case(rows: list[tuple[str, str, bool]]) -> dict[str, dict[str, bool]]:
    """{model: {case: has a critical failure in some sample}} from (model, case, critical) triples."""
    out: dict[str, dict[str, bool]] = {}
    for model, case, critical in rows:
        out.setdefault(model, {})[case] = out.get(model, {}).get(case, False) or critical
    return out


def best_pair(by_model: dict[str, dict[str, bool]]) -> BestPair | None:
    """The two best models by critical cases (the lowest share first, the name to break a tie) and McNemar between them."""
    ranked = sorted(
        ((sum(cases.values()), len(cases), model) for model, cases in by_model.items() if cases),
        key=lambda r: (r[0] / r[1], r[2]),
    )
    if len(ranked) < 2:
        return None
    (first_n, total, first), (_second_n, _t, second) = ranked[0], ranked[1]
    both = set(by_model[first]) & set(by_model[second])
    only_first = sum(1 for c in both if by_model[first][c] and not by_model[second][c])
    only_second = sum(1 for c in both if by_model[second][c] and not by_model[first][c])
    return BestPair(first, second, first_n, total, only_first, only_second, mcnemar_exact(only_first, only_second))


def _strip_anchors(cases):
    def bare(criteria):
        return tuple(dataclasses.replace(c, ancora=(), em_ajuste=False) if c.ancora else c for c in criteria)

    return [
        dataclasses.replace(c, criteria=bare(c.criteria), alternatives=tuple(dataclasses.replace(a, criteria=bare(a.criteria)) for a in c.alternatives))
        for c in cases
    ]


def _changes(saved_rows, verdicts_and_answers) -> set[tuple[int, int | None, str]]:
    """The criteria whose result differs, as (answer position, criterion position, case); a change of alternative or of
    structure counts once, for the answer, when the verdict itself differs."""
    out = set()
    for position, (row, (answer, verdict)) in enumerate(zip(saved_rows, verdicts_and_answers)):
        flags = row[5]
        results = verdict.results
        if len(flags) != len(results) or row[6] != verdict.alternative:
            if bool(row[3]) != verdict.passed:
                out.add((position, None, answer.case_id))
            continue
        for index, (flag, result) in enumerate(zip(flags, results)):
            if (flag == "1") != result.passed:
                out.add((position, index, answer.case_id))
    return out


def load_before(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compute(before_path: Path, ensaios: Path, root: Path, reading_path: Path | None = None) -> Correction:
    """The correction as the page shows it. Refuses a file of the published corrector whose answers files have changed."""
    before = load_before(before_path)
    banks = {name: read_cases(Path(root) / path) for name, path in BANK_FILES.items()}
    rows: list[Row] = []
    before_cases: dict[str, list[tuple[str, str, bool]]] = {}
    after_cases: dict[str, list[tuple[str, str, bool]]] = {}
    cephalexin: dict[str, list[int]] = {}
    changes: list[Change] = []
    u1, everything = set(), set()
    for trial, entry in sorted(before["ensaios"].items()):
        path = Path(ensaios) / trial / "respostas.jsonl"
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["respostas_sha256"]:
            raise ValueError(f"{trial}: o ficheiro de respostas já não é o que o ficheiro do corretor publicado leu")
        answers = read_answers(path)
        cases = banks[entry["banco"]]
        verdicts, _missing = grade_all(cases, answers)
        paired = match_answers(cases, answers, verdicts)
        bare_verdicts, _ = grade_all(_strip_anchors(cases), answers)
        everything |= {(trial, *c) for c in _changes(entry["respostas"], paired)}
        u1 |= {(trial, *c) for c in _changes(entry["respostas"], match_answers(cases, answers, bare_verdicts))}
        if trial not in TABLE_TRIALS:
            continue
        triples_after = [(a.model, a.case_id, any(f.risk is Risk.CRITICO for f in v.failures)) for a, v in paired]
        triples_before = [(r[0], r[1], bool(r[4])) for r in entry["respostas"]]
        changed_samples: dict[tuple[str, str], list[int]] = {}
        for row, (answer, verdict) in zip(entry["respostas"], paired):
            if bool(row[4]) != any(f.risk is Risk.CRITICO for f in verdict.failures):
                changed_samples.setdefault((answer.model, answer.case_id), []).append(answer.sample)
        after_by, before_by = _critical_by_case(triples_after), _critical_by_case(triples_before)
        for model in sorted(after_by):
            rows.append(Row(entry["banco"], trial, model, len(after_by[model]), sum(before_by[model].values()),
                            sum(after_by[model].values()), is_after_the_protocol(trial)))
        for (model, case), samples in sorted(changed_samples.items()):
            state_before = any(row[4] for row in entry["respostas"] if row[0] == model and row[1] == case)
            state_after = any(c for m, k, c in triples_after if m == model and k == case)
            if state_before != state_after:
                changes.append(Change(trial, entry["banco"], model, case, state_after, tuple(sorted(samples))))
        if entry["banco"] == "principal" and not is_after_the_protocol(trial):
            before_cases.setdefault("all", []).extend(triples_before)
            after_cases.setdefault("all", []).extend(triples_after)
        if entry["banco"] == "principal":
            for answer in answers:
                if answer.case_id == CEPHALEXIN_CASE:
                    slot = cephalexin.setdefault(answer.model, [0, 0])
                    slot[1] += 1
                    slot[0] += int(names_without_excluding(answer.text))
    def counted(changes):
        return len(changes), len({change[3] for change in changes})

    return Correction(
        before_grader=before["grader_id"], before_commit=before["commit"], after_grader=grader_id(), rows=tuple(rows),
        best_before=best_pair(_critical_by_case(before_cases.get("all", []))),
        best_after=best_pair(_critical_by_case(after_cases.get("all", []))),
        cephalexin=tuple((m, v[0], v[1]) for m, v in sorted(cephalexin.items())),
        equivalent_forms=counted(u1), all_corrections=counted(everything), trials_counted=len(before["ensaios"]),
        changes=tuple(changes), reading=read_summary(reading_path, changes) if reading_path is not None else None,
    )


READING_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([A-Z0-9-]+)\s*\|[^|]*\|[^|]*\|[^|]*\|\s*([abc])\b[^|]*\|\s*$")


def read_rows(path: Path) -> list[tuple[str, str, str]]:
    """(model, case, class) of each line of the reading of the changes, as the Markdown file writes them."""
    return [m.groups() for line in Path(path).read_text(encoding="utf-8").splitlines() if (m := READING_ROW.match(line))]


def read_summary(path: Path, changes: list[Change]) -> tuple[int, int, int, int]:
    """How many changes of the state of critical failure were read and how many are (a), (b), (c). Refuses a reading that
    is not of exactly the changes the data give today: the file is only worth what it matches."""
    rows = read_rows(path)
    if sorted((m, k) for m, k, _c in rows) != sorted((c.model, c.case) for c in changes):
        raise ValueError(f"{path}: a leitura das mudanças não corresponde às mudanças que os dados dão hoje")
    classes = [c for _m, _k, c in rows]
    return len(rows), classes.count("a"), classes.count("b"), classes.count("c")
