"""Six frozen requirement scenarios; no new empirical observations or human study."""
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
from jws_boundary_contracts import audit
from jws_nhs_application import frame
from jws_nhs_contract import N, build_contract, scaled_role
from jws_nhs_change_oracle import cohort, changes, require_equal
from jws_nhs_change_baseline import batch, shacl_control

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'external_applications/nhs_rtt_v1'
PROTOCOL=ROOT/'contracts/nhs_change_protocol_2026-10-19.json'
OUT=ROOT/'evaluation_jws/nhs_change_replay_v1'
R=Namespace(N)


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def contract(threshold,operator):
    if type(threshold) is not int or not 0<=threshold<=100 or operator not in ('ge','gt'):
        raise ValueError('unsupported policy')
    result=deepcopy(build_contract())
    result['branches'][0][1]['op']=operator
    result['branches'][0][1]['right']=scaled_role('total',threshold)
    return result


def control_frame(name,n=92,t=100):
    record={'provider_code':'control','provider_name':'Constructed control','period':'2026-08',
            'csv_present':False,'within18':None,'total':None}
    g,f=frame(record); provider=next(g.objects(f,R.aboutProvider)); month=URIRef(N+'month/2026-08')
    bundle=next(g.objects(f,R.deliveredAs))
    for role,value in [('within18',n),('total',t)]:
        if value is None: continue
        obs=URIRef(str(f)+'/'+role)
        for p,o in [(RDF.type,R.CountObservation),(R.metric,Literal(role)),(R['count'],Literal(value,datatype=XSD.integer)),
                    (R.reportedBy,provider),(R.inMonth,month),(R.unit,Literal('pathways'))]:g.add((obs,p,o))
        g.add((f,R.usesCount,obs));g.add((bundle,R.containsCount,obs))
    if name=='wrong_month':
        denominator=URIRef(str(f)+'/total'); other=URIRef(N+'month/2026-09')
        g.set((denominator,R.inMonth,other));g.add((other,RDF.type,R.ReportingMonth))
    if name=='same_witness_units':
        numerator=URIRef(str(f)+'/within18'); g.remove((numerator,R.unit,None))
        decoy=URIRef(str(f)+'/nonpassing-qualified')
        for _,p,o in list(g.triples((numerator,None,None))):g.add((decoy,p,o))
        g.set((decoy,R['count'],Literal(0,datatype=XSD.integer)));g.add((decoy,R.unit,Literal('pathways')))
        g.add((f,R.usesCount,decoy));g.add((bundle,R.containsCount,decoy))
    if name=='missing_delivered_denominator':
        g.remove((bundle,R.containsCount,URIRef(str(f)+'/total')))
    return g,f


def controls():
    result=[]
    for threshold in (90,92,95):
        for delta,label in [(-1,'below'),(0,'equal'),(1,'above')]:
            result.append((str(threshold)+'_'+label,threshold+delta,100,'numeric'))
    return result+[('missing_denominator',92,None,'unknown'),('wrong_month',92,100,'unknown'),
                   ('unavailable_publisher_only',None,None,'unknown'),('same_witness_units',100,100,'unqualified_positive'),
                   ('missing_delivered_denominator',100,100,'delivery_omission')]


def expected_control(n,t,kind,threshold,operator):
    if kind=='unknown':return {'status':'unknown','metadata_ready':False}
    if kind=='unqualified_positive':return {'status':'positive','metadata_ready':False}
    passed=t>0 and (100*n>=threshold*t if operator=='ge' else 100*n>threshold*t)
    return {'status':'positive' if passed else 'false','metadata_ready':True}


