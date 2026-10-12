"""Create a CSV-backed native Power BI project with inspectable DAX."""
from pathlib import Path
import json,uuid
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];PBI=ROOT/'powerbi'
SCHEMA='https://developer.microsoft.com/json-schemas/fabric/item/'
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def build():
    data=ROOT/'data';meta=json.loads((ROOT/'reports/metadata.json').read_text())
    dates=pd.DataFrame({'Date':pd.date_range(meta['start'],meta['end']).strftime('%Y-%m-%d')});dates['Year']=dates.Date.str[:4].astype(int);dates['Month']=dates.Date.str[:7];dates.to_csv(data/'calendar.csv',index=False)
    pd.DataFrame([meta['assumptions']]).to_csv(data/'tariff_assumptions.csv',index=False)
    datasets={
        'Prices':('daily_prices.csv',[('Date','dateTime'),('Hours','int64'),('SumEURMWh','double'),('NegativeHours','int64'),('MeanEURMWh','double'),('ConsumptionWeight','double'),('WholesaleCostPerMonthlyKWh','double'),('EveningMeanEURMWh','double'),('Cheapest4MeanEURMWh','double')]),
        'Hourly':('hourly_prices.csv',[('TimestampUTC','string'),('Date','dateTime'),('Hour','int64'),('Weekday','int64'),('PriceEURMWh','double'),('IsNegative','int64')]),
        'Calendar':('calendar.csv',[('Date','dateTime'),('Year','int64'),('Month','string')]),
        'Scenario':('tariff_assumptions.csv',[(k,'double') for k in meta['assumptions']])}
    money='€#,0.00;(€#,0.00);€0.00'
    measures={
        'Observed hours':('SUM(Prices[Hours])','#,0'),
        'Mean wholesale EUR per MWh':('DIVIDE(SUM(Prices[SumEURMWh]), [Observed hours])',money),
        'Negative hours':('SUM(Prices[NegativeHours])','#,0'),
        'Negative share':('DIVIDE([Negative hours], [Observed hours])','0.0%'),
        'Equivalent observed months':('SUM(Prices[ConsumptionWeight])','0.000'),
        'Scenario consumption kWh':('IF([Observed hours]>0, [Equivalent observed months] * SUM(Scenario[monthly_kwh]), BLANK())','#,0.0'),
        'Flat tariff EUR':('IF([Observed hours]>0, [Scenario consumption kWh] * SUM(Scenario[flat_eur_kwh]) + [Equivalent observed months] * SUM(Scenario[monthly_fixed_fee]), BLANK())',money),
        'Dynamic tariff EUR':('IF([Observed hours]>0, SUM(Prices[WholesaleCostPerMonthlyKWh]) * SUM(Scenario[monthly_kwh]) * SUM(Scenario[vat_multiplier]) + [Scenario consumption kWh] * SUM(Scenario[dynamic_adder_eur_kwh]) + [Equivalent observed months] * SUM(Scenario[monthly_fixed_fee]), BLANK())',money),
        'Flat minus dynamic EUR':('IF([Observed hours]>0, [Flat tariff EUR] - [Dynamic tariff EUR], BLANK())',money),
        'Flexible timing difference EUR':('IF([Observed hours]>0, (SUM(Prices[EveningMeanEURMWh])-SUM(Prices[Cheapest4MeanEURMWh])) / 1000 * SUM(Scenario[flexible_kwh_per_day]) * SUM(Scenario[vat_multiplier]), BLANK())',money),
        'Mean clock hour EUR per MWh':('AVERAGE(Hourly[PriceEURMWh])',money)}
    tables=[]
    for name,(file,cols) in datasets.items():
        types=', '.join('{"'+c+'", '+{'string':'type text','dateTime':'type date','int64':'Int64.Type','double':'type number'}[t]+'}' for c,t in cols)
        expr=['let',f'    Source = Csv.Document(File.Contents(DataFolder & "{file}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),','    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',f'    Typed = Table.TransformColumnTypes(Headers, {{{types}}}, "en-US")','in','    Typed']
        table={'name':name,'columns':[{'name':c,'dataType':t,'sourceColumn':c,'summarizeBy':'none'} for c,t in cols],'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expr}}]}
        if name=='Prices':table['measures']=[{'name':n,'expression':e,'formatString':f} for n,(e,f) in measures.items()]
        tables.append(table)
    relationships=[{'name':str(uuid.uuid5(uuid.NAMESPACE_URL,name+'CalendarDate')),'fromTable':name,'fromColumn':'Date','toTable':'Calendar','toColumn':'Date','fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection'} for name in ['Prices','Hourly']]
    model={'name':'German electricity cost review','compatibilityLevel':1567,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','tables':tables,'relationships':relationships,'expressions':[{'name':'DataFolder','kind':'m','expression':'"'+data.as_posix()+'/" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}]}}
    sm=PBI/'Electricity.SemanticModel';rp=PBI/'Electricity.Report';de=rp/'definition'
    save(sm/'model.bim',model);save(sm/'definition.pbism',{'$schema':SCHEMA+'semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0'})
    save(PBI/'Electricity.pbip',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'Electricity.Report'}}],'settings':{'enableAutoRecovery':True}})
    save(rp/'definition.pbir',{'$schema':SCHEMA+'report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../Electricity.SemanticModel'}}})
    save(de/'version.json',{'$schema':SCHEMA+'report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'});save(de/'report.json',{'$schema':SCHEMA+'report/definition/report/3.1.0/schema.json','themeCollection':{}})
    pages=[('overview','Wholesale market · EUR/MWh'),('patterns','Local clock-hour patterns'),('tariffs','Illustrative household tariffs'),('flexibility','Flexible demand scenario')]
    save(de/'pages/pages.json',{'$schema':SCHEMA+'report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':[p[0] for p in pages],'activePageName':'overview'})
    def field(t,c,measure=False):return {'field':{'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':t}},'Property':c}},'queryRef':t+'.'+c,'nativeQueryRef':c}
    m=lambda n:field('Prices',n,True)
    def visual(page,name,kind,x,y,w,h,roles):
        save(de/f'pages/{page}/visuals/{name}/visual.json',{'$schema':SCHEMA+'report/definition/visualContainer/2.1.0/schema.json','name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':0,'tabOrder':0},'visual':{'visualType':kind,'query':{'queryState':{k:{'projections':v} for k,v in roles.items()}},'drillFilterOtherVisuals':True}})
    for page,label in pages:
        save(de/f'pages/{page}/page.json',{'$schema':SCHEMA+'report/definition/page/1.0.0/schema.json','name':page,'displayName':label,'displayOption':'FitToPage','width':1280,'height':720})
        visual(page,'dates','slicer',20,15,600,75,{'Values':[field('Calendar','Date')]});visual(page,'years','slicer',650,15,500,75,{'Values':[field('Calendar','Year')]})
    for i,n in enumerate(['Mean wholesale EUR per MWh','Negative hours','Negative share','Observed hours']):visual('overview','kpi'+str(i),'card',20+i*315,105,300,115,{'Values':[m(n)]})
    visual('overview','trend','lineChart',20,235,770,450,{'Category':[field('Calendar','Date')],'Y':[m('Mean wholesale EUR per MWh')]})
    visual('overview','months','tableEx',810,235,450,450,{'Values':[field('Calendar','Month'),m('Mean wholesale EUR per MWh'),m('Negative hours'),m('Observed hours')]})
    visual('patterns','clock','clusteredColumnChart',20,110,790,575,{'Category':[field('Hourly','Hour')],'Y':[m('Mean clock hour EUR per MWh')]})
    visual('patterns','table','tableEx',830,110,430,575,{'Values':[field('Hourly','Weekday'),field('Hourly','Hour'),m('Mean clock hour EUR per MWh')]})
    for i,n in enumerate(['Flat tariff EUR','Dynamic tariff EUR','Flat minus dynamic EUR','Scenario consumption kWh']):visual('tariffs','kpi'+str(i),'card',20+i*315,105,300,115,{'Values':[m(n)]})
    visual('tariffs','comparison','clusteredColumnChart',20,235,790,450,{'Category':[field('Calendar','Month')],'Y':[m('Flat tariff EUR'),m('Dynamic tariff EUR')]})
    visual('tariffs','inputs','tableEx',830,235,430,450,{'Values':[field('Scenario',c) for c in meta['assumptions']]})
    visual('flexibility','difference','lineChart',20,110,790,575,{'Category':[field('Calendar','Date')],'Y':[m('Flexible timing difference EUR')]})
    visual('flexibility','days','tableEx',830,110,430,575,{'Values':[field('Calendar','Date'),m('Flexible timing difference EUR')]})
    (sm/'measures.dax').write_text('\n\n'.join(n+' =\n'+e for n,(e,f) in measures.items()),encoding='utf-8')
    print('Native Power BI project: 4 tables, 2 relationships, 11 measures, 4 report pages.')
if __name__=='__main__':build()
