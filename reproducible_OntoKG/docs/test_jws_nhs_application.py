"""Application framing controls, distinct from real cohort observations."""
import unittest
from rdflib.namespace import RDF
from jws_boundary_contracts import audit
from jws_nhs_application import frame, R
from jws_nhs_contract import build_contract


class Framing(unittest.TestCase):
    def test_unavailable_does_not_borrow_publisher_zero(self):
        g,f=frame({'provider_code':'CONTROL','provider_name':'Control','period':'2026-08',
                   'csv_present':False,'within18':None,'total':None,
                   'publisher_context':{'within18':0,'total':0}})
        self.assertEqual(list(g.subjects(RDF.type,R.CountObservation)),[])
        for result in audit(g,f,build_contract())['pools'].values():
            self.assertEqual(result['status'],'unknown')
            self.assertFalse(result['metadata_ready'])

    def test_complete_source_selectors(self):
        r={'provider_code':'CONTROL','provider_name':'Control','period':'2026-08',
           'csv_present':True,'within18':92,'total':100,
           'lineage':{'archive_sha256':'control-only','member':'control.csv',
                      'record_numbers_including_header':[2,3],
                      'within18_columns':['band1','band2'],'total_column':'Total'}}
        g,f=frame(r)
        self.assertEqual(len(list(g.subjects(RDF.type,R.CountObservation))),2)
        self.assertEqual(len(list(g.objects(None,R.sourceSHA256))),2)
        for result in audit(g,f,build_contract())['pools'].values():
            self.assertEqual(result['status'],'positive')
            self.assertTrue(result['metadata_ready'])


if __name__=='__main__': unittest.main()
