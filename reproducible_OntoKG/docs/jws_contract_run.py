"""Write separate versioned replay reports; never modifies archived graphs."""
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from jws_contracts import C, ROOT, evaluate_finding, load_contracts

AUDIT = Namespace('https://w3id.org/ontokg-eq/contracts#')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run():
    contracts = load_contracts()
    out = ROOT / 'evaluation_jws/contracts_v1'
    out.mkdir(parents=True, exist_ok=True)
    hashes = {}
    paths = set(contracts['artifacts'].values()) | {contracts[r]['query'] for r in ['R1','R2','R3','R4','CQ5']} | {'contracts/cq_contracts.json','docs/jws_contracts.py','docs/jws_contract_run.py'}
    rows = []
    for market in ['psx','msx','idx']:
        path = ROOT / f'data/demo_{market}_inferred.ttl'
        overlay = ROOT / f'evaluation_jws/source_lineage.{market}.ttl'
        paths.update([str(path.relative_to(ROOT)), str(overlay.relative_to(ROOT))])
        graph = Graph().parse(path)
        lineage = Graph().parse(overlay)
        contracted = Graph()
        contracted.bind('contract', AUDIT)
        market_rows = []
        for finding in sorted(set(graph.subjects(RDF.type,C.AnalyticalFinding)),key=str):
            result = evaluate_finding(graph,finding,lineage_graph=lineage)
            result['market'] = market
            rows.append(result)
            market_rows.append(result)
            contracted.add((finding,AUDIT.contractStatus,Literal(result['status'])))
            contracted.add((finding,AUDIT.contractVersion,Literal(contracts['version'])))
            contracted.add((finding,AUDIT.supportComplete,Literal(result['support_complete'])))
            contracted.add((finding,AUDIT.bundleSufficient,Literal(result['bundle_sufficient'])))
            contracted.add((finding,AUDIT.bundleStatus,Literal(result['bundle_status'])))
            contracted.add((finding,AUDIT.sourceSufficientWitness,Literal(result.get('source_sufficient_witness',False))))
            contracted.add((finding,AUDIT.unitVerification,Literal(result.get('unit_verification','unverified'))))
            for i,witness in enumerate(result['bundle_witnesses']):
                node = URIRef(str(finding) + '_contract_witness_' + str(i+1))
                contracted.add((finding,AUDIT.hasSufficientWitness,node))
                for role, observation in witness.items():
                    contracted.add((node,AUDIT[role],URIRef(observation)))
        (out / f'{market}.json').write_text(json.dumps(market_rows,indent=2),encoding='utf-8')
        contracted.serialize(out / f'{market}.contracted.ttl',format='turtle')
    for path in sorted(paths):
        hashes[path] = digest(ROOT/path)
    summary = {'contract_version':contracts['version'],'runtime':platform.python_version(),'hashes_sha256':hashes,'findings':rows,'counts':dict(Counter(r['status'] for r in rows)),'sufficient':sum(r['sufficient_witness'] for r in rows),'bundle_sufficient':sum(r['bundle_sufficient'] for r in rows),'complete_bundle_rate':sum(r['bundle_sufficient'] for r in rows)/len(rows),'all_roles_complete':sum(r['support_complete'] for r in rows),'source_sufficient':sum(r.get('source_sufficient_witness',False) for r in rows)}
    (out/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    lines = ['# Executable finding contracts v1','',f"Contract {contracts['version']}; Python {platform.python_version()}.",'','| Market | Findings | Finding support sufficient | Bundle sufficient | All roles available | Source-linked bundle witness |','|---|---:|---:|---:|---:|---:|']
    for market in ['psx','msx','idx']:
        subset = [r for r in rows if r['market']==market]
        lines.append(f"| {market} | {len(subset)} | {sum(r['sufficient_witness'] for r in subset)} | {sum(r['bundle_sufficient'] for r in subset)} | {sum(r['support_complete'] for r in subset)} | {sum(r.get('source_sufficient_witness',False) for r in subset)} |")
    lines.extend(['',f"Complete-bundle rate (at least one sufficient witness in the correctly targeted actual bundle): {summary['bundle_sufficient']}/{len(rows)}. Source sufficiency requires every recorded dependency cell of a sufficient bundle witness to have exactly one primary source with matching source identifier; it does not prove that all actual computational dependencies were recorded. A plausible but wrong consistently relinked source cannot be detected without an independent truth oracle. Observation and window RDF types are checked. R4 finding-to-event identity remains unverified where the finding declares no event-window anchor. Replay arithmetic reads RDF lexical numbers directly as Decimal; strict decimal margin boundaries are regression tested."])
    lines.extend(['','R4 uses a single passing OR branch as a sufficient witness. All-role availability is a separate contextual completeness measure. Only actual prov:wasDerivedFrom links count as source linkage; unlinked default-zero values remain untrusted. Graph units absent from observations remain explicitly unverified; expected units in the contract are assumptions, not measurements verified by the graph. Source linkage is not independent source truth. R2 tests the archived classification, not the complete CQ2 query. Event return labels retain the archived arithmetic caveat. Full-graph truth is an independent Python predicate replay over graph observations, not upstream numerical recomputation and not general SPARQL validation.','', 'The contracted TTL files are separate status/witness overlays. Original graphs and historical reports are unchanged. SHA256 hashes identify inputs and implementations in results.json.','', 'Reproduce with Python 3.13, rdflib available on PYTHONPATH: docs/jws_contract_run.py.'])
    (out/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'findings','hashes_sha256'}},indent=2))

if __name__ == '__main__':
    run()
