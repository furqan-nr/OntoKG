"""Small semantic regression tests, independent synthetic graphs."""
import unittest
from rdflib import Graph, Literal, Namespace, RDF
from jws_contracts import C, evaluate_finding, load_contracts
from rdflib.namespace import XSD

N = Namespace('urn:test:')

class Contracts(unittest.TestCase):
    def graph(self, rule):
        g = Graph()
        g.add((N.co,RDF.type,C.Company))
        g.add((N.f,C.concernsEntity,N.co))
        g.add((N.f,C.derivedByRule,Literal(rule)))
        g.add((N.f_bundle,RDF.type,C.EvidenceBundle))
        g.add((N.f_bundle,C.explainsResultEntity,N.co))
        return g

    def observation(self,g,name,metric,value,subject=None,window=None):
        o=N[name]
        g.add((N.f,C.supportedByObservation,o))
        g.add((N.f_bundle,C.includesObservation,o))
        g.add((o,RDF.type,C.Observation))
        g.add((o,C.isObservationOf,subject or N.co))
        g.add((o,C.hasMetricName,Literal(metric)))
        g.add((o,C.hasMetricValue,Literal(value)))
        if window:
            g.add((o,C[window],N.window))
            g.add((N.window,RDF.type,C.EventWindow if window=='observedInEventWindow' else C.AnalysisWindow))
        return o

    def test_r2_inclusive_boundary(self):
        for value in [.3,-.3,.2999]:
            g=self.graph('R2')
            self.observation(g,'corr','FX vs company return correlation',value)
            self.assertEqual(evaluate_finding(g,N.f)['sufficient_witness'],abs(value)>=.3)

    def test_volume_only_or(self):
        g=self.graph('R4')
        self.observation(g,'volume','abnormal volume ratio',1.5,window='observedInEventWindow')
        r=evaluate_finding(g,N.f)
        self.assertTrue(r['sufficient_witness'])
        self.assertFalse(r['support_complete'])
        self.assertEqual(r['witnesses'],[{'volume':str(N.volume)}])

    def test_missing_comparator_and_strict_boundary(self):
        g=self.graph('R1')
        self.observation(g,'growth','YoY profit growth %',1)
        self.observation(g,'ret','post-report window return %',0,window='observedOverWindow')
        self.assertEqual(evaluate_finding(g,N.f)['status'],'incomplete')
        g.add((N.bm,RDF.type,C.MarketIndex))
        self.observation(g,'benchmark','benchmark window return %',0,N.bm,'observedOverWindow')
        self.assertEqual(evaluate_finding(g,N.f)['status'],'predicate_false')

    def test_equal_zero_wrong_role(self):
        g=self.graph('R1')
        self.observation(g,'growth','YoY profit growth %',1)
        self.observation(g,'ret','post-report window return %',-1,window='observedOverWindow')
        self.observation(g,'benchmark','benchmark window return %',0,N.other,'observedOverWindow')
        self.assertEqual(evaluate_finding(g,N.f)['status'],'incomplete')

    def test_bundle_only_missing_evidence(self):
        g=self.graph('R2')
        o=self.observation(g,'corr','FX vs company return correlation',.3)
        g.remove((N.f_bundle,C.includesObservation,o))
        result=evaluate_finding(g,N.f)
        self.assertTrue(result['finding_support_sufficient'])
        self.assertFalse(result['bundle_sufficient'])
        self.assertEqual(result['bundle_status'],'incomplete_bundle')

    def test_exact_decimal_margin_boundary(self):
        for company, expected in [('1.1',False),('1.100000000000000000001',True)]:
            g=self.graph('R3')
            g.add((N.sector,RDF.type,C.IndustrySectorClassifier))
            g.add((N.co,C.isClassifiedByIndustrySector,N.sector))
            g.add((N.bm,RDF.type,C.MarketIndex))
            self.observation(g,'ret','post-report window return %',Literal(company,datatype=XSD.decimal),window='observedOverWindow')
            self.observation(g,'sector','sector window return %',Literal('0.1',datatype=XSD.decimal),N.sector,'observedOverWindow')
            self.observation(g,'benchmark','benchmark window return %',Literal('0.1',datatype=XSD.decimal),N.bm,'observedOverWindow')
            spec=load_contracts()['R3']
            spec['margin']=1
            self.assertEqual(evaluate_finding(g,N.f,contract=spec)['sufficient_witness'],expected)

if __name__=='__main__':
    unittest.main()
