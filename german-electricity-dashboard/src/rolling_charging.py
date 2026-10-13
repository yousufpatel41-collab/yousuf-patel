"""Continuous charging with cumulative departure targets and causal publication boundaries."""
import numpy as np
import pandas as pd

def known_until(decision):
    local=pd.Timestamp(decision).tz_convert('Europe/Berlin')
    days=2 if local.hour>=16 else 1
    return (local.normalize()+pd.DateOffset(days=days)).tz_convert('UTC')

def allocate(prices,available,deadlines,power=7.4,efficiency=.9):
    prices=np.asarray(prices,float);available=np.asarray(available,bool)
    if prices.shape!=available.shape or not np.isfinite(prices).all() or not np.isfinite([power,efficiency]).all() or power<=0 or not 0<efficiency<=1:raise ValueError('Invalid allocation inputs')
    load=np.zeros(len(prices));caps=np.where(available,power,0.)
    for stop,target in sorted(deadlines):
        if not 0<=stop<=len(prices) or target<0 or not np.isfinite(target):raise ValueError('Invalid deadline')
        need=max(0,target/efficiency-load[:stop].sum())
        for i in np.argsort(prices[:stop],kind='stable'):
            extra=min(max(0,caps[i]-load[i]),need);load[i]+=extra;need-=extra
            if need<=1e-10:break
    return load

def run_policy(actual,times,available,deadlines,policy,forecast=None,power=7.4,efficiency=.9):
    actual=np.asarray(actual,float);load=np.zeros(len(actual));log=[]
    for i,ts in enumerate(times):
        cutoff=known_until(ts)
        remaining=[(stop-i,max(0,target-load[:i].sum()*efficiency)) for stop,target in deadlines if stop>i]
        if not remaining:break
        if policy=='immediate':plan=allocate(np.arange(len(actual)-i,dtype=float),available[i:],remaining,power,efficiency)
        elif policy=='oracle':plan=allocate(actual[i:],available[i:],remaining,power,efficiency)
        else:
            known=np.asarray(times[i:]<cutoff)
            if policy=='known_only':
                costs=np.where(known,actual[i:],0);allowed=available[i:]&known
            else:
                future=forecast(cutoff,times[i:][~known],ts);costs=actual[i:].copy();costs[~known]=future;allowed=available[i:]
            plan=allocate(costs,allowed,remaining,power,efficiency)
        load[i]=plan[0]
        log.append({'time':int(ts.timestamp()*1000),'known_until':cutoff.isoformat(),'grid_kwh':float(load[i])})
    shortfalls=[max(0,target-load[:stop].sum()*efficiency) for stop,target in deadlines]
    return {'cost':float(actual@load),'load':load,'shortfalls':shortfalls,'missed':sum(s>.01 for s in shortfalls),'log':log}

def paired_ci(values,resamples=5000,seed=41,block_length=3):
    values=np.asarray(values,float);n=len(values)
    if not n:return [None,None]
    rng=np.random.default_rng(seed);starts=rng.integers(0,n,size=(resamples,int(np.ceil(n/block_length))))
    indices=((starts[:,:,None]+np.arange(block_length))%n).reshape(resamples,-1)[:,:n]
    return np.quantile(values[indices].mean(axis=1),[.025,.975]).tolist()
