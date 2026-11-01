"""Frozen synthetic gap-cover benchmark, not observed source uncertainty."""
import hashlib
import json
from pathlib import Path
from statistics import median
from time import perf_counter
from jws_source_certainty import solve
from jws_source_certainty_oracle import replay, world_oracle
from jws_source_certainty_sat import sat_counterworld, marginal_bound
from jws_source_certainty_certificate import check_counterworld, check_certain

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'evaluation_jws' / 'source_coherent_certainty_v1'


def family(k, r, remove):
    groups = [{'id': 'anchor', 'modes': [{'id': 'fixed', 'values': {'C': ['-0.5'], 'S0': [str(k) + '.5']}}]}]
    for g in range(k + 1):
        if remove and g == k // 2:
            continue
        # Gap (g-.6,g+.6) covers anchor together with adjacent gaps.
        from fractions import Fraction
        groups.append({'id': 'gap' + str(g), 'modes': [
            {'id': 'left', 'values': {'S0': [str(Fraction(g) - Fraction(3, 5))]}},
            {'id': 'right', 'values': {'C': [str(Fraction(g) + Fraction(3, 5))]}}]})
    if r == 2:
        groups.append({'id': 'fixed-benchmark', 'modes': [
            {'id': 'fixed', 'values': {'S1': ['-1000']}}]})
    return {'entity': 'synthetic', 'window': 'fixed', 'pool': 'delivered',
            'margins': ['0'] * r, 'groups': groups}


def run():
    results = []
    for k in (4, 8, 16, 32, 64):
        for r in (1, 2):
            for remove in (False, True):
                trials = []
                for repetition in range(3):
                    started = perf_counter(); data = family(k, r, remove)
                    construction = perf_counter() - started
                    worlds = 1
                    for g in data['groups']: worlds *= len(g['modes'])
                    started = perf_counter(); result = solve(data)
                    interval_seconds = perf_counter() - started
                    sat = sat_counterworld(data)
                    bound = marginal_bound(data)
                    if result['status'] != sat['status']:
                        raise AssertionError('SAT disagreement')
                    expected = 'counterworld' if remove else 'certain-qualified-positive'
                    if result['status'] != expected:
                        raise AssertionError('Family construction did not match frozen expectation')
                    started = perf_counter()
                    for answer in (result, sat):
                        if answer['status'] == 'counterworld' and replay(data, answer['choices'])['positive']:
                            raise AssertionError('Invalid counterworld')
                    replay_seconds = perf_counter() - started
                    # Independent execution-certificate checker is timed separately.
                    started = perf_counter()
                    valid = check_counterworld(data, result) if remove else check_certain(data, result)
                    if not valid: raise AssertionError('Execution certificate failed')
                    certificate_seconds = perf_counter() - started
                    oracle = world_oracle(data) if worlds <= 4096 else {'status': 'not_run_product_budget'}
                    if worlds <= 4096 and oracle['status'] != result['status']:
                        raise AssertionError('World oracle disagreement')
                    trials.append({'repetition': repetition, 'construction_seconds': construction,
                                   'interval_seconds': interval_seconds, 'sat': sat,
                                   'replay_seconds': replay_seconds, 'world_oracle': oracle})
                    trials[-1]['certificate_check_seconds'] = certificate_seconds
                    trials[-1]['marginal_bound'] = bound
                results.append({'k': k, 'comparators': r, 'interior_gap_removed': remove,
                                'groups': len(data['groups']), 'world_product': str(worlds),
                                'status': result['status'], 'input_size': result['input_size'],
                                'interval_median_seconds': median(t['interval_seconds'] for t in trials),
                                'sat_median_seconds': median(t['sat']['total_seconds'] for t in trials),
                                'trials': trials})
    hashes = {}
    for path in [OUT / 'PROTOCOL.md', *sorted((BASE / 'docs').glob('*source_certainty*.py'))]:
        hashes[str(path.relative_to(BASE))] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {'protocol': 'PROTOCOL.md', 'synthetic_only': True,
               'no_priority_or_practitioner_benefit_claim': True,
               'hashes': hashes, 'families': results, 'failures': []}
    OUT.mkdir(exist_ok=True, parents=True)
    (OUT / 'results.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'families': len(results), 'trials': sum(len(x['trials']) for x in results),
                      'output': str(OUT / 'results.json')}, indent=2))


if __name__ == '__main__': run()
