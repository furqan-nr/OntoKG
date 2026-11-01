"""Fail-closed PSX price-source acquisition ledger; never fills missing prices.

The bounded search found indexed primary documents, not successfully retrieved
PDF bytes. These leads are deliberately excluded from authenticated arithmetic.
PSX pages prohibit automated retrieval/caching without written permission; this
script makes no network requests and does not distribute raw exchange data.
"""
from pathlib import Path
from decimal import Decimal
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/authentic_prices_psx'
JAN = 'https://www.secp.gov.pk/document/daily-stock-market-report-dated-january-29-2026/?refresh=6a336fd2d98241781755858&wpdmdl=63558'
MAR = 'https://www.secp.gov.pk/document/daily-stock-market-report-dated-march-13-2026/?refresh=69f1bc4ea41951777450062&wpdmdl=64172'
QUOTE = 'https://dps.psx.com.pk/download/quote/2026-01-29.pdf'


def record(series, date, value, url, locator, basis, **extra):
    return dict(series=series, trade_date=date, value=value, source_url=url,
                publisher='PSX' if 'dps.psx' in url else 'SECP', upstream_market='PSX',
                review_date='2026-10-16', source_status='indexed_primary_document_lead',
                raw_document_sha256=None, raw_document_retrieved=False,
                visual_page_verified=False, locator=locator, return_basis=basis,
                admitted_to_authenticated_arithmetic=False, **extra)


LEADS = [
    record('FFC','2026-01-29','597.10',JAN,'Report header 29-Jan-26; Volume Leaders / Fauji Fert / Close Price; repeated Top 10 Index Drivers', 'unadjusted_price'),
    record('FFC','2026-03-13','501.02',MAR,'Report header 13-Mar-26; Top 10 Index Drivers / Fauji FertXD / Close Price', 'unadjusted_price',ex_dividend_marker=True),
    record('KSE100','2026-01-28','188380.39',JAN,'Stock Market Summary / Index / explicitly labelled 28-Jan-26 column','total_return'),
    record('KSE100','2026-01-29','182338.12',JAN,'Stock Market Summary / Index / explicitly labelled 29-Jan-26 column','total_return'),
    record('KSE100','2026-03-13','153866.17',MAR,'Stock Market Summary / Index / explicitly labelled 13-Mar-26 column','total_return'),
    record('KSE100PR','2026-01-29','57275.40',QUOTE,'QUOTATIONS / KSE100PR / current close; PDF date/header not visually verified','price_return'),
]


def endpoint_return(rows, start, end):
    by_date = {r['trade_date']: r for r in rows if r['admitted_to_authenticated_arithmetic']}
    if start not in by_date or end not in by_date:
        return None
    a,b=Decimal(by_date[start]['value']),Decimal(by_date[end]['value'])
    if a<=0 or b<=0:
        return None
    return str((b/a-1)*100)


def compare(company, benchmark, start, end):
    # Basis is checked before availability: source authenticity cannot cure a
    # price-only vs reinvested-dividend comparison.
    if {r['return_basis'] for r in company}!={'unadjusted_price'} or {r['return_basis'] for r in benchmark}!={'price_return'}:
        return dict(status='incompatible_return_basis',company_return=None,benchmark_return=None,label=None)
    co,bm=endpoint_return(company,start,end),endpoint_return(benchmark,start,end)
    if co is None or bm is None:
        return dict(status='incomplete_authenticated_endpoints',company_return=None,benchmark_return=None,label=None)
    return dict(status='authenticated_endpoint_price_comparison_only',company_return=co,benchmark_return=bm,
                label='company_below_benchmark' if Decimal(co)<Decimal(bm) else 'company_not_below_benchmark')


def controls():
    def r(date,value,basis,ok=True): return dict(trade_date=date,value=value,return_basis=basis,admitted_to_authenticated_arithmetic=ok)
    co=[r('a','100','unadjusted_price'),r('b','99','unadjusted_price')]
    pr=[r('a','100','price_return'),r('b','101','price_return')]
    tr=[r('a','100','total_return'),r('b','101','total_return')]
    assert compare(co,tr,'a','b')['status']=='incompatible_return_basis'
    assert compare(co,pr,'a','b')['label']=='company_below_benchmark'
    assert compare(co,pr[:1],'a','b')['status']=='incomplete_authenticated_endpoints'
    assert endpoint_return([r('a','100','price_return',False),pr[1]],'a','b') is None
    assert endpoint_return([r('a','0','price_return'),pr[1]],'a','b') is None
    assert compare(co,pr,'a','b')['company_return']=='-1.00'
    return 6


