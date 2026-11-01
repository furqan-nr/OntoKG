"""Independent label guard and end-to-end analytical baseline parity tests."""
import unittest
from jws_boundary_analytical_benchmark import run, assert_expected, fixture, pools, baseline

class AnalyticalTests(unittest.TestCase):
    def test_complete_benchmark(self):
        report=run()
        self.assertEqual(report['cases'],26)
        self.assertEqual(report['paired_pool_checks'],78)
        self.assertEqual(report['preserved_inputs_before'],report['preserved_inputs_after'])

    def test_wrong_label_fails(self):
        with self.assertRaises(AssertionError):assert_expected(('unknown',False),('false',True),'negative-control')

    def test_unit_witness_not_laundered(self):
        g=fixture('r1_unit_laundering','R1')
        self.assertEqual(baseline(pools(g)['delivered'],'R1'),('positive',False))
        g=fixture('r1_qualified_alternative','R1')
        self.assertEqual(baseline(pools(g)['delivered'],'R1'),('positive',True))

if __name__=='__main__':unittest.main()
