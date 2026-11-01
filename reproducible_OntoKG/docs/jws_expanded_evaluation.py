"""Bounded exhaustive graph oracle; no production rule functions imported.

Natural graph cohorts and deliberately synthetic branch/boundary cases are
reported separately. Absence is unknown, never a negative label. This oracle
checks stored observations, not source truth or financial computations.
"""
import hashlib
import argparse
import itertools
import json
import platform
from collections import Counter
from decimal import Decimal
from pathlib import Path
from rdflib import Graph, Literal, RDF, URIRef
from pyoxigraph import Store, RdfFormat
from jws_contracts import C, PROV, ROOT, evaluate_finding

# Versioned output preserves the frozen v1 sampling ledger and experiment graphs.
OUT = ROOT / 'evaluation_jws/expanded_evaluation_v2'
METRICS = {
    'growth': 'YoY profit growth %', 'company': 'post-report window return %',
    'benchmark': 'benchmark window return %', 'sector': 'sector window return %',
    'correlation': 'FX vs company return correlation',
    'event_return': 'cumulative abnormal return %', 'volume': 'abnormal volume ratio'}
ROLES = {'R1': ['growth', 'company', 'benchmark'], 'R3': ['company', 'sector', 'benchmark'],
         'R2': ['correlation'], 'R4': ['event_return', 'volume']}


def values(g, entity, role):
    """Direct RDF traversal independent of contract candidate/replay functions."""
    answer = []
    for obs in g.subjects(C.isObservationOf, entity):
        if Literal(METRICS[role]) not in set(g.objects(obs, C.hasMetricName)):
            continue
        for raw in g.objects(obs, C.hasMetricValue):
            number = Decimal(str(raw))
            if not number.is_finite():
                continue
            predicate = C.observedInEventWindow if role in {'event_return', 'volume'} else C.observedOverWindow
            windows = list(g.objects(obs, predicate)) if role not in {'growth', 'correlation'} else [None]
            answer.extend((obs, number, w) for w in windows)
    return sorted(set(answer), key=str)


def oracle_cases(g, dataset):
    companies = sorted(set(g.subjects(RDF.type, C.Company)), key=str)
    indexes = list(g.subjects(RDF.type, C.MarketIndex))
    result = []
    for company in companies:
        candidates = {r: values(g, company, r) for r in ['growth', 'company', 'correlation', 'event_return', 'volume']}
        candidates['benchmark'] = [x for e in indexes for x in values(g, e, 'benchmark')]
        candidates['sector'] = [x for e in g.objects(company, C.isClassifiedByIndustrySector) for x in values(g, e, 'sector')]
        for rid in ['R1', 'R3', 'R2']:
            roles = ROLES[rid]
            tuples = list(itertools.product(*(candidates[r] for r in roles)))
            tuples = [t for t in tuples if len({x[2] for x in t if x[2] is not None}) <= 1]
            if not tuples:
                result.append({'dataset': dataset, 'company': str(company), 'rule': rid, 'label': 'incomplete',
                               'observations': {r + str(i): str(x[0]) for r in roles for i, x in enumerate(candidates[r])}, 'window': None})
            for t in tuples:
                v = {r: x[1] for r, x in zip(roles, t)}
                truth = v['growth'] > 0 and v['company'] < v['benchmark'] if rid == 'R1' else v['company'] > v['sector'] and v['company'] > v['benchmark'] if rid == 'R3' else abs(v['correlation']) >= Decimal('.3')
                result.append({'dataset': dataset, 'company': str(company), 'rule': rid, 'label': 'positive' if truth else 'negative', 'observations': {r: str(x[0]) for r, x in zip(roles, t)}, 'values': {r: str(x[1]) for r, x in zip(roles, t)}, 'window': next((str(x[2]) for x in t if x[2] is not None), None)})
        event_windows = {x[2] for r in ['event_return', 'volume'] for x in candidates[r]}
        if not event_windows:
            result.append({'dataset': dataset, 'company': str(company), 'rule': 'R4', 'label': 'not_applicable_no_event_observations', 'observations': {}, 'window': None})
        for window in sorted(event_windows, key=str):
            observations = {r: [x for x in candidates[r] if x[2] == window] for r in ['event_return', 'volume']}
            passing = []
            for r, threshold in [('event_return', Decimal('2')), ('volume', Decimal('1.5'))]:
                if any((abs(x[1]) if r == 'event_return' else x[1]) >= threshold for x in observations[r]):
                    passing.append(r)
            label = 'positive' if passing else 'negative' if all(observations.values()) else 'incomplete'
            # All available event observations are contextual; one passing branch is enough.
            result.append({'dataset': dataset, 'company': str(company), 'rule': 'R4', 'label': label,
                           'observations': {r + str(i): str(x[0]) for r, xs in observations.items() for i, x in enumerate(xs)},
                           'window': str(window), 'passing_branches': passing})
    return companies, result


