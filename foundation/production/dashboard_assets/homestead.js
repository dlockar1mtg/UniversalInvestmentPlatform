/* The Homestead: the household plan (income, bills, savings, balances) and the road to the house.
   Replaces the Income & Net Worth Tracker workbook. Reads and writes /v1/household-plan; the
   ranges come from /v1/household-plan/projection with the live holdings from the Treasury. */
(()=>{
"use strict";
const S={doc:null,plan:null,dirty:false,proj:null,projKey:"",pick:null,chart:"house",preview:null,msg:null,tried:null,loading:false,nw:null,nwErr:null,ret:null,retKey:"",retTried:null,retBusy:false,retErr:null,homeDoc:null,homeKey:"",homeTried:null,homeErr:null};
const byId=id=>document.getElementById(id);
const esc=v=>{const n=document.createElement("span");n.textContent=String(v??"");return n.innerHTML};
const num=v=>{if(v===null||v===undefined||v==="")return null;const n=Number(v);return Number.isFinite(n)?n:null};
const money=(v,d=0)=>{const n=num(v);return n===null?"\u2014":`${n<0?"\u2212":""}$${Math.abs(n).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d})}`};
const compact=n=>Math.abs(n)>=1e6?`$${+(n/1e6).toFixed(2)}M`:Math.abs(n)>=1e3?`$${Math.round(n/1e3)}k`:`$${Math.round(n)}`;
const pctText=(v,d=0)=>{const n=num(v);return n===null?"\u2014":`${(n*100).toFixed(d)}%`};
const MONTHS=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const monthLabel=m=>/^\d{4}-\d{2}$/.test(String(m||""))?`${MONTHS[Number(m.slice(5,7))-1]} ${m.slice(0,4)}`:"\u2014";
const nowMonth=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`};
const SLEEVES=[["stocks","Stock ETFs"],["crypto","Crypto"],["metals","Metals"],["mtg","MTG sealed"],["cash","T-bills"]];
const key=()=>sessionStorage.getItem("uiip-dashboard-key")||"";
async function call(path,options={}){
  const r=await fetch(path,{...options,headers:{"X-API-Key":key(),"Accept":"application/json",...(options.headers||{})}});
  const body=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(body.error?.message||`Request failed (${r.status})`);
  return body;
}
const post=(path,body)=>call(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
const clone=o=>JSON.parse(JSON.stringify(o));
const sum=o=>Object.values(o||{}).reduce((a,b)=>a+(num(b)||0),0);
const R=()=>window.UIPRealm||{};
function statements(){const items=(R().state?.home?.retirementAccounts?.accounts||[]).filter(a=>a.category==="retirement"&&a.items?.length);if(!items.length)return null;return {value:Math.round(items.reduce((a,r)=>a+(num(r.estimate?.value??r.items[0].current_value)||0),0)*100)/100,count:items.length,latest:items.map(r=>String(r.items[0].as_of).slice(0,10)).sort().pop()}}
function liveHoldings(){const d=R().state?.home;if(!d||!R().realmTotals)return null;const t=R().realmTotals(d);return Object.values(t).some(v=>v>0)?t:null}

/* Roll the plan forward exactly like the server (and the old workbook) so edits show at once. */
function roll(plan){
  const s=plan.settings,ri=s.plan_investment_return/12,rr=s.plan_retirement_return/12;
  let prev={bank_balance:0,retirement_balance:0,investment_balance:0,house_fund_balance:0,home_equity:0};
  return plan.months.map((m,k)=>{
    const income=sum(m.income),expenses=sum(m.expenses),net=income+expenses;
    const toBank=net-(num(m.investment_contribution)||0)-(num(m.house_fund_contribution)||0);
    const pick=(f,calc)=>num(m[f])!==null?num(m[f]):calc;
    const check=m.bank_check&&num(m.bank_check.balance)!==null?m.bank_check:null;
    const b={bank_balance:pick("bank_balance",check?num(check.balance)+stillToCome(m,check.done):prev.bank_balance+toBank),
      retirement_balance:pick("retirement_balance",(k?prev.retirement_balance*(1+rr):0)+(num(m.retirement_contribution)||0)),
      investment_balance:pick("investment_balance",(k?prev.investment_balance*(1+ri):0)+(num(m.investment_contribution)||0)),
      house_fund_balance:pick("house_fund_balance",prev.house_fund_balance+(num(m.house_fund_contribution)||0)),
      home_equity:pick("home_equity",prev.home_equity)};
    prev=b;
    return {month:m.month,income,expenses,net,toBank,...b,net_worth:b.bank_balance+b.retirement_balance+b.investment_balance+b.house_fund_balance+b.home_equity,
      anchored:["bank_balance","retirement_balance","investment_balance"].filter(f=>num(m[f])!==null),
      checked:check&&num(m.bank_balance)===null?check.as_of:null};
  });
}
/* What the month's lines not yet done still add to the bank: income +, bills (stored negative) and transfers -. */
const TRANSFERS=[["investment_contribution","Into investments"],["house_fund_contribution","Into the house fund"]];
function stillToCome(m,done){
  const d=new Set(done||[]);let t=0;
  for(const [k,v] of Object.entries(m.income||{}))if(!d.has(`income:${k}`))t+=num(v)||0;
  for(const [k,v] of Object.entries(m.expenses||{}))if(!d.has(`expenses:${k}`))t+=num(v)||0;
  for(const [k] of TRANSFERS)if(!d.has(k))t-=num(m[k])||0;
  return t;
}

/* ---------------- loading ---------------- */
function load(){
  if(S.loading)return;S.loading=true;
  call("/v1/presentation/housing").then(h=>{S.housing=h;refreshHome(true);if(S.doc)render()}).catch(()=>{S.housing={available:false}});
  loadNetWorth();
  call("/v1/household-plan").then(doc=>{S.doc=doc;S.plan=doc.available?clone(doc.plan):null;S.dirty=false;S.loading=false;render();refreshProjection(true)})
    .catch(error=>{S.loading=false;S.msg=["bad",error.message];render()});
}
function loadNetWorth(){
  S.nwAt=Date.now();
  call("/v1/net-worth").then(doc=>{S.nw=doc;S.nwErr=null;if(S.doc)render()}).catch(error=>{S.nwErr=error.message;if(S.doc)render()});
}
function refreshProjection(force){
  if(!S.doc?.available)return;
  refreshHome(force);
  refreshRetirement(force);
  const holdings=liveHoldings();
  const body={as_of_month:nowMonth(),holdings:holdings||undefined,settings:S.tried||undefined};
  const k=JSON.stringify([S.doc.version?.version_id,body]);
  if(!force&&k===S.projKey)return;
  S.projKey=k;
  post("/v1/household-plan/projection",body).then(p=>{if(S.projKey!==k)return;S.proj=p;render()}).catch(error=>{S.msg=["bad",`Ranges could not be computed: ${error.message}`];render()});
}


/* ---------------- net worth, month by month ---------------- */
const PARTS=[["investments","Investments"],["retirement","Retirement"],["bank","Bank"],["house_fund","House fund"],["home_equity","Home equity"]];
function netWorth(){
  const head=`<div class="rpg-section-head"><h2 id="rpg-home-nw-h" class="rpg-stone-title">Net worth, month by month</h2><button type="button" class="rpg-btn rpg-link" data-home-export>Download my data</button></div>`;
  if(S.nwErr)return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-nw-h">${head}<p class="rpg-parch-note">${esc(`Net worth could not be read: ${S.nwErr}`)}</p></section>`;
  if(!S.nw)return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-nw-h">${head}<p class="rpg-parch-note">Adding up today\u2019s net worth\u2026</p></section>`;
  const c=S.nw.current,months=S.nw.months||[];
  const shown=PARTS.filter(([k])=>num(c.components[k])!==null&&(k!=="home_equity"||num(c.components[k])>0));
  const chips=shown.map(([k,l])=>`<span>${esc(l)} <strong class="num">${money(c.components[k])}</strong></span>`).join("");
  const inv=c.investments||{};const invParts=[["certified","certified holdings"],["manual_etfs","stocks & ETFs"],["acorns","Acorns"],["mtg_singles","MTG singles"]].filter(([k])=>num(inv[k])).map(([k,l])=>`${l} ${money(inv[k])}`).join(" \u00b7 ");
  const prev=months.filter(m=>m.month<c.month).pop(),first=months[0];
  const change=(from,label)=>from?`<span>${esc(label)} <strong class="num ${num(c.net_worth)-num(from.net_worth)<0?"rpg-down":"rpg-up"}">${num(c.net_worth)-num(from.net_worth)<0?"\u2212":"+"}${money(Math.abs(num(c.net_worth)-num(from.net_worth)))}</strong></span>`:"";
  const missing=(c.missing||[]).map(k=>(PARTS.find(p=>p[0]===k)||[k,k])[1]);
  const notes=[...(c.investments?.notes||[])];
  const why=`Investments are the Treasury\u2019s total (certified holdings, Acorns, manual stocks and ETFs, and MTG singles). Retirement is your latest statements plus the paychecks since. Bank and the house fund are this month in your plan (your check-in when you have one). Debts are not counted yet. A month is kept for good once it ends; months before the first capture come from the balances you entered in the plan.`;
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-nw-h">${head}<div class="rpg-home-nw"><div><div class="rpg-stat-label">${esc(monthLabel(c.month))}, today</div><div class="rpg-stat-big num">${money(c.net_worth)}</div><div class="rpg-crumb-stats rpg-home-nw-parts">${chips}${change(prev,`Since ${monthLabel(prev?.month)}`)}${prev&&first&&first.month!==prev.month?change(first,`Since ${monthLabel(first.month)}`):""}</div>${invParts?`<p class="rpg-vault-why">${esc(`Investments: ${invParts}.`)}</p>`:""}</div></div>${nwChart(months,c)}${missing.length?`<p class="rpg-vault-why">${esc(`Not in the total yet: ${missing.join(", ")}.`)}</p>`:""}${notes.map(n=>`<p class="rpg-vault-why">${esc(n)}</p>`).join("")}<p class="rpg-crumb-note">${esc(why)}</p></section>`;
}
function nwChart(months,c){
  const rows=months.some(m=>m.month===c.month)?months.map(m=>m.month===c.month?{...m,net_worth:c.net_worth}:m):[...months,{month:c.month,net_worth:c.net_worth,source:"TODAY"}];
  if(!rows.length)return "";
  const top0=Math.max(1,...rows.map(r=>num(r.net_worth)||0))*1.1,step=niceStep(top0,5),top=Math.ceil(top0/step)*step;
  const X0=78,X1=960,Y0=14,Y1=230,slot=(X1-X0)/rows.length,w=Math.min(46,slot*0.7),y=v=>Y1-(Y1-Y0)*Math.max(0,v)/top;
  const grid=[],labels=[];
  for(let v=0;v<=top+1;v+=step){grid.push(`M${X0} ${y(v).toFixed(1)} H${X1}`);labels.push(`<text x="${X0-8}" y="${(y(v)+5).toFixed(1)}" text-anchor="end">${esc(compact(v))}</text>`)}
  const every=Math.max(1,Math.ceil(rows.length/8));
  const bars=rows.map((r,i)=>{const cx=X0+slot*(i+.5),v=num(r.net_worth)||0,planned=r.source==="PLAN_LEDGER_ACTUALS";
    return `<rect x="${(cx-w/2).toFixed(1)}" y="${y(v).toFixed(1)}" width="${w.toFixed(1)}" height="${(Y1-y(v)).toFixed(1)}" fill="${planned?"#7d6a45":"#d9b45a"}"><title>${esc(`${monthLabel(r.month)}: ${money(v)}${planned?" (from the plan's entered balances)":r.month===c.month?" (this month, so far)":""}`)}</title></rect>${i%every===0||i===rows.length-1?`<text x="${cx.toFixed(1)}" y="252" text-anchor="middle">${esc(monthLabel(r.month))}</text>`:""}`}).join("");
  const key=rows.some(r=>r.source==="PLAN_LEDGER_ACTUALS")?`<div class="rpg-chart-key"><span><svg width="18" height="10" aria-hidden="true"><rect width="18" height="10" fill="#d9b45a"/></svg>Kept by the UIP</span><span><svg width="18" height="10" aria-hidden="true"><rect width="18" height="10" fill="#7d6a45"/></svg>From the plan\u2019s entered balances</span></div>`:"";
  return `${key}<svg viewBox="0 0 1000 264" class="rpg-fluid" role="img" aria-label="${esc(`Net worth by month, ${rows.length} month${rows.length===1?"":"s"}: ${rows.map(r=>`${monthLabel(r.month)} ${money(r.net_worth)}`).join(", ")}.`)}"><g stroke="#3a3127" stroke-width="1" fill="none"><path d="${grid.join(" ")}"/></g>${bars}<g fill="#b9a98a" font-size="14">${labels.join("")}</g></svg>`;
}
async function downloadData(){
  try{
    const r=await fetch("/v1/my-data/export",{headers:{"X-API-Key":key(),"Accept":"application/json"}});
    if(!r.ok){const body=await r.json().catch(()=>({}));throw new Error(body.error?.message||`Request failed (${r.status})`)}
    const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");
    a.href=url;a.download=`uip-my-data-${today()}.json`;document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),10000);
    setMsg("ok","Your data is downloading: every transaction, holding, statement, plan and net-worth month, as one file.");
  }catch(error){setMsg("bad",`The download did not work: ${error.message}`)}
  render();
}


