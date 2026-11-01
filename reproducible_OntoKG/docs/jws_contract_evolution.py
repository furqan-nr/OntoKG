#!/usr/bin/env python3
"""Bounded CQ3 threshold evolution experiment; writes only evaluation_jws/."""
import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, XSD
from jws_contracts import load_contracts, evaluate_finding

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws' / 'contract_evolution'
C = Namespace('https://w3id.org/ontokg-eq#')


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def rows(graph, query):
    return sorted([list(map(str, row)) for row in graph.query(query)])


def rule_entities(graph, rules):
    block = rules.split('# ---- R3', 1)[1].split('# ---- R4', 1)[0]
    block = block[block.index('PREFIX'):]
    constructed = graph.query(block).graph
    return sorted(set(map(str, constructed.objects(None, C.concernsEntity))))


def oracle(graph, margin):
    """Independent RDF traversal; no SPARQL or contract evaluator."""
    output = []
    def obs(subject, name):
        for observation in graph.subjects(C.isObservationOf, subject):
            if (observation, C.hasMetricName, Literal(name)) in graph:
                for value in graph.objects(observation, C.hasMetricValue):
                    for window in graph.objects(observation, C.observedOverWindow):
                        yield value, window
    for company in graph.subjects(RDF.type, C.Company):
        for cv, cw in obs(company, 'post-report window return %'):
            for sector in graph.objects(company, C.isClassifiedByIndustrySector):
                for sv, sw in obs(sector, 'sector window return %'):
                    for benchmark in graph.subjects(RDF.type, C.MarketIndex):
                        for bv, bw in obs(benchmark, 'benchmark window return %'):
                            if cw == sw == bw and Decimal(str(cv)) > Decimal(str(sv)) + margin and Decimal(str(cv)) > Decimal(str(bv)) + margin:
                                output.append([str(company), str(cv), str(sv), str(bv)])
    return sorted(output)


