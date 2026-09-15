"""The matching rules: what counts as saying the right thing."""

from __future__ import annotations

import unittest

from aferidor.checks import check, find_term, normalize
from aferidor.models import Criterion
from aferidor.risk import FailureType


def criterion(kind: str, *terms: str, failure=FailureType.DOSE_INCORRETA) -> Criterion:
    return Criterion(kind=kind, terms=terms, failure=failure)


class TestNormalize(unittest.TestCase):
    def test_accents_and_case_are_removed(self):
        self.assertEqual(normalize("Três Vezes"), "tres vezes")

    def test_runs_of_whitespace_become_one_space(self):
        self.assertEqual(normalize("1000\n  mg"), "1000 mg")

    def test_a_number_stuck_to_its_unit_is_separated(self):
        self.assertEqual(normalize("1000mg"), "1000 mg")
        self.assertEqual(normalize("500MG de amoxicilina"), "500 mg de amoxicilina")

    def test_a_word_that_ends_in_digits_is_left_alone(self):
        self.assertEqual(normalize("covid19"), "covid19")


class TestFindTerm(unittest.TestCase):
    def test_a_bare_number_does_not_match_inside_a_longer_number(self):
        self.assertEqual(find_term(normalize("500 mg"), "5"), -1)

    def test_a_bare_number_matches_on_its_own(self):
        self.assertGreaterEqual(find_term(normalize("durante 5 a 7 dias"), "5"), 0)

    def test_a_term_with_a_slash_still_matches_when_glued_to_a_unit(self):
        self.assertGreaterEqual(find_term(normalize("8/8h"), "8/8"), 0)

    def test_a_term_starting_with_a_digit_does_not_match_after_a_decimal_comma(self):
        self.assertEqual(find_term(normalize("apixabano 2,5 mg"), "5 mg"), -1)

    def test_a_term_starting_with_a_digit_does_not_match_inside_a_longer_number(self):
        self.assertEqual(find_term(normalize("dose de 25 mg"), "5 mg"), -1)
        self.assertEqual(find_term(normalize("cetorolac 100 mg"), "0 mg"), -1)

    def test_a_term_starting_with_a_digit_matches_on_its_own(self):
        self.assertGreaterEqual(find_term(normalize("tomar 5 mg"), "5 mg"), 0)


class TestContem(unittest.TestCase):
    def test_any_one_of_the_terms_is_enough(self):
        result = check(criterion("contem", "1000 mg", "1 g"), "dar 1 g de amoxicilina")
        self.assertTrue(result.passed)

    def test_the_evidence_quotes_what_was_seen(self):
        result = check(criterion("contem", "amoxicilina"), "prescrever amoxicilina oral")
        self.assertIn("amoxicilina", result.evidence)

    def test_none_of_the_terms_fails_and_names_them_all(self):
        result = check(criterion("contem", "1000 mg", "1 g"), "dar 500 mg")
        self.assertFalse(result.passed)
        self.assertIn("1000 mg", result.evidence)
        self.assertIn("1 g", result.evidence)

    def test_the_failure_type_travels_with_the_result(self):
        result = check(criterion("contem", "1000 mg"), "dar 500 mg")
        self.assertEqual(result.criterion.failure, FailureType.DOSE_INCORRETA)


class TestNaoContem(unittest.TestCase):
    def test_absence_passes(self):
        self.assertTrue(check(criterion("nao_contem", "1000 mg"), "dar 500 mg").passed)

    def test_presence_fails_and_shows_where(self):
        result = check(criterion("nao_contem", "1000 mg"), "dar 1000 mg de amoxicilina")
        self.assertFalse(result.passed)
        self.assertIn("1000 mg", result.evidence)


