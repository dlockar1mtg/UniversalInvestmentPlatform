/* The Universal Ledger: realm views drawn from the certified dashboard data.
   The Hall (home), the Treasury inventory (portfolio) and the Arcane Vault (crypto research).
   Read-only presentation: nothing here records, changes or executes anything. */
(()=>{
"use strict";
const state={home:null,catalog:null,catalogPromise:null,invFilter:"all",invPick:null,guild:null,guildPromise:null,guildPick:null,guildDetail:null,guildFilter:{family:"ALL",group:"",q:"",mine:false,best:false,buys:false,sort:"default",dir:"desc",cols:{},nums:{},limit:50}};
const byId=id=>document.getElementById(id);
const esc=value=>{const node=document.createElement("span");node.textContent=String(value??"");return node.innerHTML};
const num=value=>{if(value===null||value===undefined||value==="")return null;const n=Number(value);return Number.isFinite(n)?n:null};
const fmt=(n,d)=>Math.abs(n).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
const money=(value,d=2)=>{const n=num(value);return n===null?"\u2014":`${n<0?"\u2212":""}$${fmt(n,d)}`};
const signed=value=>{const n=num(value);return n===null?"\u2014":`${n>=0?"+":"\u2212"}$${fmt(n,2)}`};
const pct=(value,d=1)=>{const n=num(value);return n===null?"\u2014":`${n>=0?"+":"\u2212"}${Math.abs(n*100).toFixed(d)}%`};
const qty=value=>{const n=num(value);return n===null?"\u2014":n.toLocaleString("en-US",{maximumFractionDigits:8})};
const compact=n=>n>=1e6?`$${+(n/1e6).toFixed(1)}M`:n>=1e3?`$${+(n/1e3).toFixed(n>=1e4?0:1)}k`:`$${Math.round(n)}`;
const upDown=n=>n===null?"":n>=0?"rpg-up":"rpg-down";
const MONTHS=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const monthLabel=m=>{const s=String(m||"");return /^\d{4}-\d{2}/.test(s)?`${MONTHS[Number(s.slice(5,7))-1]} ${s.slice(0,4)}`:"\u2014"};
const dayLabel=v=>{const d=new Date(v);return Number.isNaN(d.getTime())?"\u2014":d.toLocaleDateString("en-US",{month:"short",day:"numeric",timeZone:"UTC"})};
const ordinal=n=>{const s=["th","st","nd","rd"],v=n%100;return n+(s[(v-20)%10]||s[v]||s[0])};
const longDate=()=>{const d=new Date();return `${d.toLocaleDateString("en-US",{weekday:"long"})}, the ${ordinal(d.getDate())} of ${d.toLocaleDateString("en-US",{month:"long"})}, ${d.getFullYear()}`};

const REALM={
  crypto:{name:"Arcane Vault",plain:"Crypto",color:"#2f5e8f",ink:"#9ec0ea"},
  metals:{name:"The Forge",plain:"Metals",color:"#b5862f",ink:"#e3c37e"},
  mtg:{name:"The Archive",plain:"MTG",color:"#6a4a8c",ink:"#c9b0e6"},
  etf:{name:"Merchants' Guild",plain:"ETFs",color:"#4d7a3a",ink:"#a9cf92"},
  acorns:{name:"The Coffer",plain:"Acorns",color:"#8c5a2b",ink:"#dba873"},
  retirement:{name:"The Reliquary",plain:"Retirement",color:"#3f6f6a",ink:"#9fd0c8"},
  purse:{name:"Coin purse",plain:"T-bills",color:"#7d7466",ink:"#cfc4ae"}
};
const COIN_NAMES={bitcoin:"Bitcoin",ethereum:"Ethereum",solana:"Solana",xrp:"XRP",chainlink:"Chainlink",avalanche:"Avalanche"};

async function api(path){
  const key=sessionStorage.getItem("uiip-dashboard-key")||"";
  const response=await fetch(path,{headers:{"X-API-Key":key,"Accept":"application/json"}});
  if(!response.ok)throw new Error(`Request failed (${response.status})`);
  return response.json();
}
function loadCatalog(){
  if(state.catalog)return Promise.resolve(state.catalog);
  if(!state.catalogPromise){
    state.catalogPromise=Promise.all(["crypto","metals"].map(domain=>api(`/v1/presentation/recommendation-catalog?domain=${domain}&limit=200&offset=0`).then(doc=>doc.items||[])))
      .then(([crypto,metals])=>(state.catalog={crypto,metals}))
      .catch(error=>{state.catalogPromise=null;throw error});
  }
  return state.catalogPromise;
}
function applyWidths(root){root.querySelectorAll("[data-rpg-w]").forEach(el=>{el.style.width=`${Math.max(0,Math.min(100,Number(el.dataset.rpgW)||0))}%`})}
function goPage(page){document.querySelector(`.nav-item[data-page="${page}"]`)?.click()}
function goResearch(domain,assetId){goPage("recommendations");setTimeout(()=>document.dispatchEvent(new CustomEvent("uip:open-research",{detail:{domain,asset_id:assetId||null}})),0)}
function bindNavigation(root){
  if(root.dataset.rpgBound)return;
  root.dataset.rpgBound="1";
  root.addEventListener("click",event=>{
    const target=event.target.closest("[data-rpg-page],[data-rpg-domain]");
    if(!target||!root.contains(target))return;
    event.preventDefault();
    if(target.dataset.rpgPage)goPage(target.dataset.rpgPage);
    else goResearch(target.dataset.rpgDomain,target.dataset.rpgAsset);
  });
}
/* Keep a page's realm view first and its original sections in a closed scroll below it; ids stay intact.
   Safe to run again: dashboard.js sometimes rebuilds a page or inserts a panel after the heading. */
function tuck(page,view,title,detail){
  const heading=page.querySelector(":scope > .page-heading");
  let scroll=page.querySelector(":scope > details.rpg-scroll");
  const viewPlaced=view.parentNode===page;
  const stray=[...page.children].filter(child=>child!==view&&child!==heading&&child!==scroll);
  if(!scroll){
    scroll=document.createElement("details");
    scroll.className="rpg-scroll";
    scroll.innerHTML=`<summary><span>${esc(title)}</span><small>${esc(detail)}</small></summary>`;
  }
  const top=stray.filter(child=>viewPlaced&&(child.compareDocumentPosition(view)&Node.DOCUMENT_POSITION_FOLLOWING));
  const summary=scroll.querySelector(":scope > summary");
  top.reverse().forEach(child=>scroll.insertBefore(child,summary?summary.nextSibling:scroll.firstChild));
  stray.filter(child=>!top.includes(child)).forEach(child=>scroll.appendChild(child));
  const wanted=heading?heading.nextElementSibling:page.firstElementChild;
  if(wanted!==view)page.insertBefore(view,heading?heading.nextSibling:page.firstChild);
  if(scroll.parentNode!==page||page.lastElementChild!==scroll)page.appendChild(scroll);
  page.classList.add("rpg-realm-on");
}
const HALL_SCROLL=["The steward's ledger","Certified totals, attention, domain health and authority"];
const TREASURY_SCROLL=["The counting house","Certified portfolio tables, Acorns, retirement statements and manual ETF entry"];
/* Re-apply the realm layout when dashboard.js rewrites Home or Portfolio after the last render. */
function guardRealmPage(id,viewId,render,scrollText){
  const page=byId(id);
  if(!page)return;
  let queued=false;
  new MutationObserver(()=>{
    if(queued)return;
    queued=true;
    queueMicrotask(()=>{
      queued=false;
      if(!state.home)return;
      try{const view=byId(viewId);if(view&&page.contains(view))tuck(page,view,scrollText[0],scrollText[1]);else render(state.home)}catch(error){console.error("[realm] guard",error)}
    });
  }).observe(page,{childList:true});
}

/* Icons */
const SIGIL=`<svg class="rpg-sigil" width="52" height="52" viewBox="0 0 52 52" fill="none" stroke="#d9b45a" stroke-width="1.6" aria-hidden="true"><path d="M26 3 L49 26 L26 49 L3 26 Z"/><path d="M26 11 L41 26 L26 41 L11 26 Z"/><circle cx="26" cy="26" r="5"/><path d="M26 3 V11 M49 26 H41 M26 49 V41 M3 26 H11"/></svg>`;
const LOCK=`<svg width="14" height="16" viewBox="0 0 14 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="1.5" y="7" width="11" height="8"/><path d="M4 7 V4.5 a3 3 0 0 1 6 0 V7"/></svg>`;
const ICON={
  relic:c=>`<svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><circle cx="20" cy="20" r="16" stroke="${c}" stroke-width="2.2"/><circle cx="20" cy="20" r="11" stroke="${c}" stroke-width="1.2" stroke-dasharray="2 2"/><path d="M14 20 L20 13 L26 20 L20 27 Z" stroke="${c}" stroke-width="1.6"/></svg>`,
  ingot:c=>`<svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M6 28 L11 16 H29 L34 28 Z" stroke="${c}" stroke-width="2.2"/><path d="M11 16 L14 10 H26 L29 16" stroke="${c}" stroke-width="1.4"/><path d="M15 22 H25" stroke="${c}" stroke-width="1.2"/></svg>`,
  charter:c=>`<svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M10 7 H27 a4 4 0 0 1 4 4 V31 a2 2 0 0 1 -2 2 H12 a4 4 0 0 1 -4 -4 V9 a2 2 0 0 1 2 -2 Z" stroke="${c}" stroke-width="2"/><path d="M13 14 H26 M13 19 H26 M13 24 H21" stroke="${c}" stroke-width="1.4"/><circle cx="25" cy="27" r="3" stroke="${c}" stroke-width="1.4"/></svg>`,
  tome:c=>`<svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M6 18 H34 V32 H6 Z" stroke="${c}" stroke-width="2.2"/><path d="M6 18 a14 9 0 0 1 28 0" stroke="${c}" stroke-width="2"/><rect x="17" y="18" width="6" height="7" stroke="${c}" stroke-width="1.4"/></svg>`,
  coffer:c=>`<svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><rect x="6" y="13" width="28" height="19" stroke="${c}" stroke-width="2.2"/><path d="M6 19 H34 M12 13 V32 M28 13 V32" stroke="${c}" stroke-width="1.3"/><path d="M17 8 H23 V13 H17 Z" stroke="${c}" stroke-width="1.4"/><circle cx="20" cy="24" r="2.4" stroke="${c}" stroke-width="1.4"/></svg>`,
  reliquary:c=>`<svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M10 5 H30 M10 35 H30" stroke="${c}" stroke-width="2.2"/><path d="M12 5 C12 14 18 16 18 20 C18 24 12 26 12 35 M28 5 C28 14 22 16 22 20 C22 24 28 26 28 35" stroke="${c}" stroke-width="2.2"/><path d="M15 31 C17 27 23 27 25 31 Z" fill="${c}"/></svg>`,
  purse:c=>`<svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M14 10 H26 L23 15 C31 18 33 25 31 30 C29 34 11 34 9 30 C7 25 9 18 17 15 Z" stroke="${c}" stroke-width="2"/><path d="M15 15 H25" stroke="${c}" stroke-width="1.4"/></svg>`
};
const swatch=color=>`<svg class="rpg-swatch" width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x=".5" y=".5" width="13" height="13" fill="${color}" stroke="#2a1d12"/></svg>`;
const footer=text=>`<p class="rpg-footnote">${esc(text)}</p>`;

function realmTabs(active){
  const tabs=[["hall","The Hall",'data-rpg-page="home"'],["treasury","Treasury",'data-rpg-page="portfolio"'],["metals","The Forge \u00b7 Metals",'data-rpg-domain="metals"'],["crypto","Arcane Vault \u00b7 Crypto",'data-rpg-domain="crypto"'],["mtg","The Archive \u00b7 MTG",'data-rpg-domain="mtg"'],["etf","Merchants' Guild \u00b7 ETFs",'data-rpg-page="guild"'],["homestead","The Homestead \u00b7 Plan",'data-rpg-page="homestead"'],["macro","The Watchtower \u00b7 Macro",'data-rpg-page="watchtower"']];
  return `<nav class="rpg-realms" aria-label="Realms">${tabs.map(([key,label,go])=>`<button type="button" class="rpg-btn rpg-realm${key===active?" is-active":""}" ${go}${key===active?' aria-current="page"':""}>${esc(label)}</button>`).join("")}</nav>`;
}

/* ---------- The Hall ---------- */
function retirementItems(d){return (d.retirementAccounts?.accounts||[]).filter(a=>a.category==="retirement"&&a.items?.length)}
const RET_SYMBOL={"retirement-401k":"401K",ira:"IRA",hsa:"HSA",pension:"PENSION"};
function realmTotals(d){
  const totals={mtg:0,crypto:0,metals:0,etf:0,acorns:0,purse:0,retirement:0};
  for(const p of d.portfolio?.positions||[]){
    const value=num(p.market_value)??0;
    if(p.domain_id==="metals"&&p.asset_subclass==="cash_proxy")totals.purse+=value;
    else if(totals[p.domain_id]!==undefined)totals[p.domain_id]+=value;
  }
  totals.etf=num(d.manualHoldings?.current_value)||0;
  const acorns=d.externalAccount?.items?.[0];
  totals.acorns=acorns?num(acorns.current_value)||0:0;
  totals.retirement=retirementItems(d).reduce((a,r)=>a+(num(r.estimate?.value??r.items[0].current_value)||0),0);
  return totals;
}
function chronicle(d){
  const s=d.snapshot||{};
  const gain=num(s.totalGain);
  const ret=num(s.totalReturn);
  return `<header class="rpg-stone rpg-chronicle"><div class="rpg-chronicle-id">${SIGIL}<div><div class="rpg-chronicle-title">The Universal Ledger</div><div class="rpg-chronicle-sub">Your investment journal \u00b7 ${esc(longDate())}</div></div></div><div class="rpg-chronicle-worth"><span>Treasury worth</span><strong>${money(s.totalValue)}</strong><small class="${upDown(gain)}">${signed(gain)}${ret===null?"":` \u00b7 ${pct(ret/100,2)}`} on ${money(s.totalBasis)} paid</small></div></header>`;
}
function vitals(refresh){
  const items=refresh?.items||[];
  const labels={crypto:"Crypto data",metals:"Metals data",mtg:"MTG data"};
  const rows=["crypto","metals","mtg"].map(id=>{
    const it=items.find(item=>item.domain_id===id);
    let fill=0,text="no report";
    if(it){
      const age=num(it.data_age_days),max=num(it.freshness_max_age_days);
      if(it.freshness_state==="UNKNOWN"){fill=0;text="unknown \u00b7 no data-as-of date"}
      else if(it.freshness_state==="STALE"){fill=12;text=`stale \u00b7 ${age} days old`}
      else{fill=age!==null&&max?Math.round(100-40*Math.max(0,age-1)/max):100;text=age===0?"fresh \u00b7 today":age===1?"fresh \u00b7 1 day old":`current \u00b7 ${age} days old`}
      if(it.health_state&&it.health_state!=="HEALTHY")text+=" \u00b7 needs review";
    }
    return `<div class="rpg-vital ${id}"><div class="rpg-vital-head"><span>${esc(labels[id])}</span><span>${esc(text)}</span></div><div class="rpg-bar ${id}" role="meter" aria-label="${esc(labels[id])} freshness" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${fill}"><i data-rpg-w="${fill}"></i></div></div>`;
  });
  const funds=state.guild?.available?state.guild.funds||[]:[];
  if(funds.length){const current=funds.filter(f=>f.freshness_state==="CURRENT").length,share=current/funds.length,asOf=state.guild.package?.package_as_of;const fill=Math.round(share*100);rows.push(`<div class="rpg-vital etf"><div class="rpg-vital-head"><span>ETF data</span><span>${esc(share>=0.9?`fresh \u00b7 ${current} of ${funds.length} funds \u00b7 ${dayLabel(asOf)}`:`needs review \u00b7 ${current} of ${funds.length} current`)}</span></div><div class="rpg-bar etf" role="meter" aria-label="ETF data freshness" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${fill}"><i data-rpg-w="${fill}"></i></div></div>`)}
  return `<section class="rpg-stone rpg-vitals" aria-label="Data vitals" data-rpg-page="refresh-page" title="Open Vitals">${rows.join("")}</section>`;
}
function treasuryRing(d){
  const totals=realmTotals(d);
  const order=["mtg","crypto","etf","acorns","retirement","metals","purse"];
  const entries=order.map(key=>[key,totals[key]]).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]);
  const sum=entries.reduce((a,[,v])=>a+v,0);
  const C=2*Math.PI*70;
  let offset=0;
  const arcs=entries.map(([key,v])=>{const len=Math.max(1.5,v/sum*C);const arc=`<circle cx="110" cy="110" r="70" stroke="${REALM[key].color}" stroke-dasharray="${len.toFixed(2)} ${C.toFixed(2)}" stroke-dashoffset="${(-offset).toFixed(2)}"/>`;offset+=v/sum*C;return arc}).join("");
  const share=v=>{const p=v/sum*100;return p<1?"<1%":`${Math.round(p)}%`};
  const aria=entries.map(([key,v])=>`${REALM[key].plain} ${share(v)}`).join(", ");
  const legend=entries.map(([key,v])=>`<div class="rpg-legend-row">${swatch(REALM[key].color)}<span class="rpg-legend-name">${esc(REALM[key].name)} \u00b7 ${esc(REALM[key].plain)}</span><span class="rpg-legend-value">${money(v)}</span><span class="rpg-legend-share">${share(v)}</span></div>`).join("");
  return `<section class="rpg-parch rpg-treasury" aria-labelledby="rpg-treasury-h"><h2 id="rpg-treasury-h" class="rpg-parch-title">The Treasury</h2><div class="rpg-treasury-body"><svg class="rpg-ring" width="220" height="220" viewBox="0 0 220 220" role="img" aria-label="Worth by realm: ${esc(aria)}"><g transform="rotate(-90 110 110)" fill="none" stroke-width="34">${arcs}</g><circle cx="110" cy="110" r="52" fill="none" stroke="#8a6a3a"/><circle cx="110" cy="110" r="88" fill="none" stroke="#8a6a3a"/><text x="110" y="104" text-anchor="middle" font-family="Cinzel, serif" font-size="13" fill="#5a3d1c" letter-spacing="2">WORTH</text><text x="110" y="128" text-anchor="middle" font-family="Cinzel, serif" font-size="22" font-weight="700" fill="#2a1d12">${esc(money(sum,0))}</text></svg><div class="rpg-legend">${legend}</div></div><p class="rpg-parch-note">Market value: certified prices for crypto, metals and MTG; ETFs at the Merchants' Guild close (provisional); your latest Acorns snapshot and retirement statements.</p><button type="button" class="rpg-btn rpg-link" data-rpg-page="portfolio">Open the inventory \u203a</button></section>`;
}
function badge(label,tone){return `<span class="rpg-badge rpg-badge-${tone}">${esc(label)}</span>`}
function callTone(call){return {ACCUMULATE:"azure",STEADY:"bronze",PAUSE:"crimson",BUY:"verdant",HOLD:"bronze"}[call]||"stone"}
function counselCards(d){
  const cat=state.catalog;
  if(!cat)return `<p class="rpg-parch-note">Consulting the oracles\u2026</p>`;
  const cards=[];
  for(const key of ["bitcoin","ethereum"]){
    const item=(cat.crypto||[]).find(i=>i.asset_id===`crypto:${key}`);
    const p=item?.payload;
    if(!p||p.model_version!=="crypto-v2")continue;
    const ratio=num(p.model_ratio_48m);
    const meaning={ACCUMULATE:"add more",STEADY:"keep buying steadily",PAUSE:"pause new buying"}[p.model_call]||"no call";
    cards.push(`<button type="button" class="rpg-btn rpg-counsel" data-rpg-domain="crypto" data-rpg-asset="crypto:${key}">${badge(p.model_call==="NO_CALL"?"NO CALL":String(p.model_call||"\u2014"),callTone(p.model_call))}<span><strong>${esc(COIN_NAMES[key])}: ${esc(meaning)}</strong><span>${ratio===null?"No ratio yet.":`Price is ${ratio.toFixed(2)}\u00d7 its 4-year average. Below 1\u00d7 says add more; 2\u00d7 and up says pause.`}</span></span></button>`);
  }
  const metals=(cat.metals||[]).filter(i=>String(i.payload?.recommendation||"").toLowerCase()==="buy").map(i=>i.asset_name);
  if(metals.length){const list=metals.length>1?`${metals.slice(0,-1).join(", ")} and ${metals[metals.length-1]}`:metals[0];cards.push(`<button type="button" class="rpg-btn rpg-counsel" data-rpg-domain="metals">${badge("BUY","verdant")}<span><strong>The Forge: ${esc(list)}</strong><span>The top three by expected 12-month return. Every other metal holds.</span></span></button>`)}
  const lairs=(d.portfolio?.positions||[]).filter(p=>p.domain_id==="mtg"&&p.recommendation==="BUY_CANDIDATE_NOW").length;
  const mtgHeld=(d.portfolio?.positions||[]).filter(p=>p.domain_id==="mtg").length;
  if(mtgHeld)cards.push(`<button type="button" class="rpg-btn rpg-counsel" data-rpg-domain="mtg">${badge(lairs?"BUY":"HOLD",lairs?"verdant":"bronze")}<span><strong>The Archive: ${lairs?`${lairs} of your Secret Lairs are buy candidates`:"hold the collection"}</strong><span>${lairs?"Listed below the model's buy price today. Check the live listing before buying.":"No buy signal on what you already hold."}</span></span></button>`);
  const funds=state.guild?.available?state.guild.funds||[]:[];
  if(funds.length){const mine=new Set((d.manualHoldings?.items||[]).filter(h=>h.asset_type==="ETF").map(h=>String(h.symbol).toUpperCase()));const moves=funds.filter(f=>mine.has(f.symbol)&&f.implementation?.call==="REDIRECT_NEW_MONEY");cards.push(`<button type="button" class="rpg-btn rpg-counsel" data-rpg-page="guild">${badge(moves.length?"REDIRECT":"STEADY",moves.length?"azure":"bronze")}<span><strong>Merchants' Guild: ${moves.length?esc(moves.map(f=>`${f.symbol} \u2192 ${f.implementation.to}`).join(", ")):"keep buying steadily"}</strong><span>${moves.length?"The same exposure, done better. Everything else: keep buying steadily.":"Your ETFs are already the best of their near-identical funds."}</span></span></button>`)}
  return cards.join("")||`<p class="rpg-parch-note">No active counsel.</p>`;
}
function tasks(d){
  const out=[];
  for(const it of d.refresh?.items||[]){
    const name=it.domain_id.toUpperCase();
    if(it.health_state!=="HEALTHY")out.push([false,`Review the ${name} run: ${it.failure_summary||"latest state needs review"}`]);
    else if(it.freshness_state==="STALE")out.push([false,`Refresh stale ${name} data`]);
    else if(it.freshness_state==="UNKNOWN")out.push([false,`Give ${name} data a governed as-of date`]);
  }
  const s=d.snapshot||{};
  const coverage=d.portfolio?.pricing_coverage;
  out.push([s.marketComplete!==false,s.marketComplete===false?`Price every holding (${coverage||"incomplete"})`:`Every certified holding is priced${coverage?` (${coverage})`:""}`]);
  out.push([s.basisComplete!==false,s.basisComplete===false?"Complete the cost basis":"Cost basis known for every holding"]);
  if(state.guild&&!state.guild.available)out.push([false,"Publish the first Merchants' Guild package (ETFs)"]);
  else if(state.guild?.available)out.push([true,"The Merchants' Guild is open: your ETFs are priced and counselled"]);
  const done=`<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="#4d7a3a" stroke-width="2" aria-hidden="true"><path d="M3 9 L7 13 L15 4"/></svg>`;
  const open=`<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="#8f2f24" stroke-width="2" aria-hidden="true"><rect x="2.5" y="2.5" width="13" height="13"/></svg>`;
  return `<ul class="rpg-tasks">${out.sort((a,b)=>Number(a[0])-Number(b[0])).map(([ok,text])=>`<li class="${ok?"is-done":""}">${ok?done:open}<span>${esc(text)}</span><span class="rpg-sr">${ok?"done":"open"}</span></li>`).join("")}</ul>`;
}
function questJournal(d){
  return `<section class="rpg-parch rpg-quests" id="rpg-quests" aria-labelledby="rpg-quests-h"><h2 id="rpg-quests-h" class="rpg-parch-title">Quest Journal</h2><div class="rpg-parch-kicker">Active counsel</div><div class="rpg-counsel-list">${counselCards(d)}</div><div class="rpg-parch-kicker">Tasks</div>${tasks(d)}</section>`;
}
function liveTransactions(items){
  const corrected=new Set(items.map(t=>t.corrects_transaction_id).filter(Boolean));
  return items.filter(t=>!corrected.has(t.transaction_id)).sort((a,b)=>String(b.occurred_at).localeCompare(String(a.occurred_at)));
}
function assetLabel(d,assetId){
  const p=(d.portfolio?.positions||[]).find(x=>x.asset_id===assetId);
  if(p&&p.asset_name)return p.asset_name;
  const tail=String(assetId||"").split(":").pop()||"";
  return COIN_NAMES[tail]||tail.toUpperCase()||"Unknown";
}
function recentDeeds(d){
  const rows=liveTransactions(d.transactions||[]).slice(0,6);
  const verb={BUY:"Acquired",SELL:"Sold",TRANSFER:"Moved",DIVIDEND:"Received",DEPOSIT:"Deposited",WITHDRAWAL:"Withdrew"};
  const body=rows.map(t=>{
    const q=num(t.quantity),price=num(t.price_per_unit),fees=num(t.fees)||0;
    const total=q!==null&&price!==null?q*price+(t.transaction_type==="SELL"?-fees:fees):null;
    return `<tr><td class="rpg-muted">${esc(dayLabel(t.occurred_at))}</td><td>${esc(verb[t.transaction_type]||String(t.transaction_type||"").toLowerCase())} <strong class="rpg-ink" data-rpg-ink="${t.domain_id}">${esc(assetLabel(d,t.asset_id))}</strong></td><td class="num">${esc(qty(t.quantity))}</td><td class="num">${money(price)}</td><td class="num rpg-gold">${money(total)}</td></tr>`;
  }).join("");
  return `<section class="rpg-stone rpg-deeds" aria-labelledby="rpg-deeds-h"><div class="rpg-section-head"><h2 id="rpg-deeds-h" class="rpg-stone-title">Recent deeds</h2><button type="button" class="rpg-btn rpg-link" data-rpg-page="transactions">Book of Deeds \u203a</button></div><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Day</th><th>Deed</th><th class="num">Quantity</th><th class="num">Price</th><th class="num">Gold spent</th></tr></thead><tbody>${body||`<tr><td colspan="5" class="rpg-muted">No deeds recorded yet.</td></tr>`}</tbody></table></div></section>`;
}
function renderHall(d){
  const page=byId("home");
  if(!page)return;
  let hall=byId("rpg-hall");
  if(!hall){hall=document.createElement("div");hall.id="rpg-hall";hall.className="rpg-realm-view";bindNavigation(hall)}
  tuck(page,hall,HALL_SCROLL[0],HALL_SCROLL[1]);
  hall.innerHTML=`${chronicle(d)}${realmTabs("hall")}${vitals(d.refresh)}<div class="rpg-duo">${treasuryRing(d)}${questJournal(d)}</div>${recentDeeds(d)}${footer("Research, not personal financial advice. No counsel here places a trade.")}`;
  applyWidths(hall);
  if(!state.guild)loadGuild().then(()=>{if(state.home===d)renderHall(d);renderInventory(d)}).catch(()=>{});
  if(!state.catalog)loadCatalog().then(()=>{const q=byId("rpg-quests");if(q&&state.home===d)q.outerHTML=questJournal(d)}).catch(()=>{const q=byId("rpg-quests");const list=q&&q.querySelector(".rpg-counsel-list");if(list)list.innerHTML=`<p class="rpg-parch-note">The oracles are silent: counsel could not be loaded.</p>`});
}