def materialize(g, case, number):
    finding = URIRef(f'https://w3id.org/ontokg-eq/expanded/{case["dataset"]}/{number}')
    bundle = URIRef(str(finding) + '_bundle')
    entity = URIRef(case['company'])
    for triple in [(finding, RDF.type, C.AnalyticalFinding), (finding, C.derivedByRule, Literal(case['rule'])),
                   (finding, C.concernsEntity, entity), (bundle, RDF.type, C.EvidenceBundle),
                   (bundle, C.explainsResultEntity, entity)]:
        g.add(triple)
    for obs in case['observations'].values():
        g.add((finding, C.supportedByObservation, URIRef(obs)))
        g.add((bundle, C.includesObservation, URIRef(obs)))
    if case['rule'] == 'R4' and case.get('window'):
        g.add((finding, C.observedInEventWindow, URIRef(case['window'])))
    return finding, bundle


def query_comparison(g, cases, rule):
    """Compare entire SELECT result sets incl numerical bindings, not only IDs."""
    query = (ROOT / f'queries/CQ{rule[1]}_CASE_01.rq').read_text(encoding='utf-8')
    roles = ROLES[rule]
    expected = {(c['company'], *(Decimal(c['values'][r]) for r in roles)) for c in cases if c['rule'] == rule and c['label'] == 'positive'}
    # CQ1 selects company, growth, company return, benchmark; CQ3 likewise roles order.
    # Execute original query, unbound, on the entire graph in an independent engine.
    store = Store()
    store.load(input=g.serialize(format='turtle').encode(), format=RdfFormat.TURTLE)
    actual = {(row[0].value, *(Decimal(v.value) for v in list(row)[1:])) for row in store.query(query)}
    return {'rule': rule, 'expected_distinct_rows': len(expected), 'actual_distinct_rows': len(actual),
            'false_positive_rows': len(actual - expected), 'false_negative_rows': len(expected - actual),
            'recall': len(actual & expected) / len(expected) if expected else None,
            'exact_set_agreement': actual == expected, 'execution': 'Oxigraph original unbound SELECT over entire input graph'}


def categorical_replay(case, checked):
    """Keep unknown distinct from false; source authentication is a separate output.

    R4 accepts a passing OR branch alone. A false R4 requires both branches
    available in one window; a missing nonpassing branch leaves truth unknown.
    """
    label = case['label']
    expected_status = {'positive': 'sufficient', 'negative': 'predicate_false',
                       'incomplete': 'incomplete_bundle'}[label]
    expected_truth = {'positive': True, 'negative': False, 'incomplete': None}[label]
    return {'gold_label': label, 'expected_bundle_status': expected_status,
            'bundle_status': checked['bundle_status'],
            'bundle_sufficient': checked['bundle_sufficient'],
            'expected_full_graph_truth': expected_truth,
            'full_graph_truth': checked['full_graph_truth'],
            'agrees': checked['bundle_sufficient'] == (label == 'positive'),
            'categorical_status_agrees': checked['bundle_status'] == expected_status,
            'full_graph_truth_agrees': checked['full_graph_truth'] is expected_truth}


