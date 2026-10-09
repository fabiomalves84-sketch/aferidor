"""Turning answers into verdicts, and verdicts into counts that mean something.

The count that matters is never the total. Ten failures of `formato_invalido`
and one of `dose_incorreta` are not eleven failures of the same thing, so every
tally here is kept split by failure type and by the risk that type carries.
"""

from __future__ import annotations

import math

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .checks import (
    REFUSAL_CRITERION,
    check,
    find_term,
    is_refusal,
    normalize,
    remove_term,
    replace_values,
)
from .models import Answer, Case, Criterion, CriterionResult, Verdict
from .risk import FailureType, Risk


def grade(case: Case, answer: Answer) -> Verdict:
    """Judge one answer against the case it was given.

    A refusal is checked first, against every case, whether or not that case
    declares its own refusal criterion. Grading a refusal against dose or
    interaction criteria too finds it guilty of not mentioning a dose, which
    turns one honest low-risk failure into a false critical one and inflates
    exactly the number this project promises means something. A refusal
    leads to `recusa_indevida` alone.

    But a refusal marker next to an actual dose is a courtesy warning, not a
    refusal (`checks.is_refusal`): "Amoxicilina 500 mg 8/8h. Não posso
    fornecer uma avaliação individual..." answered the question, and hiding
    that dose behind `recusa_indevida` is worse than the false critical this
    check exists to prevent, because nobody investigates a failure that
    never shows up.

    Nor is a marker a refusal when the reply says everything the case asks
    for. Many correct answers carry no dose at all ("Não me é possível
    recomendar aspirina: está contraindicada... síndrome de Reye"), and
    calling them refusals marks a model wrong for being right. So a reply
    with a marker and no dose is still graded by the case's own criteria,
    negative ones included, when it passes every positive criterion of the
    case (`_answered`). Only a reply that fails to say what the case needs is
    a refusal.

    A case with alternatives is judged against its own criteria plus each
    alternative in turn (`_judge`), and the verdict names the alternative it
    was judged against.
    """
    if answer.case_id != case.case_id:
        raise ValueError(
            f"resposta do caso {answer.case_id} avaliada contra o caso {case.case_id}"
        )
    results, alternative = _judge(case, answer.text)
    if is_refusal(answer.text) and not _answered(results):
        refusal = check(REFUSAL_CRITERION, answer.text)
        # A refusal marker must not hide what the reply goes on to say:
        # "Não posso fornecer aconselhamento individual. Em geral, pode dar
        # aspirina" is a forbidden prescription, not only a refusal.
        # Words the question itself uses, or a drug named beside the
        # patient's history, are the question repeated back, not advice.
        question = normalize(case.question)
        broken = tuple(
            r
            for r in (
                check(c, answer.text, restating=True)
                for c in _all_criteria(case)
                if c.kind == "nao_prescreve"
                or (c.kind == "nao_contem" and not any(find_term(question, t) >= 0 for t in c.terms))
            )
            if not r.passed
        )
        return Verdict(case_id=case.case_id, model=answer.model, results=(refusal,) + broken)
    return Verdict(
        case_id=case.case_id, model=answer.model, results=results, alternative=alternative
    )


def _judge(case: Case, text: str) -> tuple[tuple[CriterionResult, ...], str]:
    """The criterion results that decide an answer, and which alternative they came from.

    Without alternatives, the case's own criteria. With them, the case's own
    criteria plus the first alternative the answer meets in full; when it
    meets none, the one it came closest to, by fewest failed criteria. Closest,
    not worst: an answer that attempted the benzathine regimen and got its dose
    wrong should read as a wrong benzathine dose, not as a missing amoxicillin
    course it never meant to give.

    Between alternatives equally close, the one whose failures carry the
    highest risk wins. The opposite rule hid a wrong dose: "amoxicilina 1 g e
    doxiciclina 100 mg de 12/12h" misses one criterion of the doxycycline
    regimen (the 200 mg loading dose, critical) and one of the
    clarithromycin regimen (the drug's name, medium), because the "12/12"
    satisfies the latter's interval. Picking the lower risk reported an
    incomplete answer and no dose failure at all. A tie must never be the
    reason a critical failure disappears. Remaining ties go to the
    alternative written first.
    """
    common = tuple(check(criterion, text) for criterion in case.criteria)
    if not case.alternatives:
        return common, ""
    closest: tuple[tuple[int, int], tuple[CriterionResult, ...], str] | None = None
    for alternative in case.alternatives:
        results = common + tuple(check(c, text) for c in alternative.criteria)
        failed = [r for r in results if not r.passed]
        if not failed:
            return results, alternative.description
        distance = (len(failed), -max(r.criterion.failure.risk.value for r in failed))
        if closest is None or distance < closest[0]:
            closest = (distance, results, alternative.description)
    assert closest is not None
    return closest[1], closest[2]


