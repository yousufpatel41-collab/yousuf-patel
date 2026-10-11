"""Create the native Power BI project and its CSV-backed star model."""
from pathlib import Path
import json, uuid
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / 'powerbi'
SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/'

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def build():
    data = ROOT / 'data'
    daily = pd.read_csv(data / 'daily_costs.csv')
    budgets = pd.read_csv(data / 'budgets.csv')
    daily[['SubAccountId','SubAccountName']].drop_duplicates().to_csv(data/'dim_accounts.csv',index=False)
    daily[['ServiceName']].drop_duplicates().sort_values('ServiceName').to_csv(data/'dim_services.csv',index=False)
    daily[['Department']].drop_duplicates().sort_values('Department').to_csv(data/'dim_departments.csv',index=False)
    pd.DataFrame({'Date':pd.date_range(daily.ChargeDate.min(),daily.ChargeDate.max()).strftime('%Y-%m-%d')}).to_csv(data/'calendar.csv',index=False)
    datasets = {
        'Costs':('daily_costs.csv', [('ChargeDate','dateTime'),('SubAccountId','string'),('ServiceName','string'),('Department','string'),('BilledCost','double'),('EffectiveCost','double'),('AbsoluteBilledCost','double'),('UnallocatedAbsoluteCost','double'),('RecordCount','int64')]),
        'Accounts':('dim_accounts.csv',[('SubAccountId','string'),('SubAccountName','string')]),
        'Services':('dim_services.csv',[('ServiceName','string')]),
        'Departments':('dim_departments.csv',[('Department','string')]),
        'Calendar':('calendar.csv',[('Date','dateTime')]),
        'Budgets':('budgets.csv',[('SubAccountId','string'),('BillingMonth','string'),('MonthlyBudget','double')])
    }
    money='$#,0.00;($#,0.00);$0.00'
    measures = {
        'Net billed cost':('SUM(Costs[BilledCost])',money),
        'Effective cost':('SUM(Costs[EffectiveCost])',money),
        'Source records':('SUM(Costs[RecordCount])','#,0'),
        'Absolute billed cost':('SUM(Costs[AbsoluteBilledCost])',money),
        'Unallocated cost share':('DIVIDE(SUM(Costs[UnallocatedAbsoluteCost]), [Absolute billed cost])','0.0%'),
        'Period scenario budget':('IF(ISFILTERED(Services) || ISFILTERED(Departments), BLANK(), SUM(Budgets[MonthlyBudget]) * COUNTROWS(VALUES(\'Calendar\'[Date])) / DAY(EOMONTH(MAX(\'Calendar\'[Date]),0)))',money),
        'Budget variance':('IF(ISBLANK([Period scenario budget]), BLANK(), [Net billed cost] - [Period scenario budget])',money),
        'Budget variance percent':('DIVIDE([Budget variance], [Period scenario budget])','0.0%')
    }
    tables=[]
    for name,(file,columns) in datasets.items():
        types=', '.join('{"'+c+'", '+{'string':'type text','double':'type number','int64':'Int64.Type','dateTime':'type date'}[t]+'}' for c,t in columns)
        expression=['let',f'    Source = Csv.Document(File.Contents(DataFolder & "{file}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),','    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',f'    Typed = Table.TransformColumnTypes(Headers, {{{types}}}, "en-US")','in','    Typed']
        table={'name':name,'columns':[{'name':c,'dataType':t,'sourceColumn':c,'summarizeBy':'none',**({'formatString':'yyyy-MM-dd'} if t=='dateTime' else {})} for c,t in columns], 'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]}
        if name=='Costs': table['measures']=[{'name':n,'expression':e,'formatString':f} for n,(e,f) in measures.items()]
        tables.append(table)
    relationships=[]
    for ft,fc,dt,dc in [('Costs','ChargeDate','Calendar','Date'),('Costs','SubAccountId','Accounts','SubAccountId'),('Budgets','SubAccountId','Accounts','SubAccountId'),('Costs','ServiceName','Services','ServiceName'),('Costs','Department','Departments','Department')]:
        relationships.append({'name':str(uuid.uuid5(uuid.NAMESPACE_URL,ft+fc+dt+dc)),'fromTable':ft,'fromColumn':fc,'toTable':dt,'toColumn':dc,'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection'})
    model={'name':'Cloud cost review','compatibilityLevel':1567,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','expressions':[{'name':'DataFolder','kind':'m','expression':'"'+data.as_posix()+'/" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}], 'tables':tables,'relationships':relationships}}
    sm=PBI/'CloudCosts.SemanticModel'; report=PBI/'CloudCosts.Report'; definition=report/'definition'
    save(sm/'model.bim', model)
    save(sm/'definition.pbism',{'$schema':SCHEMA+'semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0'})
    save(PBI/'CloudCosts.pbip',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'CloudCosts.Report'}}],'settings':{'enableAutoRecovery':True}})
    save(report/'definition.pbir',{'$schema':SCHEMA+'report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../CloudCosts.SemanticModel'}}})
    save(definition/'version.json',{'$schema':SCHEMA+'report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    save(definition/'report.json',{'$schema':SCHEMA+'report/definition/report/3.1.0/schema.json','themeCollection':{}})
    pages=[('overview','Overview · USD · 1–19 June 2024'),('drivers','Cost drivers'),('allocation','Allocation & data coverage')]
    save(definition/'pages/pages.json',{'$schema':SCHEMA+'report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':[p[0] for p in pages],'activePageName':'overview'})
    for name,label in pages:
        save(definition/f'pages/{name}/page.json',{'$schema':SCHEMA+'report/definition/page/1.0.0/schema.json','name':name,'displayName':label,'displayOption':'FitToPage','width':1280,'height':720})
    def field(table,column,measure=False):
        return {'field':{'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':column}},'queryRef':table+'.'+column,'nativeQueryRef':column}
    def visual(page,name,kind,x,y,w,h,roles):
        save(definition/f'pages/{page}/visuals/{name}/visual.json',{'$schema':SCHEMA+'report/definition/visualContainer/2.1.0/schema.json','name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':0,'tabOrder':0},'visual':{'visualType':kind,'query':{'queryState':{role:{'projections':fields} for role,fields in roles.items()}},'drillFilterOtherVisuals':True}})
    measure=lambda n:field('Costs',n,True)
    for page,_ in pages:
        visual(page,'accountfilter','slicer',20,15,440,75,{'Values':[field('Accounts','SubAccountName')]})
        visual(page,'datefilter','slicer',480,15,440,75,{'Values':[field('Calendar','Date')]})
    for i,n in enumerate(['Net billed cost','Period scenario budget','Budget variance','Unallocated cost share']):
        visual('overview','kpi'+str(i),'card',20+i*315,105,300,115,{'Values':[measure(n)]})
    visual('overview','daily','lineChart',20,235,730,240,{'Category':[field('Calendar','Date')],'Y':[measure('Net billed cost'),measure('Period scenario budget')]})
    visual('overview','services','barChart',770,235,490,240,{'Category':[field('Services','ServiceName')],'Y':[measure('Net billed cost')]})
    visual('overview','accounts','tableEx',20,495,1240,205,{'Values':[field('Accounts','SubAccountName')]+[measure(n) for n in ['Net billed cost','Period scenario budget','Budget variance','Budget variance percent']]})
    visual('drivers','services','barChart',20,110,760,580,{'Category':[field('Services','ServiceName')],'Y':[measure('Net billed cost')]})
    visual('drivers','breakdown','tableEx',800,110,460,580,{'Values':[field('Services','ServiceName'),measure('Net billed cost'),measure('Effective cost'),measure('Source records')]})
    visual('allocation','share','card',20,110,380,120,{'Values':[measure('Unallocated cost share')]})
    visual('allocation','records','card',420,110,380,120,{'Values':[measure('Source records')]})
    visual('allocation','departments','barChart',20,250,740,440,{'Category':[field('Departments','Department')],'Y':[measure('Absolute billed cost')]})
    visual('allocation','definition','tableEx',780,250,480,440,{'Values':[field('Departments','Department'),measure('Net billed cost'),measure('Absolute billed cost'),measure('Source records')]})
    (sm/'measures.dax').write_text('\n\n'.join(n+' =\n'+e for n,(e,f) in measures.items())+'\n')
    print('Created Power BI project: 6 tables, 5 relationships, 8 measures, 3 pages.')

if __name__=='__main__':build()
