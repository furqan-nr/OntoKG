"""Independent replay checker for execution certificates, not a new proof system.

Recomputes interval summaries from original values; checks every finite critical
point and the unbounded initial segment. Intentionally simple O(r*M**2) checker;
not advertised as the optimized solver's complexity or a succinct certificate.
No solver, normalizer or solver interval helpers are imported.
"""
from fractions import Fraction


def check_counterworld(data, result):
    if result.get('status') != 'counterworld':
        return False
    try:
        j = result['comparison']
        if not isinstance(j, int) or not 0 <= j < len(data['margins']):
            return False
        t = Fraction(result['point'])
        delta = Fraction(data['margins'][j])
        choices = result['choices']
        if set(choices) != {g['id'] for g in data['groups']}:
            return False
        for group in data['groups']:
            selected = [m for m in group['modes'] if m['id'] == choices[group['id']]]
            if len(selected) != 1:
                return False
            values = selected[0]['values']
            if any(Fraction(c) > t for c in values.get('C', [])):
                return False
            if any(t > Fraction(s) + delta for s in values.get('S' + str(j), [])):
                return False
        return True
    except (KeyError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        return False


def check_certain(data, result):
    if result.get('status') != 'certain-qualified-positive':
        return False
    try:
        supplied = result['certificate']
        if len(supplied) != len(data['margins']):
            return False
        ngroups = len(data['groups'])
        for j, raw_delta in enumerate(data['margins']):
            intervals, endpoints = [], set()
            for group in data['groups']:
                for mode in group['modes']:
                    cs = [Fraction(c) for c in mode['values'].get('C', [])]
                    ss = [Fraction(s) + Fraction(raw_delta)
                          for s in mode['values'].get('S' + str(j), [])]
                    low, high = max(cs) if cs else None, min(ss) if ss else None
                    if low is not None and high is not None and low > high:
                        continue
                    intervals.append({'group': group['id'], 'mode': mode['id'],
                                      'lower': str(low) if low is not None else None,
                                      'upper': str(high) if high is not None else None})
                    endpoints.update(x for x in (low, high) if x is not None)
            if len({i['group'] for i in intervals if i['lower'] is None}) == ngroups:
                return False
            trace = []
            for point in sorted(endpoints):
                covered = {i['group'] for i in intervals
                           if (i['lower'] is None or Fraction(i['lower']) <= point)
                           and (i['upper'] is None or point <= Fraction(i['upper']))}
                if len(covered) == ngroups:
                    return False
                trace.append({'point': str(point), 'covered_at_point': len(covered)})
            expected = {'comparison': j, 'intervals': intervals,
                        'closed_endpoint_coverage': trace, 'intersection_empty': True}
            if supplied[j] != expected:
                return False
        return True
    except (KeyError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        return False