_POSITIVE_KINDS = ("contem", "contem_todos", "valor_numerico")


def _all_criteria(case: Case) -> tuple:
    """The case's own criteria and those of every alternative, without repeats."""
    seen: list = []
    for criterion in case.criteria + tuple(c for a in case.alternatives for c in a.criteria):
        if criterion not in seen:
            seen.append(criterion)
    return tuple(seen)


def _answered(results: tuple[CriterionResult, ...]) -> bool:
    """Whether a reply said everything the case asks it to say.

    Only the positive criteria count: a pure refusal trivially passes every
    `nao_contem` and `nao_prescreve`, because it says nothing. A case with no
    positive criterion at all can never be shown to have been answered this
    way, so a marker there stays a refusal.
    """
    positive = [r for r in results if r.criterion.kind in _POSITIVE_KINDS]
    return bool(positive) and all(r.passed for r in positive)


def grade_all(cases: list[Case], answers: list[Answer]) -> tuple[list[Verdict], list[str]]:
    """Judge every answer, and report which cases were never answered.

    The unanswered list is returned rather than ignored: a score computed over
    the cases that happened to come back is a score for a set nobody chose.

    The same (case, model, sample) twice in the file is refused outright. Two
    processes writing to the same file, or one file appended onto another,
    would otherwise count one answer twice and every rate after it would be
    computed over answers nobody asked for.
    """
    duplicates = duplicate_samples(answers)
    if duplicates:
        named = ", ".join(f"{c} ({m}, amostra {s})" for c, m, s in duplicates)
        raise ValueError(f"amostras repetidas no ficheiro de respostas: {named}")
    by_id = {c.case_id: c for c in cases}
    verdicts: list[Verdict] = []
    unknown: list[str] = []

    for answer in answers:
        case = by_id.get(answer.case_id)
        if case is None:
            unknown.append(answer.case_id)
            continue
        verdicts.append(grade(case, answer))

    answered = {a.case_id for a in answers}
    missing = [c.case_id for c in cases if c.case_id not in answered]
    return verdicts, missing + unknown


def duplicate_samples(answers: list[Answer]) -> list[tuple[str, str, int]]:
    """Every (case, model, sample) that appears more than once, in file order."""
    seen: set[tuple[str, str, int]] = set()
    repeated: list[tuple[str, str, int]] = []
    for answer in answers:
        key = (answer.case_id, answer.model, answer.sample)
        if key in seen and key not in repeated:
            repeated.append(key)
        seen.add(key)
    return repeated


@dataclass
class Tally:
    """What one model scored, split the only way that is useful."""

    model: str
    total: int = 0
    passed: int = 0
    by_failure: Counter = field(default_factory=Counter)
    by_risk: Counter = field(default_factory=Counter)
    failed_cases: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def critical(self) -> int:
        """Answers carrying at least one critical failure. The number to read first."""
        return self.by_risk[Risk.CRITICO]

    def worst_first(self) -> list[tuple[FailureType, int]]:
        return sorted(self.by_failure.items(), key=lambda kv: (-kv[0].risk.value, -kv[1]))


