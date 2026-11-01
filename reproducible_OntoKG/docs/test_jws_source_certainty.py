import copy
from fractions import Fraction
import random
import unittest
from itertools import product
from jws_source_certainty import solve, UnsupportedInput, ResourceLimit
from jws_source_certainty_oracle import world_oracle, replay
from jws_source_certainty_sat import sat_counterworld, marginal_bound
from jws_source_certainty_certificate import check_counterworld, check_certain


def model(groups, margins=('0',)):
    return {'entity': 'fixed-entity', 'window': 'fixed-window', 'pool': 'delivered',
            'margins': list(margins), 'groups': [
                {'id': 'g' + str(gi), 'modes': [
                    {'id': 'm' + str(mi), 'values': values} for mi, values in enumerate(modes)]}
                for gi, modes in enumerate(groups)]}


class CertaintyTests(unittest.TestCase):
    def check_all(self, data, expected=None):
        before = copy.deepcopy(data)
        interval, oracle, sat = solve(data), world_oracle(data), sat_counterworld(data)
        self.assertEqual(interval['status'], oracle['status'])
        self.assertEqual(interval['status'], sat['status'])
        if marginal_bound(data)['status'] == 'certain-qualified-positive':
            self.assertEqual(interval['status'], 'certain-qualified-positive')
        self.assertTrue(check_certain(data, interval) if interval['status'] == 'certain-qualified-positive'
                        else check_counterworld(data, interval))
        if expected:
            self.assertEqual(interval['status'], expected)
        for result in (interval, sat):
            if result['status'] == 'counterworld':
                self.assertFalse(replay(data, result['choices'])['positive'])
                if 'point' in result:
                    t = Fraction(result['point'])
                    j = result['comparison']
                    for group in data['groups']:
                        m = next(m for m in group['modes'] if m['id'] == result['choices'][group['id']])
                        for c in m['values'].get('C', []):
                            self.assertLessEqual(Fraction(c), t)
                        for s in m['values'].get('S' + str(j), []):
                            self.assertLessEqual(t, Fraction(s) + Fraction(data['margins'][j]))
        self.assertEqual(data, before)
        return interval

    def test_closed_equal_and_negative_margin(self):
        self.check_all(model([[{'C': ['5'], 'S0': ['5']}]]), 'counterworld')
        self.check_all(model([[{'C': ['5'], 'S0': ['6']}]], ['-2']), 'certain-qualified-positive')
        self.check_all(model([[{'C': ['5'], 'S0': ['6']}]], ['-1']), 'counterworld')

    def test_missing_roles_empty_payloads_and_unbounded(self):
        for values in ({}, {'C': ['100']}, {'S0': ['-100']}):
            self.check_all(model([[values]]), 'counterworld')
        self.check_all(model([[{}], [{'C': ['2'], 'S0': ['1']}]]), 'certain-qualified-positive')

    def test_multiple_values_and_overlapping_modes_keep_ids(self):
        data = model([[{'C': ['1', '4'], 'S0': ['3', '8']},
                       {'C': ['2'], 'S0': ['9']}, {'C': ['2'], 'S0': ['9']}],
                      [{'C': ['3'], 'S0': ['7']}]] )
        self.check_all(data)

    def test_exact_decimals_and_high_precision(self):
        self.check_all(model([[{'C': ['0.3'], 'S0': ['0.1']}]], ['0.2']), 'counterworld')
        self.check_all(model([[{'C': ['10000000000000000000000000000000000000001'],
                               'S0': ['10000000000000000000000000000000000000000']}]]),
                       'certain-qualified-positive')
        self.check_all(model([[{'C': ['0.0000000000000000000000000000000000000001'],
                               'S0': ['0']}]]), 'certain-qualified-positive')

    def test_identical_marginals_different_correlations(self):
        correlated = model([[{'C': ['2'], 'S0': ['1'], 'S1': ['0']},
                              {'C': ['12'], 'S0': ['11'], 'S1': ['10']}]], ['0', '0'])
        independent = model([[{'C': ['2']}, {'C': ['12']}],
                             [{'S0': ['1'], 'S1': ['0']}, {'S0': ['11'], 'S1': ['10']}]], ['0', '0'])
        self.check_all(correlated, 'certain-qualified-positive')
        self.check_all(independent, 'counterworld')

    def test_no_uniform_identifier_binding(self):
        data = model([[{'C': ['3'], 'S0': ['4']}, {'C': ['7'], 'S0': ['8']}],
                      [{'C': ['5'], 'S0': ['6']}], [{'S1': ['0']}]], ['0', '0'])
        self.check_all(data, 'certain-qualified-positive')
        # Different centre/comparator IDs are necessary across the two worlds.
        first = replay(data, {'g0': 'm0', 'g1': 'm0', 'g2': 'm0'})['witness']
        second = replay(data, {'g0': 'm1', 'g1': 'm0', 'g2': 'm0'})['witness']
        self.assertNotEqual(first, second)

    def test_reject_unsupported_before_verdict(self):
        good = model([[{'C': ['2'], 'S0': ['1']}]] )
        bad = []
        for key, value in [('margins', []), ('groups', []), ('window', ['w1', 'w2']),
                           ('constraints', [['g0', 'g1']]), ('arithmetic', 'C>S+B')]:
            x = copy.deepcopy(good); x[key] = value; bad.append(x)
        x = copy.deepcopy(good); x['groups'][0]['modes'] = []; bad.append(x)
        for value in (1.0, 'Infinity', 'NaN', None, True):
            x = copy.deepcopy(good); x['groups'][0]['modes'][0]['values']['C'] = [value]; bad.append(x)
        x = copy.deepcopy(good); x['groups'][0]['modes'][0]['values']['window'] = ['other']; bad.append(x)
        for data in bad:
            with self.assertRaises(UnsupportedInput):
                solve(data)
        x = copy.deepcopy(good); x['margins'] = ['0'] * 33
        with self.assertRaises(ResourceLimit): solve(x)
        for value in ('1e999999999', '1e-999999999', '1' * 4097, 1 << 32769):
            x = copy.deepcopy(good); x['groups'][0]['modes'][0]['values']['C'] = [value]
            with self.assertRaises(ResourceLimit): solve(x)

    def test_certificates_reject_tampering(self):
        positive = model([[{'C': ['2'], 'S0': ['1']}]] )
        result = solve(positive)
        self.assertTrue(check_certain(positive, result))
        damaged = copy.deepcopy(result); damaged['certificate'][0]['intersection_empty'] = False
        self.assertFalse(check_certain(positive, damaged))
        negative = model([[{'C': ['1'], 'S0': ['2']}]] )
        result = solve(negative)
        self.assertTrue(check_counterworld(negative, result))
        for key, value in [('point', '3'), ('comparison', 1), ('choices', {'g0': 'not-a-mode'})]:
            damaged = copy.deepcopy(result); damaged[key] = value
            self.assertFalse(check_counterworld(negative, damaged))

    def test_exhaustive_625_two_group_models(self):
        payloads = ({}, {'C': ['0']}, {'S0': ['0']},
                    {'C': ['0'], 'S0': ['1']}, {'C': ['1'], 'S0': ['0']})
        for case in product(payloads, repeat=4):
            self.check_all(model([[case[0], case[1]], [case[2], case[3]]]))

    def test_seeded_400_models(self):
        rng = random.Random(20261019)
        for case in range(400):
            r = rng.randint(1, 2)
            groups = []
            for _ in range(rng.randint(1, 4)):
                modes = []
                for _ in range(rng.randint(1, 3)):
                    modes.append({role: [str(Fraction(rng.randint(-4, 4), rng.choice((1, 2, 5))))
                                         for _ in range(rng.randint(0, 2))]
                                  for role in ['C'] + ['S' + str(j) for j in range(r)]})
                groups.append(modes)
            margins = [str(Fraction(rng.randint(-2, 2), rng.choice((1, 2, 5)))) for _ in range(r)]
            with self.subTest(case=case): self.check_all(model(groups, margins))


if __name__ == '__main__':
    unittest.main()
