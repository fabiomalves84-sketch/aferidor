"""Checking the grader against a person.

The grader is a measuring instrument, and an instrument nobody has compared
with a reference measures nothing anyone can state. `verificar` shows each
criterion passes the right answer and fails a constructed wrong one; it says
nothing about how often the grader agrees with a clinician on real answers.
This module exports a sample of real answers for a clinician to judge, and
measures the agreement once the judgements come back.

Two rules shape it:

* The sheet is blind. It shows the question, the reference answer and the
  model's answer, and never the grader's verdict or the model's name. A
  reviewer who can see the verdict measures the grader's influence on the
  reviewer, not the grader.
* The number that matters most is the false pass: an answer the clinician
  judged wrong that the grader let through. That is the failure nobody
  investigates, and it is reported first, with its interval.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .grading import match_answers, wilson_interval
from .models import Answer, Case, Verdict
from .runner import build_prompt, prompt_digest

SHEET_COLUMNS = (
    "revisao", "caso", "pergunta", "resposta_de_referencia", "resposta_do_modelo",
    "juizo", "notas",
)
# What a reviewer may write in the `juizo` column, and what each one means.
JUDGEMENTS = {
    "certa": True, "correta": True, "certo": True, "correto": True,
    "errada": False, "incorreta": False, "errado": False, "incorreto": False,
}


@dataclass(frozen=True)
class ReviewItem:
    """One real answer picked for a person to judge."""

    review_id: str
    case: Case
    answer: Answer
    grader_passed: bool


def sample_for_review(
    cases: list[Case], answers: list[Answer], verdicts: list[Verdict], n: int, seed: int
) -> list[ReviewItem]:
    """A reproducible sample, half passed and half failed by the grader when possible.

    Half and half on purpose: a sample drawn at random from a run where the
    grader failed nine answers in ten would hold almost no passed answers,
    and the false-pass rate, the number that matters most, would rest on a
    handful of them. When one side has fewer than half, the other fills the
    rest. The same seed on the same file gives the same sample.

    An answer given to a different wording of the question than the case
    has now is left out: the sheet shows the current question, and a
    reviewer judging an answer against a question the model never read is
    judging something else. See `asked_the_same_question`.
    """
    if n < 1:
        raise ValueError("a amostra precisa de pelo menos uma resposta")
    by_id = {c.case_id: c for c in cases}
    pairs = [
        (a, v) for a, v in match_answers(cases, answers, verdicts)
        if asked_the_same_question(by_id[a.case_id], a) is not False
    ]
    rng = random.Random(seed)
    passed = [p for p in pairs if p[1].passed]
    failed = [p for p in pairs if not p[1].passed]
    rng.shuffle(passed)
    rng.shuffle(failed)
    take_passed = min(len(passed), n // 2)
    take_failed = min(len(failed), n - take_passed)
    take_passed = min(len(passed), n - take_failed)
    chosen = passed[:take_passed] + failed[:take_failed]
    rng.shuffle(chosen)
    return [
        ReviewItem(f"R{i:03d}", by_id[a.case_id], a, v.passed)
        for i, (a, v) in enumerate(chosen, start=1)
    ]


def asked_the_same_question(case: Case, answer: Answer) -> bool | None:
    """Whether the answer was given to the question the case asks today.

    True or False when the answer recorded the hash of the text it was sent;
    None for an answer from before that was recorded, where nobody can tell.
    """
    if not answer.prompt_sha256:
        return None
    return answer.prompt_sha256 == prompt_digest(build_prompt(case))


# A cell that starts with one of these is read as a formula by Excel and
# LibreOffice. Model answers often start with "- " or "=" (lists, equations),
# and one could start with "=HYPERLINK(...)"; the reviewer must see text.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _as_text(value: str) -> str:
    """A cell value a spreadsheet will show as text, never evaluate."""
    return "'" + value if value.startswith(_FORMULA_START) else value


def write_review(items: list[ReviewItem], sheet: Path, key: Path, source: Path) -> None:
    """Write the blind sheet for the reviewer and, separately, the key.

    The sheet uses a semicolon and a byte-order mark so that a spreadsheet
    set up for Portuguese opens it in columns at the first try. The key
    records which file, which answers and which grader verdict each row was,
    and the SHA-256 of the answers file, so the agreement is always tied to
    the exact answers that were judged.
    """
    with Path(sheet).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(SHEET_COLUMNS)
        for item in items:
            writer.writerow([
                item.review_id, item.case.case_id, _as_text(item.case.question),
                _as_text(item.case.reference), _as_text(item.answer.text), "", "",
            ])
    payload = {
        "respostas": str(source),
        "respostas_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "criada_em": date.today().isoformat(),
        "itens": {
            item.review_id: {
                "caso": item.case.case_id,
                "modelo": item.answer.model,
                "amostra": item.answer.sample,
                "corretor": "certa" if item.grader_passed else "errada",
            }
            for item in items
        },
    }
    Path(key).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def key_path_for(sheet: Path) -> Path:
    """Where the key of a review sheet lives: next to it, with `-chave.json`."""
    sheet = Path(sheet)
    return sheet.with_name(sheet.stem + "-chave.json")


@dataclass(frozen=True)
class Agreement:
    """How the grader compares with a person on the same answers.

    `false_pass` is an answer the person judged wrong and the grader passed;
    `false_fail` is one the person judged right and the grader failed.
    """

    both_right: int
    both_wrong: int
    false_pass: int
    false_fail: int
    unjudged: tuple[str, ...]

    @property
    def judged(self) -> int:
        return self.both_right + self.both_wrong + self.false_pass + self.false_fail

    @property
    def agreement(self) -> float:
        return (self.both_right + self.both_wrong) / self.judged if self.judged else 0.0

    @property
    def human_wrong(self) -> int:
        return self.both_wrong + self.false_pass

    @property
    def human_right(self) -> int:
        return self.both_right + self.false_fail

    @property
    def false_pass_rate(self) -> float:
        """Of the answers the person judged wrong, the share the grader let through."""
        return self.false_pass / self.human_wrong if self.human_wrong else 0.0

    @property
    def false_fail_rate(self) -> float:
        """Of the answers the person judged right, the share the grader marked wrong."""
        return self.false_fail / self.human_right if self.human_right else 0.0

    @property
    def kappa(self) -> float | None:
        """Cohen's kappa: agreement beyond what chance alone would give.

        None when chance agreement is total (both raters said the same thing
        about every answer), where kappa is undefined.
        """
        n = self.judged
        if not n:
            return None
        grader_right = self.both_right + self.false_pass
        chance = (
            grader_right * self.human_right + (n - grader_right) * self.human_wrong
        ) / (n * n)
        if chance >= 1:
            return None
        return (self.agreement - chance) / (1 - chance)


def read_review(sheet: Path, key: Path) -> Agreement:
    """Compare the person's judgements in `sheet` with the grader's in `key`.

    A row left blank is not an error: it is counted as not yet judged and
    named, so a half-finished review can be read without pretending to be a
    finished one. A judgement that is not one of `JUDGEMENTS` is refused with
    the row it is in; guessing what the reviewer meant would be putting
    words in a clinician's mouth.
    """
    grader = json.loads(Path(key).read_text(encoding="utf-8"))["itens"]
    counts = {"both_right": 0, "both_wrong": 0, "false_pass": 0, "false_fail": 0}
    unjudged: list[str] = []
    with Path(sheet).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            review_id = (row.get("revisao") or "").strip()
            if review_id not in grader:
                raise ValueError(f"{sheet}: a linha {review_id!r} não existe na chave {key}")
            raw = (row.get("juizo") or "").strip().lower()
            if not raw:
                unjudged.append(review_id)
                continue
            if raw not in JUDGEMENTS:
                allowed = ", ".join(sorted(set(JUDGEMENTS)))
                raise ValueError(
                    f"{sheet}, {review_id}: juízo {raw!r} desconhecido; usar um de: {allowed}"
                )
            human = JUDGEMENTS[raw]
            machine = grader[review_id]["corretor"] == "certa"
            if human and machine:
                counts["both_right"] += 1
            elif not human and not machine:
                counts["both_wrong"] += 1
            elif machine:
                counts["false_pass"] += 1
            else:
                counts["false_fail"] += 1
    return Agreement(unjudged=tuple(unjudged), **counts)


def format_agreement(result: Agreement) -> str:
    """The agreement written for a person, the false pass first."""
    if not result.judged:
        return (
            f"Nenhuma resposta julgada ainda ({len(result.unjudged)} por julgar). "
            "Escrever 'certa' ou 'errada' na coluna 'juizo' e voltar a correr."
        )
    lines: list[str] = []
    if result.human_wrong:
        low, high = wilson_interval(result.false_pass, result.human_wrong)
        lines.append(
            f"Passagens falsas: {result.false_pass} de {result.human_wrong} respostas que a "
            f"revisão deu como erradas ({result.false_pass_rate:.0%}, IC 95% {low:.0%} a {high:.0%})."
        )
    else:
        lines.append("Passagens falsas: sem respostas dadas como erradas pela revisão.")
    if result.human_right:
        low, high = wilson_interval(result.false_fail, result.human_right)
        lines.append(
            f"Falhas falsas: {result.false_fail} de {result.human_right} respostas que a "
            f"revisão deu como certas ({result.false_fail_rate:.0%}, IC 95% {low:.0%} a {high:.0%})."
        )
    low, high = wilson_interval(round(result.agreement * result.judged), result.judged)
    lines.append(
        f"Concordância: {result.agreement:.0%} em {result.judged} respostas julgadas "
        f"(IC 95% {low:.0%} a {high:.0%})."
    )
    kappa = result.kappa
    lines.append(
        f"Kappa de Cohen: {kappa:.2f}." if kappa is not None
        else "Kappa de Cohen: indefinido (os dois disseram o mesmo de todas)."
    )
    lines.append(
        "A amostra é estratificada (metade aprovada e metade reprovada pelo corretor): "
        "a concordância e o kappa descrevem esta amostra, não a execução completa; as "
        "taxas de passagens e falhas falsas, por serem condicionais ao juízo da revisão, "
        "são as que se podem levar para a execução."
    )
    if result.unjudged:
        lines.append(
            f"Por julgar: {len(result.unjudged)} ({', '.join(result.unjudged)}). "
            "Não entram em nenhum número acima."
        )
    return "\n".join(lines)


__all__ = [
    "ReviewItem",
    "sample_for_review",
    "write_review",
    "key_path_for",
    "asked_the_same_question",
    "Agreement",
    "read_review",
    "format_agreement",
    "JUDGEMENTS",
]
