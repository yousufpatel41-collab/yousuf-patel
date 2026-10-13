'use strict';
window.HouseholdBill = (() => {
  const key = 'household-electricity-bill-v1';
  const reference = {rate: 37, published: '21 August 2026', checked: '13 October 2026', url: 'https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/'};
  const defaults = {mode:'known',period:'annual',consumption:3000,pricing:'contract',rate:32,fee:10,firstDate:'2026-01-01',lastDate:'2026-02-01',firstReading:1000,lastReading:1250,fridge:180,washEnergy:0.6,washCycles:3,dishEnergy:0.75,dishCycles:4,cooking:1.5,lightWatts:40,lightHours:5,deviceWatts:90,deviceHours:4,standbyWatts:12,other:200,hotWater:0,heating:0};
  let state = {...defaults};
  const $ = id => document.getElementById(id);
  const n = (x,d=1) => new Intl.NumberFormat('en-GB',{maximumFractionDigits:d,minimumFractionDigits:d}).format(x);
  const money = x => new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR'}).format(x);
  const clean = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const numericKeys = Object.keys(defaults).filter(k => typeof defaults[k] === 'number');
  function validState(s) {
    return ['known','meter','appliances'].includes(s.mode) && ['annual','monthly'].includes(s.period) && ['contract','benchmark'].includes(s.pricing)
      && numericKeys.every(k => Number.isFinite(s[k]) && s[k] >= 0 && s[k] <= 10000000)
      && s.lightHours <= 24 && s.deviceHours <= 24 && s.rate <= 1000 && s.fee <= 10000
      && /^\d{4}-\d{2}-\d{2}$/.test(s.firstDate) && /^\d{4}-\d{2}-\d{2}$/.test(s.lastDate);
  }
  try {const s=JSON.parse(localStorage.getItem(key));if(s&&validState(s))state={...defaults,...s};} catch {}
  const applianceRows = s => [
    ['Fridge / freezer',s.fridge,'Annual kWh from the energy label'],
    ['Washing machine',s.washEnergy*s.washCycles*52,`${n(s.washEnergy,2)} kWh/cycle × ${n(s.washCycles)} cycles/week × 52`],
    ['Dishwasher',s.dishEnergy*s.dishCycles*52,`${n(s.dishEnergy,2)} kWh/cycle × ${n(s.dishCycles)} cycles/week × 52`],
    ['Cooking',s.cooking*365,`${n(s.cooking,2)} kWh/day × 365`],
    ['Lighting',s.lightWatts/1000*s.lightHours*365,`${n(s.lightWatts)} W × ${n(s.lightHours)} h/day × 365 ÷ 1,000`],
    ['TV / computer / other devices',s.deviceWatts/1000*s.deviceHours*365,`${n(s.deviceWatts)} W × ${n(s.deviceHours)} h/day × 365 ÷ 1,000`],
    ['Always-on devices',s.standbyWatts/1000*24*365,`${n(s.standbyWatts)} W × 24 h/day × 365 ÷ 1,000`],
    ['Other electricity use',s.other,'Additional annual kWh'],
    ['Electric hot water',s.hotWater,'Additional annual kWh, if applicable'],
    ['Electric heating',s.heating,'Additional annual kWh, if applicable']
  ];
  function calculation(s) {
    if (!validState(s)) return {error:'Check the values. Consumption, prices and readings must be non-negative; daily hours cannot exceed 24.'};
    let annual,detail;
    if(s.mode==='known') {annual=s.consumption*(s.period==='monthly'?12:1);detail=s.period==='monthly'?'Monthly consumption multiplied by 12':'Annual consumption entered by you';}
    else if(s.mode==='meter') {
      const days=(Date.parse(s.lastDate+'T00:00:00Z')-Date.parse(s.firstDate+'T00:00:00Z'))/86400000;
      if(!Number.isFinite(days)||days<=0)return {error:'The second meter date must be after the first date.'};
      if(s.lastReading<s.firstReading)return {error:'The second reading must be at least the first reading. A replaced or reset meter needs a separate calculation.'};
      annual=(s.lastReading-s.firstReading)*365/days;detail=`${n(s.lastReading-s.firstReading)} kWh over ${n(days,0)} days, scaled to 365 days`;
    } else {annual=applianceRows(s).reduce((total,r)=>total+r[1],0);detail='Sum of your appliance and additional-use estimates';}
    const rate=s.pricing==='benchmark'?reference.rate:s.rate;
    const energy=annual*rate/100,fee=s.pricing==='benchmark'?0:s.fee*12;
    return {annual,detail,rate,energy,fee,year:energy+fee,month:(energy+fee)/12,benchmark:s.pricing==='benchmark'};
  }
  const field=(key,label,step='1',max='10000000')=>`<label for="h_${key}">${label}<input id="h_${key}" name="${key}" type="number" min="0" max="${max}" step="${step}" value="${state[key]}" required></label>`;
  const option=(value,label,current)=>`<option value="${value}"${current===value?' selected':''}>${label}</option>`;
  function usageForm() {
    if(state.mode==='known')return `<div class="house-inputs">${field('consumption',state.period==='annual'?'Electricity use (kWh/year)':'Electricity use (kWh/month)','any')}<label for="h_period">Period<select id="h_period">${option('annual','Per year',state.period)}${option('monthly','Per month',state.period)}</select></label></div><p class="small">Find annual consumption (Jahresverbrauch) on your latest electricity bill. The starting 3,000 kWh is an editable example, not a standard for every home.</p>`;
    if(state.mode==='meter')return `<div class="house-inputs"><label for="h_firstDate">First reading date<input id="h_firstDate" type="date" value="${clean(state.firstDate)}" required></label>${field('firstReading','First meter reading (kWh)','0.1')}<label for="h_lastDate">Second reading date<input id="h_lastDate" type="date" value="${clean(state.lastDate)}" required></label>${field('lastReading','Second meter reading (kWh)','0.1')}</div><p class="small">Use two readings from the same electricity meter. We scale the difference to 365 days. A short or seasonal period can overestimate or underestimate a full year, especially with electric heating.</p>`;
    return `<p class="small">Starter values below are illustrative assumptions. Replace them with energy-label or measured values; enter zero for equipment you do not use. Include only appliances on this electricity account.</p><div class="house-inputs">${field('fridge','Fridge / freezer (kWh/year)')}${field('washEnergy','Washing machine (kWh/cycle)','0.01')}${field('washCycles','Washing cycles per week','0.1')}${field('dishEnergy','Dishwasher (kWh/cycle)','0.01')}${field('dishCycles','Dishwasher cycles per week','0.1')}${field('cooking','Cooking (kWh/day)','0.1')}${field('lightWatts','Total lighting power (watts)')}${field('lightHours','Lighting hours per day','0.1','24')}${field('deviceWatts','TV / computer power (watts)')}${field('deviceHours','TV / computer hours per day','0.1','24')}${field('standbyWatts','Always-on power (watts)')}${field('other','Other electricity (kWh/year)')}${field('hotWater','Electric hot water (kWh/year)')}${field('heating','Electric heating (kWh/year)')}</div><p class="small">Hot water and heating start at zero: they are excluded until you enter their electricity use. Avoid counting the same device twice. If you already have total billed kWh, use that instead.</p>`;
  }
  function render() {
    const c=calculation(state);
    const head=`<section class="house-intro"><p class="eyebrow">YOUR HOUSEHOLD ELECTRICITY BILL</p><h2>What could my home’s bill be?</h2><p>Enter electricity use and your tariff. Get a monthly budget estimate and an annual total for one household.</p></section>`;
    const form=`<section class="panel"><form id="householdForm"><h2>1. Your electricity use</h2><label class="house-select" for="h_mode">How do you know your consumption?<select id="h_mode">${option('known','I know my kWh from a bill',state.mode)}${option('meter','Use two meter readings',state.mode)}${option('appliances','Estimate from appliances',state.mode)}</select></label>${usageForm()}<div class="house-divider"></div><h2>2. Your electricity price</h2><label class="house-select" for="h_pricing">Which price should we use?<select id="h_pricing">${option('contract','My supplier tariff',state.pricing)}${option('benchmark','German average — rough comparison',state.pricing)}</select></label>${state.pricing==='contract'?`<div class="house-inputs">${field('rate','Unit price (ct/kWh, including VAT)','0.01','1000')}${field('fee','Fixed charge (EUR/month, including VAT)','0.01','10000')}</div><p class="small">Use Arbeitspreis and Grundpreis from your contract. If the fixed charge is annual, divide it by 12; include any separate meter fee. The starting 32 ct/kWh and EUR 10/month are example inputs, not a supplier quote.</p>`:`<p class="small">Uses the 37.0 ct/kWh BDEW household reference as an indicative all-in cost per kWh. No separate fixed fee is added. This average is based on a 3,500 kWh/year reference household; scaling it to your usage is only a rough comparison, not your tariff.</p>`}<div class="row-actions"><button class="primary" type="submit">Calculate my bill</button><button class="secondary" id="houseReset" type="button">Reset example</button></div><p id="houseError" role="alert" class="house-error"${c.error?'':' hidden'}>${c.error?clean(c.error):''}</p></form></section>`;
    const benchmark=`<section class="panel benchmark"><div><p class="eyebrow">GERMANY PRICE REFERENCE</p><h2>37.0 ct/kWh</h2><p>BDEW’s household average for 2026 to date. Actual prices vary by supplier, contract and location.</p></div><p class="small"><a href="${reference.url}" target="_blank" rel="noopener">BDEW electricity price analysis ↗</a><br>Published ${reference.published} · checked ${reference.checked}. This is a manually checked reference, not a live tariff feed. The wholesale charts use a separate historical SMARD snapshot.</p></section>`;
    if(c.error)return {html:head+form+benchmark,rows:[]};
    const cards=`<div class="kpis house-results" aria-label="Bill estimate">${[['Estimated monthly cost',money(c.month),'Annual cost divided by 12'],['Estimated annual cost',money(c.year),c.benchmark?'Rough market benchmark':'Your entered tariff and consumption'],['Electricity use per year',n(c.annual,0)+' kWh',state.mode==='known'?'From your entered consumption':'Estimated from your inputs'],['Price used',n(c.rate,2)+' ct/kWh',c.benchmark?'Indicative all-in reference':money(state.fee)+' fixed fee per month']].map(([label,value,note])=>`<div class="kpi"><div class="label">${label}</div><div class="value">${value}</div><div class="note">${note}</div></div>`).join('')}</div>`;
    const calc=`<section class="panel"><h2>Your calculation</h2><p class="description">${clean(c.detail)}. This full-year estimate does not use the historical date filters.</p><div class="house-equation"><span>${n(c.annual)} kWh × ${n(c.rate/100,4)} EUR/kWh</span><strong>${money(c.energy)}</strong></div>${!c.benchmark?`<div class="house-equation"><span>Fixed charge: ${money(state.fee)} × 12 months</span><strong>${money(c.fee)}</strong></div>`:''}<div class="house-equation total"><span>Estimated annual total</span><strong>${money(c.year)}</strong></div><p class="small">Monthly amount = annual total ÷ 12. Your provider may collect a different number of instalments. Future usage or price changes, one-off bonuses, solar exports and contract changes are not modelled.</p><a class="small" href="https://www.verbraucherzentrale.de/wissen/energie/preise-tarife-anbieterwechsel/rechner-das-ist-ihr-passender-abschlag-fuer-strom-gas-oder-fernwaerme-75669" target="_blank" rel="noopener">How household bill estimates are calculated ↗</a></section>`;
    const rows=[{ConsumptionMethod:state.mode,ConsumptionDetail:c.detail,AnnualKWh:c.annual,MonthlyKWh:c.annual/12,PriceMode:state.pricing,RateCentsPerKWh:c.rate,AnnualEnergyOrBenchmarkEUR:c.energy,AnnualSeparateFixedFeeEUR:c.fee,EstimatedAnnualEUR:c.year,EstimatedMonthlyEUR:c.month,ReferencePublished:reference.published,ReferenceChecked:reference.checked}];
    const appliances=state.mode==='appliances'?`<section class="panel"><h2>Where your estimated consumption comes from</h2><div class="table-wrap"><table><thead><tr><th>Equipment / use</th><th>Annual kWh</th><th>Calculation</th></tr></thead><tbody>${applianceRows(state).map(([label,kwh,formula])=>`<tr><td>${label}</td><td>${n(kwh)}</td><td>${clean(formula)}</td></tr>`).join('')}</tbody></table></div></section>`:'';
    return {html:head+cards+`<div class="house-layout"><div>${form}</div><div>${calc}${benchmark}</div></div>`+appliances,rows};
  }
  function readForm() {
    const next={...state};
    for(const k of Object.keys(defaults))if($('h_'+k))next[k]=typeof defaults[k]==='number'?($('h_'+k).value.trim()===''?NaN:Number($('h_'+k).value)):$('h_'+k).value;
    return next;
  }
  function bind(rerender) {
    const form=$('householdForm');
    const save=next=>{state=next;try{localStorage.setItem(key,JSON.stringify(state));}catch{}};
    form.onsubmit=e=>{e.preventDefault();const next=readForm();save(next);rerender();};
    for(const k of ['mode','pricing','period'])if($('h_'+k))$('h_'+k).onchange=()=>{
      const next=readForm();
      if(k==='period'&&next.period!==state.period)next.consumption*=next.period==='monthly'?1/12:12;
      if(!validState(next)){const error=$('houseError');error.hidden=false;error.textContent='Please check the values before switching options.';return;}
      save(next);rerender();
    };
    $('houseReset').onclick=()=>{state={...defaults};try{localStorage.removeItem(key);}catch{}rerender();};
  }
  return {render,bind};
})();