/* ---------- The Treasury: inventory ---------- */
const KIND={
  relic:{label:"Relic \u00b7 Arcane Vault (crypto)",color:"#7fa9dc",tab:"Relics"},
  ingot:{label:"Ingot \u00b7 The Forge (metals)",color:"#d9b45a",tab:"Ingots"},
  charter:{label:"Charter \u00b7 Merchants' Guild (ETF)",color:"#8fbf72",tab:"Charters"},
  tome:{label:"Tome \u00b7 The Archive (MTG)",color:"#b493d6",tab:"Tomes"},
  coffer:{label:"Coffer \u00b7 Acorns",color:"#dba873",tab:"Coffers"},
  reliquary:{label:"Reliquary \u00b7 retirement",color:"#9fd0c8",tab:"Reliquary"},
  purse:{label:"Coin purse \u00b7 T-bills",color:"#b9a98a",tab:"Purse"}
};
const CALL_TEXT={STEADY_ACCUMULATION:"Arcane Vault counsel: keep buying steadily.",ACCUMULATE:"Arcane Vault counsel: add more.",PAUSE_NEW_BUYING:"Arcane Vault counsel: pause new buying.",CONTEXT_ONLY_NO_CALL:"Context only: no call for this coin.",HOLD_NO_BUY_SIGNAL:"Hold: no buy signal today.",BUY_CANDIDATE_NOW:"Buy candidate: listed below the model's buy price today.",WAIT_FOR_LISTING_DISCOUNT:"Wait for a listing discount before buying more."};
function inventoryItems(d){
  const items=[];
  for(const p of d.portfolio?.positions||[]){
    if(p.domain_id==="mtg")continue;
    const kind=p.domain_id==="crypto"?"relic":p.asset_subclass==="cash_proxy"?"purse":"ingot";
    const unit=kind==="relic"?(p.asset_symbol||""):"shares";
    items.push({key:p.asset_id,symbol:p.asset_symbol||assetLabel(d,p.asset_id),name:p.asset_name||p.asset_symbol,kind,held:`${qty(p.quantity)} ${unit}`.trim(),paid:num(p.cost_basis),worth:num(p.market_value),avg:num(p.average_cost),account:p.account_id||"\u2014",note:CALL_TEXT[p.recommendation]||(p.recommendation?String(p.recommendation).replace(/_/g," ").toLowerCase():""),ledger:["ok","In the UIP ledger and priced by the certified authority"],domain:p.domain_id,asset:p.asset_id});
  }
  for(const h of d.manualHoldings?.items||[])items.push({key:`manual:${h.symbol}`,symbol:h.symbol,name:h.asset_name||h.symbol,kind:"charter",held:`${qty(h.shares)} shares`,paid:num(h.cost_basis),worth:num(h.current_value),avg:num(h.average_cost),account:h.notes||h.account_id||"\u2014",note:guildNote(h),ledger:h.valuation_source==="ETF_PACKAGE_CLOSE"?["ok",`Shares you entered, valued at the Merchants' Guild close of ${dayLabel(h.valuation_as_of)} (free public data, provisional)`]:["manual","Manual snapshot you entered; no usable close for this fund"],guild:true});
  const ac=d.externalAccount?.items?.[0];
  if(ac)items.push({key:"acorns",symbol:"ACORNS",name:"Acorns account",kind:"coffer",held:"1 account",paid:num(ac.contributed_basis),worth:num(ac.current_value),avg:null,account:ac.provider||"Acorns",note:`Snapshot of ${dayLabel(ac.as_of)}. ${ac.notes||""}`.trim(),ledger:["manual","Manual snapshot you entered from the Acorns app"]});
  for(const r of retirementItems(d)){const st=r.items[0],e=r.estimate||{},sc=r.schedule;const paid=st.basis_known?num(e.basis??st.contributed_basis):null;items.push({key:`retirement:${r.account_id}`,symbol:String(r.name||RET_SYMBOL[r.account_kind]||"RETIRE").toUpperCase().slice(0,12),name:r.name||r.account_label,kind:"reliquary",held:r.account_label,paid,worth:num(e.value??st.current_value),avg:null,account:r.account_label,note:`Balance of ${dayLabel(st.as_of)}${e.paychecks_since?`, plus ${e.paychecks_since} paycheck deposit${e.paychecks_since===1?"":"s"} since`:""}.${sc?` Deposits of ${money(num(sc.per_paycheck))} every ${sc.every_days} days.`:""}${st.basis_known?"":" Contributions not entered, so no gain is shown."} ${st.notes||""}`.trim(),ledger:["manual",e.paychecks_since?"Balance you entered, plus scheduled paycheck deposits (no market change assumed)":"Balance you entered from the statement or app"]})}
  const mtg=(d.portfolio?.positions||[]).filter(p=>p.domain_id==="mtg");
  const groups=[["BOXES","Collector booster boxes",p=>/COLLECTOR/.test(String(p.asset_subclass||p.asset_id))],["LAIRS","Secret Lair drops",p=>/SECRET_LAIR/.test(String(p.asset_subclass||p.asset_id))],["OTHER","Other sealed products",()=>true]];
  const used=new Set();
  for(const [symbol,name,test] of groups){
    const members=mtg.filter(p=>!used.has(p.asset_id)&&test(p));
    if(!members.length)continue;
    members.forEach(p=>used.add(p.asset_id));
    const count=members.reduce((a,p)=>a+(num(p.quantity)||0),0);
    const paid=members.reduce((a,p)=>a+(num(p.cost_basis)||0),0),worth=members.reduce((a,p)=>a+(num(p.market_value)||0),0);
    const buys=members.filter(p=>p.recommendation==="BUY_CANDIDATE_NOW").length;
    items.push({key:`mtg:${symbol}`,symbol,name,kind:"tome",count:String(count),held:`${count} ${symbol==="BOXES"?"boxes":"drops"}`,paid,worth,avg:count?paid/count:null,account:"Collection",note:`${members.length} product${members.length===1?"":"s"}${buys?`, ${buys} buy candidate${buys===1?"":"s"} today`:""}.`,ledger:["ok","In the UIP ledger and priced by the certified MTG authority"],members:members.map(p=>({name:p.asset_name,qty:num(p.quantity),worth:num(p.market_value),paid:num(p.cost_basis),call:p.recommendation})),domain:"mtg"});
  }
  const rank={relic:0,ingot:1,charter:2,coffer:3,reliquary:4,tome:5,purse:6};
  return items.sort((a,b)=>rank[a.kind]-rank[b.kind]||(b.worth||0)-(a.worth||0));
}
function guildNote(h){
  const f=(state.guild?.funds||[]).find(x=>x.symbol===String(h.symbol||"").toUpperCase());
  if(!f)return `Snapshot of ${dayLabel(h.as_of)}.`;
  const i=f.implementation||{};
  const parts=[i.call==="REDIRECT_NEW_MONEY"?`Merchants' Guild counsel: send new money to ${i.to}, the same exposure done better; these shares can stay.`:i.call==="BEST_IN_CLUSTER"?"Merchants' Guild counsel: the best of its near-identical funds; keep buying steadily.":"Merchants' Guild counsel: keep buying steadily."];
  if(f.when_to_buy?.verdict==="WAIT")parts.push(`The real-asset rule says wait for a ${Math.round(num(f.when_to_buy.parameter)*100)}% dip.`);
  return parts.join(" ");
}
const LEDGER_DOT={ok:"#4d7a3a",manual:"#b5862f",missing:"#8f2f24"};
function inventoryDetail(it){
  if(!it)return `<aside class="rpg-parch rpg-item-detail"><p class="rpg-parch-note">Pick an item to inspect it.</p></aside>`;
  const gain=it.paid!==null&&it.worth!==null?it.worth-it.paid:null;
  const ret=gain!==null&&it.paid?gain/it.paid:null;
  const stat=(label,value,extra="")=>`<div><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-value">${value}</div>${extra}</div>`;
  const members=it.members?`<div class="rpg-members">${it.members.slice().sort((a,b)=>(b.worth||0)-(a.worth||0)).map(m=>`<div class="rpg-member"><span>${esc(m.name)}${m.qty>1?` \u00d7${m.qty}`:""}</span><span class="num">${money(m.worth)}</span><span class="num ${upDown(m.worth!==null&&m.paid!==null?m.worth-m.paid:null)}">${m.worth!==null&&m.paid?pct((m.worth-m.paid)/m.paid,0):"\u2014"}</span></div>`).join("")}</div>`:"";
  const research=it.guild?`<button type="button" class="rpg-btn rpg-link rpg-link-ink" data-rpg-page="guild">Open the Merchants' Guild \u203a</button>`:it.domain?`<button type="button" class="rpg-btn rpg-link rpg-link-ink" data-rpg-domain="${esc(it.domain)}"${it.domain==="crypto"&&it.asset?` data-rpg-asset="${esc(it.asset)}"`:""}>Open the research \u203a</button>`:"";
  return `<aside class="rpg-parch rpg-item-detail" aria-labelledby="rpg-item-h" aria-live="polite"><div class="rpg-parch-kicker">${esc(KIND[it.kind].label)}</div><h2 id="rpg-item-h" class="rpg-item-name">${esc(it.name)}</h2><div class="rpg-rule"></div><div class="rpg-item-stats">${stat("Held",esc(it.held))}${stat("Gold paid",money(it.paid))}${stat("Worth now",money(it.worth),`<div class="rpg-stat-sub ${upDown(gain)}">${signed(gain)}${ret===null?"":` \u00b7 ${pct(ret)}`}</div>`)}${stat("Average cost",it.avg===null?"\u2014":money(it.avg))}${stat("Account",esc(it.account))}</div>${it.note?`<p class="rpg-item-note">${esc(it.note)}</p>`:""}${members}<div class="rpg-ledger-line"><svg width="10" height="10" aria-hidden="true"><rect width="10" height="10" fill="${LEDGER_DOT[it.ledger[0]]}"/></svg><span>${esc(it.ledger[1])}</span></div>${research}</aside>`;
}
function renderInventory(d){
  const page=byId("portfolio");
  if(!page)return;
  let view=byId("rpg-treasury");
  if(!view){view=document.createElement("div");view.id="rpg-treasury";view.className="rpg-realm-view";bindNavigation(view);
    view.addEventListener("click",event=>{const tab=event.target.closest("[data-rpg-filter]");const slot=event.target.closest("[data-rpg-item]");if(tab){state.invFilter=tab.dataset.rpgFilter;renderInventory(state.home)}else if(slot){state.invPick=slot.dataset.rpgItem;renderInventory(state.home);view.querySelector(`[data-rpg-item="${CSS.escape(state.invPick)}"]`)?.focus()}});}
  tuck(page,view,TREASURY_SCROLL[0],TREASURY_SCROLL[1]);
  const all=inventoryItems(d);
  const kinds=["relic","ingot","charter","tome","coffer","reliquary","purse"].filter(k=>all.some(i=>i.kind===k));
  if(state.invFilter!=="all"&&!kinds.includes(state.invFilter))state.invFilter="all";
  const shown=all.filter(i=>state.invFilter==="all"||i.kind===state.invFilter);
  if(!shown.some(i=>i.key===state.invPick))state.invPick=(shown.find(i=>i.kind==="relic")||shown[0]||{}).key||null;
  const pick=all.find(i=>i.key===state.invPick);
  const worth=all.reduce((a,i)=>a+(i.worth||0),0),paid=all.reduce((a,i)=>a+(i.kind==="reliquary"&&i.paid===null?(i.worth||0):(i.paid||0)),0);
  const tabs=[["all","All"],...kinds.map(k=>[k,KIND[k].tab])].map(([k,label])=>`<button type="button" class="rpg-btn rpg-tab${state.invFilter===k?" is-active":""}" data-rpg-filter="${k}" aria-pressed="${state.invFilter===k}">${esc(label)}</button>`).join("");
  const slots=shown.map(i=>{const selected=i.key===state.invPick;const gain=i.paid!==null&&i.worth!==null?i.worth-i.paid:null;return `<button type="button" class="rpg-btn rpg-slot${selected?" is-selected":""}" data-rpg-item="${esc(i.key)}" data-rpg-kind="${i.kind}" aria-pressed="${selected}" aria-label="${esc(`${i.name}, worth ${money(i.worth)}`)}"><span class="rpg-slot-top">${ICON[i.kind](KIND[i.kind].color)}<span class="rpg-slot-count num">${esc(i.count||"")}</span></span><span class="rpg-slot-symbol">${esc(i.symbol)}</span><span class="rpg-slot-worth num">${money(i.worth)}</span><span class="rpg-slot-gain num ${upDown(gain)}">${gain===null||!i.paid?"\u2014":pct(gain/i.paid)}</span></button>`}).join("");
  view.innerHTML=`<header class="rpg-stone rpg-crumbs"><nav aria-label="Breadcrumb"><button type="button" class="rpg-btn rpg-crumb" data-rpg-page="home">The Hall</button><span aria-hidden="true">\u203a</span><span class="rpg-crumb-here">Treasury</span></nav><div class="rpg-crumb-stats"><span>Items <strong class="num">${all.length}</strong></span><span>Worth <strong class="num">${money(worth)}</strong></span><span>Gold paid <strong class="num">${money(paid)}</strong></span></div></header>${realmTabs("treasury")}<div class="rpg-inventory-layout"><section class="rpg-stone rpg-inventory" aria-labelledby="rpg-inv-h"><div class="rpg-section-head"><h2 id="rpg-inv-h" class="rpg-stone-title">Inventory</h2><div class="rpg-tabs" role="group" aria-label="Filter by kind">${tabs}</div></div><div class="rpg-slots">${slots}</div></section>${inventoryDetail(pick)}</div>${footer("Quantities and amounts paid from the UIP ledger. ETF rows are the shares you entered, valued at the Merchants' Guild close; Acorns and the Reliquary are your own snapshots and statements.")}`;
}

