from pathlib import Path
import sys,json,unittest
import numpy as np
import pandas as pd
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rolling_charging import allocate,known_until,run_policy,paired_ci

class RollingTests(unittest.TestCase):
    def test_nested_departure_constraints_match_independent_lp(self):
        rng=np.random.default_rng(14)
        for _ in range(25):
            prices=rng.uniform(-.2,.8,37);available=np.ones(37,dtype=bool);available[13:24]=False
            load=allocate(prices,available,[(13,8),(37,20)])
            lp=linprog(prices,A_eq=np.ones((1,37)),b_eq=[20/.9],A_ub=-np.concatenate([np.ones(13),np.zeros(24)])[None,:],b_ub=[-8/.9],bounds=[(0,7.4 if a else 0) for a in available],method='highs')
            self.assertTrue(lp.success);self.assertAlmostEqual(float(prices@load),lp.fun,places=8)
    def test_publication_boundary_changes_at_16_local(self):
        self.assertEqual(known_until(pd.Timestamp('2026-03-28 15:00',tz='Europe/Berlin')),pd.Timestamp('2026-03-29',tz='Europe/Berlin').tz_convert('UTC'))
        self.assertEqual(known_until(pd.Timestamp('2026-03-28 16:00',tz='Europe/Berlin')),pd.Timestamp('2026-03-30',tz='Europe/Berlin').tz_convert('UTC'))
    def test_overnight_model_never_receives_unknown_future(self):
        times=pd.date_range(pd.Timestamp('2026-01-02 18:00',tz='Europe/Berlin').tz_convert('UTC'),periods=13,freq='h');actual=np.linspace(.1,.4,13)
        seen=[]
        def forecast(cutoff,unknown,decision):seen.extend(unknown);return np.array([])
        model=run_policy(actual,times,np.ones(13,bool),[(13,20)],'forecast',forecast)
        known=run_policy(actual,times,np.ones(13,bool),[(13,20)],'known_only')
        self.assertEqual(seen,[]);np.testing.assert_allclose(model['load'],known['load'])
    def test_future_actual_prices_do_not_affect_early_dispatch(self):
        start=pd.Timestamp('2026-01-02 18:00',tz='Europe/Berlin').tz_convert('UTC');times=pd.date_range(start,periods=37,freq='h');actual=np.full(37,.3);available=(times.tz_convert('Europe/Berlin').hour>=18)|(times.tz_convert('Europe/Berlin').hour<7)
        future=lambda cutoff,unknown,decision:np.full(len(unknown),.1)
        a=run_policy(actual,times,available,[(13,8),(37,20)],'model',future)
        changed=actual.copy();changed[np.asarray(times>=known_until(start))]=100
        b=run_policy(changed,times,available,[(13,8),(37,20)],'model',future)
        reveal=int(np.where(times==pd.Timestamp('2026-01-03 16:00',tz='Europe/Berlin').tz_convert('UTC'))[0][0]);np.testing.assert_allclose(a['load'][:reveal],b['load'][:reveal])
    def test_bootstrap_is_paired_and_reproducible(self):
        self.assertEqual(paired_ci([1,2,3,4]),paired_ci([1,2,3,4]));self.assertEqual(paired_ci([0]*10),[0,0])
    def test_saved_results_respect_arrival_and_deadlines(self):
        d=json.loads((ROOT/'reports/rolling_experiment.json').read_text())
        for s in d['sessions']:
            self.assertEqual(pd.Timestamp(s['arrival_local']).hour,18)
            self.assertTrue(all(p['missed']==0 for p in s['policies'].values()))
            self.assertTrue(all(p['cost']>=s['policies']['oracle']['cost']-1e-8 for p in s['policies'].values()))
        for r in d['summary']:
            if r['case']=='overnight' and r['strategy'] in ['Seasonal naive','LightGBM fixed','LightGBM monthly','Chronos-Bolt tiny']:self.assertAlmostEqual(r['saved_known_only_eur'],0,places=8)
    def test_monthly_retraining_records_have_past_boundaries(self):
        d=json.loads((ROOT/'reports/rolling_experiment.json').read_text())
        for row in d['monthly_retraining']:
            self.assertEqual(pd.Timestamp(row['training_labels_before']).tz_convert('Europe/Berlin').strftime('%Y-%m-%d'),row['month']+'-01')
    def test_proto_is_not_rewritten_after_tag(self):
        import hashlib
        d=json.loads((ROOT/'reports/rolling_experiment.json').read_text());self.assertEqual(hashlib.sha256((ROOT/'PROTOCOL_V2.md').read_bytes()).hexdigest(),d['protocol_sha256'])
        self.assertEqual(d['protocol_commit'],'788e4c1d1bac14e0c53760e391c8dfb069cb01ae')
    def test_js_python_rolling_actions_match(self):
        import shutil,subprocess
        node=shutil.which('node')
        if not node:self.skipTest('Node optional')
        d=json.loads((ROOT/'reports/rolling_experiment.json').read_text());s=next(s for s in d['sessions'] if 'example' in s);e=s['example'];times=pd.to_datetime(e['timestamps'],unit='ms',utc=True);available=(times.tz_convert('Europe/Berlin').hour>=18)|(times.tz_convert('Europe/Berlin').hour<7)
        forecast={str(ts):q[1]/1000*1.19+.2 for ts,q in zip(e['unknown_timestamps'],e['initial_forecasts']['Chronos-Bolt tiny'])};prices=(np.array(e['actual_eur_mwh'])/1000*1.19+.2).tolist()
        js='const c=require('+json.dumps(str(ROOT/'dashboard/energy-core.js'))+');console.log(JSON.stringify(c.rollingSchedule('+','.join(json.dumps(x) for x in [prices,e['timestamps'],available.tolist(),s['deadlines'],'Chronos-Bolt tiny',forecast])+')));'
        result=json.loads(subprocess.check_output([node,'-e',js],text=True));np.testing.assert_allclose(result['load'],e['plans']['Chronos-Bolt tiny'],atol=1e-7)
if __name__=='__main__':unittest.main(verbosity=2)
