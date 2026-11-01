"""Replay issuer-published Maybank history; never substitute a KLCI proxy.

The CSV is a public issuer-IR download, not exchange-original authentication.
Its Close adjustment convention remains unspecified (URL says unadjusted=0).
"""
import csv
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/authentic_prices_malaysia'
CSV = OUT / 'maybank_issuer_published_20260302_20260529.csv'
CAPTURE_SHA256 = '74f65433ad1faf6003054000fd08ae80cda90ab8016c99618d1385c2c93d56a5'
URL = 'https://maybank.listedcompany.com/historical_price_download.html?date_start=20260302&date_end=20260529&unadjusted=0'


def prices(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        rows = {}
        for row_number, row in enumerate(reader, 2):
            raw = row['Date']
            date = f'{raw[:4]}-{raw[4:6]}-{raw[6:]}'
            assert date not in rows, 'Ambiguous duplicate trade date'
            assert Decimal(row['Close']) > 0
            rows[date] = dict(row, csv_line=row_number)
        return rows


def endpoint(rows, start, end):
    if start not in rows or end not in rows:
        return None
    with localcontext() as context:
        context.prec = 40
        return str((Decimal(rows[end]['Close']) / Decimal(rows[start]['Close']) - 1) * 100)


def build():
    if hashlib.sha256(CSV.read_bytes()).hexdigest() != CAPTURE_SHA256:
        raise ValueError('Issuer capture changed; create a new reviewed version rather than silently replacing evidence.')
    source = json.loads((ROOT / 'evaluation_jws/report_aligned_cohort/results.json').read_text())
    case = next(r for r in source['records'] if r['symbol'] == 'MAYBANK')
    dates = case['observed_horizon']['dates']
    rows = prices(CSV)
    required = sorted(set(dates + ['2026-03-31', '2026-04-01']))
    observations = [dict(instrument='MAYBANK / Malayan Banking Berhad / Bursa stock code 1155',
        trade_date=d, value=rows[d]['Close'] if d in rows else None, field='Close',
        field_locator=f"CSV line {rows[d]['csv_line']}, Close column" if d in rows else None,
        currency='MYR', session='daily historical OHLC; exact session/timezone not specified in CSV',
        publisher_class='issuer_IR_republished_data_not_exchange_original',
        status='issuer_published_close_basis_unresolved' if d in rows else 'unavailable',
        retrieval_date='2026-10-17', source_url=URL) for d in required]
    # Existing cells are retained separately; compare in their declared date order.
    old_cells = [c for c in case['source_cells'] if c['field'] == 'close']
    comparisons = [dict(date=d, original=old_cells[i]['value'],
        issuer_published=rows[d]['Close'] if d in rows else None,
        matches=Decimal(old_cells[i]['value']) == Decimal(rows[d]['Close']) if d in rows else False)
        for i, d in enumerate(dates)]
    result = dict(review_date='2026-10-17',
        source_url=URL, landing_url='https://maybank.listedcompany.com/historical_price.html?date_start=20260301&date_end=20260529',
        capture_method='Public browser month controls and published Download CSV Sheet link; no account or bypass',
        sha256=hashlib.sha256(CSV.read_bytes()).hexdigest(), complete_download_rows=len(rows),
        required_company_dates=len(required), required_company_dates_present=sum(d in rows for d in required),
        original_post_dates=len(dates), original_post_dates_matching=sum(c['matches'] for c in comparisons),
        adjustment_status='unresolved: exported Close field, download parameter unadjusted=0; no explanatory convention in viewed page/CSV',
        observations=observations, comparisons=comparisons,
        descriptive_as_published_company_returns_percent={
            'first_post_close_to_final_close': endpoint(rows, dates[0], dates[-1]),
            'disclosure_date_close_to_final_close': endpoint(rows, '2026-04-01', dates[-1]),
            'last_observed_pre_disclosure_date_close_to_final_close': endpoint(rows, '2026-03-31', dates[-1])},
        compatible_authenticated_benchmark_observations=0,
        authenticated_benchmark_classification=None,
        classification_status='incomplete_no_primary_KLCI_dates_and_company_adjustment_basis_unresolved',
        initial_reaction_status='not_established: official document date lacks first-publication timestamp; annual report is not necessarily first earnings news',
        volume_status='March published volumes available, but pre-event horizon must be prespecified and units independently confirmed; no new volume finding',
        redistribution_status='Public download available; redistribution licence not established. Keep captured file local pending licence review.',
        routes=[
            dict(url='https://www.bursamalaysia.com/market_information/market_statistic/market_statistics', result='not_accessible_via_research_tool; no security bypass attempted'),
            dict(url='https://www.lseg.com/en/ftse-russell/indices/bursa-malaysia', result='official index resources inspected; no exact-date public historical levels recovered; client/sales routes not pursued'),
            dict(url='https://research.ftserussell.com/Analytics/FactSheets/Home/DownloadSingleIssue?isManual=False&issueName=FBMKLCI&openfile=open', result='monthly factsheet search result; not an exact daily close and not substituted'),
            dict(url='https://bernama.com/bm/news.php?id=2557055', result='secondary news reports May14 spot KLCI1745.58 separately from futures; lead only, not primary replacement'),
            dict(url='https://maybank.listedcompany.com/historical_price.html', result='direct HTTP202 empty; ordinary browser controls returned full table and downloadable CSV')])
    return result


class Checks(unittest.TestCase):
    def test_dates_and_hash(self):
        result=build()
        self.assertEqual(result['required_company_dates_present'],32)
        self.assertEqual(result['original_post_dates_matching'],30)
        self.assertEqual(result['sha256'],'74f65433ad1faf6003054000fd08ae80cda90ab8016c99618d1385c2c93d56a5')
    def test_no_imputation(self):
        self.assertIsNone(endpoint(prices(CSV),'2026-04-04','2026-05-14'))
    def test_no_benchmark_promotion(self):
        self.assertIsNone(build()['authenticated_benchmark_classification'])
    def test_published_endpoints(self):
        rows=prices(CSV)
        self.assertEqual([rows[d]['Close'] for d in ['2026-03-31','2026-04-01','2026-04-02','2026-05-14']],['11.360','11.660','11.460','11.180'])


if __name__ == '__main__':
    import sys
    if '--test' in sys.argv:
        unittest.main(argv=[sys.argv[0]])
    else:
        result=build()
        (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ['required_company_dates_present','original_post_dates_matching','classification_status']}))
