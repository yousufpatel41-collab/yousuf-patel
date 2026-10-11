"""Prepare Microsoft's FOCUS sample and reconcile all exported tables.

Run: python src/build_data.py --source path/to/EA-Cost-FOCUS_1.0.csv
"""
from pathlib import Path
import argparse, calendar, hashlib, json, sqlite3
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
KEEP=['BilledCost','EffectiveCost','ListCost','BillingCurrency','BillingPeriodStart','BillingPeriodEnd',
      'ChargePeriodStart','ChargePeriodEnd','ChargeCategory','ChargeClass','ChargeDescription','ProviderName',
      'ServiceCategory','ServiceName','SubAccountId','SubAccountName','RegionName','ResourceId','ResourceName','Tags']

def tags(value):
    if pd.isna(value) or str(value).strip()=='': return {},'missing'
    try:
        result=json.loads(value)
        if not isinstance(result,dict): return {},'invalid'
        return {str(k).strip().lower():str(v).strip() for k,v in result.items()},'valid'
    except (ValueError,TypeError): return {},'invalid'

def prepare(source):
    raw=pd.read_csv(source,low_memory=False)
    if raw.duplicated().any(): raise ValueError('Exact duplicate source rows: inspect before ingestion')
    df=raw[KEEP].copy()
    for column in ['BilledCost','EffectiveCost','ListCost']:
        df[column]=pd.to_numeric(df[column],errors='raise')
        if df[column].isna().any(): raise ValueError('Missing monetary value: '+column)
    if df.BillingCurrency.nunique()!=1: raise ValueError('Choose one billing currency before aggregating')
    df['RecordId']=range(1,len(df)+1)
    start=pd.to_datetime(df.ChargePeriodStart,utc=True,errors='raise')
    end=pd.to_datetime(df.ChargePeriodEnd,utc=True,errors='raise')
    if (end<start).any(): raise ValueError('Charge period ends before it starts')
    df['ChargeDate']=start.dt.strftime('%Y-%m-%d')
    df['BillingMonth']=pd.to_datetime(df.BillingPeriodStart,utc=True).dt.strftime('%Y-%m')
    parsed=df.Tags.map(tags)
    df['TagStatus']=parsed.map(lambda v:v[1])
    df['Department']=parsed.map(lambda v:v[0].get('cost department',v[0].get('department','Unallocated')) or 'Unallocated')
    df['Environment']=parsed.map(lambda v:v[0].get('env',v[0].get('environment','Unknown')) or 'Unknown').str.lower()
    df['Environment']=df.Environment.replace({'production':'prod','development':'dev','unknown':'Unknown'})
    df['CostCenter']=parsed.map(lambda v:v[0].get('costcenter',v[0].get('cost center','Unallocated')) or 'Unallocated')
    for col in ['SubAccountName','ServiceName','ServiceCategory','RegionName','SubAccountId']:
        df[col]=df[col].fillna('Unknown').replace('', 'Unknown')
    df['AbsoluteBilledCost']=df.BilledCost.abs()
    df['UnallocatedAbsoluteCost']=df.AbsoluteBilledCost.where(df.Department.eq('Unallocated'),0)
    return df

