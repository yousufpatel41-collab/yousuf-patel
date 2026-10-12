"""Download, preserve and validate SMARD's published hourly DE/LU prices."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import argparse,calendar,hashlib,json,sqlite3,time,urllib.request
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE='https://www.smard.de/app/chart_data/4169/DE/'
START='2024-01-01'
END='2026-10-11'

def fetch(url,path):
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    for attempt in range(4):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'Electricity-cost-portfolio/1.0'})
            with urllib.request.urlopen(request,timeout=60) as response:raw=response.read()
            result=json.loads(raw);path.write_bytes(raw);return result
        except Exception:
            if attempt==3:raise
            time.sleep(1+attempt)

def build(end=END):
    for d in ['data/raw','reports','dashboard','sql']:(ROOT/d).mkdir(parents=True,exist_ok=True)
    rawdir=ROOT/'data/raw'
    index=fetch(BASE+'index_hour.json',rawdir/'index_hour.json')
    start=pd.Timestamp(START,tz='Europe/Berlin').tz_convert('UTC')
    stop=(pd.Timestamp(end,tz='Europe/Berlin')+pd.DateOffset(days=1)).tz_convert('UTC')
    stamps=[t for t in index['timestamps'] if start-pd.Timedelta(days=7)<=pd.Timestamp(t,unit='ms',tz='UTC')<stop]
    def get(t):
        filename=f'4169_DE_hour_{t}.json';return filename,fetch(BASE+filename,rawdir/filename)
    with ThreadPoolExecutor(max_workers=6) as pool:chunks=list(pool.map(get,stamps))
    observed={};nulls=0
    for name,chunk in chunks:
        for stamp,price in chunk['series']:
            dt=pd.Timestamp(stamp,unit='ms',tz='UTC')
            if not start<=dt<stop:continue
            if price is None:nulls+=1;continue
            if stamp in observed and observed[stamp]['PriceEURMWh']!=price:raise ValueError('Conflicting repeated timestamp')
            observed[stamp]={'TimestampMs':stamp,'PriceEURMWh':float(price),'SourceFile':name}
    df=pd.DataFrame(observed.values()).sort_values('TimestampMs').reset_index(drop=True)
    utc=pd.to_datetime(df.TimestampMs,unit='ms',utc=True);local=utc.dt.tz_convert('Europe/Berlin')
    expected=pd.date_range(start,stop,freq='h',inclusive='left')
    missing=expected.difference(pd.DatetimeIndex(utc))
    if not (df.TimestampMs.diff().dropna()%3600000==0).all():raise ValueError('Unexpected source resolution')
    df['TimestampUTC']=utc.dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    df['LocalTimestamp']=local.dt.strftime('%Y-%m-%dT%H:%M:%S%z')
    df['Date']=local.dt.strftime('%Y-%m-%d');df['Month']=local.dt.strftime('%Y-%m');df['Year']=local.dt.year
    df['Hour']=local.dt.hour;df['Weekday']=local.dt.dayofweek;df['IsWeekend']=(df.Weekday>=5).astype(int)
    df['IsNegative']=(df.PriceEURMWh<0).astype(int);df['PriceEURKWh']=df.PriceEURMWh/1000
    df['PriceCentKWh']=df.PriceEURMWh/10;df['DurationHours']=1.0
    # One monthly kWh unit spread evenly across elapsed hours of each local month.
    def monthhours(m):
        a=pd.Timestamp(m+'-01',tz='Europe/Berlin');b=a+pd.offsets.MonthBegin(1)
        return (b.tz_convert('UTC')-a.tz_convert('UTC')).total_seconds()/3600
    df['MonthlyConsumptionWeight']=df.Month.map(lambda m:1/monthhours(m))
    daily=[]
    for day,g in df.groupby('Date',sort=True):
        base=g[g.Hour.isin([18,19,20,21])]
        if len(base)!=4:raise ValueError('Evening window incomplete: '+day)
        cheapest=g.nsmallest(4,'PriceEURMWh')
        daily.append({'Date':day,'Month':day[:7],'Year':int(day[:4]),'Weekday':int(g.Weekday.iloc[0]),'Hours':len(g),
            'MeanEURMWh':float(g.PriceEURMWh.mean()),'MinimumEURMWh':float(g.PriceEURMWh.min()),'MaximumEURMWh':float(g.PriceEURMWh.max()),
            'NegativeHours':int(g.IsNegative.sum()),'SumEURMWh':float(g.PriceEURMWh.sum()),
            'EveningMeanEURMWh':float(base.PriceEURMWh.mean()),'Cheapest4MeanEURMWh':float(cheapest.PriceEURMWh.mean()),
            'CheapestHours':', '.join(cheapest.LocalTimestamp.str[11:16].tolist()),
            'ConsumptionWeight':float(g.MonthlyConsumptionWeight.sum()),
            'WholesaleCostPerMonthlyKWh':float((g.PriceEURKWh*g.MonthlyConsumptionWeight).sum())})
    daily=pd.DataFrame(daily)
    monthly=df.groupby('Month',sort=True).agg(Hours=('TimestampMs','count'),SumEURMWh=('PriceEURMWh','sum'),MeanEURMWh=('PriceEURMWh','mean'),MinimumEURMWh=('PriceEURMWh','min'),MaximumEURMWh=('PriceEURMWh','max'),NegativeHours=('IsNegative','sum'),ConsumptionWeight=('MonthlyConsumptionWeight','sum')).reset_index()
    monthly['NegativeShare']=monthly.NegativeHours/monthly.Hours
    yearly=df.groupby('Year').agg(Hours=('TimestampMs','count'),MeanEURMWh=('PriceEURMWh','mean'),NegativeHours=('IsNegative','sum'),MinimumEURMWh=('PriceEURMWh','min'),MaximumEURMWh=('PriceEURMWh','max')).reset_index()
    for name,table in [('hourly_prices',df),('daily_prices',daily),('monthly_prices',monthly),('yearly_prices',yearly)]:table.to_csv(ROOT/'data'/f'{name}.csv',index=False)
    profile=df.groupby(['Year','Weekday','Hour']).agg(MeanEURMWh=('PriceEURMWh','mean'),Observations=('TimestampMs','count')).reset_index();profile.to_csv(ROOT/'data/hour_profiles.csv',index=False)
    assumptions={'monthly_kwh':250,'flat_eur_kwh':0.32,'dynamic_adder_eur_kwh':0.20,'vat_multiplier':1.19,'monthly_fixed_fee':10,'flexible_kwh_per_day':12}
    (ROOT/'data/tariff_assumptions.json').write_text(json.dumps(assumptions,indent=2))
    db=ROOT/'data/electricity.sqlite'
    if db.exists():db.unlink()
    with sqlite3.connect(db) as con:
        for name,table in [('hourly_prices',df),('daily_prices',daily),('monthly_prices',monthly),('yearly_prices',yearly),('hour_profiles',profile)]:table.to_sql(name,con,index=False)
        con.execute('CREATE UNIQUE INDEX utc_time ON hourly_prices(TimestampMs)')
        con.execute('CREATE INDEX local_date ON hourly_prices(Date)')
        con.executescript((ROOT/'sql/model.sql').read_text(encoding='utf-8'))
        total=con.execute('SELECT SUM(PriceEURMWh) FROM hourly_prices').fetchone()[0]
    checks={'expected_hours':len(expected),'observed_hours':len(df),'missing_hours':len(missing),'duplicate_utc_timestamps':int(df.TimestampMs.duplicated().sum()),'null_values_in_requested_window':nulls,'price_sum_sql_difference':float(df.PriceEURMWh.sum()-total),'price_sum_daily_difference':float(df.PriceEURMWh.sum()-daily.SumEURMWh.sum()),'days_23_hours':int(daily.Hours.eq(23).sum()),'days_25_hours':int(daily.Hours.eq(25).sum())}
    if abs(checks['price_sum_sql_difference'])>1e-6 or abs(checks['price_sum_daily_difference'])>1e-6:raise ValueError('Reconciliation failed')
    meta={'source':'Bundesnetzagentur | SMARD.de','source_url':'https://www.smard.de/en','license_url':'https://www.smard.de/en/datennutzung','series':'4169 / DE / hour','market':'Germany/Luxembourg bidding zone','resolution':'Published hourly price; later quarter-hour market observations are hourly aggregated by source','start':START,'end':end,'retrieved_on':'2026-10-12','hours':len(df),'days':len(daily),'months':len(monthly),'mean_eur_mwh':float(df.PriceEURMWh.mean()),'negative_hours':int(df.IsNegative.sum()),'minimum':float(df.PriceEURMWh.min()),'maximum':float(df.PriceEURMWh.max()),'annual':yearly.to_dict('records'),'assumptions':assumptions}
    meta['missing_dates']=sorted(set(missing.tz_convert('Europe/Berlin').strftime('%Y-%m-%d')))
    meta['coverage_percent']=len(df)/len(expected)*100
    (ROOT/'reports/metadata.json').write_text(json.dumps(meta,indent=2));(ROOT/'reports/data_checks.json').write_text(json.dumps(checks,indent=2))
    manifest=[{'file':n,'url':BASE+n,'sha256':hashlib.sha256((rawdir/n).read_bytes()).hexdigest()} for n,_ in chunks]
    (ROOT/'data/source_manifest.json').write_text(json.dumps(manifest,indent=2))
    payload={'meta':meta,'checks':checks,'daily':daily.to_dict('records'),'monthly':monthly.to_dict('records'),'profiles':profile.to_dict('records'),'hours':df[['TimestampMs','PriceEURMWh']].values.tolist()}
    text=json.dumps(payload,separators=(',',':'),allow_nan=False)
    (ROOT/'dashboard/data.json').write_text(text);(ROOT/'dashboard/data.js').write_text('window.ELECTRICITY_DATA='+text+';')
    print(json.dumps({'metadata':meta,'checks':checks},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--end',default=END);build(p.parse_args().end)
