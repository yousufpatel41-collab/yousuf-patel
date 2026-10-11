import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=fileURLToPath(new URL('../',import.meta.url));
const payload=JSON.parse(await fs.readFile(path.join(root,'dashboard/data.json'),'utf8'));
const wb=Workbook.create();
const review=wb.worksheets.add('Review'), budgets=wb.worksheets.add('Budgets'), daily=wb.worksheets.add('Daily costs');
const ink='#172A3A',blue='#346888',muted='#647482',line='#DCE4EA';
function base(s,range){s.showGridLines=false;s.getRange(range).format.font={name:'Arial',size:10,color:ink};s.getRange(range).format.rowHeight=21;s.getRange(range).format.verticalAlignment='center';}
function header(s,range){s.getRange(range).format={fill:ink,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:27,horizontalAlignment:'center'};}
const money='"$"#,##0.00;("$"#,##0.00);"-"',percent='0.0%;(0.0%);"-"';
const date=s=>new Date(s+'T00:00:00Z');
base(review,'A1:L75');review.tabColor=ink;
review.getRange('A:L').format.columnWidth=13;
review.getRange('A:A').format.columnWidth=35;review.getRange('B:D').format.columnWidth=17;review.getRange('E:E').format.columnWidth=15;review.getRange('F:F').format.columnWidth=3;
review.getRange('A2').values=[['Cloud cost review']];review.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:ink};
review.getRange('A3').values=[['Microsoft sample billing data. Budget values are illustrative. USD.']];review.getRange('A3').format.font={name:'Arial',size:10,italic:true,color:muted};
review.getRange('A5:B6').values=[['Start date',date(payload.meta.period_start)],['End date',date(payload.meta.period_end)]];review.getRange('B5:B6').setNumberFormat('d-mmm-yy');review.getRange('B5:B6').format.fill='#FFF2D6';review.getRange('B5:B6').format.font.color='#0000FF';
review.getRange('D5:E7').values=[['Currency','USD'],['Selected days',null],['Days in source month',30]];
review.getRange('E6').formulas=[['=B6-B5+1']];
review.getRange('A9:A12').values=[['Net billed cost'],['Effective cost'],['Unallocated cost share'],['Source billing rows']];
review.getRange('D9:D11').values=[['Period budget'],['Over / under budget'],['Variance %']];
const n=payload.rows.length,last=5+n,range=col=>`'Daily costs'!$${col}$6:$${col}$${last}`;
const dateCriteria=`${range('A')},">="&$B$5,${range('A')},"<="&$B$6`;
review.getRange('B9:B12').formulas=[[
 `=SUMIFS(${range('F')},${dateCriteria})`],[`=SUMIFS(${range('G')},${dateCriteria})`],
 [`=IF(SUMIFS(${range('H')},${dateCriteria})=0,"n.a.",SUMIFS(${range('I')},${dateCriteria})/SUMIFS(${range('H')},${dateCriteria}))`],
 [`=SUMIFS(${range('J')},${dateCriteria})`]];
review.getRange('E9:E11').formulas=[[`=SUM('Budgets'!C6:C${5+payload.budgets.length})*$E$6/$E$7`],['=B9-E9'],['=IF(E9=0,"n.a.",E10/E9)']];
review.getRange('B9:B10').setNumberFormat(money);review.getRange('E9:E10').setNumberFormat(money);review.getRange('B11').setNumberFormat(percent);review.getRange('E11').setNumberFormat(percent);review.getRange('B12').setNumberFormat('#,##0');review.getRange('A11:B11').format.font.italic=true;review.getRange('D11:E11').format.font.italic=true;
review.getRange('B9:B12').format.font.bold=true;review.getRange('E9:E11').format.font.bold=true;
review.getRange('E10').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{font:{color:'#A53B37'},fill:'#FCEBE7'}});
review.getRange('A15:E15').values=[['Account','Net billed cost','Period budget','Variance','Variance %']];header(review,'A15:E15');
const accountRows=payload.budgets.map((b,i)=>{let r=16+i,br=6+i;return[
 `='Budgets'!B${br}`,`=SUMIFS(${range('F')},${range('B')},'Budgets'!A${br},${dateCriteria})`,
 `='Budgets'!C${br}*$E$6/$E$7`,`=B${r}-C${r}`,`=IF(C${r}=0,"n.a.",D${r}/C${r})`];});