def expected_control_pools(n,t,kind,threshold,operator):
    target=expected_control(n,t,kind,threshold,operator)
    result={pool:target for pool in ('ambient','support','delivered')}
    if kind=='delivery_omission':result['delivered']={'status':'unknown','metadata_ready':False}
    return result


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    protocol=json.loads(PROTOCOL.read_text(encoding='utf-8'))
    adapter=json.loads((BASE/'adapter_records.json').read_text(encoding='utf-8'))
    prior=json.loads((BASE/'application/results.json').read_text(encoding='utf-8'))
    for relative,expected_digest in prior['hashes'].items():
        anchored=ROOT.joinpath(*relative.replace('\\','/').split('/'))
        if digest(anchored)!=expected_digest:
            raise AssertionError('previous authenticated application identity changed: '+relative)
    records=adapter['records']; assert len(records)==533
    frozen=[PROTOCOL,BASE/'adapter_records.json',BASE/'source_oracle.json',BASE/'SOURCE_MANIFEST.json',
            BASE/'PROTOCOL.md',BASE/'application/contract.json',BASE/'application/results.json',
            ROOT/'contracts/finance_boundary_v1.json',ROOT/'contracts/synthetic_sensor_boundary_v1.json']
    frozen += [Path(__file__).with_name(name) for name in ('jws_boundary_contracts.py','jws_nhs_contract.py',
               'jws_nhs_matched_baseline.py','jws_nhs_application.py','jws_nhs_adapter.py','jws_nhs_source_oracle.py')]
    identities={str(path.relative_to(ROOT)):digest(path) for path in frozen}
    graphs={}; union=Graph(); providers={}
    for record in records:
        code=record['provider_code']; graph,finding=frame(record); graphs[code]=(graph,finding)
        providers[code]=next(graph.objects(finding,R.aboutProvider))
        for triple in graph: union.add(triple)
    official=cohort(records,92,'ge'); results=[]; total_validations=0
    for variant in protocol['variants']:
        threshold,operator=variant['threshold'],variant['operator']; c=contract(threshold,operator)
        expected=cohort(records,threshold,operator); actual={}
        for code,(g,f) in graphs.items():
            checked=audit(g,f,c); normalized={pool:{key:value[key] for key in ('status','metadata_ready')} for pool,value in checked['pools'].items()}
            require_equal(normalized,{pool:expected[code] for pool in ('ambient','support','delivered')},variant['id']+'/'+code)
            actual[code]=normalized['ambient']
        baseline,query_texts=batch(union,providers,threshold,operator)
        require_equal(actual,expected,variant['id']+'/checker');require_equal(baseline,expected,variant['id']+'/baseline')
        control_results=[]
        for name,n,t,kind in controls():
            g,f=control_frame(name,n,t); checked=audit(g,f,c); direct,validations=shacl_control(g,f,threshold,operator)
            total_validations+=validations
            target=expected_control(n,t,kind,threshold,operator)
            normalized={pool:{key:value[key] for key in ('status','metadata_ready')} for pool,value in checked['pools'].items()}
            wanted=expected_control_pools(n,t,kind,threshold,operator)
            require_equal(normalized,wanted,variant['id']+'/'+name+'/checker');require_equal(direct,wanted,variant['id']+'/'+name+'/shacl')
            control_results.append({'name':name,'expected':wanted,'checker':normalized,'baseline':direct,'actual_shacl_validations':validations})
        change_ids=changes(official,actual)
        require_equal({'ids':change_ids},{'ids':changes(official,baseline)},variant['id']+'/change sets')
        result={'variant':variant,'classifications':dict(Counter(row['status'] for row in actual.values())),
                'changed_provider_codes_from_official':change_ids,'unchanged_provider_count':len(records)-len(change_ids),
                'checker':actual,'baseline':baseline,'oracle':expected,'controls':control_results,
                'contract_sha256':hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest(),
                'query_sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in query_texts.items()}}
        results.append(result)
        (OUT/(variant['id']+'_contract.json')).write_text(json.dumps(c,indent=2)+'\n',encoding='utf-8')
        (OUT/(variant['id']+'_queries.json')).write_text(json.dumps(query_texts,indent=2)+'\n',encoding='utf-8')
        (OUT/'progress.json').write_text(json.dumps({'completed':[r['variant']['id'] for r in results]},indent=2)+'\n',encoding='utf-8')
        print(variant['id'],result['classifications'],'changed',len(change_ids),flush=True)
    rollback={}
    for code,(g,f) in graphs.items():
        checked=audit(g,f,contract(92,'ge'))
        for pool in ('ambient','support','delivered'):
            require_equal({code:{k:checked['pools'][pool][k] for k in ('status','metadata_ready')}},{code:official[code]},'rollback/'+pool)
        rollback[code]={k:checked['pools']['ambient'][k] for k in ('status','metadata_ready')}
    restored_baseline,_=batch(union,providers,92,'ge');require_equal(restored_baseline,official,'baseline rollback')
    after={str(path.relative_to(ROOT)):digest(path) for path in frozen};require_equal(after,identities,'frozen artifacts')
    newcode=[Path(__file__),Path(__file__).with_name('jws_nhs_change_oracle.py'),Path(__file__).with_name('jws_nhs_change_baseline.py')]
    report={'protocol':protocol,'input_and_frozen_hashes':identities,'new_code_hashes':{p.name:digest(p) for p in newcode},
            'previous_application_hash_anchors_verified':prior['hashes'],
            'summary':{'provider_frames':len(records),'csv_eligible_records':sum(r['csv_present'] for r in records),
                       'policy_scenarios':len(results),'provider_policy_evaluations_not_independent_samples':len(records)*len(results),
                       'constructed_controls_per_policy':len(controls()),'actual_shacl_control_validations':total_validations,
                       'cohort_execution':'Four independently parameterized prepared SPARQL queries bound to each provider per policy; not SHACL cohort validation',
                       'rollback_exact':True,'frozen_artifacts_unchanged':True,'core_engine_edits':0},
            'limitations':['One existing cohort, not a new sample. Counterfactual thresholds/operators are not NHS standard changes.',
                           'Both implementations parameterize changes; parity is not a demonstrated maintenance or human-performance advantage.',
                           'Controls are constructed faults/edges, not natural reporting defects. Zero denominator is false for the guarded predicate, not a defined percentage.',
                           'Recorded before scenario execution, not externally preregistered or blinded.'],
            'variants':results,'rollback':rollback}
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lines=['# Bounded NHS requirement-change replay','','Only official_92_ge reproduces the published NHS standard. Other policies are explicitly counterfactual.','',
           '| Policy | Positive | False | Unknown | Changed provider IDs from official |','|---|---:|---:|---:|---:|']
    for r in results:
        counts=r['classifications'];lines.append('| '+r['variant']['id']+' | '+str(counts.get('positive',0))+' | '+str(counts.get('false',0))+' | '+str(counts.get('unknown',0))+' | '+str(len(r['changed_provider_codes_from_official']))+' |')
    lines+=['',f"All {len(records)} existing frames agree by provider identity, status and readiness with the integer oracle and independent parameterized SPARQL baseline for all six policies. Exact affected-provider lists appear in results.json.",
            '',f"{len(controls())} separately constructed controls per policy execute {total_validations} actual SHACL pool validations. The delivery-omission control was additionally requested before execution. Cohort results use provider-bound prepared SPARQL, not SHACL validation. Both comparators centralize policy parameters; no duplicated-edit disadvantage is imposed.",
            '', 'Official-policy rollback restores every status/readiness value in every interpreter pool and the direct baseline. Frozen inputs, original outputs, configurations and implementation files retain their recorded hashes. No core-interpreter edit was required.',
            '', 'These results establish bounded change-conformance and affected-result traceability, not general maintainability, independent production use, objective human benefit or superiority. Repeated policies and pools are not independent samples.']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report['summary']),flush=True)
    return report


if __name__=='__main__':
    try:run()
    except Exception:
        import traceback
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise
