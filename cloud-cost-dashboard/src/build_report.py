"""Generate the two-page business review from the reconciled data."""
from pathlib import Path
import json, sqlite3
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT=Path(__file__).resolve().parents[1]
INK=colors.HexColor('#172A3A'); BLUE=colors.HexColor('#346888'); MUTED=colors.HexColor('#647482')

def build():
    meta=json.loads((ROOT/'reports/metadata.json').read_text())
    with sqlite3.connect(ROOT/'data/cloud_costs.sqlite') as db:
        services=db.execute('SELECT ServiceName,BilledCost FROM service_spend ORDER BY BilledCost DESC LIMIT 6').fetchall()
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Heading',fontName='Helvetica-Bold',fontSize=11,textColor=INK,spaceBefore=17,spaceAfter=8))
    styles.add(ParagraphStyle(name='Copy',fontName='Helvetica',fontSize=10,leading=15,textColor=INK,spaceAfter=9))
    styles.add(ParagraphStyle(name='Smallnote',fontName='Helvetica',fontSize=8,leading=11,textColor=MUTED,spaceAfter=8))
    story=[]
    def p(text,style='Copy'):story.append(Paragraph(text,styles[style]))
    def heading(text):p(text,'Heading')
    def table(rows,widths,header=True):
        wrapped=[[Paragraph(str(x),styles['Smallnote' if i else 'Copy']) for x in r] for i,r in enumerate(rows)]
        t=Table(wrapped,colWidths=widths,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EAF0F4')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),0.4,colors.HexColor('#DCE4EA'))]))
        story.append(t)
    p('CLOUD COST REVIEW','Smallnote')
    p('Where should a cost review start?', 'Title')
    p('Yousuf Patel | Analytics / BI portfolio project','Smallnote')
    p('Microsoft sample billing data | 1-19 June 2024 | USD','Smallnote')
    p('Start with Fabric ownership and department allocation. Fabric is the largest service in this extract, while most cost cannot be assigned to a department using the available tags. These are review priorities; this sample does not establish waste or achievable savings.')
    table([['Net billed cost','Period scenario budget','Variance'],[f"${meta['net_billed_cost']:,.2f}",f"${meta['period_scenario_budget']:,.2f}",f"${meta['net_billed_cost']-meta['period_scenario_budget']:,.2f} (55.0%)"]],[165,165,165])
    p('Budget values are authored assumptions. The period allowance is $36,100 x 19 / 30. The variance measures this scenario, not performance against an approved company plan.','Smallnote')
    heading('The main cost drivers')
    table([['Service','Net billed cost','Share of total']]+[[n,f'${v:,.2f}',f'{v/meta["net_billed_cost"]:.1%}'] for n,v in services],[285,115,95])
    p('Fabric contributes $20,730.48, or 58.5% of net billed cost. Its corresponding FTK Fabric account totals $20,551.87; account and service totals differ because they describe different slices of the data.')
    heading('Allocation is the larger control gap')
    p('Department is missing for $39,590.27 of $46,947.75 in absolute billed cost (84.3%). Absolute values provide a stable allocation denominator when credits offset charges. This percentage describes tag coverage, not an amount that can be saved.')
    p('The final date has less recorded spend than the preceding days. Because the extract ends on 19 June, treat that drop as an observation requiring source confirmation; do not assume a usage reduction.','Smallnote')
    story.append(PageBreak())
    p('DECISIONS & METHOD','Smallnote')
    p('A practical follow-up plan','Title')
    table([['Priority','Proposed owner','Next step'],['1. Fabric cost','Platform owner','Confirm capacity ownership and compare billing with capacity utilisation and workload schedules before resizing.'],['2. Allocation','Cloud governance','Agree a department tag standard, map shared services separately, then measure coverage in the next billing extract.'],['3. Budget review','Finance + account owners','Replace illustrative monthly amounts with approved account budgets. Confirm whether straight-line daily phasing is suitable.']],[115,120,260])
    heading('How the figures were calculated')
    p('The workflow retains all 135,272 source records, including 40,143 rows with negative billed cost. Positive billed charges of $41,196.80 and adjustments of -$5,750.94 reconcile to the net total. Effective cost is reported separately ($36,040.60); it is not treated as billed cost.')
    p('Billing rows are aggregated to 4,492 daily account/service/category/region/department/environment combinations. SQL aggregates account costs before joining the one-row-per-account budget, avoiding repeated budget amounts. Account IDs distinguish the two accounts named Pay-As-You-Go.')
    p('A spend review rule compares each account/service day with its preceding seven calendar days. It requires a baseline of at least $25, spend above 1.8 times that baseline, and an increase above $100. It found zero candidates. Missing recorded days are filled with zero for this rule; this is not proof of zero usage.')
    heading('What was checked')
    p('Source, SQL and daily-export totals agree within $0.000001, and daily record counts match the source. Nine automated financial/model checks pass. Dashboard controls, date guards, budget edits, CSV exports and mobile layout pass browser checks. Excel formulas were recalculated after budget and date changes; the workbook has two native charts.')
    p('The Power BI project contains a star model and three report pages. Its 28 project/report JSON files pass Microsoft schema validation. Power BI Desktop opening, native rendering, refresh and DAX execution remain unverified in this environment.','Smallnote')
    heading('Source and scope')
    p('Source: Microsoft FinOps toolkit v14, EA-Cost-FOCUS_1.0.csv. This is provider-published sample data, not employment or client data. The source covers 19 days of June 2024; no full-month projection is presented. Browser budget edits are saved locally and do not update Excel or Power BI automatically.','Smallnote')
    p('<link href="https://github.com/microsoft/finops-toolkit/releases/tag/v14" color="#346888">Microsoft source release and downloadable dataset</link>','Smallnote')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#DCE4EA'));canvas.line(50,42,A4[0]-50,42)
        canvas.setFont('Helvetica',8);canvas.setFillColor(MUTED);canvas.drawString(50,29,'Cloud cost review | Sample data | USD');canvas.drawRightString(A4[0]-50,29,str(doc.page))
    doc=SimpleDocTemplate(str(ROOT/'reports/Cloud_Cost_Business_Review.pdf'),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=43,bottomMargin=58,title='Cloud cost review',author='Yousuf Patel')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print('Business review exported')

if __name__=='__main__':build()
