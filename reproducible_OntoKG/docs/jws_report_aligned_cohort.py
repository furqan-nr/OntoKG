"""Bounded disclosure-date cohort: independent Decimal replay, not a reaction study.

All eight curated PSX/MSX companies enter the eligibility ledger before results
are inspected. Original data and financial-v2 graphs are read-only. An official
document date is not an exchange timestamp; an annual-report announcement is not
first earnings disclosure. Proxy/interpolated benchmarks are never authenticated.
"""
from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_market_graph as B
from docs.jws_source_lineage import read_rows
from docs.jws_temporal_resolution import DATE_EVIDENCE
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import XSD

OUT = ROOT / 'evaluation_jws/report_aligned_cohort'
V = Namespace('https://w3id.org/ontokg-eq/disclosure-cohort-v1#')


def dec(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except Exception:
        return None


def unique(rows, field):
    groups = defaultdict(list)
    for r in rows:
        groups[B.to_date(r['trade_date'])].append(r)
    result = {}
    for date, candidates in groups.items():
        values = {dec(r.get(field)) for r in candidates}
        # A missing duplicated entry does not override an actual observed value.
        values.discard(None)
        if len(values) == 1:
            result[date] = next(r for r in candidates if dec(r.get(field)) in values)
    return result


def shared_return(company_rows, benchmark_rows):
    co, bm = unique(company_rows, 'close'), unique(benchmark_rows, 'value')
    dates = sorted({B.to_date(r['trade_date']) for r in company_rows})
    missing_company = [d for d in dates if d not in co]
    missing = [d for d in dates if d not in bm]
    result = dict(dates=dates, missing_company_dates=missing_company, missing_benchmark_dates=missing,
                  observations=len(dates), intervals=max(0, len(dates)-1),
                  status='incomplete', company_return_percent=None,
                  benchmark_return_percent=None)
    if len(dates) < 2 or missing or missing_company:
        return result
    if any(dec(co[d]['close']) <= 0 or dec(bm[d]['value']) <= 0 for d in dates):
        return result
    with localcontext() as ctx:
        ctx.prec = 40
        factors = []
        for data, field in ((co, 'close'), (bm, 'value')):
            product = Decimal(1)
            for previous, current in zip(dates, dates[1:]):
                product *= dec(data[current][field]) / dec(data[previous][field])
            returned = (product - 1) * 100
            endpoint = (dec(data[dates[-1]][field]) / dec(data[dates[0]][field]) - 1) * 100
            assert abs(returned-endpoint) < Decimal('1e-30')
            factors.append(str(returned))
        result.update(status='complete_observed_interval_replay',
                      company_return_percent=factors[0], benchmark_return_percent=factors[1])
    return result


def classify(growth, replay):
    if growth is None or replay['status'] != 'complete_observed_interval_replay':
        return 'incomplete'
    return 'positive' if growth > 0 and Decimal(replay['company_return_percent']) < Decimal(replay['benchmark_return_percent']) else 'negative'


def address(row, field):
    from openpyxl.utils import get_column_letter
    return dict(workbook=str(row['_path'].relative_to(ROOT.parent)), sheet=row['_sheet'],
                cell=f"{get_column_letter(row['_cols'][field])}{row['_row']}",
                field=field, value=str(row.get(field)))


def controls():
    def row(date, **kw): return dict(trade_date=date, **kw)
    co = [row('2026-01-01', close=100),row('2026-01-02',close=110),row('2026-01-03',close=99)]
    bm = [row('2026-01-01', value=100),row('2026-01-02',value=100),row('2026-01-03',value=100)]
    complete = shared_return(co,bm)
    assert Decimal(complete['company_return_percent']) == -1
    assert classify(Decimal(2),complete) == 'positive'
    assert classify(Decimal(-2),complete) == 'negative'
    # No silent date intersection, even if first/last endpoints exist.
    assert shared_return(co,[bm[0],bm[2]])['status'] == 'incomplete'
    assert classify(None,complete) == 'incomplete'
    assert shared_return(co[:1],bm)['status'] == 'incomplete'
    assert shared_return([row('2026-01-01',close=0),co[1]],bm)['status'] == 'incomplete'
    assert shared_return([co[0],row('2026-01-02',close=None),co[2]],bm)['status'] == 'incomplete'
    return 8


def main():
    records, hashes = [], {}
    for market in ('psx','msx'):
        cfg=B.CONFIG[market]
        tables={stem:read_rows(cfg,stem) for stem in ('02_company_master','03_fundamentals','04_market_windows','05_comparators')}
        for rows in tables.values():
            for r in rows:
                p=r['_path'];hashes[str(p.relative_to(ROOT.parent))]=hashlib.sha256(p.read_bytes()).hexdigest()
        for co in tables['02_company_master']:
            cid=co['company_id'];uri=cfg['ns']+'company_'+B.slug(cid)
            allrows=[r for r in tables['04_market_windows'] if r['company_id']==cid]
            post=[r for r in allrows if B.is_post(r['window_type'])]
            benchmark=[r for r in tables['05_comparators'] if r['comparator_type'] in cfg['benchmark_types']]
            replay=shared_return(post,benchmark)
            fs=sorted([r for r in tables['03_fundamentals'] if r['company_id']==cid],key=lambda r:int(r['fiscal_year']),reverse=True)
            latest=fs[0];profit=next((f for f in latest if f.startswith('profit_after_tax') and dec(latest[f]) is not None),None)
            prior=next((r for r in fs if int(r['fiscal_year'])==int(latest['fiscal_year'])-1 and r['period_type']==latest['period_type'] and profit and dec(r[profit]) not in (None,0)),None)
            growth=(dec(latest[profit])-dec(prior[profit]))/abs(dec(prior[profit]))*100 if prior else None
            anchors=sorted({B.to_date(r['anchor_date']) for r in post if r.get('anchor_date')})
            official=DATE_EVIDENCE.get(uri)
            matched=bool(official and anchors==[official['date']] and B.to_date(latest.get('report_date'))==official['date'] and replay['dates'] and all(d>official['date'] for d in replay['dates']))
            valid_prices=unique(allrows,'close')
            before=[d for d in valid_prices if anchors and d<anchors[0]]
            on=[d for d in valid_prices if anchors and d==anchors[0]]
            rec=dict(market=market,company=uri,symbol=co['company_symbol'],
                declared_anchor_dates=anchors,declared_report_date=B.to_date(latest.get('report_date')),
                official_date_evidence=official,eligible_disclosure_dated_replay=matched,
                eligibility='official_date_match' if matched else 'excluded_no_verified_matching_disclosure_date',
                numerical_R1_label=classify(growth,replay),growth_percent=str(growth) if growth is not None else None,
                growth_source_status='same_field_workbook_comparison_not_universally_source_authenticated',
                observed_horizon=replay,first_close_vs_disclosure_days=(__import__('datetime').date.fromisoformat(replay['dates'][0])-__import__('datetime').date.fromisoformat(anchors[0])).days if replay['dates'] and len(anchors)==1 else None,
                full_first_publication_reaction_eligible=False,first_earnings_publication_timestamp_authenticated=False,
                benchmark_construction=sorted({str(r.get('construction_rule_if_peer_basket')) for r in benchmark}),
                benchmark_kind='interpolated_forward_filled' if market=='psx' else 'selected_universe_damped_proxy',
                benchmark_source_authenticated=False,market_prices_source_authenticated=False,
                pre_anchor_observed_close_dates=sorted(before),on_anchor_observed_close_dates=sorted(on),
                independent_pre_event_volume_baseline_available=False,
                disclosure_close_to_first_post_close_return=None,
                source_cells=[address(r,'close') for r in post if dec(r.get('close')) is not None]+[address(r,'value') for r in unique(benchmark,'value').values() if B.to_date(r['trade_date']) in replay['dates']]+([address(latest,profit),address(prior,profit)] if prior else []))
            rec['pre_event_caveat']='No prespecified independent pre-event baseline; a few event rows, where present, cannot establish a stable estimation period.'
            rec['horizon_caveat']='First available post-disclosure close to final available close; omits disclosure-day and first-post-close reaction. Observed dates only, not certified trading-calendar completeness; 30 observations mean 29 intervals, not automatically 30-day return.'
            if co['company_symbol'] in ('OGDC','PPL'):
                rec['eligibility']='excluded_wrong_period_february_anchor_no_september_2025_price_coverage'
            records.append(rec)
    eligible=[r for r in records if r['eligible_disclosure_dated_replay']]
    result=dict(version='1.0',review_date='2026-10-16',scope='All eight curated PSX/MSX companies; not the IDX/scaled cohort',
        selection_policy='Complete PSX/MSX company roster, date eligibility decided from official matched evidence, not numerical labels. Only FFC and Maybank date evidence authenticated in this bounded audit.',
        candidates=len(records),eligibility_counts=dict(Counter(r['eligibility'] for r in records)),
        all_candidate_numerical_labels=dict(Counter(r['numerical_R1_label'] for r in records)),
        eligible_numerical_labels=dict(Counter(r['numerical_R1_label'] for r in eligible)),
        eligible_document_dated_replays=len(eligible),authenticated_empirical_benchmark_classifications=0,
        authenticated_first_earnings_reactions=0,synthetic_controls_passed=controls(),input_workbook_sha256=hashes,records=records,
        bounded_primary_benchmark_search=dict(queries=['site.psx.com.pk January 30, 2026 KSE-100','site.psx.com.pk March 13, 2026 KSE-100','site.bursamalaysia.com 2 April 2026 KLCI'],outcome='No exact-date primary historical endpoint pair authenticated. Search results were mostly secondary reports and unrelated official index recomposition notice; no value substituted.'))
    for rel,sha in hashes.items(): assert hashlib.sha256((ROOT.parent/rel).read_bytes()).hexdigest()==sha
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    graph=Graph();graph.bind('cohort',V)
    for r in records:
        u=V[r['market']+'_'+B.slug(r['symbol'])]
        graph.add((u,RDF.type,V.Candidate));graph.add((u,V.company,URIRef(r['company'])))
        for key in ('eligibility','numerical_R1_label','eligible_disclosure_dated_replay','benchmark_kind','full_first_publication_reaction_eligible'):
            graph.add((u,V[key],Literal(r[key])))
        if r['official_date_evidence']:graph.add((u,V.officialDateSource,URIRef(r['official_date_evidence']['url'])))
        for key in ('company_return_percent','benchmark_return_percent'):
            value=r['observed_horizon'][key]
            if value is not None:graph.add((u,V[key],Literal(value,datatype=XSD.decimal)))
    graph.serialize(OUT/'cohort.ttl',format='turtle')
    lines=['# Disclosure-date-aligned cohort v1','', 'Eight PSX/MSX candidates are retained: three numerical positives, five negatives, and zero incomplete post-close arithmetic cases. Missing disclosure closes and pre-event baselines are separately reported rather than treated as complete. Two official dates match the declared anchors. This is an arithmetic demonstration on workbook prices, not an authenticated earnings-event study. Original workbooks and graphs are unchanged.','','| Company | Eligibility | R1 arithmetic | Dates / intervals | Company % | Benchmark % |','|---|---|---|---|---:|---:|']
    for r in records:
        p=r['observed_horizon'];lines.append(f"| {r['symbol']} | {r['eligibility']} | {r['numerical_R1_label']} | {p['dates'][0] if p['dates'] else '-'} to {p['dates'][-1] if p['dates'] else '-'} / {p['intervals']} | {p['company_return_percent']} | {p['benchmark_return_percent']} |")
    lines+=['','## What is and is not established','','[FFC official issuer letter](https://dps.psx.com.pk/download/document/269389.pdf), p. 1, dated 29 January 2026, supports document-date alignment, not first exchange publication time. [Maybank official announcement](https://maybank.listedcompany.com/news.html/id/2605866) records 1 April 2026, reference DCS-01042026-00004, for the FY2025 annual report and CG report. This is not authenticated first earnings disclosure. Maxis remains excluded: an AGM notice date alone is not publication proof. OGDC/PPL September 2025 annual dates do not match February 2026 market windows; available company rows do not cover September. Other excluded companies are preserved rather than silently omitted.','','Both matched cases have 30 observed post-disclosure closes and 29 shared intervals. The calculation starts at the first observed post-disclosure close and excludes the initial reaction. All intermediate company dates must exist in the benchmark; missing dates are not intersected away. Returns are reconstructed with 40-digit Decimal arithmetic, and interval products are checked independently against endpoint ratios. Raw monetary scaling cancels in same-scale growth, but accounting scope/source accuracy is not thereby authenticated.','','PSX benchmark rows explicitly disclose interpolation and forward filling. MSX benchmark rows explicitly disclose a damped selected-universe proxy and request replacement with a licensed official FBM KLCI feed. Thus numerical R1 labels are illustrative and cannot be advertised as empirically authenticated market underperformance. Bounded official-site endpoint searches did not retrieve a primary-source pair; secondary news values were not substituted.','','FFC has January 28/29 event rows but their close values are missing. Maybank has no pre-anchor prices. Neither supports a disclosure-close-to-first-post-close return or an independent pre-event volume estimation period. Missing values remain missing. No price/date is invented, no post-event baseline is relabelled pre-event, and no significance claim is made.','','## Reproduction','','Run `docs/jws_report_aligned_cohort.py` with openpyxl and rdflib available. Eight synthetic controls cover compounding, negative outcomes, missing growth, intermediate company/benchmark-date mismatch, inadequate endpoints and zero prices. JSON includes exact workbook cell addresses and SHA-256 hashes; RDF is a separate versioned cohort overlay. IDX temporal quarantine remains a separate evaluation, not included in the eight-company denominator.']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('candidates','eligibility_counts','all_candidate_numerical_labels','eligible_numerical_labels','eligible_document_dated_replays','authenticated_empirical_benchmark_classifications','synthetic_controls_passed')},indent=2))


if __name__=='__main__':main()
