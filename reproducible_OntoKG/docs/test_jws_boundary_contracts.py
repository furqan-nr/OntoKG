"""Regression tests for the bounded fragment; no historical artifacts are changed."""
import copy
import json
import unittest
from decimal import localcontext
from rdflib import Graph, Literal, Namespace, RDF
from jws_boundary_contracts import audit, evaluate_pool, validate_contract
from jws_boundary_benchmark import CONTRACT, L, fixture, run, ROOT

class BoundaryTests(unittest.TestCase):
    def test_twenty_cases_matched_baseline(self):
        self.assertEqual(run()['mismatches'],[])

    def test_metadata_orthogonal(self):
        for name in ['unit_wrong','unit_absent']:
            result=audit(fixture(name),L.finding,CONTRACT)
            self.assertEqual(result['pools']['delivered']['status'],'positive')
            self.assertFalse(result['pools']['delivered']['metadata_ready'])

    def test_wrong_bundle_excludes_members(self):
        result=audit(fixture('wrong_bundle_entity'),L.finding,CONTRACT)
        self.assertFalse(result['bundle_association_valid'])
        self.assertTrue(result['excluded_bundle_members'])

    def test_malformed_contracts(self):
        changes=[{'version':'other'},{'negation':True},{'shared_window':'yes'},
                 {'branches':[[{'op':'eval','left':{'role':'temperature'},'right':{'constant':0}}]]},
                 {'branches':[[None]]},{'roles':{'x':{'metric':'x','unit_predicate':'bad'}}},
                 {'branches':[[{'op':'ge','left':{'role':'missing'},'right':{'constant':0}}]]},
                 {'branches':[[{'op':'ge','left':{'role':'temperature'},'right':{'constant':'NaN'}}]]}]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(ValueError):validate_contract({**CONTRACT,**change})

    def test_assignment_limit(self):
        with self.assertRaises(ValueError):audit(fixture('delivered_false_alternative'),L.finding,CONTRACT,max_assignments=1)
        with self.assertRaises(ValueError):audit(fixture('all_positive'),L.finding,CONTRACT,max_assignments=False)

    def test_four_finance_contracts(self):
        C=Namespace('https://w3id.org/ontokg-eq#')
        configs=json.loads((ROOT/'contracts/finance_boundary_v1.json').read_text())
        values={'R1':{'growth':'1','company':'1','benchmark':'2'},'R2':{'correlation':'-0.3'},
                'R3':{'company':'3','sector':'1','benchmark':'2'},'R4':{'event_return':'-2','volume':'1'}}
        for rid,c in configs.items():
            g=Graph();g.add((L.sensor1,RDF.type,C.Company));g.add((L.sensor1,C.comparedWithIndex,L['index']));g.add((L['index'],RDF.type,C.MarketIndex))
            g.add((L.sensor1,C.isClassifiedByIndustrySector,L.sector));g.add((L.sector,RDF.type,C.IndustrySectorClassifier))
            obs=set()
            for role,spec in c['roles'].items():
                o=L[role];obs.add(o)
                target=L['index'] if role=='benchmark' else L.sector if role=='sector' else L.sensor1
                g.add((o,RDF.type,C.Observation));g.add((o,C.hasMetricName,Literal(spec['metric'])))
                g.add((o,C.hasMetricValue,Literal(values[rid][role])));g.add((o,C.isObservationOf,target))
                g.add((o,C.hasUnit,Literal(spec['expected_unit'])))
                if spec.get('window_predicate'):
                    from rdflib import URIRef
                    g.add((o,URIRef(spec['window_predicate']),L.shift1));g.add((L.shift1,RDF.type,URIRef(spec['window_type'])))
            self.assertEqual(evaluate_pool(g,obs,L.sensor1,c)['status'],'positive')
            if rid=='R3':
                g.set((L.benchmark,C.observedOverWindow,L.shift2));g.add((L.shift2,RDF.type,C.AnalysisWindow))
                self.assertEqual(evaluate_pool(g,obs,L.sensor1,c)['status'],'unknown')

    def test_exact_addition_and_abs_independent_context(self):
        c=copy.deepcopy(CONTRACT)
        c['branches']=[[{'op':'gt','left':{'abs':{'role':'temperature'}},
                         'right':{'add':[{'constant':'80'},{'constant':'0.000000000000000000000000000001'}]}}]]
        g=fixture('one_or_branch');g.set((L.t,L.number,Literal('-80.000000000000000000000000000002')))
        with localcontext() as ctx:
            ctx.prec=4
            self.assertEqual(audit(g,L.finding,c)['pools']['delivered']['status'],'positive')

if __name__=='__main__':unittest.main()
