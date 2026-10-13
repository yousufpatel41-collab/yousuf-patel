"""V2: published-price rolling baselines, monthly retraining and paired block bootstrap."""
from pathlib import Path
import hashlib,json,time
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from build_forecast_experiment import features,MODEL_REVISION
from rolling_charging import known_until,run_policy,paired_ci
ROOT=Path(__file__).resolve().parents[1]
MODEL_NAMES=['Seasonal naive','LightGBM fixed','LightGBM monthly','Chronos-Bolt tiny']
PROTOCOL_SHA='788e4c1d1bac14e0c53760e391c8dfb069cb01ae'

def train_models(x,y,mask):
    result=[]
    for q in [.1,.5,.9]:
        model=LGBMRegressor(objective='quantile',alpha=q,n_estimators=160,num_leaves=15,max_depth=5,learning_rate=.04,min_child_samples=60,reg_lambda=2,random_state=41,n_jobs=4,verbosity=-1)
        model.fit(x[mask],y[mask]);result.append(model)
    return result

def main():
    from chronos import BaseChronosPipeline
    import torch
    torch.set_num_threads(4)
    df=pd.read_csv(ROOT/'data/hourly_prices.csv');y=pd.Series(df.PriceEURMWh.values,index=pd.to_datetime(df.TimestampUTC,utc=True)).asfreq('h');x=features(y)
    valid=x.notna().all(axis=1)&y.notna();fixed=train_models(x,y,valid&(y.index.year==2024));monthly={}
    pipe=BaseChronosPipeline.from_pretrained('amazon/chronos-bolt-tiny',revision=MODEL_REVISION,device_map='cpu',torch_dtype=torch.float32)
    sessions=[];forecast_rows=[];skipped=0;cache={};retraining=[]
    def predict(name,cutoff,times,decision):
        if not len(times):return np.empty((0,3)),0
        model_month=decision.tz_convert('Europe/Berlin').strftime('%Y-%m')
        key=(name,cutoff.isoformat(),model_month if name=='LightGBM monthly' else '');horizon=pd.date_range(cutoff,periods=48,freq='h')
        if key not in cache:
            started=time.perf_counter();f=x.reindex(horizon)
            if f.isna().any().any():raise ValueError('Missing lag context')
            if name=='Seasonal naive':p=f.lag_168.to_numpy();q=np.column_stack([p,p,p])
            elif name.startswith('LightGBM'):
                models=fixed
                if name=='LightGBM monthly':
                    month=model_month;boundary=pd.Timestamp(month+'-01',tz='Europe/Berlin').tz_convert('UTC')
                    if month not in monthly:
                        mask=valid&(y.index<boundary);monthly[month]=train_models(x,y,mask);retraining.append({'month':month,'training_labels_before':boundary.isoformat(),'training_rows':int(mask.sum())})
                    models=monthly[month]
                q=np.sort(np.column_stack([m.predict(f) for m in models]),axis=1)
            else:
                context=y.loc[cutoff-pd.Timedelta(hours=512):cutoff-pd.Timedelta(hours=1)]
                if len(context)!=512 or context.isna().any():raise ValueError('Missing contiguous Chronos context')
                out,_=pipe.predict_quantiles(torch.tensor(context.to_numpy(),dtype=torch.float32),prediction_length=48,quantile_levels=[.1,.5,.9]);q=np.sort(out[0].numpy(),axis=1)
            cache[key]=(q,(time.perf_counter()-started)*1000)
        q,latency=cache[key];offset=((times-cutoff)/pd.Timedelta(hours=1)).astype(int)
        return q[offset],latency
    for arrival in pd.date_range('2025-01-02 18:00','2026-10-08 18:00',freq='3D',tz='Europe/Berlin'):
        start=arrival.tz_convert('UTC');split='calibration' if arrival<pd.Timestamp('2025-04-01',tz='Europe/Berlin') else 'validation' if arrival.year==2025 else 'test'
        for nights in [1,2]:
            end=(arrival.normalize()+pd.DateOffset(days=nights)+pd.Timedelta(hours=7)).tz_convert('UTC');times=pd.date_range(start,end,freq='h',inclusive='left');raw=y.reindex(times)
            if raw.isna().any():skipped+=1;continue
            avail=(times.tz_convert('Europe/Berlin').hour>=18)|(times.tz_convert('Europe/Berlin').hour<7)
            first=(arrival.normalize()+pd.DateOffset(days=1)+pd.Timedelta(hours=7)).tz_convert('UTC');first_stop=int((times<first).sum())
            deadlines=[(len(times),20)] if nights==1 else [(first_stop,8),(len(times),20)]
            unknown=times[times>=known_until(start)];predictions={}
            try:
                for name in MODEL_NAMES:
                    q,latency=predict(name,known_until(start),unknown,start);predictions[name]=q
                    if len(unknown):forecast_rows.append({'split':split,'case':'two_night','model':name,'actual':y.reindex(unknown).to_numpy(),'q':q,'latency':latency})
            except ValueError:skipped+=1;continue
            gross=raw.to_numpy()/1000*1.19+.2;policies={}
            for name in ['immediate','known_only','oracle']:
                policies[name]=run_policy(gross,times,avail,deadlines,name)
            for name in MODEL_NAMES:
                policies[name]=run_policy(gross,times,avail,deadlines,name,forecast=lambda cutoff,ts,decision,n=name:predict(n,cutoff,ts,decision)[0][:,1]/1000*1.19+.2)
            sessions.append({'start':start.isoformat(),'arrival_local':arrival.isoformat(),'split':split,'case':'overnight' if nights==1 else 'two_night','hours':len(times),'deadlines':deadlines,'policies':{name:{'cost':p['cost'],'missed':p['missed'],'shortfalls':p['shortfalls']} for name,p in policies.items()}})
            if nights==2 and split=='test' and len([s for s in sessions if s['case']=='two_night' and s['split']=='test'])<=6:
                sessions[-1]['example']={'timestamps':[int(ts.timestamp()*1000) for ts in times],'actual_eur_mwh':raw.to_numpy().tolist(),'known_until':known_until(start).isoformat(),'unknown_timestamps':[int(ts.timestamp()*1000) for ts in unknown],'initial_forecasts':{name:q.tolist() for name,q in predictions.items()},'plans':{name:np.round(p['load'],8).tolist() for name,p in policies.items()},'logs':{name:p['log'] for name,p in policies.items()}}
        if len(sessions)%40==0:print('V2 sessions',len(sessions),flush=True)
    # Unknown-hour calibration only; known hours never inflate forecast scores.
    expansions={};offsets={};diagnostics=[]
    for name in MODEL_NAMES:
        cal=[r for r in forecast_rows if r['split']=='calibration' and r['model']==name];truth=np.concatenate([r['actual'] for r in cal]);pred=np.concatenate([r['q'] for r in cal])
        if name=='Seasonal naive':offsets[name]=np.quantile(truth-pred[:,1],[.1,.9]).tolist();pred[:,0]+=offsets[name][0];pred[:,2]+=offsets[name][1]
        score=np.maximum(pred[:,0]-truth,truth-pred[:,2]);expansions[name]=float(max(0,np.quantile(score,min(1,np.ceil((len(score)+1)*.8)/len(score)),method='higher')))
        for split in ['validation','test']:
            rows=[r for r in forecast_rows if r['split']==split and r['model']==name];actual=np.concatenate([r['actual'] for r in rows]);q=np.concatenate([r['q'] for r in rows]).copy()
            if name in offsets:q[:,0]+=offsets[name][0];q[:,2]+=offsets[name][1]
            delta=expansions[name];err=actual[:,None]-q;pin=np.mean(np.maximum(np.array([.1,.5,.9])*err,(np.array([.1,.5,.9])-1)*err))
            diagnostics.append({'split':split,'model':name,'unknown_hours':len(actual),'mae_eur_mwh':float(np.mean(abs(actual-q[:,1]))),'pinball_eur_mwh':float(pin),'coverage80_percent':float(np.mean((actual>=q[:,0]-delta)&(actual<=q[:,2]+delta))*100),'width_eur_mwh':float(np.mean(q[:,2]-q[:,0]+2*delta)),'latency_ms_median':float(np.median([r['latency'] for r in rows]))})
    summaries=[];comparisons=[];selected={}
    for case in ['overnight','two_night']:
        for split in ['validation','test']:
            rows=[s for s in sessions if s['case']==case and s['split']==split]
            base=np.array([s['policies']['immediate']['cost'] for s in rows]);known=np.array([s['policies']['known_only']['cost'] for s in rows]);oracle=np.array([s['policies']['oracle']['cost'] for s in rows])
            for name in ['immediate','known_only',*MODEL_NAMES,'oracle']:
                costs=np.array([s['policies'][name]['cost'] for s in rows]);monthly_savings={m:float(sum(costs[i]-base[i] for i,s in enumerate(rows) if s['arrival_local'][:7]==m)) for m in {s['arrival_local'][:7] for s in rows}}
                summaries.append({'case':case,'split':split,'strategy':name,'sessions':len(rows),'cost_eur':float(costs.sum()),'saved_immediate_eur':float(sum(base-costs)),'saved_known_only_eur':float(sum(known-costs)),'mean_saved_immediate_eur':float(np.mean(base-costs)),'mean_saved_known_only_eur':float(np.mean(known-costs)),'ci_immediate_eur':paired_ci(base-costs),'ci_known_only_eur':paired_ci(known-costs),'oracle_gap_eur':float(sum(costs-oracle)),'capture_percent':None if sum(base-oracle)<=.01 else float(100*sum(base-costs)/sum(base-oracle)),'worst_month_extra_eur':max(0,max(monthly_savings.values())),'missed_deadlines':sum(s['policies'][name]['missed'] for s in rows)})
            diff=np.array([s['policies']['LightGBM monthly']['cost']-s['policies']['Chronos-Bolt tiny']['cost'] for s in rows]);comparisons.append({'case':case,'split':split,'contrast':'Chronos savings versus monthly LightGBM','mean_eur_per_session':float(diff.mean()),'ci95_eur_per_session':paired_ci(diff)})
        val={r['strategy']:r for r in summaries if r['case']==case and r['split']=='validation'};qualified=[]
        for name in MODEL_NAMES:
            d=next(r for r in diagnostics if r['split']=='validation' and r['model']==name)
            row=val[name];row['promotion_passed']=case=='two_night' and row['cost_eur']<=val['known_only']['cost_eur']*.98 and row['missed_deadlines']<=val['known_only']['missed_deadlines'] and row['ci_known_only_eur'][0]>0 and d['coverage80_percent']>=75 and d['latency_ms_median']<5000
            if row['promotion_passed']:qualified.append(name)
        selected[case]=min(qualified,key=lambda n:val[n]['cost_eur']) if qualified else 'known_only'
    report={'version':2,'protocol_commit':PROTOCOL_SHA,'protocol_tag':'v2-protocol-2026-10-13','protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL_V2.md').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'data/hourly_prices.csv').read_bytes()).hexdigest(),'selected':selected,'sessions':sessions,'summary':summaries,'paired_comparisons':comparisons,'forecast_metrics':diagnostics,'conformal_expansion':expansions,'monthly_retraining':retraining,'skipped_sessions':skipped,'bootstrap':{'resamples':5000,'seed':41,'block_sessions':3},'pilot_completed':0}
    (ROOT/'reports/rolling_experiment.json').write_text(json.dumps(report,separators=(',',':'),allow_nan=False),encoding='utf-8')
    browser={k:v for k,v in report.items() if k!='sessions'};browser['examples']=[s for s in sessions if 'example' in s]
    (ROOT/'dashboard/rolling-data.js').write_text('window.ROLLING_EXPERIMENT='+json.dumps(browser,separators=(',',':'),allow_nan=False)+';',encoding='utf-8')
    pd.DataFrame(summaries).to_csv(ROOT/'reports/rolling_metrics.csv',index=False)
    print(json.dumps({'selected':selected,'test':[r for r in summaries if r['split']=='test' and r['strategy'] in ['known_only','Chronos-Bolt tiny','LightGBM monthly']],'contrasts':comparisons,'skipped':skipped},indent=2),flush=True)

if __name__=='__main__':main()
