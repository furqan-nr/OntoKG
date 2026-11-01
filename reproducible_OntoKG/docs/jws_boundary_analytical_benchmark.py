"""Constructed analytical parity diagnostics, not population or novelty evidence.

Baseline patterns and expressions are independently authored here, not compiled
from the checker configuration. SHACL-SPARQL decides existence of passing
assignments; explicit availability ASK queries distinguish false from unknown.
"""
import hashlib
import importlib.metadata
import json
import platform
import re
from decimal import Decimal, getcontext
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from pyshacl import validate
from jws_boundary_contracts import audit

ROOT = Path(__file__).resolve().parents[1]
E = Namespace('https://w3id.org/ontokg-eq#')
T = Namespace('urn:analytical-test:')
SH = Namespace('http://www.w3.org/ns/shacl#')
CONFIG = ROOT/'contracts/finance_boundary_v1.json'
CHECKER = Path(__file__).with_name('jws_boundary_contracts.py')
PREFIX = 'PREFIX e: <https://w3id.org/ontokg-eq#> PREFIX t: <urn:analytical-test:> PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> '

# Literal role definitions are independent of the interpreter config.
# metric, target subject/path, subject type, window predicate/type, unit
ROLES = {
 'g': ('YoY profit growth %','t:company','Company',None,None,'percent'),
 'c': ('post-report window return %','t:company','Company','observedOverWindow','AnalysisWindow','percent'),
 'b': ('benchmark window return %','?targetb','MarketIndex','observedOverWindow','AnalysisWindow','percent'),
 's': ('sector window return %','?targets','IndustrySectorClassifier','observedOverWindow','AnalysisWindow','percent'),
 'r': ('FX vs company return correlation','t:company','Company',None,None,'coefficient'),
 'a': ('cumulative abnormal return %','t:company','Company','observedInEventWindow','EventWindow','percent'),
 'v': ('abnormal volume ratio','t:company','Company','observedInEventWindow','EventWindow','ratio')}
BRANCHES = {'R1': [('gcb','?ng > 0 && ?nc < ?nb')],
 'R2': [('r','ABS(?nr) >= 0.3')],
 'R3': [('csb','?nc > (?ns + 1.0) && ?nc > (?nb + 1.0)')],
 'R4': [('a','ABS(?na) >= 2.0'),('v','?nv >= 1.5')]}

# name, rule, ambient/support/delivered (status, metadata_ready); hand authored.
P=('positive',True); F=('false',True); U=('unknown',False); Q=('positive',False); N=('false',False)
CASES = [
 ('r1_positive','R1',(P,P,P)), ('r1_false','R1',(F,F,F)),
 ('r1_mixed_window','R1',(U,U,U)), ('r1_path_decoy','R1',(U,U,U)),
 ('r1_unit_laundering','R1',(Q,Q,Q)), ('r1_qualified_alternative','R1',(P,P,P)),
 ('r1_wrong_subject_type','R1',(U,U,U)),
 ('r2_negative_boundary','R2',(P,P,P)), ('r2_below','R2',(F,F,F)),
 ('r2_ambient_decoy','R2',(P,F,F)), ('r2_wrong_bundle','R2',(P,P,U)),
 ('r2_unit_wrong','R2',(Q,Q,Q)), ('r2_wrong_bundle_type','R2',(P,P,U)),
 ('r3_above_margin','R3',(P,P,P)), ('r3_exact_margin','R3',(F,F,F)),
 ('r3_bad_window_type','R3',(U,U,U)), ('r3_mixed_windows','R3',(U,U,U)),
 ('r3_wrong_window_decoy','R3',(F,F,F)), ('r3_delivery_missing','R3',(P,P,U)),
 ('r4_volume_only','R4',(P,P,P)), ('r4_false_missing','R4',(U,U,U)),
 ('r4_both_false','R4',(F,F,F)), ('r4_false_unit_missing','R4',(N,N,N)),
 ('r4_negative_boundary','R4',(P,P,P)), ('r4_invalid_event_type','R4',(U,U,U)),
 ('r4_bundle_outside_support','R4',(P,U,U))]

def contracts():
    result=json.loads(CONFIG.read_text())
    # Separate diagnostic parameter, never modify the frozen file.
    for comparison in result['R3']['branches'][0]:
        comparison['right']['add'][1]['constant']='1.0'
    return result

