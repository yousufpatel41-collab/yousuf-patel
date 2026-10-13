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
  function csvRows(text){
    const delimiter=text.split(/\r?\n/)[0].includes(';')?';':',';
    const lines=[];let row=[],cell='',quoted=false;
    for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(!quoted&&(c===delimiter||c==='\n')){row.push(cell.trim());cell='';if(c==='\n'){if(row.some(Boolean))lines.push(row);row=[];}}else if(c!=='\r')cell+=c;}
    if(quoted)throw Error('Unclosed CSV quotation.');if(cell||row.length){row.push(cell.trim());lines.push(row);}
    return {lines,delimiter};
  }
  const normalizeHeader=s=>s.replace(/^\uFEFF/,'').normalize('NFKD').replace(/\p{Diacritic}/gu,'').toLowerCase().replace(/[^a-z0-9]/g,'');
  function inspectCSV(text){const {lines}=csvRows(text);if(lines.length<2)throw Error('CSV has no readings.');return lines[0].map(s=>s.replace(/^\uFEFF/,''));}
  const berlinParts=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  function parseTimestamp(value,zone,sequence,previous,row){
    value=value.trim().replace(' ','T');
    const german=value.match(/^(\d{2})\.(\d{2})\.(\d{4})T(.+)$/);if(german)value=german[3]+'-'+german[2]+'-'+german[1]+'T'+german[4];
    const match=value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,3})?)?(Z|[+-]\d{2}:?\d{2})?$/);
    if(!match)throw Error('Row '+row+': use ISO timestamp or DD.MM.YYYY HH:mm with a selected timezone.');
    const [year,month,day,hour,minute,second]=match.slice(1,7).map(x=>Number(x||0));
    if(month<1||month>12||day<1||day>new Date(Date.UTC(year,month,0)).getUTCDate()||hour>23||minute>59||second>59)throw Error('Row '+row+': impossible calendar date or clock time.');
    const wall=Date.UTC(year,month-1,day,hour,minute,second);
    if(match[7]){const ts=Date.parse(value);if(!Number.isFinite(ts))throw Error('Invalid UTC offset at row '+row);return ts;}
    if(zone==='UTC')return wall;
    if(zone!=='Europe/Berlin')throw Error('Row '+row+': timestamp has no offset. Select Europe/Berlin or UTC explicitly.');
    const candidates=[60,120].map(offset=>wall-offset*60000).filter(ts=>{
      const parts=Object.fromEntries(berlinParts.formatToParts(ts).filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));return parts.year===year&&parts.month===month&&parts.day===day&&parts.hour===hour&&parts.minute===minute&&parts.second===second;
    }).sort((a,b)=>a-b);
    if(!candidates.length)throw Error('Row '+row+': nonexistent Berlin clock time during spring DST.');
    if(candidates.length>1){if(!sequence)throw Error('Row '+row+': ambiguous autumn Berlin time. Supply offsets, or explicitly choose chronological DST sequence.');const candidate=candidates.find(ts=>previous===null||ts>previous);if(candidate===undefined)throw Error('DST sequence is not chronological at row '+row);return candidate;}
    if(sequence&&previous!==null&&candidates[0]<=previous)throw Error('Chronological DST mode needs increasing input rows.');
    return candidates[0];
  }
  function parseCSV(text,options={}){
    const {lines,delimiter}=csvRows(text);if(lines.length<2)throw Error('CSV has no readings.');
    const headers=lines.shift().map(s=>s.replace(/^\uFEFF/,'')),header=headers.map(normalizeHeader);
    const chosen=(name,aliases)=>name?headers.indexOf(name):header.findIndex(x=>aliases.includes(x));
    const timestamp=chosen(options.timestampColumn,['timestamputc','timestamp','datetime','zeitstempel','startzeit','start','datumzeit','zeitpunkt','intervalstart']);
    const date=chosen(options.dateColumn,['datum','date']),time=chosen(options.timeColumn,['uhrzeit','time','von','zeit']);
    const energy=chosen(options.energyColumn,['kwh','wh','energiekwh','verbrauchkwh','bezugkwh','energykwh','wertkwh','energiewh','verbrauchwh','wertwh']);
    if(energy<0||(timestamp<0&&(date<0||time<0)))throw Error('Map a timestamp (or date + time) column and an interval energy column.');
    if(/zaehlerstand|zahlerstand|meterreading|cumulative|leistung|power/.test(header[energy]))throw Error('Cumulative meter readings and power columns are not interval energy.');
    if(!/kwh|wh/.test(header[energy])&&!options.confirmIntervalEnergy)throw Error('Confirm that the mapped values are interval energy, not cumulative readings or kW power.');
    if(lines.length>50000)throw Error('Maximum 50,000 readings per upload.');
    if(!/kwh|wh/.test(header[energy])&&!options.unit)throw Error('Choose kWh or Wh for an unlabeled interval-energy column.');
    const unit=options.unit||(/wh$/.test(header[energy])&&!/kwh$/.test(header[energy])?'Wh':'kWh');
    if(!['kWh','Wh'].includes(unit))throw Error('Supported units: interval kWh or Wh.');
    let previous=null;const seen=new Set();
    let readings=lines.map((r,i)=>{
      if(r.length!==header.length)throw Error('Incorrect column count at row '+(i+2));
      const stamp=timestamp>=0?r[timestamp]:r[date]+' '+r[time];const ts=parseTimestamp(stamp,options.timeZone||'offset',options.dstSequence===true,previous,i+2);previous=ts;
      let value=r[energy].replace(/[\s\u00a0\u202f]/g,'');if(value.includes(',')&&(delimiter===';'||/^[-+]?\d+,\d+$/.test(value)))value=value.replace(/\./g,'').replace(',','.');
      const kwh=value===''?NaN:Number(value)/(unit==='Wh'?1000:1);
      if(!Number.isFinite(kwh)||kwh<0)throw Error('Row '+(i+2)+': invalid non-negative interval energy.');
      if(seen.has(ts))throw Error('Duplicate UTC timestamp at row '+(i+2));seen.add(ts);return {ts,kwh};
    }).sort((a,b)=>a.ts-b.ts);
    if(readings.length<2)throw Error('At least two readings are needed.');
    const deltas=readings.slice(1).map((r,i)=>r.ts-readings[i].ts),inferred=Math.min(...deltas),step=options.intervalMinutes?Number(options.intervalMinutes)*60000:inferred;
    if(![900000,1800000,3600000].includes(step)||readings.some(r=>r.ts%step!==0)||deltas.some(d=>d%step!==0))throw Error('Only aligned 15, 30 or 60-minute interval energy is supported. Select the interval explicitly when gaps prevent inference.');
    if(options.timestampConvention==='end')readings=readings.map(r=>({...r,ts:r.ts-step}));
    const missing=deltas.reduce((s,d)=>s+d/step-1,0),map=new Map(readings.map(r=>[r.ts,r.kwh])),hourly=new Map();
    for(const r of readings){const h=Math.floor(r.ts/3600000)*3600000;if(r.ts!==h)continue;const parts=Array.from({length:3600000/step},(_,i)=>map.get(h+i*step));if(parts.every(Number.isFinite))hourly.set(h,parts.reduce((a,b)=>a+b,0));}
    return {readings,hourly,step,missing,total:readings.reduce((s,r)=>s+r.kwh,0),first:readings[0].ts,last:readings.at(-1).ts,adapter:{headers,timestampColumn:timestamp>=0?headers[timestamp]:null,dateColumn:date>=0?headers[date]:null,timeColumn:time>=0?headers[time]:null,energyColumn:headers[energy],timeZone:options.timeZone||'offset',unit,timestampConvention:options.timestampConvention||'start',dstSequence:options.dstSequence===true}};
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
  function knownUntil(ts){
    const p=Object.fromEntries(berlinParts.formatToParts(ts).filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));
    const calendar=Date.UTC(p.year,p.month-1,p.day)+(p.hour>=16?2:1)*86400000;
    return parseTimestamp(new Date(calendar).toISOString().slice(0,10)+'T00:00:00','Europe/Berlin',false,null,0);
  }
  function deadlineSchedule(prices,available,deadlines,power=7.4,efficiency=.9,household=null,connection=11){
    const load=prices.map(()=>0);const caps=prices.map((_,i)=>available[i]?Math.min(power,household?Math.max(0,connection-household[i]):power):0);
    for(const [stop,target] of deadlines.slice().sort((a,b)=>a[0]-b[0])){
      let need=Math.max(0,target/efficiency-load.slice(0,stop).reduce((a,b)=>a+b,0));
      const order=prices.slice(0,stop).map((_,i)=>i).sort((a,b)=>prices[a]-prices[b]||a-b);
      for(const i of order){const extra=Math.min(Math.max(0,caps[i]-load[i]),need);load[i]+=extra;need-=extra;if(need<=1e-10)break;}
    }return load;
  }
  function rollingSchedule(prices,timestamps,available,deadlines,policy,forecast={},power=7.4,efficiency=.9,household=null,connection=11){
    if(!Number.isFinite(power)||power<=0||!Number.isFinite(efficiency)||efficiency<=0||efficiency>1||prices.length!==timestamps.length||prices.some(p=>!Number.isFinite(p)))throw Error('Invalid rolling constraints');
    const load=prices.map(()=>0),log=[];
    for(let i=0;i<prices.length;i++){
      const delivered=load.slice(0,i).reduce((a,b)=>a+b,0)*efficiency,remaining=deadlines.filter(([stop])=>stop>i).map(([stop,target])=>[stop-i,Math.max(0,target-delivered)]),cutoff=knownUntil(timestamps[i]);
      const allowed=available.slice(i),planning=prices.slice(i);
      if(policy==='immediate')planning.forEach((_,j)=>planning[j]=j);
      else if(policy!=='oracle')for(let j=i;j<prices.length;j++)if(timestamps[j]>=cutoff){
        if(policy==='known_only'){allowed[j-i]=false;planning[j-i]=0;}
        else {const value=forecast[timestamps[j]];if(!Number.isFinite(value))throw Error('Unknown-hour forecast is unavailable');planning[j-i]=value;}
      }
      const plan=deadlineSchedule(planning,allowed,remaining,power,efficiency,household?household.slice(i):null,connection);load[i]=plan[0];log.push({ts:timestamps[i],knownUntil:cutoff,kwh:load[i]});
    }
    const shortfalls=deadlines.map(([stop,target])=>Math.max(0,target-load.slice(0,stop).reduce((a,b)=>a+b,0)*efficiency));
    return {load,log,shortfalls,delivered:load.reduce((a,b)=>a+b,0)*efficiency,shortfall:Math.max(...shortfalls)};
  }
  const api={schedule,cost,capture,parseCSV,inspectCSV,demandForecast,knownUntil,deadlineSchedule,rollingSchedule};root.EnergyCore=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
