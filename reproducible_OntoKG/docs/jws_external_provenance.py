"""Execute unmodified published NPCS rewriter, then its SPARQL with Oxigraph.

This compares provenance capability, not GraphDB/Stardog performance or native
domain-error detection. All triples receive deterministic standard reification.
"""
import ast
import hashlib
import json
import re
import os
import shutil
import subprocess
import time
from pathlib import Path
from decimal import Decimal
from collections import Counter
from rdflib import Graph, RDF, URIRef
from jws_contracts import ROOT, C, load_contracts, _replay
import pyoxigraph

WORKSPACE = ROOT.parent
CHECKOUT = Path(os.environ.get('NPCS_CHECKOUT', WORKSPACE / 'jws_external/NPCS_Fed-NPCS'))
JAR = CHECKOUT / 'NPCS-main/backend_webservices/backend_base/npcs_rewriting_main/src/main/java/jarfiles/ReifySparqlByte.jar'
OUT = ROOT / 'evaluation_jws/external_provenance'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class ResultRow(dict):
    def asdict(self):
        return self

def execute(g, query):
    store = pyoxigraph.Store()
    store.load(g.serialize(format='nt'), format=pyoxigraph.RdfFormat.N_TRIPLES)
    result = store.query(query)
    variables = [v.value for v in result.variables]
    return [ResultRow({key: URIRef(value.value) if isinstance(value,pyoxigraph.NamedNode) else value.value for key,value in zip(variables,row) if value is not None}) for row in result]

def lexical(value):
    try:
        return Decimal(str(value)).normalize()
    except Exception:
        return str(value)

def tuples(rows):
    return Counter(tuple(sorted((k,str(v)) for k,v in row.items() if k!='finalprovennacevariable')) for row in rows)

