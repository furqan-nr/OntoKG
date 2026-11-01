"""Synthetic diagnostic benchmark; explicit expectations, independent matched baseline.

The matched baseline below is authored directly in SPARQL for the synthetic sensor
configuration, not translated from the interpreter's expression tree. SHACL checks
positive witnesses; a separate availability query distinguishes false from unknown.
This demonstrates parity, not expressiveness superiority or real-world accuracy.
"""
import copy
import hashlib
import importlib.metadata
import json
import platform
import time
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from pyshacl import validate
from jws_boundary_contracts import audit

ROOT=Path(__file__).resolve().parents[1]
L=Namespace('urn:lab:')
CONTRACT=json.loads((ROOT/'contracts/synthetic_sensor_boundary_v1.json').read_text())

# Hand-authored expected ambient/support/delivered labels: not derived from audit.
CASES=[
 ('all_positive','positive','positive','positive'),
 ('delivered_missing','positive','positive','unknown'),
 ('delivered_false_alternative','positive','positive','false'),
 ('support_missing','positive','unknown','unknown'),
 ('all_missing','unknown','unknown','unknown'),
 ('one_or_branch','positive','positive','positive'),
 ('one_false_other_missing','unknown','unknown','unknown'),
 ('both_false','false','false','false'),
 ('unit_wrong','positive','positive','positive'),
 ('unit_absent','positive','positive','positive'),
 ('nonfinite','unknown','unknown','unknown'),
 ('ambiguous_value','unknown','unknown','unknown'),
 ('wrong_bundle_entity','positive','positive','unknown'),
 ('decimal_boundary','positive','positive','positive'),
 ('decimal_below','false','false','false'),
 ('ambient_decoy_not_support','positive','false','false'),
 ('wrong_subject','unknown','unknown','unknown'),
 ('ambiguous_window','unknown','unknown','unknown'),
 ('bundle_outside_support','positive','unknown','unknown'),
 ('missing_window','unknown','unknown','unknown')]

def fixture(name):
    g=Graph(); g.add((L.finding,L.aboutSensor,L.sensor1)); g.add((L.finding,L.delivery,L.bundle))
    g.add((L.bundle,L.forSensor,L.sensor1))
    def reading(identifier,metric,value,unit,support=True,delivered=True):
        o=L[identifier]
        for p,v in [(RDF.type,L.Reading),(L.quantity,Literal(metric)),(L.number,Literal(value)),
                    (L.sensor,L.sensor1),(L.period,L.shift1),(L.unit,Literal(unit))]: g.add((o,p,v))
        if support:g.add((L.finding,L.usesReading,o))
        if delivered:g.add((L.bundle,L.contains,o))
        return o
    if name=='all_missing':return g
    t=reading('t','temperature','80','Celsius')
    if name not in {'one_or_branch','one_false_other_missing','nonfinite','ambiguous_value','wrong_subject','ambiguous_window','missing_window'}:
        reading('v','vibration','2','mm/s')
    if name in {'both_false','one_false_other_missing','ambient_decoy_not_support','delivered_false_alternative','decimal_below'}:
        g.set((t,L.number,Literal('79.999999999999999999')))
    if name=='decimal_boundary':g.set((t,L.number,Literal('80.000000000000000000')))
    if name in {'ambient_decoy_not_support','delivered_false_alternative'}:
        reading('decoy','temperature','90','Celsius',name=='delivered_false_alternative',False)
    if name=='delivered_missing':g.remove((L.bundle,L.contains,None))
    if name in {'support_missing','bundle_outside_support'}:g.remove((L.finding,L.usesReading,None))
    if name=='unit_wrong':g.set((t,L.unit,Literal('Fahrenheit')))
    if name=='unit_absent':g.remove((t,L.unit,None))
    if name=='nonfinite':g.set((t,L.number,Literal('NaN')))
    if name=='ambiguous_value':g.add((t,L.number,Literal('90')))
    if name=='wrong_bundle_entity':g.set((L.bundle,L.forSensor,L.sensor2))
    if name=='wrong_subject':g.set((t,L.sensor,L.sensor2))
    if name=='ambiguous_window':g.add((t,L.period,L.shift2))
    if name=='missing_window':g.remove((t,L.period,None))
    return g

PREFIX='PREFIX l: <urn:lab:> PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> '

def binding(metric):
    # Exactly one metric, subject, raw numeric value and period, matching entity.
    return '''?o a l:Reading; l:quantity "%s"; l:sensor l:sensor1; l:number ?raw; l:period ?w.
      FILTER NOT EXISTS {?o l:quantity ?m2 FILTER(?m2 != "%s")}
      FILTER NOT EXISTS {?o l:sensor ?s2 FILTER(?s2 != l:sensor1)}
      FILTER NOT EXISTS {?o l:number ?v2 FILTER(!sameTerm(?v2,?raw))}
      FILTER NOT EXISTS {?o l:period ?w2 FILTER(?w2 != ?w)}
      BIND(IF(REGEX(STR(?raw),"^[+-]?[0-9]+([.][0-9]*)?$"),xsd:decimal(?raw),1/0) AS ?n) FILTER(BOUND(?n))
    ''' % (metric,metric)