def evaluate_dataset(path, name, output_dir=OUT):
    print('Loading ' + name, flush=True)
    graph = Graph().parse(path)
    companies, cases = oracle_cases(graph, name)
    print(f'{name}: {len(companies)} companies, {len(cases)} oracle cases; querying', flush=True)
    queries = [query_comparison(graph, cases, r) for r in ['R1', 'R3']]
    print(name + ': SELECT comparisons done; replaying', flush=True)
    experiment = Graph()
    for triple in graph:
        experiment.add(triple)
    replay, withheld = [], []
    current_company, replay_graph = None, None
    metric_subjects = set(graph.subjects(C.hasMetricName, None))
    for i, case in enumerate(cases):
        if case['label'].startswith('not_applicable'):
            continue
        if current_company != case['company']:
            current_company = case['company']
            company = URIRef(current_company)
            targets = {company} | set(graph.objects(company, C.isClassifiedByIndustrySector)) | set(graph.subjects(RDF.type, C.MarketIndex))
            allowed = {o for target in targets for o in graph.subjects(C.isObservationOf, target)
                       if any(str(m) in METRICS.values() for m in graph.objects(o, C.hasMetricName))}
            retained = targets | allowed
            retained |= {w for o in allowed for p in [C.observedOverWindow, C.observedInEventWindow] for w in graph.objects(o, p)}
            retained |= {cell for o in allowed for cell in graph.objects(o, PROV.wasDerivedFrom)}
            retained |= {source for cell in list(retained) for source in graph.objects(cell, PROV.hadPrimarySource)}
            replay_graph = Graph()
            for subject in retained:
                for predicate, obj in graph.predicate_objects(subject):
                    replay_graph.add((subject, predicate, obj))
        finding, bundle = materialize(experiment, case, i)
        materialize(replay_graph, case, i)
        checked = evaluate_finding(replay_graph, finding)
        replay.append({'case_index': i, **categorical_replay(case, checked)})
        if case['label'] == 'positive':
            # Remove one whole deciding role. OR branches are tested singly below; removing
            # one branch from a two-branch R4 witness must not be labelled an error.
            for role in ROLES[case['rule']]:
                role_obs = [o for r, o in case['observations'].items() if r == role or (case['rule'] == 'R4' and r.startswith(role))]
                for obs in role_obs:
                    replay_graph.remove((bundle, C.includesObservation, URIRef(obs)))
                changed = evaluate_finding(replay_graph, finding)
                expected_remaining = case['rule'] == 'R4' and any(r != role for r in case['passing_branches'])
                withheld.append({'case_index': i, 'withheld_role': role, 'bundle_sufficient': changed['bundle_sufficient'],
                                 'expected_remaining_sufficient': expected_remaining,
                                 'agrees': changed['bundle_sufficient'] == expected_remaining,
                                 'full_graph_truth': changed['full_graph_truth']})
                for obs in role_obs:
                    replay_graph.add((bundle, C.includesObservation, URIRef(obs)))
    experiment.serialize(output_dir / f'{name}.experiment.ttl', format='turtle')
    print(name + ': replay complete', flush=True)
    return {'dataset': name, 'input': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'companies': len(companies), 'cases': cases, 'counts': dict(Counter(c['label'] for c in cases)),
            'rule_counts': {r: dict(Counter(c['label'] for c in cases if c['rule'] == r)) for r in ROLES},
            'distinct_company_rule_window_cases': len({(c['company'], c['rule'], c['window']) for c in cases}),
            'distinct_nonnull_windows': len({c['window'] for c in cases if c['window'] is not None}),
            'distinct_tested_metric_observations': len({o for c in cases for o in c['observations'].values()}),
            'declared_observation_units': dict(Counter(str(u) for o in metric_subjects for u in graph.objects(o, C.hasUnit))),
            'replay': replay, 'withheld': withheld, 'query_comparison': queries,
            'all_replay_agrees': all(x['agrees'] for x in replay),
            'all_categorical_status_agrees': all(x['categorical_status_agrees'] for x in replay),
            'all_full_graph_truth_agrees': all(x['full_graph_truth_agrees'] for x in replay),
            'all_withheld_agrees': all(x['agrees'] for x in withheld)}