def rewrite(java, query):
    command = [str(java), '-jar', str(JAR), 'Standard', 'query', query]
    t = time.perf_counter()
    p = subprocess.run(command, capture_output=True, text=True, check=True, timeout=120)
    elapsed = time.perf_counter() - t
    array = ast.literal_eval(p.stdout[p.stdout.index('['):p.stdout.rindex(']')+1])
    return bytes(x % 256 for x in array).decode('utf-8'), elapsed, p.stdout

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    legacy_java = next((WORKSPACE / '.jws_external_deps/java17').glob('*/bin/java.exe'), None)
    java = os.environ.get('JAVA_BIN') or shutil.which('java') or legacy_java
    if not java or not JAR.is_file():
        raise RuntimeError('Set JAVA_BIN to Java 17 and NPCS_CHECKOUT to the pinned upstream checkout; see ACCESS.md')
    version = subprocess.run([str(java), '-version'], capture_output=True, text=True).stderr
    commit = subprocess.check_output(['git', '-C', str(CHECKOUT), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != 'b95bff3b56587b2a9ef6655503aada19c844630d' or sha(JAR) != '328916c1c20294ddf492b6146bc0e8e542b2f7bc73abcb6d551ef64de6f17dce':
        raise ValueError('NPCS checkout/JAR differs from pinned external implementation')
    rows = []
    for market in ['psx', 'msx', 'idx']:
        path = ROOT / f'data/demo_{market}_inferred.ttl'
        g = Graph().parse(path)
        archived_triples = len(g)
        sliced = Graph()
        for o in g.subjects(C.hasMetricName, None):
            for p in [C.isObservationOf, C.hasMetricName, C.hasMetricValue, C.observedOverWindow]:
                for value in g.objects(o,p):
                    sliced.add((o,p,value))
        # SELECT * is NPCS's provenance-producing path; retain CQ3 body and FILTER.
        original = (ROOT / 'queries/CQ3_CASE_01.rq').read_text(encoding='utf-8')
        query = 'SELECT * WHERE { ?cr <https://w3id.org/ontokg-eq#isObservationOf> ?company . ?cr <https://w3id.org/ontokg-eq#hasMetricName> ?metric . ?cr <https://w3id.org/ontokg-eq#hasMetricValue> ?value . ?cr <https://w3id.org/ontokg-eq#observedOverWindow> ?w . }'
        rewritten, rewrite_s, raw = rewrite(java, query)
        (OUT / f'{market}.input.rq').write_text(query, encoding='utf-8')
        (OUT / f'{market}.npcs.rq').write_text(rewritten, encoding='utf-8')
        (OUT / f'{market}.rewrite_stdout.txt').write_text(raw, encoding='utf-8')
        reified = Graph()
        lookup = {}
        t = time.perf_counter()
        for triple in sorted(sliced, key=lambda x: tuple(v.n3() for v in x)):
            ident = URIRef('urn:ontokg:npcs:triple:' + hashlib.sha256(' '.join(v.n3() for v in triple).encode()).hexdigest())
            lookup[str(ident)] = triple
            for predicate, value in zip([RDF.subject, RDF.predicate, RDF.object], triple):
                reified.add((ident, predicate, value))
        encoding_s = time.perf_counter() - t
        t = time.perf_counter()
        direct = execute(g,query)
        direct_s = time.perf_counter()-t
        t = time.perf_counter()
        external = execute(reified,rewritten)
        external_s = time.perf_counter()-t
        direct_companies = sorted({str(r.asdict()['company']) for r in direct})
        external_companies = sorted({str(r.asdict()['company']) for r in external})
        details = []
        for r in external:
            record = r.asdict()
            polynomial = str(record.get('finalprovennacevariable', ''))
            ids = re.findall(r'urn:ontokg:npcs:triple:[a-f0-9]{64}', polynomial)
            triples = [lookup[x] for x in ids if x in lookup]
            observations = {s for s,p,o in triples if (s, C.hasMetricName, None) in g}
            details.append({'company':str(record['company']), 'polynomial':polynomial,
                            'triple_tokens':len(ids), 'unknown_tokens':sum(x not in lookup for x in ids),
                            'observation_support':sorted(map(str,observations)),
                            'observation':str(record['cr']),
                            'provenance_support_exact':{tuple(map(lexical,t)) for t in triples}=={tuple(map(lexical,t)) for t in [(record['cr'], C.isObservationOf, record['company']), (record['cr'], C.hasMetricName, record['metric']), (record['cr'], C.hasMetricValue, record['value']), (record['cr'], C.observedOverWindow, record['w'])]},
                            'derived_sources':{str(o):sorted(map(str,g.objects(o,URIRef('http://www.w3.org/ns/prov#wasDerivedFrom')))) for o in observations}})
        recovered = {URIRef(x['observation']) for x in details if x['provenance_support_exact']}
        replay_companies = sorted(str(company) for company in g.subjects(RDF.type,C.Company) if _replay(g,recovered,company,'R3',load_contracts()['R3'])[2])
        t = time.perf_counter()
        cq3_truth = sorted({str(r['company']) for r in execute(g,original)})
        cq3_direct_s = time.perf_counter()-t
        full_query = re.sub(r'SELECT .*? WHERE','SELECT * WHERE',original,flags=re.S)
        full_query = re.sub(r'ORDER BY.*','',full_query,flags=re.S)
        full_rewritten, full_s, full_raw = rewrite(java,full_query)
        (OUT/f'{market}.cq3_full.input.rq').write_text(full_query,encoding='utf-8')
        (OUT/f'{market}.cq3_full.npcs.rq').write_text(full_rewritten,encoding='utf-8')
        # Full graph encoding for honest FILTER compatibility probe.
        full_reified = Graph()
        full_lookup = {}
        for triple in g:
            ident = URIRef('urn:ontokg:npcs:triple:' + hashlib.sha256(' '.join(v.n3() for v in triple).encode()).hexdigest())
            full_lookup[str(ident)] = triple
            for p,v in zip([RDF.subject,RDF.predicate,RDF.object],triple): full_reified.add((ident,p,v))
        full_results = execute(full_reified,full_rewritten)
        nofilter_query = re.sub(r'FILTER\([^\n]*\)', '', full_query)
        nofilter_rewrite, nofilter_s, _ = rewrite(java,nofilter_query)
        (OUT/f'{market}.cq3_bgp.input.rq').write_text(nofilter_query,encoding='utf-8')
        (OUT/f'{market}.cq3_bgp.npcs.rq').write_text(nofilter_rewrite,encoding='utf-8')
        t = time.perf_counter()
        nofilter_rows = execute(full_reified,nofilter_rewrite)
        nofilter_execute_s = time.perf_counter()-t
        nofilter_direct = execute(g,nofilter_query)
        nofilter_selected = sorted({str(r['company']) for r in nofilter_rows if Decimal(r['companyReturn'])>Decimal(r['sectorReturn']) and Decimal(r['companyReturn'])>Decimal(r['benchmarkReturn'])})
        candidate_details = []
        for r in nofilter_rows:
            polynomial = str(r.get('finalprovennacevariable',''))
            ids = re.findall(r'urn:ontokg:npcs:triple:[a-f0-9]{64}',polynomial)
            triples = [full_lookup[x] for x in ids if x in full_lookup]
            observations = {s for s,p,o in triples if (s,C.hasMetricName,None) in g}
            sufficient = bool(_replay(g,observations,r['company'],'R3',load_contracts()['R3'])[2])
            numeric = Decimal(r['companyReturn'])>Decimal(r['sectorReturn']) and Decimal(r['companyReturn'])>Decimal(r['benchmarkReturn'])
            expected = {(r['company'],RDF.type,C.Company),(r['company'],C.isClassifiedByIndustrySector,r['sector']),(r['bm'],RDF.type,C.MarketIndex)}
            for obs,entity,metric,value in [(r['cr'],r['company'],'post-report window return %',r['companyReturn']),
                                             (r['sr'],r['sector'],'sector window return %',r['sectorReturn']),
                                             (r['br'],r['bm'],'benchmark window return %',r['benchmarkReturn'])]:
                expected.update([(obs,C.isObservationOf,entity),(obs,C.hasMetricName,metric),
                                 (obs,C.hasMetricValue,value),(obs,C.observedOverWindow,r['w'])])
            exact = {tuple(map(lexical,t)) for t in triples}=={tuple(map(lexical,t)) for t in expected}
            candidate_details.append({'company':str(r['company']),'polynomial':polynomial,'triple_tokens':len(ids),
                                      'unknown_tokens':sum(x not in full_lookup for x in ids),
                                      'observations':sorted(map(str,observations)),
                                      'contract_positive':sufficient,'numeric_positive':numeric,
                                      'verdict_parity':sufficient==numeric,'support_exact':exact})
        rows.append({'market':market, 'input_sha256':sha(path), 'query_sha256':sha(OUT/f'{market}.input.rq'),
                     'rewrite_sha256':sha(OUT/f'{market}.npcs.rq'), 'archived_triples':archived_triples, 'triples':len(sliced), 'reified_triples':len(reified),
                     'encoding_s':encoding_s,'rewrite_process_s':rewrite_s,'direct_execution_s':direct_s,
                     'rewritten_execution_s':external_s,'direct_rows':len(direct),'external_rows':len(external),
                     'answer_parity':tuples(direct)==tuples(external),'direct_companies':direct_companies,
                     'external_companies':external_companies,'results':details,
                     'cq3_contract_replay_companies':replay_companies,'cq3_direct_companies':cq3_truth,
                     'cq3_contract_replay_parity':replay_companies==cq3_truth,
                     'full_cq3_npcs_rows':len(full_results),'full_cq3_direct_rows':len(cq3_truth),
                     'full_cq3_provenance_projection':'finalprovennacevariable' in full_rewritten,
                     'full_cq3_rewrite_process_s':full_s,
                     'cq3_direct_execution_s':cq3_direct_s,
                     'cq3_bgp_npcs_rows':len(nofilter_rows),'cq3_bgp_direct_rows':len(nofilter_direct),
                     'cq3_bgp_tuple_parity':tuples(nofilter_rows)==tuples(nofilter_direct),
                     'cq3_bgp_provenance_projection':'finalprovennacevariable' in nofilter_rewrite,
                     'cq3_bgp_rewrite_process_s':nofilter_s,'cq3_bgp_execution_s':nofilter_execute_s,
                     'cq3_bgp_candidates':candidate_details,
                     'cq3_bgp_postfilter_companies':nofilter_selected,
                     'cq3_bgp_postfilter_parity':nofilter_selected==cq3_truth})
    report = {'external_system':'NPCS','publication':'10.4230/TGDK.4.1.4','repository':str(CHECKOUT),
              'repository_url':'https://github.com/ZubariaForthAcc/NPCS_Fed-NPCS','commit':commit,
              'jar_sha256':sha(JAR),'adapter_sha256':sha(Path(__file__)),'java':version,'execution_backend':'Oxigraph '+pyoxigraph.__version__+'; shared local backend',
              'coverage':'Four-triple analytical observation BGP, plus full CQ3 BGP (numeric FILTER explicitly post-processed) on three actual market graphs',
              'limits':['No GraphDB/Stardog or federated execution benchmark','No full CQ1/CQ2/CQ4 operator coverage claim',
                        'Recovered triple provenance does not independently verify source truth or units',
                        'Contract replay uses original graph metadata to interpret recovered observation identifiers',
                        'Single-run timings include Java startup and are descriptive, not performance superiority evidence'],
              'markets':rows}
    (OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'commit':commit,'markets':[{k:v for k,v in r.items() if k in ['market','direct_rows','external_rows','answer_parity']} for r in rows]},indent=2))
    assert all(r['answer_parity'] and r['direct_rows']==r['external_rows'] for r in rows)
    assert all(x['triple_tokens'] and not x['unknown_tokens'] and x['provenance_support_exact'] for r in rows for x in r['results'])
    assert all(r['cq3_contract_replay_parity'] for r in rows)
    assert all(r['cq3_bgp_postfilter_parity'] and r['cq3_bgp_tuple_parity'] and r['cq3_bgp_npcs_rows']==r['cq3_bgp_direct_rows'] for r in rows)
    assert all(c['triple_tokens']==15 and not c['unknown_tokens'] and c['verdict_parity'] and c['support_exact'] for r in rows for c in r['cq3_bgp_candidates'])

if __name__ == '__main__':
    run()