def tally(verdicts: list[Verdict]) -> Tally:
    """Count one model's verdicts. Mixing models in one tally is refused."""
    if not verdicts:
        return Tally(model="")
    models = {v.model for v in verdicts}
    if len(models) > 1:
        raise ValueError(
            "veredictos de modelos diferentes na mesma contagem: " + ", ".join(sorted(models))
        )

    counts = Tally(model=verdicts[0].model, total=len(verdicts))
    for verdict in verdicts:
        if verdict.passed:
            counts.passed += 1
            continue
        failures = verdict.failures
        seen = counts.failed_cases.get(verdict.case_id, ())
        counts.failed_cases[verdict.case_id] = seen + tuple(
            f.value for f in failures if f.value not in seen
        )
        for failure in failures:
            counts.by_failure[failure] += 1
        if verdict.worst_risk:
            counts.by_risk[verdict.worst_risk] += 1
    return counts


def tally_by_model(verdicts: list[Verdict]) -> dict[str, Tally]:
    """One tally per model, for comparing two models over the same cases."""
    grouped: dict[str, list[Verdict]] = {}
    for verdict in verdicts:
        grouped.setdefault(verdict.model, []).append(verdict)
    return {model: tally(group) for model, group in sorted(grouped.items())}


class ConsistencyState(Enum):
    """How stable a model's answers were across repeated samples of one case.

    A model right in one sample out of five is, for a clinician who only ever
    sees one answer, a model that gets that case wrong. Instability is a
    finding on its own, separate from whether any given sample passed.
    """

    ESTAVEL_CERTO = "estavel_certo"
    ESTAVEL_ERRADO = "estavel_errado"
    INSTAVEL = "instavel"

    @property
    def label(self) -> str:
        return _CONSISTENCY_LABELS[self]

    def __str__(self) -> str:
        return self.value


_CONSISTENCY_LABELS: dict[ConsistencyState, str] = {
    ConsistencyState.ESTAVEL_CERTO: "sempre correto",
    ConsistencyState.ESTAVEL_ERRADO: "nunca correto",
    ConsistencyState.INSTAVEL: "parcialmente correto",
}


@dataclass
class Consistency:
    """How one model answered one case across every sample it was asked."""

    case_id: str
    model: str
    samples: int
    passed: int
    worst_failure: FailureType | None
    state: ConsistencyState


def match_answers(
    cases: list[Case], answers: list[Answer], verdicts: list[Verdict]
) -> list[tuple[Answer, Verdict]]:
    """Pair every answer with its verdict, in the order `grade_all` produced them.

    `verdicts` must be exactly what `grade_all(cases, answers)` returned for
    this same `answers` list: its order lines up with the answers whose case
    is known, which is the same filter applied here.
    """
    known_ids = {c.case_id for c in cases}
    matched = [a for a in answers if a.case_id in known_ids]
    if len(matched) != len(verdicts):
        raise ValueError(
            "answers e verdicts fora de sincronia; correr de novo grade_all(cases, answers)"
        )
    return list(zip(matched, verdicts))


def pairs_by_case(
    cases: list[Case], answers: list[Answer], verdicts: list[Verdict]
) -> dict[tuple[str, str], list[tuple[Answer, Verdict]]]:
    """Every (answer, verdict) asked of one case by one model, sample order kept."""
    grouped: dict[tuple[str, str], list[tuple[Answer, Verdict]]] = {}
    for answer, verdict in match_answers(cases, answers, verdicts):
        grouped.setdefault((answer.case_id, answer.model), []).append((answer, verdict))
    return grouped


def consistency_by_case(
    cases: list[Case], answers: list[Answer], verdicts: list[Verdict]
) -> dict[tuple[str, str], Consistency]:
    """Group verdicts by (case, model), reading sample numbers off `answers`."""
    result: dict[tuple[str, str], Consistency] = {}
    for (case_id, model), pairs in pairs_by_case(cases, answers, verdicts).items():
        samples = len(pairs)
        passed = sum(1 for _, v in pairs if v.passed)
        failures = [f for _, v in pairs for f in v.failures]
        worst = max(failures, key=lambda f: f.risk.value) if failures else None
        if passed == samples:
            state = ConsistencyState.ESTAVEL_CERTO
        elif passed == 0:
            state = ConsistencyState.ESTAVEL_ERRADO
        else:
            state = ConsistencyState.INSTAVEL
        result[(case_id, model)] = Consistency(
            case_id=case_id,
            model=model,
            samples=samples,
            passed=passed,
            worst_failure=worst,
            state=state,
        )
    return result