def baseline(pool_graph):
    passing='{ '+binding('temperature')+' FILTER(?n >= 80) } UNION { '+binding('vibration')+' FILTER(?n >= 4.5) }'
    # A positive witness conforms. Failure alone is not interpreted as false.
    query=PREFIX+'SELECT $this WHERE { FILTER NOT EXISTS { '+passing+' } }'
    shapes=Graph(); SH=Namespace('http://www.w3.org/ns/shacl#')
    shapes.add((L.shape,RDF.type,SH.NodeShape)); shapes.add((L.shape,SH.targetNode,L.finding))
    shapes.add((L.shape,SH.sparql,L.constraint)); shapes.add((L.constraint,SH.select,Literal(query)))
    conforms,_,_=validate(pool_graph,shacl_graph=shapes,advanced=True)
    available=[bool(pool_graph.query(PREFIX+'ASK { '+binding(metric)+' }')) for metric in ['temperature','vibration']]
    return 'positive' if conforms else 'false' if all(available) else 'unknown'

def projected(g,members):
    p=Graph(); members={URIRef(x) for x in members}
    readings=set(g.subjects(RDF.type,L.Reading))
    for s,pred,o in g:
        if s not in readings or s in members:p.add((s,pred,o))
    return p

def baseline_pools(g):
    """Independent fixture-specific selection; no interpreter pool output."""
    ambient=set(g.subjects(RDF.type,L.Reading))
    support=set(g.objects(L.finding,L.usesReading))
    entities=set(g.objects(L.finding,L.aboutSensor))
    bundles=set(g.objects(L.finding,L.delivery))
    delivered=set()
    if len(entities)==1 and len(bundles)==1:
        bundle=next(iter(bundles))
        if set(g.objects(bundle,L.forSensor))==entities:
            delivered=set(g.objects(bundle,L.contains)) & support
    return dict(ambient=ambient,support=support,delivered=delivered)

def run(output=None):
    results=[]; interpreter_s=0.; baseline_s=0.
    for name,*expected in CASES:
        g=fixture(name); start=time.perf_counter(); result=audit(g,L.finding,CONTRACT)
        interpreter_s+=time.perf_counter()-start
        labels=[result['pools'][p]['status'] for p in ['ambient','support','delivered']]
        start=time.perf_counter()
        independent_pools=baseline_pools(g)
        pool_match=all(set(result['pool_members'][p])==set(map(str,independent_pools[p]))
                       for p in ['ambient','support','delivered'])
        baseline_labels=[baseline(projected(g,independent_pools[p])) for p in ['ambient','support','delivered']]
        baseline_s+=time.perf_counter()-start
        results.append({'case':name,'expected':expected,'actual':labels,'matched_shacl_sparql':baseline_labels,
                        'independent_pool_membership_agrees':pool_match,'audit':result})
    mismatches=[r['case'] for r in results if r['expected']!=r['actual'] or r['actual']!=r['matched_shacl_sparql']
                or not r['independent_pool_membership_agrees']]
    report={'scope':'20 constructed synthetic sensor diagnostics; 60 pool checks, not independent empirical samples',
            'baseline_scope':'All 20 cases/all three pools; SHACL-SPARQL positive check plus availability ASK, numeric truth only; no metadata-baseline claim',
            'runtime':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ['rdflib','pyshacl']}},
            'baseline_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'configuration_bytes':{p.name:p.stat().st_size for p in [ROOT/'contracts/finance_boundary_v1.json',ROOT/'contracts/synthetic_sensor_boundary_v1.json']},
            'mismatches':mismatches,'cases':results,'timing_single_run_seconds':{'interpreter':interpreter_s,'matched_baseline':baseline_s},
            'timing_limit':'Diagnostic whole-run wall time; no speedup or statistically controlled performance claim',
            'reuse':'Same interpreter, different RDF vocabulary and JSON; synthetic configuration reuse only. Finance bindings require explicit comparedWithIndex link; no frozen v1 replay equivalence claim.',
            'baseline_limit':'Matched baseline covers only synthetic sensor OR configuration, not all four financial contracts; ordinary finite decimal lexical fixture values, not arbitrary RDF numeric terms.'}
    if output:
        output=Path(output);output.mkdir(parents=True,exist_ok=True)
        (output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if mismatches:raise AssertionError(mismatches)
    return report

if __name__=='__main__':
    report=run(ROOT/'evaluation_jws/boundary_audit_v1')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
