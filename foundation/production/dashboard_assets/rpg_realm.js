/* The Universal Ledger: realm views drawn from the certified dashboard data.
   The Hall (home), the Treasury inventory (portfolio) and the Arcane Vault (crypto research).
   Read-only presentation: nothing here records, changes or executes anything. */
(()=>{
"use strict";
const state={home:null,catalog:null,catalogPromise:null,invFilter:"all",invPick:null};
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
/* Move a page's original sections into a closed scroll below the realm view; ids stay intact. */
function tuck(page,view,title,detail){
  if(page.classList.contains("rpg-realm-on"))return;
  const heading=page.querySelector(":scope > .page-heading");
  page.insertBefore(view,heading?heading.nextSibling:page.firstChild);
  const scroll=document.createElement("details");
  scroll.className="rpg-scroll";
  scroll.innerHTML=`<summary><span>${esc(title)}</span><small>${esc(detail)}</small></summary>`;
  [...page.children].filter(child=>child!==view&&child!==heading&&child!==scroll).forEach(child=>scroll.appendChild(child));
  page.appendChild(scroll);
  page.classList.add("rpg-realm-on");
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
  purse:c=>`<svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M14 10 H26 L23 15 C31 18 33 25 31 30 C29 34 11 34 9 30 C7 25 9 18 17 15 Z" stroke="${c}" stroke-width="2"/><path d="M15 15 H25" stroke="${c}" stroke-width="1.4"/></svg>`
};
const swatch=color=>`<svg class="rpg-swatch" width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x=".5" y=".5" width="13" height="13" fill="${color}" stroke="#2a1d12"/></svg>`;
const footer=text=>`<p class="rpg-footnote">${esc(text)}</p>`;

function realmTabs(active){
  const tabs=[["hall","The Hall",'data-rpg-page="home"'],["treasury","Treasury",'data-rpg-page="portfolio"'],["metals","The Forge \u00b7 Metals",'data-rpg-domain="metals"'],["crypto","Arcane Vault \u00b7 Crypto",'data-rpg-domain="crypto"'],["mtg","The Archive \u00b7 MTG",'data-rpg-domain="mtg"']];
  return `<nav class="rpg-realms" aria-label="Realms">${tabs.map(([key,label,go])=>`<button type="button" class="rpg-btn rpg-realm${key===active?" is-active":""}" ${go}${key===active?' aria-current="page"':""}>${esc(label)}</button>`).join("")}<span class="rpg-realm is-locked" title="Opens with the ETF section">${LOCK}Merchants' Guild \u00b7 ETFs</span></nav>`;
}

/* ---------- The Hall ---------- */
function realmTotals(d){
  const totals={mtg:0,crypto:0,metals:0,etf:0,acorns:0,purse:0};
  for(const p of d.portfolio?.positions||[]){
    const value=num(p.market_value)??0;
    if(p.domain_id==="metals"&&p.asset_subclass==="cash_proxy")totals.purse+=value;
    else if(totals[p.domain_id]!==undefined)totals[p.domain_id]+=value;
  }
  totals.etf=num(d.manualHoldings?.current_value)||0;
  const acorns=d.externalAccount?.items?.[0];
  totals.acorns=acorns?num(acorns.current_value)||0:0;
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
  return `<section class="rpg-stone rpg-vitals" aria-label="Data vitals" data-rpg-page="refresh-page" title="Open Vitals">${rows.join("")}</section>`;
}
function treasuryRing(d){
  const totals=realmTotals(d);
  const order=["mtg","crypto","etf","acorns","metals","purse"];
  const entries=order.map(key=>[key,totals[key]]).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]);
  const sum=entries.reduce((a,[,v])=>a+v,0);
  const C=2*Math.PI*70;
  let offset=0;
  const arcs=entries.map(([key,v])=>{const len=Math.max(1.5,v/sum*C);const arc=`<circle cx="110" cy="110" r="70" stroke="${REALM[key].color}" stroke-dasharray="${len.toFixed(2)} ${C.toFixed(2)}" stroke-dashoffset="${(-offset).toFixed(2)}"/>`;offset+=v/sum*C;return arc}).join("");
  const share=v=>{const p=v/sum*100;return p<1?"<1%":`${Math.round(p)}%`};
  const aria=entries.map(([key,v])=>`${REALM[key].plain} ${share(v)}`).join(", ");
  const legend=entries.map(([key,v])=>`<div class="rpg-legend-row">${swatch(REALM[key].color)}<span class="rpg-legend-name">${esc(REALM[key].name)} \u00b7 ${esc(REALM[key].plain)}</span><span class="rpg-legend-value">${money(v)}</span><span class="rpg-legend-share">${share(v)}</span></div>`).join("");
  return `<section class="rpg-parch rpg-treasury" aria-labelledby="rpg-treasury-h"><h2 id="rpg-treasury-h" class="rpg-parch-title">The Treasury</h2><div class="rpg-treasury-body"><svg class="rpg-ring" width="220" height="220" viewBox="0 0 220 220" role="img" aria-label="Worth by realm: ${esc(aria)}"><g transform="rotate(-90 110 110)" fill="none" stroke-width="34">${arcs}</g><circle cx="110" cy="110" r="52" fill="none" stroke="#8a6a3a"/><circle cx="110" cy="110" r="88" fill="none" stroke="#8a6a3a"/><text x="110" y="104" text-anchor="middle" font-family="Cinzel, serif" font-size="13" fill="#5a3d1c" letter-spacing="2">WORTH</text><text x="110" y="128" text-anchor="middle" font-family="Cinzel, serif" font-size="22" font-weight="700" fill="#2a1d12">${esc(money(sum,0))}</text></svg><div class="rpg-legend">${legend}</div></div><p class="rpg-parch-note">Market value: certified prices for crypto, metals and MTG; your latest snapshots for the ETFs and Acorns.</p><button type="button" class="rpg-btn rpg-link" data-rpg-page="portfolio">Open the inventory \u203a</button></section>`;
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
  out.push([false,"Raise the Merchants' Guild (the ETF section)"]);
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
  if(!hall){hall=document.createElement("div");hall.id="rpg-hall";hall.className="rpg-realm-view";tuck(page,hall,"The steward's ledger","Certified totals, attention, domain health and authority");bindNavigation(hall)}
  hall.innerHTML=`${chronicle(d)}${realmTabs("hall")}${vitals(d.refresh)}<div class="rpg-duo">${treasuryRing(d)}${questJournal(d)}</div>${recentDeeds(d)}${footer("Research, not personal financial advice. No counsel here places a trade.")}`;
  applyWidths(hall);
  if(!state.catalog)loadCatalog().then(()=>{const q=byId("rpg-quests");if(q&&state.home===d)q.outerHTML=questJournal(d)}).catch(()=>{const q=byId("rpg-quests");const list=q&&q.querySelector(".rpg-counsel-list");if(list)list.innerHTML=`<p class="rpg-parch-note">The oracles are silent: counsel could not be loaded.</p>`});
}

