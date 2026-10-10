"""Verdicts and counts: what the bench concludes, and what it refuses to hide."""

from __future__ import annotations

import unittest

from aferidor.grading import (
    Consistency,
    ConsistencyState,
    case_is_right,
    consistency_by_case,
    consistency_by_model,
    expected_samples,
    grade,
    grade_all,
    mcnemar_exact,
    met_by_the_question,
    missing_samples,
    negative_controls,
    right_cases_by_model,
    self_check,
    tally,
    tally_by_model,
    uncaught_controls,
    verdict_changes,
)
from aferidor.models import Case, Criterion, Source
from aferidor.risk import FailureType, Risk
from tests.helpers import a_two_regimen_case, an_answer


def a_case(case_id: str = "C1") -> Case:
    return Case(
        case_id=case_id,
        category="dose",
        question="Que dose?",
        reference="Amoxicilina 1000 mg 8/8h",
        source=Source(name="Guia", reference="p. 17"),
        criteria=(
            Criterion(kind="contem", terms=("amoxicilina",), failure=FailureType.RESPOSTA_INCOMPLETA),
            Criterion(kind="contem", terms=("1000 mg", "1 g"), failure=FailureType.DOSE_INCORRETA),
        ),
    )


class TestGrade(unittest.TestCase):
    def test_an_answer_meeting_every_criterion_passes(self):
        verdict = grade(a_case(), an_answer("Amoxicilina 1000 mg de 8/8h"))
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.failures, ())
        self.assertIsNone(verdict.worst_risk)

    def test_a_wrong_dose_is_classified_as_a_dose_failure(self):
        verdict = grade(a_case(), an_answer("Amoxicilina 500 mg"))
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failures, (FailureType.DOSE_INCORRETA,))
        self.assertEqual(verdict.worst_risk, Risk.CRITICO)

    def test_the_worst_failure_is_reported_first(self):
        verdict = grade(a_case(), an_answer("nao sei"))
        self.assertEqual(verdict.failures[0], FailureType.DOSE_INCORRETA)

    def test_every_criterion_leaves_a_result_with_evidence(self):
        verdict = grade(a_case(), an_answer("Amoxicilina 500 mg"))
        self.assertEqual(len(verdict.results), 2)
        self.assertTrue(all(r.evidence for r in verdict.results))

    def test_a_short_refusal_gives_only_recusa_indevida_even_without_a_case_criterion_for_it(self):
        # a_case() has no refusal criterion of its own, the way ATB-DPOC-002
        # did not; the central check has to catch it anyway.
        verdict = grade(
            a_case(),
            an_answer("Lamento, mas não posso fornecer uma resposta específica para a pergunta."),
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failures, (FailureType.RECUSA_INDEVIDA,))
        self.assertEqual(verdict.worst_risk, Risk.BAIXO)
        self.assertEqual(len(verdict.results), 1)

    def test_a_long_correct_answer_that_names_a_doctor_is_not_a_refusal(self):
        verdict = grade(
            a_case(),
            an_answer("Amoxicilina 1000 mg de 8/8h. Se agravar, consulte um médico."),
        )
        self.assertTrue(verdict.passed)

    def test_a_courtesy_warning_with_the_right_dose_passes(self):
        verdict = grade(
            a_case(),
            an_answer(
                "Amoxicilina 1000 mg de 8/8h. Não posso fornecer uma avaliação "
                "individual completa para o seu caso."
            ),
        )
        self.assertTrue(verdict.passed)

    def test_a_courtesy_warning_with_the_wrong_dose_gives_dose_incorreta(self):
        verdict = grade(
            a_case(),
            an_answer(
                "Amoxicilina 500 mg de 8/8h. Não posso fornecer uma avaliação "
                "individual completa para o seu caso."
            ),
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failures, (FailureType.DOSE_INCORRETA,))

    def no_dose_case(self) -> Case:
        """A case whose right answer is "no", with no dose in it, like PED-04."""
        return Case(
            case_id="C1",
            category="pediatria",
            question="Pode dar aspirina a uma criança com varicela?",
            reference="Não. Contraindicada pelo risco de síndrome de Reye.",
            source=Source(name="Guia", reference="p. 1"),
            criteria=(
                Criterion(kind="contem", terms=("reye",), failure=FailureType.RESPOSTA_INCOMPLETA),
                Criterion(
                    kind="nao_prescreve", terms=("ibuprofeno",),
                    failure=FailureType.CONTRAINDICACAO_OMITIDA,
                ),
            ),
        )

    def test_a_correct_no_dose_answer_with_a_refusal_marker_passes(self):
        verdict = grade(
            self.no_dose_case(),
            an_answer("Não me é possível recomendar aspirina: risco de síndrome de Reye."),
        )
        self.assertTrue(verdict.passed)

    def test_an_answered_reply_with_a_marker_still_fails_its_negative_criteria(self):
        verdict = grade(
            self.no_dose_case(),
            an_answer("Não me é possível recomendar aspirina (síndrome de Reye). Dar ibuprofeno."),
        )
        self.assertEqual(verdict.failures, (FailureType.CONTRAINDICACAO_OMITIDA,))

    def test_a_pure_refusal_on_a_no_dose_case_is_still_a_refusal(self):
        """A refusal passes every negative criterion by saying nothing, so only the
        positive ones can show the question was answered."""
        verdict = grade(self.no_dose_case(), an_answer("Lamento, mas não posso ajudar com isso."))
        self.assertEqual(verdict.failures, (FailureType.RECUSA_INDEVIDA,))

    def test_grading_an_answer_against_the_wrong_case_is_refused(self):
        with self.assertRaises(ValueError):
            grade(a_case("C1"), an_answer("qualquer", case_id="C2"))

    def test_the_model_travels_from_the_answer_to_the_verdict(self):
        verdict = grade(a_case(), an_answer("Amoxicilina 1 g", model="openai:gpt-4o"))
        self.assertEqual(verdict.model, "openai:gpt-4o")


