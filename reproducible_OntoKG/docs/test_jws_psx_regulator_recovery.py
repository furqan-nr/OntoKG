import unittest
from unittest.mock import patch
import jws_psx_regulator_recovery as recovery
from decimal import Decimal
from jws_psx_regulator_recovery import build, endpoint_return


class RegulatorRecoveryTests(unittest.TestCase):
    def test_reviewed_hash_mismatch_rejected(self):
        with patch.dict(recovery.REVIEWED_HASHES, {'2026-01-28': '0' * 64}):
            with self.assertRaisesRegex(ValueError, 'Source copy changed'):
                build()

    @classmethod
    def setUpClass(cls):
        cls.report = build()

    def test_original_sources_and_unique_coverage(self):
        self.assertEqual(len(self.report['reviewed_documents']), 4)
        self.assertEqual(self.report['unique_authenticated_observations'], 8)
        self.assertTrue(all(len(d['sha256']) == 64 for d in self.report['reviewed_documents']))

    def test_missing_company_baseline_stays_missing(self):
        company = [r for r in self.report['observations'] if r['series'] == 'FFC']
        self.assertIsNone(endpoint_return(company, '2026-01-28', '2026-03-13'))
        self.assertEqual(len(company), 2)

    def test_mixed_basis_not_promoted(self):
        comparison = self.report['proposed_report_anchored_comparison']
        self.assertEqual(comparison['status'], 'incompatible_return_basis')
        self.assertIsNone(comparison['label'])

    def test_endpoint_decimal_and_xd(self):
        result = self.report['company_endpoint_only']
        self.assertEqual(Decimal(result['price_return_percent']), (Decimal('501.02') / Decimal('597.10') - 1) * 100)
        end = next(r for r in self.report['observations'] if r['series'] == 'FFC' and r['trade_date'] == '2026-03-13')
        self.assertTrue(end['ex_dividend_marker'])


if __name__ == '__main__':
    unittest.main()
