"""Versioned financial repair; never mutates historical workbooks or graphs.

Returns are compounded over identical consecutive company close-date intervals.
Event CAR uses supplied daily simple returns minus same-date benchmark returns;
missing/ambiguous intervals yield an explicitly incomplete observation, no zero.
Independent arithmetic does not authenticate upstream facts.
"""
from pathlib import Path
from collections import defaultdict, Counter
import hashlib, json, math, statistics, sys
from functools import lru_cache
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import XSD

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_market_graph as B
from docs.jws_source_lineage import read_rows

C = B.CORE
A = Namespace('https://w3id.org/ontokg-eq/financial-v2#')
AUD = Namespace('https://w3id.org/ontokg-eq/lineage-audit#')
P = Namespace('http://www.w3.org/ns/prov#')
OUT = ROOT / 'evaluation_jws/financial_v2'

@lru_cache(maxsize=None)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dt(r): return B.to_date(r.get('trade_date'))
def finite(v): return isinstance(v, (int, float)) and math.isfinite(v)
def correlation(x, y):
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2: return None
    return statistics.correlation(x, y)

def run(market):
    cfg = B.CONFIG[market]; ns = Namespace(cfg['ns'])
    inp = ROOT / 'data' / f'demo_{market}.ttl'
    g = Graph().parse(inp); g.bind('financialv2', A); g.bind('prov', P)
    sheets = {s:read_rows(cfg,s) for s in ['02_company_master','03_fundamentals','04_market_windows','05_comparators',cfg['fx_stem'],'08_provenance']}
    sources = defaultdict(list)
    for r in sheets['08_provenance']:
        if r.get('source_id') is not None: sources[str(r['source_id'])].append(r)
    records=[]; checks=[]; cells=set()
    def n(x): return ns[B.slug(x)]
    def cell(r,f):
        u=A[f"{market}_{B.slug(r['_path'].stem)}_{B.slug(r['_sheet'])}_{r['_row']}_{B.slug(f)}"]
        g.add((u,RDF.type,P.Entity)); cells.add(u)
        for pred,val in [('workbookPath',str(r['_path'].relative_to(ROOT.parent))),('workbookSHA256',digest(r['_path'])),('worksheet',r['_sheet']),('fieldName',f),('cellValue',str(r.get(f))),('excelRow',r['_row'])]: g.add((u,A[pred],Literal(val)))
        # Only source-reviewed values receive normalized monetary metadata.
        # Raw cells/workbooks remain intact; ratios do not require this scale repair.
        reviewed = market == 'psx' and str(r.get('company_id')) in {'1','2'} and int(r.get('fiscal_year') or 0) in {2024,2025}
        if reviewed and f in {'profit_after_tax_thousand_pkr','sales_thousand_pkr'}:
            scale = 1000 if str(r['company_id']) == '1' and f == 'sales_thousand_pkr' else 1000000
            url = 'https://dps.psx.com.pk/company/' + ('ENGROH' if str(r['company_id'])=='1' else 'FFC')
            g.set((u,A.normalizedValue,Literal(str(round(r[f]*scale,6)),datatype=XSD.decimal)))
            g.set((u,A.normalizedUnit,Literal('thousand PKR')))
            g.set((u,A.normalizationMultiplier,Literal(scale)))
            g.set((u,A.sourceCheckURL,Literal(url)))
            g.set((u,A.sourceCheckDate,Literal('2026-10-16',datatype=XSD.date)))
            g.set((u,A.sourceCheckStatus,Literal('numeric match after declared scale correction; exchange-hosted standardized table')))
            g.set((u,A.originalColumnUnitIncorrect,Literal(True)))
        sid=r.get('source_id'); matches=sources.get(str(sid),[])
        if sid is not None:
            g.add((u,A.sourceIdentifier,Literal(str(sid))))
            g.add((u,AUD.sourceIdentifier,Literal(str(sid))))
            if len(matches)==1:
                src=n(f'source_{sid}'); g.add((u,P.hadPrimarySource,src));g.add((src,C.hasSourceIdentifier,Literal(str(sid))))
                if matches[0].get('source_url'):g.add((src,C.hasSourceURL,Literal(str(matches[0]['source_url']))))
        return u
    def update(local,value,definition,unit,deps=(),dates=(),note='',extra=None):
        o=n(local); old=g.value(o,C.hasMetricValue)
        if (o,RDF.type,C.Observation) not in g:
            # New absent metrics are logged but not fabricated without entity/window semantics.
            records.append(dict(market=market,observation=str(o),old=None,value=value,status='not_present_in_archived_graph',definition=definition,note=note,dates=list(dates)))
            return
        g.remove((o,C.hasMetricValue,None));g.remove((o,P.wasDerivedFrom,None))
        if value is not None and finite(value):g.add((o,C.hasMetricValue,Literal(str(round(value,10)),datatype=XSD.decimal)))
        unit = 'coefficient' if unit == 'dimensionless' else unit
        g.set((o,C.hasUnit,Literal(unit)));g.set((o,A.metricDefinition,Literal(definition)))
        g.set((o,A.computationStatus,Literal('recomputed' if value is not None else 'incomplete')))
        g.set((o,A.sourceTruthVerified,Literal(False)));g.set((o,A.calculationVersion,Literal('financial-v2')))
        for d in sorted(set(dates)):g.add((o,A.decidingDate,Literal(d,datatype=XSD.date)))
        for r,f in deps:g.add((o,P.wasDerivedFrom,cell(r,f)))
        for p,v in (extra or {}).items():g.set((o,A[p],Literal(v)))
        if note:g.set((o,A.caveat,Literal(note)))
        records.append(dict(market=market,observation=str(o),old=str(old) if old is not None else None,value=value,status='recomputed' if value is not None else 'incomplete',changed=old is None or value is None or abs(float(old)-value)>2e-6,definition=definition,unit=unit,note=note,dates=sorted(set(dates)),dependency_cells=len(deps),source_register_resolved_cells=sum(len(sources.get(str(r.get('source_id')),[]))==1 for r,f in deps)))
    post=defaultdict(list);events=defaultdict(list)
    for r in sheets['04_market_windows']:(events[(r['company_id'],r['window_type'])] if B.is_event(r['window_type']) else post[r['company_id']]).append(r)
    bench=[r for r in sheets['05_comparators'] if r['comparator_type'] in cfg['benchmark_types']]
    sectors=defaultdict(list)
    for r in sheets['05_comparators']:
        if r['comparator_type'] not in cfg['benchmark_types']:sectors[r.get('sector_name_if_applicable')].append(r)
    def unique(rows,field):
        groups=defaultdict(list)
        for r in rows:
            if finite(r.get(field)):groups[dt(r)].append(r)
        # Duplicate dates are acceptable only for identical numeric values.
        return {d:rs[0] for d,rs in groups.items() if len({r[field] for r in rs})==1}
    # Audit supplied daily returns against consecutive close/value arithmetic in each actual series.
    series=defaultdict(list)
    for r in sheets['04_market_windows']:series[('company',r['company_id'],r['window_label'],r['window_type'])].append(r)
    for r in sheets['05_comparators']:series[('comparator',r['comparator_name'])].append(r)
    for key,rs in series.items():
        field='close' if key[0]=='company' else 'value';by=unique(rs,field);dates=sorted(by)
        for prev,cur in zip(dates,dates[1:]):
            r=by[cur]; supplied=r.get('daily_return')
            if finite(supplied) and by[prev][field]!=0:
                computed=r[field]/by[prev][field]-1
                checks.append(dict(series=str(key),date=cur,supplied=supplied,recomputed=computed,absolute_error=abs(supplied-computed),match=abs(supplied-computed)<=2e-6,previous_date=prev))
    fx=unique(sheets[cfg['fx_stem']],cfg['fx_rate_col']);fxdates=sorted(fx);fxret={}
    for d0,d1 in zip(fxdates,fxdates[1:]):
        if fx[d0][cfg['fx_rate_col']]!=0:fxret[(d0,d1)]=fx[d1][cfg['fx_rate_col']]/fx[d0][cfg['fx_rate_col']]-1
    for co in sheets['02_company_master']:
        cid=co['company_id'];rows=post[cid];by=unique(rows,'close');dates=sorted(by);intervals=list(zip(dates,dates[1:]))
        # Reconstruct all three returns on the exact same observed close-date intervals.
        # No missing-date intersection is silently substituted.
        def ret(local,rs,field):
            bm=unique(rs,field);valid=len(dates)>=2 and all(d in bm for d in dates) and all(bm[d0][field]>0 for d0,d1 in intervals)
            vals=[bm[d1][field]/bm[d0][field]-1 for d0,d1 in intervals] if valid else []
            val=(math.prod(1+x for x in vals)-1)*100 if valid else None
            deps=[(bm[d],field) for d in dates] if valid else []
            update(local,val,'100*(product(1+r_t)-1); r_t reconstructed from consecutive observed close/value endpoints; exact company dates','percent',deps,dates,'Price return, not dividend-adjusted total return. Dates are workbook observations; trading-calendar completeness is not certified.' if valid else 'Missing/ambiguous comparator endpoint or insufficient company dates; metric omitted.')
        ret(f'derived_post_return_{cid}',rows,'close')
        ret(f'derived_bench_return_{cid}',bench,'value')
        ret(f'derived_sector_return_{cid}',sectors[co['sector']],'value')
        # Correlation pairs only identical date intervals, never a gap-spanning FX return against a one-day equity return.
        common=[i for i in intervals if i in fxret and by[i[0]]['close']>0]
        xs=[fxret[i] for i in common];ys=[by[d1]['close']/by[d0]['close']-1 for d0,d1 in common]
        deps=[(by[d], 'close') for i in common for d in i]+[(fx[d],cfg['fx_rate_col']) for i in common for d in i]
        update(f'derived_fx_corr_company_{cid}',correlation(xs,ys),'Pearson correlation of price and FX simple returns on identical date intervals; >=3 pairs','dimensionless',deps,[i[1] for i in common],extra={'pairedIntervals':len(common)})
        fs=sorted([r for r in sheets['03_fundamentals'] if r['company_id']==cid],key=lambda r:int(r['fiscal_year']),reverse=True)
        latest=next((r for r in fs if finite(r.get('yoy_profit_growth_pct'))),None)
        if latest:
            profit=next((f for f in latest if f.startswith('profit_after_tax') and finite(latest[f])),None)
            prior=next((r for r in fs if int(r['fiscal_year'])==int(latest['fiscal_year'])-1 and r['period_type']==latest['period_type'] and profit and finite(r.get(profit)) and r[profit]!=0),None)
            supplied=latest['yoy_profit_growth_pct']*cfg['growth_scale']
            val=100*(latest[profit]-prior[profit])/abs(prior[profit]) if prior else supplied
            deps=[(latest,profit),(prior,profit)] if prior else [(latest,'yoy_profit_growth_pct')]
            update(f'derived_fund_growth_{cid}',val,'100*(PAT_current-PAT_previous)/abs(PAT_previous)' if prior else 'Supplied workbook YoY profit growth normalized to percent; independent PAT inputs absent','percent',deps,note='Profit scale/source accounting scope remain unverified; EPS is not treated as profit.' if prior else 'Supplied metric only; EPS does not independently verify profit growth.',extra={'independentWorkbookProfitRecomputation':bool(prior),'suppliedGrowthPercent':supplied,'suppliedDifference':val-supplied,'periodEndDate':B.to_date(latest.get('period_end_date')) or 'absent','reportDateStatus':'provided' if latest.get('report_date') else 'absent'})
        # Workbook anchors are retained without inferring annual report publication dates.
        for r in rows:
            wn=n(f"window_{cid}_{B.slug(r['window_label'])}_{B.slug(r['window_type'])}")
            if r.get('anchor_date'):
                g.add((wn,A.anchorDate,Literal(B.to_date(r['anchor_date']),datatype=XSD.date)))
                g.add((wn,C.hasAnchorDate,Literal(B.to_date(r['anchor_date']),datatype=XSD.date)))
            if r.get('anchor_type'):g.add((wn,A.anchorType,Literal(str(r['anchor_type']))))
    # Event CAR uses same-date supplied daily returns, explicitly market-adjusted (not market-model estimated).
    bdr=unique(bench,'daily_return')
    for (cid,wt),rows in events.items():
        dr=unique(rows,'daily_return'); dates=sorted({dt(r) for r in rows});valid=bool(dates) and all(d in dr and d in bdr for d in dates)
        val=100*sum(dr[d]['daily_return']-bdr[d]['daily_return'] for d in dates) if valid else None
        deps=[(r,'daily_return') for d in dates for r in (dr[d],bdr[d])] if valid else []
        update(f'derived_event_ar_{cid}_{B.slug(wt)}',val,'Market-adjusted CAR = 100*sum(company daily simple return - benchmark daily simple return) on every observed event date','percent',deps,dates,'Daily returns are supplied inputs; full first-date arithmetic and trading-calendar coverage remain unverified. Not a fitted market-model CAR.' if valid else 'Missing/ambiguous company or benchmark return on at least one event date; no zero imputation.')
        ev=[r for r in rows if finite(r.get('volume')) and r['volume']>=0];base=[r for r in post[cid] if finite(r.get('volume')) and r['volume']>=0]
        validvol=len(ev)==len(rows) and len(base)==len(post[cid]) and bool(base) and statistics.mean(r['volume'] for r in base)>0
        ratio=statistics.mean(r['volume'] for r in ev)/statistics.mean(r['volume'] for r in base) if validvol else None
        update(f'derived_event_vol_{cid}_{B.slug(wt)}',ratio,'Mean observed event volume / mean company post-report-window volume; zeros included','ratio',[(r,'volume') for r in ev+base] if validvol else [],[dt(r) for r in rows], 'Descriptive ratio; baseline is post-report window, not an independent pre-event estimation period.',extra={'baselineDates':json.dumps(sorted({dt(r) for r in base})),'baselineOverlapsEvent':bool({dt(r) for r in base}&set(dates))})
        for r in rows:
            wn=n(f"window_{cid}_{B.slug(r['window_label'])}_{B.slug(wt)}")
            if r.get('anchor_date'):
                g.add((wn,A.anchorDate,Literal(B.to_date(r['anchor_date']),datatype=XSD.date)))
                g.add((wn,C.hasAnchorDate,Literal(B.to_date(r['anchor_date']),datatype=XSD.date)))
    # FX aggregate re-evaluation with independent statistics arithmetic.
    bm=unique(bench,'value');bd=sorted(bm);pairs=[(d0,d1) for d0,d1 in zip(bd,bd[1:]) if (d0,d1) in fxret and bm[d0]['value']>0]
    update('derived_fx_corr_bench',correlation([fxret[i] for i in pairs],[bm[d1]['value']/bm[d0]['value']-1 for d0,d1 in pairs]),'Pearson on identical benchmark and FX intervals; >=3 pairs','dimensionless',[(r,f) for i in pairs for d in i for r,f in [(bm[d],'value'),(fx[d],cfg['fx_rate_col'])]],[i[1] for i in pairs])
    if len(fxdates)>=2:
        first,last=fxdates[0],fxdates[-1];field=cfg['fx_rate_col']
        update('derived_fx_change',(fx[last][field]/fx[first][field]-1)*100 if fx[first][field]!=0 else None,'100*(last FX rate/first FX rate-1)','percent',[(fx[first],field),(fx[last],field)],fxdates)
    # Repair raw event mislabeling: supplied simple return is not an abnormal return.
    for rows in events.values():
        for r in rows:
            o=n(f"mkt_{r['market_obs_id']}");g.set((o,C.hasMetricName,Literal('daily simple return %')));g.set((o,C.hasUnit,Literal('percent')))
            if not finite(r.get('daily_return')):g.remove((o,C.hasMetricValue,None));g.set((o,A.computationStatus,Literal('incomplete')))
    for o in g.subjects(C.hasMetricName,Literal('close price')):g.set((o,C.hasUnit,Literal(cfg['local_currency'])))
    for o in g.subjects(C.hasMetricName,Literal('EPS')):g.set((o,C.hasUnit,Literal(cfg['local_currency']+'/share')))
    # Record advertised financial currency context; does not validate workbook magnitudes.
    for o in list(g.subjects(RDF.type,C.Observation)):
        g.set((o,A.marketCurrencyContext,Literal(cfg['local_currency'])))
        g.set((o,C.hasCurrencyContext,Literal(cfg['local_currency'])))
    for r in sheets['03_fundamentals']:
        # Find the actual period already attached to the corresponding raw observation.
        o=n(f"fund_{r['period_id']}")
        for period in g.objects(o,C.observedInPeriod):
            if r.get('report_date'):g.set((period,C.hasReportDate,Literal(B.to_date(r['report_date']),datatype=XSD.date)))
        if market=='psx' and str(r.get('company_id')) in {'1','2'}:
            for field in ('profit_after_tax_thousand_pkr','sales_thousand_pkr'):
                if finite(r.get(field)):cell(r,field)
    target=OUT/f'demo_{market}_financial_v2.ttl';g.serialize(target,format='turtle')
    assert len(Graph().parse(target))==len(g)
    return dict(market=market,input_graph_sha256=digest(inp),output_graph_sha256=digest(target),output_graph=str(target),records=records,arithmetic_checks=checks,summary={'recomputed':sum(r['status']=='recomputed' for r in records),'incomplete':sum(r['status']=='incomplete' for r in records),'changed':sum(r.get('changed',False) for r in records),'arithmetic_checks':len(checks),'arithmetic_mismatches':sum(not r['match'] for r in checks),'source_cells':len(cells)},workbook_sha256={str(r['_path'].relative_to(ROOT.parent)):digest(r['_path']) for rows in sheets.values() for r in rows})

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    results=[run(m) for m in B.CONFIG]
    verified=0;normalized=0
    for r in results:
        inp=ROOT/'data'/f"demo_{r['market']}.ttl"
        assert hashlib.sha256(inp.read_bytes()).hexdigest()==r['input_graph_sha256'], 'Historical input changed'
        graph=Graph().parse(r['output_graph'])
        normalized+=len(list(graph.subjects(A.normalizedUnit,None)))
        for rec in r['records']:
            if rec['status']=='not_present_in_archived_graph':continue
            o=URIRef(rec['observation']);value=graph.value(o,C.hasMetricValue)
            assert (value is None)==(rec['status']=='incomplete')
            assert str(graph.value(o,C.hasUnit)) in {'percent','ratio','coefficient'}
            if value is not None:assert abs(float(value)-rec['value'])<=1e-8
            verified+=1
    assert normalized==8, 'Eight source-reviewed monetary cells must retain normalized units'
    (OUT/'financial_v2.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    lines=['# Financial v2: separate corrected graphs','', 'Independent arithmetic over existing workbook inputs; no new independent dataset and no source-truth certification. Historical graphs and inputs remain unchanged.','', '| Market | Recomputed | Incomplete | Changed values | Daily-return checks | Mismatches |','|---|---:|---:|---:|---:|---:|']
    for r in results:
        s=r['summary'];lines.append(f"| {r['market']} | {s['recomputed']} | {s['incomplete']} | {s['changed']} | {s['arithmetic_checks']} | {s['arithmetic_mismatches']} |")
    lines += ['', '## Definitions and limits','', 'Company, sector and benchmark returns use identical company close-date endpoints and compound consecutive price changes. This deliberately excludes any first-row supplied return whose prior close is absent. Missing comparator endpoints cause incomplete metrics instead of silently intersecting dates. Observed-date matching is not trading-calendar completeness. Market-adjusted event CAR subtracts the supplied benchmark return on every event date; missing inputs cause incomplete metrics. These are price returns, not verified adjusted total returns. FX correlations use identical date intervals. Volume ratios include legitimate zeros and explicitly retain the post-report baseline dates and overlap flag. This baseline is descriptive and can overlap the event; no significance claim is justified.', '', 'Growth is independently recomputed only where same-field current and prior-year PAT inputs exist. Otherwise it remains clearly marked as a supplied workbook metric. Absolute prior PAT is the declared loss-to-profit convention. Accounting scope and uniform scaling require independent source review. Graphs have explicit unit declarations, computation definitions, cell dependencies, actual workbook window anchors and source-register identity paths. These declarations make assumptions inspectable, not externally verified. Market currency context does not mean percentage returns are currency-valued. Missing report dates are never inferred from fiscal year-end.', '', '## Official-source spot check', '', 'See source_spot_checks.md for bounded original-document verification. PSX ENGROH supplied PAT magnitudes conflict with the column unit: no silent scaling correction was applied. Workbook record labels such as verified are not treated as independent verification.']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps([{ 'market':r['market'],**r['summary']} for r in results],indent=2))
    print(f'PASS: {verified} metric values/statuses/units; {normalized} reviewed monetary normalizations; historical input hashes unchanged.')

if __name__=='__main__':main()