@dataclass
class ConsistencySummary:
    """One model's consistency, counted by case rather than by sample.

    Counting by sample hides exactly what this is for: a model that is wrong
    in one sample out of five still gets a case wrong for the one clinician
    who saw that sample.
    """

    model: str
    cases: int
    critical_cases: int
    unstable_cases: int
    sample_accuracy: float


def consistency_by_model(
    consistency: dict[tuple[str, str], Consistency]
) -> dict[str, ConsistencySummary]:
    """One summary per model, sorted by name. Mixing models here is as wrong as in `tally`."""
    grouped: dict[str, list[Consistency]] = {}
    for (_, model), entry in consistency.items():
        grouped.setdefault(model, []).append(entry)

    result: dict[str, ConsistencySummary] = {}
    for model, entries in sorted(grouped.items()):
        total_samples = sum(e.samples for e in entries)
        total_passed = sum(e.passed for e in entries)
        result[model] = ConsistencySummary(
            model=model,
            cases=len(entries),
            critical_cases=sum(
                1 for e in entries if e.worst_failure and e.worst_failure.risk == Risk.CRITICO
            ),
            unstable_cases=sum(1 for e in entries if e.state is ConsistencyState.INSTAVEL),
            sample_accuracy=(total_passed / total_samples) if total_samples else 0.0,
        )
    return result


# The boolean rule that turns a case's samples into one verdict: right or
# wrong. Declared in the protocol, before the run; without a protocol the
# strictest applies, because a clinician sees one answer and does not choose
# which sample it is.
CASE_RULES: dict[str, str] = {
    "todas": "todas as amostras são corretas",
    "maioria_sem_critica": "a maioria das amostras é correta e nenhuma tem falha crítica",
    "nenhuma_critica": "nenhuma amostra tem falha crítica",
}
DEFAULT_CASE_RULE = "todas"


def case_is_right(entry: "Consistency", rule: str = DEFAULT_CASE_RULE) -> bool:
    """One case, one model, one yes or no, by the named rule."""
    critical = entry.worst_failure is not None and entry.worst_failure.risk == Risk.CRITICO
    if rule == "todas":
        return entry.passed == entry.samples
    if rule == "maioria_sem_critica":
        return entry.passed * 2 > entry.samples and not critical
    if rule == "nenhuma_critica":
        return not critical
    raise ValueError(f"regra do caso desconhecida {rule!r}; esperava uma de {', '.join(CASE_RULES)}")


def right_cases_by_model(
    consistency: dict[tuple[str, str], "Consistency"], rule: str = DEFAULT_CASE_RULE
) -> dict[str, tuple[int, int]]:
    """(cases right, cases answered) per model, by the named rule."""
    result: dict[str, tuple[int, int]] = {}
    for (_, model), entry in consistency.items():
        right, total = result.get(model, (0, 0))
        result[model] = (right + int(case_is_right(entry, rule)), total + 1)
    return dict(sorted(result.items()))


def states_by_model(
    consistency: dict[tuple[str, str], Consistency]
) -> dict[str, dict[ConsistencyState, int]]:
    """How many cases each model left in each consistency state, every state present."""
    result: dict[str, dict[ConsistencyState, int]] = {}
    for (_, model), entry in consistency.items():
        counts = result.setdefault(model, {state: 0 for state in ConsistencyState})
        counts[entry.state] += 1
    return dict(sorted(result.items()))


def critical_by_category(
    cases: list[Case], consistency: dict[tuple[str, str], Consistency]
) -> tuple[list[str], dict[str, dict[str, tuple[int, int]]]]:
    """Cases with a critical failure in some sample, per clinical area and per model.

    Returns the categories in the order the cases first show them, and for
    each model a (critical, answered) pair per category. The whole point of
    the bench is that a model can look good on average and be dangerous in
    one area; this is where that shows.
    """
    categories: list[str] = []
    for case in cases:
        if case.category not in categories:
            categories.append(case.category)
    by_id = {c.case_id: c for c in cases}
    table: dict[str, dict[str, tuple[int, int]]] = {}
    for (case_id, model), entry in consistency.items():
        category = by_id[case_id].category
        row = table.setdefault(model, {c: (0, 0) for c in categories})
        critical, answered = row[category]
        is_critical = entry.worst_failure is not None and entry.worst_failure.risk == Risk.CRITICO
        row[category] = (critical + int(is_critical), answered + 1)
    return categories, dict(sorted(table.items()))


