"""Real published RTT cohort replay; no patient-level or human-performance claims."""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from rdflib import Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD
from jws_boundary_contracts import audit
from jws_nhs_contract import N, build_contract
from jws_nhs_matched_baseline import audit_baseline

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'external_applications/nhs_rtt_v1'
R = Namespace(N)
PROV = Namespace('http://www.w3.org/ns/prov#')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame(record):
    """One provider-month task context, with explicit field/record selectors."""
    provider = URIRef(N+'provider/'+quote(record['provider_code']))
    finding = URIRef(str(provider)+'/screen/'+record['period'])
    bundle = URIRef(str(finding)+'/view')
    month = URIRef(N+'month/'+record['period'])
    g = Graph(identifier=finding)
    for s, p, o in [(provider,RDF.type,R.Provider),(month,RDF.type,R.ReportingMonth),
                    (bundle,RDF.type,R.EvidenceView),(finding,R.aboutProvider,provider),
                    (finding,R.deliveredAs,bundle),(bundle,R.forProvider,provider)]:
        g.add((s,p,o))
    g.add((provider,R.label,Literal(record['provider_name'])))
    if record['csv_present']:
        for role in ('within18','total'):
            obs = URIRef(str(finding)+'/'+role)
            selector = URIRef(str(obs)+'/source-selector')
            for p,o in [(RDF.type,R.CountObservation),(R.metric,Literal(role)),
                        (R['count'],Literal(record[role],datatype=XSD.integer)),
                        (R.reportedBy,provider),(R.inMonth,month),(R.unit,Literal('pathways')),
                        (PROV.wasDerivedFrom,selector)]:
                g.add((obs,p,o))
            g.add((finding,R.usesCount,obs)); g.add((bundle,R.containsCount,obs))
            lineage = record['lineage']
            columns = lineage['within18_columns'] if role=='within18' else [lineage['total_column']]
            for p,o in [(R.sourceSHA256,Literal(lineage['archive_sha256'])),
                        (R.archiveMember,Literal(lineage['member'])),
                        (R.logicalRecordsIncludingHeader,Literal(json.dumps(lineage['record_numbers_including_header']))),
                        (R.sourceColumns,Literal(json.dumps(columns))),
                        (R.operation,Literal('sum selected source cells'))]:
                g.add((selector,p,o))
    return g, finding


def run():
    adapter = json.loads((BASE/'adapter_records.json').read_text(encoding='utf-8'))
    oracle = json.loads((BASE/'source_oracle.json').read_text(encoding='utf-8'))
    manifest = json.loads((BASE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert digest(BASE/'SOURCE_MANIFEST.json') == adapter['manifest_sha256']
    oracle_sources={s['filename']:s for s in oracle['sources']}
    for source in manifest['sources']:
        path=BASE/source['file']
        assert digest(path) == adapter['source_sha256'][source['file']] == source['sha256'] == oracle_sources[path.name]['sha256']
        assert path.stat().st_size == source['bytes'] == oracle_sources[path.name]['bytes']
    assert digest(Path(__file__).with_name('jws_nhs_adapter.py')) == adapter['adapter_sha256']
    assert digest(BASE/'PROTOCOL.md') == adapter['protocol_sha256'] == oracle['protocol_sha256']
    reference = {r['provider_code']:r for r in oracle['records']}
    prior=json.loads((ROOT/'evaluation_jws/boundary_legacy_parity_v1/results.json').read_text(encoding='utf-8'))
    assert digest(Path(__file__).with_name('jws_boundary_contracts.py')) == prior['checker_sha256']
    assert len(reference)==len(oracle['records'])
    assert {r['provider_code'] for r in adapter['records'] if r['csv_present']}==set(reference)
    output=BASE/'application'; output.mkdir(exist_ok=True)
    contract=build_contract(); dataset=Dataset(); results=[]; timings=Counter()
    for record in adapter['records']:
        assert not record['errors']
        if record['csv_present']:
            ref=reference[record['provider_code']]
            for field in ('within18','total','weekly_counts','period','classification'):
                assert record[field]==ref[field], (record['provider_code'],field)
            lineage=record['lineage']; independent=ref['csv_lineage']
            assert lineage['member']==independent['member']
            assert sorted(lineage['record_numbers_including_header'])==sorted(independent['line_numbers'])
            assert lineage['within18_columns']==independent['within18_columns']
            assert lineage['total_column']==independent['total_column']
            assert all(ref['publisher_comparison'][k] for k in
                       ('total','within18','all_18_weekly_cells','stored_percentage'))
            expected='positive' if ref['classification']=='at_least_92_percent' else 'false'
        else:
            assert record['within18'] is None and record['total'] is None
            expected='unknown'
        g,finding=frame(record)
        for triple in g: dataset.graph(finding).add(triple)
        start=time.perf_counter(); checked=audit(g,finding,contract)
        timings['checker_seconds']+=time.perf_counter()-start
        start=time.perf_counter(); baseline=audit_baseline(g,finding)
        timings['baseline_seconds']+=time.perf_counter()-start
        assert checked['bundle_association_valid']==baseline['bundle_association_valid']
        assert checked['pool_members']==baseline['pool_members']
        for pool in ('ambient','support','delivered'):
            for key in ('status','metadata_ready'):
                assert checked['pools'][pool][key]==baseline['pools'][pool][key]
            assert checked['pools'][pool]['status']==expected
            assert checked['pools'][pool]['metadata_ready']==record['csv_present']
        results.append({'provider_code':record['provider_code'],'classification':record['classification'],
                        'publisher_context':record['publisher_context'],'checker':checked,'baseline':baseline})
        if len(results)%100==0: print('Verified provider frames:',len(results),flush=True)
    dataset.serialize(destination=str(output/'application.trig'),format='trig')
    (output/'contract.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')
    summary={'application_frames':len(results),'csv_provider_records':len(reference),
             'classifications':dict(Counter(r['classification'] for r in results)),
             'matched_baseline_agreements':len(results),'publisher_reconciled_provider_records':len(reference),
             'actual_shacl_validations':sum(r['baseline']['shacl_validations'] for r in results),
             'named_graphs':len(results),'rdf_triples':len(dataset),
             'source_cells_referenced':adapter['summary']['source_cells_referenced']}
    hashes={str(p.relative_to(ROOT)):digest(p) for p in
            [BASE/'adapter_records.json',BASE/'source_oracle.json',BASE/'PROTOCOL.md',
             Path(__file__),Path(__file__).with_name('jws_boundary_contracts.py'),
             Path(__file__).with_name('jws_nhs_contract.py'),Path(__file__).with_name('jws_nhs_matched_baseline.py')]}
    result={'summary':summary,'hashes':hashes,'one_run_timings_not_benchmark':dict(timings),
            'scope':'Provider-month contextual ambient graph; generated views, not publisher explanation artifacts. Source selectors identify published aggregate fields, not patient-level derivation.',
            'limitations':['CSV and workbook share the same reporting collection.',
                           'No natural source discrepancy was found; no clinical accuracy or objective human benefit is established.',
                           'Three equal pools per provider are not independent samples; identical baseline pools are cached.',
                           'New source adapter, bounded integer-scaling compiler and application contract; core interpreter unchanged.',
                           'Workbook-only zero denominator is retained as context, never zero-filled into unavailable CSV evidence.'],
            'records':results}
    (output/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)
    return result


if __name__=='__main__': run()