def synthetic_cases():
    """Purpose-built fixture, never presented as independent natural findings."""
    specs = [('return_only_boundary', '2', None, True), ('volume_only_boundary', None, '1.5', True),
             ('both_alternative_witnesses', '2', '1.5', True), ('both_below', '1.999', '1.499', False),
             ('negative_return_boundary', '-2', None, True), ('missing_nonpassing_other', '1', None, False),
             ('no_evidence', None, None, False)]
    results = []
    for name, ret, vol, expected in specs:
        graph = Graph()
        entity, window = URIRef('urn:synthetic:company'), URIRef('urn:synthetic:event')
        graph.add((entity, RDF.type, C.Company)); graph.add((window, RDF.type, C.EventWindow))
        observations = {}
        for role, value in [('event_return', ret), ('volume', vol)]:
            if value is None:
                continue
            obs = URIRef('urn:synthetic:' + role)
            for t in [(obs, RDF.type, C.Observation), (obs, C.isObservationOf, entity),
                      (obs, C.hasMetricName, Literal(METRICS[role])), (obs, C.hasMetricValue, Literal(Decimal(value))),
                      (obs, C.observedInEventWindow, window)]:
                graph.add(t)
            observations[role] = str(obs)
        case = {'dataset': 'synthetic', 'company': str(entity), 'rule': 'R4', 'observations': observations}
        finding, bundle = materialize(graph, case, name)
        report = evaluate_finding(graph, finding)
        branch_checks = []
        if name == 'both_alternative_witnesses':
            for role, obs in observations.items():
                other = next(o for r, o in observations.items() if r != role)
                graph.remove((bundle, C.includesObservation, URIRef(other)))
                branch_checks.append({'retained_branch': role, 'sufficient': evaluate_finding(graph, finding)['bundle_sufficient']})
                graph.add((bundle, C.includesObservation, URIRef(other)))
        results.append({'name': name, 'expected_sufficient': expected, 'actual_sufficient': report['bundle_sufficient'], 'agrees': expected == report['bundle_sufficient'], 'branch_checks': branch_checks})
    for name, rid, metrics, expected in [
        ('R1_zero_growth', 'R1', {'growth': '0', 'company': '1', 'benchmark': '2'}, False),
        ('R1_equal_returns', 'R1', {'growth': '1', 'company': '2', 'benchmark': '2'}, False),
        ('R3_equal_sector', 'R3', {'company': '2', 'sector': '2', 'benchmark': '1'}, False),
        ('R3_decimal_strict_positive', 'R3', {'company': '2.0000000001', 'sector': '2', 'benchmark': '2'}, True)]:
        graph = Graph()
        entity, sector, benchmark, window = map(URIRef, ['urn:synthetic:company', 'urn:synthetic:sector', 'urn:synthetic:benchmark', 'urn:synthetic:window'])
        for subject, kind in [(entity, C.Company), (sector, C.IndustrySectorClassifier), (benchmark, C.MarketIndex), (window, C.AnalysisWindow)]:
            graph.add((subject, RDF.type, kind))
        graph.add((entity, C.isClassifiedByIndustrySector, sector))
        observations = {}
        for role, value in metrics.items():
            obs = URIRef('urn:synthetic:' + role)
            target = sector if role == 'sector' else benchmark if role == 'benchmark' else entity
            for triple in [(obs, RDF.type, C.Observation), (obs, C.isObservationOf, target),
                           (obs, C.hasMetricName, Literal(METRICS[role])), (obs, C.hasMetricValue, Literal(Decimal(value)))]:
                graph.add(triple)
            if role != 'growth':
                graph.add((obs, C.observedOverWindow, window))
            observations[role] = str(obs)
        finding, _ = materialize(graph, {'dataset':'synthetic', 'company':str(entity), 'rule':rid, 'observations':observations}, name)
        report = evaluate_finding(graph, finding)
        results.append({'name':name,'expected_sufficient':expected,'actual_sufficient':report['bundle_sufficient'],'agrees':expected == report['bundle_sufficient'],'branch_checks':[]})
    return results