@dataclass(frozen=True)
class CriticalComparison:
    """Models ordered from fewest to most cases with a critical failure.

    `rows` holds (model, critical, cases, low, high) with the 95% Wilson
    interval. `overlap` says whether the first two intervals overlap: when
    they do, the difference between the two best models can be chance.
    """

    rows: tuple[tuple[str, int, int, float, float], ...]
    overlap: bool
    # The paired comparison of the first two models, when their cases are known:
    # cases where only the first failed critically, only the second, and the
    # exact McNemar p-value on those discordant cases.
    only_first: int | None = None
    only_second: int | None = None
    p_value: float | None = None


def mcnemar_exact(only_first: int, only_second: int) -> float:
    """Two-sided exact McNemar test: a binomial test on the discordant pairs.

    Two models answered the same cases, so their results are paired; the
    overlap of two separate intervals ignores that and is too cautious. Only
    the cases where exactly one of them failed carry information about which
    is better; under no difference, each is equally likely to be either one.
    """
    n = only_first + only_second
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(only_first, only_second) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _critical(entry: "Consistency") -> bool:
    return entry.worst_failure is not None and entry.worst_failure.risk == Risk.CRITICO


def compare_critical(
    summaries: dict[str, "ConsistencySummary"],
    consistency: dict[tuple[str, str], "Consistency"] | None = None,
) -> CriticalComparison:
    rows = []
    for model, summary in summaries.items():
        if not summary.cases:
            continue
        low, high = wilson_interval(summary.critical_cases, summary.cases)
        rows.append((model, summary.critical_cases, summary.cases, low, high))
    rows.sort(key=lambda r: (r[1] / r[2], r[0]))
    overlap = len(rows) > 1 and rows[0][4] >= rows[1][3]
    if consistency is None or len(rows) < 2:
        return CriticalComparison(rows=tuple(rows), overlap=overlap)
    first, second = rows[0][0], rows[1][0]
    both = {
        case_id for (case_id, model) in consistency
        if model == first and (case_id, second) in consistency
    }
    only_first = sum(
        1 for c in both
        if _critical(consistency[(c, first)]) and not _critical(consistency[(c, second)])
    )
    only_second = sum(
        1 for c in both
        if _critical(consistency[(c, second)]) and not _critical(consistency[(c, first)])
    )
    return CriticalComparison(
        rows=tuple(rows), overlap=overlap, only_first=only_first, only_second=only_second,
        p_value=mcnemar_exact(only_first, only_second),
    )


def worst_examples(
    cases: list[Case],
    consistency: dict[tuple[str, str], Consistency],
    pairs: dict[tuple[str, str], list[tuple[Answer, Verdict]]],
    limit: int = 4,
) -> list[tuple[Case, Answer, Verdict]]:
    """A few of the gravest mistakes, picked by a fixed rule, not by a person.

    A case qualifies for a model when the model got it wrong in every sample
    and its worst failure is critical. From each such case the first sample
    with a critical failure is shown, not merely the first that failed: that
    one can be a refusal, which is not what this list is for. Models take turns, in name order, so one model's
    mistakes do not fill the list; within a model, cases keep their order.
    """
    queues: dict[str, list[tuple[Case, Answer, Verdict]]] = {}
    for case in cases:
        for (case_id, model), entry in sorted(consistency.items()):
            if case_id != case.case_id:
                continue
            if entry.state is not ConsistencyState.ESTAVEL_ERRADO:
                continue
            if entry.worst_failure is None or entry.worst_failure.risk != Risk.CRITICO:
                continue
            for answer, verdict in pairs.get((case_id, model), []):
                if verdict.worst_risk == Risk.CRITICO:
                    queues.setdefault(model, []).append((case, answer, verdict))
                    break
    chosen: list[tuple[Case, Answer, Verdict]] = []
    while len(chosen) < limit and any(queues.values()):
        for model in sorted(queues):
            if queues[model] and len(chosen) < limit:
                chosen.append(queues[model].pop(0))
    return chosen


