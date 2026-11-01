"""Frozen-frame dependency coverage, not a population source-accuracy estimate.

Only joins exact recorded workbook identities to previously reviewed evidence.
No upstream price is substituted, and missing dependencies never prove absence.
"""
from pathlib import Path, PureWindowsPath
from functools import lru_cache
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import sys
import openpyxl
from rdflib import Graph, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/systematic_source_audit'
A = Namespace('https://w3id.org/ontokg-eq/financial-v2#')
P = Namespace('http://www.w3.org/ns/prov#')
C = Namespace('https://w3id.org/ontokg-eq#')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(rel): return json.loads((ROOT / 'evaluation_jws' / rel).read_text(encoding='utf-8'))
def number_equal(a,b):
    try: return Decimal(str(a)) == Decimal(str(b))
    except (InvalidOperation, ValueError): return str(a)==str(b)
def norm(path): return str(path).replace('\\','/').casefold()

@lru_cache(None)
def workbook(relative):
    path = ROOT.parent / PureWindowsPath(relative).as_posix()
    wb = openpyxl.load_workbook(path,read_only=True,data_only=True)
    sheets={}
    for ws in wb:
        rows=list(ws.values); headers=rows[0]
        sheets[ws.title]=(headers,rows)
    wb.close()
    return sha(path),sheets

def reviewed_facts():
    facts={}
    for rel in ['source_authentication/results.json','annual_source_repair/results.json','ppl_source_completion/results.json']:
        report=read(rel)
        for fact in report['facts']:
            # Later PPL original-PDF review supersedes its earlier pending status.
            key=(norm(fact['workbook']),fact['worksheet'],fact['cell'])
            f=dict(fact,review_report=rel,review_report_sha256=sha(ROOT/'evaluation_jws'/rel))
            source=report.get('sources',{})
            if isinstance(source,list):source={s['company']:s for s in source}
            f['source_document_evidence']=source.get(fact['company'],report.get('source'))
            f['expected_workbook_sha256']=report.get('workbook_sha256') or read('source_authentication/results.json')['workbook_sha256']
            facts[key]=f
    return facts

