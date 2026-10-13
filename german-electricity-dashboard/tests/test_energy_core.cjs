const test=require('node:test'),assert=require('node:assert/strict');
const C=require('../dashboard/energy-core.js');
test('reject ambiguous local time and duplicate UTC rows',()=>{
  assert.throws(()=>C.parseCSV('TimestampUTC,kWh\n2025-01-01T00:00:00,1\n2025-01-01T01:00:00,1'));
  assert.throws(()=>C.parseCSV('TimestampUTC,kWh\n2025-01-01T00:00:00Z,1\n2025-01-01T00:00:00Z,1'));
  assert.throws(()=>C.parseCSV('TimestampUTC,kWh\n2025-02-30T00:00:00Z,1\n2025-03-01T01:00:00Z,1'));
});
test('half-hour intervals aggregate only complete pairs',()=>{
  const file=C.parseCSV('TimestampUTC,kWh\n2025-01-01T00:00:00Z,.2\n2025-01-01T00:30:00Z,.3\n2025-01-01T01:30:00Z,.4');
  assert.equal(file.hourly.size,1);assert.equal([...file.hourly.values()][0],.5);assert.equal(file.missing,1);
});
test('quoted and semicolon CSV supported, negative energy rejected',()=>{
  assert.equal(C.parseCSV('"TimestampUTC";"kWh"\n"2025-01-01T00:00:00Z";".2"\n"2025-01-01T01:00:00Z";".3"').total,.5);
  assert.throws(()=>C.parseCSV('TimestampUTC,kWh\n2025-01-01T00:00:00Z,-1\n2025-01-01T01:00:00Z,1'));
});
test('DST repeated local hours have distinct UTC keys',()=>{
  const file=C.parseCSV('TimestampUTC,kWh\n2025-10-26T02:00:00+02:00,1\n2025-10-26T02:00:00+01:00,2');assert.equal(file.hourly.size,2);
});
test('daily persistence can beat weekly seasonal predictor',()=>{
  let csv='TimestampUTC,kWh\n';for(let i=0;i<35*24;i++)csv+=new Date(Date.UTC(2025,0,1)+i*3600000).toISOString()+','+(i*.001)+'\n';
  const result=C.demandForecast(C.parseCSV(csv));assert.ok(result.dailyMAE<result.weeklyMAE);assert.equal(result.next.length,24);
});
test('capacity and efficiency conserve energy under negative prices',()=>{
  const result=C.schedule([-.2,-.1,.8],[true,true,false],4,7,.8);assert.equal(result.delivered,4);assert.equal(result.load.reduce((a,b)=>a+b,0),5);
});
test('oracle ratio undefined for negligible opportunity and losses retained',()=>{assert.equal(C.capture(1,1,.995),null);assert.equal(C.capture(2,3,1),-100);});