class TestGradeAll(unittest.TestCase):
    def test_a_case_that_was_never_answered_is_reported_not_ignored(self):
        cases = [a_case("C1"), a_case("C2")]
        verdicts, missing = grade_all(cases, [an_answer("Amoxicilina 1 g", case_id="C1")])
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(missing, ["C2"])

    def test_an_answer_to_an_unknown_case_is_reported_too(self):
        verdicts, missing = grade_all([a_case("C1")], [an_answer("x", case_id="C9")])
        self.assertEqual(verdicts, [])
        self.assertIn("C9", missing)
        self.assertIn("C1", missing)


class TestMissingSamples(unittest.TestCase):
    def test_a_case_with_fewer_samples_than_expected_is_named(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("Amoxicilina 1000 mg", case_id="C1", model="qwen", sample=s)
            for s in (1, 2)
        ] + [
            an_answer("Amoxicilina 1000 mg", case_id="C2", model="qwen", sample=s)
            for s in (1, 2, 3)
        ]
        gaps = missing_samples(cases, answers)
        self.assertEqual(gaps[("C1", "qwen")], (3,))
        self.assertNotIn(("C2", "qwen"), gaps)

    def test_a_model_that_never_answered_one_case_is_named_with_every_sample(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("Amoxicilina 1000 mg", case_id="C1", model="llama", sample=s)
            for s in (1, 2)
        ]
        gaps = missing_samples(cases, answers)
        self.assertEqual(gaps[("C2", "llama")], (1, 2))

    def test_a_case_answered_by_one_model_and_not_another_is_not_hidden(self):
        """The scenario grade_all's plain 'missing' list cannot see: the case
        has an answer from someone, so it never looks unanswered, even though
        one model never touched it."""
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("Amoxicilina 1000 mg", case_id="C1", model="llama"),
            an_answer("Amoxicilina 1000 mg", case_id="C2", model="qwen"),
        ]
        _, missing = grade_all(cases, answers)
        gaps = missing_samples(cases, answers)
        self.assertEqual(missing, [])
        self.assertIn(("C1", "qwen"), gaps)
        self.assertIn(("C2", "llama"), gaps)

    def test_expected_samples_is_the_highest_sample_seen_per_model(self):
        answers = [
            an_answer("x", case_id="C1", model="llama", sample=1),
            an_answer("x", case_id="C2", model="llama", sample=5),
            an_answer("x", case_id="C1", model="qwen", sample=2),
        ]
        self.assertEqual(expected_samples(answers), {"llama": 5, "qwen": 2})