def expected_samples(answers: list[Answer]) -> dict[str, int]:
    """How many samples each model was actually asked for.

    Read off the data itself, as the highest sample number that model has
    anywhere in the file, rather than configured separately: it can never
    drift from what the run really did.
    """
    expected: dict[str, int] = {}
    for answer in answers:
        expected[answer.model] = max(expected.get(answer.model, 0), answer.sample)
    return expected


def missing_samples(
    cases: list[Case], answers: list[Answer]
) -> dict[tuple[str, str], tuple[int, ...]]:
    """Which sample numbers are missing, for every (case, model) pair.

    A case answered 3 times out of 5 by one model, or answered in full by
    `llama` and not at all by `qwen`, is invisible to `grade_all`'s plain
    list of unanswered cases: that list only names a case when every model
    missed it completely, and both of these have at least one answer from
    someone. This checks every case against every model that answered
    anything at all, including a model that has nothing whatsoever for that
    case, and names exactly which sample numbers never came back.
    """
    expected = expected_samples(answers)
    have: dict[tuple[str, str], set[int]] = {}
    for answer in answers:
        have.setdefault((answer.case_id, answer.model), set()).add(answer.sample)

    result: dict[tuple[str, str], tuple[int, ...]] = {}
    for case in cases:
        for model, wanted in expected.items():
            got = have.get((case.case_id, model), set())
            gaps = tuple(n for n in range(1, wanted + 1) if n not in got)
            if gaps:
                result[(case.case_id, model)] = gaps
    return result


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval for a proportion, 95% by default.

    Wilson and not the textbook normal approximation: with the small counts
    this bench works with (27 cases, a few dozen reviewed answers) and rates
    near 0 or 1, the normal approximation gives intervals that run below 0
    or above 1, and collapses to a width of zero when nothing was observed,
    claiming certainty exactly where there is least of it.
    """
    if total <= 0:
        raise ValueError("um intervalo precisa de pelo menos uma observação")
    if not 0 <= successes <= total:
        raise ValueError(f"{successes} sucessos em {total} observações não é uma proporção")
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    low = 0.0 if successes == 0 else max(0.0, centre - half)
    high = 1.0 if successes == total else min(1.0, centre + half)
    return low, high


@dataclass(frozen=True)
class RunConditions:
    """Under what conditions one model's answers in a file were obtained.

    Every field is a sorted tuple of the distinct values seen, not a single
    value: a file that mixes two temperatures shows both, which is the point.
    `None` in `max_tokens` and "" in `builds` mean some answers predate those
    fields being recorded.
    """

    model: str
    answers: int
    first_asked: datetime
    last_asked: datetime
    temperatures: tuple[float, ...]
    max_tokens: tuple[int | None, ...]
    builds: tuple[str, ...]


def run_conditions(answers: list[Answer]) -> dict[str, RunConditions]:
    """One `RunConditions` per model, sorted by model name."""
    grouped: dict[str, list[Answer]] = {}
    for answer in answers:
        grouped.setdefault(answer.model, []).append(answer)
    result: dict[str, RunConditions] = {}
    for model, group in sorted(grouped.items()):
        tokens = {a.max_tokens for a in group}
        result[model] = RunConditions(
            model=model,
            answers=len(group),
            first_asked=min(a.asked_at for a in group),
            last_asked=max(a.asked_at for a in group),
            temperatures=tuple(sorted({a.temperature for a in group})),
            max_tokens=tuple(sorted(tokens - {None})) + ((None,) if None in tokens else ()),
            builds=tuple(sorted({a.build for a in group})),
        )
    return result


def self_check(cases: list[Case]) -> list[tuple[Case, Verdict]]:
    """Grade every case's own reference answer against its own criteria.

    A case whose reference answer fails its own criteria is broken, and it is
    broken in the direction that matters: it marks a correct model wrong. This
    costs nothing to run and catches the mistake before any model is paid for.

    A case with alternatives is checked once for its overall reference, and
    once for each alternative's own reference against the case's criteria and
    that alternative's: every regimen the case accepts has to be shown to
    pass, not only the one the overall reference happens to describe.
    """
    broken: list[tuple[Case, Verdict]] = []
    for case in cases:
        verdict = grade(case, _reference_answer(case, case.reference))
        if not verdict.passed:
            broken.append((case, verdict))
            continue
        for alternative in case.alternatives:
            results = tuple(
                check(c, alternative.reference) for c in case.criteria + alternative.criteria
            )
            if not all(r.passed for r in results):
                broken.append((
                    case,
                    Verdict(
                        case_id=case.case_id, model="referencia", results=results,
                        alternative=alternative.description,
                    ),
                ))
                break
    return broken


def _reference_answer(case: Case, text: str) -> Answer:
    return Answer(case_id=case.case_id, model="referencia", text=text, asked_at=datetime.now())


@dataclass(frozen=True)
class NegativeControl:
    """A deliberately wrong answer that one criterion must catch.

    Built from the case's own reference answer by breaking exactly what the
    criterion checks, so no clinical content is invented: the terms a
    `contem` asks for are taken out, the value a `valor_numerico` asks for is
    doubled or halved, a term a `nao_contem` or `nao_prescreve` forbids is
    prescribed at the end. `text` is None when no such answer can be built,
    which is itself a finding: a criterion nobody can show failing proves
    nothing.
    """

    case_id: str
    criterion: Criterion
    change: str
    text: str | None
    alternative: str = ""


def negative_controls(case: Case) -> list[NegativeControl]:
    """Every negative control for every criterion of one case.

    A criterion of an alternative is broken in that alternative's own
    reference, so the control is a wrong version of that regimen and not of
    the overall answer.
    """
    controls: list[NegativeControl] = []
    targets = [(c, case.reference, "") for c in case.criteria] + [
        (c, a.reference, a.description) for a in case.alternatives for c in a.criteria
    ]
    for criterion, reference, alternative in targets:
        label = f"{alternative}: " if alternative else ""

        def add(change: str, text: str | None) -> None:
            controls.append(
                NegativeControl(case.case_id, criterion, label + change, text, alternative)
            )

        if criterion.kind == "contem":
            text = reference
            for term in criterion.terms:
                text = remove_term(text, term)
            add("sem " + ", ".join(criterion.terms), text)
        elif criterion.kind == "contem_todos":
            for term in criterion.terms:
                add(f"sem {term}", remove_term(reference, term))
        elif criterion.kind == "valor_numerico":
            expected = float(criterion.terms[0].replace(",", "."))
            unit = criterion.terms[1]
            tolerance = (
                float(criterion.terms[2].replace(",", ".")) if len(criterion.terms) > 2 else 0.0
            )
            built = False
            for wrong in (expected * 2, expected / 2):
                if abs(wrong - expected) <= tolerance:
                    continue
                text = replace_values(reference, unit, wrong)
                if text is not None:
                    add(f"{expected:g} {unit} trocado por {wrong:g}", text)
                    built = True
            if not built:
                add(f"sem valor errado possível para {expected:g} {unit}", None)
        else:
            for term in criterion.terms:
                add(f"com {term}", f"{reference} Iniciar {term}.")
                # A refusal marker in front of the forbidden term must not hide it.
                add(
                    f"recusa seguida de {term}",
                    f"Não posso fornecer aconselhamento individual. Em geral, iniciar {term}.",
                )
                if criterion.kind == "nao_prescreve":
                    # Denying a contraindication is not excluding the drug.
                    add(f"{term} dado como não contraindicado", f"{reference} {term} não está contraindicado.")
    return controls


def met_by_the_question(cases: list[Case]) -> list[tuple[Case, Criterion]]:
    """Positive criteria that the question alone, repeated back, already meets.

    Such a criterion cannot tell an answer from an echo of the question: a
    required term that the question contains ("sem contraceção", a "|" asked
    for in the format) passes whatever the answer says about it. Reported as
    a warning, not an error: fixing it means rewriting a criterion, which is
    a clinical decision with its reason in the commit.
    """
    found: list[tuple[Case, Criterion]] = []
    for case in cases:
        for criterion in case.all_criteria:
            if criterion.kind in _POSITIVE_KINDS and check(criterion, case.question).passed:
                found.append((case, criterion))
    return found


@dataclass(frozen=True)
class VerdictChange:
    """One answer whose verdict differs between a saved grading and the current one."""

    case_id: str
    model: str
    sample: int
    passed_before: bool
    passed_now: bool
    failures_before: tuple[str, ...]
    failures_now: tuple[str, ...]


def verdict_changes(
    saved: list[dict], cases: list[Case], answers: list[Answer], verdicts: list[Verdict]
) -> list[VerdictChange]:
    """What a change to the grader or the criteria did to answers already graded.

    `saved` is a verdicts file written earlier (vereditos.json), in the order
    the answers were graded; `verdicts` is the grading now, of the same
    answers. They are paired in that order and checked case by case and model
    by model, so a file that does not belong to these answers is refused
    rather than compared.
    """
    pairs = match_answers(cases, answers, verdicts)
    if len(saved) != len(pairs):
        raise ValueError(
            f"o ficheiro de veredictos tem {len(saved)} entradas e as respostas dão {len(pairs)}"
        )
    changes: list[VerdictChange] = []
    for old, (answer, now) in zip(saved, pairs):
        if (old.get("caso"), old.get("modelo")) != (answer.case_id, answer.model):
            raise ValueError(
                f"veredicto {old.get('caso')} ({old.get('modelo')}) não corresponde à resposta "
                f"{answer.case_id} ({answer.model}): os ficheiros não são do mesmo ensaio"
            )
        before = tuple(old.get("falhas", []))
        after = tuple(f.value for f in now.failures)
        if bool(old.get("passou")) != now.passed or before != after:
            changes.append(VerdictChange(
                answer.case_id, answer.model, answer.sample,
                bool(old.get("passou")), now.passed, before, after,
            ))
    return changes


def uncaught_controls(
    cases: list[Case],
) -> tuple[int, list[tuple[NegativeControl, Verdict | None]]]:
    """How many negative controls exist, and which ones got through.

    `self_check` shows each criterion passes the right answer; this shows each
    one can fail a wrong one, which `self_check` never tests. A control is
    caught when its criterion fails and the whole verdict, refusal detection
    included, carries that criterion's failure type. Without this, a
    criterion that can never fail looks exactly like one that never needed
    to.

    A criterion of an alternative is held to a different standard: the wrong
    answer must not be accepted by any alternative. Its failure type is then
    the one of whichever regimen the answer came closest to, which can
    rightly be another alternative's: "amoxicilina, 5 a 7 dias" with the
    clavulanate taken out reads as plain amoxicillin without its dose, a
    dose failure, and that verdict is correct.
    """
    total = 0
    uncaught: list[tuple[NegativeControl, Verdict | None]] = []
    for case in cases:
        for control in negative_controls(case):
            total += 1
            if control.text is None:
                uncaught.append((control, None))
                continue
            verdict = grade(
                case,
                Answer(
                    case_id=case.case_id,
                    model="controlo",
                    text=control.text,
                    asked_at=datetime.now(),
                ),
            )
            criterion_failed = not check(control.criterion, control.text).passed
            if control.alternative:
                caught = criterion_failed and not verdict.passed
            else:
                caught = criterion_failed and control.criterion.failure in verdict.failures
            if not caught:
                uncaught.append((control, verdict))
    return total, uncaught


__all__ = [
    "grade",
    "grade_all",
    "duplicate_samples",
    "tally",
    "tally_by_model",
    "self_check",
    "Tally",
    "match_answers",
    "pairs_by_case",
    "ConsistencyState",
    "Consistency",
    "consistency_by_case",
    "ConsistencySummary",
    "consistency_by_model",
    "states_by_model",
    "CASE_RULES",
    "DEFAULT_CASE_RULE",
    "case_is_right",
    "right_cases_by_model",
    "critical_by_category",
    "CriticalComparison",
    "compare_critical",
    "mcnemar_exact",
    "worst_examples",
    "expected_samples",
    "missing_samples",
    "wilson_interval",
    "RunConditions",
    "run_conditions",
    "NegativeControl",
    "negative_controls",
    "uncaught_controls",
    "met_by_the_question",
    "VerdictChange",
    "verdict_changes",
]
