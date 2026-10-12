"""Render a two-page review from the frozen SMARD snapshot and scenario inputs."""
from pathlib import Path
import json
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak
ROOT=Path(__file__).resolve().parents[1]
def build():
    meta=json.loads((ROOT/'reports/metadata.json').read_text());daily=pd.read_csv(ROOT/'data/daily_prices.csv');a=meta['assumptions']
    recent=daily[daily.Year==2026];matching=set(recent.Date.str.replace('2026-','2025-',regex=False));prior=daily[daily.Date.isin(matching)]
    mean=lambda d:d.SumEURMWh.sum()/d.Hours.sum()
    previous=mean(prior);current=mean(recent)
    def model(d):
        w=d.ConsumptionWeight.sum();kwh=w*a['monthly_kwh'];flat=kwh*a['flat_eur_kwh']+w*a['monthly_fixed_fee'];dynamic=d.WholesaleCostPerMonthlyKWh.sum()*a['monthly_kwh']*a['vat_multiplier']+kwh*a['dynamic_adder_eur_kwh']+w*a['monthly_fixed_fee'];return kwh,flat,dynamic
    year2025=daily[daily.Year==2025];kwh,flat,dynamic=model(year2025);flex=(year2025.EveningMeanEURMWh-year2025.Cheapest4MeanEURMWh).mean()/1000*a['flexible_kwh_per_day']*a['vat_multiplier']
    styles=getSampleStyleSheet();styles['Title'].textColor=colors.HexColor('#172E24');styles['Title'].fontSize=20;styles['Title'].leading=25
    styles.add(ParagraphStyle(name='Copy',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=9,textColor=colors.HexColor('#172E24')))
    styles.add(ParagraphStyle(name='Label',fontName='Helvetica',fontSize=8,leading=11,spaceAfter=8,textColor=colors.HexColor('#65796E')))
    styles.add(ParagraphStyle(name='Section',fontName='Helvetica-Bold',fontSize=11,leading=14,spaceBefore=15,spaceAfter=8,textColor=colors.HexColor('#172E24')))
    story=[]
    def p(t,s='Copy'):story.append(Paragraph(t,styles[s]))
    def table(rows,widths):
        t=Table([[Paragraph(str(v),styles['Label' if i else 'Copy']) for v in row] for i,row in enumerate(rows)],colWidths=widths)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8EFEA')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#DAE4DD'))]));story.append(t)
    p('GERMAN ELECTRICITY COST REVIEW','Label');p('Price exposure depends on when electricity is used','Title');p('Yousuf Patel | Analytics / BI portfolio project','Label');p('Bundesnetzagentur | SMARD.de | Snapshot retrieved 12 October 2026','Label')
    p('Wholesale electricity is volatile, and an annual average does not describe the price paid by a household at a particular time. This project combines market history with transparent household tariff and flexible-demand scenarios. It does not use actual household bills or supplier offers.')
    table([['Period','Hourly mean EUR/MWh','Negative hourly prices','Observed hours']]+[[str(r['Year'])+(' to 11 Oct' if r['Year']==2026 else ''),f"{r['MeanEURMWh']:.2f}",f"{r['NegativeHours']:,}",f"{r['Hours']:,}"] for r in meta['annual']],[120,140,140,95])
    p('2024 and 2025 are complete years. The 2026 period has one missing day, 10 October. Its prices are excluded rather than replaced by zero. Negative-hour counts refer to published hourly averages, not quarter-hour market intervals.','Label')
    p('Use matching dates for the year comparison','Section')
    p(f'The 2026 observed-hour mean is EUR {current:.2f}/MWh. Using the corresponding available calendar dates in 2025 gives EUR {previous:.2f}/MWh, a {(current/previous-1)*100:.1f}% increase. This comparison also excludes 10 October 2025 to match the 2026 source gap. It describes observed price levels, not a forecast or a causal explanation.')
    p('Household comparison: make the assumptions visible','Section')
    table([['2025 scenario','Amount'],['Consumption',f'{kwh:,.0f} kWh'],['Flat tariff cost',f'EUR {flat:,.2f}'],['Dynamic tariff cost',f'EUR {dynamic:,.2f}'],['Flat minus dynamic',f'EUR {flat-dynamic:,.2f}']],[340,155])
    p('Assumptions: 250 kWh/month, EUR 0.32/kWh gross flat rate, EUR 0.20/kWh gross dynamic non-energy adder, a 1.19 wholesale gross multiplier, and EUR 10/month fixed fee for either tariff. Monthly energy is spread uniformly across elapsed hours. These are illustrative inputs, not current quotes.','Label')
    p('The dynamic scenario can be more expensive when the non-energy adder or the household load profile changes. A negative wholesale hour does not necessarily make the final household unit price negative.','Copy')
    story.append(PageBreak())
    p('TIMING, DECISIONS AND CHECKS','Label');p('Separate flexibility from tariff selection','Title')
    p(f'For 2025, moving the same 12 kWh/day from 18:00-22:00 to the four cheapest observed hours of that local day gives a modelled mean difference of EUR {flex:.2f}/day after the assumed gross multiplier. The cheapest hours may be separate. This requires all-day equipment availability and does not establish achievable household savings.')
    table([['Decision','Evidence needed before acting'],['Choose a tariff','Obtain an actual supplier offer, fees, price formula and household interval meter readings. Compare equivalent consumption and contract terms.'],['Schedule flexible load','Confirm equipment availability, power limits and acceptable timing. Use day-ahead published prices, then compare actual meter readings.'],['Investigate price changes','Join verified generation, demand and weather data before attributing price changes to a particular cause.']],[140,355])
    p('How the calculation works','Section')
    p('The unique key is the UTC timestamp. Europe/Berlin supplies the local date and clock hour. Daylight saving time produces 23- and 25-hour days; repeated autumn clock hours remain distinct. Monthly and annual market means weight each observed elapsed hour equally. Means of daily means would give unequal weight to DST days.')
    p('Household cost uses a monthly-consumption coefficient based on the actual elapsed hours in each month. Dynamic unit cost = wholesale EUR/MWh / 1,000 x gross multiplier + gross non-energy adder. Missing hours contribute neither modelled energy nor fees. The same energy and fixed fee are used in both tariff scenarios. Negative source prices are preserved.')
    p('Validation and limitations','Section')
    p('Twelve automated checks cover official annual benchmarks, leap-year coverage, UTC uniqueness, source gaps, DST, units, aggregation, monthly energy weights, equal-energy scheduling, raw checksums, SQL, Power BI date keys and Excel formulas/charts. Browser checks exercise filters, heatmaps, tariff edits and persistence, CSV exports, missing dates and mobile layout.')
    p('The Power BI project has four tables, two relationships, eleven DAX measures and four report pages. Its 34 project/report JSON files pass Microsoft schema validation. Desktop opening, refresh, rendering and DAX execution remain unverified in this environment.','Label')
    p('Source and reproducibility','Section')
    p('Published hourly DE/LU price series 4169 from Bundesnetzagentur | SMARD.de. Requested window: 1 January 2024 to 11 October 2026. The project preserves the weekly raw responses and their SHA-256 checksums. Prices can be revised by the source; the included files form a dated snapshot. Market data is licensed CC BY 4.0.','Label')
    p('<link href="https://www.smard.de/en/datennutzung" color="#42775F">SMARD data-use and attribution terms</link> | <link href="https://www.smard.de/page/en/topic-article/217400/219038" color="#42775F">Official 2025 market review</link>','Label')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#DAE4DD'));canvas.line(50,42,A4[0]-50,42);canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#65796E'));canvas.drawString(50,29,'Bundesnetzagentur | SMARD.de - observed prices and illustrative scenarios');canvas.drawRightString(A4[0]-50,29,str(doc.page))
    doc=SimpleDocTemplate(str(ROOT/'reports/German_Electricity_Business_Review.pdf'),pagesize=A4,leftMargin=50,rightMargin=50,topMargin=42,bottomMargin=58,title='German electricity cost review',author='Yousuf Patel');doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(json.dumps({'matched_2025_mean':previous,'2026_mean':current,'2025_flat':flat,'2025_dynamic':dynamic,'2025_flex_daily':flex},indent=2))
if __name__=='__main__':build()