def fixture(name, rule):
    g=Graph()
    for triple in [(T.company,RDF.type,E.Company),(T['index'],RDF.type,E.MarketIndex),
      (T.sector,RDF.type,E.IndustrySectorClassifier),(T.bundle,RDF.type,E.EvidenceBundle),
      (T.company,E.comparedWithIndex,T['index']),(T.company,E.isClassifiedByIndustrySector,T.sector),
      (T.finding,RDF.type,E.AnalyticalFinding),
      (T.finding,E.concernsEntity,T.company),(T.finding,E.hasEvidenceBundle,T.bundle),
      (T.bundle,E.explainsResultEntity,T.company),(T.w1,RDF.type,E.AnalysisWindow),
      (T.w2,RDF.type,E.AnalysisWindow),(T.ev,RDF.type,E.EventWindow)]:g.add(triple)
    def obs(key, value, identifier=None, support=True, delivered=True, unit=None, window=None):
        metric,target,_,wp,_,expected=ROLES[key]; o=T[identifier or key]
        subject=T['index'] if key=='b' else T.sector if key=='s' else T.company
        for p,v in [(RDF.type,E.Observation),(E.hasMetricName,Literal(metric)),
          (E.isObservationOf,subject),(E.hasMetricValue,Literal(value)),
          (E.hasUnit,Literal(expected if unit is None else unit))]:g.add((o,p,v))
        if wp:g.add((o,E[wp],window or (T.ev if key in 'av' else T.w1)))
        if support:g.add((T.finding,E.supportedByObservation,o))
        if delivered:g.add((T.bundle,E.includesObservation,o))
        return o
    if rule=='R1':
        obs('g','5');obs('c','1');obs('b','2')
        if name=='r1_false':g.set((T.g,E.hasMetricValue,Literal('-1')))
        if name=='r1_mixed_window':g.set((T.b,E.observedOverWindow,T.w2))
        if name=='r1_path_decoy':g.set((T.company,E.comparedWithIndex,T.other))
        if name=='r1_wrong_subject_type':g.remove((T.company,RDF.type,E.Company));g.add((T.company,RDF.type,E.Wrong))
        if name in {'r1_unit_laundering','r1_qualified_alternative'}:
            g.set((T.g,E.hasUnit,Literal('ratio')))
            obs('g','-1','negative_ready')
            if name=='r1_qualified_alternative':obs('g','6','positive_ready')
    if rule=='R2':
        obs('r','-0.3')
        if name in {'r2_below','r2_ambient_decoy'}:g.set((T.r,E.hasMetricValue,Literal('-0.2999')))
        if name=='r2_ambient_decoy':obs('r','0.5','decoy',False,False)
        if name=='r2_wrong_bundle':g.set((T.bundle,E.explainsResultEntity,T.other))
        if name=='r2_wrong_bundle_type':g.remove((T.bundle,RDF.type,E.EvidenceBundle))
        if name=='r2_unit_wrong':g.set((T.r,E.hasUnit,Literal('percent')))
    if rule=='R3':
        obs('c','3.0001');obs('s','2');obs('b','1')
        if name in {'r3_exact_margin','r3_wrong_window_decoy'}:g.set((T.c,E.hasMetricValue,Literal('3.0')))
        if name=='r3_bad_window_type':g.remove((T.w1,RDF.type,E.AnalysisWindow))
        if name=='r3_mixed_windows':g.set((T.s,E.observedOverWindow,T.w2))
        if name=='r3_wrong_window_decoy':obs('c','9','decoy',window=T.w2)
        if name=='r3_delivery_missing':g.remove((T.bundle,E.includesObservation,T.s))
    if rule=='R4':
        if name=='r4_volume_only':obs('v','1.5')
        elif name=='r4_negative_boundary':obs('a','-2.0')
        else:
            obs('a','1.9')
            if name!='r4_false_missing':obs('v','1.4')
        if name=='r4_false_unit_missing':g.remove((T.v,E.hasUnit,None))
        if name=='r4_invalid_event_type':g.remove((T.ev,RDF.type,E.EventWindow))
        if name=='r4_bundle_outside_support':
            g.set((T.a,E.hasMetricValue,Literal('2')))
            g.remove((T.finding,E.supportedByObservation,None))
    # Wrong role subject type test uses a typed finding but wrong benchmark type.
    if name=='r1_wrong_subject_type':
        g.add((T.company,RDF.type,E.Company));g.remove((T['index'],RDF.type,E.MarketIndex))
    return g

