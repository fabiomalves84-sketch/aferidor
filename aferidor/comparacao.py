"""What the numbers of a comparison between models decide, in one place.

The Markdown report and the HTML report both say whether a model reaches the reference threshold,
whether two models tie at the top, whether a difference is significant and how a share is
rounded. Those decisions were written out in each report; here they are written once, so the two
reports cannot disagree. Nothing here is a measurement: the counts come from `grading`, and
nothing in this module formats text for a page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from .grading import Consistency, ConsistencySummary, compare_critical
from .protocolo import REFERENCE_CRITICAL_LIMIT

# A difference between the two best models counts as significant when the exact McNemar p-value
# is below this level (a p-value of exactly 0.05 is not below it).
SIGNIFICANCE_LEVEL = 0.05


def is_significant(p_value: float) -> bool:
    return p_value < SIGNIFICANCE_LEVEL


def meets_reference(summary: ConsistencySummary) -> bool:
    """The reference threshold: no more cases with a critical failure than the projects' protocols allow."""
    return summary.critical_cases <= REFERENCE_CRITICAL_LIMIT


def models_meeting_reference(summaries: dict[str, ConsistencySummary]) -> list[str]:
    return [model for model, summary in summaries.items() if meets_reference(summary)]


class Row(NamedTuple):
    """One model's critical cases and the 95% Wilson interval, as `grading.compare_critical` gives them."""

    model: str
    critical: int
    cases: int
    low: float
    high: float

    @property
    def share(self) -> float:
        return self.critical / self.cases


@dataclass(frozen=True)
class Ranking:
    """The models from fewest to most cases with a critical failure, and the paired comparison of the
    first two (None when the cases are not known or there is only one model)."""

    rows: tuple[Row, ...]
    overlap: bool
    only_first: int | None
    only_second: int | None
    p_value: float | None


def ranking(
    summaries: dict[str, ConsistencySummary],
    consistency: dict[tuple[str, str], Consistency] | None = None,
) -> Ranking:
    result = compare_critical(summaries, consistency)
    return Ranking(
        tuple(Row(*row) for row in result.rows), result.overlap,
        result.only_first, result.only_second, result.p_value,
    )


def same_proportion(first: Row, second: Row) -> bool:
    """The same share of cases with a critical failure, whatever the number of cases (4 of 10 and 8 of 20)."""
    return first.critical * second.cases == second.critical * first.cases


def top_tie(rows: tuple[Row, ...]) -> tuple[Row, ...]:
    """The models that share the best proportion with the first one; the first alone when none does."""
    return tuple(row for row in rows if same_proportion(row, rows[0]))


def same_numbers(group: tuple[Row, ...]) -> bool:
    """Whether the group also shares the counts, and not only the proportion."""
    return all((row.critical, row.cases) == (group[0].critical, group[0].cases) for row in group)


def percent(value: float) -> str:
    """A share as every interval of the reports writes it: rounded to the nearest whole number."""
    return f"{value * 100:.0f}%"


__all__ = [
    "SIGNIFICANCE_LEVEL", "Ranking", "Row", "is_significant", "meets_reference", "models_meeting_reference",
    "percent", "ranking", "same_numbers", "same_proportion", "top_tie",
]
