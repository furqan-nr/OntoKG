"""Oracle logic controls independent of RDF/interpreter semantics."""
import unittest
from jws_nhs_source_oracle import classify, integer


class SourceOracleTests(unittest.TestCase):
    def test_count_inputs(self):
        for value in ['0', 1, '123.0']:
            self.assertEqual(integer(value), int(float(value)))
        for value in ['', None, -1, '1.5', 'NaN', True, 'suppressed']:
            with self.assertRaises((ValueError, ArithmeticError)):
                integer(value)

    def test_threshold_is_inclusive_and_not_rounded(self):
        self.assertEqual(classify(92, 100), 'at_least_92_percent')
        self.assertEqual(classify(91999, 100000), 'below_92_percent')
        self.assertEqual(classify(92001, 100000), 'at_least_92_percent')

    def test_zero_denominator(self):
        self.assertEqual(classify(0, 0), 'not_applicable')


if __name__ == '__main__':
    unittest.main()