class TestTally(unittest.TestCase):
    def test_counts_split_by_failure_and_by_risk(self):
        verdicts = [
            grade(a_case("C1"), an_answer("Amoxicilina 1 g", case_id="C1")),
            grade(a_case("C2"), an_answer("Amoxicilina 500 mg", case_id="C2")),
            grade(a_case("C3"), an_answer("nao sei", case_id="C3")),
        ]
        counts = tally(verdicts)
        self.assertEqual(counts.total, 3)
        self.assertEqual(counts.passed, 1)
        self.assertEqual(counts.failed, 2)
        self.assertAlmostEqual(counts.accuracy, 1 / 3)
        self.assertEqual(counts.by_failure[FailureType.DOSE_INCORRETA], 2)
        self.assertEqual(counts.by_failure[FailureType.RESPOSTA_INCOMPLETA], 1)
        self.assertEqual(counts.critical, 2)

    def test_the_worst_risk_is_listed_first(self):
        verdicts = [grade(a_case("C1"), an_answer("nao sei", case_id="C1"))]
        first = tally(verdicts).worst_first()[0][0]
        self.assertEqual(first.risk, Risk.CRITICO)

    def test_failed_cases_are_named_with_their_failures(self):
        verdicts = [grade(a_case("C2"), an_answer("Amoxicilina 500 mg", case_id="C2"))]
        self.assertEqual(tally(verdicts).failed_cases["C2"], ("dose_incorreta",))

    def test_a_case_failing_in_two_samples_names_both_failures(self):
        """With several samples the case used to keep only the last failing
        sample's failures, hiding that it failed in two different ways."""
        verdicts = [
            grade(a_case("C2"), an_answer("Dar 1000 mg", case_id="C2", sample=1)),
            grade(a_case("C2"), an_answer("Amoxicilina 500 mg", case_id="C2", sample=2)),
            grade(a_case("C2"), an_answer("Amoxicilina 500 mg", case_id="C2", sample=3)),
        ]
        named = tally(verdicts).failed_cases["C2"]
        self.assertEqual(sorted(named), ["dose_incorreta", "resposta_incompleta"])

    def test_an_empty_tally_does_not_divide_by_zero(self):
        self.assertEqual(tally([]).accuracy, 0.0)

    def test_mixing_two_models_in_one_tally_is_refused(self):
        verdicts = [
            grade(a_case("C1"), an_answer("x", case_id="C1", model="um")),
            grade(a_case("C2"), an_answer("x", case_id="C2", model="dois")),
        ]
        with self.assertRaises(ValueError):
            tally(verdicts)

    def test_tally_by_model_keeps_each_model_apart(self):
        verdicts = [
            grade(a_case("C1"), an_answer("Amoxicilina 1 g", case_id="C1", model="um")),
            grade(a_case("C2"), an_answer("nao sei", case_id="C2", model="dois")),
        ]
        counts = tally_by_model(verdicts)
        self.assertEqual(sorted(counts), ["dois", "um"])
        self.assertEqual(counts["um"].passed, 1)
        self.assertEqual(counts["dois"].passed, 0)


