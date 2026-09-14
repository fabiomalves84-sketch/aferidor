import unittest

from aferidor.risk import FailureType, Risk, failure_from_label


class TestFailureTaxonomy(unittest.TestCase):
    def test_every_failure_has_a_risk(self):
        for failure in FailureType:
            self.assertIsInstance(failure.risk, Risk)

    def test_dosing_and_interactions_are_critical(self):
        self.assertEqual(FailureType.DOSE_INCORRETA.risk, Risk.CRITICO)
        self.assertEqual(FailureType.INTERACAO_OMITIDA.risk, Risk.CRITICO)
        self.assertEqual(FailureType.CONTRAINDICACAO_OMITIDA.risk, Risk.CRITICO)
        self.assertEqual(FailureType.ALUCINACAO.risk, Risk.CRITICO)

    def test_formatting_outranks_nothing(self):
        self.assertLess(
            FailureType.FORMATO_INVALIDO.risk.value,
            FailureType.DOSE_INCORRETA.risk.value,
        )

    def test_label_round_trip(self):
        for failure in FailureType:
            self.assertIs(failure_from_label(failure.value), failure)

    def test_unknown_label_names_the_alternatives(self):
        with self.assertRaises(ValueError) as caught:
            failure_from_label("dose_mais_ou_menos_certa")
        self.assertIn("dose_incorreta", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
