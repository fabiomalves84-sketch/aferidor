"""The matching rules: what counts as saying the right thing."""

from __future__ import annotations

import unittest

from aferidor.checks import REFUSAL_CRITERION, check, find_term, is_refusal, normalize
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

    def test_a_bare_number_does_not_match_inside_a_decimal(self):
        self.assertEqual(find_term(normalize("2,5 mg"), "5"), -1)
        self.assertEqual(find_term(normalize("5,5 dias"), "5"), -1)

    def test_a_bare_number_matches_a_range(self):
        self.assertGreaterEqual(find_term(normalize("5-7 dias"), "5"), 0)

    def test_a_term_with_a_slash_still_matches_when_glued_to_a_unit(self):
        self.assertGreaterEqual(find_term(normalize("8/8h"), "8/8"), 0)

    def test_a_term_starting_with_a_digit_does_not_match_after_a_decimal_comma(self):
        self.assertEqual(find_term(normalize("apixabano 2,5 mg"), "5 mg"), -1)

    def test_a_term_starting_with_a_digit_does_not_match_inside_a_longer_number(self):
        self.assertEqual(find_term(normalize("dose de 25 mg"), "5 mg"), -1)
        self.assertEqual(find_term(normalize("cetorolac 100 mg"), "0 mg"), -1)

    def test_a_term_starting_with_a_digit_matches_on_its_own(self):
        self.assertGreaterEqual(find_term(normalize("tomar 5 mg"), "5 mg"), 0)

    def test_a_total_dose_term_does_not_match_a_per_kilo_dose(self):
        self.assertEqual(find_term(normalize("dar 5 mg/kg"), "5 mg"), -1)
        self.assertEqual(find_term(normalize("dar 5 mg / kg"), "5 mg"), -1)

    def test_a_per_kilo_term_still_matches_a_per_kilo_dose(self):
        self.assertGreaterEqual(find_term(normalize("dar 80 mg/kg/dia"), "80 mg/kg"), 0)

    def test_a_total_dose_term_still_matches_a_daily_total(self):
        self.assertGreaterEqual(find_term(normalize("dar 1000 mg/dia"), "1000 mg"), 0)

    def test_a_total_dose_term_does_not_match_a_concentration(self):
        self.assertEqual(find_term(normalize("suspensão de 500 mg/5 ml"), "500 mg"), -1)
        self.assertEqual(find_term(normalize("xarope 40 mg/ml"), "40 mg"), -1)
        self.assertEqual(find_term(normalize("250 mg / 5ml"), "250 mg"), -1)

    def test_a_dose_next_to_a_concentration_still_matches(self):
        text = normalize("suspensão 250 mg/5 ml: dar 500 mg de 12/12h")
        self.assertGreaterEqual(find_term(text, "500 mg"), 0)

    def test_a_word_term_does_not_match_in_the_middle_of_another_word(self):
        """Seen in the 16/09 run: two answers to ATB-PAC-001 gave no interval at all
        and passed the interval criterion because `tid` was found in `mantida` and
        `discutida`."""
        self.assertEqual(find_term(normalize("terapeutica mantida"), "tid"), -1)
        text = normalize("evitar o consumo de sumo")
        self.assertEqual(find_term(text, "sumo"), text.rindex("sumo"))

    def test_a_word_term_still_matches_at_the_start_of_a_word(self):
        self.assertGreaterEqual(find_term(normalize("amoxicilina tid"), "tid"), 0)
        self.assertGreaterEqual(find_term(normalize("(TID)"), "tid"), 0)
        self.assertGreaterEqual(find_term(normalize("contraindicação"), "contraindica"), 0)

    def test_a_longer_stem_may_still_end_in_the_middle_of_a_word(self):
        self.assertGreaterEqual(find_term(normalize("diminuição da urina"), "urin"), 0)
        self.assertGreaterEqual(find_term(normalize("não urinou"), "urin"), 0)

    def test_a_short_acronym_must_end_the_word(self):
        self.assertEqual(find_term(normalize("ajustar ao peso"), "pes"), -1)
        self.assertEqual(find_term(normalize("pessoas com diabetes"), "pes"), -1)
        self.assertGreaterEqual(find_term(normalize("exame dos pés"), "pes"), 0)

    def test_a_short_acronym_may_take_a_plural_s(self):
        self.assertGreaterEqual(find_term(normalize("os AVKs"), "avk"), 0)


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

    def test_a_per_kilo_dose_does_not_satisfy_a_total_dose_criterion(self):
        result = check(criterion("contem", "5 mg"), "dar 5 mg/kg")
        self.assertFalse(result.passed)


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

    def test_an_exclusion_in_the_previous_sentence_does_not_cover_a_prescription(self):
        """Found in the code review: in type I hypersensitivity, cefuroxime given
        right after "amoxicilina contraindicada" passed as excluded, and the
        critical failure vanished from the verdict."""
        crit = criterion(
            "nao_prescreve", "cefuroxima", failure=FailureType.CONTRAINDICACAO_OMITIDA
        )
        for text in (
            "A amoxicilina está contraindicada. Em alternativa, cefuroxima 500 mg de 12/12h.",
            "A amoxicilina está contraindicada.\n\nTratamento: cefuroxima 250 mg.",
        ):
            with self.subTest(text=text):
                self.assertFalse(check(crit, text).passed)

    def test_an_unrelated_warning_in_the_next_sentence_does_not_excuse_a_prescription(self):
        """Once a known limit of the README: "Evitar alcool" used to excuse the drug."""
        self.assertFalse(check(self.crit(), "Amoxicilina 1000 mg 8/8h. Evitar álcool.").passed)

    def test_a_semicolon_or_a_numbered_list_does_not_end_the_sentence(self):
        crit = criterion(
            "nao_prescreve", "cefuroxima", failure=FailureType.CONTRAINDICACAO_OMITIDA
        )
        for text in (
            "A amoxicilina está contraindicada; a cefuroxima também.",
            "Não usar os seguintes fármacos: 1. amoxicilina 2. cefuroxima",
        ):
            with self.subTest(text=text):
                self.assertTrue(check(crit, text).passed)

    def test_a_term_inside_another_word_is_not_a_prescription(self):
        crit = criterion("nao_prescreve", "sumo", failure=FailureType.AJUSTE_OMITIDO)
        self.assertTrue(check(crit, "Soro de reidratacao oral; reduzir o consumo de leite.").passed)
        self.assertFalse(check(crit, "Dar sumo de maca diluido.").passed)


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

    def test_a_total_dose_criterion_does_not_accept_a_per_kilo_dose(self):
        result = check(criterion("valor_numerico", "1000", "mg"), "1000 mg/kg/dia")
        self.assertFalse(result.passed)

    def test_a_per_kilo_criterion_still_accepts_a_per_kilo_dose(self):
        self.assertTrue(
            check(criterion("valor_numerico", "80", "mg/kg"), "80 mg/kg/dia").passed
        )

    def test_a_total_dose_criterion_still_accepts_a_daily_total(self):
        self.assertTrue(
            check(criterion("valor_numerico", "1000", "mg"), "1000 mg/dia").passed
        )

    def test_a_total_dose_criterion_does_not_accept_a_concentration(self):
        result = check(criterion("valor_numerico", "500", "mg"), "suspensão 500 mg/5 ml, 5 ml")
        self.assertFalse(result.passed)

    def test_a_concentration_criterion_still_accepts_a_concentration(self):
        self.assertTrue(check(criterion("valor_numerico", "40", "mg/ml"), "xarope 40 mg/ml").passed)

    def test_a_period_as_thousands_separator_is_read_as_one_thousand(self):
        self.assertTrue(check(criterion("valor_numerico", "1000", "mg"), "1.000 mg").passed)

    def test_a_space_as_thousands_separator_is_read_as_one_thousand(self):
        self.assertTrue(check(criterion("valor_numerico", "1000", "mg"), "1 000 mg").passed)

    def test_a_value_in_grams_counts_as_the_same_value_in_milligrams_times_1000(self):
        self.assertTrue(check(criterion("valor_numerico", "1000", "mg"), "1 g").passed)
        self.assertTrue(check(criterion("valor_numerico", "500", "mg"), "0,5 g").passed)

    def test_a_period_that_is_not_a_thousands_separator_is_still_a_decimal(self):
        self.assertTrue(
            check(criterion("valor_numerico", "0,125", "mg"), "0.125 mg").passed
        )