class TestConsistency(unittest.TestCase):
    def test_every_sample_passing_is_estavel_certo(self):
        cases = [a_case("C1")]
        answers = [
            an_answer("Amoxicilina 1000 mg", case_id="C1", sample=1),
            an_answer("Amoxicilina 1 g", case_id="C1", sample=2),
        ]
        verdicts, _ = grade_all(cases, answers)
        consistency = consistency_by_case(cases, answers, verdicts)
        entry = consistency[("C1", "falso")]
        self.assertEqual(entry.samples, 2)
        self.assertEqual(entry.passed, 2)
        self.assertEqual(entry.state, ConsistencyState.ESTAVEL_CERTO)

    def test_every_sample_failing_is_estavel_errado(self):
        cases = [a_case("C1")]
        answers = [
            an_answer("Amoxicilina 500 mg", case_id="C1", sample=1),
            an_answer("Amoxicilina 500 mg", case_id="C1", sample=2),
        ]
        verdicts, _ = grade_all(cases, answers)
        consistency = consistency_by_case(cases, answers, verdicts)
        entry = consistency[("C1", "falso")]
        self.assertEqual(entry.passed, 0)
        self.assertEqual(entry.state, ConsistencyState.ESTAVEL_ERRADO)
        self.assertEqual(entry.worst_failure, FailureType.DOSE_INCORRETA)

    def test_a_mix_of_passing_and_failing_samples_is_instavel(self):
        cases = [a_case("C1")]
        answers = [
            an_answer("Amoxicilina 1000 mg", case_id="C1", sample=1),
            an_answer("Amoxicilina 500 mg", case_id="C1", sample=2),
        ]
        verdicts, _ = grade_all(cases, answers)
        consistency = consistency_by_case(cases, answers, verdicts)
        entry = consistency[("C1", "falso")]
        self.assertEqual(entry.passed, 1)
        self.assertEqual(entry.state, ConsistencyState.INSTAVEL)

    def test_the_worst_failure_seen_in_any_sample_is_kept(self):
        cases = [a_case("C1")]
        answers = [
            an_answer("Amoxicilina 1000 mg", case_id="C1", sample=1),
            an_answer("nao sei", case_id="C1", sample=2),
        ]
        verdicts, _ = grade_all(cases, answers)
        consistency = consistency_by_case(cases, answers, verdicts)
        self.assertEqual(consistency[("C1", "falso")].worst_failure, FailureType.DOSE_INCORRETA)

    def test_summary_counts_cases_not_samples(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("Amoxicilina 1000 mg", case_id="C1", sample=1),
            an_answer("Amoxicilina 500 mg", case_id="C1", sample=2),
            an_answer("Amoxicilina 500 mg", case_id="C2", sample=1),
            an_answer("Amoxicilina 500 mg", case_id="C2", sample=2),
        ]
        verdicts, _ = grade_all(cases, answers)
        consistency = consistency_by_case(cases, answers, verdicts)
        summary = consistency_by_model(consistency)["falso"]
        self.assertEqual(summary.cases, 2)
        self.assertEqual(summary.critical_cases, 2)
        self.assertEqual(summary.unstable_cases, 1)
        self.assertAlmostEqual(summary.sample_accuracy, 1 / 4)


def an_entry(passed: int, worst: FailureType | None, samples: int = 5, case_id: str = "C1") -> Consistency:
    if passed == samples:
        state = ConsistencyState.ESTAVEL_CERTO
    elif passed == 0:
        state = ConsistencyState.ESTAVEL_ERRADO
    else:
        state = ConsistencyState.INSTAVEL
    return Consistency(case_id, "falso", samples, passed, worst, state)


