"""Small constructed compiler controls, separate from the real NHS cohort."""
import unittest
from decimal import Decimal, localcontext
from rdflib import Graph, Namespace, RDF, Literal
from jws_boundary_contracts import audit, validate_contract, _value
from jws_nhs_contract import N, build_contract, scaled_role

R = Namespace(N)
T = Namespace('urn:nhs-compiler-test:')


class NHSContractTests(unittest.TestCase):
    def graph(self, numerator, denominator):
        g = Graph()
        for triple in [(T.provider,RDF.type,R.Provider),(T.month,RDF.type,R.ReportingMonth),
                       (T.bundle,RDF.type,R.EvidenceView),(T.finding,R.aboutProvider,T.provider),
                       (T.finding,R.deliveredAs,T.bundle),(T.bundle,R.forProvider,T.provider)]:
            g.add(triple)
        for role, value in [('within18', numerator), ('total', denominator)]:
            if value is None:
                continue
            obs=T[role]
            for p,v in [(RDF.type,R.CountObservation),(R.metric,Literal(role)),
                        (R['count'],Literal(value)),(R.reportedBy,T.provider),
                        (R.inMonth,T.month),(R.unit,Literal('pathways'))]:g.add((obs,p,v))
            g.add((T.finding,R.usesCount,obs));g.add((T.bundle,R.containsCount,obs))
        return g

    def test_exact_scaled_addition(self):
        for factor in [0,1,2,92,100,256]:
            for value in [-1,0,1,123456789]:
                self.assertEqual(_value(scaled_role('x',factor), {'x':{'value':Decimal(value)}}),factor*value)
        for factor in [-1,257,True,1.5]:
            with self.assertRaises(ValueError):scaled_role('x',factor)

    def test_threshold_and_missing(self):
        contract=validate_contract(build_contract())
        for numerator,denominator,expected in [(92,100,'positive'),(91,100,'false'),
                                               (0,100,'false'),(0,0,'false'),(92,None,'unknown')]:
            result=audit(self.graph(numerator,denominator),T.finding,contract)
            self.assertEqual(result['pools']['delivered']['status'],expected)
        # A zero denominator is ineligible at application level; the underlying
        # guarded numerical condition is false, not a valid 0% performance score.

    def test_low_precision_and_delivery_isolation(self):
        g=self.graph(92000001,100000000)
        with localcontext() as context:
            context.prec=4
            self.assertEqual(audit(g,T.finding,build_contract())['pools']['delivered']['status'],'positive')
        g.remove((T.bundle,R.containsCount,T.total))
        result=audit(g,T.finding,build_contract())
        self.assertEqual(result['pools']['ambient']['status'],'positive')
        self.assertEqual(result['pools']['delivered']['status'],'unknown')


if __name__=='__main__':unittest.main()
