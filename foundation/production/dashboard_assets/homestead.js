/* The Homestead: the household plan (income, bills, savings, balances) and the road to the house.
   Replaces the Income & Net Worth Tracker workbook. Reads and writes /v1/household-plan; the
   ranges come from /v1/household-plan/projection with the live holdings from the Treasury. */
(()=>{
"use strict";
const S={doc:null,plan:null,dirty:false,proj:null,projKey:"",pick:null,chart:"house",preview:null,msg:null,tried:null,loading:false};
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
  call("/v1/presentation/housing").then(h=>{S.housing=h;if(S.doc)render()}).catch(()=>{S.housing={available:false}});
  call("/v1/household-plan").then(doc=>{S.doc=doc;S.plan=doc.available?clone(doc.plan):null;S.dirty=false;S.loading=false;render();refreshProjection(true)})
    .catch(error=>{S.loading=false;S.msg=["bad",error.message];render()});
}
function refreshProjection(force){
  if(!S.doc?.available)return;
  const holdings=liveHoldings();
  const body={as_of_month:nowMonth(),holdings:holdings||undefined,settings:S.tried||undefined};
  const k=JSON.stringify([S.doc.version?.version_id,body]);
  if(!force&&k===S.projKey)return;
  S.projKey=k;
  post("/v1/household-plan/projection",body).then(p=>{if(S.projKey!==k)return;S.proj=p;render()}).catch(error=>{S.msg=["bad",`Ranges could not be computed: ${error.message}`];render()});
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
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-home-t-h"><div class="rpg-section-head"><h2 id="rpg-home-t-h" class="rpg-stone-title">${esc(monthLabel(p.target_month))}, typical case</h2><span class="rpg-crumb-note">Starting from ${esc(money(p.starting_investments))} invested today${p.starting_investments_source==="LIVE_UIP_HOLDINGS"?" (live UIP holdings)":" (the plan's balance)"}, plus ${esc(money(p.investment_contributions_ahead))} still to put in</span></div><div class="rpg-tiles rpg-home-tiles">${tile("Investments",money(t.investments.p50),`plan ${money(last.investment_balance)} \u00b7 ${sleeves}`)}${tile("Bank",money(last.bank_balance),"as your plan has it")}${tile("Retirement",money(s.retirement),`plan ${money(last.retirement_balance)} \u00b7 not counted toward the house`)}${tile(`Chance below the plan's ${compact(t.plan_net_worth)}`,pctText(p.chance_below_plan_net_worth),`investments end below what you put in: ${pctText(p.chance_investments_below_money_put_in)}`)}</div></section>`;
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
  return `<section class="rpg-stone rpg-guild-ledger" aria-labelledby="rpg-home-led-h"><div class="rpg-section-head"><h2 id="rpg-home-led-h" class="rpg-stone-title">The ledger of months</h2><span class="rpg-crumb-note">Pick a month to edit it. Gold figures are actuals you entered; the rest roll forward from them.</span></div>${S.dirty?`<div class="rpg-home-dirty" role="status"><span>Unsaved changes to the plan.</span><button type="button" class="rpg-btn rpg-action" data-home-save>Save the plan</button><button type="button" class="rpg-btn rpg-link" data-home-discard>Discard</button></div>`:""}<div class="rpg-table-wrap"><table class="rpg-table rpg-guild-table rpg-home-ledger"><thead><tr><th>Month</th><th class="num">Income</th><th class="num">Bills</th><th class="num">Net</th><th class="num">Invested</th><th class="num">Bank</th><th class="num">Retirement</th><th class="num">Investments</th><th class="num">Net worth</th></tr></thead><tbody>${body}</tbody></table></div><div id="rpg-home-editor">${editor()}</div></section>`;
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
  return `<form class="rpg-home-editor" data-home-editor="${esc(m.month)}"><h3 class="rpg-stone-title">${esc(monthLabel(m.month))}</h3><fieldset><legend>Income</legend><div class="rpg-board-filters rpg-home-grid">${inc}</div></fieldset><fieldset><legend>Bills</legend><div class="rpg-board-filters rpg-home-grid">${exp}</div></fieldset><fieldset><legend>Savings</legend><div class="rpg-board-filters rpg-home-grid">${field("investment_contribution","Into investments",m.investment_contribution)}${field("house_fund_contribution","Into a house fund",m.house_fund_contribution)}${field("retirement_contribution","Into retirement",m.retirement_contribution)}</div></fieldset><fieldset><legend>Actual balances at month end (leave blank to roll forward)</legend><div class="rpg-board-filters rpg-home-grid">${field("bank_balance","Bank",m.bank_balance)}${field("retirement_balance","Retirement",m.retirement_balance)}${field("investment_balance","Investments",m.investment_balance)}${field("house_fund_balance","House fund",m.house_fund_balance)}</div></fieldset><label class="rpg-home-note">Note<input type="text" maxlength="500" data-home-field="note" value="${esc(m.note||"")}"></label><div class="rpg-home-actions"><button type="submit" class="rpg-btn rpg-action" data-home-apply="one">Apply to ${esc(monthLabel(m.month))}</button><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-home-apply="later">Apply income, bills and savings to every later month too</button><button type="button" class="rpg-btn rpg-link" data-home-close>Close</button></div></form>`;
}

const SIGNAL_TONE={"Strong Buy":"verdant","Buy":"verdant","Slight Buy":"verdant","Neutral / Fair Value":"bronze","Slight Wait":"azure","Wait":"crimson","Strong Wait / High Risk":"crimson"};
function badge(label,tone){return `<span class="rpg-badge rpg-badge-${tone}">${esc(label)}</span>`}
function payment(principal,rate,years){const r=rate/12,n=years*12;return r?principal*r/(1-Math.pow(1+r,-n)):principal/n}
const monthsBetween=(a,b)=>(Number(b.slice(0,4))-Number(a.slice(0,4)))*12+Number(b.slice(5,7))-Number(a.slice(5,7));
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
  const why=`${nc!==null&&cf!==null?`Since ${String(t.first_origin||"1985").slice(0,4)}, guessing "no change" missed the rate ${row.months} months later by ${nc.toFixed(1)} points on average, and the market's own yield curve missed by ${cf.toFixed(1)}: nobody, the bond market included, has had an edge on where mortgage rates will be in three years. `:""}So the typical figure starts from today's rate, and the range is how far rates actually moved over past ${row.months}-month stretches${num(t.band_coverage_10_90)===null?"":` (${Math.round(num(t.band_coverage_10_90)*100)}% of past outcomes landed inside it)`}. The market's curve today points to about ${num(row.curve_forward)===null?"\u2014":`${Number(row.curve_forward).toFixed(1)}%`}${R0.fomc_sep_context?.fed_funds_longer_run_median?`; the Fed's own projections put its overnight rate near ${Number(R0.fomc_sep_context.fed_funds_longer_run_median).toFixed(1)}% in the longer run, but mortgages follow the 10-year Treasury (${Number(R0.treasury_10y).toFixed(2)}% now, with a ${Number(R0.spread_3m).toFixed(2)}-point mortgage spread), not that rate`:""}. Owners who locked in 2\u20134% rarely sell at ${Number(now.rate).toFixed(1)}%; if rates fall toward the low end, more of them list, which adds supply and tends to slow price gains.`;
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
    return `<article class="rpg-parch rpg-home-market"><div class="rpg-section-head"><h3 class="rpg-parch-title">${esc(m.market.replace(" Composite",""))}${m.market_rank?` \u00b7 #${esc(m.market_rank)}`:""}</h3>${badge(m.signal,SIGNAL_TONE[m.signal]||"stone")}</div><div class="rpg-item-stats"><div><div class="rpg-stat-label">Entry score</div><div class="rpg-stat-value">${esc(Number(m.entry_score).toFixed(1))} / 100</div></div><div><div class="rpg-stat-label">Next 12 months</div><div class="rpg-stat-value">${pctText(g,1)}</div><div class="rpg-stat-sub">${esc(`${v10?"walk-forward":"tested"} error \u00b1${pctText(m.walk_forward_mae,1)}${v10?"":`, as of ${monthLabel(String(m.market_state_as_of).slice(0,7))}`}`)}</div></div><div><div class="rpg-stat-label">Best window</div><div class="rpg-stat-value">${bw.months?`${esc(bw.months)} months`:"\u2014"}</div><div class="rpg-stat-sub">${bw.months?`${Math.round(num(bw.prob_neutral_or_better)*100)}% chance of fair value or better`:""}</div></div></div>${stale?`<p class="rpg-item-note rpg-home-stale">${esc(v10?`This describes ${monthLabel(String(m.market_state_as_of).slice(0,7))}, ${behind} months behind the newest data: V10 scores the last quarter whose next 12 months are already known${realized!==null?` (that period actually grew ${pctText(realized,1)})`:""}.`:`This describes ${monthLabel(String(m.market_state_as_of).slice(0,7))}, ${behind} months behind the newest data.`)}</p>`:""}<p class="rpg-item-note">${esc(`${calText(cal)} ${tr.plain_english||""}`)}</p><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-home-use-growth="${esc(g)}" ${using?"disabled":""}>${using?"Used for the house price":`Grow the house price ${pctText(g,1)} a year`}</button></article>`}).join("");
  return `<section class="rpg-stone rpg-road rpg-home-housing" aria-labelledby="rpg-home-hm-h"><div class="rpg-section-head"><h2 id="rpg-home-hm-h" class="rpg-stone-title">The housing market</h2><span class="rpg-crumb-note">${esc(`Housing Intelligence Platform ${pkg.model_version||""} \u00b7 provisional \u00b7 data through ${pkg.latest_input_observation?monthLabel(String(pkg.latest_input_observation).slice(0,7)):"\u2014"}`)}</span></div><div class="rpg-home-markets">${cards}</div><p class="rpg-footnote">${esc(v10?"Scores rank each market against its own history; the 12-month forecast's walk-forward error is optimistic in V10 and calibration is in-sample. Research, not advice.":"Each quarter's score ranks it against that market's history up to then. The 12-month forecast's error comes from a walk-forward test that trains only on what was known at the time. The Entry Score failed its out-of-sample timing test, so read the signal as a description of buying conditions (prices, supply, rates, affordability), not as a forecast of when prices will rise. Research, not advice.")}</p></section>`;
}
function settingsForm(){
  const s=S.plan.settings,mix=s.contribution_mix||{};
  const f=(k,label,v,step="any",extra="")=>`<label>${esc(label)}<input type="number" step="${step}" data-home-set="${k}" value="${v===null||v===undefined?"":esc(v)}"${extra}></label>`;
  return `<section class="rpg-stone rpg-guild-ledger" aria-labelledby="rpg-home-set-h"><div class="rpg-section-head"><h2 id="rpg-home-set-h" class="rpg-stone-title">The house and the plan</h2><span class="rpg-crumb-note">Try changes to see the ranges move, then save them into the plan.</span></div><form class="rpg-board-filters rpg-home-grid" data-home-settings><label>Target month<input type="month" data-home-set="target_month" value="${esc(s.target_month)}"></label>${f("home_price_low","Home price, low",s.home_price_low,"1000")}${f("home_price_high","Home price, high",s.home_price_high,"1000")}${f("home_price_growth","Home-price growth % a year",Math.round((s.home_price_growth||0)*1000)/10,"0.1")}${f("down_payment_pct","Down payment %",Math.round(s.down_payment_pct*1000)/10,"0.5")}${f("closing_cost_pct","Closing costs %",Math.round(s.closing_cost_pct*1000)/10,"0.5")}${f("safety_fund","Safety fund ($, blank = months)",s.safety_fund,"100")}${f("safety_fund_months","Safety fund (months of bills)",s.safety_fund_months,"1")}${f("mortgage_rate","Mortgage rate %",Math.round(s.mortgage_rate*10000)/100,"0.05")}${f("loan_years","Loan years",s.loan_years,"1")}${f("plan_investment_return","Plan's steady return %",Math.round(s.plan_investment_return*1000)/10,"0.5")}<fieldset class="rpg-home-mix"><legend>Where new investment money goes (%)</legend>${SLEEVES.map(([k,l])=>f(`mix:${k}`,l,Math.round((mix[k]||0)*1000)/10,"5")).join("")}</fieldset><label class="rpg-check"><input type="checkbox" data-home-set="house_counts_retirement"${s.house_counts_retirement?" checked":""}> Count retirement toward the house</label><div class="rpg-home-actions"><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-home-try>Try these</button><button type="button" class="rpg-btn rpg-action" data-home-keep>Save into the plan</button></div></form></section>`;
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
  view.innerHTML=`${crumbs(note)}${message()}${p?goal(p)+fan(p)+targetTiles(p)+capacity(p)+ratesSection(p)+housingSection():`<p class="rpg-parch-note">Working out the ranges\u2026</p>`}${purse()}${ledger()}${settingsForm()}${importPanel()}${p?assumptions(p):""}`;
}
function setMsg(kind,text){S.msg=text?[kind,text]:null}
async function savePlan(plan,okText){
  try{const out=await post("/v1/household-plan",{plan});S.doc={available:true,version:out.version,plan:out.plan,rows:out.rows};S.plan=clone(out.plan);S.dirty=false;S.tried=null;setMsg("ok",okText);render();refreshProjection(true)}
  catch(error){setMsg("bad",`Not saved: ${error.message}`);render()}
}
function bind(view){
  view.addEventListener("click",event=>{
    const t=event.target.closest("button");if(!t||!view.contains(t))return;
    if(t.dataset.homeMonth){S.pick=t.dataset.homeMonth===S.pick?null:t.dataset.homeMonth;const slot=byId("rpg-home-editor");if(slot){slot.innerHTML=editor();view.querySelectorAll("[data-home-month]").forEach(b=>{const on=b.dataset.homeMonth===S.pick;b.setAttribute("aria-pressed",String(on));b.closest("tr")?.classList.toggle("is-picked",on)});slot.querySelector("input")?.focus()}return}
    if(t.dataset.homeChart){S.chart=t.dataset.homeChart;render();return}
    if(t.hasAttribute("data-home-close")){S.pick=null;render();return}
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
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",watch);else watch();
window.UIPHomestead={render,state:S,roll};
})();