def main():
    path=ROOT/'evaluation_jws/report_aligned_cohort/results.json'
    cohort=json.loads(path.read_text(encoding='utf-8'))
    ffc=next(r for r in cohort['records'] if r['symbol']=='FFC')
    dates=ffc['observed_horizon']['dates']
    wanted=sorted(set(['2026-01-28','2026-01-29']+dates))
    co=[r for r in LEADS if r['series']=='FFC']
    pr=[r for r in LEADS if r['series']=='KSE100PR']
    tr=[r for r in LEADS if r['series']=='KSE100']
    coverage={series:dict(required_dates=len(wanted),indexed_primary_lead_dates=sorted({r['trade_date'] for r in LEADS if r['series']==series}),
              authenticated_dates=[],missing_authenticated_dates=wanted) for series in ('FFC','KSE100PR','KSE100')}
    result=dict(version='1.0',review_date='2026-10-16',symbol='FFC',anchor='2026-01-29',
        required_post_dates=dates,required_baseline_dates=['2026-01-28','2026-01-29'],
        original_cohort_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),coverage=coverage,
        lead_records=LEADS,authenticated_daily_shared_intervals=0,
        post_endpoint_comparison=compare(co,pr,dates[0],dates[-1]),
        disclosure_endpoint_comparison=compare(co,pr,'2026-01-29',dates[-1]),
        total_return_substitution_control=compare(co,tr,'2026-01-29',dates[-1]),
        synthetic_controls_passed=controls(),
        retrieval_outcomes=[dict(url='https://dps.psx.com.pk/historical',outcome='HTTP200 public page; no historical values harvested after restrictive terms inspected'),
          dict(url='https://www.secp.gov.pk/data-and-statistics/trading-data/',outcome='HTTP403 Cloudflare challenge; no bypass'),
          dict(url=MAR,outcome='Direct publicly linked download HTTP403; PDF bytes unavailable; indexed table only')],
        limitations=['No source-byte hash exists: null is not a missing checksum silently invented.',
          'No original workbook or graph changed. Indexed leads are not promoted to authenticated prices.',
          'Jan29 FFC opening 662.91 is NOT a Jan28 closing price.',
          'KSE100PR previous value 59173.37 is indexed but its precise previous-date header was not visually verified, so it is not assigned to Jan28.',
          'FFC March13 XD marker warns of a dividend event; no dividend-adjusted company series established.',
          'No volume estimation baseline, trading-calendar completeness or first earnings timestamp established.'])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# PSX authentic-price acquisition ledger','','Status: acquisition incomplete; zero authenticated daily intervals. No missing value is replaced with zero, interpolation, a proxy, an opening price or a secondary-news quotation.','','## Indexed primary-document leads','','| Series | Trade date | Indexed value | Evidence |','|---|---|---:|---|']
    for r in LEADS:
        lines.append(f"| {r['series']} | {r['trade_date']} | {r['value']} | [{r['publisher']} document]({r['source_url']}) — {r['locator']} |")
    lines+=['','These are search-indexed primary-document leads, NOT downloaded/visually authenticated PDFs. The document hash is explicitly null. SECP is the regulator publisher; its report uses PSX market data. Report-header date and explicitly labelled prior-session column are kept separate from publication date.','','## Access and rights','','The public PSX historical page was reachable, but its terms prohibit automated collection/caching and redistribution without written permission. No raw PSX data are cached or distributed here. SECP direct downloads returned an HTTP403 challenge; no challenge bypass was attempted. A publicly indexed exchange quotation link is recorded as a retrieval lead only. Before packaging market data, obtain a permissible-use basis or an appropriately licensed research feed. No account, payment or message to a third party was initiated.','','## Fail-closed comparison','','FFC closes are price-only, whereas KSE100 is a total-return benchmark. The executable gate rejects this substitution regardless of numerical/source availability. KSE100PR is the appropriate price-return candidate, but matching authenticated endpoints and all daily values remain absent. Neither an underperformance conclusion nor an authenticated event-reaction result is emitted. A January29 opening price is not substituted for the January28 baseline close.','','## Reproduction and next acquisition','','Run `docs/jws_psx_authentic_prices.py`. Six synthetic controls exercise incompatible bases, missing endpoints, unverified leads, zero baselines and exact arithmetic. The required-date inventory comes from the existing FFC cohort and is frozen in JSON. Obtain permitted original quotation PDFs or a licensed historical series for every listed FFC/KSE100PR date; verify PDF header, symbol, close field, adjustment convention and source bytes before admitting values. A verified endpoint pair may support endpoint-only descriptive price returns, not daily CAR or a pre-event volume model.']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(required_dates=len(wanted),authenticated_daily_shared_intervals=0,synthetic_controls_passed=6,comparison=result['post_endpoint_comparison']),indent=2))


if __name__=='__main__': main()