def build(source):
    for folder in ['data','reports','sql','dashboard']:(ROOT/folder).mkdir(exist_ok=True)
    df=prepare(source)
    df.to_csv(ROOT/'data/billing_records.csv',index=False)
    dates=sorted(df.ChargeDate.unique())
    keys=['ChargeDate','BillingMonth','SubAccountId','SubAccountName','ServiceName','ServiceCategory','RegionName','Department','Environment']
    daily=df.groupby(keys,dropna=False,sort=True).agg(BilledCost=('BilledCost','sum'),EffectiveCost=('EffectiveCost','sum'),
        ListCost=('ListCost','sum'),AbsoluteBilledCost=('AbsoluteBilledCost','sum'),
        UnallocatedAbsoluteCost=('UnallocatedAbsoluteCost','sum'),RecordCount=('RecordId','count')).reset_index()
    daily.to_csv(ROOT/'data/daily_costs.csv',index=False)
    accounts=df[['SubAccountId','SubAccountName']].drop_duplicates().sort_values('SubAccountName')
    if accounts.SubAccountId.duplicated().any():raise ValueError('Account ID has conflicting names')
    budgets={'FTK Fabric':18000,'Cost Management Research':7000,'Trey Research R&D Playground':4000,
        'Trey Research IT':4500,'Trey Research Finance':1500,'contosocgitestsub':500,'EA-SUB-7F11':200,
        'Trey Research R&D Production':100,'FTK @ MS':100,'Pay-As-You-Go':50,'Unassigned':0,'Trey Research Corporate':100}
    accounts['BillingMonth']=df.BillingMonth.iloc[0]
    accounts['MonthlyBudget']=accounts.SubAccountName.map(budgets)
    if accounts.MonthlyBudget.isna().any():raise ValueError('Add an explicit scenario budget for each account')
    accounts['BudgetBasis']='Illustrative monthly budget; not provided by Microsoft'
    accounts.to_csv(ROOT/'data/budgets.csv',index=False)
    # Detect spikes using previous seven calendar days only. Zero means no recorded
    # charge in this extract, not verified zero usage in a provider invoice.
    service_daily=daily.groupby(['SubAccountId','SubAccountName','ServiceName','ChargeDate']).BilledCost.sum().reset_index()
    flags=[]
    for (account,name,service),group in service_daily.groupby(['SubAccountId','SubAccountName','ServiceName']):
        series=group.set_index('ChargeDate').BilledCost.reindex(pd.date_range(dates[0],dates[-1]).strftime('%Y-%m-%d'),fill_value=0)
        baseline=series.shift(1).rolling(7,min_periods=7).mean()
        for day,value in series.items():
            previous=baseline.loc[day]
            if pd.notna(previous) and previous>=25 and value>previous*1.8 and value-previous>100:
                flags.append({'ChargeDate':day,'SubAccountId':account,'SubAccountName':name,'ServiceName':service,
                    'BilledCost':float(value),'Previous7DayMean':float(previous),'ExcessCost':float(value-previous),
                    'Ratio':float(value/previous),'Action':'Check capacity changes, scheduled jobs and billing adjustments.'})
    anomalies=pd.DataFrame(flags,columns=['ChargeDate','SubAccountId','SubAccountName','ServiceName','BilledCost','Previous7DayMean','ExcessCost','Ratio','Action'])
    anomalies=anomalies.sort_values('ExcessCost',ascending=False)
    anomalies.to_csv(ROOT/'data/anomalies.csv',index=False)
    database=ROOT/'data/cloud_costs.sqlite'
    if database.exists():database.unlink()
    with sqlite3.connect(database) as con:
        df.to_sql('billing_records',con,index=False)
        daily.to_sql('daily_costs',con,index=False)
        accounts.to_sql('budgets',con,index=False)
        anomalies.to_sql('anomalies',con,index=False)
        con.execute('CREATE UNIQUE INDEX record_id ON billing_records(RecordId)')
        con.execute('CREATE INDEX billing_day_account ON billing_records(ChargeDate, SubAccountId)')
        con.executescript((ROOT/'sql/model.sql').read_text())
        sql_total=con.execute('SELECT SUM(BilledCost) FROM billing_records').fetchone()[0]
        budget_total=con.execute('SELECT SUM(MonthlyBudget) FROM budgets').fetchone()[0]
        checks={'source_to_sql_difference':float(df.BilledCost.sum()-sql_total),
            'source_to_daily_difference':float(df.BilledCost.sum()-daily.BilledCost.sum()),
            'daily_record_count':int(daily.RecordCount.sum()),'source_rows':len(df),
            'missing_monetary_values':int(df[['BilledCost','EffectiveCost','ListCost']].isna().sum().sum()),
            'invalid_tag_json':int(df.TagStatus.eq('invalid').sum()),
            'negative_cost_rows':int(df.BilledCost.lt(0).sum()),'all_currency_values':sorted(df.BillingCurrency.unique().tolist())}
    if abs(checks['source_to_sql_difference'])>1e-6 or abs(checks['source_to_daily_difference'])>1e-6:raise ValueError('Cost reconciliation failed')
    if checks['source_rows']!=checks['daily_record_count']:raise ValueError('Row reconciliation failed')
    days=(pd.Timestamp(dates[-1])-pd.Timestamp(dates[0])).days+1
    month_days=calendar.monthrange(int(dates[0][:4]),int(dates[0][5:7]))[1]
    metadata={'publisher':'Microsoft FinOps toolkit','source_type':'Official sample billing dataset',
        'source_url':'https://github.com/microsoft/finops-toolkit/releases/tag/v14',
        'source_file':'EA-Cost-FOCUS_1.0.csv','source_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        'currency':df.BillingCurrency.iloc[0],'period_start':dates[0],'period_end':dates[-1],
        'coverage_days':days,'month_days':month_days,'source_rows':len(df),'daily_rows':len(daily),
        'account_count':len(accounts),'service_count':int(df.ServiceName.nunique()),
        'net_billed_cost':float(df.BilledCost.sum()),'effective_cost':float(df.EffectiveCost.sum()),
        'absolute_cost':float(df.AbsoluteBilledCost.sum()),'unallocated_absolute_cost':float(df.UnallocatedAbsoluteCost.sum()),
        'positive_charges':float(df.loc[df.BilledCost>0,'BilledCost'].sum()),
        'negative_adjustments':float(df.loc[df.BilledCost<0,'BilledCost'].sum()),
        'monthly_scenario_budget':budget_total,'period_scenario_budget':budget_total*days/month_days,
        'anomaly_count':len(anomalies),
        'anomaly_rule':{'prior_calendar_days':7,'minimum_baseline_usd':25,'minimum_excess_usd':100,'ratio_threshold':1.8}}
    (ROOT/'reports/data_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (ROOT/'reports/metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    payload={'meta':metadata,'rows':daily.to_dict('records'),'budgets':accounts.to_dict('records'),
        'anomalies':anomalies.to_dict('records'),'checks':checks}
    (ROOT/'dashboard/data.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False),encoding='utf-8')
    (ROOT/'dashboard/data.js').write_text('window.CLOUD_DATA='+json.dumps(payload,separators=(',',':'),allow_nan=False)+';',encoding='utf-8')
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True,type=Path)
    args=parser.parse_args()
    build(args.source)