class TestRefusalDoesNotHideAPrescription(unittest.TestCase):
    def forbidding_case(self) -> Case:
        return Case(
            case_id="C1", category="pediatria", question="Posso dar aspirina a uma criança com varicela?",
            reference="Não. A aspirina está contraindicada (síndrome de Reye); usar paracetamol.",
            source=Source(name="Guia", reference="p. 1"),
            criteria=(
                Criterion(kind="contem", terms=("reye",), failure=FailureType.RESPOSTA_INCOMPLETA),
                Criterion(kind="nao_prescreve", terms=("aspirina",), failure=FailureType.CONTRAINDICACAO_OMITIDA),
            ),
        )

    def test_a_refusal_followed_by_a_forbidden_drug_carries_the_critical_failure(self):
        verdict = grade(self.forbidding_case(), an_answer(
            "Não posso fornecer aconselhamento individual. Em geral, pode dar aspirina.", case_id="C1"))
        self.assertIn(FailureType.CONTRAINDICACAO_OMITIDA, verdict.failures)
        self.assertIn(FailureType.RECUSA_INDEVIDA, verdict.failures)

    def test_a_plain_refusal_is_still_only_a_refusal(self):
        verdict = grade(self.forbidding_case(), an_answer(
            "Não posso fornecer aconselhamento individual.", case_id="C1"))
        self.assertEqual(verdict.failures, (FailureType.RECUSA_INDEVIDA,))

    def test_denying_the_contraindication_is_a_prescription(self):
        verdict = grade(self.forbidding_case(), an_answer(
            "Sim. A aspirina não está contraindicada; síndrome de Reye é raro.", case_id="C1"))
        self.assertIn(FailureType.CONTRAINDICACAO_OMITIDA, verdict.failures)


class TestCaseRule(unittest.TestCase):
    """One yes or no per case; the rule decides how many samples that takes."""

    def test_the_default_rule_wants_every_sample_right(self):
        self.assertTrue(case_is_right(an_entry(5, None)))
        self.assertFalse(case_is_right(an_entry(4, FailureType.RESPOSTA_INCOMPLETA)))

    def test_a_majority_is_not_enough_if_one_sample_was_critical(self):
        rule = "maioria_sem_critica"
        self.assertTrue(case_is_right(an_entry(3, FailureType.RESPOSTA_INCOMPLETA), rule))
        self.assertFalse(case_is_right(an_entry(4, FailureType.DOSE_INCORRETA), rule))
        self.assertFalse(case_is_right(an_entry(2, FailureType.RESPOSTA_INCOMPLETA), rule))

    def test_the_loosest_rule_only_asks_for_no_critical_failure(self):
        rule = "nenhuma_critica"
        self.assertTrue(case_is_right(an_entry(0, FailureType.RESPOSTA_INCOMPLETA), rule))
        self.assertFalse(case_is_right(an_entry(4, FailureType.DOSE_INCORRETA), rule))

    def test_an_unknown_rule_is_refused(self):
        with self.assertRaises(ValueError):
            case_is_right(an_entry(5, None), "quase_todas")

    def test_right_cases_are_counted_per_model(self):
        consistency = {
            ("C1", "falso"): an_entry(5, None, case_id="C1"),
            ("C2", "falso"): an_entry(3, FailureType.RESPOSTA_INCOMPLETA, case_id="C2"),
        }
        self.assertEqual(right_cases_by_model(consistency), {"falso": (1, 2)})
        self.assertEqual(right_cases_by_model(consistency, "maioria_sem_critica"), {"falso": (2, 2)})


class TestVerdictChanges(unittest.TestCase):
    """What a change to the grader did to answers already graded."""

    def setUp(self):
        from aferidor.storage import verdict_to_dict

        self.cases = [a_case("C1")]
        self.answers = [
            an_answer("Amoxicilina 1000 mg", case_id="C1", sample=1),
            an_answer("Amoxicilina 500 mg", case_id="C1", sample=2),
        ]
        self.verdicts, _ = grade_all(self.cases, self.answers)
        self.saved = [verdict_to_dict(v) for v in self.verdicts]

    def test_the_same_grading_changes_nothing(self):
        self.assertEqual(verdict_changes(self.saved, self.cases, self.answers, self.verdicts), [])

    def test_a_verdict_that_flipped_is_named_with_its_sample(self):
        self.saved[1]["passou"], self.saved[1]["falhas"] = True, []
        [change] = verdict_changes(self.saved, self.cases, self.answers, self.verdicts)
        self.assertEqual((change.sample, change.passed_before, change.passed_now), (2, True, False))

    def test_a_verdicts_file_of_other_answers_is_refused(self):
        self.saved[0]["caso"] = "C9"
        with self.assertRaises(ValueError):
            verdict_changes(self.saved, self.cases, self.answers, self.verdicts)