def audit():
    frame=ROOT/'evaluation_jws/source_sampling/expanded_evaluation_frozen.json'
    manifest=read('source_sampling/frozen_manifest.json'); frozen=json.loads(frame.read_text())
    frame_ok=sha(frame)==manifest['input_sha256']
    reports={d['dataset']:d for d in frozen['datasets']}
    reviews=reviewed_facts(); graphs={}; graph_checks={}; facts={}; cases=[]
    malaysia=read('authentic_prices_malaysia/results.json')
    regulator=read('authentic_prices_psx/regulator_recovery.json')
    evidence_checks=[]
    for report_name in ['source_authentication/results.json','annual_source_repair/results.json','ppl_source_completion/results.json']:
        rr=read(report_name); ss=rr.get('sources',{})
        if isinstance(ss,dict):ss=list(ss.values())
        ss=list(ss)+([rr['source']] if 'source' in rr else [])
        for s in ss:
            if not s.get('file') or not s.get('sha256'):continue
            path=ROOT/PureWindowsPath(s['file']).as_posix()
            if not path.exists():path=ROOT/'evaluation_jws/source_authentication/evidence'/PureWindowsPath(s['file']).name
            evidence_checks.append({'file':str(path.relative_to(ROOT)),'expected_sha256':s['sha256'],'matches':path.exists() and sha(path)==s['sha256']})
    for s in regulator['reviewed_documents']:
        path=ROOT/PureWindowsPath(s['local_file']).as_posix();evidence_checks.append({'file':s['local_file'],'expected_sha256':s['sha256'],'matches':path.exists() and sha(path)==s['sha256']})
    path=ROOT/'evaluation_jws/authentic_prices_malaysia/maybank_issuer_published_20260302_20260529.csv'
    evidence_checks.append({'file':str(path.relative_to(ROOT)),'expected_sha256':malaysia['sha256'],'matches':sha(path)==malaysia['sha256']})
    for selected in manifest['selected_cases']:
        name=selected['dataset']; report=reports[name]
        if name not in graphs:
            path=ROOT/PureWindowsPath(report['input']).as_posix(); graphs[name]=Graph().parse(path)
            graph_checks[name]={'frozen_sha256':report['sha256'],'current_sha256':sha(path),'matches':sha(path)==report['sha256']}
        g=graphs[name]; dependencies=[]; observations=[]
        for role,obs in selected['observations'].items():
            u=URIRef(obs); ids=[]
            for cell in g.objects(u,P.wasDerivedFrom):
                rel=str(g.value(cell,A.workbookPath)); sheet=str(g.value(cell,A.worksheet)); row=int(g.value(cell,A.excelRow)); field=str(g.value(cell,A.fieldName)); val=str(g.value(cell,A.cellValue)); expected=str(g.value(cell,A.workbookSHA256))
                actual,sheets=workbook(rel); headers,rows=sheets[sheet]; column=list(headers).index(field); address=f'{openpyxl.utils.get_column_letter(column+1)}{row}'
                raw=rows[row-1][column]; context=dict(zip(headers,rows[row-1]))
                identity=(norm(rel),expected,sheet,row,field)
                fid=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
                if fid not in facts:
                    source_nodes=list(g.objects(cell,P.hadPrimarySource))
                    source_urls=[str(g.value(s,C.hasSourceURL)) for s in source_nodes if g.value(s,C.hasSourceURL) is not None]
                    status='recorded_lineage_only_unreviewed'; evidence=None; qualified=False
                    exact_identity=actual==expected and number_equal(raw,val)
                    review=reviews.get((norm(rel),sheet,address))
                    if not exact_identity: status='workbook_hash_or_value_mismatch'
                    elif review and review['expected_workbook_sha256']==actual and review['field']==field and number_equal(review['raw_value'],val):
                        status=review['status']; evidence=review
                        qualified=status in {'exact_value_and_unit_match','exact_match_after_scale_correction'}
                    else:
                        # Price evidence must identify the same instrument, date, field AND value.
                        date=str(context.get('trade_date',''))[:10]; cid=str(context.get('company_id',''))
                        candidates=[]
                        if name.startswith('demo_msx') and str(context.get('company_symbol',''))=='MAYBANK' and field=='close':
                            candidates=[dict(o,evidence_sha256=malaysia['sha256']) for o in malaysia['observations'] if o['trade_date']==date]
                        if name.startswith('demo_psx') and ((cid=='2' and field=='close') or (field=='value' and str(context.get('comparator_type','')).lower()=='market index')):
                            target='FFC' if field=='close' else 'KSE100'
                            candidates=[o for o in regulator['observations'] if o['series']==target and o['trade_date']==date]
                        match=next((o for o in candidates if number_equal(o['value'],val)),None)
                        if match:
                            evidence=match; status='issuer_republished_unknown_adjustment_basis' if 'instrument' in match else 'regulator_original_value_match_basis_not_transferred_to_workbook'
                            # Numeric agreement alone cannot transfer a feed adjustment convention.
                        elif candidates: status='reviewed_price_does_not_match_workbook_value'; evidence=candidates
                        elif 'proxy' in str(context.get('comparator_type','')).lower():status='declared_proxy_unreviewed'
                    facts[fid]={'fact_id':fid,'workbook':rel,'workbook_sha256':expected,'worksheet':sheet,'row':row,'cell':address,'field':field,'recorded_value':val,'workbook_identity_matches':exact_identity,'source_register_resolved':len(source_nodes)==1,'registered_source_urls':source_urls,'coverage_status':status,'source_value_qualified':qualified,'evidence':evidence,'datasets':[],'case_uses':0}
                facts[fid]['row_context']={k:str(context[k]) for k in ['company_id','company_symbol','trade_date','comparator_type','comparator_name','fiscal_year','period_end_date','source_url_or_file'] if k in context}
                record=facts[fid]
                if isinstance(record['evidence'],dict) and record['evidence'].get('replacement_source_url'):
                    replacement=record['evidence']['replacement_source_url']
                    record['annual_source_review_uses_repair_overlay']=True
                    record['replacement_source_already_registered_in_financial_graph']=replacement in record['registered_source_urls']
                    record['provenance_repaired_automatically']=False
                record=facts[fid]; record['case_uses']+=1
                if name not in record['datasets']:record['datasets'].append(name)
                ids.append(fid); dependencies.append(fid)
            observations.append({'role':role,'observation':obs,'recorded_dependency_facts':sorted(set(ids)),'metric_definition':str(g.value(u,A.metricDefinition)),'computation_status':str(g.value(u,A.computationStatus))})
        unique=sorted(set(dependencies)); unresolved=[f for f in unique if not facts[f]['source_value_qualified']]
        status='incomplete_input_not_absence_proof' if selected['numerical_label']=='incomplete' else 'not_fully_source_qualified'
        # Deliberately conservative: all recorded deciding dependencies, plus interval/scope gates.
        cases.append(dict(selected,observations_detail=observations,unique_dependency_facts=unique,unqualified_dependency_facts=unresolved,coverage_status=status,fully_source_qualified=False,temporal_and_basis_gate='not_established_by_source_coverage',missing_dependency_proof=False))
    result={'version':'frozen-systematic-dependency-coverage-v1','review_date':'2026-10-17','frame_hash_matches':frame_ok,'frozen_frame_sha256':sha(frame),'manifest_sha256':sha(ROOT/'evaluation_jws/source_sampling/frozen_manifest.json'),'graph_checks':graph_checks,'selected_cases':len(cases),'strata':len(manifest['strata']),'unique_recorded_input_facts':len(facts),'fact_status_counts':dict(Counter(f['coverage_status'] for f in facts.values())),'qualified_source_value_facts':sum(f['source_value_qualified'] for f in facts.values()),'fully_source_qualified_cases':0,'cases_by_numerical_label':dict(Counter(c['numerical_label'] for c in cases)),'cases':cases,'facts':list(facts.values()),'limits':['Coverage review of frozen selected cases, not 52 independently externally reviewed findings or a population accuracy rate.','Exact recorded lineage is not source authenticity; zero dependency cells do not establish source completeness.','All-recorded-dependency coverage is conservative, not a minimal AND/OR sufficiency proof.','Annual scale-corrected facts do not establish unreviewed monetary accuracy or compatible accounting scopes.','Price matching is numeric evidence only; original-workbook adjustment basis, benchmark compatibility, calendar completeness and publication-time semantics remain separate gates.','IDX curated/scaled copies are deduplicated by workbook hash, sheet, row and field; datasets are not independent.','No new internet source facts admitted in this bounded coverage integration; existing primary-source reviews are cited at fact level.']}
    result['source_document_hash_checks']=evidence_checks
    result['cross_workbook_overlap_policy']='Exact workbook-cell identities are deduplicated. Different workbook copies are NOT automatically merged or counted as independent companies; apparent equal values are not an identity oracle.'
    result['limits'][5]=result['cross_workbook_overlap_policy']
    result['limits'].append('Annual review evidence may depend on a separate repair overlay. This coverage join does not update historical source associations in the financial graphs.')
    result['primary_review_price_disagreements']=[{'fact_id':f['fact_id'],'workbook':f['workbook'],'cell':f['cell'],'trade_date':f['row_context'].get('trade_date'),'workbook_value':f['recorded_value'],'reviewed_values':[e['value'] for e in f['evidence']],'primary_evidence':f['evidence']} for f in facts.values() if f['coverage_status']=='reviewed_price_does_not_match_workbook_value']
    OUT.mkdir(exist_ok=True)
    (OUT/'results.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    lines=['# Frozen source-dependency coverage','','This is an executed coverage audit, not a completed source-authenticated financial cohort.','',f"Selected cases: {len(cases)} across {len(manifest['strata'])} strata. Unique recorded input facts: {len(facts)}. Qualified source-value facts: {result['qualified_source_value_facts']}. Fully source-qualified findings: 0.",'','| Dependency status | Unique facts |','|---|---:|']
    lines += [f'| {s} | {n} |' for s,n in sorted(result['fact_status_counts'].items())]
    lines += ['','## Exact primary-review disagreements','','These are pre-existing workbook values compared with previously reviewed original regulator observations; no substitution was performed.','']
    for item in result['primary_review_price_disagreements']:
        lines.append(f"- {item['workbook']} {item['cell']} ({item['trade_date']}): workbook {item['workbook_value']}; reviewed original {', '.join(item['reviewed_values'])}. Full date-column, page, source URL and document hash in results.json.")
    lines += ['','Four exact scale-qualified dependency facts are FFC PAT I4/I5 and OGDC PAT I6/I7. OGDC review depends on its separate source-repair evidence; financial-v2 graph source links are not automatically repaired. The six verified PPL annual facts are outside this particular frozen dependency selection and are not counted.','']
    lines += ['',*result['limits'],'','Reproduce: `python docs/jws_systematic_source_audit.py`. Run assertions with `--test`. No data or manuscript inputs are modified.']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return result

def tests(r):
    assert r['frame_hash_matches'], 'Frozen frame changed'
    assert all(c['matches'] for c in r['source_document_hash_checks']), 'Inspected source document changed'
    assert all(c['matches'] for c in r['graph_checks'].values()),'Graph/frame mismatch'
    assert r['selected_cases']==52 and r['strata']==29
    assert len({f['fact_id'] for f in r['facts']})==r['unique_recorded_input_facts']
    assert sum(r['fact_status_counts'].values())==len(r['facts'])
    assert all(not c['fully_source_qualified'] for c in r['cases'])
    assert all(c['coverage_status']=='incomplete_input_not_absence_proof' for c in r['cases'] if c['numerical_label']=='incomplete')
    assert all(f['workbook_identity_matches'] for f in r['facts'])
    assert all(f['coverage_status'] in {'exact_value_and_unit_match','exact_match_after_scale_correction'} for f in r['facts'] if f['source_value_qualified'])
    assert any(f['case_uses']>1 for f in r['facts']), 'Repeated exact inputs must deduplicate'
    assert number_equal('1.0','1') and not number_equal('1','1.01')
    assert all(set(c['unqualified_dependency_facts']) <= set(c['unique_dependency_facts']) for c in r['cases'])
    print('13 coverage assertions passed')

if __name__=='__main__':
    result=audit()
    if '--test' in sys.argv:tests(result)
    print(json.dumps({k:result[k] for k in ['selected_cases','strata','unique_recorded_input_facts','fact_status_counts','qualified_source_value_facts','fully_source_qualified_cases']}))
