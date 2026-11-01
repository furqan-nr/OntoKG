"""Replay admitted public-release cases, not a new statistical experiment.

Source text is manually transcribed and reviewed separately; this script checks
the supplied models and their exact outputs, not publisher authenticity.
"""
import hashlib
import json
from fractions import Fraction
from itertools import product
from pathlib import Path
from time import perf_counter

from jws_source_certainty import solve, normalize
from jws_source_certainty_oracle import replay, world_oracle
from jws_source_certainty_sat import sat_counterworld, marginal_bound
from jws_source_certainty_certificate import check_certain, check_counterworld


BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'evaluation_jws' / 'source_certainty_application_v1'


def verify_bindings(case, binding, sources):
    """Check all supplied mode values against source transcriptions, not web text."""
    groups = case['model']['groups']
    if len(groups) != 1 or groups[0]['id'] != binding['group']:
        raise ValueError('Reviewed whole-release group changed')
    modes = {m['id']: m for m in groups[0]['modes']}
    links = binding['bindings']
    if len(links) != len(modes) or {b['mode'] for b in links} != set(modes):
        raise ValueError('Incomplete or duplicated source-mode bindings')
    for link in links:
        if link['source'] not in case['source_refs']:
            raise ValueError('Binding uses an undeclared case source')
        raw = sources[link['source']]['raw']
        for key in link['path']:
            raw = raw[key]
        values = modes[link['mode']]['values']
        if set(values) != set(link['roles']):
            raise ValueError('Unbound model role')
        for role, field in link['roles'].items():
            if len(values[role]) != 1 or Fraction(values[role][0]) != Fraction(raw[field]):
                raise ValueError('Model value differs from reviewed source transcription')


def evaluate_case(case):
    data = case['model']
    normalize(data)  # Validate scope before either baseline is invoked.
    count = 1
    for group in data['groups']:
        count *= len(group['modes'])
    if count > 4096:
        raise ValueError('Application replay budget exceeded; no verdict')
    started = perf_counter()
    interval = solve(data)
    decision_seconds = perf_counter() - started
    oracle, sat = world_oracle(data), sat_counterworld(data)
    if not interval['status'] == oracle['status'] == sat['status']:
        raise AssertionError('Independent decisions disagree')
    checker = check_certain if interval['status'] == 'certain-qualified-positive' else check_counterworld
    if not checker(data, interval):
        raise AssertionError('Independent certificate replay failed')
    for answer in (interval, oracle, sat):
        if answer['status'] == 'counterworld' and replay(data, answer['choices'])['positive']:
            raise AssertionError('Claimed counterworld has a positive original witness')
    bound = marginal_bound(data)
    if bound['status'] == 'certain-qualified-positive' and interval['status'] != bound['status']:
        raise AssertionError('Sound marginal bound contradicted exact decision')
    worlds = []
    for mode_ids in product(*([m['id'] for m in g['modes']] for g in data['groups'])):
        choices = dict(zip((g['id'] for g in data['groups']), mode_ids))
        worlds.append({'choices': choices, 'original_binding_replay': replay(data, choices)})
    return {'id': case['id'], 'model': data, 'world_count': count,
            'interval': interval, 'world_oracle': oracle, 'exact_sat': sat,
            'marginal_bound': bound, 'certificate_valid': True,
            'decision_seconds_descriptive_only': decision_seconds,
            'all_declared_worlds': worlds}


def run():
    fixture = OUT / 'cases.json'
    suite = json.loads(fixture.read_text(encoding='utf-8'))
    binding_file = OUT / 'bindings.json'
    bindings = json.loads(binding_file.read_text(encoding='utf-8'))
    sources = {s['id']: s for s in suite['sources']}
    if len(sources) != len(suite['sources']):
        raise ValueError('Duplicate source identity')
    if {c['id'] for c in suite['cases']} != set(bindings['cases']):
        raise ValueError('Cases differ from reviewed binding inventory')
    for check in bindings['cross_checks']:
        def raw_path(path):
            value = sources[path[0]]['raw']
            for key in path[1:]:
                value = value[key]
            return value
        if raw_path(check['left']) != raw_path(check['right']):
            raise ValueError('Repeated publisher vintage disagrees across transcriptions')
    cases, failures, seen = [], [], set()
    for case in suite['cases']:
        cid = case['id']
        if cid in seen:
            raise ValueError('Duplicate application case identity')
        seen.add(cid)
        try:
            verify_bindings(case, bindings['cases'][cid], sources)
            cases.append(evaluate_case(case))
        except Exception as exc:
            failures.append({'id': cid, 'status': 'execution_error_no_verdict',
                             'error_type': type(exc).__name__, 'message': str(exc)})
    paths = [fixture, binding_file, OUT / 'PROTOCOL.md',
             *sorted(Path(__file__).parent.glob('*source_certainty*.py'))]
    hashes = {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in paths}
    result = {'task': 'bounded retrospective published-vintage robustness',
              'not_current_truth_or_deployment': True,
              'source_authentication': 'Manual primary-page transcription reviewed separately; '
                                       'hashes identify local artifacts, not publisher signatures.',
              'no_originality_or_performance_claim': True,
              'hashes': hashes, 'cases': cases, 'failures': failures}
    (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cases': len(cases), 'failures': len(failures),
                      'statuses': {c['id']: c['interval']['status'] for c in cases}}, indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(run())