def fixtures():
    graph = Graph()
    graph.add((C.fixture_sector, RDF.type, C.IndustrySectorClassifier))
    graph.add((C.fixture_benchmark, RDF.type, C.MarketIndex))
    cases = [('below_old', '-0.1', False, False), ('equal_old', '0', False, False),
             ('inside_margin', '0.5', True, False), ('equal_new', '1', True, False),
             ('above_new', '1.01', True, True)]
    def add(subject, name, value):
        node = C['fixture_obs_' + str(len(graph))]
        for predicate, obj in [(C.isObservationOf, subject), (C.hasMetricName, Literal(name)),
                               (C.hasMetricValue, Literal(value, datatype=XSD.decimal)),
                               (C.observedOverWindow, C.fixture_window)]:
            graph.add((node, predicate, obj))
    add(C.fixture_sector, 'sector window return %', '0')
    add(C.fixture_benchmark, 'benchmark window return %', '0')
    for label, value, _, _ in cases:
        company = C['fixture_' + label]
        graph.add((company, RDF.type, C.Company))
        graph.add((company, C.isClassifiedByIndustrySector, C.fixture_sector))
        add(company, 'post-report window return %', value)
    return graph, cases


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = load_contracts()
    query_path = ROOT / manifest['R3']['query']
    old_query = query_path.read_text(encoding='utf-8')
    old_filter = 'FILTER(?companyReturn > ?sectorReturn && ?companyReturn > ?benchmarkReturn)'
    assert old_query.count(old_filter) == 1
    new_query = old_query.replace(old_filter, 'FILTER(?companyReturn > (?sectorReturn + 1.0) && ?companyReturn > (?benchmarkReturn + 1.0))')
    old_rules = (ROOT / manifest['artifacts']['documented_rules']).read_text(encoding='utf-8')
    rule_filter = 'FILTER(?cret > ?sret && ?cret > ?bret)'
    assert old_rules.count(rule_filter) == 1
    new_rules = old_rules.replace(rule_filter, 'FILTER(?cret > (?sret + 1.0) && ?cret > (?bret + 1.0))')
    (OUT / 'CQ3_v1.rq').write_text(old_query, encoding='utf-8')
    (OUT / 'CQ3_v2.rq').write_text(new_query, encoding='utf-8')
    (OUT / 'inference_rules_v1.rq').write_text(old_rules, encoding='utf-8')
    (OUT / 'inference_rules_v2.rq').write_text(new_rules, encoding='utf-8')
    contracts = []
    for version, margin, query, rules in [('v1', 0, old_query, old_rules), ('v2', 1, new_query, new_rules)]:
        spec = deepcopy(manifest['R3'])
        spec['margin'] = float(margin)
        contract = {'cq': 'CQ3', 'version': version, 'margin_percentage_points': margin, 'replay_spec': spec,
                    'operator': 'strictly_greater_than_both', 'query_sha256': digest(query),
                    'rules_sha256': digest(rules), 'shape_sha256': digest((ROOT / 'shacl/shapes.ttl').read_bytes()),
                    'required_metrics': ['post-report window return %', 'sector window return %', 'benchmark window return %'],
                    'period_constraint': 'identical_window', 'entity_constraint': 'company_sector_and_market_index'}
        encoded = json.dumps(contract, indent=2, sort_keys=True) + '\n'
        (OUT / f'CQ3_contract_{version}.json').write_text(encoded, encoding='utf-8')
        contracts.append({'version': version, 'contract_sha256': digest(encoded), **contract})
    report = {'scope': 'Bounded, explicitly declared CQ3 threshold scenario; not general change-impact inference.',
              'manifest_sha256': digest((ROOT / 'contracts/cq_contracts.json').read_bytes()),
              'declared_dependencies': {'query': manifest['R3']['query'], **manifest['artifacts']},
              'impact': {'changed': ['R3 contract margin', manifest['R3']['query'], manifest['artifacts']['documented_rules']],
                         'production_followup_required': [manifest['artifacts']['rules']],
                         'unchanged_for_this_threshold_only_scenario': [manifest['artifacts'][k] for k in ['builder', 'shapes', 'ontology']],
                         'method': 'Select paths from the declared manifest, then classify this known threshold edit explicitly. No automatic dependency discovery.'},
              'contracts': contracts, 'market_results': [], 'synthetic_fixtures': {},
              'stale_pair_detected': digest(old_query) != contracts[1]['query_sha256']}
    for market in ['psx', 'msx', 'idx']:
        path = ROOT / f'data/demo_{market}_inferred.ttl'
        graph = Graph().parse(path)
        old = rows(graph, old_query)
        new = rows(graph, new_query)
        assert old == oracle(graph, Decimal(0))
        assert new == oracle(graph, Decimal(1))
        assert rule_entities(graph, old_rules) == sorted({row[0] for row in old})
        assert rule_entities(graph, new_rules) == sorted({row[0] for row in new})
        replay = []
        for finding in graph.subjects(C.derivedByRule, Literal('R3')):
            old_result = evaluate_finding(graph, finding, contract=contracts[0]['replay_spec'])
            new_result = evaluate_finding(graph, finding, contract=contracts[1]['replay_spec'])
            entity = str(next(graph.objects(finding, C.concernsEntity)))
            replay.append({'finding': str(finding), 'v1': old_result, 'v2': new_result,
                           'v1_support_matches_query_truth': old_result['sufficient_witness'] == (entity in {row[0] for row in old}),
                           'v2_support_matches_query_truth': new_result['sufficient_witness'] == (entity in {row[0] for row in new})})
        assert all(item['v1_support_matches_query_truth'] and item['v2_support_matches_query_truth'] for item in replay)
        regressions = {}
        for cq in [1, 2, 4]:
            text = (ROOT / f'queries/CQ{cq}_CASE_01.rq').read_text(encoding='utf-8')
            before = rows(graph, text)
            # The new CQ3 query operates read-only; rerun each unchanged CQ.
            after = rows(graph, text)
            assert before == after
            regressions[f'CQ{cq}'] = {'query_sha256': digest(text), 'rows': before, 'unchanged': True}
        assert rows(graph, (OUT / 'CQ3_v1.rq').read_text(encoding='utf-8')) == old
        report['market_results'].append({'market': market, 'graph_sha256': digest(path.read_bytes()),
                                         'v1_rows': old, 'v2_rows': new, 'oracle_matches_both': True,
                                         'documented_construct_rule_matches_both': True,
                                         'archived_finding_support_replay': replay,
                                         'v1_replay_matches': True, 'unchanged_cq_regressions': regressions})
    graph, cases = fixtures()
    graph.serialize(OUT / 'synthetic_boundary_fixture.ttl', format='turtle')
    old, new = rows(graph, old_query), rows(graph, new_query)
    assert old == oracle(graph, Decimal(0)) and new == oracle(graph, Decimal(1))
    assert rule_entities(graph, old_rules) == sorted({row[0] for row in old})
    assert rule_entities(graph, new_rules) == sorted({row[0] for row in new})
    assert {r[0] for r in old} == {str(C['fixture_' + n]) for n, _, yes, _ in cases if yes}
    assert {r[0] for r in new} == {str(C['fixture_' + n]) for n, _, _, yes in cases if yes}
    report['synthetic_fixtures'] = {'label': 'Synthetic analytical boundary cases, not market findings',
                                  'cases': [{'name': n, 'company_return_percent': v, 'expected_v1': a, 'expected_v2': b} for n, v, a, b in cases],
                                  'v1_rows': old, 'v2_rows': new, 'oracle_matches_both': True}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    summary = ['# Bounded CQ3 contract evolution', '',
               'Change: strict outperformance over both comparators becomes strict outperformance by more than 1 percentage point.', '',
               'The query and documented rule variants are derived by replacing their original FILTERs. Production code and source graphs remain unchanged. The manifest supplies artifact paths; impact classification is explicit for this bounded edit and is not a general inference mechanism.', '',
               '| Snapshot | Original selected rows | Changed selected rows | Oracle and archived-query replay |',
               '|---|---:|---:|---|']
    for item in report['market_results']:
        summary.append(f"| {item['market']} | {len(item['v1_rows'])} | {len(item['v2_rows'])} | Pass |")
    summary += ['', 'CQ1, CQ2 and CQ4 return identical rows before and after read-only CQ3 execution on each unchanged snapshot. These are read-only same-snapshot controls, not a broad regression or change-impact proof. Query, rule, contract, shape and graph hashes are recorded in report.json. An old query paired with the new contract fails the query-hash match.', '',
                'Synthetic boundary fixtures select 3 companies under the original condition and 1 under the new condition. These are test cases, not market findings. Exact thresholds are excluded because both conditions use strict greater-than.', '',
                'Support-only replay results are also recorded separately. Disagreement with full-query selection means the archived finding supports do not meet the typed contract; it is not silently counted as successful replay.', '',
                'Limitations: no production rematerialization, source verification, general change-impact inference, or proof of upstream metric correctness. Rule artifacts are versioned but the main production inference implementation would require a corresponding reviewed update before adopting v2.']
    (OUT / 'README.md').write_text('\n'.join(summary) + '\n', encoding='utf-8')
    print(json.dumps({'markets': [(x['market'], len(x['v1_rows']), len(x['v2_rows'])) for x in report['market_results']],
                      'synthetic_counts': [len(old), len(new)], 'stale_pair_detected': report['stale_pair_detected']}))


if __name__ == '__main__':
    main()