review.getRange(`A16:E${15+accountRows.length}`).formulas=accountRows;
review.getRange(`B16:D${15+accountRows.length}`).setNumberFormat(money);review.getRange(`E16:E${15+accountRows.length}`).setNumberFormat(percent);
review.getRange(`D16:D${15+accountRows.length}`).conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{font:{color:'#A53B37'},fill:'#FCEBE7'}});
review.getRange('A30:E30').values=[['Total',null,null,null,null]];review.getRange('B30:E30').formulas=[['=SUM(B16:B28)','=SUM(C16:C28)','=B30-C30','=IF(C30=0,"n.a.",D30/C30)']];review.getRange('B30:D30').setNumberFormat(money);review.getRange('E30').setNumberFormat(percent);review.getRange('A30:E30').format.font.bold=true;review.getRange('A30:E30').format.borders={top:{style:'thin',color:ink}};
// Chart source is formula-linked and kept visible beneath the service table.
const services=[...new Set(payload.rows.map(r=>r.ServiceName))].sort((a,b)=>payload.rows.filter(r=>r.ServiceName===b).reduce((v,r)=>v+r.BilledCost,0)-payload.rows.filter(r=>r.ServiceName===a).reduce((v,r)=>v+r.BilledCost,0));
review.getRange('A34:B34').values=[['Service','Net billed cost']];header(review,'A34:B34');
review.getRange(`A35:A${34+services.length}`).values=services.map(s=>[s]);
review.getRange(`B35:B${34+services.length}`).formulas=services.map((_,i)=>[`=SUMIFS(${range('F')},${range('D')},A${35+i},${dateCriteria})`]);review.getRange(`B35:B${34+services.length}`).setNumberFormat(money);
review.getRange('G57:H57').values=[['Charge date','Net billed cost']];header(review,'G57:H57');
review.getRange('G58:H76').values=Array.from({length:19},(_,i)=>[`${i+1} Jun`,null]);
review.getRange('H58:H76').formulas=Array.from({length:19},(_,i)=>[`=SUMIFS(${range('F')},${range('A')},DATE(2024,6,${i+1}),${dateCriteria})`]);review.getRange('H58:H76').setNumberFormat(money);
function chart(type,source,title,start,end){const c=review.charts.add(type,review.getRange(source));c.title=title;c.titleTextStyle.typeface='Arial';c.titleTextStyle.fontSize=12;c.hasLegend=false;c.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:10}};c.yAxis={numberFormatCode:'$#,##0',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:10}};c.series.items[0].fill=blue;if(type==='line')c.series.items[0].line={fill:blue,style:'solid',width:2};c.setPosition(start,end);return c;}
chart('line','G57:H76','Daily net billed cost (USD)','G15','L31');
chart('bar','A34:B44','Ten leading services (full-extract ranking)','G34','L54');
base(budgets,'A1:E22');budgets.tabColor=blue;budgets.getRange('A:A').format.columnWidth=55;budgets.getRange('B:B').format.columnWidth=36;budgets.getRange('C:C').format.columnWidth=22;budgets.getRange('D:D').format.columnWidth=4;budgets.getRange('E:E').format.columnWidth=70;
budgets.getRange('A2').values=[['Illustrative account budgets']];budgets.getRange('A2').format.font={name:'Arial',size:14,bold:true};budgets.getRange('A3').values=[['Monthly USD assumptions for June 2024. Blue cells can be edited.']];budgets.getRange('A5:C5').values=[['Account ID','Account','Monthly budget (USD)']];header(budgets,'A5:C5');
budgets.getRange(`A6:C${5+payload.budgets.length}`).values=payload.budgets.map(b=>[b.SubAccountId,b.SubAccountName,b.MonthlyBudget]);budgets.getRange(`C6:C${5+payload.budgets.length}`).setNumberFormat(money);budgets.getRange(`C6:C${5+payload.budgets.length}`).format.font.color='#0000FF';budgets.getRange(`C6:C${5+payload.budgets.length}`).format.fill='#FFF2D6';budgets.getRange(`C6:C${5+payload.budgets.length}`).dataValidation={rule:{type:'decimal',operator:'greaterThanOrEqual',formula1:0}};
budgets.getRange('E6').values=[['Budget source: authored planning assumptions, not provider data.']];budgets.getRange('E8').values=[['Period allowance = monthly budget × selected days ÷ 30.']];budgets.getRange('E10').values=[['Zero budget means variance percentage is unavailable.']];budgets.freezePanes.freezeRows(5);
base(daily,`A1:J${last}`);daily.getRange('A:A').format.columnWidth=14;daily.getRange('B:B').format.columnWidth=56;daily.getRange('C:C').format.columnWidth=35;daily.getRange('D:D').format.columnWidth=30;daily.getRange('E:E').format.columnWidth=25;daily.getRange('F:J').format.columnWidth=22;
daily.getRange('A2').values=[['Prepared daily costs']];daily.getRange('A2').format.font={name:'Arial',size:14,bold:true};daily.getRange('A3').values=[['Source: Microsoft FinOps toolkit v14, EA-Cost-FOCUS_1.0.csv. Original billing records remain in data/billing_records.csv.']];
daily.getRange('A4').values=[['https://github.com/microsoft/finops-toolkit/releases/tag/v14']];
daily.getRange('A5:J5').values=[['Charge date','Account ID','Account','Service','Department','Net billed cost','Effective cost','Absolute billed cost','Unallocated abs. cost','Source rows']];header(daily,'A5:J5');
daily.getRange(`A6:J${last}`).values=payload.rows.map(r=>[date(r.ChargeDate),r.SubAccountId,r.SubAccountName,r.ServiceName,r.Department,r.BilledCost,r.EffectiveCost,r.AbsoluteBilledCost,r.UnallocatedAbsoluteCost,r.RecordCount]);daily.getRange(`A6:A${last}`).setNumberFormat('d-mmm-yy');daily.getRange(`F6:I${last}`).setNumberFormat(money);daily.getRange(`J6:J${last}`).setNumberFormat('#,##0');daily.freezePanes.freezeRows(5);
daily.tables.add(`A5:J${last}`,true,'DailyCostTable');
wb.recalculate();
const initial=review.getRange('B9').values[0][0];if(Math.abs(initial-payload.meta.net_billed_cost)>1e-6)throw Error('Workbook total mismatch: '+initial);
const oldBudget=budgets.getRange('C6').values[0][0],oldAllowance=review.getRange('E9').values[0][0];budgets.getRange('C6').values=[[oldBudget+1000]];wb.recalculate();if(Math.abs(review.getRange('E9').values[0][0]-oldAllowance-1000*19/30)>1e-6)throw Error('Budget edit did not recalculate');budgets.getRange('C6').values=[[oldBudget]];
review.getRange('B5').values=[[date('2024-06-10')]];wb.recalculate();const expected=payload.rows.filter(r=>r.ChargeDate>='2024-06-10').reduce((v,r)=>v+r.BilledCost,0);if(Math.abs(review.getRange('B9').values[0][0]-expected)>1e-6)throw Error('Date filter failed');review.getRange('B5').values=[[date(payload.meta.period_start)]];wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:2500});console.log(errors.ndjson);
await fs.mkdir(path.join(root,'reports'),{recursive:true});
for(const [name,range]of [['Review','A1:L55'],['Budgets','A1:C20'],['Daily costs','A1:F15']]){const blob=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(path.join(root,'reports',`excel-${name.replaceAll(' ','-')}.png`),new Uint8Array(await blob.arrayBuffer()));}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(root,'Cloud_Cost_Review.xlsx'));
await fs.writeFile(path.join(root,'reports/workbook_checks.json'),JSON.stringify({source_total:initial,budget_edit_recalculation:true,date_filter_recalculation:true,chart_count:review.charts.items.length},null,2));
console.log('Workbook exported');
