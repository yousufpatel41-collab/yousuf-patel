"""Constrained divisible-energy scheduling. No model is allowed to see future actual prices."""
import numpy as np

def schedule(prices, available, required_kwh, power_kw=7.4, efficiency=.9, duration_hours=1, strategy='cheapest', household_kwh=None, connection_kw=None):
    prices=np.asarray(prices,float);available=np.asarray(available,bool)
    if len(prices)!=len(available) or not np.isfinite(prices).all():raise ValueError('Invalid price/availability series')
    if not np.isfinite([required_kwh,power_kw,efficiency,duration_hours]).all() or required_kwh<0 or power_kw<=0 or not 0<efficiency<=1 or duration_hours<=0:raise ValueError('Invalid energy, power or efficiency')
    capacity=np.where(available,power_kw*duration_hours,0.)
    if household_kwh is not None:
        household_kwh=np.asarray(household_kwh,float)
        if len(household_kwh)!=len(prices) or (household_kwh<0).any() or not np.isfinite(household_kwh).all() or connection_kw is None or not np.isfinite(connection_kw) or connection_kw<=0:raise ValueError('Invalid household load')
        capacity=np.minimum(capacity,np.maximum(0,connection_kw*duration_hours-household_kwh))
    order=np.arange(len(prices)) if strategy=='immediate' else np.argsort(prices,kind='stable')
    load=np.zeros(len(prices));remaining=required_kwh/efficiency
    for i in order:
        load[i]=min(capacity[i],remaining);remaining-=load[i]
        if remaining<=1e-10:break
    return {'load':load,'delivered_kwh':float(load.sum()*efficiency),'shortfall_kwh':float(max(0,remaining*efficiency))}

def savings_capture(baseline,model,oracle):
    opportunity=baseline-oracle
    return None if opportunity<=.01 else 100*(baseline-model)/opportunity

def evaluate(actual,predicted,available,required_kwh=20,power_kw=7.4,efficiency=.9):
    baseline=schedule(actual,available,required_kwh,power_kw,efficiency,strategy='immediate')
    model=schedule(predicted,available,required_kwh,power_kw,efficiency)
    oracle=schedule(actual,available,required_kwh,power_kw,efficiency)
    costs={k:float(np.dot(actual,v['load'])) for k,v in [('immediate',baseline),('model',model),('oracle',oracle)]}
    return {**costs,'saved_eur':costs['immediate']-costs['model'],'oracle_gap_eur':costs['model']-costs['oracle'],'capture_percent':savings_capture(costs['immediate'],costs['model'],costs['oracle']),'missed_target':model['shortfall_kwh']>.01}
