import unittest
from jws_nhs_change_oracle import classify, changes, require_equal
from jws_nhs_change_replay import contract, control_frame, controls, expected_control_pools
from jws_nhs_change_baseline import batch, selected_pools, shacl_control
from jws_boundary_contracts import audit


class ChangeReplayControls(unittest.TestCase):
    def test_oracle_exact_boundary_and_unavailable(self):
        record={'csv_present':True,'within18':92,'total':100}
        self.assertEqual(classify(record,92,'ge')['status'],'positive')
        self.assertEqual(classify(record,92,'gt')['status'],'false')
        self.assertEqual(classify({'csv_present':False,'within18':None,'total':None},95,'ge')['status'],'unknown')
        record.update(within18=0,total=0)
        self.assertEqual(classify(record,92,'ge')['status'],'false')

    def test_independent_controls_all_policy_pairs(self):
        for threshold in (90,92,95):
            for operator in ('ge','gt'):
                for name,n,t,kind in controls():
                    g,f=control_frame(name,n,t); result=audit(g,f,contract(threshold,operator))
                    provider,pools=selected_pools(g,f)
                    wanted=expected_control_pools(n,t,kind,threshold,operator)
                    for pool,graph in pools.items():
                        direct,_=batch(graph,{'control':provider},threshold,operator)
                        self.assertEqual(direct['control'],wanted[pool],(threshold,operator,name,pool))
                        self.assertEqual({k:result['pools'][pool][k] for k in wanted[pool]},wanted[pool])

    def test_real_shacl_smoke(self):
        for n,expected in [(91,'false'),(92,'positive')]:
            g,f=control_frame('edge',n,100); result,count=shacl_control(g,f,92,'ge')
            self.assertEqual(count,3);self.assertEqual(result['ambient']['status'],expected)

    def test_guards_reject_mismatch_and_unsupported_policy(self):
        with self.assertRaises(AssertionError):require_equal({'A':1},{'B':1},'identity guard')
        with self.assertRaises(ValueError):changes({'A':1},{'B':1})
        for threshold,operator in [(101,'ge'),(92,'eq'),(92.0,'ge')]:
            with self.assertRaises(ValueError):contract(threshold,operator)


if __name__=='__main__':unittest.main()