/* ---------- The Arcane Vault: a coin's research page ---------- */
function vaultWhy(p,name){
  const r=num(p.model_ratio_48m),t=p.model_thresholds||{};
  const lo=num(t.accumulate_below)??1,hi=num(t.pause_from)??2;
  if(r===null)return `${name} has too little history for a 4-year average yet.`;
  const head=`The price is ${r.toFixed(2)}\u00d7 its average over the last four years.`;
  if(p.model_role!=="CORE")return `${head} The counsel gives no call for this coin; it is shown for context.`;
  if(r<lo)return `${head} That is below the average: the add-more zone.`;
  if(r<hi)return `${head} That is above the add-more zone and ${r<(lo+hi)/2+0.15?"well below":"approaching"} the ${hi}\u00d7 level where the counsel says to pause new money.`;
  return `${head} That is at or above ${hi}\u00d7, where the counsel says to pause new money.`;
}
function vaultRune(p){
  const r=num(p.model_ratio_48m);
  if(r===null)return "";
  const t=p.model_thresholds||{};const lo=num(t.accumulate_below)??1,hi=num(t.pause_from)??2;
  const top=Math.max(3,Math.ceil(r+0.25));
  const x=v=>20+960*Math.min(v,top)/top;
  const mark=x(r);
  const labelX=mark>860?mark-14:mark+14,anchor=mark>860?"end":"start";
  const ticks=Array.from({length:top+1},(_,i)=>`<text x="${x(i)}" y="84" text-anchor="${i===0?"start":i===top?"end":"middle"}" font-family="Alegreya, serif" font-size="16" fill="#5a4128">${i}\u00d7</text>`).join("");
  return `<section class="rpg-parch rpg-rune" aria-labelledby="rpg-rune-h"><h2 id="rpg-rune-h" class="rpg-parch-title">The Rune of Value \u00b7 price \u00f7 4-year average</h2><svg viewBox="0 0 1000 96" class="rpg-fluid" role="img" aria-label="Ratio ${r.toFixed(2)} on a scale from 0 to ${top}. Accumulate below ${lo}, steady from ${lo} to ${hi}, pause from ${hi}."><rect x="20" y="30" width="${x(lo)-20}" height="30" fill="#2f5e8f"/><rect x="${x(lo)}" y="30" width="${x(hi)-x(lo)}" height="30" fill="#b5862f"/><rect x="${x(hi)}" y="30" width="${980-x(hi)}" height="30" fill="#8f2f24"/><rect x="20" y="30" width="960" height="30" fill="none" stroke="#4a2f14" stroke-width="2"/><text x="${(20+x(lo))/2}" y="51" text-anchor="middle" font-family="Cinzel, serif" font-size="15" font-weight="700" fill="#f6e7c2" letter-spacing="2">ACCUMULATE</text><text x="${(x(lo)+x(hi))/2}" y="51" text-anchor="middle" font-family="Cinzel, serif" font-size="15" font-weight="700" fill="#1b140c" letter-spacing="2">STEADY</text><text x="${(x(hi)+980)/2}" y="51" text-anchor="middle" font-family="Cinzel, serif" font-size="15" font-weight="700" fill="#f6e7c2" letter-spacing="2">PAUSE</text>${ticks}<path d="M${mark} 24 L${mark+9} 10 L${mark-9} 10 Z" fill="#2a1d12"/><rect x="${mark-2}" y="24" width="4" height="42" fill="#2a1d12"/><text x="${labelX}" y="20" text-anchor="${anchor}" font-family="Cinzel, serif" font-size="18" font-weight="900" fill="#2a1d12">${r.toFixed(2)}\u00d7</text></svg></section>`;
}
function niceStep(range,count){const raw=range/count;const mag=10**Math.floor(Math.log10(raw));const n=raw/mag;return (n<1.5?1:n<3?2:n<7?5:10)*mag}
function vaultRoad(p,name){
  const hist=(p.model_price_history||[]).filter(r=>Array.isArray(r)&&num(r[1])!==null&&num(r[2])!==null).slice(-48);
  if(hist.length<6)return "";
  const prices=hist.map(r=>num(r[1])),avgs=hist.map(r=>num(r[2]));
  const yMax=Math.max(...prices,...avgs.map(a=>a*1.5))*1.08;
  const step=niceStep(yMax,6);
  const top=Math.ceil(yMax/step)*step;
  const X0=60,X1=860,Y0=16,Y1=296;
  const x=i=>X0+(X1-X0)*i/(hist.length-1);
  const y=v=>Math.max(Y0,Y1-(Y1-Y0)*v/top);
  const line=vals=>vals.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const avgLine=line(avgs),twoLine=line(avgs.map(a=>a*2));
  const back=vals=>vals.map((v,i)=>[i,v]).reverse().map(([i,v])=>`L${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const below=`${avgLine} L${X1},${Y1} L${X0},${Y1} Z`;
  const steady=`${twoLine} ${back(avgs)} Z`;
  const pause=`${twoLine} L${X1},${Y0} L${X0},${Y0} Z`;
  const grid=[];const labels=[];
  for(let v=step;v<=top;v+=step){grid.push(`M${X0} ${y(v).toFixed(1)} H${X1}`);labels.push(`<text x="52" y="${(y(v)+4).toFixed(1)}">${compact(v)}</text>`)}
  const months=hist.map(r=>String(r[0]));
  const xt=[0,Math.round((hist.length-1)/4),Math.round((hist.length-1)/2),Math.round(3*(hist.length-1)/4),hist.length-1];
  const xl=xt.map(i=>`<text x="${x(i).toFixed(0)}" y="318">${esc(monthLabel(months[i]))}</text>`).join("");
  const last=prices[prices.length-1];
  const ly=y(last);
  const ratio=num(p.model_ratio_48m);
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-road-h"><div class="rpg-section-head"><h2 id="rpg-road-h" class="rpg-stone-title">The Long Road \u00b7 ${hist.length} months of month-end prices</h2><div class="rpg-chart-key"><span><svg width="26" height="8" aria-hidden="true"><path d="M0 4 H26" stroke="#f1d78f" stroke-width="3"/></svg>Price</span><span><svg width="26" height="8" aria-hidden="true"><path d="M0 4 H26" stroke="#9ec0ea" stroke-width="2" stroke-dasharray="6 4"/></svg>4-year average</span><span><svg width="26" height="8" aria-hidden="true"><path d="M0 4 H26" stroke="#e08a7d" stroke-width="2" stroke-dasharray="2 4"/></svg>2\u00d7 average</span></div></div><svg viewBox="0 0 900 330" class="rpg-fluid" role="img" aria-label="${esc(`${name} month-end price from ${monthLabel(months[0])} to ${monthLabel(months[months.length-1])} against its 4-year average; ${ratio===null?"":`${ratio.toFixed(2)} times the average now`}.`)}"><path d="${below}" fill="#2f5e8f" fill-opacity=".28"/><path d="${steady}" fill="#b5862f" fill-opacity=".16"/><path d="${pause}" fill="#8f2f24" fill-opacity=".22"/><path d="${grid.join(" ")}" stroke="#4a3d2c"/><path d="M${X0} ${Y1} H${X1}" stroke="#7a6038" stroke-width="1.5"/><g font-family="Alegreya, serif" font-size="14" fill="#b9a98a" text-anchor="end">${labels.join("")}</g><g font-family="Alegreya, serif" font-size="14" fill="#b9a98a" text-anchor="middle">${xl}</g><path d="${twoLine}" fill="none" stroke="#e08a7d" stroke-width="2" stroke-dasharray="2 5"/><path d="${avgLine}" fill="none" stroke="#9ec0ea" stroke-width="2" stroke-dasharray="6 4"/><path d="${line(prices)}" fill="none" stroke="#f1d78f" stroke-width="3" stroke-linejoin="round"/><circle cx="${X1}" cy="${ly.toFixed(1)}" r="6" fill="#f1d78f" stroke="#231f1a" stroke-width="2"/><text x="${X1-8}" y="${(ly-13).toFixed(1)}" text-anchor="end" font-family="Cinzel, serif" font-size="15" font-weight="700" fill="#f1d78f">${esc(money(last,last>=100?0:2))}${ratio===null?"":` \u00b7 ${ratio.toFixed(2)}\u00d7`}</text><text x="${X0+10}" y="${Y1-12}" font-family="'Alegreya SC', serif" font-size="14" fill="#9ec0ea">accumulate zone</text><text x="${X0+10}" y="${((y(avgs[0])+y(avgs[0]*2))/2+5).toFixed(1)}" font-family="'Alegreya SC', serif" font-size="14" fill="#e3c37e">steady zone</text><text x="${X0+10}" y="${Y0+24}" font-family="'Alegreya SC', serif" font-size="14" fill="#e08a7d">pause zone</text></svg></section>`;
}
function vaultScrying(p){
  const proj=p.model_projection;
  const h12=proj?.horizons?.["12"],h24=proj?.horizons?.["24"];
  const now=num(proj?.price)??num(p.model_price_usd);
  if(!h12||!h24||now===null)return "";
  const all=[now,...["p10","p25","p50","p75","p90"].flatMap(k=>[num(h12.prices[k]),num(h24.prices[k])])].filter(v=>v!==null&&v>0);
  const lo=Math.min(...all)*0.88,hi=Math.max(...all)*1.12;
  const Y0=20,Y1=250;
  const y=v=>Y1-(Y1-Y0)*(Math.log(v)-Math.log(lo))/(Math.log(hi)-Math.log(lo));
  const X=[56,236,416];
  const band=(a,b)=>`M${X[0]},${y(now).toFixed(1)} L${X[1]},${y(h12.prices[b]).toFixed(1)} L${X[2]},${y(h24.prices[b]).toFixed(1)} L${X[2]},${y(h24.prices[a]).toFixed(1)} L${X[1]},${y(h12.prices[a]).toFixed(1)} Z`;
  const candidates=[1e3,2e3,5e3,1e4,2e4,4e4,6e4,1e5,2e5,3e5,5e5,1e6,2e6,5e6].concat([0.1,0.2,0.5,1,2,5,10,20,50,100,200,500]);
  const ticks=candidates.filter(v=>v>lo&&v<hi).sort((a,b)=>a-b);
  const thin=ticks.length>6?ticks.filter((_,i)=>i%2===0):ticks;
  const tickLabel=v=>v>=1e3?compact(v):`$${v}`;
  const status=String(proj.status||h12.kind||"").toUpperCase();
  const probability=(label,v)=>`<div class="rpg-inset"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${num(v)===null?"\u2014":`${Math.round(num(v)*100)}%`}</div></div>`;
  const short=v=>{const n=num(v);return n===null?"\u2014":n>=1e3?compact(n):money(n)};
  return `<section class="rpg-parch rpg-scrying" aria-labelledby="rpg-scry-h"><div class="rpg-section-head"><h2 id="rpg-scry-h" class="rpg-parch-title">The Scrying Pool \u00b7 12 and 24 months</h2>${badge(status==="VALIDATED"?"VALIDATED":status||"SCENARIO",status==="VALIDATED"?"azure":"stone")}</div><div class="rpg-scry-body"><svg viewBox="0 0 480 270" class="rpg-scry-chart" role="img" aria-label="${esc(`Range of simulated prices. In 12 months the middle is about ${short(h12.prices.p50)}, with 8 in 10 outcomes between ${short(h12.prices.p10)} and ${short(h12.prices.p90)}. In 24 months the middle is about ${short(h24.prices.p50)}, between ${short(h24.prices.p10)} and ${short(h24.prices.p90)}.`)}"><path d="${thin.map(v=>`M56 ${y(v).toFixed(1)} H430`).join(" ")}" stroke="#c8b183"/><g font-family="Alegreya, serif" font-size="15" fill="#6b4e2c" text-anchor="end">${thin.map(v=>`<text x="50" y="${(y(v)+4).toFixed(1)}">${esc(tickLabel(v))}</text>`).join("")}</g><path d="${band("p10","p90")}" fill="#2f5e8f" fill-opacity=".22"/><path d="${band("p25","p75")}" fill="#2f5e8f" fill-opacity=".38"/><path d="M${X[0]},${y(now).toFixed(1)} L${X[1]},${y(h12.prices.p50).toFixed(1)} L${X[2]},${y(h24.prices.p50).toFixed(1)}" fill="none" stroke="#1d3e63" stroke-width="3"/><path d="M236 20 V250 M416 20 V250" stroke="#8a6a3a" stroke-dasharray="3 4"/><circle cx="56" cy="${y(now).toFixed(1)}" r="5" fill="#2a1d12"/><g font-family="Alegreya, serif" font-size="15" fill="#2a1d12" text-anchor="middle"><text x="56" y="266">Today</text><text x="236" y="266">12 months</text><text x="416" y="266">24 months</text></g><text x="244" y="${(y(h12.prices.p50)-4).toFixed(1)}" font-family="Cinzel, serif" font-size="15" font-weight="700" fill="#1d3e63">${esc(short(h12.prices.p50))}</text><text x="424" y="${(y(h24.prices.p50)-4).toFixed(1)}" font-family="Cinzel, serif" font-size="15" font-weight="700" fill="#1d3e63">${esc(short(h24.prices.p50))}</text></svg><div class="rpg-scry-side">${probability("Higher in 12 months",h12.prob_up)}${probability("Higher in 24 months",h24.prob_up)}<p class="rpg-parch-note">Darker band: middle half of outcomes. Lighter band: 8 in 10.</p></div></div><p class="rpg-parch-note"><em>Simulated paths built from the coin's own past monthly moves, re-checked against how past forecasts actually landed.</em></p></section>`;
}
function vaultOmen(p){
  const st=p.model_short_term,f=st?.forecast;
  const prob=num(f?.probability_up);
  const theta=prob===null?Math.PI/2:Math.PI*(1-prob);
  const nx=150+98*Math.cos(theta),ny=150-98*Math.sin(theta);
  const needle=prob===null?`<path d="M150 150 L150 52" stroke="#8c7f68" stroke-width="3" stroke-dasharray="4 5"/>`:`<path d="M150 150 L${nx.toFixed(1)} ${ny.toFixed(1)}" stroke="#f1d78f" stroke-width="4" stroke-linecap="round"/>`;
  const reading=prob===null?"[ \u2014 ]":`${Math.round(prob*100)}%`;
  const copy=prob===null?`The chance this coin is higher 7 days from now. ${st?.latest_price_date?`No reading in this run (prices through ${st.latest_price_date}).`:"The first reading arrives with the next crypto run."}`:`The chance this coin is higher on ${f.target_date?dayLabel(`${f.target_date}T12:00:00Z`):"the target day"}, read on ${f.origin_date?dayLabel(`${f.origin_date}T12:00:00Z`):"\u2014"} from ${money(f.origin_price,0)}. It ${prob>=0.5?"leans up":"leans down or flat"}.`;
  return `<section class="rpg-stone rpg-omen" aria-labelledby="rpg-omen-h"><div class="rpg-section-head"><h2 id="rpg-omen-h" class="rpg-stone-title">Omen of the week</h2>${badge("CONTEXT ONLY","outline")}</div><svg viewBox="0 0 300 200" class="rpg-omen-gauge" role="img" aria-label="7-day chance-higher gauge: ${prob===null?"awaiting its first reading":`${Math.round(prob*100)} percent`}"><path d="M30 150 A120 120 0 0 1 270 150" fill="none" stroke="#3a3128" stroke-width="22"/><path d="M30 150 A120 120 0 0 1 150 30" fill="none" stroke="#8f2f24" stroke-opacity=".55" stroke-width="22"/><path d="M150 30 A120 120 0 0 1 270 150" fill="none" stroke="#2f5e8f" stroke-opacity=".7" stroke-width="22"/>${needle}<circle cx="150" cy="150" r="8" fill="#7a6038"/><text x="30" y="168" text-anchor="middle" font-family="Alegreya, serif" font-size="13" fill="#b9a98a">0%</text><text x="270" y="168" text-anchor="middle" font-family="Alegreya, serif" font-size="13" fill="#b9a98a">100%</text><text x="150" y="196" text-anchor="middle" font-family="Cinzel, serif" font-size="24" font-weight="700" fill="${prob===null?"#d8cbb0":"#f1d78f"}">${esc(reading)}</text></svg><p class="rpg-omen-copy">${esc(copy)}</p><p class="rpg-omen-note">${esc(st?.label||"This model passed one test of 60 forecasts (50% right against 37% for always guessing the usual direction).")} It never changes the call above.</p></section>`;
}
function vaultHoard(item){
  const d=state.home;
  const pos=(d?.portfolio?.positions||[]).find(p=>p.asset_id===item.asset_id);
  const sym=item.asset_symbol||String(item.asset_id).split(":").pop().toUpperCase();
  const stat=(label,value,sub="")=>`<div><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-value num">${value}</div>${sub}</div>`;
  if(!pos)return `<section class="rpg-parch rpg-hoard"><h2 class="rpg-parch-title">Your hoard</h2><p class="rpg-parch-note">${d?`None held yet.`:"Open The Hall once to load your holdings."}</p></section>`;
  const paid=num(pos.cost_basis),worth=num(pos.market_value),gain=paid!==null&&worth!==null?worth-paid:null;
  return `<section class="rpg-parch rpg-hoard" aria-labelledby="rpg-hoard-h"><h2 id="rpg-hoard-h" class="rpg-parch-title">Your hoard</h2>${stat("Held",`${esc(qty(pos.quantity))} ${esc(sym)}`)}${stat("Paid",money(paid),`<div class="rpg-stat-sub">avg ${esc(money(pos.average_cost,0))} a coin</div>`)}${stat("Worth now",money(worth),`<div class="rpg-stat-sub rpg-strong ${upDown(gain)}">${signed(gain)}${gain!==null&&paid?` \u00b7 ${pct(gain/paid)}`:""}</div>`)}</section>`;
}
function renderVault(page,item,p){
  const shell=page.querySelector(".rec-detail");
  if(!shell||!p||p.model_version!=="crypto-v2")return;
  const key=String(item.asset_id).split(":").pop();
  const name=COIN_NAMES[key]||item.asset_name||key;
  const tile=(label,value,sub="")=>`<div class="rpg-parch rpg-tile"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${value}</div>${sub?`<div class="rpg-stat-sub">${esc(sub)}</div>`:""}</div>`;
  const price=num(p.model_price_usd),avg=num(p.model_avg_48m_usd),dd=num(p.model_drawdown_from_peak),ch=num(p.model_change_12m);
  const m=v=>money(v,v!==null&&v>=100?0:2);
  const prior=price!==null&&ch!==null&&ch>-1?price/(1+ch):null;
  const call=String(p.model_call||"NO_CALL");
  const meaning={ACCUMULATE:"Add more",STEADY:"Keep buying steadily",PAUSE:"Pause new buying"}[call]||(p.model_role==="CORE"?"Not enough history for a call":"No call: context only");
  const role=p.model_role==="CORE"?"Core relic of the vault":"Satellite relic \u00b7 context only";
  const asOf=String(p.model_as_of||"").slice(0,10);
  const asOfLabel=asOf?new Date(`${asOf}T12:00:00Z`).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"}):"\u2014";
  const vault=document.createElement("div");
  vault.className="rpg-realm-view rpg-vault";
  vault.innerHTML=`<header class="rpg-stone rpg-crumbs"><nav aria-label="Breadcrumb"><button type="button" class="rpg-btn rpg-crumb" data-rpg-page="home">The Hall</button><span aria-hidden="true">\u203a</span><button type="button" class="rpg-btn rpg-crumb rpg-crumb-azure" data-rpg-vault-back>Arcane Vault</button><span aria-hidden="true">\u203a</span><span class="rpg-crumb-here">${esc(name)}</span></nav><span class="rpg-crumb-note">Kraken prices as of ${esc(asOfLabel)}</span></header>${realmTabs("crypto")}<section class="rpg-stone rpg-vault-hero"><div class="rpg-vault-call"><div class="rpg-vault-id"><svg width="64" height="64" viewBox="0 0 64 64" fill="none" aria-hidden="true"><circle cx="32" cy="32" r="29" stroke="#d9b45a" stroke-width="2"/><circle cx="32" cy="32" r="23" stroke="#7a6038" stroke-width="1.5"/><path d="M32 14 L46 32 L32 50 L18 32 Z" stroke="#f1d78f" stroke-width="2.2"/><path d="M32 22 L39 32 L32 42 L25 32 Z" stroke="#f1d78f" stroke-width="1.4"/></svg><div><h1 class="rpg-vault-name">${esc(name)}</h1><div class="rpg-vault-role">${esc(role)}${p.model_robinhood_tradable?" \u00b7 tradable on Robinhood":""}</div></div></div><div class="rpg-vault-verdict"><span class="rpg-seal rpg-seal-${callTone(call)}">${esc(call==="NO_CALL"?"NO CALL":call)}</span><span>${esc(meaning)}</span></div><p class="rpg-vault-why">${esc(vaultWhy(p,name))}</p></div><div class="rpg-tiles">${tile("Price",m(price))}${tile("4-year average",m(avg))}${tile("From its peak",dd===null?"\u2014":`${dd<0?"\u2212":"+"}${Math.abs(Math.round(dd*100))}%`,`peak ${m(num(p.model_peak_usd))} \u00b7 ${monthLabel(p.model_peak_month)}`)}${tile("Past 12 months",ch===null?"\u2014":`${ch<0?"\u2212":"+"}${Math.abs(Math.round(ch*100))}%`,prior===null?"":`from ${m(prior)}`)}</div></section>${vaultRune(p)}${vaultRoad(p,name)}<div class="rpg-duo">${vaultScrying(p)}${p.model_short_term||key==="bitcoin"||key==="ethereum"?vaultOmen(p):""}</div><div id="rpg-hoard-slot">${vaultHoard(item)}</div><h2 class="rpg-notes-title">Scholar's notes</h2>`;
  shell.insertBefore(vault,shell.firstChild);
  shell.classList.add("rpg-vault-on");
  bindNavigation(vault);
  vault.querySelector("[data-rpg-vault-back]")?.addEventListener("click",()=>page.querySelector("#cv-v2-back")?.click());
  shell.insertAdjacentHTML("beforeend",footer("Timing counsel for new money, not a price forecast. Research, not personal financial advice."));
  state.vault={item};
}

/* ---------- Counsel: a realm bar above every research view ---------- */
const COUNSEL_REALM={metals:["The Forge","Metals research"],mtg:["The Archive","MTG research"],crypto:["Arcane Vault","Crypto research"]};
function counselRealm(page){
  const eyebrow=String(page.querySelector(".eyebrow")?.textContent||"").toUpperCase();
  if(/METAL/.test(eyebrow))return "metals";
  if(/MTG/.test(eyebrow))return "mtg";
  if(/CRYPTO/.test(eyebrow))return "crypto";
  return null;
}
function decorateCounsel(){
  const page=byId("recommendations");
  if(!page||page.querySelector(":scope > .rpg-counsel-bar")||page.querySelector(".rpg-vault"))return;
  if(!page.querySelector(".eyebrow"))return;
  const domain=counselRealm(page);
  const detail=page.querySelector(".rec-detail");
  const title=detail?String(detail.querySelector(".rec-detail-title h2")?.firstChild?.textContent||"").trim():"";
  const sep=`<span aria-hidden="true">\u203a</span>`;
  const crumbs=[`<button type="button" class="rpg-btn rpg-crumb" data-rpg-page="home">The Hall</button>`,sep];
  if(domain){
    const [name]=COUNSEL_REALM[domain];
    crumbs.push(detail&&title?`<button type="button" class="rpg-btn rpg-crumb" data-rpg-domain="${domain}">${esc(name)}</button>`:`<span class="rpg-crumb-here">${esc(name)}</span>`);
    if(detail&&title)crumbs.push(sep,`<span class="rpg-crumb-here">${esc(title)}</span>`);
  }else crumbs.push(`<span class="rpg-crumb-here">Counsel</span>`);
  const bar=document.createElement("div");
  bar.className="rpg-realm-view rpg-counsel-bar";
  bar.innerHTML=`<header class="rpg-stone rpg-crumbs"><nav aria-label="Breadcrumb">${crumbs.join("")}</nav><span class="rpg-crumb-note">${esc(domain?COUNSEL_REALM[domain][1]:"Research across every realm")} \u00b7 research, not orders</span></header>${realmTabs(domain||"counsel")}`;
  bindNavigation(bar);
  page.insertBefore(bar,page.firstChild);
}
function watchCounsel(){
  const page=byId("recommendations");
  if(!page)return;
  let queued=false;
  new MutationObserver(()=>{if(queued)return;queued=true;queueMicrotask(()=>{queued=false;try{decorateCounsel()}catch(error){console.error("[realm] counsel",error)}})}).observe(page,{childList:true});
  decorateCounsel();
}
/* ---------- The Merchants' Guild: the ETF market board ---------- */
const FAMILY_NAME={US_EQUITY:"US stocks",INTL_EQUITY:"International stocks",BONDS:"Bonds",OTHER:"Real assets",NONE:"Specialized / ungrouped"};
const GROUP_WORDS={US_EQUITY_LARGE_BLEND:"US large cap",US_EQUITY_LARGE_GROWTH:"US large growth",US_EQUITY_LARGE_VALUE:"US large value",US_EQUITY_SMALL_MID:"US small & mid cap",US_EQUITY_DEFENSIVE_INCOME:"US defensive & income",INTL_DEVELOPED_EQUITY:"Developed markets",INTL_EMERGING_EQUITY:"Emerging markets",BOND_SHORT_TREASURY:"Short-term bonds",BOND_INTERMEDIATE_TREASURY:"Core & intermediate bonds",BOND_LONG_TREASURY:"Long-term Treasuries",BOND_INVESTMENT_GRADE_CORPORATE:"Corporate bonds",BOND_HIGH_YIELD:"High-yield bonds",BOND_INFLATION_PROTECTED:"Inflation-protected bonds",BOND_MUNICIPAL:"Municipal bonds",BOND_CASH_EQUIVALENT:"Cash & T-bills",PRECIOUS_METALS:"Precious metals",COMMODITIES:"Commodities",REAL_ESTATE:"Real estate",IDIOSYNCRATIC:"Ungrouped (no close match)",SPECIALIZED_LEVERAGED:"Leveraged",SPECIALIZED_INVERSE:"Inverse",INSUFFICIENT_HISTORY:"Too new to group",NOT_RANKED_OUTSIDE_MODEL:"Outside the model universe"};
const groupName=g=>GROUP_WORDS[g]||(String(g||"").startsWith("US_SECTOR_")?`${String(g).slice(10).toLowerCase().replace(/_/g," ")} sector`.replace(/^./,c=>c.toUpperCase()):String(g||"\u2014").toLowerCase().replace(/_/g," "));
const RULE_NAMES={TREND_PAUSE:"Pause below the trend",STRETCH_PAUSE:"Pause when stretched",WAIT_FOR_DIP:"Wait for a dip",MOMENTUM_PAUSE:"Pause after a losing year"};
const FACTOR_NAMES={mom_12_1:"12-month momentum",mom_6:"6-month momentum",trend_200:"Price vs 200-day average",stretch_60m:"Stretch vs 5-year average",vol_1y:"Volatility",maxdd_3y:"Worst fall, 3 years",dd_now:"Distance from peak",yield_12m:"Distribution yield"};
function loadGuild(){
  if(state.guild)return Promise.resolve(state.guild);
  if(!state.guildPromise)state.guildPromise=api("/v1/presentation/etf").then(doc=>(state.guild=doc)).catch(error=>{state.guildPromise=null;throw error});
  return state.guildPromise;
}
function guildHoldings(){
  const out={};
  for(const h of state.home?.manualHoldings?.items||[]){
    if(h.asset_type!=="ETF")continue;
    const key=String(h.symbol||"").toUpperCase();
    const o=out[key]||(out[key]={shares:0,paid:0,worth:0,marked:true,asOf:null});
    o.shares+=num(h.shares)||0;o.paid+=num(h.cost_basis)||0;o.worth+=num(h.current_value)||0;
    o.marked=o.marked&&h.valuation_source==="ETF_PACKAGE_CLOSE";o.asOf=h.valuation_as_of||o.asOf;
  }
  return out;
}
function whenText(w){
  if(!w)return ["\u2014","stone","No family reading"];
  if(w.verdict==="WAIT")return ["WAIT","crimson",`Wait for a ${Math.round(num(w.parameter)*100)}% dip`];
  if(w.verdict==="BUY_NOW")return ["BUY NOW","verdant","The family is in its buy zone"];
  return ["STEADY","bronze","Keep buying steadily"];
}
function implText(f){
  const i=f.implementation||{};
  if(i.call==="REDIRECT_NEW_MONEY")return [`\u2192 ${i.to}`,"azure",`Same exposure as ${i.to}, which has done it better`];
  if(i.call==="BEST_IN_CLUSTER")return ["BEST","verdant","The best of its near-identical funds"];
  return ["\u2014","stone","No near-identical fund"];
}
function callText(f){const c=f.ranking_call;const m={BUY:["BUY","verdant","Among the cheapest fifth of its peers"],ACCUMULATE:["ACCUMULATE","azure","Cheaper than most of its peers"],HOLD:["HOLD","bronze","Middling cost for its peer group"],AVOID:["AVOID","crimson","Among the costliest fifth of its peers"]};return m[c]||["\u2014","stone",c==="NOT_RANKED_OUTSIDE_MODEL"?"Outside the model universe":c==="RANKED_NO_CALL"?"No official fee on file":"No call for specialized or ungrouped funds"]}
function looseWhy(f){
  const r=f.loose_peer_reading;
  const base=f.peer_group==="SPECIALIZED_LEVERAGED"||f.peer_group==="SPECIALIZED_INVERSE"?"Leveraged and inverse funds get no call: the 3-year cost evidence was measured on proper peer groups.":f.peer_group==="IDIOSYNCRATIC"?"This fund has no proper peer group, so it gets no call: the 3-year cost evidence was measured on proper peer groups.":"Specialized, ungrouped and outside-universe funds get no call.";
  if(!r)return base;
  const fee=num(f.expense_ratio)===null?"":` (${(num(f.expense_ratio)*100).toFixed(2)}% a year)`;
  const who=r.basis==="LOOSE_PEERS"?`the ${groupName(r.peer_group)} funds it most resembles (it tracks ${r.nearest_reference} at ${num(r.correlation)===null?"a loose":num(r.correlation).toFixed(2)} correlation)`:`the other ${r.peer_group==="SPECIALIZED_INVERSE"?"inverse":"leveraged"} funds`;
  return num(r.cost_percentile)===null?`${base} There are too few priced funds like it for a cost reading.`:`${base} As a reading only: its official fee${fee} is cheaper than ${Math.round(num(r.cost_percentile))}% of ${who}.`;
}
const CALL_ORDER={BUY:0,ACCUMULATE:1,HOLD:2,AVOID:3};
function guildFamily(f){return f.group_family||"NONE"}
/* The Market Board works like a spreadsheet: click a header to sort (again to flip), filter any column. */
const fromHigh=f=>num(f.drawdown_3y_high)!==null?num(f.drawdown_3y_high):num(f.drawdown_now);
const projP50=f=>num(f.projection_3y?.p50)??num(f.outlook_3y?.p50);
const callLabel=f=>CALL_ORDER[f.ranking_call]===undefined?"No call":callText(f)[0];
const BOARD_COLS=[
  {k:"fund",label:"Fund",text:true,val:f=>String(f.symbol)},
  {k:"group",label:"Peer group",text:true,cat:f=>groupName(f.peer_group),val:f=>groupName(f.peer_group)},
  {k:"close",label:"Close",val:f=>num(f.close)},
  {k:"1y",label:"1 year",pct:true,val:f=>num(f.return_1y)},
  {k:"3y",label:"3 years, a year",pct:true,val:f=>num(f.annualized_3y)},
  {k:"p3y",label:"Next 3 years, typical",pct:true,val:projP50},
  {k:"peak",label:"From 3-year high",pct:true,val:fromHigh},
  {k:"yield",label:"Yield",pct:true,val:f=>num(f.yield_12m)},
  {k:"fee",label:"Fee",pct:true,val:f=>num(f.expense_ratio)},
  {k:"call",label:"Call",cat:callLabel,val:f=>CALL_ORDER[f.ranking_call]===undefined?null:-CALL_ORDER[f.ranking_call]+(num(f.cost_percentile_in_group)??0)/1000,order:["BUY","ACCUMULATE","HOLD","AVOID","No call"]},
  {k:"which",label:"Which fund",cat:f=>implText(f)[0],val:f=>implText(f)[0]==="REDIRECT"?0:1},
  {k:"when",label:"When",cat:f=>whenText(f.when_to_buy)[0],val:f=>({"BUY NOW":2,STEADY:1,WAIT:0})[whenText(f.when_to_buy)[0]]??null},
  {k:"worth",label:"Your worth",val:(f,h)=>h[f.symbol]?num(h[f.symbol].worth):null},
];
/* "> 5", ">= 5", "< 0.5", "5..10", "5 to 10" or a plain number (at least). Percent columns read in percent. */
function parseNumFilter(text,isPct){
  const t=String(text||"").trim().replace(/[%$,\s]/g,"").toLowerCase();if(!t)return null;
  const scale=v=>isPct?v/100:v;
  let m=t.match(/^(-?\d*\.?\d+)(?:\.\.|to)(-?\d*\.?\d+)$/);
  if(m){const a=scale(Number(m[1])),b=scale(Number(m[2]));return v=>v!==null&&v>=Math.min(a,b)&&v<=Math.max(a,b)}
  m=t.match(/^(>=|<=|>|<|=)?(-?\d*\.?\d+)$/);
  if(!m)return undefined;
  const x=scale(Number(m[2])),op=m[1]||">=";
  return v=>v!==null&&(op===">"?v>x:op===">="?v>=x:op==="<"?v<x:op==="<="?v<=x:Math.abs(v-x)<1e-9);
}
function guildFiltered(funds,held){
  const st=state.guildFilter;
  const q=st.q.trim().toUpperCase();
  const cats=BOARD_COLS.filter(c=>c.cat&&(st.cols[c.k]||[]).length).map(c=>[c,new Set(st.cols[c.k])]);
  const nums=BOARD_COLS.filter(c=>!c.text&&!c.cat&&st.nums[c.k]).map(c=>[c,parseNumFilter(st.nums[c.k],c.pct)]).filter(([,fn])=>typeof fn==="function");
  let out=funds.filter(f=>(st.family==="ALL"||(!st.family?guildFamily(f)!=="NONE"||!!held[f.symbol]:guildFamily(f)===st.family))&&(!st.group||f.peer_group===st.group)&&(!st.mine||held[f.symbol])&&(!st.buys||f.ranking_call==="BUY")&&(!st.best||f.implementation?.call==="BEST_IN_CLUSTER"||f.implementation?.call==="NO_NEAR_DUPLICATE")&&(!q||String(f.symbol).includes(q)||String(f.name||"").toUpperCase().includes(q))
    &&cats.every(([c,set])=>set.has(c.cat(f)))&&nums.every(([c,fn])=>fn(c.val(f,held))));
  if(st.sort==="default")return out.slice().sort((a,b)=>(held[b.symbol]?1:0)-(held[a.symbol]?1:0)||groupName(a.peer_group).localeCompare(groupName(b.peer_group))||(num(b.annualized_3y)??-9)-(num(a.annualized_3y)??-9));
  const col=BOARD_COLS.find(c=>c.k===st.sort)||BOARD_COLS[0],dir=st.dir==="asc"?1:-1;
  return out.slice().sort((a,b)=>{const x=col.val(a,held),y=col.val(b,held);
    if(col.text)return dir*String(x).localeCompare(String(y))||String(a.symbol).localeCompare(String(b.symbol));
    if(x===null&&y===null)return String(a.symbol).localeCompare(String(b.symbol));if(x===null)return 1;if(y===null)return -1;   // blanks last either way
    return dir*(x-y)||String(a.symbol).localeCompare(String(b.symbol))});
}
function guildHeader(funds,held){
  const st=state.guildFilter;
  const has3y=funds.some(f=>num(f.drawdown_3y_high)!==null);
  const head=BOARD_COLS.map(c0=>{const c=c0.k==="peak"&&!has3y?{...c0,label:"From peak"}:c0;const on=st.sort===c.k,arrow=on?(st.dir==="asc"?" \u25b2":" \u25bc"):"";const aria=on?(st.dir==="asc"?"ascending":"descending"):"none";
    return `<th class="${c.text||c.cat?"":"num"}" aria-sort="${aria}"><button type="button" class="rpg-btn rpg-sort${on?" is-on":""}" data-rpg-sort="${c.k}" title="Sort by ${esc(c.label)}${on?`, ${st.dir==="asc"?"low to high":"high to low"} (click to flip)`:""}">${esc(c.label)}<span aria-hidden="true">${arrow}</span></button></th>`}).join("");
  const base=funds.filter(f=>st.family==="ALL"||(!st.family?guildFamily(f)!=="NONE"||!!held[f.symbol]:guildFamily(f)===st.family));
  const filt=BOARD_COLS.map(c=>{
    if(c.k==="fund")return `<td><input type="search" class="rpg-colfilter-text" data-rpg-filter-key="q" value="${esc(st.q)}" placeholder="Symbol or name" aria-label="Filter funds by symbol or name" autocomplete="off"></td>`;
    if(c.cat){const vals=[...new Set(base.map(c.cat))].sort((a,b)=>c.order?c.order.indexOf(a)-c.order.indexOf(b):String(a).localeCompare(String(b)));const sel=new Set(st.cols[c.k]||[]);
      const label=!sel.size?"All":sel.size===1?[...sel][0]:`${sel.size} chosen`;
      return `<td><details class="rpg-colfilter"${state.guildOpenFilter===c.k?" open":""} data-rpg-colfilter="${c.k}"><summary aria-label="Filter ${esc(c.label)}">${esc(label)} \u25be</summary><div class="rpg-colfilter-menu" role="group" aria-label="${esc(c.label)} values">${vals.map(v=>`<label class="rpg-check"><input type="checkbox" data-rpg-col="${c.k}" value="${esc(v)}"${sel.has(v)?" checked":""}> ${esc(v)}</label>`).join("")}${sel.size?`<button type="button" class="rpg-btn rpg-link" data-rpg-col-clear="${c.k}">Show all</button>`:""}</div></details></td>`}
    if(c.text)return "<td></td>";
    const bad=st.nums[c.k]&&parseNumFilter(st.nums[c.k],c.pct)===undefined;
    return `<td class="num"><input type="text" inputmode="decimal" class="rpg-colfilter-num${bad?" is-bad":""}" data-rpg-num="${c.k}" value="${esc(st.nums[c.k]||"")}" placeholder="${c.k==="fee"?"< 0.2":c.pct?"> 5":"> 100"}" aria-label="Filter ${esc(c.label)}${c.pct?" (in percent)":""}, for example > 5 or 2..8" title="> 5, < 0.5, 2..8${c.pct?" (percent)":""}"></td>`}).join("");
  return `<thead><tr>${head}</tr><tr class="rpg-colfilters">${filt}</tr></thead>`;
}
function guildBoardRows(funds,held){
  const st=state.guildFilter;
  const shown=guildFiltered(funds,held);
  const page=shown.slice(0,st.limit);
  const cell=v=>{const n=num(v);return `<td class="num ${upDown(n)}">${pct(n)}</td>`};
  const rows=page.map(f=>{const [il,it]=implText(f);const [wl,wt]=whenText(f.when_to_buy);const h=held[f.symbol];
    const peak=fromHigh(f);
    return `<tr class="${f.symbol===state.guildPick?"is-picked":""}${h?" is-mine":""}"><th scope="row"><button type="button" class="rpg-btn rpg-fund-pick" data-rpg-fund="${esc(f.symbol)}" aria-pressed="${f.symbol===state.guildPick}"><strong>${esc(f.symbol)}${h?" \u2726":""}</strong><span>${esc(f.name||"")}</span></button></th><td>${esc(groupName(f.peer_group))}</td><td class="num">${money(f.close)}</td>${cell(f.return_1y)}${cell(f.annualized_3y)}${projCell(f)}${peak!==null&&peak>-0.0005?`<td class="num rpg-up">at high</td>`:cell(peak)}<td class="num">${num(f.yield_12m)===null?"\u2014":`${(num(f.yield_12m)*100).toFixed(2)}%`}</td><td class="num">${num(f.expense_ratio)===null?"\u2014":`${(num(f.expense_ratio)*100).toFixed(2)}%`}</td><td class="rpg-nowrap">${badge(callText(f)[0],callText(f)[1])}</td><td class="rpg-nowrap">${badge(il,it)}</td><td class="rpg-nowrap">${badge(wl,wt)}</td><td class="num">${h?money(h.worth):"\u2014"}</td></tr>`}).join("");
  const more=shown.length>page.length?`<button type="button" class="rpg-btn rpg-link" data-rpg-more>Show ${Math.min(50,shown.length-page.length)} more of ${shown.length-page.length} \u203a</button>`:"";
  const active=Object.values(st.cols).some(v=>(v||[]).length)||Object.values(st.nums).some(Boolean)||st.q;
  const projNote=st.sort==="p3y"?`<p class="rpg-item-note rpg-board-note">${esc("Sorted by the typical 3-year figure. Within a peer group a higher figure mostly means a fund that swings more than its peers, which did not pay more in the Guild's trials; figures marked \u00b0 come from a fund's own history alone and are weaker still. Read the bad case on each fund's page before buying.")}</p>`:"";
  return `<div class="rpg-board-count"><span class="rpg-crumb-note">${shown.length} of ${funds.length} funds${st.sort!=="default"?` \u00b7 sorted by ${esc((BOARD_COLS.find(c=>c.k===st.sort)||{}).label||"")}, ${st.dir==="asc"?"low to high":"high to low"}`:""}</span>${active||st.sort!=="default"?`<button type="button" class="rpg-btn rpg-link" data-rpg-board-reset>Clear sort and filters</button>`:""}</div>${projNote}<div class="rpg-table-wrap"><table class="rpg-table rpg-guild-table">${guildHeader(funds,held)}<tbody>${rows||`<tr><td colspan="13" class="rpg-muted">No fund matches these filters.</td></tr>`}</tbody></table></div>${more}`;
}
function guildBoard(funds,held){
  const st=state.guildFilter;
  const fams=["US_EQUITY","INTL_EQUITY","BONDS","OTHER","NONE"].filter(k=>funds.some(f=>guildFamily(f)===k));
  const groups=[...new Set(funds.filter(f=>st.family==="ALL"||(!st.family?guildFamily(f)!=="NONE":guildFamily(f)===st.family)).map(f=>f.peer_group))].sort((a,b)=>groupName(a).localeCompare(groupName(b)));
  const opt=(v,label,cur)=>`<option value="${esc(v)}"${v===cur?" selected":""}>${esc(label)}</option>`;
  return `<section class="rpg-stone rpg-guild-ledger" aria-labelledby="rpg-board-h"><div class="rpg-section-head"><h2 id="rpg-board-h" class="rpg-stone-title">The Market Board</h2><span class="rpg-crumb-note">Total return, distributions reinvested</span></div><div class="rpg-board-filters" role="search"><label>Family <select data-rpg-filter-key="family">${opt("ALL",`All ${funds.length} funds`,st.family)}${opt("","Grouped funds only (hides specialized)",st.family)}${fams.map(k=>opt(k,FAMILY_NAME[k],st.family)).join("")}</select></label>${st.group?`<label class="rpg-check"><input type="checkbox" data-rpg-filter-key="group" value="" checked> Only ${esc(groupName(st.group))}</label>`:""}<label class="rpg-check"><input type="checkbox" data-rpg-filter-key="mine"${st.mine?" checked":""}> Your funds</label><label class="rpg-check"><input type="checkbox" data-rpg-filter-key="best"${st.best?" checked":""}> Best of each exposure</label><span class="rpg-crumb-note rpg-board-hint">Click a column name to sort; click again to flip. Use the row under the names to filter.</span></div><div id="rpg-guild-board">${guildBoardRows(funds,held)}</div></section>`;
}
function guildChart(f){
  const hist=(f.history_monthly||[]).filter(r=>num(r.close)!==null);
  if(hist.length<6)return "";
  const prices=hist.map(r=>num(r.close));
  const lo=Math.min(...prices),hi=Math.max(...prices);
  const step=niceStep(Math.max(hi-lo,hi*0.05,0.01),5);
  const bottom=Math.max(0,Math.floor(lo/step)*step),top=Math.ceil(hi/step)*step||1;
  const X0=60,X1=860,Y0=16,Y1=236;
  const x=i=>X0+(X1-X0)*i/(hist.length-1);
  const y=v=>Y1-(Y1-Y0)*(v-bottom)/((top-bottom)||1);
  const grid=[],labels=[];
  for(let v=bottom;v<=top+1e-9;v+=step){grid.push(`M${X0} ${y(v).toFixed(1)} H${X1}`);labels.push(`<text x="52" y="${(y(v)+4).toFixed(1)}">${compact(v)}</text>`)}
  const xt=[0,Math.round((hist.length-1)/2),hist.length-1];
  const last=prices[prices.length-1];
  return `<section class="rpg-stone rpg-road" aria-labelledby="rpg-groad-h"><div class="rpg-section-head"><h2 id="rpg-groad-h" class="rpg-stone-title">The Long Road \u00b7 ${hist.length} month-end closes</h2></div><svg viewBox="0 0 900 270" class="rpg-fluid" role="img" aria-label="${esc(`${f.symbol} month-end close from ${monthLabel(hist[0].month)} to ${monthLabel(hist[hist.length-1].month)}`)}"><path d="${grid.join(" ")}" stroke="#4a3d2c"/><g font-family="Alegreya, serif" font-size="14" fill="#b9a98a" text-anchor="end">${labels.join("")}</g><g font-family="Alegreya, serif" font-size="14" fill="#b9a98a" text-anchor="middle">${xt.map(i=>`<text x="${x(i).toFixed(0)}" y="258">${esc(monthLabel(hist[i].month))}</text>`).join("")}</g><path d="${prices.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}" fill="none" stroke="#a9cf92" stroke-width="3" stroke-linejoin="round"/><circle cx="${X1}" cy="${y(last).toFixed(1)}" r="6" fill="#a9cf92" stroke="#231f1a" stroke-width="2"/></svg></section>`;
}
const PROJ_STATUS={TESTED:["TESTED","verdant","Ranges for this family held their stated odds in the walk-forward test"],TOO_CAUTIOUS:["TOO CAUTIOUS","bronze","Ranges for this family were wider than the real outcomes in testing, so growth is not compared on them"],TOO_NARROW:["TOO NARROW","crimson","Ranges for this family were narrower than the real outcomes in testing"],TOO_FEW_TESTS:["TOO FEW TESTS","stone","Too few past starts to test this family's ranges"],UNTESTED:["UNTESTED","stone","This family was not in the test"]};
const projTested=f=>f?.projection_3y?.status==="TESTED";
function projCell(f){const p=f.projection_3y;if(!p){const o=f.outlook_3y;return o?`<td class="num rpg-muted" title="${esc("Own-history outlook: from this fund's own past only; not compared with other funds")}">${pct(o.p50)}\u00b0</td>`:`<td class="num rpg-muted">\u2014</td>`}const n=num(p.p50);return projTested(f)?`<td class="num ${upDown(n)}">${pct(n)}</td>`:`<td class="num rpg-muted" title="${esc(PROJ_STATUS[p.status]?.[2]||"")}">${pct(n)}~</td>`}
const OUTLOOK_KIND={IDIOSYNCRATIC:"it follows no reference fund closely",SPECIALIZED_LEVERAGED:"it is a leveraged fund; its own history includes the daily-reset decay",SPECIALIZED_INVERSE:"it is an inverse fund; its own history includes the daily-reset decay",MOVES_FAR_MORE_THAN_ITS_REFERENCE:"it moves far more than its reference, the way leveraged funds do"};
function guildOwnOutlook(f,h){
  const o=f.outlook_3y,st=PROJ_STATUS[o.status]||PROJ_STATUS.UNTESTED;
  const tile=(label,value,sub="")=>`<div class="rpg-parch rpg-tile"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${value}</div>${sub?`<div class="rpg-stat-sub">${esc(sub)}</div>`:""}</div>`;
  const g=o.growth_of_1000||{};
  const mine=h&&h.worth?`<p class="rpg-vault-why">${esc(`Your ${money(h.worth)} here: about ${money(h.worth*num(g.p50)/1000)} in three years in the typical case, ${money(h.worth*num(g.p10)/1000)} in the bad case and ${money(h.worth*num(g.p90)/1000)} in the good case, before anything you add.`)}</p>`:"";
  const years=Math.round(num(o.months_of_history)/12);
  const cov=num(o.category_band_coverage);
  const stWhy={TESTED:"In the walk-forward test, funds of this kind landed inside this sort of 80% range",TOO_NARROW:"In the walk-forward test this sort of range was too narrow for funds of this kind: real outcomes landed outside it more often than the 1 in 5 it promises",TOO_CAUTIOUS:"In the walk-forward test this sort of range was wider than real outcomes for funds of this kind",TOO_FEW_TESTS:"Too few past starts to test funds of this kind",UNTESTED:"Funds of this kind were not in the test"}[o.status]||"";
  const miss=num(o.category_center_median_abs_error);
  const lev=o.category==="SPECIALIZED_LEVERAGED"||o.category==="MOVES_FAR_MORE_THAN_ITS_REFERENCE";
  const why=`This fund has no reference-based range because ${OUTLOOK_KIND[o.category]||"it has no clean peer group"}. So the range here comes from its own ${years} years of month-to-month returns alone: typical growth is its own long-run average (${pct(o.center)} a year) and the spread is its own past swings, resampled. ${stWhy}${cov===null?"":` ${Math.round(cov*100)}% of the time`}.${miss===null?"":` The typical figure itself missed the real 3-year result by a median of ${(miss*100).toFixed(0)} percentage points a year for funds of this kind.`}${lev&&num(o.center)>0.15?" Its own average comes from the years it happens to have lived through; a fund that magnifies its market repeats a strong stretch only if the market does.":""} A fund's own past is a weak guide to its future, so read the bad case as seriously as the good one; growth is never compared across funds on it.`;
  return `<section class="rpg-stone rpg-road rpg-outlook" aria-labelledby="rpg-out-h"><div class="rpg-section-head"><h2 id="rpg-out-h" class="rpg-stone-title">The next three years \u00b7 $1,000 in ${esc(f.symbol)} \u00b7 its own history</h2>${badge("OWN HISTORY","stone")} ${badge(st[0],st[1])}</div><div class="rpg-tiles rpg-outlook-tiles">${tile("Bad case (1 in 10 worse)",money(g.p10,0),`${pct(o.p10)} a year`)}${tile("Typical",money(g.p50,0),`${pct(o.p50)} a year`)}${tile("Good case (1 in 10 better)",money(g.p90,0),`${pct(o.p90)} a year`)}${tile("Chance of a loss",`${Math.round(num(o.chance_of_loss)*100)}%`,"over the full three years")}</div>${mine}<p class="rpg-item-note rpg-outlook-why">${esc(why)}</p></section>`;
}
function guildOutlook(f,h){
  const p=f.projection_3y;
  if(!p&&f.outlook_3y)return guildOwnOutlook(f,h);
  if(!p)return `<section class="rpg-stone rpg-road rpg-outlook" aria-labelledby="rpg-out-h"><div class="rpg-section-head"><h2 id="rpg-out-h" class="rpg-stone-title">The next three years</h2></div><p class="rpg-vault-why">${esc(f.projection_3y_excluded==="MOVES_FAR_MORE_THAN_ITS_REFERENCE"?"No 3-year range for this fund: it has moved more than twice as much as its reference or the S&P 500, the way leveraged funds do, so a scaled copy of the reference's history would not describe it honestly.":"No 3-year range for this fund: leveraged, inverse, ungrouped and very young funds are left out, because their past does not describe their next three years.")}</p></section>`;
  const st=PROJ_STATUS[p.status]||PROJ_STATUS.UNTESTED;
  const tile=(label,value,sub="")=>`<div class="rpg-parch rpg-tile"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${value}</div>${sub?`<div class="rpg-stat-sub">${esc(sub)}</div>`:""}</div>`;
  const g=p.growth_of_1000||{};
  const mine=h&&h.worth?`<p class="rpg-vault-why">${esc(`Your ${money(h.worth)} here: about ${money(h.worth*num(g.p50)/1000)} in three years in the typical case, ${money(h.worth*num(g.p10)/1000)} in the bad case and ${money(h.worth*num(g.p90)/1000)} in the good case, before anything you add.`)}</p>`:"";
  const rule={CASH_PLUS_BETA:`today's cash yield plus ${num(p.beta)===null?"its":`${num(p.beta).toFixed(2)}\u00d7`} the long-run extra return of ${p.reference} over cash`,REFERENCE_HISTORY:`the long-run return of ${p.reference}`,OWN_HISTORY:"its own last ten years",BOND_YIELD:"its current yield"}[p.center_rule]||"its family's rule";
  const why=`Typical growth comes from ${rule}${num(p.fee_gap)?`, less ${(Math.abs(num(p.fee_gap))*100).toFixed(2)}% a year of ${num(p.fee_gap)>0?"extra":"(negative) "}fee against ${p.reference}`:""}; the range comes from ${p.reference}'s own ups and downs over the last ${p.reference_months?Math.round(p.reference_months/12):"\u2014"} years, scaled to this fund's swings. ${st[2]}${num(p.family_band_coverage)===null?"":` (${Math.round(num(p.family_band_coverage)*100)}% of past outcomes landed inside the 80% range)`}.`;
  return `<section class="rpg-stone rpg-road rpg-outlook" aria-labelledby="rpg-out-h"><div class="rpg-section-head"><h2 id="rpg-out-h" class="rpg-stone-title">The next three years \u00b7 $1,000 in ${esc(f.symbol)}</h2>${badge(st[0],st[1])}</div><div class="rpg-tiles rpg-outlook-tiles">${tile("Bad case (1 in 10 worse)",money(g.p10,0),`${pct(p.p10)} a year`)}${tile("Typical",money(g.p50,0),`${pct(p.p50)} a year`)}${tile("Good case (1 in 10 better)",money(g.p90,0),`${pct(p.p90)} a year`)}${tile("Chance of a loss",`${Math.round(num(p.chance_of_loss)*100)}%`,"over the full three years")}</div>${mine}<p class="rpg-item-note rpg-outlook-why">${esc(why)}</p></section>`;
}
function guildGrowthBoard(pkg){
  const groups=Object.entries(pkg.groups||{}).filter(([,v])=>v.projection_3y).sort((a,b)=>num(b[1].projection_3y.p50)-num(a[1].projection_3y.p50));
  if(!groups.length)return "";
  const rows=groups.map(([k,v])=>{const p=v.projection_3y,st=PROJ_STATUS[p.status]||PROJ_STATUS.UNTESTED,ok=p.status==="TESTED";return `<tr class="${ok?"":"rpg-muted"}"><th scope="row"><button type="button" class="rpg-btn rpg-link" data-rpg-growth-group="${esc(k)}">${esc(groupName(k))}</button></th><td class="num">${esc(String(p.funds))}</td><td class="num ${upDown(num(p.p10))}">${pct(p.p10)}</td><td class="num ${ok?upDown(num(p.p50)):""}"><strong>${pct(p.p50)}</strong></td><td class="num">${pct(p.p90)}</td><td class="num">${Math.round(num(p.chance_of_loss)*100)}%</td><td class="rpg-nowrap">${badge(st[0],st[1])}</td></tr>`}).join("");
  const t=pkg.research?.projection_test||{};
  const note=`Medians across each group's funds, a year, over the next 36 months. ${t.observations?`Tested on ${Number(t.observations).toLocaleString("en-US")} past fund-years (starts ${t.test_starts?.[0]}\u2013${t.test_starts?.[t.test_starts.length-1]}): ${Math.round(num(t.overall?.inside_10_90)*100)}% of real outcomes landed inside the 80% range.`:""} Groups differ by what they hold, not by any fund's skill. Within a group a higher figure mostly means a higher-beta fund with wider swings, which did not pay more in the Guild's trials, so the counsel within a group stays the cheapest fund. The test years were mostly good ones for US stocks, and nothing here looks at today's prices against earnings. Pick a group to see its funds, cheapest first.`;
  return `<section class="rpg-stone rpg-guild-research rpg-growth" aria-labelledby="rpg-growth-h"><div class="rpg-section-head"><h2 id="rpg-growth-h" class="rpg-stone-title">Where three years of growth could come from</h2><span class="rpg-crumb-note">Bad case \u00b7 typical \u00b7 good case, a year</span></div><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Peer group</th><th class="num">Funds</th><th class="num">Bad case</th><th class="num">Typical</th><th class="num">Good case</th><th class="num">Chance of a loss</th><th>Ranges</th></tr></thead><tbody>${rows}</tbody></table></div><p class="rpg-footnote">${esc(note)}</p></section>`;
}
function guildDetail(f,held,groups){
  if(!f)return "";
  const tile=(label,value,sub="")=>`<div class="rpg-parch rpg-tile"><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-big num">${value}</div>${sub?`<div class="rpg-stat-sub">${esc(sub)}</div>`:""}</div>`;
  const g=groups[f.peer_group]||{};
  const [il,it,imean]=implText(f);
  const w=f.when_to_buy;
  const [wl,wt,wmean]=whenText(w);
  const h=held[f.symbol];
  const ev=f.group_evidence||{};
  const cl=f.cluster;
  const loose=w&&w.loose?`This fund has no peer family; the reading shown is the one for ${FAMILY_NAME[String(w.basis||"").replace("NEAREST_REFERENCE_FAMILY_","")]||"the family of the fund it most resembles"}, and it fits loosely. `:"";
  const whenWhy=!w?(f.peer_group==="SPECIALIZED_LEVERAGED"||f.peer_group==="SPECIALIZED_INVERSE"?"Leveraged and inverse funds get no timing reading: the families' tests do not describe them.":"This fund has no peer family, so there is no timing reading."):loose+(w.verdict==="STEADY_BUYING"?"For this family no timing rule beat plain monthly buying out of sample, so steady buying is the counsel.":`For ${FAMILY_NAME[f.group_family||String(w.basis||"").replace("NEAREST_REFERENCE_FAMILY_","")]||"this family"}, waiting for a ${Math.round(num(w.parameter)*100)}% dip from the peak beat monthly buying in ${Math.round(num(w.evidence?.share_beating)*100)}% of 3-year test periods (median gain ${pct(w.evidence?.median_edge)}). The family is ${pct(w.drawdown)} from its peak as of ${monthLabel(w.as_of_month)}.`);
  const implWhy=!cl?"No other fund in the universe moves almost identically to this one.":f.implementation?.call==="REDIRECT_NEW_MONEY"?`${cl.members.length} funds move almost identically (daily returns at 0.998+ correlation over 3 years). ${f.implementation.to} did it best${cl.basis==="LOWEST_OFFICIAL_EXPENSE_RATIO_AMONG_BEST_TRACKERS"?" at the lowest official fee":", net of its costs"}, so new money goes further there; shares you already hold can stay.`:`It is the best of ${cl.members.length} near-identical funds${cl.basis==="LOWEST_OFFICIAL_EXPENSE_RATIO_AMONG_BEST_TRACKERS"?", by official fee":", by 3-year return net of costs"}.`;
  const callWhy=f.ranking_basis==="COST_WITHIN_PEER_GROUP_36M"?`Its official fee (${(num(f.expense_ratio)*100).toFixed(2)}% a year) is cheaper than ${Math.round(num(f.cost_percentile_in_group))}% of its peers. ${costEvidence()} Past returns, momentum and trend did not predict which peer would do better.`:f.ranking_call==="RANKED_NO_CALL"?"There is no official SEC expense ratio on file for this fund, so it gets no call.":looseWhy(f);
  const hold=h?`<div class="rpg-parch-kicker">Your charter</div><div class="rpg-item-stats"><div><div class="rpg-stat-label">Held</div><div class="rpg-stat-value">${esc(qty(h.shares))} shares</div></div><div><div class="rpg-stat-label">Gold paid</div><div class="rpg-stat-value">${money(h.paid)}</div></div><div><div class="rpg-stat-label">Worth at the close</div><div class="rpg-stat-value">${money(h.worth)}</div><div class="rpg-stat-sub ${upDown(h.worth-h.paid)}">${signed(h.worth-h.paid)}${h.paid?` \u00b7 ${pct((h.worth-h.paid)/h.paid)}`:""}</div></div></div>`:"";
  const pctile=v=>num(v)===null?"\u2014":`${Math.round(num(v))}th`;
  return `<section class="rpg-stone rpg-vault-hero" aria-labelledby="rpg-fund-h"><div class="rpg-vault-call"><div class="rpg-vault-id"><div><h2 id="rpg-fund-h" class="rpg-vault-name">${esc(f.symbol)}</h2><div class="rpg-vault-role">${esc(f.name||"")} \u00b7 ${esc(groupName(f.peer_group))}${f.history_from?` \u00b7 since ${esc(String(f.history_from).slice(0,4))}`:""}</div></div></div><div class="rpg-guild-verdicts"><div class="rpg-vault-verdict">${badge(callText(f)[0],callText(f)[1])}<span>${esc(callText(f)[2])}</span></div><div class="rpg-vault-verdict">${badge(il,it)}<span>${esc(imean)}</span></div><div class="rpg-vault-verdict">${badge(wl,wt)}<span>${esc(wmean)}</span></div></div><p class="rpg-vault-why">${esc(callWhy)}</p><p class="rpg-vault-why">${esc(implWhy)}</p><p class="rpg-vault-why">${esc(whenWhy)}</p></div><div class="rpg-tiles">${tile("Close",money(f.close),`as of ${dayLabel(f.as_of_date)}`)}${tile("3 years, a year",pct(f.annualized_3y),`5 years ${pct(f.annualized_5y)} a year`)}${tile("Worst fall, 3 years",pct(f.max_drawdown_3y),num(f.drawdown_3y_high)!==null?`now ${pct(f.drawdown_3y_high)} from its 3-year high; ${pct(f.drawdown_now)} from its all-time high${f.peak_date?` (${String(f.peak_date).slice(0,4)})`:""}`:`now ${pct(f.drawdown_now)} from its peak`)}${tile("Fee",num(f.expense_ratio)===null?"\u2014":`${(num(f.expense_ratio)*100).toFixed(2)}%`,num(f.expense_ratio)===null?"not in SEC data yet":"official, SEC filing")}</div></section><div class="rpg-duo">${guildChart(f)}<aside class="rpg-parch rpg-item-detail"><div class="rpg-parch-kicker">Among its ${esc(String(g.members||"\u2014"))} peers \u00b7 ${esc(groupName(f.peer_group))}</div><p class="rpg-item-note">1-year return in the ${pctile(f.return_1y_group_percentile)} percentile; 3-year in the ${pctile(f.annualized_3y_group_percentile)}. Peer medians: ${pct(g.median_return_1y)} over 1 year, ${pct(g.median_annualized_3y)} a year over 3. Past rank did not predict future rank in testing, so this is context, not counsel.</p><p class="rpg-item-note">Grouped by its own returns: closest to ${esc(ev.nearest_reference||"\u2014")} (${num(ev.correlation)===null?"\u2014":num(ev.correlation).toFixed(2)} correlation), beta ${num(ev.beta_spy)===null?"\u2014":num(ev.beta_spy).toFixed(2)} to the S&P 500. Provisional until the SEC taxonomy is certified.</p>${cl?`<div class="rpg-parch-kicker">Near-identical funds</div><p class="rpg-item-note">${cl.members.map(s=>s===cl.best?`<strong>${esc(s)} (best)</strong>`:esc(s)).join(", ")}</p>`:""}${hold}</aside></div>${guildOutlook(f,h)}`;
}
function costEvidence(){
  /* The cost test's own numbers, from this package's research (never a sentence fixed at one run). */
  const ct=state.guild?.package?.research?.cost_test?.["36m"];
  const share=num(ct?.share_years_cheapest_beats_most_expensive),years=num(ct?.test_years),cheap=num(ct?.cheapest_quintile_mean_excess),dear=num(ct?.most_expensive_quintile_mean_excess);
  if(share===null||years===null)return "Cheaper funds have tended to do better than costlier peers in testing.";
  const won=Math.round(share*years);
  const gap=cheap!==null&&dear!==null?` On average the cheapest fifth ran ${(Math.abs(cheap-dear)*100).toFixed(1)}% a year ${cheap>=dear?"ahead of":"behind"} the costliest.`:"";
  return `In testing, the cheapest fifth of a peer group beat the costliest fifth over the next 3 years in ${won} of ${years} years.${gap}`;
}
function guildTrials(pkg){
  const r=pkg?.research||{};
  const ic=r.factor_ic_12m||{};
  const rows=Object.entries(ic).filter(([k])=>FACTOR_NAMES[k]).map(([k,v])=>`<tr><th scope="row">${esc(FACTOR_NAMES[k])}</th><td class="num">${num(v.mean_ic)===null?"\u2014":num(v.mean_ic).toFixed(3)}</td><td class="num">${num(v.t_yearly)===null?"\u2014":num(v.t_yearly).toFixed(1)}</td><td>${Math.abs(num(v.t_yearly)||0)>=2?badge("RELIABLE","verdant"):badge("NOISE","stone")}</td></tr>`).join("");
  const fams=Object.entries(r.timing||{}).map(([fam,rules])=>`<tr><th scope="row">${esc(FAMILY_NAME[fam]||fam)}</th>${["TREND_PAUSE","STRETCH_PAUSE","WAIT_FOR_DIP","MOMENTUM_PAUSE"].map(k=>{const v=rules[k]||{};return `<td class="num">${v.share_beating===null||v.share_beating===undefined?"\u2014":`${Math.round(num(v.share_beating)*100)}%`}${v.passes_gate?" \u2713":""}</td>`}).join("")}</tr>`).join("");
  const ct=r.cost_test&&r.cost_test["36m"];
  const costRow=ct?`<tr class="rpg-cost-row"><th scope="row">Lower official fee (3 years)</th><td class="num">${num(ct.mean_ic).toFixed(3)}</td><td class="num">${num(ct.t_yearly).toFixed(1)}</td><td>${r.cost_test.calls_enabled?badge("USED FOR CALLS","verdant"):badge("NOISE","stone")}</td></tr>`:"";
  return `<section class="rpg-stone rpg-guild-research" aria-labelledby="rpg-gres-h"><div class="rpg-section-head"><h2 id="rpg-gres-h" class="rpg-stone-title">The Guild's trials</h2></div><div class="rpg-duo"><div><div class="rpg-parch-kicker">Does it pick next year's winners within a peer group?</div><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Signal</th><th class="num">Rank correlation</th><th class="num">t (yearly)</th><th>Verdict</th></tr></thead><tbody>${rows}${costRow}</tbody></table></div></div><div><div class="rpg-parch-kicker">Does waiting beat buying every month? (share of 3-year tests won)</div><div class="rpg-table-wrap"><table class="rpg-table"><thead><tr><th>Family</th>${["TREND_PAUSE","STRETCH_PAUSE","WAIT_FOR_DIP","MOMENTUM_PAUSE"].map(k=>`<th class="num">${esc(RULE_NAMES[k])}</th>`).join("")}</tr></thead><tbody>${fams}</tbody></table></div></div></div><p class="rpg-footnote">${esc("Every test was walk-forward on 1,077 funds' month-end total returns, with each setting chosen only from earlier years and the pass marks set before any result was seen. No price signal reliably picked winners within a peer group. Cost did, over 3 years: the calls rank each fund by its official SEC fee against its peers, a change approved after seeing the results and labelled provisional. Among funds that are effectively the same, the Guild names the one with the lowest fee and best tracking (\u2713 marks a timing rule that passed).")}</p></section>`;
}
function guildCounsel(funds,held){
  const mine=funds.filter(f=>held[f.symbol]);
  const moves=mine.filter(f=>f.implementation?.call==="REDIRECT_NEW_MONEY").map(f=>`${f.symbol} \u2192 ${f.implementation.to}`);
  const waits=mine.filter(f=>f.when_to_buy?.verdict==="WAIT").map(f=>f.symbol);
  const parts=[];
  parts.push(moves.length?`Send new money for ${moves.join(", ")}: the same exposure, done better.`:"Your funds are already the best of their near-identical groups.");
  const avoid=mine.filter(f=>f.ranking_call==="AVOID").map(f=>f.symbol);
  const buys=mine.filter(f=>f.ranking_call==="BUY").map(f=>f.symbol);
  if(avoid.length)parts.push(`${avoid.join(", ")} ${avoid.length>1?"cost":"costs"} more than most of ${avoid.length>1?"their":"its"} peers (AVOID for new money).`);
  if(buys.length)parts.push(`${buys.join(", ")} ${buys.length>1?"are":"is"} among the cheapest of ${buys.length>1?"their":"its"} peers (BUY).`);
  if(waits.length)parts.push(`For ${waits.join(", ")}, the real-asset rule says wait for a dip.`);
  parts.push("Everything else: keep buying steadily.");
  return parts.join(" ");
}
function renderGuild(){
  const page=byId("guild");
  if(!page)return;
  let view=byId("rpg-guild");
  if(!view){view=document.createElement("div");view.id="rpg-guild";view.className="rpg-realm-view";page.appendChild(view);bindNavigation(view);
    view.addEventListener("click",event=>{const pick=event.target.closest("[data-rpg-fund]");const more=event.target.closest("[data-rpg-more]");const grow=event.target.closest("[data-rpg-growth-group]");if(grow){Object.assign(state.guildFilter,{family:"ALL",group:grow.dataset.rpgGrowthGroup,sort:"call",dir:"desc",buys:false,best:false,mine:false,q:"",cols:{},nums:{},limit:50});renderGuild();byId("rpg-board-h")?.scrollIntoView({behavior:"smooth",block:"start"});return}if(pick){state.guildPick=pick.dataset.rpgFund;state.guildDetail=null;renderGuild();loadGuildFund(state.guildPick)}else if(more){state.guildFilter.limit+=50;guildRefreshBoard()}
      const st=state.guildFilter,sortBtn=event.target.closest("[data-rpg-sort]"),clear=event.target.closest("[data-rpg-col-clear]");
      if(sortBtn){const k=sortBtn.dataset.rpgSort,col=BOARD_COLS.find(c=>c.k===k);if(st.sort===k)st.dir=st.dir==="asc"?"desc":"asc";else{st.sort=k;st.dir=col&&col.text?"asc":"desc"}guildRefreshBoard();return}
      if(clear){st.cols[clear.dataset.rpgColClear]=[];st.limit=50;guildRefreshBoard();return}
      if(event.target.closest("[data-rpg-board-reset]")){Object.assign(st,{sort:"default",dir:"desc",cols:{},nums:{},q:"",group:"",buys:false,limit:50});state.guildOpenFilter=null;renderGuild()}});
    view.addEventListener("toggle",event=>{const d=event.target;if(!d.matches||!d.matches("[data-rpg-colfilter]"))return;if(d.open){state.guildOpenFilter=d.dataset.rpgColfilter;view.querySelectorAll("[data-rpg-colfilter][open]").forEach(o=>{if(o!==d)o.open=false})}else if(state.guildOpenFilter===d.dataset.rpgColfilter)state.guildOpenFilter=null},true);
    const onColumn=event=>{const st=state.guildFilter,box=event.target.closest("[data-rpg-col]"),inp=event.target.closest("[data-rpg-num]");
      if(box){const k=box.dataset.rpgCol;const set=new Set(st.cols[k]||[]);box.checked?set.add(box.value):set.delete(box.value);st.cols[k]=[...set];st.limit=50;guildRefreshBoard();return true}
      if(inp){st.nums[inp.dataset.rpgNum]=inp.value;st.limit=50;guildRefreshBoard();return true}
      return false};
    view.addEventListener("change",event=>{if(event.target.closest("[data-rpg-num]"))return;onColumn(event)});
    view.addEventListener("input",event=>{if(event.target.closest("[data-rpg-num]"))onColumn(event)});
    const onFilter=event=>{const el=event.target.closest("[data-rpg-filter-key]");if(!el)return;const k=el.dataset.rpgFilterKey;state.guildFilter[k]=el.type==="checkbox"?el.checked:el.value;if(k==="family")state.guildFilter.group="";state.guildFilter.limit=50;if(k==="q")guildRefreshBoard();else renderGuild()};
    view.addEventListener("change",onFilter);view.addEventListener("input",event=>{if(event.target.dataset?.rpgFilterKey==="q")onFilter(event)});}
  const crumbs=note=>`<header class="rpg-stone rpg-crumbs"><nav aria-label="Breadcrumb"><button type="button" class="rpg-btn rpg-crumb" data-rpg-page="home">The Hall</button><span aria-hidden="true">\u203a</span><span class="rpg-crumb-here">Merchants' Guild</span></nav><span class="rpg-crumb-note">${esc(note)}</span></header>${realmTabs("etf")}`;
  const g=state.guild;
  if(!g){view.innerHTML=`${crumbs("ETFs")}<p class="rpg-parch-note">Opening the Guild's ledger\u2026</p>`;loadGuild().then(renderGuild).catch(()=>{view.innerHTML=`${crumbs("ETFs")}<p class="rpg-parch-note">The Guild's ledger could not be loaded.</p>`});return}
  if(!g.available||!(g.funds||[]).length){view.innerHTML=`${crumbs("ETFs")}<section class="rpg-stone"><p class="rpg-parch-note">The Merchants' Guild has no ledger in this publication yet. It fills after the daily ETF package publishes.</p></section>`;return}
  const pkg=g.package||{};
  const funds=g.funds;
  const held=guildHoldings();
  if(!state.guildPick){const first=funds.find(f=>held[f.symbol])||funds.find(f=>f.symbol==="VOO")||funds[0];state.guildPick=first.symbol}
  const worth=Object.values(held).reduce((a,h)=>a+h.worth,0),paid=Object.values(held).reduce((a,h)=>a+h.paid,0);
  const asOf=pkg.package_as_of||funds[0].as_of_date;
  const detail=state.guildDetail&&state.guildDetail.symbol===state.guildPick?state.guildDetail:funds.find(f=>f.symbol===state.guildPick);
  view.innerHTML=`${crumbs(`${funds.length} funds \u00b7 closes of ${dayLabel(asOf)} \u00b7 ${String(pkg.certification_status||"PROVISIONAL").toLowerCase()} \u00b7 research, not orders`)}<section class="rpg-stone rpg-guild-hero"><div><div class="rpg-parch-kicker">The Guild's counsel for your charters</div><p class="rpg-guild-counsel">${esc(guildCounsel(funds,held))}</p></div><div class="rpg-crumb-stats"><span>Charters <strong class="num">${Object.keys(held).length}</strong></span><span>Worth <strong class="num">${money(worth)}</strong></span><span>Gold paid <strong class="num">${money(paid)}</strong></span><span class="${upDown(worth-paid)}">${signed(worth-paid)}</span></div></section>${guildBoard(funds,held)}<div id="rpg-guild-detail">${guildDetail(detail,held,pkg.groups||{})}</div>${guildGrowthBoard(pkg)}${guildTrials(pkg)}${footer(`Prices from free public data (tier 4) and peer groups from each fund's own returns: provisional, not certified. Package ${pkg.package_id||"\u2014"}. Research, not personal financial advice; nothing here places a trade.`)}`;
  if(!state.guildDetail||state.guildDetail.symbol!==state.guildPick)loadGuildFund(state.guildPick);
}
function guildRefreshBoard(){
  const slot=byId("rpg-guild-board");if(!slot||!state.guild)return;
  const a=document.activeElement,keep=a&&slot.contains(a)?(a.dataset.rpgNum?`[data-rpg-num="${a.dataset.rpgNum}"]`:a.dataset.rpgFilterKey?`[data-rpg-filter-key="${a.dataset.rpgFilterKey}"]`:a.dataset.rpgSort?`[data-rpg-sort="${a.dataset.rpgSort}"]`:a.dataset.rpgCol?`[data-rpg-col="${a.dataset.rpgCol}"][value="${CSS.escape(a.value)}"]`:null):null;
  const caret=keep&&a.selectionStart!==undefined?[a.selectionStart,a.selectionEnd]:null;
  slot.innerHTML=guildBoardRows(state.guild.funds,guildHoldings());
  if(keep){const el=slot.querySelector(keep);if(el){el.focus({preventScroll:true});if(caret&&el.setSelectionRange)try{el.setSelectionRange(...caret)}catch(e){}}}
}
function loadGuildFund(symbol){
  api(`/v1/presentation/etf/${encodeURIComponent(symbol)}`).then(doc=>{if(state.guildPick!==symbol)return;state.guildDetail=doc;const slot=byId("rpg-guild-detail");if(slot)slot.innerHTML=guildDetail(doc,guildHoldings(),state.guild?.package?.groups||{})}).catch(()=>{});
}

function watchGuild(){document.addEventListener("click",event=>{if(event.target.closest('.nav-item[data-page="guild"]'))setTimeout(()=>{try{renderGuild()}catch(error){console.error("[realm] guild",error)}},0)});if(location.hash==="#guild")setTimeout(renderGuild,0)}
function watchPages(){watchGuild();watchCounsel();guardRealmPage("home","rpg-hall",renderHall,HALL_SCROLL);guardRealmPage("portfolio","rpg-treasury",renderInventory,TREASURY_SCROLL)}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",watchPages);else watchPages();

document.addEventListener("uip:home-rendered",event=>{
  const d=event.detail||{};
  state.home=d;
  try{renderHall(d)}catch(error){console.error("[realm] hall",error)}
  try{renderInventory(d)}catch(error){console.error("[realm] treasury",error)}
  try{if(byId("guild")?.classList.contains("active-page")||byId("rpg-guild"))renderGuild()}catch(error){console.error("[realm] guild",error)}
  const slot=byId("rpg-hoard-slot");
  if(slot&&state.vault)slot.innerHTML=vaultHoard(state.vault.item);
});
document.addEventListener("uip:crypto-detail",event=>{
  const d=event.detail||{};
  try{renderVault(d.page,d.item,d.payload)}catch(error){console.error("[realm] vault",error)}
});
window.UIPRealm={renderHall,renderInventory,renderVault,renderGuild,state,realmTabs,realmTotals,bindNavigation};
})();
