"""Small controls, not observations in the genuine NHS cohort."""
import unittest
from rdflib import Graph, Literal, RDF, XSD
from jws_nhs_matched_baseline import N, audit_baseline, shape_graph


def fixture(numerator=92, denominator=100):
    g=Graph(); f=N.finding; p=N.provider; month=N.august; bundle=N.bundle
    g.add((p,RDF.type,N.Provider));g.add((month,RDF.type,N.ReportingMonth))
    g.add((f,N.aboutProvider,p));g.add((f,N.deliveredAs,bundle))
    g.add((bundle,RDF.type,N.EvidenceView));g.add((bundle,N.forProvider,p))
    for obs,metric,count in [(N.n,'within18',numerator),(N.d,'total',denominator)]:
        g.add((obs,RDF.type,N.CountObservation));g.add((obs,N.metric,Literal(metric)))
        g.add((obs,N['count'],Literal(count,datatype=XSD.integer)))
        g.add((obs,N.reportedBy,p));g.add((obs,N.inMonth,month))
        g.add((obs,N.unit,Literal('pathways')));g.add((f,N.usesCount,obs))
        g.add((bundle,N.containsCount,obs))
    return g,f


class BaselineControls(unittest.TestCase):
    def test_inclusive_and_below(self):
        for n,expected in [(92,'positive'),(91,'false'),(0,'false')]:
            g,f=fixture(n)
            for pool in audit_baseline(g,f)['pools'].values():
                self.assertEqual(pool,{'status':expected,'metadata_ready':True})

    def test_missing_not_false_and_no_ambient_rescue(self):
        g,f=fixture();g.remove((f,N.usesCount,N.d))
        result=audit_baseline(g,f)
        self.assertEqual(result['pools']['ambient']['status'],'positive')
        self.assertEqual(result['pools']['support']['status'],'unknown')
        self.assertEqual(result['pools']['delivered']['status'],'unknown')

    def test_month_entity_and_bundle_isolation(self):
        for mutation in ['month','provider','bundle']:
            g,f=fixture()
            if mutation=='month':
                g.remove((N.d,N.inMonth,None));g.add((N.d,N.inMonth,N.september))
                g.add((N.september,RDF.type,N.ReportingMonth))
            elif mutation=='provider':
                g.remove((N.d,N.reportedBy,None));g.add((N.d,N.reportedBy,N.otherProvider))
                g.add((N.otherProvider,RDF.type,N.Provider))
            else:
                g.remove((N.bundle,N.forProvider,None));g.add((N.bundle,N.forProvider,N.otherProvider))
            result=audit_baseline(g,f)
            self.assertEqual(result['pools']['delivered']['status'],'unknown')
            if mutation=='bundle':
                self.assertFalse(result['bundle_association_valid'])
                self.assertEqual(result['pools']['support']['status'],'positive')

    def test_unit_readiness_cannot_launder_passing_witness(self):
        g,f=fixture();g.remove((N.n,N.unit,None))
        for triple in list(g.triples((N.n,None,None))):
            g.add((N.decoy,triple[1],triple[2]))
        g.set((N.decoy,N['count'],Literal(91,datatype=XSD.integer)))
        g.add((N.decoy,N.unit,Literal('pathways')))
        g.add((f,N.usesCount,N.decoy));g.add((N.bundle,N.containsCount,N.decoy))
        result=audit_baseline(g,f)
        for pool in result['pools'].values():
            self.assertEqual(pool,{'status':'positive','metadata_ready':False})

    def test_large_integer_exactness_and_zero_denominator(self):
        for n,d,expected in [(92*10**40,100*10**40,'positive'),
                             (92*10**40-1,100*10**40,'false'),(0,0,'false')]:
            g,f=fixture(n,d)
            self.assertEqual(audit_baseline(g,f)['pools']['ambient']['status'],expected)

    def test_ambiguous_observation_and_full_shacl_smoke(self):
        from pyshacl import validate
        for n,expected in [(92,True),(91,False)]:
            g,f=fixture(n)
            conforms,_,_=validate(g,shacl_graph=shape_graph(N.provider),advanced=True)
            self.assertEqual(conforms,expected)
        g,f=fixture();g.add((N.n,N['count'],Literal(91,datatype=XSD.integer)))
        self.assertEqual(audit_baseline(g,f)['pools']['ambient']['status'],'unknown')


if __name__=='__main__':
    unittest.main()
