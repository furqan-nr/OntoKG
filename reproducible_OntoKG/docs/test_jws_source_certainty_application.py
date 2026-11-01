import copy
import json
import unittest

from jws_source_certainty_application import evaluate_case, verify_bindings, OUT
from jws_source_certainty import UnsupportedInput


def case(modes):
    return {'id': 'runner-control', 'model': {
        'entity': 'synthetic-control', 'window': 'fixed', 'pool': 'qualified',
        'margins': ['0'], 'groups': [{'id': 'release', 'modes': [
            {'id': str(i), 'values': {'C': [c], 'S0': [s]}}
            for i, (c, s) in enumerate(modes)]}]}}


class ApplicationReplayTests(unittest.TestCase):
    def test_public_cases_bind_exactly_and_reject_value_tampering(self):
        suite = json.loads((OUT / 'cases.json').read_text(encoding='utf-8'))
        bindings = json.loads((OUT / 'bindings.json').read_text(encoding='utf-8'))
        sources = {s['id']: s for s in suite['sources']}
        for fixture in suite['cases']:
            link = bindings['cases'][fixture['id']]
            verify_bindings(fixture, link, sources)
            altered = copy.deepcopy(fixture)
            altered['model']['groups'][0]['modes'][0]['values']['C'] = ['999']
            with self.assertRaisesRegex(ValueError, 'differs'):
                verify_bindings(altered, link, sources)

    def test_all_worlds_preserve_source_mode_and_input(self):
        fixture = case([('2', '1'), ('12', '11')])
        original = copy.deepcopy(fixture)
        result = evaluate_case(fixture)
        self.assertEqual(result['interval']['status'], 'certain-qualified-positive')
        self.assertEqual(result['marginal_bound']['status'], 'undetermined')
        self.assertEqual(result['world_count'], 2)
        self.assertTrue(all(w['original_binding_replay']['positive']
                            for w in result['all_declared_worlds']))
        self.assertEqual(fixture, original)

    def test_changed_verdict_is_not_hidden(self):
        result = evaluate_case(case([('1', '2'), ('3', '2')]))
        self.assertEqual(result['interval']['status'], 'counterworld')
        self.assertEqual([w['original_binding_replay']['positive']
                          for w in result['all_declared_worlds']], [False, True])
        self.assertTrue(result['certificate_valid'])

    def test_scope_and_world_budget_reject_without_verdict(self):
        fixture = case([('2', '1')])
        fixture['model']['constraints'] = []
        with self.assertRaises(UnsupportedInput):
            evaluate_case(fixture)
        fixture = case([('2', '1'), ('3', '2')])
        group = fixture['model']['groups'][0]
        fixture['model']['groups'] = [dict(copy.deepcopy(group), id=str(i)) for i in range(13)]
        with self.assertRaisesRegex(ValueError, 'budget exceeded'):
            evaluate_case(fixture)


if __name__ == '__main__':
    unittest.main()
