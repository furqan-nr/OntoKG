"""Independent unit/currency/date declaration checks for expanded positive cases.

These checks test metadata consistency, not source authenticity or source truth.
Historical graphs, contracts and expanded reports are never changed.
"""
from pathlib import Path
from collections import Counter
from datetime import date
import json, hashlib
from rdflib import Graph, Namespace, URIRef, Literal

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evaluation_jws/metadata_v2'
C=Namespace('https://w3id.org/ontokg-eq#')
UNITS={'growth':'percent','company':'percent','benchmark':'percent','sector':'percent','correlation':'coefficient','event_return':'percent','volume':'ratio'}

def singleton(g,o,p):
    values=set(map(str,g.objects(o,p)))
    return next(iter(values)) if len(values)==1 else None

def declaration(values,expected=None):
    if not values or any(v is None for v in values):return 'absent_or_ambiguous'
    return 'verified_as_declared' if (all(v==expected for v in values) if expected is not None else len(set(values))==1) else 'mismatch'

def date_check(values,predicate):
    if any(v is None for v in values):return 'absent_or_ambiguous'
    try: ds=[date.fromisoformat(v) for v in values]
    except ValueError:return 'mismatch'
    return 'verified_as_declared' if predicate(*ds) else 'mismatch'

def check(g,case,index):
    rid=case['rule'];dataset=case['dataset'];checks=[]
    def add(name,status,**details):checks.append(dict(check=name,status=status,**details))
    # R4 is OR: only the passing branch is required; all passing alternative
    # witnesses are checked separately and one metadata-complete branch suffices.
    selected={}
    for role,obs in case['observations'].items():
        stem=role.rstrip('0123456789')
        if rid!='R4' or stem in case.get('passing_branches',[]):selected[role]=(stem,URIRef(obs))
    branch_checks={}
    for role,(stem,obs) in selected.items():
        declared=singleton(g,obs,C.hasUnit);status=declaration([declared],UNITS[stem])
        add('unit:'+role,status,observation=str(obs),expected=UNITS[stem],declared=declared)
        branch_checks[role]=[status]
    if rid in {'R1','R3'}:
        vals=[singleton(g,o,C.hasCurrencyContext) for role,(stem,o) in selected.items() if stem in {'company','benchmark','sector'}]
        add('return_currency_context',declaration(vals),declared=vals,meaning='Common local price-currency context; return units remain percent')
    if rid=='R1':
        grow=URIRef(case['observations']['growth']);company=URIRef(case['observations']['company'])
        period=singleton(g,grow,C.observedInPeriod);window=singleton(g,company,C.observedOverWindow)
        report=singleton(g,URIRef(period),C.hasReportDate) if period else None
        anchor=singleton(g,URIRef(window),C.hasAnchorDate) if window else None
        start=singleton(g,URIRef(window),C.hasStartDate) if window else None
        end=singleton(g,URIRef(period),C.hasEndDate) if period else None
        add('report_date_equals_window_anchor',date_check([report,anchor],lambda r,a:r==a),report_date=report,anchor_date=anchor,period=period,window=window)
        add('post_report_window_starts_on_or_after_anchor',date_check([anchor,start],lambda a,s:s>=a),anchor_date=anchor,start_date=start,policy='Inclusive anchor date allowed; this is not proof of publication timing')
        # Period endpoints use archived core hasPeriodEndDate, when available.
        end=end or (singleton(g,URIRef(period),C.hasPeriodEndDate) if period else None)
        add('fiscal_period_ends_before_or_on_report',date_check([end,report],lambda e,r:e<=r),period_end=end,report_date=report)
    if rid=='R4':
        window=URIRef(case['window']);anchor=singleton(g,window,C.hasAnchorDate)
        start=singleton(g,window,C.hasStartDate);end=singleton(g,window,C.hasEndDate)
        status=date_check([start,anchor,end],lambda s,a,e:s<=a<=e)
        add('event_anchor_inside_window',status,start=start,anchor=anchor,end=end)
        finding=URIRef(f'https://w3id.org/ontokg-eq/expanded/{dataset}/{index}')
        actual=singleton(g,finding,C.observedInEventWindow)
        add('finding_explicit_event_window',declaration([actual],str(window)),finding=str(finding),declared=actual,expected=str(window))
    statuses=[x['status'] for x in checks]
    all_declared='mismatch' if 'mismatch' in statuses else 'absent_or_ambiguous' if 'absent_or_ambiguous' in statuses else 'verified_as_declared'
    if rid=='R4':
        # Any passing OR branch with a correct unit is a valid metadata witness.
        # Preserve stricter all-branch diagnostic separately.
        unit_states=[v[0] for v in branch_checks.values()]
        branch_state='verified_as_declared' if 'verified_as_declared' in unit_states else 'absent_or_ambiguous' if 'absent_or_ambiguous' in unit_states else 'mismatch'
        statuses=[c['status'] for c in checks if not c['check'].startswith('unit:')]+[branch_state]
    overall='mismatch' if 'mismatch' in statuses else 'absent_or_ambiguous' if 'absent_or_ambiguous' in statuses else 'verified_as_declared'
    return dict(dataset=dataset,case_index=index,rule=rid,company=case['company'],metadata_status=overall,all_passing_branch_declarations_status=all_declared,checks=checks,source_date_authenticity='not_checked',interpretation='Consistency of graph declarations only')