def binding(key, ready=False):
    metric,target,typ,wp,wt,unit=ROLES[key]
    path='t:company e:comparedWithIndex ?targetb.' if key=='b' else 't:company e:isClassifiedByIndustrySector ?targets.' if key=='s' else ''
    pattern=f'''{path} {target} a e:{typ}.
    ?o{key} a e:Observation; e:hasMetricName "{metric}"; e:isObservationOf {target}; e:hasMetricValue ?raw{key}.
    FILTER NOT EXISTS {{?o{key} e:hasMetricName ?otherm{key} FILTER(STR(?otherm{key}) != "{metric}")}}
    FILTER NOT EXISTS {{?o{key} e:isObservationOf ?others{key} FILTER(?others{key} != {target})}}
    FILTER NOT EXISTS {{?o{key} e:hasMetricValue ?otherv{key} FILTER(!sameTerm(?otherv{key},?raw{key}))}}
    BIND(xsd:decimal(?raw{key}) AS ?n{key}) FILTER(BOUND(?n{key}))
    '''
    if wp:
        pattern+=f'''?o{key} e:{wp} ?w{key}. ?w{key} a e:{wt}.
        FILTER NOT EXISTS {{?o{key} e:{wp} ?otherw{key} FILTER(?otherw{key} != ?w{key})}}'''
    if ready:
        pattern+=f'''?o{key} e:hasUnit "{unit}".
        FILTER NOT EXISTS {{?o{key} e:hasUnit ?otheru{key} FILTER(STR(?otheru{key}) != "{unit}")}}'''
    return pattern

def branch_pattern(keys, ready=False):
    pattern='\n'.join(binding(k,ready) for k in keys)
    windowed=[k for k in keys if ROLES[k][3]]
    if len(windowed)>1:pattern+=' FILTER('+ ' && '.join('?w'+k+' = ?w'+windowed[0] for k in windowed[1:])+')'
    return pattern

def queries(rule, ready=False):
    branches=BRANCHES[rule]
    positive=' UNION '.join('{'+branch_pattern(keys,ready)+' FILTER('+condition+')}' for keys,condition in branches)
    select=PREFIX+'SELECT $this WHERE { FILTER NOT EXISTS {'+positive+'} }'
    availability=[PREFIX+'ASK {'+branch_pattern(keys,ready)+'}' for keys,_ in branches]
    return select,availability

def conforms(g, select):
    shapes=Graph()
    for triple in [(T.shape,RDF.type,SH.NodeShape),(T.shape,SH.targetNode,T.finding),
      (T.shape,SH.sparql,T.constraint),(T.constraint,SH.select,Literal(select))]:shapes.add(triple)
    return bool(validate(g,shacl_graph=shapes,advanced=True)[0])

def baseline(g, rule):
    positive,available=queries(rule)
    unitpositive,unitavailable=queries(rule,True)
    status='positive' if conforms(g,positive) else 'false' if all(bool(g.query(q)) for q in available) else 'unknown'
    ready=conforms(g,unitpositive) if status=='positive' else all(bool(g.query(q)) for q in unitavailable) if status=='false' else False
    return status,ready

def pools(g):
    # Independent direct RDF selection; never consume audit pool_members.
    ambient=set(g.subjects(RDF.type,E.Observation))
    support=set(g.objects(T.finding,E.supportedByObservation))
    bundles=set(g.objects(T.finding,E.hasEvidenceBundle))
    valid=len(bundles)==1
    bundle=next(iter(bundles)) if valid else None
    valid=valid and (bundle,RDF.type,E.EvidenceBundle) in g and set(g.objects(bundle,E.explainsResultEntity))=={T.company}
    delivered={o for o in support if (bundle,E.includesObservation,o) in g} if valid else set()
    result={}
    for name,members in [('ambient',ambient),('support',support),('delivered',delivered)]:
        projected=Graph()
        # Context stays ambient; only observation triples are restricted.
        for s,p,o in g:
            if s not in ambient or s in members:projected.add((s,p,o))
        result[name]=projected
    return result

def assert_expected(actual, expected, context):
    if tuple(actual)!=tuple(expected):raise AssertionError(f'{context}: {actual!r} != {expected!r}')

def check_fixture_precision(g):
    """Guard the measured comparator subset, not the interpreter's wider input range."""
    for raw in g.objects(None,E.hasMetricValue):
        if not re.fullmatch(r'[+-]?[0-9]+(?:\.[0-9]+)?',str(raw)):
            raise ValueError('primary fixture is outside the ordinary decimal lexical subset')
        number=Decimal(str(raw))
        if len(number.as_tuple().digits)>5 or number.as_tuple().exponent < -4:
            raise ValueError('primary fixture exceeds five significant digits/four decimal places')

