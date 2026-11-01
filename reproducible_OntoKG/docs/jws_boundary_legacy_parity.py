"""Replay frozen classification pools with the additive declarative interpreter.

This is a paired implementation check, not new independent observations.
Adapter links exist only in memory. Metadata readiness is not certified here.
"""
import hashlib
import json
import platform
from pathlib import Path
from rdflib import Graph, RDF, URIRef
from jws_boundary_contracts import evaluate_pool

ROOT = Path(__file__).resolve().parents[1]
C = 'https://w3id.org/ontokg-eq#'
SOURCE = ROOT / 'evaluation_jws/expanded_evaluation_v2'
OUT = ROOT / 'evaluation_jws/boundary_legacy_parity_v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    report_path = SOURCE / 'results.json'
    ledger = json.loads(report_path.read_text(encoding='utf-8'))
    configs_path = ROOT / 'contracts/finance_boundary_v1.json'
    configs = json.loads(configs_path.read_text(encoding='utf-8'))
    checker_path = Path(__file__).with_name('jws_boundary_contracts.py')
    implementation_hashes = {'contract': digest(configs_path), 'checker': digest(checker_path)}
    hashes = {str(report_path.relative_to(ROOT)): digest(report_path)}
    rows = []
    expected_status = {'positive': 'positive', 'negative': 'false', 'incomplete': 'unknown'}
    for dataset in ledger['datasets']:
        path = SOURCE / (dataset['dataset'] + '.experiment.ttl')
        hashes[str(path.relative_to(ROOT))] = digest(path)
        g = Graph().parse(path, format='turtle')
        # Explicit adapter for the v1 implicit market-index lookup. No source
        # graph is rewritten and no comparator is newly authenticated.
        indexes = set(g.subjects(RDF.type, URIRef(C + 'MarketIndex')))
        for company in g.subjects(RDF.type, URIRef(C + 'Company')):
            for index in indexes:
                g.add((company, URIRef(C + 'comparedWithIndex'), index))
        all_obs = set(g.subjects(RDF.type, URIRef(C + 'Observation')))
        cases = dataset['cases']
        for frozen in dataset['replay']:
            i = frozen['case_index']
            case = cases[i]
            finding = URIRef(f'https://w3id.org/ontokg-eq/expanded/{dataset["dataset"]}/{i}')
            bundle = URIRef(str(finding) + '_bundle')
            entity = URIRef(case['company'])
            spec = configs[case['rule']]
            support = set(g.objects(finding, URIRef(C + 'supportedByObservation')))
            delivered = support & set(g.objects(bundle, URIRef(C + 'includesObservation')))
            ambient = all_obs
            # The frozen R4 replay explicitly anchors ambient candidates to
            # the case event; preserve that evaluation context, not another event.
            if case['rule'] == 'R4' and case.get('window'):
                window = URIRef(case['window'])
                ambient = {o for o in all_obs if (o, URIRef(C + 'observedInEventWindow'), window) in g}
            actual = {pool: evaluate_pool(g, observations, entity, spec)
                      for pool, observations in [('ambient', ambient), ('support', support), ('delivered', delivered)]}
            status = expected_status[case['label']]
            agrees = (actual['support']['status'] == status
                      and actual['delivered']['status'] == status
                      and actual['ambient']['truth'] is frozen['expected_full_graph_truth'])
            rows.append(dict(dataset=dataset['dataset'], case_index=i, rule=case['rule'],
                             expected_status=status, expected_ambient_truth=frozen['expected_full_graph_truth'],
                             actual={pool: {'status': value['status'], 'truth': value['truth']}
                                     for pool, value in actual.items()}, agrees=agrees))
        print(dataset['dataset'] + ': declarative paired replay complete', flush=True)
    assert all(digest(ROOT / path) == value for path, value in hashes.items()), 'frozen input changed'
    assert digest(configs_path) == implementation_hashes['contract'] and digest(checker_path) == implementation_hashes['checker'], 'implementation changed during replay; rerun stable sources'
    report = dict(python=platform.python_version(), frozen_input_sha256=hashes,
                  contract_sha256=implementation_hashes['contract'], checker_sha256=implementation_hashes['checker'],
                  records=len(rows), disagreements=[r for r in rows if not r['agrees']], rows=rows,
                  scope='Paired replay of existing overlapping experiment cohorts, not additional independent findings.',
                  adapter='In-memory company-to-index edges expand the v1 implicit class lookup. R4 ambient pools retain the frozen case event window. Direct pool evaluation uses frozen support and bundle membership; it does not test new bundle-link selection.',
                  limits='Numerical/status parity only. Neither metadata declarations, market source truth, new-domain validity nor v1 source-path output is revalidated by this comparison.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['records', 'disagreements', 'scope']}, indent=2))
    assert not report['disagreements'], 'Paired differences recorded; do not relabel them.'


if __name__ == '__main__':
    run()
