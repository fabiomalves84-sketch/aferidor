"""What the numbers of a comparison between models decide, in one place.

The Markdown report and the HTML report both say whether a model reaches the reference threshold,
whether two models tie at the top, whether a difference is significant and how a share is
rounded. Those decisions were written out in each report; here they are written once, so the two
reports cannot disagree. Nothing here is a measurement: the counts come from `grading`, and
nothing in this module formats text for a page.
"""

from __future__ import annotations

from .grading import ConsistencySummary
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


def percent(value: float) -> str:
    """A share as every interval of the reports writes it: rounded to the nearest whole number."""
    return f"{value * 100:.0f}%"


__all__ = ["SIGNIFICANCE_LEVEL", "is_significant", "meets_reference", "models_meeting_reference", "percent"]
