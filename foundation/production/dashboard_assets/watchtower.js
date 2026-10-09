/* The Watchtower: the Composite Recession Stress Index (RSI v2.0) from the Macro Intelligence Platform.
   Read-only. Reads /v1/presentation/macro. It informs; it never trades, allocates or decides a purchase. */
(()=>{
"use strict";
const S={doc:null,loading:false,open:null};
const byId=id=>document.getElementById(id);
const esc=v=>{const n=document.createElement("span");n.textContent=String(v??"");return n.innerHTML};
const num=v=>{if(v===null||v===undefined||v==="")return null;const n=Number(v);return Number.isFinite(n)?n:null};
const MONTHS=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const monthLabel=m=>/^\d{4}-\d{2}/.test(String(m||""))?`${MONTHS[Number(String(m).slice(5,7))-1]} ${String(m).slice(0,4)}`:"\u2014";
const sgn=(v,d=2)=>{const n=num(v);return n===null?"\u2014":`${n>0?"+":n<0?"\u2212":""}${Math.abs(n).toFixed(d)}`};
const key=()=>sessionStorage.getItem("uiip-dashboard-key")||"";
const R=()=>window.UIPRealm||{};
async function call(path){
  const r=await fetch(path,{headers:{"X-API-Key":key(),"Accept":"application/json"}});
  const body=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(body.error?.message||`Request failed (${r.status})`);
  return body;
}
function badge(label,tone){return `<span class="rpg-badge rpg-badge-${tone}">${esc(label)}</span>`}
const BAND={EXPANSION:["Expansion","verdant","Conditions support growth"],LATE_CYCLE:["Late cycle","bronze","Mostly supportive, with some strain"],DETERIORATION:["Deteriorating","bronze","Several systems are flashing stress"],RECESSIONARY_STRESS:["Recessionary stress","crimson","Broad stress across systems"],PANIC:["Panic","crimson","Stress in nearly every system"]};
const SYSTEM={labor:"Labor",financial:"Financial conditions",real_economy:"Real economy",liquidity:"Liquidity",market:"Market expectations",consumer:"Consumer psychology"};
const COMP={payrolls:"Payrolls",claims:"Jobless claims",unemployment:"Unemployment (Sahm reading)",yield_curve:"Yield curve (10y \u2212 3m)",credit:"Credit spreads",manufacturing:"Manufacturing (Philly Fed)",housing:"Building permits",m2:"M2 money supply",sp500_trend:"S&P 500 trend",sentiment:"Consumer sentiment"};
const STATUS={OK:["OK","verdant"],FLOORED_AFTER_INVERSION:["FLOORED","bronze"],STALE:["STALE","crimson"],MISSING:["MISSING","crimson"]};
const tone=v=>v===null?"":v<0?"rpg-up":v>0?"rpg-down":"";
function crumbs(note){
  const tabs=R().realmTabs?R().realmTabs("macro"):"";
  return `<header class="rpg-stone rpg-crumbs"><nav aria-label="Breadcrumb"><button type="button" class="rpg-btn rpg-crumb" data-rpg-page="home">The Hall</button><span aria-hidden="true">\u203a</span><span class="rpg-crumb-here">The Watchtower</span></nav><span class="rpg-crumb-note">${esc(note)}</span></header>${tabs}`;
}

/* -1..+1 gauge with the v1 bands */
function gauge(rsi,prev){
  const X0=20,X1=880,x=v=>X0+(X1-X0)*(Math.max(-1,Math.min(1,v))+1)/2;
  const zones=[[-1,0,"#4d7a3a"],[0,0.2,"#9c7a33"],[0.2,0.4,"#b5862f"],[0.4,0.6,"#a9452f"],[0.6,1,"#7a2a1e"]];
  const ticks=[-1,-0.5,0,0.2,0.4,0.6,1];
  const mark=v=>num(v)===null?"":`<path d="M${x(v).toFixed(1)} 18 l-9 -14 h18 z" fill="#f1d78f" stroke="#1b140c" stroke-width="1.5"/>`;
  const ghost=num(prev)===null?"":`<line x1="${x(prev).toFixed(1)}" y1="22" x2="${x(prev).toFixed(1)}" y2="52" stroke="#f1e3c2" stroke-dasharray="3 3" stroke-width="1.5"/>`;
  return `<svg viewBox="0 0 900 84" class="rpg-fluid rpg-watch-gauge" role="img" aria-label="${esc(`RSI ${sgn(rsi)} on a scale from minus one (supportive) to plus one (stress)`)}">${zones.map(([a,b,c])=>`<rect x="${x(a).toFixed(1)}" y="22" width="${(x(b)-x(a)).toFixed(1)}" height="30" fill="${c}"/>`).join("")}${ghost}${mark(rsi)}<g font-family="Alegreya, serif" font-size="14" fill="#b9a98a" text-anchor="middle">${ticks.map(t=>`<text x="${x(t).toFixed(1)}" y="72">${sgn(t,1).replace("+0.0","0").replace("\u22120.0","0")}</text>`).join("")}</g></svg>`;
}
function hero(cur,pkg){
  const hist=(pkg.history||[]).filter(h=>num(h.rsi)!==null);
  const last=hist[hist.length-1],prev=hist[hist.length-2];
  const rsi=num(cur.rsi),b=BAND[cur.band]||["Not published","stone","Too little current data to publish a reading"];
  const delta=last&&prev&&last.month===cur.as_of_month?num(last.rsi)-num(prev.rsi):null;
  const oil=(cur.overlays||{}).inflation_energy_shock;
  const why=rsi===null?`Coverage is ${Math.round(num(cur.coverage)*100)}%, below the 80% the index needs, so no headline is shown.`:`Below zero means the six systems mostly support growth; above zero means stress. The band names are the original v1 labels, not measured odds of recession.${delta===null?"":` That is ${sgn(delta)} since ${monthLabel(prev.month)}.`}`;
  return `<section class="rpg-stone rpg-road rpg-watch-hero" aria-labelledby="rpg-watch-h"><div class="rpg-section-head"><h2 id="rpg-watch-h" class="rpg-stone-title">The storm signs \u00b7 ${esc(monthLabel(cur.as_of_month))}</h2>${badge(b[0].toUpperCase(),b[1])}</div><div class="rpg-watch-top"><div class="rpg-watch-big num ${tone(rsi)}">${rsi===null?"\u2014":sgn(rsi)}</div><div><p class="rpg-watch-band">${esc(b[2])}</p><p class="rpg-vault-why">${esc(why)}</p></div></div>${gauge(rsi,prev&&last&&last.month===cur.as_of_month?prev.rsi:null)}<div class="rpg-watch-chips">${badge(`COVERAGE ${Math.round(num(cur.coverage)*100)}%`,num(cur.coverage)>=0.999?"verdant":"bronze")} ${badge(`RSI v${esc(cur.model_version||"2.0.0")}`,"stone")} ${oil?badge(oil.flag==="NONE"?`OIL ${sgn(oil.value,0)}% Y/Y`:`OIL ${oil.flag} ${sgn(oil.value,0)}%`,oil.flag==="NONE"?"stone":"crimson"):""} ${badge("PROVISIONAL","stone")}</div></section>`;
}
function bar(v){const n=num(v);if(n===null)return `<span class="rpg-muted">\u2014</span>`;const w=Math.abs(n)*50;return `<span class="rpg-watch-bar" aria-hidden="true"><i class="${n<0?"is-good":"is-bad"}" style="${n<0?`right:50%;width:${w}%`:`left:50%;width:${w}%`}"></i></span>`}
function systems(cur){
  const comps=cur.components||[];
  const rows=Object.entries(cur.systems||{}).map(([k,s])=>{
    const mine=comps.filter(c=>c.system===k),contrib=mine.reduce((a,c)=>a+(num(c.contribution)||0),0);
    const open=S.open===k;
    const sub=open?mine.map(c=>{const st=STATUS[c.status]||["\u2014","stone"];return `<tr class="rpg-watch-sub"><th scope="row">${esc(COMP[c.component]||c.component)} <small>${Math.round(c.within_weight*100)}%</small></th><td class="num">${num(c.value)===null?"\u2014":esc(Number(c.value).toFixed(Math.abs(c.value)>=100?0:2))}<br><small>${esc(c.unit)}</small></td><td class="num ${tone(num(c.score))}">${sgn(c.score)}</td><td>${bar(c.score)}</td><td class="num">${sgn(c.contribution,3)}</td><td class="rpg-nowrap">${badge(st[0],st[1])}<br><small>${esc(monthLabel(c.observation_month))}${c.anchors?` \u00b7 \u22121 at ${esc(c.anchors.expansion)}, +1 at ${esc(c.anchors.stress)}`:""}</small></td></tr>`}).join(""):"";
    return `<tr class="rpg-watch-sys"><th scope="row"><button type="button" class="rpg-btn rpg-link" data-watch-open="${esc(k)}" aria-expanded="${open}">${open?"\u25be":"\u25b8"} ${esc(SYSTEM[k]||k)}</button></th><td class="num">${Math.round(s.weight*100)}%</td><td class="num ${tone(num(s.score))}"><strong>${sgn(s.score)}</strong></td><td>${bar(s.score)}</td><td class="num">${sgn(contrib,3)}</td><td>${s.coverage<0.999?badge(`${Math.round(s.coverage*100)}% DATA`,"bronze"):""}</td></tr>${sub}`}).join("");
  return `<section class="rpg-stone rpg-guild-ledger" aria-labelledby="rpg-watch-sys-h"><div class="rpg-section-head"><h2 id="rpg-watch-sys-h" class="rpg-stone-title">The six watch-fires</h2><span class="rpg-crumb-note">Open a system to see its readings. Each is scored \u22121 (supportive) to +1 (stress) on a straight line between two fixed thresholds.</span></div><div class="rpg-table-wrap"><table class="rpg-table rpg-watch-table"><thead><tr><th>System</th><th class="num">Weight</th><th class="num">Score</th><th>\u22121 \u2026 +1</th><th class="num">Adds to RSI</th><th>Status</th></tr></thead><tbody>${rows}</tbody><tfoot><tr><th scope="row">RSI</th><td class="num">100%</td><td class="num"><strong>${sgn(cur.rsi)}</strong></td><td></td><td class="num">${sgn(cur.rsi,3)}</td><td></td></tr></tfoot></table></div></section>`;
}
function chart(pkg){
  const h=(pkg.history||[]).filter(r=>num(r.rsi)!==null);
  if(h.length<24)return "";
  const X0=50,X1=880,Y0=14,Y1=226,n=h.length;
  const x=i=>X0+(X1-X0)*i/(n-1),y=v=>Y1-(Y1-Y0)*(v+1)/2;
  const shade=[];let start=null;
  h.forEach((r,i)=>{if(r.recession&&start===null)start=i;if((!r.recession||i===n-1)&&start!==null){shade.push([start,r.recession?i:i-1]);start=null}});
  const years=[...new Set(h.map(r=>r.month.slice(0,4)))].filter(yy=>Number(yy)%5===0);
  const line=h.map((r,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(num(r.rsi)).toFixed(1)}`).join(" ");
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-watch-hist-h"><div class="rpg-section-head"><h2 id="rpg-watch-hist-h" class="rpg-stone-title">The wall \u00b7 ${esc(monthLabel(h[0].month))} to ${esc(monthLabel(h[n-1].month))}</h2><span class="rpg-crumb-note">Shaded: NBER recessions \u00b7 dashed: 0.2, where the v1 bands turn to deterioration</span></div><svg viewBox="0 0 900 250" class="rpg-fluid" role="img" aria-label="${esc(`RSI by month since ${monthLabel(h[0].month)}, with recessions shaded`)}">${shade.map(([a,b])=>`<rect x="${x(a).toFixed(1)}" y="${Y0}" width="${Math.max(2,x(b)-x(a)).toFixed(1)}" height="${Y1-Y0}" fill="#5a2a22" opacity="0.55"/>`).join("")}<g stroke="#4a3d2c">${[-1,-0.5,0,0.5,1].map(v=>`<line x1="${X0}" x2="${X1}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`).join("")}</g><line x1="${X0}" x2="${X1}" y1="${y(0.2).toFixed(1)}" y2="${y(0.2).toFixed(1)}" stroke="#d9b45a" stroke-dasharray="5 4"/><g font-family="Alegreya, serif" font-size="13" fill="#b9a98a" text-anchor="end">${[-1,-0.5,0,0.5,1].map(v=>`<text x="${X0-6}" y="${(y(v)+4).toFixed(1)}">${v===0?"0":sgn(v,1)}</text>`).join("")}</g><g font-family="Alegreya, serif" font-size="13" fill="#b9a98a" text-anchor="middle">${years.map(yy=>{const i=h.findIndex(r=>r.month.startsWith(yy));return `<text x="${x(i).toFixed(0)}" y="244">${yy}</text>`}).join("")}</g><path d="${line}" fill="none" stroke="#e2c27a" stroke-width="2"/></svg><p class="rpg-footnote">${esc("Replayed on today's revised data, each month using only figures published by then. It is not a real-time record of what was known at the time, and nothing in the index was fitted to these recessions.")}</p></section>`;
}
function trials(pkg){
  const ev=pkg.evaluation||{};
  const rows=(ev.recessions||[]).map(e=>`<tr><th scope="row">${esc(monthLabel(e.recession_start))}</th><td class="num ${tone(num(e.rsi_12_months_before))}">${sgn(e.rsi_12_months_before)}</td><td class="num">${e.lead_months===null?"never":`${esc(e.lead_months)} months`}</td><td class="num ${tone(num(e.max_in_24_before))}">${sgn(e.max_in_24_before)}</td><td class="num ${tone(num(e.rsi_at_start))}">${sgn(e.rsi_at_start)}</td></tr>`).join("");
  const fa=ev.false_alarms||[];
  const falseText=fa.length?`It crossed 0.2 without a recession following within a year ${fa.length} time${fa.length>1?"s":""}: ${fa.map(f=>`${monthLabel(f.from)}\u2013${monthLabel(f.to)} (peak ${sgn(f.peak)})`).join("; ")}.`:"It never crossed 0.2 without a recession following within a year.";
  return `<section class="rpg-stone rpg-guild-research" aria-labelledby="rpg-watch-ev-h"><div class="rpg-section-head"><h2 id="rpg-watch-ev-h" class="rpg-stone-title">How it read before past recessions</h2></div><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Recession began</th><th class="num">RSI a year before</th><th class="num">First at 0.2+ (within 2 years before)</th><th class="num">Highest in those 2 years</th><th class="num">At the start</th></tr></thead><tbody>${rows||`<tr><td colspan="5" class="rpg-muted">No recession in the replay window.</td></tr>`}</tbody></table></div><p class="rpg-vault-why">${esc(`${falseText} Average reading in recession months ${sgn(ev.mean_rsi_in_recession_months)}, outside them ${sgn(ev.mean_rsi_outside_recessions)}. ${ev.note||""}`)}</p></section>`;
}
function others(cur,pkg){
  const rp=pkg.recession_probability||{},ae=pkg.asset_environment||{};
  const oil=(cur.overlays||{}).inflation_energy_shock;
  const card=(title,status,body,tn)=>`<div class="rpg-parch rpg-watch-card"><div class="rpg-parch-kicker">${esc(title)}</div>${badge(status,tn)}<p>${esc(body)}</p></div>`;
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-watch-more-h"><div class="rpg-section-head"><h2 id="rpg-watch-more-h" class="rpg-stone-title">The rest of the system</h2></div><div class="rpg-watch-cards">${card("12-month recession probability","NOT PUBLISHED",`${String(rp.why||"Hidden until a walk-forward model passes").replace(/\.?$/,".")} No percentage is shown until it holds up against the history of recessions it never saw.`,"stone")}${card("Asset environment","NOT YET",`${String(ae.why||"Phase 5").replace(/\.?$/,".")} A healthy economy is not the same as a good price to buy at.`,"stone")}${card("Energy shock overlay",oil?(oil.flag==="NONE"?"QUIET":oil.flag):"\u2014",oil?`WTI crude is ${sgn(oil.value,0)}% on a year earlier (${monthLabel(oil.observation_month)}). Shown beside the index, not inside it: oil was left out of the accepted v2 formula.`:"No oil data this run.",oil&&oil.flag!=="NONE"?"crimson":"stone")}${card("Housing","HOMESTEAD","Wichita and Dallas\u2013Fort Worth, the mortgage-rate outlook and your plan live in the Homestead; this index adds the national backdrop.","stone")}</div><button type="button" class="rpg-btn rpg-action rpg-action-quiet" data-rpg-page="homestead">Go to the Homestead</button></section>`;
}
function legacy(pkg){
  const rows=(pkg.legacy_snapshots||[]).map(s=>`<tr><th scope="row" class="rpg-nowrap">${esc(s.as_of)}</th><td class="num">${esc(s.rsi_reported||"\u2014")}</td><td class="num">${s.v2_recomputed_for_that_month===null||s.v2_recomputed_for_that_month===undefined?"\u2014":sgn(s.v2_recomputed_for_that_month)}</td><td class="num">${esc(s.risk_reported||"\u2014")}</td><td>${esc(s.notes||"")}</td></tr>`).join("");
  if(!rows)return "";
  return `<section class="rpg-stone rpg-guild-ledger" aria-labelledby="rpg-watch-leg-h"><div class="rpg-section-head"><h2 id="rpg-watch-leg-h" class="rpg-stone-title">Earlier readings (unverified)</h2>${badge("LEGACY","bronze")}</div><p class="rpg-vault-why">${esc("These came from earlier conversations, with changing thresholds and hand arithmetic. They are kept as history beside what v2.0 computes for the same month, and never mixed into its series.")}</p><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>As of</th><th class="num">Reported then</th><th class="num">v2.0 for that month</th><th class="num">Recession risk then</th><th>Notes</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
}
function freshness(pkg){
  const f=pkg.data_freshness||{};const names={PAYEMS:"Payrolls",IC4WSA:"Claims (4-wk)",CCSA:"Continuing claims",UNRATE:"Unemployment",T10Y3M:"Yield curve",BAMLH0A0HYM2:"High-yield spread",BAA10Y:"Baa spread",GACDFSA066MSFRBPHI:"Philly Fed",PERMIT:"Permits",M2SL:"M2",UMCSENT:"Sentiment",DCOILWTICO:"WTI oil","^GSPC":"S&P 500",USREC:"NBER recessions",MORTGAGE30US:"30-yr mortgage"};
  const items=Object.entries(f).map(([k,v])=>`<li><span>${esc(names[k]||k)}</span><strong>${esc(v.date)}</strong></li>`).join("");
  return items?`<section class="rpg-stone rpg-road"><div class="rpg-section-head"><h2 class="rpg-stone-title">Latest data</h2><span class="rpg-crumb-note">${esc(`Package ${pkg.package_id||""} \u00b7 generated ${String(pkg.generated_at_utc||"").slice(0,16).replace("T"," ")} UTC`)}</span></div><ul class="rpg-watch-fresh">${items}</ul></section>`:"";
}
function load(){
  if(S.loading)return;S.loading=true;
  call("/v1/presentation/macro").then(d=>{S.doc=d;S.loading=false;render()}).catch(e=>{S.doc={available:false,error:e.message};S.loading=false;render()});
}
function render(){
  const page=byId("watchtower");if(!page)return;
  let view=byId("rpg-watchtower");
  if(!view){view=document.createElement("div");view.id="rpg-watchtower";view.className="rpg-realm-view";page.appendChild(view);R().bindNavigation?.(view);
    view.addEventListener("click",event=>{const t=event.target.closest("[data-watch-open]");if(!t)return;S.open=S.open===t.dataset.watchOpen?null:t.dataset.watchOpen;render()})}
  if(!S.doc){view.innerHTML=`${crumbs("Recession stress")}<p class="rpg-parch-note">Climbing the tower\u2026</p>`;load();return}
  if(!S.doc.available){view.innerHTML=`${crumbs("Recession stress")}<section class="rpg-stone"><p class="rpg-parch-note">${esc(S.doc.error?`The Watchtower could not be read: ${S.doc.error}`:"The Watchtower has no reading in this publication yet. It fills after the Macro Intelligence Platform's daily package publishes.")}</p></section>`;return}
  const cur=S.doc.current||{},pkg=S.doc.package||{};
  view.innerHTML=`${crumbs(`RSI v${cur.model_version||"2.0.0"} \u00b7 as of ${monthLabel(cur.as_of_month)} \u00b7 provisional`)}${hero(cur,pkg)}${systems(cur)}${chart(pkg)}${trials(pkg)}${others(cur,pkg)}${legacy(pkg)}${freshness(pkg)}`;
}
function watch(){
  document.addEventListener("click",event=>{if(event.target.closest('.nav-item[data-page="watchtower"]'))setTimeout(()=>{try{render()}catch(error){console.error("[watchtower]",error)}},0)});
  if(location.hash==="#watchtower")setTimeout(render,0);
}
window.UIPWatchtower={render,state:S};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",watch);else watch();
})();
