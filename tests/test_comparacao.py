"""What the numbers of a comparison decide: the threshold, the tie at the top, significance, the rounding."""

from __future__ import annotations

import unittest

from aferidor.comparacao import (
    SIGNIFICANCE_LEVEL,
    is_significant,
    meets_reference,
    models_meeting_reference,
    percent,
    ranking,
    same_numbers,
    same_proportion,
    top_tie,
)
from aferidor.grading import ConsistencySummary


def summaries(*results: tuple[str, int, int]) -> dict[str, ConsistencySummary]:
    """Summaries built by hand: (model, cases with a critical failure, cases)."""
    return {
        model: ConsistencySummary(model=model, cases=cases, critical_cases=critical, unstable_cases=0, sample_accuracy=0.5)
        for model, critical, cases in results
    }


class TestTheReferenceThreshold(unittest.TestCase):
    def test_a_model_with_no_case_with_a_critical_failure_meets_it_and_one_with_a_single_case_does_not(self):
        both = summaries(("a", 0, 27), ("b", 1, 27))
        self.assertTrue(meets_reference(both["a"]))
        self.assertFalse(meets_reference(both["b"]))

    def test_the_models_that_meet_it_are_named_in_the_order_given(self):
        data = summaries(("a", 3, 27), ("b", 0, 27), ("c", 0, 10))
        self.assertEqual(models_meeting_reference(data), ["b", "c"])
        self.assertEqual(models_meeting_reference(summaries(("a", 2, 27))), [])


class TestTheTieAtTheTop(unittest.TestCase):
    def rows(self, *results):
        return ranking(summaries(*results)).rows

    def test_the_same_proportion_over_different_numbers_of_cases_is_a_tie_without_the_same_counts(self):
        rows = self.rows(("a", 4, 10), ("b", 8, 20), ("c", 9, 10))
        tied = top_tie(rows)
        self.assertEqual([r.model for r in tied], ["a", "b"])
        self.assertFalse(same_numbers(tied))
        self.assertTrue(same_proportion(rows[0], rows[1]))
        self.assertFalse(same_proportion(rows[0], rows[2]))

    def test_the_same_counts_are_a_tie_with_the_same_numbers(self):
        tied = top_tie(self.rows(("a", 8, 27), ("b", 8, 27), ("c", 16, 27)))
        self.assertEqual([r.model for r in tied], ["a", "b"])
        self.assertTrue(same_numbers(tied))

    def test_without_a_tie_the_first_stands_alone(self):
        tied = top_tie(self.rows(("a", 8, 27), ("b", 11, 27)))
        self.assertEqual([r.model for r in tied], ["a"])

    def test_the_rows_have_names_and_the_first_has_the_fewest_cases_with_a_critical_failure(self):
        first = self.rows(("b", 11, 27), ("a", 8, 27))[0]
        self.assertEqual((first.model, first.critical, first.cases), ("a", 8, 27))
        self.assertAlmostEqual(first.share, 8 / 27)
        self.assertLess(first.low, first.share)
        self.assertGreater(first.high, first.share)


class TestSignificance(unittest.TestCase):
    def test_a_p_value_of_exactly_the_level_is_not_significant_and_just_below_it_is(self):
        self.assertEqual(SIGNIFICANCE_LEVEL, 0.05)
        self.assertFalse(is_significant(0.05))
        self.assertTrue(is_significant(0.049))
        self.assertFalse(is_significant(0.375))


class TestPercent(unittest.TestCase):
    def test_a_share_is_rounded_to_the_nearest_whole_number(self):
        self.assertEqual(percent(8 / 27), "30%")
        self.assertEqual(percent(0.0), "0%")
        self.assertEqual(percent(1.0), "100%")
        self.assertEqual(percent(0.496), "50%")


if __name__ == "__main__":
    unittest.main()