class TestContemTodos(unittest.TestCase):
    def test_all_present_passes(self):
        result = check(
            criterion("contem_todos", "ceftriaxona", "cefuroxima"),
            "ceftriaxona em dose unica, depois cefuroxima oral",
        )
        self.assertTrue(result.passed)

    def test_one_missing_fails_and_names_only_what_is_missing(self):
        result = check(
            criterion("contem_todos", "ceftriaxona", "cefuroxima"),
            "apenas ceftriaxona",
        )
        self.assertFalse(result.passed)
        self.assertIn("cefuroxima", result.evidence)
        self.assertNotIn("'ceftriaxona'", result.evidence)


class TestNaoPrescreve(unittest.TestCase):
    """The distinction plain matching could not make: giving a drug versus ruling it out."""

    def crit(self):
        return criterion(
            "nao_prescreve", "amoxicilina", failure=FailureType.CONTRAINDICACAO_OMITIDA
        )

    def test_not_mentioning_the_drug_passes(self):
        self.assertTrue(check(self.crit(), "Azitromicina 500 mg, 5 dias").passed)

    def test_naming_the_drug_to_rule_it_out_passes(self):
        for text in (
            "Azitromicina 500 mg. A amoxicilina esta contraindicada nesta situacao.",
            "Prescrever azitromicina. Nao usar amoxicilina.",
            "A amoxicilina deve ser evitada. Dar azitromicina.",
        ):
            with self.subTest(text=text):
                self.assertTrue(check(self.crit(), text).passed)

    def test_actually_prescribing_the_drug_fails(self):
        result = check(self.crit(), "Na hipersensibilidade tipo I, dar amoxicilina 500 mg.")
        self.assertFalse(result.passed)
        self.assertIn("prescreve", result.evidence)

    def test_the_question_wording_alone_does_not_excuse_a_prescription(self):
        """The words 'alergia' and 'hipersensibilidade' appear in every case of this
        kind, so they must not count as ruling the drug out."""
        text = "Doente com alergia e hipersensibilidade tipo I: prescrever amoxicilina."
        self.assertFalse(check(self.crit(), text).passed)

    def test_one_excluded_mention_does_not_cover_a_second_prescribing_one(self):
        text = (
            "A amoxicilina esta contraindicada. "
            + "x" * 200
            + " Comecar amoxicilina 1000 mg de 8 em 8 horas."
        )
        self.assertFalse(check(self.crit(), text).passed)

    def test_a_second_term_is_checked_too(self):
        crit = criterion(
            "nao_prescreve", "amoxicilina", "cefuroxima",
            failure=FailureType.CONTRAINDICACAO_OMITIDA,
        )
        self.assertFalse(check(crit, "Dar cefuroxima 250 mg.").passed)


class TestValorNumerico(unittest.TestCase):
    def test_the_exact_value_passes(self):
        self.assertTrue(check(criterion("valor_numerico", "6", "mg"), "dexametasona 6 mg").passed)

    def test_a_different_value_fails_and_reports_what_it_found(self):
        result = check(criterion("valor_numerico", "6", "mg"), "dexametasona 8 mg")
        self.assertFalse(result.passed)
        self.assertIn("8", result.evidence)

    def test_a_tolerance_is_honoured(self):
        self.assertTrue(
            check(criterion("valor_numerico", "6", "mg", "2"), "dexametasona 8 mg").passed
        )

    def test_a_decimal_comma_is_read_as_a_decimal_point(self):
        self.assertTrue(check(criterion("valor_numerico", "0,5", "mg"), "0,5 mg").passed)

    def test_no_value_in_that_unit_fails(self):
        result = check(criterion("valor_numerico", "6", "mg"), "sem dose indicada")
        self.assertFalse(result.passed)
        self.assertIn("mg", result.evidence)

    def test_a_missing_unit_is_refused_at_the_criterion(self):
        with self.assertRaises(ValueError):
            check(criterion("valor_numerico", "6"), "6 mg")


class TestUnknownKind(unittest.TestCase):
    def test_an_unknown_kind_never_gets_past_the_criterion(self):
        with self.assertRaises(ValueError):
            Criterion(kind="adivinha", terms=("x",), failure=FailureType.ALUCINACAO)


if __name__ == "__main__":
    unittest.main()
