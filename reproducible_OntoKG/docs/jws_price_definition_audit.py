"""Source-specific, fail-closed eligibility audit; no market data scraping."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/price_definition_audit'


def eligibility(company_basis, benchmark_basis, baseline_present, benchmark_present,
                action_review_complete=False):
    reasons = []
    if company_basis == 'unknown':
        reasons.append('company_adjustment_definition_unresolved')
    if not benchmark_present:
        reasons.append('compatible_benchmark_endpoints_absent')
    elif company_basis != benchmark_basis:
        reasons.append('incompatible_or_unresolved_return_basis')
    if not baseline_present:
        reasons.append('company_pre_anchor_baseline_absent')
    if not action_review_complete:
        reasons.append('corporate_action_review_incomplete')
    return {'eligible': not reasons, 'reasons': reasons,
            'event_effect_established': False}


def build():
    return {
        'review_date': '2026-10-17',
        'status': 'bounded_primary_source_definition_audit_no_new_price_admissions',
        'source_specific_definitions': [
            {'source_url': 'https://dps.psx.com.pk/company/FFC',
             'feed': 'PSX company-page historical series and displayed returns',
             'locator': 'legend below market quote immediately before Company Profile',
             'verification': 'primary_page_rendered_text',
             'split_adjusted': True, 'payout_adjusted_returns': False,
             'scope': 'Only this page/feed; does not authenticate SECP dated close fields or original workbook basis.'},
            {'source_url': 'https://maybank.listedcompany.com/historical_price.html?date_start=20260301&date_end=20260529',
             'feed': 'Maybank issuer-IR published historical table',
             'verification': 'ordinary_browser_accessibility_review',
             'visible_fields': ['Date', 'Open', 'High', 'Low', 'Close', "Vol (\'00)"],
             'adjustment_basis': 'unknown',
             'reason': 'No adjustment legend, help link or toggle was visible. CSV unadjusted=0 is not a documented definition.',
             'scope': 'Other listedcompany issuers have adjustment notes, but their definitions cannot be transferred to Maybank.'},
        ],
        'acquisition_routes': [
            {'source_url': 'https://www.lseg.com/en/ftse-russell/indices/bursa-malaysia',
             'outcome': 'Official page separates total and price return; current performance and monthly resources do not provide required daily endpoints.',
             'required': ['KLCI price-return 2026-03-31', 'KLCI price-return 2026-04-01', 'KLCI price-return 2026-05-14']},
            {'source_url': 'https://financials.psx.com.pk/lib/DownloadPDF.php?id=270829',
             'outcome': 'Official FFC annual-report route timed out; indexed text is not promoted to reviewed fact.'},
            {'source_url': 'https://www.psx.com.pk/psx/files?file=269423-1.pdf',
             'outcome': 'Official revised-trading notice route timed out; not reviewed.'},
            {'source_url': 'https://www.secp.gov.pk/document/daily-stock-market-report-dated-january-28-2026/',
             'outcome': 'Existing reviewed original summary lacks FFC baseline; no alternate primary close recovered.'},
        ],
        'corporate_actions': {
            'FFC': {'status': 'incomplete',
                    'reviewed_evidence': 'Existing 2026-03-13 SECP row explicitly marks Fauji FertXD.',
                    'new_primary_amount_or_ex_date_verified': False,
                    'reason': 'Secondary dividend leads disagree on ex-date; no exact ex-date inferred from book closure or XD row. Issuance lead also needs issuer verification.'},
            'Maybank': {'status': 'incomplete',
                        'new_primary_amount_or_ex_date_verified': False,
                        'reason': 'Dividend-history search leads are not issuer-verified; Maybank Indonesia is a different entity and excluded.'}},
        'cohort_eligibility': {
            'Maybank': eligibility('unknown', 'price_return', True, False),
            'FFC': eligibility('price_only_dated_close', 'total_return', False, True)},
        'new_authenticated_benchmark_observations': 0,
        'rights': 'No account, payment, subscription, contact, access bypass or redistribution licence assumed. Existing captures and base graphs unchanged.'}


class Tests(unittest.TestCase):
    def test_unknown_basis_rejected(self):
        self.assertFalse(eligibility('unknown', 'price_return', True, True, True)['eligible'])
    def test_total_return_substitution_rejected(self):
        self.assertFalse(eligibility('price_return', 'total_return', True, True, True)['eligible'])
    def test_missing_baseline_rejected(self):
        self.assertFalse(eligibility('price_return', 'price_return', False, True, True)['eligible'])
    def test_matching_prices_not_causality(self):
        result = eligibility('price_return', 'price_return', True, True, True)
        self.assertTrue(result['eligible'])
        self.assertFalse(result['event_effect_established'])
    def test_real_cohort_not_promoted(self):
        self.assertTrue(all(not v['eligible'] for v in build()['cohort_eligibility'].values()))


if __name__ == '__main__':
    import sys
    if '--test' in sys.argv:
        unittest.main(argv=[sys.argv[0]])
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        result = build()
        (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result['cohort_eligibility'], indent=2))