def precision_probe(configured):
    """Separate stress observation; never included in the 26-case parity count."""
    g=fixture('r3_above_margin','R3')
    sector='2.00000000000000000000000000001'
    company='3.00000000000000000000000000001'
    g.set((T.s,E.hasMetricValue,Literal(sector)))
    g.set((T.c,E.hasMetricValue,Literal(company)))
    actual=audit(g,T.finding,configured['R3'])['pools']['delivered']
    independent=baseline(pools(g)['delivered'],'R3')
    return dict(scope='Out-of-primary-fixture precision stress; not part of 26-case/78-pool agreement.',
                sector=sector,company=company,margin='1.0',
                checker=[actual['status'],actual['metadata_ready']],independent_baseline=independent,
                agreement=(actual['status'],actual['metadata_ready'])==independent,
                explanation='The tested RDFLib SPARQL arithmetic uses ambient Decimal precision. Rounding can change strict comparisons; increased comparator precision can address this example. This is not a SHACL expressiveness limitation.')

def run():
    if getcontext().prec != 28:raise ValueError('reproducible benchmark requires ambient Decimal precision 28')
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [CHECKER,CONFIG]}
    records=[];configured=contracts()
    for name,rule,expected in CASES:
        g=fixture(name,rule);check_fixture_precision(g);actual=audit(g,T.finding,configured[rule])
        for i,(pool,projected) in enumerate(pools(g).items()):
            observed=(actual['pools'][pool]['status'],actual['pools'][pool]['metadata_ready'])
            independently=baseline(projected,rule)
            assert_expected(observed,expected[i],name+'/'+pool+'/checker')
            assert_expected(independently,expected[i],name+'/'+pool+'/baseline')
            records.append({'case':name,'rule':rule,'pool':pool,'expected':expected[i],
                'checker':observed,'independent_baseline':independently})
    after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [CHECKER,CONFIG]}
    assert before==after
    return {'scope':'constructed diagnostics, not independent empirical samples or superiority evidence',
      'cases':len(CASES),'paired_pool_checks':len(records),'status_and_readiness_disagreements':0,
      'fixture_parameters':{'R3_margin':'1.0','decimal_scope':'tested ordinary decimal fixtures, at most five significant digits/four decimal places','ambient_decimal_precision':getcontext().prec},
      'out_of_scope_precision_probe':precision_probe(configured),
      'preserved_inputs_before':before,'preserved_inputs_after':after,
      'benchmark_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'test_sha256':hashlib.sha256(Path(__file__).with_name('test_jws_boundary_analytical.py').read_bytes()).hexdigest(),
      'source_separation':{'checker':str(CHECKER.relative_to(ROOT)),
          'independent_baseline_and_fixtures':str(Path(__file__).relative_to(ROOT)),
          'policy':'manual expressions/patterns, not generated from configuration; pools selected directly from RDF'},
      'effective_contract_sha256':{r:hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest() for r,c in configured.items()},
      'runtime':{'python':platform.python_version(),'rdflib':importlib.metadata.version('rdflib'),'pyshacl':importlib.metadata.version('pyshacl')},
      'baseline_queries':{r:{'numeric':queries(r),'unit_ready':queries(r,True)} for r in BRANCHES},
      'records':records}

def main():
    report=run(); out=ROOT/'evaluation_jws/boundary_analytical_v1';out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (out/'README.md').write_text('# Matched analytical diagnostics\n\n26 constructed cases, 78 paired pool checks; numerical status and metadata readiness agree with hand-authored expectations and independently authored SHACL-SPARQL plus explicit availability queries. These paired checks are not 78 independent empirical samples. R3 uses a declared diagnostic margin of 1.0, not the frozen zero-margin finance configuration. Primary inputs are tested short-precision ordinary decimals: at most five significant digits and four decimal places. Passing unit readiness requires one same-assignment qualified witness; false readiness requires a qualified complete assignment for every OR branch. Query texts, input hashes before/after and source hash appear in results.json.\n\nA separate out-of-scope precision probe records sector 2.00000000000000000000000000001 and company 3.00000000000000000000000000001 with margin 1. The exact checker returns false; the default-precision RDFLib baseline returns positive due to arithmetic rounding. This is excluded from the bounded primary parity count but explicitly retained, not discarded. It is an implementation/context limitation, not proof of SHACL expressiveness limits; greater comparator precision can address this example. No general numeric equivalence, speed, superiority, source-authentication, human-performance or cross-domain claim follows.\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['cases','paired_pool_checks','status_and_readiness_disagreements']}))

if __name__=='__main__':main()