class TestUnknownKind(unittest.TestCase):
    def test_an_unknown_kind_never_gets_past_the_criterion(self):
        with self.assertRaises(ValueError):
            Criterion(kind="adivinha", terms=("x",), failure=FailureType.ALUCINACAO)


class TestRefusalCriterion(unittest.TestCase):
    def test_a_refusal_seen_in_a_real_run_is_caught(self):
        result = check(
            REFUSAL_CRITERION,
            "Lamento, mas não posso fornecer uma resposta específica para a pergunta.",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.criterion.failure, FailureType.RECUSA_INDEVIDA)

    def test_a_correct_answer_that_ends_by_naming_a_doctor_is_not_a_refusal(self):
        result = check(
            REFUSAL_CRITERION,
            "Amoxicilina 1000 mg de 8/8h. Se os sintomas se agravarem, consulte um médico.",
        )
        self.assertTrue(result.passed)


class TestIsRefusal(unittest.TestCase):
    def test_a_pure_refusal_is_a_refusal(self):
        self.assertTrue(
            is_refusal("Lamento, mas não posso fornecer uma resposta específica para a pergunta.")
        )

    def test_a_courtesy_warning_with_a_dose_is_not_a_refusal(self):
        self.assertFalse(
            is_refusal(
                "Amoxicilina 500 mg 8/8h. Não posso fornecer uma avaliação individual "
                "completa; consulte um profissional de saúde."
            )
        )

    def test_no_marker_at_all_is_not_a_refusal(self):
        self.assertFalse(is_refusal("Amoxicilina 500 mg de 8/8h durante 7 dias."))

    def test_a_dose_per_kilo_still_counts_as_a_dose(self):
        self.assertFalse(is_refusal("Não posso fornecer... 10 mg/kg de amoxicilina."))

    def test_a_rate_or_concentration_copied_from_the_question_is_not_a_dose(self):
        """A refusal that repeats the clearance, a lab value or a syrup strength
        from the question is still a refusal, not an answer with a dose."""
        for text in (
            "Lamento, mas não posso dar aconselhamento sobre metformina com depuração de 40 ml/min.",
            "Não posso fornecer uma dose com creatinina de 1,5 mg/dl.",
            "Não me é possível indicar a dose do xarope de 40 mg/ml.",
        ):
            with self.subTest(text=text):
                self.assertTrue(is_refusal(text))

    def test_a_dose_next_to_a_copied_rate_still_counts_as_a_dose(self):
        self.assertFalse(
            is_refusal("Com 40 ml/min, metformina 1000 mg/dia. Não posso fornecer mais detalhe.")
        )


if __name__ == "__main__":
    unittest.main()
