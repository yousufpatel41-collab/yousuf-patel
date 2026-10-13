"""Reproducible frozen chronological price experiment; emits a static dashboard artifact."""
from pathlib import Path
import json,hashlib,time,platform,importlib.metadata
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from energy_optimizer import evaluate

ROOT=Path(__file__).resolve().parents[1]
NAMES=['Seasonal naive','LightGBM','Chronos-Bolt tiny']
MODEL_REVISION='f6ff2d2ba9168d498c015bc8dd07e3b395b31b3f'
def features(series):
    local=series.index.tz_convert('Europe/Berlin')
    x=pd.DataFrame(index=series.index)
    for lag in [168,336,504]:x[f'lag_{lag}']=series.shift(lag)
    x['hour']=local.hour;x['weekday']=local.dayofweek;x['month']=local.month
    x['annual_sin']=np.sin(2*np.pi*local.dayofyear/365.25);x['annual_cos']=np.cos(2*np.pi*local.dayofyear/365.25)
    return x

def main():
    from chronos import BaseChronosPipeline
    import torch
    torch.set_num_threads(4)
    frame=pd.read_csv(ROOT/'data/hourly_prices.csv');index=pd.to_datetime(frame.TimestampUTC,utc=True)
    prices=pd.Series(frame.PriceEURMWh.values,index=index).asfreq('h');x=features(prices)
    train=(x.index.year==2024)&x.notna().all(axis=1)&prices.notna()
    print('Training LightGBM on',int(train.sum()),'2024 observations',flush=True)
    models=[]
    for q in [.1,.5,.9]:
        m=LGBMRegressor(objective='quantile',alpha=q,n_estimators=160,num_leaves=15,max_depth=5,learning_rate=.04,min_child_samples=60,reg_lambda=2,random_state=41,n_jobs=4,verbosity=-1)
        m.fit(x[train],prices[train]);models.append(m)
    pipeline=BaseChronosPipeline.from_pretrained('amazon/chronos-bolt-tiny',revision=MODEL_REVISION,device_map='cpu',torch_dtype=torch.float32)
    checkpoint=MODEL_REVISION
    records=[];skipped=0
    for start in pd.date_range('2025-01-02','2026-10-08',freq='7D',tz='Europe/Berlin').tz_convert('UTC'):
        times=pd.date_range(start,periods=48,freq='h');target=prices.reindex(times);context=prices.loc[start-pd.Timedelta(hours=512):start-pd.Timedelta(hours=1)]
        f=x.reindex(times)
        local_start=start.tz_convert('Europe/Berlin');issue=(local_start.normalize()-pd.DateOffset(days=2))+pd.Timedelta(hours=16)
        known_end=(issue.normalize()+pd.DateOffset(days=2)).tz_convert('UTC')
        if start<known_end or target.isna().any() or f.isna().any().any() or len(context)!=512 or context.isna().any():skipped+=1;continue
        split='calibration' if start<pd.Timestamp('2025-04-01',tz='UTC') else 'validation' if start.year==2025 else 'test'
        t=time.perf_counter();naive=f.lag_168.to_numpy();lat_naive=(time.perf_counter()-t)*1000
        t=time.perf_counter();lgb=np.sort(np.column_stack([m.predict(f) for m in models]),axis=1);lat_lgb=(time.perf_counter()-t)*1000
        t=time.perf_counter();q,median=pipeline.predict_quantiles(torch.tensor(context.to_numpy(),dtype=torch.float32),prediction_length=48,quantile_levels=[.1,.5,.9]);cq=np.sort(q[0].numpy(),axis=1);lat_chronos=(time.perf_counter()-t)*1000
        records.append({'start':start.isoformat(),'issue':issue.isoformat(),'split':split,'timestamps':[int(t.timestamp()*1000) for t in times],'actual':target.to_numpy(),'predictions':{'Seasonal naive':naive,'LightGBM':lgb,'Chronos-Bolt tiny':cq},'latencies':[lat_naive,lat_lgb,lat_chronos]})
        if len(records)%10==0:print('Forecast blocks',len(records),flush=True)
    cal=[r for r in records if r['split']=='calibration']
    residual=np.concatenate([r['actual']-r['predictions']['Seasonal naive'] for r in cal])
    naive_offsets=np.quantile(residual,[.1,.9])
    for r in records:
        p=r['predictions']['Seasonal naive'];r['predictions']['Seasonal naive']=np.column_stack([p+min(0,naive_offsets[0]),p,p+max(0,naive_offsets[1])])
    expansions={}
    for name in NAMES:
        scores=np.concatenate([np.maximum(r['predictions'][name][:,0]-r['actual'],r['actual']-r['predictions'][name][:,2]) for r in cal])
        quant=min(1,np.ceil((len(scores)+1)*.8)/len(scores));expansions[name]=float(max(0,np.quantile(scores,quant,method='higher')))
    summary=[]
    for split in ['validation','test']:
        subset=[r for r in records if r['split']==split]
        for name in NAMES:
            truth=np.concatenate([r['actual'] for r in subset]);pred=np.concatenate([r['predictions'][name] for r in subset]);delta=expansions[name]
            err=truth[:,None]-pred;pin=np.mean(np.maximum(np.array([.1,.5,.9])*err,(np.array([.1,.5,.9])-1)*err))
            results=[]
            for r in subset:
                local=pd.to_datetime(r['timestamps'],unit='ms',utc=True).tz_convert('Europe/Berlin');available=(local.hour>=18)|(local.hour<7)
                actual=r['actual']/1000*1.19+.20;forecast=r['predictions'][name][:,1]/1000*1.19+.20
                result=evaluate(actual,forecast,available);result['month']=r['start'][:7];results.append(result)
            base=sum(a['immediate'] for a in results);cost=sum(a['model'] for a in results);oracle=sum(a['oracle'] for a in results)
            monthly={m:sum(a['model']-a['immediate'] for a in results if a['month']==m) for m in {a['month'] for a in results}}
            summary.append({'split':split,'model':name,'blocks':len(subset),'hours':len(truth),'mae_eur_mwh':float(np.mean(np.abs(truth-pred[:,1]))),'pinball_eur_mwh':float(pin),'coverage80_percent':float(np.mean((truth>=pred[:,0]-delta)&(truth<=pred[:,2]+delta))*100),'interval_width_eur_mwh':float(np.mean(pred[:,2]-pred[:,0]+2*delta)),'inference_ms_median':float(np.median([r['latencies'][NAMES.index(name)] for r in subset])),'immediate_eur':base,'schedule_eur':cost,'oracle_eur':oracle,'saved_eur':base-cost,'oracle_gap_eur':cost-oracle,'capture_percent':None if base-oracle<=.01 else 100*(base-cost)/(base-oracle),'missed_targets':sum(a['missed_target'] for a in results),'worst_month_extra_eur':max(0,max(monthly.values()))})
    val={r['model']:r for r in summary if r['split']=='validation'};baseline=val['Seasonal naive'];qualified=[]
    for name in NAMES[1:]:
        row=val[name];row['promotion_passed']=row['schedule_eur']<=baseline['schedule_eur']*.98 and row['missed_targets']<=baseline['missed_targets'] and row['coverage80_percent']>=75 and row['inference_ms_median']<5000
        if row['promotion_passed']:qualified.append(name)
    selected=min(qualified,key=lambda n:val[n]['schedule_eur']) if qualified else 'Seasonal naive'
    for r in records:
        r['actual']=np.round(r['actual'],4).tolist();r['predictions']={name:np.round(p,4).tolist() for name,p in r['predictions'].items()}
    report={'version':1,'built_on':'2026-10-13','selected_model':selected,'source_sha256':hashlib.sha256((ROOT/'data/hourly_prices.csv').read_bytes()).hexdigest(),'checkpoint':'amazon/chronos-bolt-tiny','checkpoint_revision':checkpoint,'training_year':2024,'calibration':'2025-01 to 2025-03','validation':'2025-04 to 2025-12','test':'2026-01 to 2026-10-08, incomplete year','skipped_blocks':skipped,'calibration_blocks':len(cal),'conformal_expansion_eur_mwh':expansions,'summary':summary,'blocks':records,'environment':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ['lightgbm','chronos-forecasting','torch','transformers','numpy','pandas']}}}
    (ROOT/'reports/forecast_experiment.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    payload=json.dumps(report,separators=(',',':'),allow_nan=False)
    (ROOT/'dashboard/forecast-data.js').write_text('window.FORECAST_EXPERIMENT='+payload+';',encoding='utf-8')
    pd.DataFrame(summary).to_csv(ROOT/'reports/forecast_metrics.csv',index=False)
    print(json.dumps({'selected':selected,'summary':summary,'skipped':skipped},indent=2),flush=True)

if __name__=='__main__':main()
