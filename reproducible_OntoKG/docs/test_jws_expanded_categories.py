"""Categorical false/unknown regression coverage, without financial assumptions."""
import unittest
from rdflib import RDF
from jws_contracts import C, evaluate_finding
from jws_expanded_evaluation import categorical_replay
import test_jws_contracts as fixtures

N = fixtures.N


class Categories(unittest.TestCase):
    def check(self, graph, label):
        result = categorical_replay({'label': label}, evaluate_finding(graph, N.f))
        self.assertTrue(result['agrees'])
        self.assertTrue(result['categorical_status_agrees'], result)
        self.assertTrue(result['full_graph_truth_agrees'], result)

    def test_three_categories_for_each_conjunctive_rule(self):
        helper = fixtures.Contracts()
        for rule in ['R1', 'R2', 'R3']:
            for label in ['positive', 'negative', 'incomplete']:
                with self.subTest(rule=rule, label=label):
                    graph = helper.graph(rule)
                    graph.add((N.bm, RDF.type, C.MarketIndex))
                    graph.add((N.sector, RDF.type, C.IndustrySectorClassifier))
                    graph.add((N.co, C.isClassifiedByIndustrySector, N.sector))
                    roles = {'R1': [('growth','YoY profit growth %',1,N.co,None), ('ret','post-report window return %',1,N.co,'observedOverWindow'), ('benchmark','benchmark window return %',2,N.bm,'observedOverWindow')],
                             'R2': [('corr','FX vs company return correlation',.3,N.co,None)],
                             'R3': [('ret','post-report window return %',3,N.co,'observedOverWindow'), ('sector','sector window return %',2,N.sector,'observedOverWindow'), ('benchmark','benchmark window return %',2,N.bm,'observedOverWindow')]}[rule]
                    if label == 'incomplete':
                        roles = roles[:-1]
                    for i, (name, metric, value, subject, window) in enumerate(roles):
                        if label == 'negative' and i == 0:
                            value = 0
                        helper.observation(graph,name,metric,value,subject,window)
                    self.check(graph,label)

    def test_r4_missing_branch_convention(self):
        helper = fixtures.Contracts()
        for ret, vol, label in [(2,None,'positive'), (None,1.5,'positive'), (1,None,'incomplete'), (None,1,'incomplete'), (None,None,'incomplete'), (1,1,'negative'), (2,1,'positive'), (1,1.5,'positive')]:
            with self.subTest(ret=ret, vol=vol):
                graph = helper.graph('R4')
                if ret is not None:
                    helper.observation(graph,'ret','cumulative abnormal return %',ret,window='observedInEventWindow')
                if vol is not None:
                    helper.observation(graph,'vol','abnormal volume ratio',vol,window='observedInEventWindow')
                self.check(graph,label)

    def test_wrong_false_on_unknown_is_not_agreement(self):
        result = categorical_replay({'label':'incomplete'}, {'bundle_status':'predicate_false', 'bundle_sufficient':False, 'full_graph_truth':False})
        self.assertTrue(result['agrees'])
        self.assertFalse(result['categorical_status_agrees'])
        self.assertFalse(result['full_graph_truth_agrees'])


if __name__ == '__main__':
    unittest.main()
