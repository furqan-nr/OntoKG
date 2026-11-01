"""Consolidate recovered company evidence without manufacturing benchmark truth."""
from pathlib import Path
from decimal import Decimal, localcontext
import hashlib
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/source_backed_cohort'


def endpoint(observations, start, end):
    if start >= end:
        return None
    by_date = {}
    for row in observations:
        if row['value'] is None:
            continue
        value = Decimal(str(row['value']))
        date = row['trade_date']
        if date in by_date and by_date[date] != value:
            raise ValueError('Conflicting duplicate source observation')
        by_date[date] = value
    if start not in by_date or end not in by_date:
        return None
    if any(not x.is_finite() or x <= 0 for x in (by_date[start], by_date[end])):
        return None
    with localcontext() as context:
        context.prec = 40
        return str((by_date[end] / by_date[start] - 1) * 100)


def build():
    paths = {name: ROOT / f'evaluation_jws/{rel}' for name, rel in {
        'psx': 'authentic_prices_psx/regulator_recovery.json',
        'malaysia': 'authentic_prices_malaysia/results.json',
        'definitions': 'price_definition_audit/results.json',
        'roster': 'report_aligned_cohort/results.json'}.items()}
    data = {name: json.loads(path.read_text(encoding='utf-8')) for name, path in paths.items()}
    ffc = [r for r in data['psx']['observations'] if r['series'] == 'FFC']
    maybank = data['malaysia']['observations']
    roster = {r['symbol']: r for r in data['roster']['records']}
    records = []
    for symbol, observations, start, end, name in (
        ('FFC', ffc, '2026-01-29', '2026-03-13', 'FFC'),
        ('MAYBANK', maybank, '2026-03-31', '2026-05-14', 'Maybank')):
        policy = data['definitions']['cohort_eligibility'][name]
        # Neither source-backed comparison can be classified without a
        # compatible benchmark and resolved source definitions.
        assert not policy['eligible'], 'New eligible source version needs explicit benchmark replay implementation.'
        records.append(dict(company=symbol, existing_fixture_R1_label=roster[symbol]['numerical_R1_label'],
            source_qualified_R1_label=None, eligible=False, reasons=policy['reasons'],
            descriptive_company_only=dict(start=start, end=end,
                return_percent=endpoint(observations, start, end),
                initial_reaction=False, total_return=False,
                caveat='Different endpoint horizons must not be compared as if identical; source adjustment and corporate-action caveats remain.'),
            source_status='regulator_original_dated_close' if symbol == 'FFC' else 'issuer_republished_adjustment_basis_unresolved'))
    return dict(version='source-backed-cohort-v1',
        scope='Two recovered-company subsets of the eight-candidate PSX/MSX ledger, not independent additional findings.',
        input_sha256={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()},
        candidates=len(records), eligible_market_relative_comparisons=0,
        classifications_not_recomputed_due_to_missing_prerequisites=len(records), records=records,
        limits='Arithmetic company-only changes are recomputed; no proxy, total-return substitution, inferred baseline or unsupported market-relative label is admitted. Historical fixture labels are not source-qualified results.')


class Checks(unittest.TestCase):
    def test_known_endpoint(self):
        rows = [{'trade_date': '2026-01-01', 'value': '100'}, {'trade_date': '2026-01-02', 'value': '90'}]
        self.assertEqual(Decimal(endpoint(rows, '2026-01-01', '2026-01-02')), Decimal('-10'))
    def test_missing_endpoint(self):
        self.assertIsNone(endpoint([], '2026-01-01', '2026-01-02'))
    def test_no_benchmark_result(self):
        self.assertTrue(all(r['source_qualified_R1_label'] is None for r in build()['records']))
    def test_no_sample_inflation(self):
        self.assertEqual(build()['candidates'], 2)
        self.assertEqual(build()['eligible_market_relative_comparisons'], 0)
    def test_conflicting_duplicates_rejected(self):
        rows = [{'trade_date': '2026-01-01', 'value': '100'}, {'trade_date': '2026-01-01', 'value': '101'}]
        with self.assertRaises(ValueError):
            endpoint(rows, '2026-01-01', '2026-01-02')
    def test_invalid_horizon_rejected(self):
        self.assertIsNone(endpoint([], '2026-01-02', '2026-01-01'))


if __name__ == '__main__':
    import sys
    if '--test' in sys.argv:
        unittest.main(argv=[sys.argv[0]])
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        result = build()
        (OUT / 'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))