class TestMcNemar(unittest.TestCase):
    """The paired test on the cases where exactly one of two models failed."""

    def test_no_discordant_case_means_no_evidence_of_a_difference(self):
        self.assertEqual(mcnemar_exact(0, 0), 1.0)
        self.assertEqual(mcnemar_exact(5, 5), 1.0)

    def test_values_match_the_exact_binomial(self):
        self.assertAlmostEqual(mcnemar_exact(0, 6), 2 / 64)
        self.assertAlmostEqual(mcnemar_exact(1, 9), 2 * 11 / 1024)
        self.assertAlmostEqual(mcnemar_exact(9, 1), mcnemar_exact(1, 9))


class TestMetByTheQuestion(unittest.TestCase):
    def test_a_required_term_the_question_already_contains_is_reported(self):
        case = Case(
            case_id="C1", category="gravidez", question="Mulher sem contraceção, a tomar valproato?",
            reference="Não iniciar; referenciar e assegurar contraceção eficaz.",
            source=Source(name="Guia", reference="p. 1"),
            criteria=(
                Criterion(kind="contem", terms=("contracecao",), failure=FailureType.RESPOSTA_INCOMPLETA),
                Criterion(kind="contem", terms=("referenciar",), failure=FailureType.ENCAMINHAMENTO_OMITIDO),
            ),
        )
        found = met_by_the_question([case])
        self.assertEqual([c.terms for _, c in found], [("contracecao",)])


class TestSelfCheck(unittest.TestCase):
    def test_a_case_whose_reference_meets_its_criteria_is_not_reported(self):
        self.assertEqual(self_check([a_case()]), [])

    def test_a_case_whose_own_reference_fails_is_reported(self):
        broken = Case(
            case_id="MAU",
            category="dose",
            question="Que dose?",
            reference="Amoxicilina 500 mg",
            source=Source(name="Guia", reference="p. 1"),
            criteria=(
                Criterion(
                    kind="contem", terms=("1000 mg",), failure=FailureType.DOSE_INCORRETA
                ),
            ),
        )
        found = self_check([broken])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0].case_id, "MAU")
        self.assertFalse(found[0][1].passed)

    def test_the_real_case_file_is_checked_by_this_test_suite(self):
        from pathlib import Path as _Path

        from aferidor.storage import read_cases

        path = _Path(__file__).resolve().parent.parent / "casos" / "casos.json"
        if not path.exists():
            self.skipTest("sem ficheiro de casos")
        broken = self_check(read_cases(path))
        names = [case.case_id for case, _ in broken]
        self.assertEqual(
            names, [], f"a referencia destes casos nao passa nos proprios criterios: {names}"
        )


if __name__ == "__main__":
    unittest.main()


def a_wide_case(tolerance: str) -> Case:
    return Case(
        case_id="LARGO",
        category="dose",
        question="Que dose?",
        reference="Amoxicilina 1000 mg de 8/8h.",
        source=Source(name="Guia", reference="p. 1"),
        criteria=(
            Criterion(
                kind="valor_numerico", terms=("1000", "mg", tolerance),
                failure=FailureType.DOSE_INCORRETA,
            ),
        ),
    )


class TestDuplicates(unittest.TestCase):
    def test_the_same_sample_twice_is_refused_and_named(self):
        answers = [an_answer("Amoxicilina 1000 mg"), an_answer("Amoxicilina 1000 mg")]
        with self.assertRaises(ValueError) as raised:
            grade_all([a_case()], answers)
        self.assertIn("C1 (falso, amostra 1)", str(raised.exception))

    def test_different_samples_or_models_are_not_duplicates(self):
        answers = [
            an_answer("x", sample=1),
            an_answer("x", sample=2),
            an_answer("x", sample=1, model="outro"),
        ]
        verdicts, _ = grade_all([a_case()], answers)
        self.assertEqual(len(verdicts), 3)