/* ---------- The Treasury: inventory ---------- */
const KIND={
  relic:{label:"Relic \u00b7 Arcane Vault (crypto)",color:"#7fa9dc",tab:"Relics"},
  ingot:{label:"Ingot \u00b7 The Forge (metals)",color:"#d9b45a",tab:"Ingots"},
  charter:{label:"Charter \u00b7 Merchants' Guild (ETF)",color:"#8fbf72",tab:"Charters"},
  tome:{label:"Tome \u00b7 The Archive (MTG)",color:"#b493d6",tab:"Tomes"},
  coffer:{label:"Coffer \u00b7 Acorns",color:"#dba873",tab:"Coffers"},
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
  for(const h of d.manualHoldings?.items||[])items.push({key:`manual:${h.symbol}`,symbol:h.symbol,name:h.asset_name||h.symbol,kind:"charter",held:`${qty(h.shares)} shares`,paid:num(h.cost_basis),worth:num(h.current_value),avg:num(h.average_cost),account:h.notes||h.account_id||"\u2014",note:`Snapshot of ${dayLabel(h.as_of)}. The Merchants' Guild will add counsel for ETFs.`,ledger:["manual","Manual snapshot you entered; not priced by the UIP yet"]});
  const ac=d.externalAccount?.items?.[0];
  if(ac)items.push({key:"acorns",symbol:"ACORNS",name:"Acorns account",kind:"coffer",held:"1 account",paid:num(ac.contributed_basis),worth:num(ac.current_value),avg:null,account:ac.provider||"Acorns",note:`Snapshot of ${dayLabel(ac.as_of)}. ${ac.notes||""}`.trim(),ledger:["manual","Manual snapshot you entered from the Acorns app"]});
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
  const rank={relic:0,ingot:1,charter:2,coffer:3,tome:4,purse:5};
  return items.sort((a,b)=>rank[a.kind]-rank[b.kind]||(b.worth||0)-(a.worth||0));
}
const LEDGER_DOT={ok:"#4d7a3a",manual:"#b5862f",missing:"#8f2f24"};
function inventoryDetail(it){
  if(!it)return `<aside class="rpg-parch rpg-item-detail"><p class="rpg-parch-note">Pick an item to inspect it.</p></aside>`;
  const gain=it.paid!==null&&it.worth!==null?it.worth-it.paid:null;
  const ret=gain!==null&&it.paid?gain/it.paid:null;
  const stat=(label,value,extra="")=>`<div><div class="rpg-stat-label">${esc(label)}</div><div class="rpg-stat-value">${value}</div>${extra}</div>`;
  const members=it.members?`<div class="rpg-members">${it.members.slice().sort((a,b)=>(b.worth||0)-(a.worth||0)).map(m=>`<div class="rpg-member"><span>${esc(m.name)}${m.qty>1?` \u00d7${m.qty}`:""}</span><span class="num">${money(m.worth)}</span><span class="num ${upDown(m.worth!==null&&m.paid!==null?m.worth-m.paid:null)}">${m.worth!==null&&m.paid?pct((m.worth-m.paid)/m.paid,0):"\u2014"}</span></div>`).join("")}</div>`:"";
  const research=it.domain?`<button type="button" class="rpg-btn rpg-link rpg-link-ink" data-rpg-domain="${esc(it.domain)}"${it.domain==="crypto"&&it.asset?` data-rpg-asset="${esc(it.asset)}"`:""}>Open the research \u203a</button>`:"";
  return `<aside class="rpg-parch rpg-item-detail" aria-labelledby="rpg-item-h" aria-live="polite"><div class="rpg-parch-kicker">${esc(KIND[it.kind].label)}</div><h2 id="rpg-item-h" class="rpg-item-name">${esc(it.name)}</h2><div class="rpg-rule"></div><div class="rpg-item-stats">${stat("Held",esc(it.held))}${stat("Gold paid",money(it.paid))}${stat("Worth now",money(it.worth),`<div class="rpg-stat-sub ${upDown(gain)}">${signed(gain)}${ret===null?"":` \u00b7 ${pct(ret)}`}</div>`)}${stat("Average cost",it.avg===null?"\u2014":money(it.avg))}${stat("Account",esc(it.account))}</div>${it.note?`<p class="rpg-item-note">${esc(it.note)}</p>`:""}${members}<div class="rpg-ledger-line"><svg width="10" height="10" aria-hidden="true"><rect width="10" height="10" fill="${LEDGER_DOT[it.ledger[0]]}"/></svg><span>${esc(it.ledger[1])}</span></div>${research}</aside>`;
}
function renderInventory(d){
  const page=byId("portfolio");
  if(!page)return;
  let view=byId("rpg-treasury");
  if(!view){view=document.createElement("div");view.id="rpg-treasury";view.className="rpg-realm-view";tuck(page,view,"The counting house","Certified portfolio tables, Acorns and manual ETF entry");bindNavigation(view);
    view.addEventListener("click",event=>{const tab=event.target.closest("[data-rpg-filter]");const slot=event.target.closest("[data-rpg-item]");if(tab){state.invFilter=tab.dataset.rpgFilter;renderInventory(state.home)}else if(slot){state.invPick=slot.dataset.rpgItem;renderInventory(state.home);view.querySelector(`[data-rpg-item="${CSS.escape(state.invPick)}"]`)?.focus()}});}
  const all=inventoryItems(d);
  const kinds=["relic","ingot","charter","tome","coffer","purse"].filter(k=>all.some(i=>i.kind===k));
  if(state.invFilter!=="all"&&!kinds.includes(state.invFilter))state.invFilter="all";
  const shown=all.filter(i=>state.invFilter==="all"||i.kind===state.invFilter);
  if(!all.some(i=>i.key===state.invPick))state.invPick=(all.find(i=>i.kind==="relic")||all[0]||{}).key||null;
  const pick=all.find(i=>i.key===state.invPick);
  const worth=all.reduce((a,i)=>a+(i.worth||0),0),paid=all.reduce((a,i)=>a+(i.paid||0),0);
  const tabs=[["all","All"],...kinds.map(k=>[k,KIND[k].tab])].map(([k,label])=>`<button type="button" class="rpg-btn rpg-tab${state.invFilter===k?" is-active":""}" data-rpg-filter="${k}" aria-pressed="${state.invFilter===k}">${esc(label)}</button>`).join("");
  const slots=shown.map(i=>{const selected=i.key===state.invPick;const gain=i.paid!==null&&i.worth!==null?i.worth-i.paid:null;return `<button type="button" class="rpg-btn rpg-slot${selected?" is-selected":""}" data-rpg-item="${esc(i.key)}" data-rpg-kind="${i.kind}" aria-pressed="${selected}" aria-label="${esc(`${i.name}, worth ${money(i.worth)}`)}"><span class="rpg-slot-top">${ICON[i.kind](KIND[i.kind].color)}<span class="rpg-slot-count num">${esc(i.count||"")}</span></span><span class="rpg-slot-symbol">${esc(i.symbol)}</span><span class="rpg-slot-worth num">${money(i.worth)}</span><span class="rpg-slot-gain num ${upDown(gain)}">${gain===null||!i.paid?"\u2014":pct(gain/i.paid)}</span></button>`}).join("");
  view.innerHTML=`<header class="rpg-stone rpg-crumbs"><nav aria-label="Breadcrumb"><button type="button" class="rpg-btn rpg-crumb" data-rpg-page="home">The Hall</button><span aria-hidden="true">\u203a</span><span class="rpg-crumb-here">Treasury</span></nav><div class="rpg-crumb-stats"><span>Items <strong class="num">${all.length}</strong></span><span>Worth <strong class="num">${money(worth)}</strong></span><span>Gold paid <strong class="num">${money(paid)}</strong></span></div></header>${realmTabs("treasury")}<div class="rpg-inventory-layout"><section class="rpg-stone rpg-inventory" aria-labelledby="rpg-inv-h"><div class="rpg-section-head"><h2 id="rpg-inv-h" class="rpg-stone-title">Inventory</h2><div class="rpg-tabs" role="group" aria-label="Filter by kind">${tabs}</div></div><div class="rpg-slots">${slots}</div></section>${inventoryDetail(pick)}</div>${footer("Quantities and amounts paid from the UIP ledger; ETF and Acorns rows are your own snapshots.")}`;
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
  const copy=prob===null?`The chance this coin is higher 7 days from now. ${st?.latest_price_date?`No reading in this run (prices through ${st.latest_price_date}).`:"The first reading arrives with the next crypto run."}`:`The chance this coin is higher on ${f.target_date||"the target day"}, read on ${f.origin_date||"\u2014"} from ${money(f.origin_price,0)}. It ${prob>=0.5?"leans up":"leans down or flat"}.`;
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
  vault.innerHTML=`<header class="rpg-stone rpg-crumbs"><nav aria-label="Breadcrumb"><button type="button" class="rpg-btn rpg-crumb" data-rpg-page="home">The Hall</button><span aria-hidden="true">\u203a</span><button type="button" class="rpg-btn rpg-crumb rpg-crumb-azure" data-rpg-vault-back>Arcane Vault</button><span aria-hidden="true">\u203a</span><span class="rpg-crumb-here">${esc(name)}</span></nav><span class="rpg-crumb-note">Kraken prices as of ${esc(asOfLabel)}</span></header><section class="rpg-stone rpg-vault-hero"><div class="rpg-vault-call"><div class="rpg-vault-id"><svg width="64" height="64" viewBox="0 0 64 64" fill="none" aria-hidden="true"><circle cx="32" cy="32" r="29" stroke="#d9b45a" stroke-width="2"/><circle cx="32" cy="32" r="23" stroke="#7a6038" stroke-width="1.5"/><path d="M32 14 L46 32 L32 50 L18 32 Z" stroke="#f1d78f" stroke-width="2.2"/><path d="M32 22 L39 32 L32 42 L25 32 Z" stroke="#f1d78f" stroke-width="1.4"/></svg><div><h1 class="rpg-vault-name">${esc(name)}</h1><div class="rpg-vault-role">${esc(role)}${p.model_robinhood_tradable?" \u00b7 tradable on Robinhood":""}</div></div></div><div class="rpg-vault-verdict"><span class="rpg-seal rpg-seal-${callTone(call)}">${esc(call==="NO_CALL"?"NO CALL":call)}</span><span>${esc(meaning)}</span></div><p class="rpg-vault-why">${esc(vaultWhy(p,name))}</p></div><div class="rpg-tiles">${tile("Price",m(price))}${tile("4-year average",m(avg))}${tile("From its peak",dd===null?"\u2014":`${dd<0?"\u2212":"+"}${Math.abs(Math.round(dd*100))}%`,`peak ${m(num(p.model_peak_usd))} \u00b7 ${monthLabel(p.model_peak_month)}`)}${tile("Past 12 months",ch===null?"\u2014":`${ch<0?"\u2212":"+"}${Math.abs(Math.round(ch*100))}%`,prior===null?"":`from ${m(prior)}`)}</div></section>${vaultRune(p)}${vaultRoad(p,name)}<div class="rpg-duo">${vaultScrying(p)}${vaultOmen(p)}</div><div id="rpg-hoard-slot">${vaultHoard(item)}</div><h2 class="rpg-notes-title">Scholar's notes</h2>`;
  shell.insertBefore(vault,shell.firstChild);
  shell.classList.add("rpg-vault-on");
  bindNavigation(vault);
  vault.querySelector("[data-rpg-vault-back]")?.addEventListener("click",()=>page.querySelector("#cv-v2-back")?.click());
  shell.insertAdjacentHTML("beforeend",footer("Timing counsel for new money, not a price forecast. Research, not personal financial advice."));
  state.vault={item};
}

document.addEventListener("uip:home-rendered",event=>{
  const d=event.detail||{};
  state.home=d;
  try{renderHall(d)}catch(error){console.error("[realm] hall",error)}
  try{renderInventory(d)}catch(error){console.error("[realm] treasury",error)}
  const slot=byId("rpg-hoard-slot");
  if(slot&&state.vault)slot.innerHTML=vaultHoard(state.vault.item);
});
document.addEventListener("uip:crypto-detail",event=>{
  const d=event.detail||{};
  try{renderVault(d.page,d.item,d.payload)}catch(error){console.error("[realm] vault",error)}
});
window.UIPRealm={renderHall,renderInventory,renderVault,state};
})();