def run(output_dir=OUT):
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [('psx_curated', ROOT / 'data/demo_psx_inferred.ttl'), ('msx_curated', ROOT / 'data/demo_msx_inferred.ttl'),
             ('idx_curated', ROOT / 'data/demo_idx_inferred.ttl'), ('idx_scaled_archived', ROOT / 'data/demo_idx_scaled.ttl')]
    # Corrected cohorts supplied by separate audit are included only when present.
    paths.extend((p.stem, p) for p in sorted((ROOT / 'evaluation_jws/financial_v2').glob('demo_*_financial_v2.ttl')))
    datasets = [evaluate_dataset(p, n, output_dir) for n, p in paths]
    synthetic = synthetic_cases()
    report = {'runtime': platform.python_version(), 'oracle_scope': 'Stored RDF numerical tuples; independent traversal and Decimal predicate arithmetic, no production rule functions. No manual source oracle or source accuracy claim.',
              'cohort_overlap': 'Curated IDX is a subset of scaled IDX; original and corrected graphs are paired versions, not independent extra companies. Do not sum across datasets as independent sample size.',
              'r2_scope': 'R2 classification only, not full CQ2 (benchmark correlation and FX change).',
              'event_scope': 'No event observations = not applicable; not a negative. Curated events evaluated separately from scaled cohort.',
              'datasets': datasets, 'synthetic': synthetic}
    report['categorical_convention'] = 'Positive=sufficient/True; negative=predicate_false/False; incomplete=incomplete_bundle/None. R4 OR accepts one passing branch, but a negative requires both same-window branches. Source paths do not determine numerical truth.'
    report['categorical_disagreements'] = [{'dataset': d['dataset'], **r} for d in datasets for r in d['replay'] if not r['categorical_status_agrees'] or not r['full_graph_truth_agrees']]
    (output_dir / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = ['# Expanded bounded contract evaluation', '', report['oracle_scope'], '', report['cohort_overlap'], '',
             '| Cohort | Companies | Positive | Negative | Incomplete | No event applicable | Replay agrees |', '|---|---:|---:|---:|---:|---:|---|']
    for d in datasets:
        c = d['counts']
        lines.append(f"| {d['dataset']} | {d['companies']} | {c.get('positive',0)} | {c.get('negative',0)} | {c.get('incomplete',0)} | {c.get('not_applicable_no_event_observations',0)} | {d['all_replay_agrees']} |")
    lines.extend(['', 'CQ1/CQ3 comparisons enumerate all eligible graph tuples, compare entire distinct SELECT numerical rows, and report false positives and negatives in results.json. Unknown inputs remain incomplete. R2 is classification only; events are not implied for scaled companies.', '',
                  'Experiment TTL files contain the unchanged source triples plus explicitly constructed candidate findings/bundles for each positive, negative, or incomplete case. These are evaluation fixtures, not newly observed production findings. Positives are oracle-selected independently of stored production findings. Contract replay must reject negative/incomplete evidence. Withheld tests remove complete deciding roles from actual bundles and retain full graph observations. R4 can remain sufficient when its other OR branch passes.', '',
                  'Replay uses a company-specific projection retaining every relevant contract-metric observation for that company, its sectors, and market indexes, plus their entity/window types, links, dependency cells, and primary-source triples. The oracle runs on the complete graph. Oxigraph executes the original unbound SELECT text on the entire input graph. Serialized experiment graphs retain complete inputs.', '',
                  'Eleven synthetic cases include seven R4 cases checking exact inclusive boundaries, missing evidence, negative-return magnitude, and disjoint alternative OR witnesses, plus four R1/R3 strict Decimal boundaries. Their counts are separate from natural cohorts.', '',
                  'Units and upstream metric validity are not certified by this graph-level test. The corrected financial_v2 cohorts are paired sensitivity/repair comparisons. No claims about human audit performance follow from automated replay.', '',
                  'Reproduce: Python 3.13 with .jws_deps on PYTHONPATH; run docs/jws_expanded_evaluation.py.'])
    lines.extend(['', report['categorical_convention'], '', f"Categorical/full-graph disagreements: {len(report['categorical_disagreements'])}. These are reported independently of binary sufficiency agreement."])
    (output_dir / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    assert all(d['all_replay_agrees'] and d['all_withheld_agrees'] and all(q['exact_set_agreement'] for q in d['query_comparison']) for d in datasets)
    assert all(r['agrees'] and all(x['sufficient'] for x in r['branch_checks']) for r in synthetic)
    assert not report['categorical_disagreements'], 'Categorical disagreements retained in results.json; do not relabel unknown as false.'
    print(json.dumps([{k: d[k] for k in ['dataset','companies','counts','all_replay_agrees','query_comparison']} for d in datasets], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=OUT)
    run(parser.parse_args().output_dir)
