"""Independent original-witness/world oracle. No interval/extrema solver imports."""
from fractions import Fraction
from itertools import product


def replay(data, choices):
    """Enumerate original role assignments; do not use max/min equivalences."""
    if set(choices) != {g['id'] for g in data['groups']}:
        raise ValueError('One mode per group is required')
    roles = ['C'] + ['S' + str(j) for j in range(len(data['margins']))]
    values = {r: [] for r in roles}
    for group in data['groups']:
        selected = [m for m in group['modes'] if m['id'] == choices[group['id']]]
        if len(selected) != 1:
            raise ValueError('Unknown/ambiguous selected mode')
        for role in roles:
            values[role].extend((Fraction(v), group['id'], selected[0]['id'], role, index)
                                for index, v in enumerate(selected[0]['values'].get(role, [])))
    for witness in product(*(values[r] for r in roles)):
        if all(witness[0][0] > witness[j + 1][0] + Fraction(delta)
               for j, delta in enumerate(data['margins'])):
            return {'positive': True, 'witness': [[str(v[0]), *v[1:]] for v in witness]}
    return {'positive': False, 'witness': None,
            'missing_roles': [r for r in roles if not values[r]]}


def world_oracle(data, max_worlds=4096):
    count = 1
    for group in data['groups']:
        count *= len(group['modes'])
    if count > max_worlds:
        raise RuntimeError('Explicit-world resource budget exceeded; no verdict')
    checked = 0
    for mids in product(*([m['id'] for m in g['modes']] for g in data['groups'])):
        choices = dict(zip((g['id'] for g in data['groups']), mids))
        checked += 1
        if not replay(data, choices)['positive']:
            return {'status': 'counterworld', 'choices': choices, 'worlds_checked': checked}
    return {'status': 'certain-qualified-positive', 'worlds_checked': checked}