/* ---------------- the emergency fund ---------------- */
function essentialLines(plan){const e=plan.settings?.essential_lines;return Array.isArray(e)?e:plan.expense_lines||[]}
function emergency(){
  const month=nowMonth(),m=S.plan.months.find(x=>x.month===month);if(!m)return "";
  const keep=new Set(essentialLines(S.plan));
  const bills=Math.abs(Object.entries(m.expenses||{}).filter(([k])=>keep.has(k)).reduce((a,[,v])=>a+(num(v)||0),0));
  const want=num(S.plan.settings.safety_fund_months)??6,target=bills*want;
  const row=roll(S.plan).find(r=>r.month===month)||{},bank=num(row.bank_balance)||0;
  const live=liveHoldings(),tbills=live?num(live.purse)||0:0,have=Math.max(0,bank)+tbills;
  const covered=bills>0?have/bills:null,short=Math.max(0,target-have),save=num(row.toBank)||0;
  const pct=target>0?Math.min(1,have/target):1;
  const W=880,bar=`<svg viewBox="0 0 ${W+20} 34" class="rpg-fluid rpg-home-ef-bar" role="img" aria-label="${esc(`${covered===null?"\u2014":covered.toFixed(1)} of ${want} months covered`)}"><rect x="10" y="8" width="${W}" height="16" fill="#2a241d" stroke="#6b5432"/><rect x="10" y="8" width="${(W*pct).toFixed(1)}" height="16" fill="${pct>=1?"#4d7a3a":"#b5862f"}"/>${Array.from({length:Math.max(0,Math.round(want)-1)},(_,i)=>`<path d="M${(10+W*(i+1)/want).toFixed(1)} 8 V24" stroke="#1c1814" stroke-width="2"/>`).join("")}</svg>`;
  const verdict=bills<=0?"Mark which bills are essential below to set the target.":pct>=1?`Covered: ${covered.toFixed(1)} months of essential bills, past your ${want}-month target. Money beyond it can go to the house fund or investments.`:`${covered.toFixed(1)} of ${want} months covered. ${money(short)} to go${save>0?`; at this month\u2019s ${money(save)} left for the bank, about ${Math.ceil(short/save)} month${Math.ceil(short/save)===1?"":"s"}.`:"; the plan leaves nothing for the bank this month."}`;
  const picks=(S.plan.expense_lines||[]).map(l=>`<label class="rpg-check"><input type="checkbox" data-home-essential="${esc(l)}"${keep.has(l)?" checked":""}> ${esc(l)} <span class="rpg-muted num">${money(Math.abs(num(m.expenses[l])||0))}</span></label>`).join("");
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-ef-h"><div class="rpg-section-head"><h2 id="rpg-home-ef-h" class="rpg-stone-title">The emergency fund \u00b7 ${esc(want)} months</h2><span class="rpg-crumb-note">${esc(`Essential bills ${money(bills)} a month \u00b7 target ${money(target)}`)}</span></div><p class="rpg-guild-counsel">${esc(verdict)}</p>${bar}<div class="rpg-crumb-stats"><span>Bank this month <strong class="num">${money(bank)}</strong></span><span>T-bills (the Purse) <strong class="num">${money(tbills)}</strong></span><span>Have <strong class="num">${money(have)}</strong></span></div><details class="rpg-home-ef-pick"><summary>Which bills are essential</summary><form class="rpg-home-ef-form" data-home-essentials>${picks}<div class="rpg-home-actions"><button type="submit" class="rpg-btn rpg-action">Save</button></div></form></details><p class="rpg-crumb-note">${esc("Essential means it has to be paid even in a bad month (rent, utilities, food, transport, insurance, minimum debt payments). The house fund and retirement are not counted: they have their own jobs. The house plan keeps the same number of months as its safety fund. Change the months under The house and the plan.")}</p></section>`;
}


