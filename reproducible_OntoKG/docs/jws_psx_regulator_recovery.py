"""Offline, reviewed SECP source recovery; does not scrape or repair base graphs."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json

from jws_psx_authentic_prices import compare, endpoint_return

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/authentic_prices_psx'
REVIEWED_HASHES = {
    '2026-01-28': '79ffbf92d35448dc8607137d61c307dce73ceab8c4ffa012cf2e3729b0ca6b7b',
    '2026-01-29': '16501b092f8d4a30b82790f73dd52b568bdeb83be14fa17e58737385b9cd75b5',
    '2026-01-30': 'adc9326ac13882e7c1dd192435dccc8d1c6f5abe5008709f8f50f13950408e58',
    '2026-03-13': '4771b19b60ae2dba5237a2cd6477df8a28f09dedfb5bab0b01fb00863ffee5d6',
}
REPORTS = {
    '2026-01-28': [('KSE100', '2026-01-27', '188202.86'), ('KSE100', '2026-01-28', '188380.39')],
    '2026-01-29': [('KSE100', '2026-01-28', '188380.39'), ('KSE100', '2026-01-29', '182338.12'), ('FFC', '2026-01-29', '597.10')],
    '2026-01-30': [('KSE100', '2026-01-29', '182338.12'), ('KSE100', '2026-01-30', '184174.49')],
    '2026-03-13': [('KSE100', '2026-03-12', '154421.43'), ('KSE100', '2026-03-13', '153866.17'), ('FFC', '2026-03-13', '501.02')],
}
SLUGS = {'2026-01-28':'january-28', '2026-01-29':'january-29', '2026-01-30':'january-30', '2026-03-13':'march-13'}


def build():
    rows = {}
    docs = []
    for report_date, facts in REPORTS.items():
        pdf = OUT / 'evidence' / f'SECP_{report_date}.pdf'
        raw = pdf.read_bytes()
        assert raw.startswith(b'%PDF-'), f'Not a PDF: {pdf}'
        assert pdf.with_suffix('.png').exists(), 'Reviewed rendering required'
        url = f'https://www.secp.gov.pk/document/daily-stock-market-report-dated-{SLUGS[report_date]}-2026/'
        digest = hashlib.sha256(raw).hexdigest()
        if digest != REVIEWED_HASHES[report_date]:
            raise ValueError('Source copy changed: new visual review and a separate evidence version are required.')
        docs.append(dict(report_trade_date=report_date, source_url=url, sha256=digest,
                         bytes=len(raw), local_file=str(pdf.relative_to(ROOT)), page=1,
                         retrieval='public archive search, article attached-file link, browser download',
                         visual_review_date='2026-10-17', rights='Local research review only; not a redistribution licence'))
        for series, trade_date, value in facts:
            key = (series, trade_date)
            locator = (f'Stock Market Summary / KSE-100 / Index / explicitly labelled {trade_date} column'
                       if series == 'KSE100' else
                       ('Volume Leaders / Fauji Fert / Close Price; repeated Top 10 Index Drivers' if report_date == '2026-01-29'
                        else 'Top 10 Index Drivers / Fauji FertXD / Close Price'))
            evidence = dict(report_trade_date=report_date, source_url=url, sha256=digest, page=1, locator=locator)
            if key in rows:
                assert rows[key]['value'] == value, 'Conflicting duplicate source value'
                rows[key]['evidence'].append(evidence)
                continue
            rows[key] = dict(series=series, trade_date=trade_date, value=value,
                             return_basis='total_return' if series == 'KSE100' else 'unadjusted_price',
                             publisher='SECP', upstream_market='PSX', source_status='original_pdf_visually_verified',
                             admitted_to_authenticated_arithmetic=True, visual_page_verified=True,
                             evidence=[evidence], ex_dividend_marker=(series == 'FFC' and trade_date == '2026-03-13'))
    observations = list(rows.values())
    company = [r for r in observations if r['series'] == 'FFC']
    benchmark = [r for r in observations if r['series'] == 'KSE100']
    result = dict(status='partial_original_source_recovery_not_a_completed_event_study',
                  reviewed_documents=docs, observations=observations,
                  unique_authenticated_observations=len(observations),
                  company_endpoint_only=dict(start='2026-01-29', end='2026-03-13',
                                            price_return_percent=endpoint_return(company, '2026-01-29', '2026-03-13'),
                                            status='descriptive_unadjusted_price_change_not_total_return',
                                            caveat='End row explicitly XD. Cash distributions and other corporate actions not adjusted; not an announcement-effect estimate.'),
                  proposed_report_anchored_comparison=compare(company, benchmark, '2026-01-28', '2026-03-13'),
                  gaps=['FFC January 28 baseline close is absent from the reviewed January 28 summary.',
                        'FFC January 30 close is absent from the reviewed January 30 summary.',
                        'Jan29 opening price is not evidence of Jan28 closing price.',
                        'Authenticated KSE100PR price-return endpoints and daily series remain unavailable.',
                        'Remaining daily FFC prices/volumes and corporate-action adjustments remain unauthenticated.'],
                  unchanged_history='results.json and README.md preserve the earlier indexed-only acquisition stage; this separate report supersedes its zero-source coverage statement only.')
    assert len(observations) == 8
    assert result['proposed_report_anchored_comparison']['status'] == 'incompatible_return_basis'
    assert endpoint_return(company, '2026-01-28', '2026-03-13') is None
    assert Decimal(result['company_endpoint_only']['price_return_percent']) < 0
    return result


if __name__ == '__main__':
    result = build()
    (OUT / 'regulator_recovery.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['status', 'unique_authenticated_observations', 'company_endpoint_only', 'proposed_report_anchored_comparison']}, indent=2))
