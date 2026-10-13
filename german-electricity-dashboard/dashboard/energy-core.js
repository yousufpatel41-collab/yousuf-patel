(function(root){
  'use strict';
  function schedule(prices, available, target, power, efficiency, immediate=false, household=null, connection=11){
    if(!Array.isArray(prices)||prices.length!==available.length||prices.some(p=>!Number.isFinite(p))||!Number.isFinite(target)||target<0||!Number.isFinite(power)||power<=0||!Number.isFinite(efficiency)||efficiency<=0||efficiency>1)throw Error('Check prices, energy target, charging power and efficiency.');
    if(household&&(household.length!==prices.length||household.some(x=>!Number.isFinite(x)||x<0)||!Number.isFinite(connection)||connection<=0))throw Error('Invalid household load or connection limit.');
    const order=prices.map((_,i)=>i);if(!immediate)order.sort((a,b)=>prices[a]-prices[b]||a-b);
    const load=prices.map(()=>0);let remaining=target/efficiency;
    for(const i of order){const capacity=available[i]?Math.min(power,household?Math.max(0,connection-household[i]):power):0;load[i]=Math.min(capacity,remaining);remaining-=load[i];if(remaining<=1e-10)break;}
    return {load,delivered:load.reduce((a,b)=>a+b,0)*efficiency,shortfall:Math.max(0,remaining*efficiency)};
  }
  const cost=(prices,load)=>prices.reduce((s,p,i)=>s+p*load[i],0);
  const capture=(base,model,oracle)=>base-oracle<=.01?null:100*(base-model)/(base-oracle);
  function parseCSV(text){
    const delimiter=text.split(/\r?\n/)[0].includes(';')?';':',';
    const lines=[];let row=[],cell='',quoted=false;
    for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(!quoted&&(c===delimiter||c==='\n')){row.push(cell.trim());cell='';if(c==='\n'){if(row.some(Boolean))lines.push(row);row=[];}}else if(c!=='\r')cell+=c;}
    if(quoted)throw Error('Unclosed CSV quotation.');if(cell||row.length){row.push(cell.trim());lines.push(row);}
    if(lines.length<2)throw Error('CSV has no readings.');
    const header=lines.shift().map(x=>x.replace(/^\uFEFF/,'').toLowerCase());
    const t=header.findIndex(x=>['timestamputc','timestamp'].includes(x)),k=header.indexOf('kwh');
    if(t<0||k<0)throw Error('Use columns TimestampUTC and kWh. Energy must be interval kWh, not cumulative meter readings.');
    if(lines.length>50000)throw Error('Maximum 50,000 readings per upload.');
    const seen=new Set(),readings=lines.map((r,i)=>{
      if(r.length!==header.length)throw Error('Incorrect column count at row '+(i+2));
      if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/.test(r[t]))throw Error('Row '+(i+2)+': timestamp needs ISO date/time and Z or UTC offset.');
      const parts=r[t].match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/).slice(1).map(Number);
      if(parts[1]<1||parts[1]>12||parts[2]<1||parts[2]>new Date(Date.UTC(parts[0],parts[1],0)).getUTCDate()||parts[3]>23||parts[4]>59||(Number.isFinite(parts[5])&&parts[5]>59))throw Error('Row '+(i+2)+': impossible calendar date or clock time.');
      const ts=Date.parse(r[t]),energy=r[k]===''?NaN:Number(r[k]);
      if(!Number.isFinite(ts)||!Number.isFinite(energy)||energy<0)throw Error('Row '+(i+2)+': invalid timestamp or non-negative interval kWh.');
      if(seen.has(ts))throw Error('Duplicate UTC timestamp at row '+(i+2));seen.add(ts);return {ts,kwh:energy};
    }).sort((a,b)=>a.ts-b.ts);
    if(readings.length<2)throw Error('At least two readings are needed.');
    const deltas=readings.slice(1).map((r,i)=>r.ts-readings[i].ts),step=Math.min(...deltas);
    if(![1800000,3600000].includes(step)||readings.some(r=>r.ts%step!==0)||deltas.some(d=>d%step!==0))throw Error('Only aligned 30-minute or hourly interval energy is supported.');
    const missing=deltas.reduce((s,d)=>s+d/step-1,0);const map=new Map(readings.map(r=>[r.ts,r.kwh]));
    const hourly=new Map();for(const r of readings){const h=Math.floor(r.ts/3600000)*3600000;if(step===3600000)hourly.set(h,r.kwh);else if(r.ts===h&&map.has(h+step))hourly.set(h,r.kwh+map.get(h+step));}
    return {readings,hourly,step,missing,total:readings.reduce((s,r)=>s+r.kwh,0),first:readings[0].ts,last:readings.at(-1).ts};
  }
  function demandForecast(input){
    const hourly=input.hourly;const times=[...hourly.keys()].sort((a,b)=>a-b);if(times.length<24*28)throw Error('Demand forecasting needs at least 28 days of complete hourly observations.');
    const hour=3600000,end=times.at(-1),start=end-7*24*hour+hour;
    const median=a=>{const b=a.slice().sort((x,y)=>x-y);return b.length%2?b[(b.length-1)/2]:(b[b.length/2-1]+b[b.length/2])/2;};
    const weekly=t=>{const lags=[1,2,3].map(w=>hourly.get(t-w*168*hour));return lags.every(Number.isFinite)?median(lags):null;};
    let n=0,dailyError=0,weeklyError=0;for(const t of times.filter(t=>t>=start)){const truth=hourly.get(t),daily=hourly.get(t-24*hour),week=weekly(t);if(Number.isFinite(daily)&&week!==null){n++;dailyError+=Math.abs(truth-daily);weeklyError+=Math.abs(truth-week);}}
    if(!n)throw Error('Not enough matching historical intervals to validate the demand forecast.');
    const next=Array.from({length:24},(_,i)=>({ts:end+(i+1)*hour,kwh:weekly(end+(i+1)*hour)}));
    return {n,dailyMAE:dailyError/n,weeklyMAE:weeklyError/n,next};
  }
  const api={schedule,cost,capture,parseCSV,demandForecast};root.EnergyCore=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
