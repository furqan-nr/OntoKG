"""Restricted source-coherent arithmetic-star certainty; not boundary-1 statuses.

Every group chooses one mode independently. Values are already locally qualified
for the one immutable entity/window/pool. No source authentication is implied.
The ordinary colored closed-interval sweep is not a new geometric primitive.
"""
from fractions import Fraction
from decimal import Decimal
import json
import re


class UnsupportedInput(ValueError):
    pass


class ResourceLimit(RuntimeError):
    pass


def exact(x):
    if isinstance(x, bool) or isinstance(x, float):
        raise UnsupportedInput('Boolean/float numeric input is unsupported')
    if not isinstance(x, (str, int, Decimal, Fraction)):
        raise UnsupportedInput('Expected exact integer, decimal string or rational')
    # Representation budget is checked BEFORE Fraction expands a decimal exponent.
    # It is a resource restriction, not a mathematical decision about the star.
    if isinstance(x, str):
        if len(x) > 4096:
            raise ResourceLimit('Numeric lexical-length budget exceeded')
        exponent = re.search(r'[eE]([+-]?\d+)$', x.strip())
        if exponent and (len(exponent.group(1).lstrip('+-')) > 5 or
                         abs(int(exponent.group(1))) > 4096):
            raise ResourceLimit('Decimal exponent budget exceeded')
    if isinstance(x, Decimal) and x.is_finite():
        if len(x.as_tuple().digits) > 4096 or abs(x.as_tuple().exponent) > 4096:
            raise ResourceLimit('Decimal representation budget exceeded')
    if isinstance(x, int) and x.bit_length() > 4096:
        raise ResourceLimit('Integer representation budget exceeded')
    if isinstance(x, Fraction) and max(x.numerator.bit_length(), x.denominator.bit_length()) > 4096:
        raise ResourceLimit('Rational representation budget exceeded')
    try:
        result = Fraction(x)
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise UnsupportedInput('Numeric values must be finite and exact') from exc
    if max(result.numerator.bit_length(), result.denominator.bit_length()) > 4096:
        raise ResourceLimit('Rational representation budget exceeded')
    return result


def _keys(obj, allowed, required):
    if not isinstance(obj, dict) or set(obj) - set(allowed) or not set(required) <= set(obj):
        raise UnsupportedInput('Unsupported fields or missing required fields')


def normalize(data):
    """Validate all restrictions before producing any verdict; input is immutable."""
    _keys(data, ('entity', 'window', 'pool', 'margins', 'groups'),
          ('entity', 'window', 'pool', 'margins', 'groups'))
    for key in ('entity', 'window', 'pool'):
        if not isinstance(data[key], str) or not data[key]:
            raise UnsupportedInput('Exactly one nonempty fixed context is required')
    if not isinstance(data['margins'], list) or not data['margins']:
        raise UnsupportedInput('At least one comparator is required')
    margins = tuple(exact(x) for x in data['margins'])
    if len(margins) > 32:
        raise ResourceLimit('Comparator budget exceeded')
    if not isinstance(data['groups'], list) or not data['groups']:
        raise UnsupportedInput('At least one source group is required')
    roles = ('C',) + tuple('S' + str(j) for j in range(len(margins)))
    groups, gids, count, nvalues = [], set(), 0, 0
    for group in data['groups']:
        _keys(group, ('id', 'modes'), ('id', 'modes'))
        gid = group['id']
        if not isinstance(gid, str) or not gid or gid in gids:
            raise UnsupportedInput('Source IDs must be unique nonempty strings')
        gids.add(gid)
        if not isinstance(group['modes'], list) or not group['modes']:
            raise UnsupportedInput('Every group requires a nonempty mode list')
        modes, mids = [], set()
        for mode in group['modes']:
            _keys(mode, ('id', 'values'), ('id', 'values'))
            mid = mode['id']
            if not isinstance(mid, str) or not mid or mid in mids:
                raise UnsupportedInput('Mode IDs must be unique within each group')
            mids.add(mid)
            values = mode['values']
            _keys(values, roles, ())
            parsed = {}
            for role in roles:
                raw = values.get(role, [])
                if not isinstance(raw, list):
                    raise UnsupportedInput('Roles require finite value lists')
                parsed[role] = tuple(exact(v) for v in raw)
                nvalues += len(raw)
            count += 1
            if count > 10000 or nvalues > 100000:
                raise ResourceLimit('Mode/value budget exceeded')
            modes.append((mid, parsed))
        groups.append((gid, tuple(modes)))
    return margins, tuple(groups), nvalues, count


def _s(x):
    return None if x is None else str(x)


def solve(data):
    """Return certain-qualified-positive or a mode-coherent non-positive world.

    None is used only as a structural endpoint: lower None=-infinity and upper
    None=+infinity. It is never accepted as a numeric observation. Every emitted
    counterworld point is a finite Fraction serialized without rounding.
    """
    margins, groups, nvalues, nmodes = normalize(data)
    summaries = []
    for gid, modes in groups:
        summaries.append((gid, tuple((mid,
            max(v['C']) if v['C'] else None,
            tuple(min(v['S' + str(j)]) + delta if v['S' + str(j)] else None
                  for j, delta in enumerate(margins))) for mid, v in modes)))
    certificate = []
    for j in range(len(margins)):
        active = {gid: set() for gid, _ in groups}
        events, intervals = {}, []
        for gid, modes in summaries:
            for mid, low, uppers in modes:
                high = uppers[j]
                if low is not None and high is not None and low > high:
                    continue
                intervals.append({'group': gid, 'mode': mid, 'lower': _s(low), 'upper': _s(high)})
                if low is None:
                    active[gid].add(mid)
                else:
                    events.setdefault(low, [[], []])[0].append((gid, mid))
                if high is not None:
                    events.setdefault(high, [[], []])[1].append((gid, mid))
        covered = sum(bool(v) for v in active.values())
        points = sorted(events)
        trace = []

        def answer(t):
            return {'status': 'counterworld', 'comparison': j, 'point': str(t),
                    'choices': {gid: sorted(active[gid])[0] for gid, _ in groups},
                    'semantics': 'non-positive qualified star, not boundary-1 false',
                    'input_size': {'values': nvalues, 'modes': nmodes, 'comparators': len(margins)}}

        if covered == len(groups):
            return answer(points[0] - 1 if points else Fraction(0))
        for point in points:
            starts, ends = events[point]
            for gid, mid in starts:
                if not active[gid]:
                    covered += 1
                active[gid].add(mid)
            trace.append({'point': str(point), 'covered_at_point': covered})
            if covered == len(groups):
                return answer(point)
            for gid, mid in ends:
                active[gid].remove(mid)
                if not active[gid]:
                    covered -= 1
        certificate.append({'comparison': j, 'intervals': intervals,
                            'closed_endpoint_coverage': trace, 'intersection_empty': True})
    return {'status': 'certain-qualified-positive', 'certificate': certificate,
            'input_size': {'values': nvalues, 'modes': nmodes, 'comparators': len(margins)}}


def certificate_json(data):
    return json.dumps(solve(data), sort_keys=True, indent=2)