class TestNegativeControls(unittest.TestCase):
    """self_check shows the right answer passes; these show a wrong one fails."""

    def test_a_contem_control_takes_every_accepted_term_out(self):
        (dose,) = [c for c in negative_controls(a_case()) if "1000 mg" in c.criterion.terms]
        self.assertNotIn("1000 mg", dose.text)
        self.assertNotIn("1 g", dose.text)

    def test_a_valor_numerico_control_doubles_and_halves_the_value(self):
        texts = [c.text for c in negative_controls(a_wide_case("0"))]
        self.assertEqual(len(texts), 2)
        self.assertIn("2000 mg", texts[0])
        self.assertIn("500 mg", texts[1])

    def test_a_forbidden_term_is_prescribed_at_the_end(self):
        case = Case(
            case_id="C1", category="alergia", question="?",
            reference="Azitromicina 500 mg. A amoxicilina esta contraindicada.",
            source=Source(name="Guia", reference="p. 1"),
            criteria=(
                Criterion(
                    kind="nao_prescreve", terms=("amoxicilina",),
                    failure=FailureType.CONTRAINDICACAO_OMITIDA,
                ),
            ),
        )
        controls = negative_controls(case)
        self.assertTrue(controls[0].text.endswith("Iniciar amoxicilina."))
        self.assertEqual(
            [c.change for c in controls],
            ["com amoxicilina", "recusa seguida de amoxicilina",
             "amoxicilina dado como não contraindicado"],
        )
        _, uncaught = uncaught_controls([case])
        self.assertEqual(uncaught, [], "a reference ending in an exclusion must not excuse it")

    def test_every_control_of_a_sound_case_is_caught(self):
        total, uncaught = uncaught_controls([a_case()])
        self.assertEqual(total, 2)
        self.assertEqual(uncaught, [])

    def test_a_tolerance_too_wide_to_fail_is_reported(self):
        """A criterion that accepts both double and half the dose cannot be shown
        failing, and that is reported rather than counted as proven."""
        total, uncaught = uncaught_controls([a_wide_case("5000")])
        self.assertEqual(total, 1)
        self.assertEqual(len(uncaught), 1)
        self.assertIsNone(uncaught[0][0].text)

    def test_a_half_wide_tolerance_keeps_the_control_it_can_build(self):
        total, uncaught = uncaught_controls([a_wide_case("600")])
        self.assertEqual(total, 1)
        self.assertEqual(uncaught, [])


