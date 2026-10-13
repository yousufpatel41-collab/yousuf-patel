from pathlib import Path
import sys,json,unittest
import numpy as np
from scipy.optimize import linprog
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from energy_optimizer import schedule,evaluate,savings_capture

class EnergyOptimizerTests(unittest.TestCase):
    def test_matches_independent_linear_program(self):
        rng=np.random.default_rng(41)
        for _ in range(20):
            prices=rng.uniform(-.15,.65,24);available=rng.random(24)>.3
            result=schedule(prices,available,20,7.4,.9)
            lp=linprog(prices,A_eq=np.ones((1,24)),b_eq=[20/.9],bounds=[(0,7.4 if a else 0) for a in available],method='highs')
            self.assertTrue(lp.success);self.assertAlmostEqual(float(np.dot(prices,result['load'])),lp.fun,places=8)
    def test_negative_prices_do_not_create_extra_consumption(self):
        result=schedule([-.2,-.1,.5],[1,1,1],4,7,.8)
        self.assertAlmostEqual(sum(result['load']),5);self.assertAlmostEqual(result['delivered_kwh'],4)
    def test_infeasible_target_shortfall(self):
        result=schedule([.2,.1],[1,0],20,7,.9)
        self.assertAlmostEqual(result['shortfall_kwh'],13.7)
    def test_connection_capacity_accounts_for_household(self):
        result=schedule([.1,.2],[1,1],6,7,.9,household_kwh=[10,10],connection_kw=11)
        np.testing.assert_allclose(result['load'],[1,1]);self.assertAlmostEqual(result['shortfall_kwh'],4.2)
    def test_immediate_can_be_optimal(self):
        result=evaluate([.1,.2,.3],[.1,.2,.3],[1,1,1],4,7,1)
        self.assertEqual(result['immediate'],result['oracle']);self.assertIsNone(result['capture_percent'])
    def test_losses_are_not_clipped(self):self.assertLess(savings_capture(2,3,1),0)
    def test_invalid_efficiency_rejected(self):
        for efficiency in [0,1.1]:
            with self.assertRaises(ValueError):schedule([.2],[1],4,7,efficiency)
    def test_stored_forecast_chronology_and_scoring(self):
        report=json.loads((ROOT/'reports/forecast_experiment.json').read_text())
        source=pd.read_csv(ROOT/'data/hourly_prices.csv').set_index('TimestampMs').PriceEURMWh
        for block in report['blocks']:
            times=pd.to_datetime(block['timestamps'],unit='ms',utc=True);issue=pd.Timestamp(block['issue']);end=(issue.normalize()+pd.DateOffset(days=2)).tz_convert('UTC')
            self.assertEqual(times[0],end);self.assertTrue((np.diff(block['timestamps'])==3600000).all())
            np.testing.assert_allclose(source.loc[block['timestamps']].values,block['actual'],atol=1e-4)
            for name,q in block['predictions'].items():
                self.assertEqual(np.asarray(q).shape,(48,3));self.assertTrue((np.diff(q,axis=1)>=0).all())
            self.assertLess(times[-1]-pd.Timedelta(hours=168),end)
    def test_report_totals_reconcile_with_sessions(self):
        report=json.loads((ROOT/'reports/forecast_experiment.json').read_text())
        for row in report['summary']:
            results=[]
            for block in report['blocks']:
                if block['split']!=row['split']:continue
                local=pd.to_datetime(block['timestamps'],unit='ms',utc=True).tz_convert('Europe/Berlin')
                q=np.asarray(block['predictions'][row['model']]);actual=np.asarray(block['actual'])/1000*1.19+.2
                results.append(evaluate(actual,q[:,1]/1000*1.19+.2,(local.hour>=18)|(local.hour<7)))
            self.assertAlmostEqual(sum(r['model'] for r in results),row['schedule_eur'],places=2)
            self.assertAlmostEqual(sum(r['oracle'] for r in results),row['oracle_eur'],places=2)
            self.assertTrue(all(r['model']>=r['oracle']-1e-8 for r in results))
    def test_js_and_python_share_schedules(self):
        import subprocess,shutil
        node=shutil.which('node')
        if not node:self.skipTest('Node is optional for cross-runtime check')
        core=str(ROOT/'dashboard/energy-core.js')
        prices=[.3,-.1,.7,.2];available=[1,1,0,1]
        expected=schedule(prices,available,12,7.4,.9)
        js='const c=require('+json.dumps(core)+');console.log(JSON.stringify(c.schedule([.3,-.1,.7,.2],[true,true,false,true],12,7.4,.9)));'
        actual=json.loads(subprocess.check_output([node,'-e',js],text=True))
        np.testing.assert_allclose(actual['load'],expected['load'],atol=1e-10)
if __name__=='__main__':unittest.main(verbosity=2)