def mutations():
    """Small explicitly synthetic controls, separated from actual cohorts."""
    g=Graph();co,bm,gr,period,window=map(URIRef,['urn:test:co','urn:test:bm','urn:test:growth','urn:test:period','urn:test:window'])
    for obs,unit in [(co,'percent'),(bm,'percent'),(gr,'percent')]:g.add((obs,C.hasUnit,Literal(unit)))
    for obs in [co,bm]:g.add((obs,C.hasCurrencyContext,Literal('PKR')))
    g.add((co,C.observedOverWindow,window));g.add((gr,C.observedInPeriod,period))
    g.add((period,C.hasReportDate,Literal('2026-01-10')));g.add((period,C.hasEndDate,Literal('2025-12-31')))
    g.add((window,C.hasAnchorDate,Literal('2026-01-10')));g.add((window,C.hasStartDate,Literal('2026-01-11')))
    case=dict(dataset='synthetic_metadata',rule='R1',company='urn:test:entity',observations={'growth':str(gr),'company':str(co),'benchmark':str(bm)},window=str(window))
    results=[dict(name='valid_R1_metadata',detected=check(g,case,0)['metadata_status']=='verified_as_declared')]
    for name,o,p,bad in [('wrong_unit',co,C.hasUnit,'ratio'),('wrong_currency',bm,C.hasCurrencyContext,'IDR'),('wrong_report_anchor',window,C.hasAnchorDate,'2026-02-01')]:
        old=list(g.objects(o,p));g.set((o,p,Literal(bad)));r=check(g,case,0)
        results.append(dict(name=name,detected=r['metadata_status']=='mismatch',checks=r['checks']))
        g.remove((o,p,None))
        for v in old:g.add((o,p,v))
    g.remove((period,C.hasReportDate,None));r=check(g,case,0)
    results.append(dict(name='absent_report_date_is_unknown',detected=r['metadata_status']=='absent_or_ambiguous'))
    assert all(r['detected'] for r in results)
    return results

def main():
    source=ROOT/'evaluation_jws/expanded_evaluation/results.json'
    report=json.loads(source.read_text(encoding='utf-8'));OUT.mkdir(parents=True,exist_ok=True)
    records=[];summaries=[]
    for dataset in report['datasets']:
        path=ROOT/'evaluation_jws/expanded_evaluation'/f"{dataset['dataset']}.experiment.ttl"
        graph=Graph().parse(path)
        rows=[check(graph,case,i) for i,case in enumerate(dataset['cases']) if case['label']=='positive']
        records+=rows;counts=Counter(r['metadata_status'] for r in rows)
        summaries.append(dict(dataset=dataset['dataset'],positive_cases=len(rows),status_counts=dict(counts),checks=dict(Counter(c['status'] for r in rows for c in r['checks'])),by_rule={rid:dict(Counter(r['metadata_status'] for r in rows if r['rule']==rid)) for rid in ['R1','R2','R3','R4']},fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result=dict(scope='Actual positive oracle cases; metadata consistency, not source authenticity. Corrected and archived cohorts are paired, overlapping datasets.',expanded_results_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),summaries=summaries,records=records,synthetic_controls=mutations())
    (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# Independent metadata consistency checks','',result['scope'],'','| Cohort | Positive cases | All applicable metadata consistent | Absent/ambiguous | Mismatch |','|---|---:|---:|---:|---:|']
    for s in summaries:
        c=s['status_counts'];lines.append(f"| {s['dataset']} | {s['positive_cases']} | {c.get('verified_as_declared',0)} | {c.get('absent_or_ambiguous',0)} | {c.get('mismatch',0)} |")
    lines+=['','## Actual temporal gaps','', 'Corrected curated IDX contains a positive R1 case for TOWR whose growth-period report date is 2026-03-18 while its return window is anchored at 2026-03-25. This is a numerical positive with an unresolved report-to-window linkage. The corrected scaled cohort contains 20 positive R1 cases whose recorded report dates differ from the recent-analysis window anchor. These remain numerical positives, but do not satisfy the strict report-anchored metadata policy. They must not be counted as validated report-event findings. No dates are silently rewritten to force agreement.','', 'Corrected curated cohorts have 16 numerical positives, 15 of which satisfy all applicable declared-metadata checks. The corrected scaled cohort has 42 numerical positives, 22 of which satisfy those checks; the other 20 are R1 anchor mismatches. These cohorts overlap and their counts are not an independent sample-size total.']
    lines+=['','Unit labels must equal the role contract (percent, ratio, coefficient). Return comparator currency contexts must agree. R1 requires actual period report date equal to the company window anchor, period end no later than report, and window start on/after anchor. R4 requires the observed event anchor within window endpoints and an explicit finding-to-window link matching the fixture witness. Missing or ambiguous values are unknown, never a pass. R4 checks only passing branch units; an unused nonpassing branch cannot invalidate a sufficient OR witness.','', 'These conditions validate declarations. They cannot establish that a registered report date is authentic, that a same-day market observation followed announcement time, or that monetary extraction was correct. Company currency context is not the measurement unit of percentage returns. Archived inputs lacking declarations remain unknown.','', 'Five synthetic metadata controls cover a valid fixture, wrong unit, wrong currency, wrong report anchor and absent report date. All expected responses must pass. Controls are not natural findings or new participants.','', 'Reproduce: docs/jws_metadata_v2.py after expanded-evaluation results are finalized.']
    (OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