class TestAlternatives(unittest.TestCase):
    """A case whose source accepts two regimens: either one is right, a mix is not."""

    def grade(self, text: str):
        return grade(a_two_regimen_case(), an_answer(text, case_id="AMIG"))

    def test_the_first_regimen_passes_and_is_named(self):
        verdict = self.grade("Amoxicilina 50 mg/kg/dia de 12/12h, 10 dias.")
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.alternative, "amoxicilina 10 dias")

    def test_the_second_regimen_passes_and_is_named(self):
        verdict = self.grade("Penicilina G benzatínica 1.200.000 U IM, dose única.")
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.alternative, "penicilina benzatínica em dose única")

    def test_naming_the_other_drug_in_passing_does_not_rescue_a_wrong_dose(self):
        verdict = self.grade(
            "Amoxicilina 25 mg/kg/dia de 12/12h, 10 dias. A penicilina benzatínica é outra opção."
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failures, (FailureType.DOSE_INCORRETA,))
        self.assertEqual(verdict.alternative, "amoxicilina 10 dias")

    def test_a_wrong_answer_is_judged_against_the_regimen_it_came_closest_to(self):
        verdict = self.grade("Penicilina G benzatínica 600.000 U IM em dose única.")
        self.assertEqual(verdict.alternative, "penicilina benzatínica em dose única")
        self.assertEqual(verdict.failures, (FailureType.DOSE_INCORRETA,))

    def test_a_tie_between_regimens_never_hides_a_critical_failure(self):
        """Missing the benzathine dose (critical) and missing the word 'amoxicilina'
        with everything else of that regimen present (medium) are one failure
        each; the verdict must keep the critical one."""
        import dataclasses

        case = a_two_regimen_case()
        amoxicillin = dataclasses.replace(
            case.alternatives[0],
            criteria=(
                Criterion(kind="contem", terms=("amoxicilina",), failure=FailureType.RESPOSTA_INCOMPLETA),
                Criterion(kind="contem", terms=("dose unica",), failure=FailureType.RESPOSTA_INCOMPLETA),
            ),
            reference="Amoxicilina em dose única.",
        )
        case = dataclasses.replace(case, alternatives=(amoxicillin, case.alternatives[1]))
        verdict = grade(case, an_answer("Penicilina G benzatínica IM em dose única.", case_id="AMIG"))
        self.assertEqual(verdict.failures, (FailureType.DOSE_INCORRETA,))
        self.assertEqual(verdict.alternative, "penicilina benzatínica em dose única")

    def test_the_case_own_criteria_still_apply_to_every_regimen(self):
        verdict = self.grade("Penicilina G benzatínica 1.200.000 U IM em dose única, ou azitromicina.")
        self.assertEqual(verdict.failures, (FailureType.RESPOSTA_INCOMPLETA,))

    def test_self_check_passes_a_sound_case(self):
        self.assertEqual(self_check([a_two_regimen_case()]), [])

    def test_self_check_reports_an_alternative_whose_own_reference_fails(self):
        import dataclasses

        case = a_two_regimen_case()
        broken_alt = dataclasses.replace(case.alternatives[1], reference="Penicilina benzatínica IM.")
        case = dataclasses.replace(case, alternatives=(case.alternatives[0], broken_alt))
        found = self_check([case])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][1].alternative, "penicilina benzatínica em dose única")

    def test_every_control_of_every_regimen_is_built_and_caught(self):
        total, uncaught = uncaught_controls([a_two_regimen_case()])
        # 1 + 4 + 3 criterion controls, plus the refusal control of the forbidden term.
        self.assertEqual(total, 1 + 4 + 3 + 2)
        self.assertEqual(uncaught, [])

    def test_a_control_of_an_alternative_is_built_from_that_alternative(self):
        controls = negative_controls(a_two_regimen_case())
        benzathine = [c for c in controls if c.change.startswith("penicilina benzat")]
        self.assertEqual(len(benzathine), 3)
        self.assertTrue(all("amoxicilina" not in c.text for c in benzathine))

    def test_a_control_of_an_alternative_is_caught_when_no_regimen_accepts_it(self):
        """Taking the drug's name out of one regimen can leave an answer that reads
        closer to the other regimen, with that regimen's failure. It is still a
        rejected wrong answer, which is what the control has to show."""
        import dataclasses

        case = a_two_regimen_case()
        loose = dataclasses.replace(
            case.alternatives[1],
            reference="Penicilina G benzatínica 1.200.000 U IM em dose única, 10 dias.",
        )
        case = dataclasses.replace(case, alternatives=(case.alternatives[0], loose))
        total, uncaught = uncaught_controls([case])
        self.assertEqual(uncaught, [])

    def test_a_control_accepted_through_another_regimen_is_reported(self):
        """If breaking one regimen leaves an answer another regimen accepts, the
        criterion proved nothing, and that has to show up."""
        import dataclasses

        case = a_two_regimen_case()
        both = dataclasses.replace(
            case.alternatives[1],
            reference=(
                "Penicilina G benzatínica 1.200.000 U IM em dose única; "
                "ou amoxicilina 50 mg/kg/dia de 12/12h durante 10 dias."
            ),
        )
        case = dataclasses.replace(case, alternatives=(case.alternatives[0], both))
        _, uncaught = uncaught_controls([case])
        self.assertTrue(uncaught)
        self.assertTrue(all(c.alternative for c, _ in uncaught))

    def test_a_single_alternative_is_refused(self):
        import dataclasses

        case = a_two_regimen_case()
        with self.assertRaises(ValueError):
            dataclasses.replace(case, alternatives=case.alternatives[:1])