/* ---------------- the road to early retirement ---------------- */
function retirementAccounts(){return (R().state?.home?.retirementAccounts?.accounts||[]).filter(a=>a.category==="retirement"&&a.items?.length)}
function refreshRetirement(force){
  if(!S.doc?.available)return;
  const cfg=S.retTried||S.plan?.settings?.retirement;
  if(!cfg){S.ret=null;return}
  const accts=retirementAccounts(),st=statements(),holdings=liveHoldings();
  const deposits={};let monthly=0;
  for(const a of accts)if(a.schedule){deposits[a.account_id]={per_paycheck:num(a.schedule.per_paycheck),every_days:num(a.schedule.every_days)};monthly+=num(a.schedule.monthly_equivalent)||0}
  const body={as_of_month:nowMonth(),holdings:holdings||undefined,retirement_start:st?st.value:0,retirement_monthly:Math.round(monthly*100)/100,deposits,retirement:S.retTried||undefined,home_value:S.homeDoc&&!S.homeDoc.preview?S.homeDoc.value:undefined};
  const k=JSON.stringify([S.doc.version?.version_id,body]);
  if(!force&&k===S.retKey)return;
  S.retKey=k;S.retBusy=true;S.retErr=null;
  post("/v1/household-plan/retirement-path",body).then(out=>{if(S.retKey!==k)return;S.ret=out;S.retBusy=false;render()}).catch(error=>{if(S.retKey!==k)return;S.retBusy=false;S.retErr=error.message;render()});
}
const pct1=v=>{const n=num(v);return n===null?"\u2014":`${Math.round(n*100)}%`};
function retirementSection(){
  const cfg=S.retTried||S.plan.settings.retirement;
  const head=sub=>`<div class="rpg-section-head"><h2 id="rpg-home-rt-h" class="rpg-stone-title">The road to early retirement${cfg?.retire_age?` \u00b7 age ${esc(cfg.retire_age)}`:""}</h2><span class="rpg-crumb-note">${esc(sub)}</span></div>`;
  if(!cfg)return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-rt-h">${head("Not set up yet")}<p class="rpg-guild-counsel">Enter your age, the age you want to retire and what you expect to spend a year, and the Homestead will run the same simulated markets to 95: the bridge years before 59\u00bd paid from the money you can reach, then retirement accounts.</p>${retirementForm(null)}</section>`;
  if(S.retErr)return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-rt-h">${head("")}<p class="rpg-parch-note">${esc(`The retirement path could not be worked out: ${S.retErr}`)}</p>${retirementForm(cfg)}</section>`;
  const p=S.ret;
  if(!p||!p.configured)return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-rt-h">${head("")}<p class="rpg-parch-note">Running the markets to age 95\u2026</p>${retirementForm(cfg)}</section>`;
  const home=p.cases[0],abroad=p.cases.find(c=>c.case==="abroad");
  const ok=p.chance>=p.on_track_threshold;
  const caseText=c=>c.chance>=p.on_track_threshold?`on track (${pct1(c.chance)} of markets last to 95)`:`${pct1(c.chance)} of markets last to 95; ${c.earliest_age?`age ${c.earliest_age} reaches ${pct1(p.on_track_threshold)}`:"no age up to 70 reaches it"}${c.extra_monthly_for_target?`, or about ${money(c.extra_monthly_for_target)} more a month invested keeps ${p.retire_age}`:""}`;
  const counsel=`Retiring at ${p.retire_age} (${monthLabel(p.retire_month)}) on ${money(p.spending_year)} a year in today's dollars: ${caseText(home)}.${abroad?` Spending ${money(abroad.spending_year)} a year abroad: ${caseText(abroad)}.`:""}`;
  const r=p.at_retirement,acc=p.at_access;
  const tile=(label,value,sub)=>`<div class="rpg-parch rpg-tile"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${value}</div>${sub?`<div class="rpg-stat-sub">${esc(sub)}</div>`:""}</div>`;
  const tiles=`<div class="rpg-tiles rpg-home-tiles">${tile(`Investments you can reach at ${p.retire_age}`,money(r.investments.p50),`bad case ${money(r.investments.p10)} \u00b7 the ${p.bridge_years}-year bridge to 59\u00bd needs about ${money(p.bridge_need)}`)}${tile(`Retirement accounts at ${p.retire_age}`,money(r.retirement.p50),`bad case ${money(r.retirement.p10)} \u00b7 untouched until 59\u00bd in most markets (${pct1(p.chance_bridge_without_retirement)})`)}${tile("Your number",money(p.fi_number),`${money(p.spending_year)} a year at a ${pctText(p.withdrawal_rate,1)} draw (25\u00d7, the 4% guide: ${money(p.fi_number_4pct)})`)}${tile("Saving rate",pctText(p.savings_rate),`of gross pay over the next 12 months: ${money(p.saving_next_12_months.investments)} invested + ${money(p.saving_next_12_months.retirement_deposits)} retirement deposits`)}</div>`;
  const sell=p.other_sell_home?`<p class="rpg-vault-why">${esc(p.other_sell_home.sell_home?`If you sell the home when you retire (about ${money(p.other_sell_home.home_proceeds)} after the loan and 6% selling costs), ${pct1(p.other_sell_home.chance)} of markets last to 95. Tick it in the inputs to plan on it.`:`Without selling the home at retirement: ${pct1(p.other_sell_home.chance)} of markets last to 95.`)}</p>`:"";
  const house=p.house&&p.house.from_investments>0?`<p class="rpg-vault-why">${esc(`The house in ${monthLabel(p.house.month)} takes about ${money(p.house.from_investments)} out of investments (what the house fund and the bank above the safety fund don't cover).`)}</p>`:"";
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-rt-h">${head(`Today's dollars \u00b7 ${p.paths.toLocaleString("en-US")} simulated markets to age ${p.end_age}${S.retTried?" \u00b7 showing unsaved inputs":""}`)}<p class="rpg-guild-counsel">${esc(counsel)}</p>${tiles}${retChart(p)}${house}${sell}${matchTable(p)}${earlyAccess(p)}${retirementForm(cfg)}<ul class="rpg-home-limits">${(p.limitations||[]).map(l=>`<li>${esc(l)}</li>`).join("")}</ul><p class="rpg-footnote">${esc(`Planning assumptions, not forecasts. Rules of thumb, not personal tax or investment advice. ${p.rules.year} IRS limits.`)}</p></section>`;
}
function retChart(p){
  const rows=p.by_age;if(rows.length<2)return "";
  const tot=(r,k)=>r.investments[k]+r.retirement[k];
  const top0=Math.max(...rows.map(r=>Math.min(tot(r,"p90"),tot(r,"p50")*3)))*1.05||1,step=niceStep(top0,6),top=Math.ceil(top0/step)*step;
  const a0=rows[0].age,a1=rows[rows.length-1].age;
  const X0=78,X1=960,Y0=18,Y1=300,x=a=>X0+(X1-X0)*(a-a0)/(a1-a0),y=v=>Y1-(Y1-Y0)*Math.min(1,Math.max(0,v)/top);
  const line=f=>rows.map((r,i)=>`${i?"L":"M"}${x(r.age).toFixed(1)},${y(f(r)).toFixed(1)}`).join(" ");
  const band=`${line(r=>tot(r,"p90"))} ${[...rows].reverse().map(r=>`L${x(r.age).toFixed(1)},${y(tot(r,"p10")).toFixed(1)}`).join(" ")} Z`;
  const grid=[],labels=[];
  for(let v=0;v<=top+1;v+=step){grid.push(`M${X0} ${y(v).toFixed(1)} H${X1}`);labels.push(`<text x="${X0-8}" y="${(y(v)+5).toFixed(1)}" text-anchor="end">${esc(compact(v))}</text>`)}
  const ticks=rows.filter(r=>Math.round(r.age)%5===0).map(r=>`<text x="${x(r.age).toFixed(0)}" y="324" text-anchor="middle">${esc(`age ${Math.round(r.age)}`)}</text>`).join("");
  const mark=(a,l)=>a>a0&&a<a1?`<path d="M${x(a).toFixed(1)} ${Y0} V${Y1}" stroke="#e08a7d" stroke-width="1.5" stroke-dasharray="3 5"/><text x="${(x(a)+6).toFixed(1)}" y="${Y0+14}" fill="#e08a7d">${esc(l)}</text>`:"";
  return `<div class="rpg-chart-key"><span><svg width="26" height="10" aria-hidden="true"><rect width="26" height="10" fill="#4d7a3a" fill-opacity=".35"/></svg>Everything, 8 in 10 markets</span><span><svg width="26" height="8" aria-hidden="true"><path d="M0 4 H26" stroke="#f1d78f" stroke-width="3"/></svg>Everything, typical</span><span><svg width="26" height="8" aria-hidden="true"><path d="M0 4 H26" stroke="#d9b45a" stroke-width="2" stroke-dasharray="2 4"/></svg>Investments you can reach</span><span><svg width="26" height="8" aria-hidden="true"><path d="M0 4 H26" stroke="#9ec0ea" stroke-width="2" stroke-dasharray="6 4"/></svg>Retirement accounts</span></div><svg viewBox="0 0 1000 336" class="rpg-fluid" role="img" aria-label="${esc(`Balance by age in today's dollars: typical ${money(tot(p.at_retirement,"p50"))} at ${p.retire_age}; bad case ${money(tot(p.at_retirement,"p10"))}.`)}"><g stroke="#3a3127" stroke-width="1" fill="none"><path d="${grid.join(" ")}"/></g><path d="${band}" fill="#4d7a3a" fill-opacity=".35"/><path d="${line(r=>r.investments.p50)}" stroke="#d9b45a" stroke-width="2" stroke-dasharray="2 4" fill="none"/><path d="${line(r=>r.retirement.p50)}" stroke="#9ec0ea" stroke-width="2" stroke-dasharray="6 4" fill="none"/><path d="${line(r=>tot(r,"p50"))}" stroke="#f1d78f" stroke-width="3" fill="none"/>${mark(p.retire_age,`retire ${p.retire_age}`)}${mark(59.5,"59\u00bd")}<g fill="#b9a98a" font-size="14">${labels.join("")}${ticks}</g></svg>`;
}
function matchTable(p){
  const m=p.match;if(!m.jobs.length)return "";
  const rows=m.jobs.map(j=>`<tr><th scope="row">${esc(j.label)}</th><td class="num">${money(j.salary)}${j.bonus?` + ${money(j.bonus)} bonus`:""}</td><td class="num">${j.match_pct===null?"\u2014":esc(pctText(j.match_pct,1))}</td><td class="num">${j.you_pct===null?"\u2014":esc(pctText(j.you_pct,1))}${j.you_pct_inferred?`<small> from deposits (${esc(pctText(j.deposit_pct_of_pay,1))} of pay in all)</small>`:""}</td><td>${j.full_match===null?"\u2014":j.full_match?badge("Full match","verdant"):badge(`Missing ${money(j.match_missed_year)} a year`,"crimson")}</td></tr>`).join("");
  const room=`Your own pre-tax deposits come to about ${money(m.employee_total_year)} a year across both jobs; the ${m.rules_year} limit is ${money(m.employee_limit)} per person across every employer, so about ${money(m.room_left_year)} of room is left. For retiring at ${p.retire_age}, extra saving that you can reach before 59\u00bd (a brokerage account, or Roth IRA contributions) does more for the bridge than more 401(k).`;
  return `<div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Job</th><th class="num">Pay</th><th class="num">Match</th><th class="num">Your share</th><th>Match taken</th></tr></thead><tbody>${rows}</tbody></table></div><p class="rpg-vault-why">${esc(room)}</p>`;
}
function earlyAccess(p){
  const r=p.rules,ph=r.roth_ira_phaseout_single;
  const items=[
    "Brokerage and Acorns: reachable any time; only gains are taxed, and long-term gains can be taxed at 0% when other income is low.",
    `Roth IRA: what you put in (not the growth) comes out any time without tax or penalty. Limit ${money(r.ira_limit)} a year in ${r.year}; for a single filer, direct contributions phase out between ${money(ph[0])} and ${money(ph[1])} of modified income, above which people use the backdoor Roth (ask a tax pro).`,
    "Roth conversion ladder: move some 401(k) or traditional IRA money to a Roth each year after you stop working; each conversion can come out penalty-free after 5 years (it is taxed in the year you convert).",
    "72(t) payments: penalty-free withdrawals from an IRA before 59\u00bd, in fixed amounts you must keep taking for 5 years or until 59\u00bd, whichever is longer.",
    `HSA: ${money(r.hsa_limit_self_only)} a year self-only (${money(r.hsa_limit_family)} family) in ${r.year}. Paying medical bills out of pocket now and keeping the receipts lets you reimburse yourself tax-free years later.`,
    "The rule of 55 does not help at 48: it only applies when you leave a job in or after the year you turn 55.",
    "Living abroad: US citizens still owe US tax on 401(k), IRA and investment income (the foreign earned income exclusion covers wages only); Medicare does not cover care abroad, and some brokerages limit accounts for people who live outside the US.",
  ];
  return `<details class="rpg-home-ef-pick"><summary>Reaching the money before 59\u00bd (rules of thumb)</summary><ul class="rpg-home-limits">${items.map(i=>`<li>${esc(i)}</li>`).join("")}</ul></details>`;
}
function retirementForm(cfg){
  const c=cfg||{},accts=retirementAccounts();
  const v=x=>x===null||x===undefined?"":esc(x);
  const f=(k,label,val,step="any",ph="")=>`<label>${esc(label)}<input type="number" step="${step}" data-ret="${k}" value="${v(val)}"${ph?` placeholder="${esc(ph)}"`:""}></label>`;
  const p100=x=>x===null||x===undefined?null:Math.round(x*1000)/10;
  const age=c.age!=null?Math.floor(c.age+((Number(nowMonth().slice(0,4))*12+Number(nowMonth().slice(5,7)))-(Number(String(c.age_as_of).slice(0,4))*12+Number(String(c.age_as_of).slice(5,7))))/12):null;
  const jobs=(c.jobs&&c.jobs.length?c.jobs:[{},{}]).map((j,i)=>`<fieldset class="rpg-home-mix" data-ret-job="${i}"><legend>${esc(j.label||`Job ${i+1}`)}</legend><label>Name<input type="text" data-job="label" value="${v(j.label)}" maxlength="60"></label><label>401(k) account<select data-job="account_id"><option value="">\u2014</option>${accts.map(a=>`<option value="${esc(a.account_id)}"${a.account_id===j.account_id?" selected":""}>${esc(a.name||a.account_label)}</option>`).join("")}</select></label><label>Yearly pay<input type="number" step="100" data-job="salary" value="${v(j.salary)}"></label><label>Bonus a year<input type="number" step="100" data-job="bonus" value="${v(j.bonus)}"></label><label>Match %<input type="number" step="0.5" data-job="match_pct" value="${v(p100(j.match_pct))}"></label><label>Your % (blank = from deposits)<input type="number" step="0.5" data-job="you_pct" value="${v(p100(j.you_pct))}"></label></fieldset>`).join("");
  return `<details class="rpg-home-ef-pick"${cfg?"":" open"}><summary>Your retirement inputs</summary><form class="rpg-board-filters rpg-home-grid" data-ret-form>${f("age","Your age today",age,"1")}${f("retire_age","Retire at age",c.retire_age,"1")}${f("spending_year","Spending a year (today's $)",c.spending_year,"500",S.ret?.spending_default_year?`blank = ${Math.round(S.ret.spending_default_year)} (12\u00d7 this month's bills)`:"blank = 12\u00d7 this month's bills")}${f("spending_abroad_year","Spending a year abroad (optional)",c.spending_abroad_year,"500")}${f("withdrawal_rate","Draw rate %",p100(c.withdrawal_rate??0.035),"0.1")}${f("inflation","Inflation %",p100(c.inflation??0.025),"0.1")}${f("withdrawal_tax","Tax on retirement withdrawals %",p100(c.withdrawal_tax??0.10),"1")}${f("after_plan_monthly_investing","Invested a month after the plan ends",c.after_plan_monthly_investing,"50",S.ret?.after_plan_default!=null?`blank = ${Math.round(S.ret.after_plan_default)}`:"")}${f("social_security_monthly","Social Security a month (ssa.gov, optional)",c.social_security_monthly,"50")}${f("social_security_age","Claim it at age",c.social_security_age??67,"1")}<label class="rpg-check"><input type="checkbox" data-ret="sell_home_at_retirement"${c.sell_home_at_retirement?" checked":""}> Sell the home when I retire</label>${jobs}<div class="rpg-home-actions"><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-ret-try>Try these</button><button type="button" class="rpg-btn rpg-action" data-ret-keep>Save into the plan</button></div></form></details>`;
}
function readRetirement(form){
  const out={age_as_of:nowMonth()},n=el=>el.value===""?null:Number(el.value);
  form.querySelectorAll("[data-ret]").forEach(el=>{
    const k=el.dataset.ret;
    if(k==="sell_home_at_retirement"){out[k]=el.checked;return}
    const v=n(el);
    out[k]=["withdrawal_rate","inflation","withdrawal_tax"].includes(k)&&v!==null?v/100:v;
  });
  out.jobs=[...form.querySelectorAll("[data-ret-job]")].map(fs=>{const j={};fs.querySelectorAll("[data-job]").forEach(el=>{const k=el.dataset.job;if(k==="label"||k==="account_id"){j[k]=el.value;return}const v=n(el);j[k]=["match_pct","you_pct"].includes(k)&&v!==null?v/100:v});return j}).filter(j=>j.salary);
  return out;
}


/* ---------------- goals, side by side ---------------- */
function goalsSection(){
  const goals=S.plan.settings.goals||[],p=S.proj,r=S.ret&&S.ret.configured?S.ret:null,ret=S.plan.settings.retirement;
  const open=goals.filter(g=>g.status==="open"),done=goals.filter(g=>g.status==="done");
  const chanceOf=g=>{const a=(p?.goals_before_target||[]).find(x=>x.id===g.id);if(a)return a.chance;const b=(r?.goals||[]).find(x=>x.id===g.id);return b?b.chance:null};
  const cell=c=>c===null||c===undefined?"\u2014":`${Math.round(c*100)}%`;
  const hi=p?.house?.chances?.find(c=>c.price===p.house.price_high),hiFree=p?.house?.chances_without_goals?.find(c=>c.price===p.house.price_high);
  const rows=[];
  if(S.plan.settings.home)rows.push(`<tr><th scope="row">The house</th><td>${esc(monthLabel(S.plan.settings.home.closing_month))}</td><td class="num">${money(S.plan.settings.home.price)}</td><td class="num">Bought</td><td></td></tr>`);else
  rows.push(`<tr><th scope="row">The house</th><td>${esc(monthLabel(S.plan.settings.target_month))}</td><td class="num">${esc(`${compact(S.plan.settings.home_price_low)}\u2013${compact(S.plan.settings.home_price_high)} home`)}</td><td class="num">${hi?esc(`${cell(hi.chance)} at ${compact(p.house.price_high)}`):"\u2014"}</td><td><span class="rpg-muted">set under The house and the plan</span></td></tr>`);
  for(const g of open)rows.push(`<tr><th scope="row">${esc(g.name)}</th><td>${esc(monthLabel(g.month))}</td><td class="num">${money(g.amount)}</td><td class="num">${cell(chanceOf(g))}</td><td><button type="button" class="rpg-btn rpg-link" data-goal-done="${esc(g.id)}">Done</button> <button type="button" class="rpg-btn rpg-link" data-goal-remove="${esc(g.id)}">Remove</button></td></tr>`);
  if(ret)rows.push(`<tr><th scope="row">Retire at ${esc(ret.retire_age)}</th><td>${r?esc(monthLabel(r.retire_month)):"\u2014"}</td><td class="num">${r?esc(`${money(r.spending_year)} a year`):"\u2014"}</td><td class="num">${r?esc(`${cell(r.chance)} last to 95`):"\u2026"}</td><td><span class="rpg-muted">set under the road to early retirement</span></td></tr>`);
  const effects=[];
  if(hi&&hiFree&&hiFree.chance!==hi.chance)effects.push(`the house at ${compact(p.house.price_high)} from ${cell(hiFree.chance)} to ${cell(hi.chance)}`);
  if(r&&r.chance_without_goals!==null&&r.chance_without_goals!==undefined&&r.chance_without_goals!==r.chance)effects.push(`retiring at ${r.retire_age} from ${cell(r.chance_without_goals)} to ${cell(r.chance)}`);
  const effect=!open.length?"Add a goal to see what it costs the house and retirement.":effects.length?`Together, your other goals move ${effects.join(" and ")}.`:"Your other goals don't change the house or retirement chances.";
  const finished=done.length?`<p class="rpg-vault-why">${esc(`Finished: ${done.map(g=>`${g.name} (${monthLabel(g.done_month)}, ${money(g.done_amount)})`).join(" \u00b7 ")}`)}</p>`:"";
  const form=`<form class="rpg-board-filters rpg-home-grid rpg-home-goal-form" data-goal-add><label>Goal<input type="text" data-goal="name" maxlength="80" placeholder="e.g. replace the car"></label><label>Amount (today's $)<input type="number" step="100" min="1" data-goal="amount"></label><label>When<input type="month" data-goal="month" value="${esc(addMonths(nowMonth(),12))}"></label><div class="rpg-home-actions"><button type="submit" class="rpg-btn rpg-action">Add the goal</button></div></form>`;
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-goals-h"><div class="rpg-section-head"><h2 id="rpg-home-goals-h" class="rpg-stone-title">Your goals</h2><span class="rpg-crumb-note">Simulated together, in date order \u00b7 paid from the bank above the safety fund, then investments; never retirement</span></div><p class="rpg-guild-counsel">${esc(effect)}</p><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Goal</th><th>When</th><th class="num">Amount</th><th class="num">Chance it is covered</th><th></th></tr></thead><tbody>${rows.join("")}</tbody></table></div>${finished}${form}<p class="rpg-crumb-note">${esc("A goal the money cannot cover in its month is counted as postponed in that market, not paid. Mark a goal done when you pay for it; it stays here with its date and amount.")}</p></section>`;
}


/* ---------------- owner mode: the home once it is bought ---------------- */
const HOME_MARKETS=[["Wichita","Wichita"],["DFW Composite","Dallas\u2013Fort Worth"]];
function marketNow(name){const m=(S.housing?.markets||[]).find(x=>x.market===name);const r=S.housing?.package?.rates_outlook;const w=r?.mortgage_30yr_latest_weekly?.rate??r?.mortgage_30yr_month_avg??m?.mortgage_30yr;return {hpi:num(m?.hpi),rate:num(w)===null?null:num(w)/100,as_of:m?.market_state_as_of}}
function owned(){return S.homeTried||S.plan?.settings?.home||null}
function refreshHome(force){
  if(!S.doc?.available)return;
  const h=owned();if(!h){S.homeDoc=null;return}
  const now=marketNow(h.market);
  const body={as_of_month:nowMonth(),hpi_now:now.hpi||undefined,rate_now:now.rate||undefined,home:S.homeTried||undefined};
  const k=JSON.stringify([S.doc.version?.version_id,body]);
  if(!force&&k===S.homeKey)return;
  S.homeKey=k;S.homeErr=null;
  post("/v1/household-plan/home",body).then(d=>{if(S.homeKey!==k)return;S.homeDoc=d.owned?d:null;render();if(!d.preview)refreshRetirement(true)}).catch(e=>{if(S.homeKey!==k)return;S.homeErr=e.message;render()});
}
function ownerSection(){
  const d=S.homeDoc,h=owned();
  if(S.homeErr)return `<section class="rpg-stone rpg-road"><p class="rpg-parch-note">${esc(`The home could not be worked out: ${S.homeErr}`)}</p>${homeForms(h)}</section>`;
  if(!d)return `<section class="rpg-stone rpg-road"><p class="rpg-parch-note">Working out the home\u2026</p></section>`;
  const tile=(label,value,sub)=>`<div class="rpg-parch rpg-tile"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${value}</div>${sub?`<div class="rpg-stat-sub">${esc(sub)}</div>`:""}</div>`;
  const pay=d.payment,src={PRICE_X_HPI:"price moved with the market index",APPRAISAL_X_HPI:"appraisal moved with the market index",APPRAISAL:"your appraisal",PRICE:"the price (no index yet)"}[d.value_source]||"";
  const tiles=`<div class="rpg-tiles rpg-home-tiles">${tile("Home value",money(d.value),`${src} \u00b7 ${d.gain_since_closing<0?"\u2212":"+"}${money(Math.abs(d.gain_since_closing))} since closing`)}${tile("Loan balance",money(d.loan_balance),`paid off ${monthLabel(d.payoff_month)} on schedule \u00b7 ${money(d.interest_left)} interest still to pay`)}${tile("Equity",money(d.equity),`${pctText(d.equity_share)} of the home \u00b7 in net worth, never spending money`)}${tile("Monthly payment",money(pay.total,2),`${money(pay.principal_and_interest,2)} loan${pay.pmi?` + ${money(pay.pmi,2)} PMI`:""}${pay.escrow?` + ${money(pay.escrow,2)} escrow`:""}${pay.hoa?` + ${money(pay.hoa,2)} HOA`:""}`)}</div>`;
  const checks=[];
  if(d.pmi)checks.push(`PMI (${money(d.pmi.monthly,2)} a month): you can ask for it to come off ${d.pmi.request_month?`in ${monthLabel(d.pmi.request_month)}`:"once the loan reaches 80% of the price"}, when the loan reaches 80% of the original price, and it ends on its own ${d.pmi.automatic_month?`by ${monthLabel(d.pmi.automatic_month)}`:"at 78%"}. Today the loan is ${pctText(d.pmi.ltv_today_value)} of the home's current value; lenders sometimes drop PMI early on a new appraisal, under their own rules.`);
  if(d.refinance){const r=d.refinance;checks.push(r.monthly_saving>0?`Refinancing at today's ${pctText(r.rate_now,2)} (yours is ${pctText(h.rate,2)}) would cost about ${money(r.costs)} and save about ${money(r.monthly_saving)} a month, paying back in ${r.break_even_months} months. ${r.worth_a_look?`That is before ${r.keep_until?`you plan to sell (${monthLabel(r.keep_until)})`:"5 years"}, so it is worth asking a lender for a quote.`:`That is not before ${r.keep_until?`you plan to sell (${monthLabel(r.keep_until)})`:"5 years"}, so not yet.`}`:`Today's rate (${pctText(r.rate_now,2)}) is not below yours (${pctText(h.rate,2)}), so refinancing would not save anything.`)}
  const x=d.extra_principal;
  checks.push(`${money(x.monthly)} more principal a month saves about ${money(x.interest_saved)} of interest and ends the loan ${x.months_sooner} months sooner: a guaranteed ${pctText(x.guaranteed_return,2)} return. Investing it instead has a typical 8% a year for stocks with big swings, and money you can reach before 59\u00bd helps the early-retirement bridge more.`);
  checks.push(`Set aside ${money(d.maintenance_month[0])}\u2013${money(d.maintenance_month[1])} a month for upkeep (1\u20132% of the home's value a year).`);
  checks.push(`Your plan's bills should now carry the ${money(pay.total,2)} payment in place of rent (edit any month in the ledger and apply it to every later month).`);
  const head=`<div class="rpg-section-head"><h2 id="rpg-home-own-h" class="rpg-stone-title">The home \u00b7 bought ${esc(monthLabel(h.closing_month))}</h2><span class="rpg-crumb-note">${esc(d.preview?"Preview \u00b7 not saved":`${HOME_MARKETS.find(m=>m[0]===h.market)?.[1]||h.market} price index`)}</span></div>`;
  const previewBar=d.preview?`<div class="rpg-home-dirty" role="status"><span>This is a preview of owner mode with the figures you entered.</span><button type="button" class="rpg-btn rpg-action" data-home-own-save>Save the purchase</button><button type="button" class="rpg-btn rpg-link" data-home-own-cancel>Leave the preview</button></div>`:"";
  return `<section class="rpg-stone rpg-guild-hero rpg-home-hero rpg-home-owner" aria-labelledby="rpg-home-own-h">${head}${previewBar}${tiles}<ul class="rpg-home-limits rpg-home-checks">${checks.map(c=>`<li>${esc(c)}</li>`).join("")}</ul>${d.preview?"":homeForms(h)}<ul class="rpg-home-limits">${(d.limitations||[]).map(l=>`<li>${esc(l)}</li>`).join("")}</ul></section>`;
}
function homeForms(h){
  const v=x=>x===null||x===undefined?"":esc(x);
  return `<details class="rpg-home-ef-pick"><summary>Record a statement, extra principal or an appraisal</summary><form class="rpg-board-filters rpg-home-grid" data-home-own-add><label>What<select data-own="kind"><option value="statements">Loan balance from a statement</option><option value="extra_payments">Extra principal paid</option><option value="appraisals">Appraisal</option></select></label><label>Month<input type="month" data-own="month" value="${esc(nowMonth())}"></label><label>Amount<input type="number" step="0.01" min="0" data-own="amount"></label><div class="rpg-home-actions"><button type="submit" class="rpg-btn rpg-action">Save</button></div></form><form class="rpg-board-filters rpg-home-grid" data-home-own-costs><label>PMI a month<input type="number" step="0.01" min="0" data-own="pmi_monthly" value="${v(h.pmi_monthly)}"></label><label>Escrow a month (tax and insurance)<input type="number" step="0.01" min="0" data-own="escrow_monthly" value="${v(h.escrow_monthly)}"></label><label>HOA a month<input type="number" step="0.01" min="0" data-own="hoa_monthly" value="${v(h.hoa_monthly)}"></label><div class="rpg-home-actions"><button type="submit" class="rpg-btn rpg-action rpg-action-quiet">Update the monthly costs</button></div></form><p class="rpg-crumb-note">${esc(`${h.statements.length} statement${h.statements.length===1?"":"s"}, ${h.extra_payments.length} extra payment${h.extra_payments.length===1?"":"s"} and ${h.appraisals.length} appraisal${h.appraisals.length===1?"":"s"} recorded.`)}</p><button type="button" class="rpg-btn rpg-link" data-home-own-undo>Undo the purchase record</button></details>`;
}
function purchaseForm(){
  const s=S.plan.settings,mid=Math.round((s.home_price_low+s.home_price_high)/2);
  const f=(k,label,val,step="any")=>`<label>${esc(label)}<input type="number" step="${step}" min="0" data-buy="${k}" value="${val===null||val===undefined?"":esc(val)}"></label>`;
  return `<details class="rpg-home-ef-pick rpg-home-buy"><summary>Bought the house? Record it at closing (or preview owner mode with sample figures)</summary><form class="rpg-board-filters rpg-home-grid" data-home-buy><label>Market<select data-buy="market">${HOME_MARKETS.map(([k,l])=>`<option value="${esc(k)}">${esc(l)}</option>`).join("")}</select></label>${f("price","Price",mid,"1000")}<label>Closing month<input type="month" data-buy="closing_month" value="${esc(s.target_month)}"></label>${f("down_payment","Down payment",Math.round(mid*s.down_payment_pct),"100")}${f("closing_costs","Closing costs",Math.round(mid*s.closing_cost_pct),"100")}${f("loan_amount","Loan amount",Math.round(mid*(1-s.down_payment_pct)),"100")}${f("rate","Rate %",Math.round(s.mortgage_rate*10000)/100,"0.01")}${f("term_years","Years",s.loan_years,"1")}${f("pmi_monthly","PMI a month",0,"1")}${f("escrow_monthly","Escrow a month",0,"1")}${f("hoa_monthly","HOA a month",0,"1")}<div class="rpg-home-actions"><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-home-buy-try>Preview owner mode</button><button type="button" class="rpg-btn rpg-action" data-home-buy-save>Save the purchase</button></div></form></details>`;
}
function readPurchase(form){
  const out={};form.querySelectorAll("[data-buy]").forEach(el=>{const k=el.dataset.buy;out[k]=k==="market"||k==="closing_month"?el.value:el.value===""?null:Number(el.value)});
  if(out.rate!==null)out.rate=out.rate/100;
  out.hpi_at_closing=marketNow(out.market).hpi;out.statements=[];out.extra_payments=[];out.appraisals=[];
  return out;
}

/* ---------------- a plan that keeps going ---------------- */
const HORIZON=36;
const addMonths=(m,n)=>{const t=Number(m.slice(0,4))*12+Number(m.slice(5,7))-1+n;return `${Math.floor(t/12)}-${String(t%12+1).padStart(2,"0")}`};
function extendPlan(plan,through){
  const last=plan.months[plan.months.length-1];let m=last.month;const added=[];
  while(m<through){m=addMonths(m,1);added.push({month:m,income:{...last.income},expenses:{...last.expenses},investment_contribution:last.investment_contribution,house_fund_contribution:last.house_fund_contribution,retirement_contribution:last.retirement_contribution,bank_balance:null,retirement_balance:null,investment_balance:null,house_fund_balance:null,home_equity:null,note:`Copied from ${monthLabel(last.month)}; edit to fit.`,bank_check:null})}
  plan.months.push(...added);return added.length;
}
function horizonNote(){
  const end=S.plan.months[S.plan.months.length-1].month,want=addMonths(nowMonth(),HORIZON);
  if(end>=want)return "";
  return `<div class="rpg-home-dirty rpg-home-horizon" role="status"><span>${esc(`Your plan runs to ${monthLabel(end)}. Keep it ${HORIZON} months ahead so the Homestead stays useful after the house: add months through ${monthLabel(want)}, copied from ${monthLabel(end)} for you to edit.`)}</span><button type="button" class="rpg-btn rpg-action" data-home-extend="${esc(want)}">Add the months</button></div>`;
}

/* ---------------- pieces ---------------- */
function crumbs(note){
  const tabs=R().realmTabs?R().realmTabs("homestead"):"";
  return `<header class="rpg-stone rpg-crumbs"><nav aria-label="Breadcrumb"><button type="button" class="rpg-btn rpg-crumb" data-rpg-page="home">The Hall</button><span aria-hidden="true">\u203a</span><span class="rpg-crumb-here">The Homestead</span></nav><span class="rpg-crumb-note">${esc(note)}</span></header>${tabs}`;
}
function message(){if(!S.msg)return "";return `<p class="rpg-home-msg ${S.msg[0]==="bad"?"rpg-down":"rpg-up"}" role="status">${esc(S.msg[1])}</p>`}

function goal(p){
  const h=p.house,t=p.target;
  const low=h.chances.find(c=>c.price===h.price_low),high=h.chances.find(c=>c.price===h.price_high);
  const chance=c=>c?`${Math.round(c.chance*100)}%`:"\u2014";
  const cap=h.capacity||[];
  const hi=cap.find(c=>c.price===h.price_high)||cap[cap.length-1];
  const counsel=low&&high?`By ${monthLabel(p.target_month)}, a ${pctText(h.down_payment_pct)} down payment on a ${compact(h.price_low)}\u2013${compact(h.price_high)} home, closing costs and a ${money(p.safety_fund)} safety fund need ${money(h.need_low)}\u2013${money(h.need_high)} in cash. Your plan gets there in ${chance(high)} of ${p.paths.toLocaleString("en-US")} simulated markets (${chance(low)} at ${compact(h.price_low)}).`:"";
  const grownNote=num(h.home_price_growth)?` Prices are grown ${pctText(h.home_price_growth,1)} a year to ${compact(h.price_low_at_target)}\u2013${compact(h.price_high_at_target)} by then.`:" Prices are today's; the housing forecast can grow them.";
  const room=hi?` Typical house money is ${money(t.house_usable.p50)} (bad case ${money(t.house_usable.p10)}), so on a ${compact(hi.price)} home you could put down about ${pctText(hi.down_pct_p50)} instead of ${pctText(h.down_payment_pct)}: roughly ${money(hi.payment_p50)} a month instead of ${money(hi.twenty_pct_payment)} at ${pctText(h.mortgage_rate,1)}.`:"";
  return `<section class="rpg-stone rpg-guild-hero rpg-home-hero"><div><div class="rpg-parch-kicker">The road to the Homestead</div><p class="rpg-guild-counsel">${esc(counsel)}</p><p class="rpg-vault-why">${esc(grownNote+room)}</p></div><div class="rpg-crumb-stats rpg-home-stats"><span>Plan, ${esc(monthLabel(p.target_month))} <strong class="num">${money(t.plan_net_worth)}</strong></span><span>Typical <strong class="num">${money(t.net_worth.p50)}</strong></span><span>Range <strong class="num">${compact(t.net_worth.p10)}\u2013${compact(t.net_worth.p90)}</strong></span></div></section>`;
}

function niceStep(range,count){const raw=range/count;const mag=10**Math.floor(Math.log10(raw||1));const n=raw/mag;return (n<1.5?1:n<3?2:n<7?5:10)*mag}
function fan(p){
  const which=S.chart==="worth"?"net_worth":"house_usable",planKey=S.chart==="worth"?"plan_net_worth":"plan_house_usable";
  const rows=p.series;if(rows.length<2)return "";
  const needs=S.chart==="worth"?[]:[[p.house.need_high,`${compact(p.house.price_high)} home`],[p.house.need_low,`${compact(p.house.price_low)} home`]];
  const top0=Math.max(...rows.map(r=>Math.max(r[which].p90,r[planKey])),...needs.map(n=>n[0]))*1.08;
  const step=niceStep(top0,6),top=Math.ceil(top0/step)*step;
  const X0=78,X1=960,Y0=18,Y1=300,x=i=>X0+(X1-X0)*i/(rows.length-1),y=v=>Y1-(Y1-Y0)*Math.max(0,v)/top;
  const line=f=>rows.map((r,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(f(r)).toFixed(1)}`).join(" ");
  const band=(lo,hi)=>`${line(r=>r[which][hi])} ${rows.map((r,i)=>[i,r]).reverse().map(([i,r])=>`L${x(i).toFixed(1)},${y(r[which][lo]).toFixed(1)}`).join(" ")} Z`;
  const grid=[],labels=[];
  for(let v=0;v<=top+1;v+=step){grid.push(`M${X0} ${y(v).toFixed(1)} H${X1}`);labels.push(`<text x="${X0-8}" y="${(y(v)+5).toFixed(1)}" text-anchor="end">${esc(compact(v))}</text>`)}
  const ticks=[...new Set([0,Math.round((rows.length-1)/3),Math.round(2*(rows.length-1)/3),rows.length-1])];
  const xl=ticks.map(i=>`<text x="${x(i).toFixed(0)}" y="324" text-anchor="middle">${esc(monthLabel(rows[i].month))}</text>`).join("");
  const needLines=needs.map(([v,l])=>`<path d="M${X0} ${y(v).toFixed(1)} H${X1}" stroke="#e08a7d" stroke-width="1.5" stroke-dasharray="3 5" fill="none"/><text x="${X0+6}" y="${(y(v)-6).toFixed(1)}" fill="#e08a7d">${esc(`Cash needed, ${l}: ${compact(v)}`)}</text>`).join("");
  const last=rows[rows.length-1];
  const label=S.chart==="worth"?"Net worth":"Money for the house (bank, house fund and investments after MTG selling costs)";
  const toggle=`<div class="rpg-home-toggle" role="group" aria-label="Chart">${[["house","House money"],["worth","Net worth"]].map(([k,l])=>`<button type="button" class="rpg-btn rpg-realm${S.chart===k?" is-active":""}" data-home-chart="${k}" aria-pressed="${S.chart===k}">${l}</button>`).join("")}</div>`;
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-road-h"><div class="rpg-section-head"><h2 id="rpg-home-road-h" class="rpg-stone-title">The road ahead \u00b7 ${esc(monthLabel(rows[0].month))} to ${esc(monthLabel(last.month))}</h2>${toggle}</div><div class="rpg-chart-key"><span><svg width="26" height="10" aria-hidden="true"><rect width="26" height="10" fill="#4d7a3a" fill-opacity=".28"/></svg>8 in 10 markets</span><span><svg width="26" height="10" aria-hidden="true"><rect width="26" height="10" fill="#4d7a3a" fill-opacity=".55"/></svg>Middle half</span><span><svg width="26" height="8" aria-hidden="true"><path d="M0 4 H26" stroke="#f1d78f" stroke-width="3"/></svg>Typical</span><span><svg width="26" height="8" aria-hidden="true"><path d="M0 4 H26" stroke="#9ec0ea" stroke-width="2" stroke-dasharray="6 4"/></svg>Your plan at a steady ${esc(pctText(S.plan?.settings?.plan_investment_return))} a year</span></div><svg viewBox="0 0 1000 336" class="rpg-fluid" role="img" aria-label="${esc(`${label}: typical ${money(last[which].p50)} by ${monthLabel(last.month)}, 8 in 10 markets between ${money(last[which].p10)} and ${money(last[which].p90)}; the plan says ${money(last[planKey])}.`)}"><g stroke="#3a3127" stroke-width="1" fill="none"><path d="${grid.join(" ")}"/></g><path d="${band("p10","p90")}" fill="#4d7a3a" fill-opacity=".28"/><path d="${band("p25","p75")}" fill="#4d7a3a" fill-opacity=".55"/><path d="${line(r=>r[planKey])}" stroke="#9ec0ea" stroke-width="2" stroke-dasharray="6 4" fill="none"/><path d="${line(r=>r[which].p50)}" stroke="#f1d78f" stroke-width="3" fill="none"/>${needLines}<g fill="#b9a98a" font-size="14">${labels.join("")}${xl}</g></svg><p class="rpg-crumb-note">${esc(label)}. Your monthly plan is taken as written; only the markets are simulated.</p></section>`;
}

function targetTiles(p){
  const t=p.target,s=p.target_by_sleeve_median||{};
  const tile=(label,value,sub="")=>`<div class="rpg-parch rpg-tile"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${value}</div>${sub?`<div class="rpg-stat-sub">${esc(sub)}</div>`:""}</div>`;
  const last=roll(S.plan).find(r=>r.month===p.target_month)||{};
  const sleeves=SLEEVES.filter(([k])=>(s[k]||0)>=1).map(([k,l])=>`${l} ${compact(s[k])}`).join(" \u00b7 ");
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-t-h"><div class="rpg-section-head"><h2 id="rpg-home-t-h" class="rpg-stone-title">${esc(monthLabel(p.target_month))}, typical case</h2><span class="rpg-crumb-note">Starting from ${esc(money(p.starting_investments))} invested today${p.starting_investments_source==="LIVE_UIP_HOLDINGS"?" (live UIP holdings)":" (the plan's balance)"}${p.starting_retirement_source==="RETIREMENT_STATEMENTS"?`, with ${esc(money(p.starting_retirement))} in retirement from your statements`:""}, plus ${esc(money(p.investment_contributions_ahead))} still to put in</span></div><div class="rpg-tiles rpg-home-tiles">${tile("Investments",money(t.investments.p50),`plan ${money(last.investment_balance)} \u00b7 ${sleeves}`)}${tile("Bank",money(last.bank_balance),"as your plan has it")}${tile("Retirement",money(s.retirement),`plan ${money(last.retirement_balance)} \u00b7 not counted toward the house`)}${tile(`Chance below the plan's ${compact(t.plan_net_worth)}`,pctText(p.chance_below_plan_net_worth),`investments end below what you put in: ${pctText(p.chance_investments_below_money_put_in)}`)}</div></section>`;
}

function capacity(p){
  const h=p.house;
  const rows=(h.capacity||[]).map(c=>`<tr><th scope="row">${esc(money(c.price))}${num(c.price_at_target)&&c.price_at_target!==c.price?`<small class="rpg-home-grown"> \u2192 ${esc(money(c.price_at_target))} by ${esc(monthLabel(p.target_month))}</small>`:""}</th><td class="num">${esc(money((c.price_at_target||c.price)*h.down_payment_pct))} \u00b7 ${esc(money(c.twenty_pct_payment))}/mo</td><td class="num">${esc(money(c.down_p10))} (${esc(pctText(c.down_pct_p10))}) \u00b7 ${esc(money(c.payment_p10))}/mo</td><td class="num">${esc(money(c.down_p50))} (${esc(pctText(c.down_pct_p50))}) \u00b7 ${esc(money(c.payment_p50))}/mo</td><td class="num">${esc(money(c.down_p90))} (${esc(pctText(c.down_pct_p90))}) \u00b7 ${esc(money(c.payment_p90))}/mo</td></tr>`).join("");
  const all=h.chances.every(c=>c.chance>=0.995),mp=(num(h.home_price_growth)?h.max_price_today_dollars:h.max_price_at_down_payment_pct)||{};
  const sure=all?`<p class="rpg-vault-why rpg-home-sure">${esc(`Every price from ${compact(h.chances[0].price)} to ${compact(h.chances[h.chances.length-1].price)} is covered in ${p.paths.toLocaleString("en-US")} of ${p.paths.toLocaleString("en-US")} simulated markets. Even the bad case pays ${pctText(h.down_payment_pct)} down on a home up to about ${compact(mp.p10||0)}${num(h.home_price_growth)?" in today's prices":""}, so the down payment is not what limits the house: the monthly payment is.`)}</p>`:"";
  const ladder=all?"":h.chances.map(c=>`<tr><th scope="row">${esc(money(c.price))}</th><td class="num">${esc(money(c.cash_needed))}</td><td class="num">${esc(`${Math.round(c.chance*100)}%`)}</td></tr>`).join("");
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-cap-h"><div class="rpg-section-head"><h2 id="rpg-home-cap-h" class="rpg-stone-title">What the down payment could be</h2><span class="rpg-crumb-note">After closing costs and keeping the ${esc(money(p.safety_fund))} safety fund \u00b7 mortgage at ${esc(pctText(h.mortgage_rate,2))} for ${esc(h.loan_years)} years (the plan's assumption, not a quote; principal and interest only; the rate outlook is below)</span></div><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Home price</th><th class="num">${esc(pctText(h.down_payment_pct))} down</th><th class="num">Bad case</th><th class="num">Typical</th><th class="num">Good case</th></tr></thead><tbody>${rows}</tbody></table></div>${sure}${all?"":`<div class="rpg-table-wrap"><table class="rpg-table rpg-home-ladder"><thead><tr><th>Home price</th><th class="num">Cash needed (${esc(pctText(h.down_payment_pct))} down, closing, safety fund)</th><th class="num">Chance your plan has it</th></tr></thead><tbody>${ladder}</tbody></table></div>`}</section>`;
}

function ledger(){
  const rows=roll(S.plan),now=nowMonth();
  const body=rows.map(r=>`<tr class="${r.month===S.pick?"is-picked":""}${r.month===now?" is-now":""}"><th scope="row"><button type="button" class="rpg-btn rpg-fund-pick" data-home-month="${esc(r.month)}" aria-pressed="${r.month===S.pick}"><strong>${esc(monthLabel(r.month))}</strong><span>${r.checked?`bank checked ${esc(dayText(r.checked))}`:r.anchored.length?"actuals entered":r.month<now?"plan only":r.month===now?"this month":""}</span></button></th><td class="num">${money(r.income)}</td><td class="num">${money(r.expenses)}</td><td class="num">${money(r.net)}</td><td class="num">${money(S.plan.months.find(m=>m.month===r.month).investment_contribution)}</td><td class="num${r.anchored.includes("bank_balance")?" rpg-home-actual":r.checked?" rpg-home-checked":""}"${r.checked?` title="Projected from your ${esc(dayText(r.checked))} bank balance"`:""}>${money(r.bank_balance)}</td><td class="num${r.anchored.includes("retirement_balance")?" rpg-home-actual":""}">${money(r.retirement_balance)}</td><td class="num${r.anchored.includes("investment_balance")?" rpg-home-actual":""}">${money(r.investment_balance)}</td><td class="num"><strong>${money(r.net_worth)}</strong></td></tr>`).join("");
  return `<section class="rpg-stone rpg-guild-ledger" aria-labelledby="rpg-home-led-h"><div class="rpg-section-head"><h2 id="rpg-home-led-h" class="rpg-stone-title">The ledger of months</h2><span class="rpg-crumb-note">Pick a month to edit it. Gold figures are actuals you entered; the rest roll forward from them.</span></div>${horizonNote()}${S.dirty?`<div class="rpg-home-dirty" role="status"><span>Unsaved changes to the plan.</span><button type="button" class="rpg-btn rpg-action" data-home-save>Save the plan</button><button type="button" class="rpg-btn rpg-link" data-home-discard>Discard</button></div>`:""}<div class="rpg-table-wrap"><table class="rpg-table rpg-guild-table rpg-home-ledger"><thead><tr><th>Month</th><th class="num">Income</th><th class="num">Bills</th><th class="num">Net</th><th class="num">Invested</th><th class="num">Bank</th><th class="num">Retirement</th><th class="num">Investments</th><th class="num">Net worth</th></tr></thead><tbody>${body}</tbody></table></div><div id="rpg-home-editor">${editor()}</div></section>`;
}

const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`};
const dayText=d=>/^\d{4}-\d{2}-\d{2}$/.test(String(d||""))?`${MONTHS[Number(d.slice(5,7))-1]} ${Number(d.slice(8,10))}`:"\u2014";
function purse(){
  const month=nowMonth(),m=S.plan.months.find(x=>x.month===month);
  if(!m)return "";
  const c=m.bank_check||{},done=new Set(c.done||[]);
  const line=(key,label,amount,sign,verb)=>{const shown=sign<0?Math.abs(num(amount)||0):(num(amount)||0);return `<tr><th scope="row">${esc(label)}</th><td class="num"><input type="number" step="0.01" min="0" inputmode="decimal" aria-label="${esc(label)} amount" data-check-amount="${esc(key)}" data-sign="${sign}" value="${shown?esc(shown):""}"></td><td><label class="rpg-check"><input type="checkbox" data-check-done="${esc(key)}"${done.has(key)?" checked":""} aria-label="${esc(label)} ${esc(verb)}"><span class="rpg-check-verb">${esc(verb)}</span></label></td></tr>`};
  const keep=(k,v)=>(num(v)||0)!==0||done.has(k);
  const ordered=(obj,names)=>(names||Object.keys(obj)).filter(k=>k in obj).map(k=>[k,obj[k]]);
  const inc=ordered(m.income,S.plan.income_lines).filter(([k,v])=>keep(`income:${k}`,v)).map(([k,v])=>line(`income:${k}`,k,v,1,"received")).join("");
  const exp=ordered(m.expenses,S.plan.expense_lines).filter(([k,v])=>keep(`expenses:${k}`,v)).map(([k,v])=>line(`expenses:${k}`,k,v,-1,"paid")).join("");
  const tr=TRANSFERS.filter(([k])=>keep(k,m[k])).map(([k,l])=>line(k,l,m[k],-1,"moved")).join("");
  const has=num(c.balance)!==null;
  return `<section class="rpg-stone rpg-road rpg-home-purse" aria-labelledby="rpg-home-purse-h"><div class="rpg-section-head"><h2 id="rpg-home-purse-h" class="rpg-stone-title">The purse \u00b7 ${esc(monthLabel(month))}</h2><span class="rpg-crumb-note">${has?`Checked ${esc(dayText(c.as_of))}`:"Enter your real bank balance to project the month's end"}</span></div><form class="rpg-home-check" data-home-check="${esc(month)}"><div class="rpg-board-filters rpg-home-grid"><label>Bank balance now<input type="number" step="0.01" inputmode="decimal" data-check-balance value="${has?esc(c.balance):""}" placeholder="What your account shows"></label><label>As of<input type="date" data-check-asof value="${esc(has?c.as_of:today())}" min="${esc(month)}-01" max="${esc(month)}-31"></label></div><p class="rpg-vault-why">Tick what has already come in or gone out this month: your balance already includes those. Change an amount if the real one differs (a smaller car payment, say); it changes the month in the plan too.</p><div class="rpg-table-wrap"><table class="rpg-table rpg-home-check-table"><thead><tr><th>This month</th><th class="num">Amount</th><th>Done?</th></tr></thead><tbody>${inc?`<tr class="rpg-home-check-group"><th colspan="3">Income</th></tr>${inc}`:""}${exp?`<tr class="rpg-home-check-group"><th colspan="3">Bills</th></tr>${exp}`:""}${tr?`<tr class="rpg-home-check-group"><th colspan="3">Savings moved out of the bank</th></tr>${tr}`:""}</tbody></table></div><div class="rpg-home-check-sum" data-check-sum role="status">${purseSum(m,c.balance,c.done)}</div><div class="rpg-home-actions"><button type="submit" class="rpg-btn rpg-action">Save the check-in</button>${has?`<button type="button" class="rpg-btn rpg-link" data-home-check-clear>Clear the check-in</button>`:""}</div></form></section>`;
}
function purseSum(m,balance,done){
  const b=num(balance);
  if(b===null)return `<span class="rpg-muted">Enter the balance to see where the month ends.</span>`;
  const d=new Set(done||[]);let inc=0,out=0;
  for(const [k,v] of Object.entries(m.income||{}))if(!d.has(`income:${k}`))inc+=num(v)||0;
  for(const [k,v] of Object.entries(m.expenses||{}))if(!d.has(`expenses:${k}`))out-=num(v)||0;
  for(const [k] of TRANSFERS)if(!d.has(k))out+=num(m[k])||0;
  return `<span>${money(b,2)} now</span><span class="rpg-up">+ ${money(inc,2)} still coming in</span><span class="rpg-down">\u2212 ${money(out,2)} still going out</span><strong>= ${money(b+inc-out,2)} at the end of ${esc(monthLabel(m.month))}</strong>`;
}
function readCheck(form){
  const month=form.dataset.homeCheck,m=clone(S.plan.months.find(x=>x.month===month));
  form.querySelectorAll("[data-check-amount]").forEach(el=>{
    const k=el.dataset.checkAmount,sign=Number(el.dataset.sign),v=el.value===""?0:Math.abs(Number(el.value))*sign;
    if(k.includes(":")){const [g,l]=k.split(/:(.*)/s);m[g][l]=v}else m[k]=Math.abs(v);
  });
  const done=[...form.querySelectorAll("[data-check-done]:checked")].map(el=>el.dataset.checkDone);
  const raw=form.querySelector("[data-check-balance]").value;
  m.bank_check=raw===""?null:{balance:Number(raw),as_of:form.querySelector("[data-check-asof]").value||today(),done};
  return m;
}
function field(id,label,value,extra=""){return `<label>${esc(label)}<input type="number" step="0.01" data-home-field="${esc(id)}" value="${value===null||value===undefined?"":esc(value)}"${extra}></label>`}
function editor(){
  const m=S.plan.months.find(x=>x.month===S.pick);
  if(!m)return `<p class="rpg-parch-note rpg-home-hint">Pick a month above to change its income, bills or savings, or to enter what your bank and retirement balances really were.</p>`;
  const inc=S.plan.income_lines.map(l=>field(`income:${l}`,l,m.income[l])).join("");
  const exp=S.plan.expense_lines.map(l=>field(`expenses:${l}`,`${l} (negative)`,m.expenses[l])).join("");
  return `<form class="rpg-home-editor" data-home-editor="${esc(m.month)}"><h3 class="rpg-stone-title">${esc(monthLabel(m.month))}</h3><fieldset><legend>Income</legend><div class="rpg-board-filters rpg-home-grid">${inc}</div></fieldset><fieldset><legend>Bills</legend><div class="rpg-board-filters rpg-home-grid">${exp}</div></fieldset><fieldset><legend>Savings</legend><div class="rpg-board-filters rpg-home-grid">${field("investment_contribution","Into investments",m.investment_contribution)}${field("house_fund_contribution","Into a house fund",m.house_fund_contribution)}${field("retirement_contribution","Into retirement",m.retirement_contribution)}</div></fieldset><fieldset><legend>Actual balances at month end (leave blank to roll forward)</legend><div class="rpg-board-filters rpg-home-grid">${field("bank_balance","Bank",m.bank_balance)}${field("retirement_balance","Retirement",m.retirement_balance)}${field("investment_balance","Investments",m.investment_balance)}${field("house_fund_balance","House fund",m.house_fund_balance)}</div>${(()=>{const st=statements();return st?`<p class="rpg-home-note">Your retirement accounts come to ${esc(money(st.value))} today (${st.count} account${st.count===1?"":"s"}, latest balance ${esc(st.latest)}, plus paycheck deposits since). <button type="button" class="rpg-btn rpg-link" data-home-use-statements="${st.value}">Put it in Retirement</button></p>`:""})()}</fieldset><label class="rpg-home-note">Note<input type="text" maxlength="500" data-home-field="note" value="${esc(m.note||"")}"></label><div class="rpg-home-actions"><button type="submit" class="rpg-btn rpg-action" data-home-apply="one">Apply to ${esc(monthLabel(m.month))}</button><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-home-apply="later">Apply income, bills and savings to every later month too</button><button type="button" class="rpg-btn rpg-link" data-home-close>Close</button></div></form>`;
}

const SIGNAL_TONE={"Strong Buy":"verdant","Buy":"verdant","Slight Buy":"verdant","Neutral / Fair Value":"bronze","Slight Wait":"azure","Wait":"crimson","Strong Wait / High Risk":"crimson"};
function badge(label,tone){return `<span class="rpg-badge rpg-badge-${tone}">${esc(label)}</span>`}
function payment(principal,rate,years){const r=rate/12,n=years*12;return r?principal*r/(1-Math.pow(1+r,-n)):principal/n}
const monthsBetween=(a,b)=>(Number(b.slice(0,4))-Number(a.slice(0,4)))*12+Number(b.slice(5,7))-Number(a.slice(5,7));
function sepYear(R0,target){const y=String(target).slice(0,4),v=(R0.fomc_sep_context?.fed_funds_median_by_year||{})[y];return num(v)===null?"":`${Number(v).toFixed(1)}% in ${y} and `}
function ratesSection(p){
  const R0=S.housing?.package?.rates_outlook;
  if(!R0||!(R0.horizons||[]).length)return "";
  const ahead=Math.max(0,monthsBetween(R0.as_of_month,p.target_month));
  const row=R0.horizons.reduce((a,b)=>Math.abs(b.months-ahead)<Math.abs(a.months-ahead)?b:a);
  const t=(R0.test||{})[String(row.months)]||{},rules=t.rules||{};
  const now=R0.mortgage_30yr_latest_weekly||{rate:R0.mortgage_30yr_month_avg,date:null};
  const tile=(label,value,sub="")=>`<div class="rpg-parch rpg-tile"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${value}</div>${sub?`<div class="rpg-stat-sub">${esc(sub)}</div>`:""}</div>`;
  const h=p.house,years=h.loan_years,dp=h.down_payment_pct;
  const pay=price=>["p10","p25","p50","p75","p90"].map(k=>num(row[k])===null?"<td class=\"num\">\u2014</td>":`<td class="num">${money(payment(price*(1-dp),row[k]/100,years))}</td>`).join("");
  const prices=[...new Set([h.price_low_at_target||h.price_low,h.price_high_at_target||h.price_high])];
  const table=`<div class="rpg-table-wrap"><table class="rpg-table rpg-home-rates-table"><thead><tr><th>Home price, ${esc(pctText(dp))} down</th>${["p10","p25","p50","p75","p90"].map((k,i)=>`<th class="num">${["Low (1 in 10)","Lower","Typical","Higher","High (1 in 10)"][i]}<br><small>${num(row[k])===null?"\u2014":`${Number(row[k]).toFixed(2)}%`}</small></th>`).join("")}</tr></thead><tbody>${prices.map(pr=>`<tr><th scope="row">${esc(money(pr))}</th>${pay(pr)}</tr>`).join("")}</tbody></table></div>`;
  const st={TESTED:["TESTED","verdant"],TOO_WIDE:["A LITTLE CAUTIOUS","bronze"],TOO_NARROW:["TOO NARROW","crimson"],TOO_FEW_TESTS:["TOO FEW TESTS","stone"]}[t.status]||["UNTESTED","stone"];
  const nc=num(rules.NO_CHANGE?.mae),cf=num(rules.CURVE_FORWARD?.mae);
  const why=`${nc!==null&&cf!==null?`Since ${String(t.first_origin||"1985").slice(0,4)}, guessing "no change" missed the rate ${row.months} months later by ${nc.toFixed(1)} points on average, and the market's own yield curve missed by ${cf.toFixed(1)}: nobody, the bond market included, has had an edge on where mortgage rates will be in three years. `:""}So the typical figure starts from today's rate, and the range is how far rates actually moved over past ${row.months}-month stretches${num(t.band_coverage_10_90)===null?"":` (${Math.round(num(t.band_coverage_10_90)*100)}% of past outcomes landed inside it)`}. The market's curve today points to about ${num(row.curve_forward)===null?"\u2014":`${Number(row.curve_forward).toFixed(1)}%`}${R0.fomc_sep_context?.fed_funds_longer_run_median?`; the Fed's own projections put its overnight rate near ${sepYear(R0,p.target_month)}${Number(R0.fomc_sep_context.fed_funds_longer_run_median).toFixed(1)}% in the longer run, but mortgages follow the 10-year Treasury (${Number(R0.treasury_10y).toFixed(2)}% now, with a ${Number(R0.spread_3m).toFixed(2)}-point mortgage spread), not that rate`:""}. Owners who locked in 2\u20134% rarely sell at ${Number(now.rate).toFixed(1)}%; if rates fall toward the low end, more of them list, which adds supply and tends to slow price gains.`;
  const using=Math.abs(num(S.tried?.mortgage_rate??S.plan.settings.mortgage_rate)-row.p50/100)<1e-6;
  return `<section class="rpg-stone rpg-road rpg-home-rates" aria-labelledby="rpg-home-rates-h"><div class="rpg-section-head"><h2 id="rpg-home-rates-h" class="rpg-stone-title">Mortgage rates around ${esc(monthLabel(p.target_month))}</h2><span class="rpg-crumb-note">Outlook for ${esc(monthLabel(row.month))}, ${row.months} months ahead</span>${badge(st[0],st[1])}</div><div class="rpg-tiles rpg-home-rate-tiles">${tile("Today",`${Number(now.rate).toFixed(2)}%`,now.date?`30-year fixed, week of ${dayText(now.date)}`:"30-year fixed")}${tile("Typical then",`${Number(row.p50).toFixed(1)}%`,`${row.months} months ahead`)}${tile("Range (1 in 10 each side)",`${Number(row.p10).toFixed(1)}\u2013${Number(row.p90).toFixed(1)}%`,`half the time ${Number(row.p25).toFixed(1)}\u2013${Number(row.p75).toFixed(1)}%`)}${tile("Market's curve",num(row.curve_forward)===null?"\u2014":`${Number(row.curve_forward).toFixed(1)}%`,"implied by Treasury yields")}</div><p class="rpg-home-rates-k">The monthly payment at each rate (principal and interest, ${esc(years)} years)</p>${table}<p class="rpg-item-note rpg-home-rates-why">${esc(why)}</p><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-home-use-rate="${esc(row.p50/100)}" ${using?"disabled":""}>${using?"The plan uses the typical rate":`Use the typical ${Number(row.p50).toFixed(1)}% for the plan's payment`}</button>${ahead>row.months+3?`<p class="rpg-footnote">${esc(`Your target is ${ahead} months away; the outlook reaches ${row.months} months, so this is its furthest horizon.`)}</p>`:""}</section>`;
}
function calText(cal){
  if(!cal||!cal.status)return "Calibration: \u2014.";
  if(cal.in_sample!==false)return `Calibration: ${cal.status==="PASS"?"higher scores were followed by better growth in the past":"higher scores were not followed by better growth in the past"} (${cal.status}, measured in-sample).`;
  if(cal.status==="PASS")return `Timing test, out of sample over ${cal.quarters} quarters: PASS. Higher scores were followed by faster price growth (rank correlation ${Number(cal.rank_correlation).toFixed(2)}).`;
  const hi=num(cal.mean_growth_neutral_or_better),lo=num(cal.mean_growth_below_neutral);
  return `Timing test, out of sample over ${cal.quarters} quarters: FAIL. Higher scores were not followed by faster price growth (rank correlation ${Number(cal.rank_correlation).toFixed(2)})${hi!==null&&lo!==null?`; after fair-value-or-better readings prices grew ${pctText(hi,1)} over the next year on average, against ${pctText(lo,1)} after the others`:""}.`;
}
function housingSection(){
  const H=S.housing;
  if(!H)return "";
  if(!H.available)return `<section class="rpg-stone rpg-road rpg-home-housing" aria-labelledby="rpg-home-hm-h"><div class="rpg-section-head"><h2 id="rpg-home-hm-h" class="rpg-stone-title">The housing market</h2></div><p class="rpg-vault-why">${esc("Wichita and Dallas\u2013Fort Worth appear here once the Housing Intelligence Platform's weekly package publishes.")}</p></section>`;
  const pkg=H.package||{};
  const v10=(pkg.model_version||"V10")==="V10";
  const cards=(H.markets||[]).slice().sort((a,b)=>(a.market_rank||9)-(b.market_rank||9)).map(m=>{
    const cal=m.calibration||{},bw=m.best_window||{},tr=m.trigger||{};
    const behind=num(m.months_behind_latest_input);
    const stale=behind!==null&&behind>6;
    const g=num(m.predicted_12m_growth);
    const realized=num(m.realized_growth_for_that_period);
    const using=num(S.plan?.settings?.home_price_growth)!==null&&Math.abs(num(S.tried?.home_price_growth??S.plan.settings.home_price_growth)-g)<1e-6;
    return `<article class="rpg-parch rpg-home-market"><div class="rpg-section-head"><h3 class="rpg-parch-title">${esc(m.market.replace(" Composite",""))}${m.market_rank?` \u00b7 #${esc(m.market_rank)}`:""}</h3>${badge(m.signal,SIGNAL_TONE[m.signal]||"stone")}</div><div class="rpg-item-stats"><div><div class="rpg-stat-label">Entry score</div><div class="rpg-stat-value">${esc(Number(m.entry_score).toFixed(1))} / 100</div></div><div><div class="rpg-stat-label">Next 12 months</div><div class="rpg-stat-value">${pctText(g,1)}</div><div class="rpg-stat-sub">${esc(`${v10?"walk-forward":"tested"} error \u00b1${pctText(m.walk_forward_mae,1)}${v10?"":`, as of ${monthLabel(String(m.market_state_as_of).slice(0,7))}`}`)}</div></div>${bw.months?`<div><div class="rpg-stat-label">Best window</div><div class="rpg-stat-value">${esc(bw.months)} months</div><div class="rpg-stat-sub">${Math.round(num(bw.prob_neutral_or_better)*100)}% chance of fair value or better</div></div>`:`<div><div class="rpg-stat-label">Best window</div><div class="rpg-stat-value">Not given</div><div class="rpg-stat-sub">no buy window is projected until the entry score passes its timing test</div></div>`}</div>${stale?`<p class="rpg-item-note rpg-home-stale">${esc(v10?`This describes ${monthLabel(String(m.market_state_as_of).slice(0,7))}, ${behind} months behind the newest data: V10 scores the last quarter whose next 12 months are already known${realized!==null?` (that period actually grew ${pctText(realized,1)})`:""}.`:`This describes ${monthLabel(String(m.market_state_as_of).slice(0,7))}, ${behind} months behind the newest data.`)}</p>`:""}<p class="rpg-item-note">${esc(`${calText(cal)} ${tr.plain_english||""}`)}</p><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-home-use-growth="${esc(g)}" ${using?"disabled":""}>${using?"Used for the house price":`Grow the house price ${pctText(g,1)} a year`}</button></article>`}).join("");
  return `<section class="rpg-stone rpg-road rpg-home-housing" aria-labelledby="rpg-home-hm-h"><div class="rpg-section-head"><h2 id="rpg-home-hm-h" class="rpg-stone-title">The housing market</h2><span class="rpg-crumb-note">${esc(`Housing Intelligence Platform ${pkg.model_version||""} \u00b7 provisional \u00b7 data through ${pkg.latest_input_observation?monthLabel(String(pkg.latest_input_observation).slice(0,7)):"\u2014"}`)}</span></div><div class="rpg-home-markets">${cards}</div><p class="rpg-footnote">${esc(v10?"Scores rank each market against its own history; the 12-month forecast's walk-forward error is optimistic in V10 and calibration is in-sample. Research, not advice.":"Each quarter's score ranks it against that market's history up to then. The 12-month forecast's error comes from a walk-forward test that trains only on what was known at the time. The Entry Score failed its out-of-sample timing test, so read the signal as a description of buying conditions (prices, supply, rates, affordability), not as a forecast of when prices will rise. Research, not advice.")}</p></section>`;
}
function settingsForm(){
  const s=S.plan.settings,mix=s.contribution_mix||{};
  const f=(k,label,v,step="any",extra="")=>`<label>${esc(label)}<input type="number" step="${step}" data-home-set="${k}" value="${v===null||v===undefined?"":esc(v)}"${extra}></label>`;
  return `<section class="rpg-stone rpg-guild-ledger" aria-labelledby="rpg-home-set-h"><div class="rpg-section-head"><h2 id="rpg-home-set-h" class="rpg-stone-title">The house and the plan</h2><span class="rpg-crumb-note">Try changes to see the ranges move, then save them into the plan.</span></div><form class="rpg-board-filters rpg-home-grid" data-home-settings><label>Target month<input type="month" data-home-set="target_month" value="${esc(s.target_month)}"></label>${f("home_price_low","Home price, low",s.home_price_low,"1000")}${f("home_price_high","Home price, high",s.home_price_high,"1000")}${f("home_price_growth","Home-price growth % a year",Math.round((s.home_price_growth||0)*1000)/10,"0.1")}${f("down_payment_pct","Down payment %",Math.round(s.down_payment_pct*1000)/10,"0.5")}${f("closing_cost_pct","Closing costs %",Math.round(s.closing_cost_pct*1000)/10,"0.5")}${f("safety_fund","Safety fund ($, blank = months)",s.safety_fund,"100")}${f("safety_fund_months","Emergency / safety fund (months of essential bills)",s.safety_fund_months,"1")}${f("mortgage_rate","Mortgage rate %",Math.round(s.mortgage_rate*10000)/100,"0.05")}${f("loan_years","Loan years",s.loan_years,"1")}${f("plan_investment_return","Plan's steady return %",Math.round(s.plan_investment_return*1000)/10,"0.5")}<fieldset class="rpg-home-mix"><legend>Where new investment money goes (%)</legend>${SLEEVES.map(([k,l])=>f(`mix:${k}`,l,Math.round((mix[k]||0)*1000)/10,"5")).join("")}</fieldset><label class="rpg-check"><input type="checkbox" data-home-set="house_counts_retirement"${s.house_counts_retirement?" checked":""}> Count retirement toward the house</label><div class="rpg-home-actions"><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-home-try>Try these</button><button type="button" class="rpg-btn rpg-action" data-home-keep>Save into the plan</button></div></form></section>`;
}
function readSettings(root){
  const out={},mix={};
  root.querySelectorAll("[data-home-set]").forEach(el=>{
    const k=el.dataset.homeSet;
    if(k==="house_counts_retirement"){out[k]=el.checked;return}
    if(k==="target_month"){out[k]=el.value;return}
    const v=el.value===""?null:Number(el.value);
    if(k.startsWith("mix:")){if(v)mix[k.slice(4)]=v/100;return}
    out[k]=["down_payment_pct","closing_cost_pct","mortgage_rate","plan_investment_return","home_price_growth"].includes(k)&&v!==null?v/100:v;
  });
  out.contribution_mix=mix;
  return out;
}

function importPanel(){
  const pv=S.preview;
  const summary=pv?`<div class="rpg-parch rpg-home-preview"><div class="rpg-parch-kicker">Read from the workbook</div><p class="rpg-item-note">${esc(`${pv.plan.months.length} months (${monthLabel(pv.plan.months[0].month)} to ${monthLabel(pv.plan.months[pv.plan.months.length-1].month)}), ${pv.plan.income_lines.length} income lines and ${pv.plan.expense_lines.length} bills. The UIP's roll-forward gives ${money(pv.source.reproduced_end_net_worth,2)} in ${monthLabel(pv.source.workbook_end_month)}; the workbook says ${money(pv.source.workbook_end_net_worth,2)} (largest monthly difference ${money(pv.source.largest_monthly_difference,2)}).`)}</p><p class="rpg-item-note">${esc(S.doc?.available?"Saving replaces the current plan with this one. Earlier versions are kept.":"Saving makes this your plan. Holdings tabs (MTG, crypto, metals, ETFs, Acorns) are not needed: the UIP values those itself.")}</p><div class="rpg-home-actions"><button type="button" class="rpg-btn rpg-action" data-home-import-save>Save as the plan</button><button type="button" class="rpg-btn rpg-link rpg-link-ink" data-home-import-cancel>Cancel</button></div></div>`:"";
  return `<section class="rpg-stone rpg-guild-ledger" aria-labelledby="rpg-home-imp-h"><div class="rpg-section-head"><h2 id="rpg-home-imp-h" class="rpg-stone-title">Bring in the workbook</h2><span class="rpg-crumb-note">The Income &amp; Net Worth Tracker (.xlsx). It is checked against its own totals and only saved when you say so.</span></div><form class="rpg-board-filters" data-home-import><label>Workbook<input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" data-home-file></label><button type="submit" class="rpg-btn rpg-action">Read the workbook</button></form>${summary}</section>`;
}

function assumptions(p){
  const rows=Object.values(p.sleeves||{}).map(v=>`<tr><th scope="row">${esc(v.label)}</th><td class="num">${esc(pctText(v.annual_return,0))}</td><td class="num">${esc(pctText(v.annual_volatility,0))}</td><td class="num">${v.sell_cost?esc(pctText(v.sell_cost,0)):"\u2014"}</td></tr>`).join("");
  return `<section class="rpg-stone rpg-guild-research" aria-labelledby="rpg-home-as-h"><div class="rpg-section-head"><h2 id="rpg-home-as-h" class="rpg-stone-title">How the ranges are made</h2></div><div class="rpg-duo"><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Part</th><th class="num">Typical growth a year</th><th class="num">Yearly swing</th><th class="num">Selling cost</th></tr></thead><tbody>${rows}</tbody></table></div><ul class="rpg-home-limits">${(p.limitations||[]).map(l=>`<li>${esc(l)}</li>`).join("")}</ul></div><p class="rpg-footnote">${esc(`${p.paths.toLocaleString("en-US")} simulated markets, month by month, with the parts moving together the way they tend to (a bad year for stocks is usually a bad year for crypto). These are planning assumptions, not forecasts. Research, not personal financial advice.`)}</p></section>`;
}

/* ---------------- page ---------------- */
function render(){
  const page=byId("homestead");if(!page)return;
  let view=byId("rpg-homestead");
  if(!view){view=document.createElement("div");view.id="rpg-homestead";view.className="rpg-realm-view";page.appendChild(view);R().bindNavigation?.(view);bind(view)}
  if(!S.doc){view.innerHTML=`${crumbs("Household plan")}${message()}<p class="rpg-parch-note">Opening the household ledger\u2026</p>`;load();return}
  if(!S.plan){view.innerHTML=`${crumbs("Household plan \u00b7 not set up yet")}${message()}<section class="rpg-stone rpg-guild-hero"><div><div class="rpg-parch-kicker">The Homestead</div><p class="rpg-guild-counsel">Bring your Income &amp; Net Worth Tracker into the UIP once. After that the plan lives here: edit any month, enter real balances as months pass, and see the range of where the plan lands and what it means for the house.</p></div></section>${importPanel()}`;return}
  const v=S.doc.version,p=S.proj;
  const note=`Plan saved ${v?new Date(v.recorded_at).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"}):"\u2014"} \u00b7 ${monthLabel(S.plan.months[0].month)} to ${monthLabel(S.plan.months[S.plan.months.length-1].month)}${S.tried?" \u00b7 showing unsaved settings":""}`;
  view.innerHTML=`${crumbs(note)}${message()}${netWorth()}${emergency()}${goalsSection()}${owned()?ownerSection()+housingSection():p?goal(p)+fan(p)+targetTiles(p)+capacity(p)+ratesSection(p)+housingSection()+purchaseForm():`<p class="rpg-parch-note">Working out the ranges\u2026</p>`}${retirementSection()}${purse()}${ledger()}${settingsForm()}${importPanel()}${p?assumptions(p):""}`;
}
function setMsg(kind,text){S.msg=text?[kind,text]:null}
async function savePlan(plan,okText){
  try{const out=await post("/v1/household-plan",{plan});S.doc={available:true,version:out.version,plan:out.plan,rows:out.rows};S.plan=clone(out.plan);S.dirty=false;S.tried=null;setMsg("ok",okText);render();refreshProjection(true);loadNetWorth()}
  catch(error){setMsg("bad",`Not saved: ${error.message}`);render()}
}
function bind(view){
  view.addEventListener("click",event=>{
    const t=event.target.closest("button");if(!t||!view.contains(t))return;
    if(t.dataset.homeMonth){S.pick=t.dataset.homeMonth===S.pick?null:t.dataset.homeMonth;const slot=byId("rpg-home-editor");if(slot){slot.innerHTML=editor();view.querySelectorAll("[data-home-month]").forEach(b=>{const on=b.dataset.homeMonth===S.pick;b.setAttribute("aria-pressed",String(on));b.closest("tr")?.classList.toggle("is-picked",on)});slot.querySelector("input")?.focus()}return}
    if(t.dataset.homeChart){S.chart=t.dataset.homeChart;render();return}
    if(t.hasAttribute("data-home-export")){downloadData();return}
    if(t.hasAttribute("data-home-buy-try")||t.hasAttribute("data-home-buy-save")){const h=readPurchase(t.closest("form"));if(!(h.price>0)||!h.closing_month||h.loan_amount===null||h.rate===null){setMsg("bad","Enter at least the price, closing month, loan amount and rate.");render();return}
      if(t.hasAttribute("data-home-buy-try")){S.homeTried=h;S.homeDoc=null;setMsg(null);render();refreshHome(true);return}
      const plan=clone(S.plan);plan.settings={...plan.settings,home:h};S.homeTried=null;S.homeDoc=null;savePlan(plan,"The purchase is recorded. The Homestead is in owner mode.");return}
    if(t.hasAttribute("data-home-own-save")){const plan=clone(S.plan);plan.settings={...plan.settings,home:S.homeTried};S.homeTried=null;S.homeDoc=null;savePlan(plan,"The purchase is recorded. The Homestead is in owner mode.");return}
    if(t.hasAttribute("data-home-own-cancel")){S.homeTried=null;S.homeDoc=null;setMsg(null);render();refreshHome(true);return}
    if(t.hasAttribute("data-home-own-undo")){const plan=clone(S.plan);plan.settings={...plan.settings,home:null};S.homeDoc=null;savePlan(plan,"The purchase record is removed. The Homestead is back on the road to the house.");return}
    if(t.dataset.goalDone||t.dataset.goalRemove){const id=t.dataset.goalDone||t.dataset.goalRemove;const plan=clone(S.plan);const list=plan.settings.goals||[];const g=list.find(x=>x.id===id);if(!g)return;
      if(t.dataset.goalRemove){plan.settings.goals=list.filter(x=>x.id!==id);savePlan(plan,`Removed ${g.name}.`)}
      else{Object.assign(g,{status:"done",done_month:nowMonth(),done_amount:g.amount});savePlan(plan,`${g.name} marked done. It stays in the list with its date and amount.`)}
      return}
    if(t.hasAttribute("data-ret-try")){const cfg=readRetirement(t.closest("form"));if(!cfg.age||!cfg.retire_age){setMsg("bad","Enter your age and the age you want to retire.");render();return}S.retTried=cfg;S.ret=null;setMsg(null);render();refreshRetirement(true);return}
    if(t.hasAttribute("data-ret-keep")){const cfg=readRetirement(t.closest("form"));if(!cfg.age||!cfg.retire_age){setMsg("bad","Enter your age and the age you want to retire.");render();return}const plan=clone(S.plan);plan.settings={...plan.settings,retirement:cfg};S.retTried=null;S.ret=null;savePlan(plan,"Retirement inputs saved into the plan.");return}
    if(t.dataset.homeExtend){const n=extendPlan(S.plan,t.dataset.homeExtend);S.dirty=S.dirty||n>0;setMsg("ok",`Added ${n} month${n===1?"":"s"} through ${monthLabel(t.dataset.homeExtend)}, copied from the last month. Edit any of them, then save the plan.`);render();return}
    if(t.hasAttribute("data-home-close")){S.pick=null;render();return}
    if(t.dataset.homeUseStatements!==undefined){const input=t.closest("form")?.querySelector('[data-home-field="retirement_balance"]');if(input){input.value=t.dataset.homeUseStatements;input.focus()}return}
    if(t.dataset.homeApply==="later"){applyEdit(t.closest("form"),true);return}
    if(t.hasAttribute("data-home-save")){savePlan(S.plan,"Plan saved. The ranges are updated.");return}
    if(t.hasAttribute("data-home-discard")){S.plan=clone(S.doc.plan);S.dirty=false;setMsg(null);render();return}
    if(t.dataset.homeUseRate!==undefined){S.tried={...(S.tried||{}),mortgage_rate:Number(t.dataset.homeUseRate)};setMsg("ok","Showing the payments at the rate outlook's typical figure. Save it under The house and the plan to keep it.");S.proj=null;render();refreshProjection(true);return}
    if(t.dataset.homeUseGrowth!==undefined){S.tried={...(S.tried||{}),home_price_growth:Number(t.dataset.homeUseGrowth)};setMsg("ok","Showing the house price grown by the housing forecast. Save it under The house and the plan to keep it.");S.proj=null;render();refreshProjection(true);return}
    if(t.hasAttribute("data-home-try")){S.tried=readSettings(t.closest("form"));setMsg(null);S.proj=null;render();refreshProjection(true);return}
    if(t.hasAttribute("data-home-keep")){const plan=clone(S.plan);const set=readSettings(t.closest("form"));plan.settings={...plan.settings,...set};savePlan(plan,"Settings saved into the plan.");return}
    if(t.hasAttribute("data-home-import-save")){const plan=S.preview.plan;S.preview=null;savePlan(plan,"The workbook is now your plan in the UIP.");return}
    if(t.hasAttribute("data-home-import-cancel")){S.preview=null;render();return}
    if(t.hasAttribute("data-home-check-clear")){const plan=clone(S.plan);const m=plan.months.find(x=>x.month===nowMonth());if(m){m.bank_check=null;savePlan(plan,"Check-in cleared. The month rolls forward from the plan again.")}}
  });
  const live=event=>{const form=event.target.closest("[data-home-check]");if(!form)return;const m=readCheck(form);const box=form.querySelector("[data-check-sum]");if(box)box.innerHTML=purseSum(m,m.bank_check?.balance,m.bank_check?.done)};
  view.addEventListener("input",live);view.addEventListener("change",live);
  view.addEventListener("submit",async event=>{
    const form=event.target;event.preventDefault();
    if(form.dataset.homeEditor){applyEdit(form,false);return}
    if(form.hasAttribute("data-home-own-add")){
      const kind=form.querySelector('[data-own="kind"]').value,month=form.querySelector('[data-own="month"]').value,amount=Number(form.querySelector('[data-own="amount"]').value);
      if(!/^\d{4}-\d{2}$/.test(month)||!(amount>0)){setMsg("bad","Enter a month and an amount.");render();return}
      const plan=clone(S.plan),h=plan.settings.home;
      const item=kind==="statements"?{month,balance:amount}:kind==="extra_payments"?{month,amount}:{month,value:amount,hpi:marketNow(h.market).hpi};
      h[kind]=[...(h[kind]||[]).filter(x=>kind==="extra_payments"||x.month!==month),item];
      savePlan(plan,{statements:"Statement balance saved; the loan follows it from that month.",extra_payments:"Extra principal saved.",appraisals:"Appraisal saved; the home's value starts from it."}[kind]);return}
    if(form.hasAttribute("data-home-own-costs")){
      const plan=clone(S.plan),h=plan.settings.home;
      for(const k of ["pmi_monthly","escrow_monthly","hoa_monthly"]){const v=form.querySelector(`[data-own="${k}"]`).value;h[k]=v===""?0:Number(v)}
      savePlan(plan,"Monthly costs updated.");return}
    if(form.hasAttribute("data-goal-add")){
      const v=k=>form.querySelector(`[data-goal="${k}"]`)?.value||"";
      const name=v("name").trim(),amount=Number(v("amount")),month=v("month");
      if(!name||!(amount>0)||!/^\d{4}-\d{2}$/.test(month)){setMsg("bad","A goal needs a name, an amount and a month.");render();return}
      if(month<=nowMonth()){setMsg("bad","Pick a month after this one.");render();return}
      const plan=clone(S.plan);plan.settings.goals=[...(plan.settings.goals||[]),{name,amount,month,status:"open"}];
      savePlan(plan,`Added ${name}. The house and retirement chances now count it.`);return}
    if(form.hasAttribute("data-home-essentials")){
      const chosen=[...form.querySelectorAll("[data-home-essential]")].filter(el=>el.checked).map(el=>el.dataset.homeEssential);
      if(!chosen.length){setMsg("bad","Pick at least one essential bill.");render();return}
      const plan=clone(S.plan);plan.settings={...plan.settings,essential_lines:chosen.length===(plan.expense_lines||[]).length?null:chosen};
      savePlan(plan,"Saved. The emergency fund and the house's safety fund now count only the essential bills.");return}
    if(form.dataset.homeCheck){
      const m=readCheck(form);
      if(m.bank_check&&!Number.isFinite(m.bank_check.balance)){setMsg("bad","The bank balance must be a number.");render();return}
      const replaced=m.bank_check&&num(m.bank_balance)!==null;
      if(replaced)m.bank_balance=null;                  // a check-in is newer than a month-end figure typed in advance
      const plan=clone(S.plan);plan.months[plan.months.findIndex(x=>x.month===m.month)]=m;
      savePlan(plan,m.bank_check?`Check-in saved. ${monthLabel(m.month)} now ends from your real balance${replaced?" (it replaces the month-end bank figure the plan had)":""}.`:"Check-in cleared.");return}
    if(form.hasAttribute("data-home-import")){
      const file=form.querySelector("[data-home-file]")?.files?.[0];
      if(!file){setMsg("bad","Choose the workbook file first.");render();return}
      setMsg("ok","Reading the workbook\u2026");render();
      try{S.preview=await call("/v1/household-plan/import",{method:"POST",headers:{"Content-Type":"application/octet-stream"},body:file});setMsg(null)}
      catch(error){S.preview=null;setMsg("bad",`The workbook could not be used: ${error.message}`)}
      render();
    }
  });
}
function applyEdit(form,later){
  const month=form.dataset.homeEditor,idx=S.plan.months.findIndex(m=>m.month===month);if(idx<0)return;
  const m=S.plan.months[idx],before=clone(m),changed=[];
  form.querySelectorAll("[data-home-field]").forEach(el=>{
    const k=el.dataset.homeField;
    if(k==="note"){m.note=el.value;return}
    const v=el.value===""?null:Number(el.value);
    const [group,line]=k.includes(":")?k.split(/:(.*)/s):[null,k];
    if(group){if((m[group][line]??0)!==(v??0)){m[group][line]=v??0;changed.push([group,line])}}
    else if(["bank_balance","retirement_balance","investment_balance","house_fund_balance"].includes(k))m[k]=v;
    else if((m[k]??0)!==(v??0)){m[k]=v??0;changed.push([null,k])}
  });
  if(later)for(const later of S.plan.months.slice(idx+1))for(const [g,l] of changed){if(g)later[g][l]=m[g][l];else later[l]=m[l]}
  S.dirty=S.dirty||JSON.stringify(before)!==JSON.stringify(m)||(later&&changed.length>0);
  setMsg("ok",later&&changed.length?`Applied to ${monthLabel(month)} and every later month. Save the plan to keep it.`:`Applied to ${monthLabel(month)}. Save the plan to keep it.`);
  render();
}

function watch(){
  document.addEventListener("click",event=>{if(event.target.closest('.nav-item[data-page="homestead"]'))setTimeout(()=>{try{render()}catch(error){console.error("[homestead]",error)}},0)});
  if(location.hash==="#homestead")setTimeout(render,0);
  document.addEventListener("uip:home-rendered",()=>{if(S.doc?.available)refreshProjection(false);if(byId("rpg-homestead")&&byId("homestead")?.classList.contains("active-page"))render()});
  // New retirement balances or MTG cards change net worth: read it again (and on opening the page, at most once a minute).
  document.addEventListener("uip:mtg-singles-changed",()=>{S.nwAt=0;if(S.doc)loadNetWorth()});
  document.addEventListener("click",event=>{if(event.target.closest('.nav-item[data-page="homestead"],[data-rpg-page="homestead"]')&&S.doc&&Date.now()-(S.nwAt||0)>60000)loadNetWorth()});
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",watch);else watch();
window.UIPHomestead={render,state:S,roll};
})();
