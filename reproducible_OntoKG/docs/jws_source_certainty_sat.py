"""Independent exact Boolean pair-conflict baseline, compilation included.

For each failed comparator, forbid simultaneous selection of modes supplying a
positive centre/comparator pair. No interval helpers or extrema are imported.
Multiple comparators are independent SAT alternatives (logical OR of failure).
"""
from fractions import Fraction
from itertools import combinations
from time import perf_counter
from sympy import Symbol, And, Or, Not, false
from sympy.logic.inference import satisfiable


def marginal_bound(data):
    """Sound but incomplete independent aggregate-envelope abstraction.

    Independently minimizes the world's max(C) and maximizes its min(S_j).
    Their simultaneous attainability is NOT assumed. A failed bound is only
    undetermined; it is never a negative verdict or an invented counterworld.
    """
    started = perf_counter()
    center_lowers = []
    for group in data['groups']:
        per_mode = [max(Fraction(c) for c in m['values']['C'])
                    if m['values'].get('C') else None for m in group['modes']]
        if all(v is not None for v in per_mode):
            center_lowers.append(min(per_mode))
    lower = max(center_lowers) if center_lowers else None
    guaranteed = lower is not None
    for j, delta in enumerate(data['margins']):
        upper_candidates = []
        for group in data['groups']:
            per_mode = [min(Fraction(s) for s in m['values']['S' + str(j)])
                        if m['values'].get('S' + str(j)) else None for m in group['modes']]
            if all(v is not None for v in per_mode):
                upper_candidates.append(max(per_mode))
        upper = min(upper_candidates) if upper_candidates else None
        guaranteed = guaranteed and upper is not None and lower > upper + Fraction(delta)
    return {'status': 'certain-qualified-positive' if guaranteed else 'undetermined',
            'total_seconds': perf_counter() - started}


def sat_counterworld(data):
    started = perf_counter()
    groups = data['groups']
    flat = [(gi, mi, m) for gi, g in enumerate(groups) for mi, m in enumerate(g['modes'])]
    if len(flat) > 10000:
        raise RuntimeError('SAT variable budget exceeded; no verdict')
    base_clause_count = sum(1 + len(g['modes']) * (len(g['modes']) - 1) // 2 for g in groups)
    if base_clause_count > 1000000:
        raise RuntimeError('SAT exactly-one clause budget exceeded; no verdict')
    variables = {(gi, mi): Symbol('g%d_m%d' % (gi, mi)) for gi, mi, _ in flat}
    base = []
    for gi, g in enumerate(groups):
        vs = [variables[gi, mi] for mi in range(len(g['modes']))]
        base.append(Or(*vs))
        base.extend(Or(Not(a), Not(b)) for a, b in combinations(vs, 2))
    compile_seconds = perf_counter() - started
    solve_seconds = 0.0
    nchecks = nclauses = 0
    for j, raw_delta in enumerate(data['margins']):
        compile_start = perf_counter()
        delta = Fraction(raw_delta)
        forbidden, pair_conflicts = set(), set()
        for gi, mi, mode_c in flat:
            centers = mode_c['values'].get('C', [])
            if not centers:
                continue
            for hi, ni, mode_s in flat:
                if gi == hi and mi != ni:
                    continue  # Mutually exclusive modes cannot coexist.
                comparators = mode_s['values'].get('S' + str(j), [])
                conflict = False
                for c in centers:
                    for s in comparators:
                        nchecks += 1
                        if nchecks > 1000000:
                            raise RuntimeError('SAT pair-check budget exceeded; no verdict')
                        if Fraction(c) > Fraction(s) + delta:
                            conflict = True
                            break
                    if conflict:
                        break
                if conflict:
                    if gi == hi:
                        forbidden.add((gi, mi))
                    else:
                        pair_conflicts.add(tuple(sorted(((gi, mi), (hi, ni)))))
        # Local impossibilities propagated before building inter-group clauses.
        clauses = list(base) + [Not(variables[k]) for k in sorted(forbidden)]
        clauses.extend(Or(Not(variables[a]), Not(variables[b]))
                       for a, b in sorted(pair_conflicts) if a not in forbidden and b not in forbidden)
        nclauses += len(clauses)
        if nclauses > 1000000:
            raise RuntimeError('SAT clause budget exceeded; no verdict')
        formula = And(*clauses)
        compile_seconds += perf_counter() - compile_start
        solve_start = perf_counter()
        model = satisfiable(formula, algorithm='dpll2')
        solve_seconds += perf_counter() - solve_start
        if model is not False:
            choices = {}
            for gi, g in enumerate(groups):
                selected = [mi for mi in range(len(g['modes'])) if model.get(variables[gi, mi], False)]
                if len(selected) != 1:
                    raise AssertionError('SAT model did not select exactly one mode per group')
                choices[g['id']] = g['modes'][selected[0]]['id']
            return {'status': 'counterworld', 'comparison': j, 'choices': choices,
                    'compile_seconds': compile_seconds, 'solve_seconds': solve_seconds,
                    'total_seconds': perf_counter() - started, 'pair_checks': nchecks, 'clauses': nclauses}
    return {'status': 'certain-qualified-positive', 'compile_seconds': compile_seconds,
            'solve_seconds': solve_seconds, 'total_seconds': perf_counter() - started,
            'pair_checks': nchecks, 'clauses': nclauses}
