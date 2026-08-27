(()=>{
const REC_DOMAINS=["crypto","metals","mtg"];
const REC_PAGE_SIZE=50;
let catalog=null;
let selectedDomain="all";
let selectedStatus="all";
let searchText="";
let pageIndex=0;
let loading=false;
const detailCache=new Map();

function node(id){return document.getElementById(id)}
function recommendationDomainSummaryAnchor(){return '<div id="recommendation-domain-summary" class="mini-statuses" hidden></div>'}
function escapeHtml(value){const span=document.createElement("span");span.textContent=String(value??"");return span.innerHTML}
function fmtNumber(value,digits=2){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?new Intl.NumberFormat(undefined,{maximumFractionDigits:digits}).format(parsed):String(value)}
function fmtMoney(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",maximumFractionDigits:2}).format(parsed):String(value)}
function fmtPercent(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?`${(parsed*100).toFixed(1)}%`:String(value)}
function fmtPctPoint(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?`${parsed.toFixed(1)}%`:String(value)}
function nativeStatus(item){const payload=item.payload||{};return item.domain_id==="mtg"?(payload.native_purchase_status??null):(payload.native_recommendation??payload.recommendation??null)}
function displayName(item){return item.asset_name||item.asset_symbol||item.asset_id||"Unknown governed asset"}
function searchKey(item){const payload=item.payload||{};return [item.asset_name,item.asset_symbol,item.asset_id,item.asset_subclass,nativeStatus(item),payload.purchase_semantic,payload.evidence_state,payload.actionability_state].filter(Boolean).join(" ").toLowerCase()}
function detailKey(item){return `${item.domain_id}:${item.asset_id}`}
function detailRecords(detail,type){return Array.isArray(detail?.records?.[type])?detail.records[type]:[]}
function payloads(detail,type){return detailRecords(detail,type).map(record=>record.payload||{})}
function firstPayload(detail,type){return payloads(detail,type)[0]||null}
function forecastBy(detail,horizon,method=null){return payloads(detail,"forecast").find(payload=>Number(payload.forecast_horizon_months)===Number(horizon)&&(!method||payload.forecast_method===method))||null}
function crypto36(detail){return forecastBy(detail,36,"LONG_RANGE_SCENARIO_MODEL")}
function cleanStatus(value){return String(value||"MISSING").replaceAll("_"," ")}
function riskLevel(detail,item){const risk=firstPayload(detail,"risk")||{};return String(risk.risk_level??risk.risk_summary??item?.payload?.risk_summary??"unavailable").toLowerCase()}
function riskScore(detail){const risk=firstPayload(detail,"risk")||{};const value=Number(risk.risk_score);return Number.isFinite(value)?value:null}
function riskBars(level){const normalized=String(level||"").toLowerCase();const count=normalized.includes("low")?2:normalized.includes("medium")||normalized.includes("moderate")?3:normalized.includes("high")?5:1;return `<span class="rec-risk-bars ${normalized.includes("low")?"low":""}">${[1,2,3,4,5].map(i=>`<i class="${i<=count?"on":""}"></i>`).join("")}</span>`}
function rangePosition(f){if(!f)return 50;const low=Number(f.lower_bound),base=Number(f.point_forecast),high=Number(f.upper_bound);if(![low,base,high].every(Number.isFinite)||high<=low)return 50;return Math.max(0,Math.min(100,((base-low)/(high-low))*100))}
function coinLabel(item){const symbol=String(item.asset_symbol||"").toUpperCase();if(symbol==="BTC")return "₿";if(symbol==="ETH")return "Ξ";if(symbol==="SOL")return "S";if(symbol==="XRP")return "X";if(symbol==="LINK")return "L";if(symbol==="AVAX")return "A";return (symbol||displayName(item)).slice(0,2).toUpperCase()}
function metalLabel(item){const symbol=String(item.asset_symbol||"").toUpperCase();return (symbol||displayName(item)).slice(0,4).toUpperCase()}
function allForecasts(detail){return payloads(detail,"forecast").slice().sort((a,b)=>Number(a.forecast_horizon_months)-Number(b.forecast_horizon_months)||String(a.forecast_method||"").localeCompare(String(b.forecast_method||"")))}
function longRangeForecasts(detail){return allForecasts(detail).filter(f=>f.forecast_method==="LONG_RANGE_SCENARIO_MODEL"&&Number.isFinite(Number(f.forecast_horizon_months)))}
function svgSparkline(detail){const rows=longRangeForecasts(detail).filter(f=>Number.isFinite(Number(f.point_forecast))).slice(-8);if(rows.length<2)return "";const values=rows.map(f=>Number(f.point_forecast));const lo=Math.min(...values),hi=Math.max(...values);const span=hi-lo||1;const pts=values.map((v,i)=>`${(i/(values.length-1))*100},${32-((v-lo)/span)*27}`).join(" ");return `<div class="rec-sparkline" aria-hidden="true"><svg viewBox="0 0 100 34" preserveAspectRatio="none"><polyline points="${pts}"></polyline></svg></div>`}

async function recRequest(path){const key=sessionStorage.getItem("uiip-dashboard-key")||"";if(!key)throw new Error("Connect to UIP to load certified recommendations.");const response=await fetch(path,{headers:{"X-API-Key":key,"Accept":"application/json"}});if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.error?.message||`Request failed (${response.status})`)}return response.json()}
async function readDomain(domain){const items=[];let offset=0;while(true){const document=await recRequest(`/v1/presentation/recommendation-catalog?domain=${encodeURIComponent(domain)}&limit=200&offset=${offset}`);const page=Array.isArray(document.items)?document.items:[];items.push(...page);if(page.length<200)break;offset+=200;if(offset>5000)throw new Error(`${domain.toUpperCase()} recommendation pagination exceeded safety bound.`)}return items}
async function readAssetDetail(item){const key=detailKey(item);if(detailCache.has(key))return detailCache.get(key);const detail=await recRequest(`/v1/presentation/assets/${encodeURIComponent(item.domain_id)}/${encodeURIComponent(item.asset_id)}`);detailCache.set(key,detail);return detail}
async function hydrateCryptoResearch(){const items=catalog?.crypto||[];await Promise.all(items.map(readAssetDetail))}
async function hydrateMetalsResearch(){const items=(catalog?.metals||[]).filter(item=>!isBil(item));await Promise.all(items.map(readAssetDetail))}

const mtgResearchCache=new Map();

function isSecretLairPremiumCandidate(item){
  return String(item?.asset_id||"").startsWith("SECRET_LAIR_V1_1|");
}

async function readMtgPremiumResearch(item){
  const key=detailKey(item);
  if(mtgResearchCache.has(key))return mtgResearchCache.get(key);
  const detail=await recRequest(`/v1/presentation/mtg-research/${encodeURIComponent(item.asset_id)}`);
  mtgResearchCache.set(key,detail);
  return detail;
}

async function hydrateMtgPremiumResearch(items){
  const candidates=items.filter(isSecretLairPremiumCandidate);
  await Promise.all(candidates.map(async item=>{
    try{
      await readMtgPremiumResearch(item);
    }catch(error){
      mtgResearchCache.set(detailKey(item),{
        premium_research:null,
        premium_research_error:String(error?.message||error||"Unavailable")
      });
    }
  }));
}

function mtgPremiumDetail(item){
  return mtgResearchCache.get(detailKey(item))||null;
}

function mtgPremiumPayload(item){
  const detail=mtgPremiumDetail(item);
  return detail&&typeof detail.premium_research==="object"&&detail.premium_research!==null
    ?detail.premium_research
    :null;
}

function mtgPremiumValue(item,key){
  const premium=mtgPremiumPayload(item);
  return premium?premium[key]:null;
}


function ensureMetalsVisualStyles(){
  if(document.getElementById("metals-v3-visual-styles"))return;
  const style=document.createElement("style");
  style.id="metals-v3-visual-styles";
  style.textContent=`
  .metals-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:14px}
  .metals-card-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
  .metals-card{border:1px solid var(--line);border-radius:14px;background:linear-gradient(145deg,rgba(18,37,34,.96),rgba(9,23,21,.98));padding:18px;display:grid;gap:14px;min-height:250px;box-shadow:var(--shadow)}
  .metals-card-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.metals-asset-id{display:flex;align-items:center;gap:10px}.metals-symbol{width:38px;height:38px;border-radius:50%;display:grid;place-items:center;background:rgba(99,230,190,.10);border:1px solid rgba(99,230,190,.28);color:var(--accent);font-weight:900;font-size:10px}
  .metals-asset-name{display:grid;gap:3px}.metals-asset-name strong{font-size:14px}.metals-asset-name small{font-size:9px;color:var(--muted)}.metals-status{border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:9px;text-transform:uppercase;color:var(--accent);background:rgba(99,230,190,.06)}
  .metals-kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.metals-kpi span{display:block;color:var(--muted);font-size:9px}.metals-kpi strong{display:block;margin-top:4px;font-size:18px}
  .metals-momentum{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.metals-momentum div{border:1px solid rgba(36,65,59,.7);border-radius:9px;padding:8px;background:rgba(7,19,16,.45)}.metals-momentum span{display:block;font-size:8px;color:var(--muted)}.metals-momentum strong{display:block;margin-top:4px;font-size:12px}
  .metals-regime-track{height:8px;border-radius:999px;background:linear-gradient(90deg,rgba(255,123,123,.8),rgba(255,207,102,.8),rgba(99,230,190,.8));position:relative}.metals-regime-dot{position:absolute;top:50%;width:12px;height:12px;border-radius:50%;background:var(--text);border:2px solid #07100f;transform:translate(-50%,-50%)}.metals-track-labels{display:flex;justify-content:space-between;color:var(--muted);font-size:8px;margin-top:5px}
  .metals-card-foot{display:flex;justify-content:space-between;gap:10px;align-items:end}.metals-tactical-mini span{display:block;color:var(--muted);font-size:8px}.metals-tactical-mini strong{display:block;font-size:11px;margin-top:3px}
  .metals-explainer{border:1px solid var(--line);border-radius:14px;padding:18px;background:linear-gradient(145deg,rgba(18,37,34,.9),rgba(10,24,22,.95));align-self:stretch}.metals-explainer h4{margin:0 0 16px}.metals-explainer-item{display:grid;grid-template-columns:34px 1fr;gap:10px;margin:16px 0}.metals-explainer-icon{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;border:1px solid rgba(99,230,190,.28);color:var(--accent)}.metals-explainer strong{font-size:10px}.metals-explainer p{font-size:9px;color:var(--muted);line-height:1.55;margin:4px 0 0}
  .metals-secondary-table{margin-top:22px}.metals-secondary-table summary{cursor:pointer;color:var(--text);font-weight:800;padding:14px 0}.metals-reference-note{border:1px dashed rgba(255,207,102,.35);background:rgba(255,207,102,.05);border-radius:10px;padding:10px 12px;font-size:9px;color:var(--muted);margin-top:12px}
  .metals-hero{border:1px solid var(--line);border-radius:16px;padding:24px;background:linear-gradient(135deg,rgba(18,37,34,.98),rgba(8,24,20,.98));display:grid;grid-template-columns:1.2fr .8fr;gap:20px;box-shadow:var(--shadow)}.metals-hero h3{font-size:27px;margin:10px 0}.metals-hero-copy{color:var(--muted);line-height:1.55;font-size:10px}.metals-hero-side{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.metals-hero-metric{border:1px solid var(--line);border-radius:11px;padding:13px;background:rgba(7,19,16,.45)}.metals-hero-metric span{display:block;color:var(--muted);font-size:8px}.metals-hero-metric strong{display:block;margin-top:5px;font-size:16px}
  .metals-detail-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:12px 0}.metals-detail-kpis article{border:1px solid var(--line);border-radius:12px;padding:15px;background:rgba(18,37,34,.88)}.metals-detail-kpis span{font-size:8px;color:var(--muted)}.metals-detail-kpis strong{display:block;font-size:20px;margin-top:6px}
  .metals-detail-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(280px,.75fr);gap:14px}.metals-panel{border:1px solid var(--line);border-radius:14px;padding:18px;background:rgba(13,27,25,.92)}.metals-panel h4{margin:0 0 6px}.metals-panel-sub{color:var(--muted);font-size:9px;line-height:1.5;margin-bottom:14px}
  .metals-momentum-bars{display:grid;gap:10px}.metals-bar-row{display:grid;grid-template-columns:80px 1fr 62px;gap:10px;align-items:center;font-size:9px}.metals-bar-track{height:9px;border-radius:999px;background:#071310;position:relative;overflow:hidden}.metals-bar-fill{position:absolute;top:0;bottom:0;left:50%;background:var(--accent);border-radius:999px}.metals-bar-fill.negative{right:50%;left:auto;background:var(--bad)}
  @media(max-width:1100px){.metals-layout,.metals-detail-grid,.metals-hero{grid-template-columns:1fr}.metals-card-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:720px){.metals-card-grid,.metals-detail-kpis{grid-template-columns:1fr}.metals-hero-side{grid-template-columns:1fr 1fr}}
  `;
  document.head.appendChild(style);
}

function renderDomainSummary(domain,items){let title="Domain-native research",note="Recommendations remain domain-specific; no cross-domain rank is created.",lens="Domain-native",icon="◆";if(domain==="crypto"){title="3-year growth outlook";note="36-month outlook, long-term risk, and shorter-horizon entry context.";lens="3Y Growth oriented";icon="₿"}if(domain==="metals"){title="Long-term thesis + tactical opportunity";note="Certified recommendation, risk, and forecast evidence remain inside Metals.";lens="Long-term tactical";icon="△"}if(domain==="mtg"){title="Native sealed-product opportunity";note="Native rank and purchase semantics stay inside MTG; no universal rank is created.";lens="Collection focused";icon="✦"}const heights=domain==="crypto"?[22,35,28,53,46,69]:domain==="metals"?[18,23,31,29,44,60]:[13,28,20,39,47,62];return `<article class="rec-domain-card ${escapeHtml(domain)}"><div class="rec-domain-top"><div class="rec-domain-name"><span class="rec-domain-icon">${icon}</span><span>${escapeHtml(domain.toUpperCase())}</span></div><span class="rec-lens-chip">${escapeHtml(lens)}</span></div><p><strong style="color:var(--text)">${escapeHtml(title)}</strong><br>${escapeHtml(note)}</p><div class="rec-domain-viz" aria-hidden="true">${heights.map(h=>`<i style="height:${h}%"></i>`).join("")}</div><div class="rec-domain-foot"><span><strong>${escapeHtml(items.length)}</strong> assets · Active</span><button type="button" class="secondary rec-open-domain" data-rec-domain="${escapeHtml(domain)}">Browse research ↗</button></div></article>`}

function cryptoCard(item){const detail=detailCache.get(detailKey(item));const f=crypto36(detail);const level=riskLevel(detail,item);const status=cleanStatus(nativeStatus(item));const returnValue=f?.expected_return;const positive=Number(returnValue)>0;return `<article class="rec-asset-card"><div class="rec-asset-head"><div class="rec-asset-id"><span class="rec-coin">${escapeHtml(coinLabel(item))}</span><span class="rec-asset-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_symbol||item.asset_id||"")}</small></span></div><span class="rec-status ${String(status).toLowerCase()}">${escapeHtml(status)}</span></div><div class="rec-card-kpis"><div class="rec-card-kpi"><span>3Y expected return</span><strong class="${positive?"positive":""}">${escapeHtml(fmtPercent(returnValue))}</strong></div><div class="rec-card-kpi"><span>3Y base forecast</span><strong>${escapeHtml(fmtMoney(f?.point_forecast))}</strong></div></div><div class="rec-scenario-labels"><span>Bear</span><span>Base</span><span>Bull</span></div><div class="rec-scenario-values"><span>${escapeHtml(fmtMoney(f?.lower_bound))}</span><span>${escapeHtml(fmtMoney(f?.point_forecast))}</span><span>${escapeHtml(fmtMoney(f?.upper_bound))}</span></div><div class="rec-range"><i class="rec-range-dot" style="left:${rangePosition(f)}%"></i></div>${svgSparkline(detail)}<div class="rec-card-foot"><div class="rec-risk-mini"><span>Long-term risk</span><strong>${escapeHtml(level)}</strong>${riskBars(level)}</div><button type="button" class="rec-research-button rec-crypto-detail" data-asset-id="${escapeHtml(item.asset_id)}">Research ↗</button></div></article>`}
function renderExplainer(){return `<aside class="rec-explainer"><h4>Why this view is useful</h4><div class="rec-explainer-item"><span class="rec-explainer-icon">↗</span><div><strong>3-Year strategic outlook</strong><p>Lead with the certified 36-month expected return and scenario range to evaluate long-term opportunity.</p></div></div><div class="rec-explainer-item"><span class="rec-explainer-icon">◈</span><div><strong style="color:var(--warn)">Long-term risk</strong><p>Risk evidence stays separate from return so upside and downside can be evaluated together.</p></div></div><div class="rec-explainer-item"><span class="rec-explainer-icon">◎</span><div><strong style="color:var(--accent2)">Current entry context</strong><p>Shorter horizons inform accumulation timing while 36 months remains the strategic objective.</p></div></div><div class="rec-governance-callout">Research is domain-native. Execution is not authorized by UIP. Rows are not a UIP-created rank.</div></aside>`}

function isBil(item){const symbol=String(item?.asset_symbol||"").toUpperCase();const id=String(item?.asset_id||"").toUpperCase();return symbol==="BIL"||id.endsWith(":BIL")||id.includes("VEHICLE:BIL")}
function tacticalPayload(detail){return firstPayload(detail,"tactical_state")||null}
function tacticalState(detail){return tacticalPayload(detail)?.tactical_state??"TACTICAL_STATE_UNAVAILABLE"}
function tacticalRegime(detail){return tacticalPayload(detail)?.candidate_regime??"REGIME_UNAVAILABLE"}
function tacticalPosition(detail){const state=tacticalState(detail);if(state==="TACTICAL_DEFENSIVE")return 12;if(state==="TACTICAL_SUPPORTIVE")return 88;return 50}
function metalsForecast(detail){const rows=allForecasts(detail);return rows.find(row=>Number(row.forecast_horizon_months)===36)||rows.at(-1)||null}
function metalsScore(item){const p=item.payload||{};return p.normalized_score??p.domain_score??null}
function metalsConfidence(item){const p=item.payload||{};return p.confidence_score??p.confidence??null}
function metalsCard(item){const detail=detailCache.get(detailKey(item));const t=tacticalPayload(detail)||{};const f=metalsForecast(detail);const status=cleanStatus(nativeStatus(item));const score=metalsScore(item);const confidence=metalsConfidence(item);const drawdown=t.current_drawdown_pct;return `<article class="metals-card"><div class="metals-card-head"><div class="metals-asset-id"><span class="metals-symbol">${escapeHtml(metalLabel(item))}</span><span class="metals-asset-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_symbol||item.asset_id||"")}</small></span></div><span class="metals-status">${escapeHtml(status)}</span></div><div class="metals-kpis"><div class="metals-kpi"><span>Domain score</span><strong>${escapeHtml(fmtNumber(score))}</strong></div><div class="metals-kpi"><span>Confidence</span><strong>${escapeHtml(fmtNumber(confidence))}</strong></div><div class="metals-kpi"><span>Forecast return</span><strong>${escapeHtml(f?fmtPercent(f.expected_return):"—")}</strong></div><div class="metals-kpi"><span>Current drawdown</span><strong class="${Number(drawdown)<0?"negative":""}">${escapeHtml(fmtPctPoint(drawdown))}</strong></div></div><div><div class="metals-momentum"><div><span>1M momentum</span><strong>${escapeHtml(fmtPctPoint(t.return_1m_pct))}</strong></div><div><span>3M momentum</span><strong>${escapeHtml(fmtPctPoint(t.return_3m_pct))}</strong></div><div><span>6M momentum</span><strong>${escapeHtml(fmtPctPoint(t.return_6m_pct))}</strong></div></div><div style="margin-top:12px"><div class="metals-regime-track"><i class="metals-regime-dot" style="left:${tacticalPosition(detail)}%"></i></div><div class="metals-track-labels"><span>Defensive</span><span>Neutral</span><span>Supportive</span></div></div></div><div class="metals-card-foot"><div class="metals-tactical-mini"><span>Tactical context</span><strong>${escapeHtml(cleanStatus(tacticalState(detail)))}</strong><span>${escapeHtml(cleanStatus(tacticalRegime(detail)))}</span></div><button type="button" class="rec-research-button rec-metals-detail" data-asset-id="${escapeHtml(item.asset_id)}">Research ↗</button></div></article>`}
function renderMetalsExplainer(){return `<aside class="metals-explainer"><h4>Why this view is useful</h4><div class="metals-explainer-item"><span class="metals-explainer-icon">↗</span><div><strong>Long-term thesis first</strong><p>Native Metals recommendation, forecast, and risk remain the strategic authority.</p></div></div><div class="metals-explainer-item"><span class="metals-explainer-icon">◎</span><div><strong>Current tactical context</strong><p>1M/3M/6M momentum, drawdown, trend distance, and regime interpretation help frame current conditions.</p></div></div><div class="metals-explainer-item"><span class="metals-explainer-icon">◇</span><div><strong>Separate decision layers</strong><p>No tactical overlay is not a sell signal and does not erase a constructive long-term thesis.</p></div></div><div class="metals-reference-note"><strong>BIL is reference/control only.</strong><br>It remains available in the secondary research table but is excluded from featured opportunity cards.</div></aside>`}

function bindDomainButtons(page){page.querySelectorAll(".rec-open-domain").forEach(button=>button.addEventListener("click",()=>openDomain(button.dataset.recDomain)));page.querySelectorAll(".rec-crypto-detail").forEach(button=>button.addEventListener("click",()=>openCryptoDetail(button.dataset.assetId)));page.querySelectorAll(".rec-metals-detail").forEach(button=>button.addEventListener("click",()=>openMetalsDetail(button.dataset.assetId)))}
function renderAll(){const page=node("recommendations");const crypto=catalog?.crypto||[];page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-shell"><section class="rec-hero"><div class="rec-intro"><span class="eyebrow">RECOMMENDATIONS</span><h2>Investment research ✦</h2><p>Domain-native research, long-term thesis first. Current entry context second.</p><span class="rec-intro-link">How we research ↗</span></div><div class="rec-domain-grid">${REC_DOMAINS.map(domain=>renderDomainSummary(domain,catalog[domain]||[])).join("")}</div></section><section><div class="rec-section-head"><div><span class="eyebrow">FEATURED DOMAIN</span><h3>Crypto research <span class="rec-count-chip">${crypto.length} assets</span></h3></div><div class="rec-section-head-actions"><button type="button" class="secondary rec-open-domain" data-rec-domain="crypto">View all crypto research</button></div></div><div class="rec-crypto-layout" style="margin-top:14px"><div class="rec-asset-grid">${crypto.map(cryptoCard).join("")}</div>${renderExplainer()}</div></section><p class="governance-note">UIP keeps Crypto, Metals, and MTG as separate decision systems. This surface exposes certified investment evidence without manufacturing a universal score, cross-domain ranking, or automatic purchase decision.</p></div>`;bindDomainButtons(page)}


function ensureMtgPremiumVisualStyles(){
  if(document.getElementById("mtg-premium-visual-styles"))return;
  const style=document.createElement("style");
  style.id="mtg-premium-visual-styles";
  style.textContent=`
  .mtg-premium-shell{display:grid;gap:16px}
  .mtg-premium-hero{border:1px solid var(--line);border-radius:16px;padding:24px;background:linear-gradient(135deg,rgba(35,25,48,.98),rgba(12,22,28,.98));box-shadow:var(--shadow);display:grid;grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr);gap:22px}
  .mtg-premium-hero h3{font-size:28px;margin:8px 0}
  .mtg-premium-hero p{font-size:10px;line-height:1.6;color:var(--muted);max-width:780px}
  .mtg-premium-hero-stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .mtg-premium-hero-stat{border:1px solid rgba(186,153,255,.24);background:rgba(20,14,31,.5);border-radius:11px;padding:13px}
  .mtg-premium-hero-stat span{display:block;color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.08em}
  .mtg-premium-hero-stat strong{display:block;margin-top:5px;font-size:16px}
  .mtg-premium-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
  .mtg-premium-card{border:1px solid rgba(186,153,255,.22);border-radius:14px;background:linear-gradient(145deg,rgba(28,22,39,.96),rgba(10,22,25,.98));padding:17px;display:grid;gap:13px;min-height:290px;box-shadow:var(--shadow)}
  .mtg-premium-card.native-only{border-color:var(--line);background:rgba(13,27,25,.94)}
  .mtg-premium-card-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
  .mtg-premium-name{display:grid;gap:4px}
  .mtg-premium-name strong{font-size:13px;line-height:1.35}
  .mtg-premium-name small{font-size:8px;color:var(--muted);word-break:break-all}
  .mtg-rank-chip,.mtg-state-chip{border:1px solid rgba(186,153,255,.28);border-radius:999px;padding:4px 8px;font-size:8px;white-space:nowrap;color:#d8c5ff;background:rgba(128,87,187,.12)}
  .mtg-state-chip.entry{border-color:rgba(99,230,190,.35);color:var(--accent);background:rgba(99,230,190,.08)}
  .mtg-state-chip.wait{border-color:rgba(255,207,102,.35);color:#ffcf66;background:rgba(255,207,102,.06)}
  .mtg-premium-kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .mtg-premium-kpi{border:1px solid rgba(255,255,255,.07);border-radius:9px;padding:9px;background:rgba(4,12,14,.28)}
  .mtg-premium-kpi span{display:block;color:var(--muted);font-size:8px}
  .mtg-premium-kpi strong{display:block;margin-top:4px;font-size:14px}
  .mtg-entry-panel{border:1px solid rgba(255,207,102,.28);background:rgba(255,207,102,.055);border-radius:10px;padding:11px}
  .mtg-entry-panel .label{font-size:8px;color:#ffcf66;text-transform:uppercase;letter-spacing:.08em}
  .mtg-entry-panel strong{font-size:18px;display:block;margin-top:4px}
  .mtg-entry-panel small{display:block;color:var(--muted);font-size:8px;margin-top:4px;line-height:1.45}
  .mtg-scenario-strip{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .mtg-scenario-strip div{border:1px solid rgba(255,255,255,.07);border-radius:9px;padding:9px}
  .mtg-scenario-strip span{display:block;color:var(--muted);font-size:8px}
  .mtg-scenario-strip strong{font-size:12px;display:block;margin-top:4px}
  .mtg-native-note{font-size:8px;line-height:1.5;color:var(--muted)}
  .mtg-premium-toolbar{display:grid;grid-template-columns:minmax(0,1fr) 220px;gap:10px}
  .mtg-detail-hero{border:1px solid rgba(186,153,255,.26);border-radius:16px;padding:24px;background:linear-gradient(135deg,rgba(34,25,47,.98),rgba(8,25,24,.98));display:grid;grid-template-columns:minmax(0,1.25fr) minmax(300px,.75fr);gap:20px;box-shadow:var(--shadow)}
  .mtg-detail-title h3{font-size:29px;margin:7px 0}
  .mtg-detail-title p{font-size:9px;color:var(--muted);line-height:1.6}
  .mtg-detail-price{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
  .mtg-detail-price article{border:1px solid rgba(255,255,255,.08);border-radius:11px;padding:13px;background:rgba(5,15,17,.42)}
  .mtg-detail-price span{font-size:8px;color:var(--muted)}
  .mtg-detail-price strong{font-size:19px;display:block;margin-top:5px}
  .mtg-detail-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(280px,.65fr);gap:14px}
  .mtg-research-panel{border:1px solid var(--line);border-radius:14px;background:rgba(13,27,25,.94);padding:18px}
  .mtg-research-panel h4{margin:0 0 5px}
  .mtg-research-sub{font-size:9px;color:var(--muted);line-height:1.55;margin-bottom:14px}
  .mtg-q10-callout{border:1px solid rgba(255,207,102,.30);border-radius:12px;padding:16px;background:rgba(255,207,102,.06)}
  .mtg-q10-callout strong{display:block;font-size:24px;margin:5px 0}
  .mtg-q10-callout span{font-size:8px;color:#ffcf66;text-transform:uppercase;letter-spacing:.08em}
  .mtg-q10-callout p{font-size:9px;color:var(--muted);line-height:1.55;margin:7px 0 0}
  .mtg-range-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
  .mtg-range-grid article{border:1px solid rgba(255,255,255,.07);border-radius:10px;padding:11px;background:rgba(5,15,17,.34)}
  .mtg-range-grid span{font-size:8px;color:var(--muted)}
  .mtg-range-grid strong{display:block;font-size:14px;margin-top:4px}
  .mtg-scenario-table{width:100%;border-collapse:collapse}
  .mtg-scenario-table th,.mtg-scenario-table td{padding:9px;border-bottom:1px solid rgba(255,255,255,.06);font-size:9px;text-align:right}
  .mtg-scenario-table th:first-child,.mtg-scenario-table td:first-child{text-align:left}
  .mtg-evidence-list{display:grid;gap:9px}
  .mtg-evidence-list div{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid rgba(255,255,255,.06);padding-bottom:8px;font-size:9px}
  .mtg-evidence-list span{color:var(--muted)}
  .mtg-scenario-warning{border:1px dashed rgba(186,153,255,.35);border-radius:10px;padding:11px;color:var(--muted);font-size:9px;line-height:1.55;background:rgba(128,87,187,.055)}
  @media(max-width:1100px){.mtg-premium-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.mtg-premium-hero,.mtg-detail-hero,.mtg-detail-grid{grid-template-columns:1fr}}
  @media(max-width:720px){.mtg-premium-grid,.mtg-premium-toolbar,.mtg-detail-price{grid-template-columns:1fr}}
  `;
  document.head.appendChild(style);
}

function mtgEntryStateClass(value){
  const state=String(value||"").toUpperCase();
  if(state.includes("BELOW")||state.includes("AT_Q10")||state.includes("BUY"))return "entry";
  return "wait";
}

function mtgPremiumCard(item){
  const p=item.payload||{};
  const premium=mtgPremiumPayload(item);
  const rank=p.native_rank==null?"?":fmtNumber(p.native_rank,0);
  const status=cleanStatus(nativeStatus(item));

  if(!premium){
    return `<article class="mtg-premium-card native-only">
      <div class="mtg-premium-card-head">
        <div class="mtg-premium-name">
          <strong>${escapeHtml(displayName(item))}</strong>
          <small>${escapeHtml(item.asset_id||"")}</small>
        </div>
        <span class="mtg-rank-chip">Native rank ${escapeHtml(rank)}</span>
      </div>
      <div>
        <span class="mtg-state-chip">${escapeHtml(status)}</span>
      </div>
      <div class="mtg-native-note">
        Premium research unavailable for this lane. UIP does not synthesize Secret Lair price or forecast authority for Collector or Pre-Collector records.
      </div>
      <div class="mtg-premium-kpis">
        <div class="mtg-premium-kpi"><span>Evidence</span><strong>${escapeHtml(cleanStatus(p.evidence_state))}</strong></div>
        <div class="mtg-premium-kpi"><span>Actionability</span><strong>${escapeHtml(cleanStatus(p.actionability_state))}</strong></div>
      </div>
      <div class="mtg-native-note">Recommendation does not authorize execution.</div>
    </article>`;
  }

  const q10State=premium.current_price_vs_q10_break_even_state;
  return `<article class="mtg-premium-card">
    <div class="mtg-premium-card-head">
      <div class="mtg-premium-name">
        <strong>${escapeHtml(premium.product_name||displayName(item))}</strong>
        <small>${escapeHtml(item.asset_id||"")}</small>
      </div>
      <span class="mtg-rank-chip">Native rank ${escapeHtml(rank)}</span>
    </div>
    <div style="display:flex;gap:7px;flex-wrap:wrap">
      <span class="mtg-state-chip">${escapeHtml(status)}</span>
      <span class="mtg-state-chip ${mtgEntryStateClass(q10State)}">${escapeHtml(cleanStatus(q10State))}</span>
    </div>
    <div class="mtg-premium-kpis">
      <div class="mtg-premium-kpi"><span>Current market</span><strong>${escapeHtml(fmtMoney(premium.current_tcg_market_price_usd))}</strong></div>
      <div class="mtg-premium-kpi"><span>Certified 1Y outlook</span><strong>${escapeHtml(fmtPercent(premium.certified_1y_point_return))}</strong></div>
    </div>
    <div class="mtg-entry-panel">
      <span class="label">Governed Q10 entry</span>
      <strong>${escapeHtml(fmtMoney(premium.y1_q10_break_even_entry_price_usd))}</strong>
      <small>Current margin to governed Q10: ${escapeHtml(fmtMoney(premium.current_price_margin_to_q10_break_even))}. Q25/Q50 do not replace this purchase threshold.</small>
    </div>
    <div class="mtg-scenario-strip">
      <div><span>3Y scenario median</span><strong>${escapeHtml(fmtPercent(premium.y3_median_total_return_scenario))}</strong></div>
      <div><span>5Y scenario median</span><strong>${escapeHtml(fmtPercent(premium.y5_median_total_return_scenario))}</strong></div>
    </div>
    <button type="button" class="secondary rec-mtg-premium-detail" data-asset-id="${escapeHtml(item.asset_id)}">Open investment research ?</button>
  </article>`;
}

function bindMtgPremiumButtons(page,items){
  const byId=new Map(items.map(item=>[String(item.asset_id),item]));
  page.querySelectorAll(".rec-mtg-premium-detail").forEach(button=>{
    button.addEventListener("click",()=>{
      const item=byId.get(String(button.dataset.assetId));
      if(item)openMtgPremiumDetail(page,item);
    });
  });
}

async function renderMtgDomain(page,all,filtered,statusOptions,start,maxPage){
  ensureMtgPremiumVisualStyles();

  const visible=filtered.slice(start,start+REC_PAGE_SIZE);

  page.innerHTML=`${recommendationDomainSummaryAnchor()}
    <div class="rec-shell mtg-premium-shell">
      <div class="rec-section-head">
        <div>
          <span class="eyebrow">MTG INVESTMENT RESEARCH</span>
          <h3>Sealed-product opportunity <span class="rec-count-chip">${filtered.length} matching ? ${all.length} total</span></h3>
        </div>
        <button type="button" id="rec-all-domains" class="secondary">All domains</button>
      </div>
      <p class="governance-note">Native MTG rank remains MTG-only. Secret Lair premium authority is loaded from the certified MTG research endpoint; missing premium authority remains missing. Recommendation does not authorize execution.</p>
      <div class="mtg-premium-toolbar">
        <input id="rec-search" value="${escapeHtml(searchText)}" placeholder="Search sealed product, ID, lane, or native status...">
        <select id="rec-status">${statusOptions}</select>
      </div>
      <article class="mtg-premium-hero">
        <div>
          <span class="eyebrow">SECRET LAIR PREMIUM RESEARCH</span>
          <h3>Price discipline first. Long-term scenario context second.</h3>
          <p>UIP shows the governed Q10 entry threshold beside the certified one-year outlook. Three- and five-year values remain scenario distributions and never become direct certified forecasts or purchase triggers.</p>
        </div>
        <div class="mtg-premium-hero-stats">
          <div class="mtg-premium-hero-stat"><span>Visible assets</span><strong>${visible.length}</strong></div>
          <div class="mtg-premium-hero-stat"><span>Premium lane</span><strong>Secret Lair</strong></div>
          <div class="mtg-premium-hero-stat"><span>Purchase gate</span><strong>1Y Q10</strong></div>
          <div class="mtg-premium-hero-stat"><span>Execution</span><strong>Manual only</strong></div>
        </div>
      </article>
      <div id="mtg-premium-card-grid" class="mtg-premium-grid">
        ${visible.map(item=>`<article class="mtg-premium-card native-only"><div class="mtg-premium-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_id||"")}</small></div><div class="mtg-native-note">${isSecretLairPremiumCandidate(item)?"Loading certified premium research?":"Native MTG authority ? premium research unavailable for this lane."}</div></article>`).join("")}
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:12px">
        <span class="page-note">Rows ${filtered.length?start+1:0}-${Math.min(start+REC_PAGE_SIZE,filtered.length)} of ${filtered.length}</span>
        <div style="display:flex;gap:8px">
          <button type="button" id="rec-prev" class="secondary" ${pageIndex===0?"disabled":""}>Previous</button>
          <button type="button" id="rec-next" class="secondary" ${pageIndex>=maxPage?"disabled":""}>Next</button>
        </div>
      </div>
    </div>`;

  bindDomainControls(page,maxPage);

  await hydrateMtgPremiumResearch(visible);

  if(selectedDomain!=="mtg")return;

  const grid=page.querySelector("#mtg-premium-card-grid");
  if(!grid)return;

  grid.innerHTML=visible.map(mtgPremiumCard).join("");
  bindMtgPremiumButtons(page,visible);
}

async function openMtgPremiumDetail(page,item){
  ensureMtgPremiumVisualStyles();

  let detail=mtgPremiumDetail(item);

  if(!detail){
    page.innerHTML=`<div class="rec-shell"><p class="governance-note">Loading certified MTG premium research?</p></div>`;
    detail=await readMtgPremiumResearch(item);
  }

  const premium=detail?.premium_research||null;
  const p=item.payload||{};

  if(!premium){
    page.innerHTML=`${recommendationDomainSummaryAnchor()}
      <div class="rec-shell">
        <div class="rec-section-head">
          <div><span class="eyebrow">MTG RESEARCH</span><h3>${escapeHtml(displayName(item))}</h3></div>
          <button type="button" id="mtg-premium-back" class="secondary">Back to MTG research</button>
        </div>
        <article class="mtg-research-panel">
          <h4>Premium research unavailable for this lane</h4>
          <p class="mtg-research-sub">UIP does not synthesize Secret Lair premium authority for this MTG asset. Collector and Pre-Collector governance remains unchanged.</p>
          <div class="mtg-evidence-list">
            <div><span>Native status</span><strong>${escapeHtml(cleanStatus(nativeStatus(item)))}</strong></div>
            <div><span>Native rank</span><strong>${escapeHtml(p.native_rank==null?"?":fmtNumber(p.native_rank,0))}</strong></div>
            <div><span>Evidence</span><strong>${escapeHtml(cleanStatus(p.evidence_state))}</strong></div>
            <div><span>Actionability</span><strong>${escapeHtml(cleanStatus(p.actionability_state))}</strong></div>
          </div>
        </article>
      </div>`;
    const back=page.querySelector("#mtg-premium-back");
    if(back)back.addEventListener("click",()=>renderDomain());
    return;
  }

  const nativeRank=p.native_rank==null?"?":fmtNumber(p.native_rank,0);
  const q10State=cleanStatus(premium.current_price_vs_q10_break_even_state);

  page.innerHTML=`${recommendationDomainSummaryAnchor()}
    <div class="rec-shell mtg-premium-shell">
      <div class="rec-section-head">
        <div><span class="eyebrow">MTG ? SECRET LAIR PREMIUM RESEARCH</span><h3>Investment research</h3></div>
        <button type="button" id="mtg-premium-back" class="secondary">Back to MTG research</button>
      </div>

      <article class="mtg-detail-hero">
        <div class="mtg-detail-title">
          <span class="eyebrow">${escapeHtml(cleanStatus(nativeStatus(item)))}</span>
          <h3>${escapeHtml(premium.product_name||displayName(item))}</h3>
          <p>${escapeHtml(item.asset_id||"")} ? Native rank ${escapeHtml(nativeRank)}. MTG native rank is used only inside MTG and cannot override the governed Q10 purchase policy.</p>
        </div>
        <div class="mtg-detail-price">
          <article><span>Current market price</span><strong>${escapeHtml(fmtMoney(premium.current_tcg_market_price_usd))}</strong></article>
          <article><span>Governed Q10 entry</span><strong>${escapeHtml(fmtMoney(premium.y1_q10_break_even_entry_price_usd))}</strong></article>
          <article><span>Certified 1Y forecast</span><strong>${escapeHtml(fmtMoney(premium.certified_1y_point_forecast_usd))}</strong></article>
          <article><span>Certified 1Y return</span><strong>${escapeHtml(fmtPercent(premium.certified_1y_point_return))}</strong></article>
        </div>
      </article>

      <div class="mtg-detail-grid">
        <div style="display:grid;gap:14px">
          <article class="mtg-research-panel">
            <h4>Governed Q10 entry discipline</h4>
            <p class="mtg-research-sub">Secret Lair BUY eligibility remains tied to the governed one-year Q10 break-even threshold. Q25 and Q50 are diagnostic context only.</p>
            <div class="mtg-q10-callout">
              <span>Current price vs Q10 state</span>
              <strong>${escapeHtml(q10State)}</strong>
              <p>Current market ${escapeHtml(fmtMoney(premium.current_tcg_market_price_usd))} ? Q10 break-even entry ${escapeHtml(fmtMoney(premium.y1_q10_break_even_entry_price_usd))} ? margin ${escapeHtml(fmtMoney(premium.current_price_margin_to_q10_break_even))}</p>
            </div>
          </article>

          <article class="mtg-research-panel">
            <h4>Certified 1Y outlook</h4>
            <p class="mtg-research-sub">Direct certified one-year forecast and modeled distribution.</p>
            <div class="mtg-range-grid">
              <article><span>Q10 terminal</span><strong>${escapeHtml(fmtMoney(premium.y1_q10_terminal_value_usd))}</strong></article>
              <article><span>Q50 terminal</span><strong>${escapeHtml(fmtMoney(premium.y1_q50_terminal_value_usd))}</strong></article>
              <article><span>Q90 terminal</span><strong>${escapeHtml(fmtMoney(premium.y1_q90_terminal_value_usd))}</strong></article>
            </div>
            <div class="mtg-range-grid" style="margin-top:9px">
              <article><span>Probability of loss</span><strong>${escapeHtml(fmtPercent(premium.y1_probability_of_loss))}</strong></article>
              <article><span>Positive return probability</span><strong>${escapeHtml(fmtPercent(premium.y1_probability_of_positive_return))}</strong></article>
              <article><span>Upside tail mean</span><strong>${escapeHtml(fmtPercent(premium.y1_upside_tail_mean_total_return))}</strong></article>
            </div>
          </article>

          <article class="mtg-research-panel">
            <h4>Longer-horizon scenarios</h4>
            <p class="mtg-research-sub">Three- and five-year outputs are scenario distributions, not direct certified forecasts and not purchase triggers.</p>
            <table class="mtg-scenario-table">
              <thead><tr><th>Scenario horizon</th><th>Q10 terminal</th><th>Q50 terminal</th><th>Q90 terminal</th><th>Median return</th><th>Loss probability</th></tr></thead>
              <tbody>
                <tr>
                  <td>3Y scenario</td>
                  <td>${escapeHtml(fmtMoney(premium.y3_q10_terminal_value_scenario_usd))}</td>
                  <td>${escapeHtml(fmtMoney(premium.y3_q50_terminal_value_scenario_usd))}</td>
                  <td>${escapeHtml(fmtMoney(premium.y3_q90_terminal_value_scenario_usd))}</td>
                  <td>${escapeHtml(fmtPercent(premium.y3_median_total_return_scenario))}</td>
                  <td>${escapeHtml(fmtPercent(premium.y3_probability_of_loss_scenario))}</td>
                </tr>
                <tr>
                  <td>5Y scenario</td>
                  <td>${escapeHtml(fmtMoney(premium.y5_q10_terminal_value_scenario_usd))}</td>
                  <td>${escapeHtml(fmtMoney(premium.y5_q50_terminal_value_scenario_usd))}</td>
                  <td>${escapeHtml(fmtMoney(premium.y5_q90_terminal_value_scenario_usd))}</td>
                  <td>${escapeHtml(fmtPercent(premium.y5_median_total_return_scenario))}</td>
                  <td>${escapeHtml(fmtPercent(premium.y5_probability_of_loss_scenario))}</td>
                </tr>
              </tbody>
            </table>
            <div class="mtg-scenario-warning" style="margin-top:12px">
              3Y and 5Y are scenarios only. UIP does not present these values as direct certified forecasts, does not use them to replace Q10, and does not authorize purchase execution from them.
            </div>
          </article>
        </div>

        <div style="display:grid;gap:14px;align-content:start">
          <article class="mtg-research-panel">
            <h4>Evidence strength</h4>
            <p class="mtg-research-sub">Historical depth and structural comparable support behind the premium analysis.</p>
            <div class="mtg-evidence-list">
              <div><span>Own-history evidence</span><strong>${escapeHtml(cleanStatus(premium.own_history_evidence_class))}</strong></div>
              <div><span>History span</span><strong>${escapeHtml(fmtNumber(premium.history_span_days,0))} days</strong></div>
              <div><span>Historical observations</span><strong>${escapeHtml(fmtNumber(premium.historical_observation_count,0))}</strong></div>
              <div><span>Exact structural products</span><strong>${escapeHtml(fmtNumber(premium.exact_structural_comparable_product_count,0))}</strong></div>
              <div><span>Global comparable products</span><strong>${escapeHtml(fmtNumber(premium.global_comparable_product_count,0))}</strong></div>
              <div><span>Exact comparable events</span><strong>${escapeHtml(fmtNumber(premium.exact_structural_comparable_event_count,0))}</strong></div>
              <div><span>Global comparable events</span><strong>${escapeHtml(fmtNumber(premium.global_comparable_event_count,0))}</strong></div>
            </div>
          </article>

          <article class="mtg-research-panel">
            <h4>Authority & governance</h4>
            <div class="mtg-evidence-list">
              <div><span>Native rank</span><strong>${escapeHtml(nativeRank)}</strong></div>
              <div><span>Native purchase status</span><strong>${escapeHtml(cleanStatus(nativeStatus(item)))}</strong></div>
              <div><span>Source authority</span><strong style="text-align:right;max-width:220px;word-break:break-word">${escapeHtml(premium.source_authority_path||"?")}</strong></div>
            </div>
            <p class="mtg-research-sub" style="margin-top:12px">No universal MTG rank or cross-domain rank is created. Recommendation does not authorize execution.</p>
          </article>
        </div>
      </div>
    </div>`;

  const back=page.querySelector("#mtg-premium-back");
  if(back)back.addEventListener("click",()=>renderDomain());
}

function filteredDomainItems(){let items=[...(catalog[selectedDomain]||[])];if(selectedDomain==="mtg"){items.sort((a,b)=>{const ar=Number(a.payload?.native_rank);const br=Number(b.payload?.native_rank);const aRank=Number.isFinite(ar);const bRank=Number.isFinite(br);if(aRank&&bRank&&ar!==br)return ar-br;if(aRank!==bRank)return aRank?-1:1;return String(a.record_key||"").localeCompare(String(b.record_key||""))})}if(selectedStatus!=="all")items=items.filter(item=>(nativeStatus(item)||"MISSING")===selectedStatus);if(searchText)items=items.filter(item=>searchKey(item).includes(searchText));return items}
function genericRows(items){return items.map(item=>{const p=item.payload||{};const horizon=p.time_horizon_months==null?"—":`${fmtNumber(p.time_horizon_months,0)} mo`;return `<tr><td><span class="position-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_symbol||item.asset_id||"")}</small></span></td><td>${escapeHtml(cleanStatus(nativeStatus(item)))}</td><td>${escapeHtml(fmtNumber(p.normalized_score))}</td><td>${escapeHtml(fmtNumber(p.confidence_score))}</td><td>${escapeHtml(horizon)}</td><td style="text-align:left;max-width:320px">${escapeHtml(p.rationale??"—")}</td><td style="text-align:left;max-width:260px">${escapeHtml(p.risk_summary??"—")}</td><td><button type="button" class="secondary rec-metals-detail" data-asset-id="${escapeHtml(item.asset_id)}">Research ↗</button></td></tr>`}).join("")}
function mtgRows(items){return items.map(item=>{const p=item.payload||{};const rank=p.native_rank==null?"—":`${fmtNumber(p.native_rank,0)}${p.native_rank_type?` · ${p.native_rank_type}`:""}`;return `<tr><td><span class="position-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_subclass||item.asset_id||"")}</small></span></td><td>${escapeHtml(cleanStatus(nativeStatus(item)))}</td><td>${escapeHtml(rank)}</td><td>${escapeHtml(p.evidence_state??"—")}</td><td>${escapeHtml(p.actionability_state??"—")}</td><td>${p.manual_execution_price_check_required===true?"Required":p.manual_execution_price_check_required===false?"No":"—"}</td><td>${p.execution_ready_purchase_certified===true?"Yes":p.execution_ready_purchase_certified===false?"No":"—"}</td><td>${p.automatic_purchase_execution===true?"Yes":p.automatic_purchase_execution===false?"No":"—"}</td></tr>`}).join("")}
function bindDomainControls(page,maxPage){node("rec-all-domains")?.addEventListener("click",()=>{selectedDomain="all";selectedStatus="all";searchText="";pageIndex=0;renderAll()});node("rec-search")?.addEventListener("input",event=>{searchText=event.target.value.trim().toLowerCase();pageIndex=0;renderDomain()});node("rec-status")?.addEventListener("change",event=>{selectedStatus=event.target.value;pageIndex=0;renderDomain()});node("rec-prev")?.addEventListener("click",()=>{if(pageIndex>0){pageIndex-=1;renderDomain()}});node("rec-next")?.addEventListener("click",()=>{if(pageIndex<maxPage){pageIndex+=1;renderDomain()}});page.querySelectorAll(".rec-crypto-detail").forEach(button=>button.addEventListener("click",()=>openCryptoDetail(button.dataset.assetId)));page.querySelectorAll(".rec-metals-detail").forEach(button=>button.addEventListener("click",()=>openMetalsDetail(button.dataset.assetId)))}
function renderCryptoDomain(page,all,filtered,statusOptions){page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-shell"><div class="rec-section-head"><div><span class="eyebrow">RECOMMENDATIONS</span><h3>Crypto research <span class="rec-count-chip">${filtered.length} matching · ${all.length} total</span></h3></div><button type="button" id="rec-all-domains" class="secondary">All domains</button></div><p class="governance-note">Crypto is presented 3-year first. Rows are not a UIP-created rank; shorter horizons are entry context only. Recommendation does not authorize execution.</p><div class="rec-toolbar"><input id="rec-search" value="${escapeHtml(searchText)}" placeholder="Search asset, symbol, or status..."><select id="rec-status">${statusOptions}</select><button type="button" class="secondary" disabled>36-month strategic outlook</button></div><div class="rec-crypto-layout"><div class="rec-asset-grid">${filtered.map(cryptoCard).join("")}</div>${renderExplainer()}</div></div>`;bindDomainControls(page,0)}
function renderMetalsDomain(page,all,filtered,statusOptions,start,maxPage){ensureMetalsVisualStyles();const featured=filtered.filter(item=>!isBil(item));const visibleTable=filtered.slice(start,start+REC_PAGE_SIZE);const table=`<table style="min-width:1380px"><thead><tr><th>Asset</th><th>Native recommendation</th><th>Domain score</th><th>Confidence</th><th>Horizon</th><th>Rationale</th><th>Risk</th><th>Detail</th></tr></thead><tbody>${genericRows(visibleTable)}</tbody></table>`;page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-shell"><div class="rec-section-head"><div><span class="eyebrow">METALS RESEARCH</span><h3>Long-term thesis + tactical opportunity <span class="rec-count-chip">${featured.length} featured · ${all.length} total</span></h3></div><button type="button" id="rec-all-domains" class="secondary">All domains</button></div><p class="governance-note">Metals is long-term thesis first, tactical context second. Featured cards exclude BIL. Tactical states do not authorize execution.</p><div class="rec-toolbar"><input id="rec-search" value="${escapeHtml(searchText)}" placeholder="Search metal, vehicle, or status..."><select id="rec-status">${statusOptions}</select><button type="button" class="secondary" disabled>Long-term + tactical</button></div><div class="metals-layout"><div class="metals-card-grid">${featured.map(metalsCard).join("")}</div>${renderMetalsExplainer()}</div><details class="metals-secondary-table" open><summary>All Metals research · secondary evidence table</summary><div class="table-wrap">${table}</div><div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:14px"><span class="page-note">Rows ${filtered.length?start+1:0}-${Math.min(start+REC_PAGE_SIZE,filtered.length)} of ${filtered.length}</span><div style="display:flex;gap:8px"><button type="button" id="rec-prev" class="secondary" ${pageIndex===0?"disabled":""}>Previous</button><button type="button" id="rec-next" class="secondary" ${pageIndex>=maxPage?"disabled":""}>Next</button></div></div></details></div>`;bindDomainControls(page,maxPage)}
function renderDomain(){const page=node("recommendations");const all=catalog[selectedDomain]||[];const statuses=[...new Set(all.map(item=>nativeStatus(item)||"MISSING"))].sort();const filtered=filteredDomainItems();const maxPage=Math.max(0,Math.ceil(filtered.length/REC_PAGE_SIZE)-1);if(pageIndex>maxPage)pageIndex=maxPage;const start=pageIndex*REC_PAGE_SIZE;const visible=filtered.slice(start,start+REC_PAGE_SIZE);const statusOptions=[`<option value="all">All native statuses</option>`,...statuses.map(status=>`<option value="${escapeHtml(status)}"${selectedStatus===status?" selected":""}>${escapeHtml(cleanStatus(status))}</option>`)].join("");if(selectedDomain==="crypto"){renderCryptoDomain(page,all,filtered,statusOptions);return}if(selectedDomain==="metals"){renderMetalsDomain(page,all,filtered,statusOptions,start,maxPage);return}if(selectedDomain==="mtg"){renderMtgDomain(page,all,filtered,statusOptions,start,maxPage);return}let orderNote="Catalog order is presentation order; UIP does not manufacture a rank for this domain.";let utilityNote="Certified recommendation, rationale, and risk evidence.";let table=`<table style="min-width:1380px"><thead><tr><th>Asset</th><th>Native recommendation</th><th>Domain score</th><th>Confidence</th><th>Horizon</th><th>Rationale</th><th>Risk</th><th>Detail</th></tr></thead><tbody>${genericRows(visible)}</tbody></table>`;if(selectedDomain==="mtg"){table=`<table style="min-width:1450px"><thead><tr><th>Asset</th><th>Native status</th><th>Native rank</th><th>Evidence</th><th>Actionability</th><th>Manual price check</th><th>Execution ready</th><th>Automatic execution</th></tr></thead><tbody>${mtgRows(visible)}</tbody></table>`;orderNote="MTG native rank is used only inside MTG where provided. Unranked native records remain visible.";utilityNote="Native MTG authority remains unchanged; richer price and forecast presentation follows in the MTG utility pass."}page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-shell"><div class="rec-section-head"><div><span class="eyebrow">RECOMMENDATIONS</span><h3>${escapeHtml(selectedDomain.toUpperCase())} research</h3></div><button type="button" id="rec-all-domains" class="secondary">All domains</button></div><article class="rec-domain-table panel"><div class="section-title"><div><h3>${escapeHtml(utilityNote)}</h3><span>${escapeHtml(filtered.length)} matching · ${escapeHtml(all.length)} total</span></div></div><p class="governance-note">${escapeHtml(orderNote)} Recommendation does not authorize execution.</p><div class="transaction-form" style="grid-template-columns:1fr 1fr;margin:16px 0"><label>Search<input id="rec-search" value="${escapeHtml(searchText)}" placeholder="Asset, ID, lane, status..."></label><label>Native status<select id="rec-status">${statusOptions}</select></label></div><div class="table-wrap">${table}</div><div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:14px"><span class="page-note">Rows ${filtered.length?start+1:0}-${Math.min(start+REC_PAGE_SIZE,filtered.length)} of ${filtered.length}</span><div style="display:flex;gap:8px"><button type="button" id="rec-prev" class="secondary" ${pageIndex===0?"disabled":""}>Previous</button><button type="button" id="rec-next" class="secondary" ${pageIndex>=maxPage?"disabled":""}>Next</button></div></div></article></div>`;bindDomainControls(page,maxPage)}

function forecastRows(detail){const rows=allForecasts(detail);return rows.map(f=>`<tr class="${Number(f.forecast_horizon_months)===36&&f.forecast_method==="LONG_RANGE_SCENARIO_MODEL"?"strategic":""}"><td>${escapeHtml(`${fmtNumber(f.forecast_horizon_months,0)} mo`)}</td><td style="text-align:left">${escapeHtml(f.forecast_method??"—")}</td><td>${escapeHtml(fmtMoney(f.point_forecast))}</td><td>${escapeHtml(fmtPercent(f.expected_return))}</td><td>${escapeHtml(fmtMoney(f.lower_bound))}</td><td>${escapeHtml(fmtMoney(f.upper_bound))}</td><td>${escapeHtml(fmtNumber(f.confidence_score,3))}</td></tr>`).join("")}
function riskMetrics(detail){const risk=firstPayload(detail,"risk")||{};const candidates=[["Risk level",risk.risk_level],["Risk score",risk.risk_score],["Volatility",risk.volatility],["Downside",risk.downside_risk],["Max drawdown",risk.max_drawdown],["VaR",risk.var],["Expected shortfall",risk.expected_shortfall],["Beta",risk.beta],["Liquidity",risk.liquidity],["Concentration",risk.concentration]];const rows=candidates.filter(([,value])=>value!==null&&value!==undefined&&value!=="");if(!rows.length)return `<p class="governance-note">No separately populated risk metrics are available in this presentation record.</p>`;return rows.map(([label,value])=>`<div class="history-row"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(typeof value==="number"?fmtNumber(value,3):value)}</span></div>`).join("")}
function chartPoints(rows,key,width,height,pad=16){const valid=rows.filter(r=>Number.isFinite(Number(r[key])));if(valid.length<2)return "";const xs=valid.map(r=>Number(r.forecast_horizon_months));const ys=valid.map(r=>Number(r[key]));const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),xSpan=maxX-minX||1,ySpan=maxY-minY||1;return valid.map(r=>{const x=pad+((Number(r.forecast_horizon_months)-minX)/xSpan)*(width-pad*2);const y=height-pad-((Number(r[key])-minY)/ySpan)*(height-pad*2);return `${x.toFixed(1)},${y.toFixed(1)}`}).join(" ")}
function forecastChart(detail){const rows=longRangeForecasts(detail).filter(f=>Number(f.forecast_horizon_months)<=36);if(rows.length<2)return `<div class="empty">No multi-horizon long-range series is available.</div>`;const width=270,height=190;const horizons=[...new Set(rows.map(r=>Number(r.forecast_horizon_months)))];const lines=[40,85,130,175].map(y=>`<line class="grid-line" x1="16" y1="${y}" x2="254" y2="${y}"></line>`).join("");const labels=horizons.filter((_,i)=>i===0||i===horizons.length-1||i%2===0).map(h=>{const x=16+((h-Math.min(...horizons))/(Math.max(...horizons)-Math.min(...horizons)||1))*238;return `<text x="${x}" y="187" text-anchor="middle">${h}m</text>`}).join("");return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Long-range forecast path through 36 months">${lines}<polyline class="bear-line" points="${chartPoints(rows,"lower_bound",width,height)}"></polyline><polyline class="base-line" points="${chartPoints(rows,"point_forecast",width,height)}"></polyline><polyline class="bull-line" points="${chartPoints(rows,"upper_bound",width,height)}"></polyline>${labels}</svg>`}
function horizonTabs(detail){const available=new Set(allForecasts(detail).map(f=>Number(f.forecast_horizon_months)));return [1,3,6,12,24,36].map(h=>`<div class="rec-horizon-tab ${h===36?"strategic":""}"><strong>${h}m</strong><span>${h===36?"Strategic objective":available.has(h)?h>=24?"Mid-term view":"Entry context":"Not populated"}</span></div>`).join("")}

function openCryptoDetail(assetId){const item=(catalog?.crypto||[]).find(candidate=>candidate.asset_id===assetId);if(!item)return;const detail=detailCache.get(detailKey(item));if(!detail){renderBlocked("Certified Crypto detail is not available in the local presentation cache.");return}const page=node("recommendations");const f36=crypto36(detail)||{};const recommendation=item.payload||{};const risk=firstPayload(detail,"risk")||{};const score=riskScore(detail);const level=riskLevel(detail,item);const angle=score===null?-145:-175+Math.max(0,Math.min(100,score))*1.7;page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-detail"><div class="rec-detail-head"><div class="rec-detail-title"><span class="eyebrow">CRYPTO RESEARCH</span><h2>${escapeHtml(displayName(item))}</h2><p>${escapeHtml(item.asset_symbol||item.asset_id||"")} · domain-native research · certified authority</p></div><button type="button" id="rec-back-crypto" class="secondary">← Back to Crypto</button></div><section class="rec-strategic-hero"><div><span class="eyebrow">3-YEAR GROWTH OUTLOOK</span><h3><span class="return">${escapeHtml(fmtPercent(f36.expected_return))}</span> expected return over the certified 36-month horizon</h3><p class="rec-strategic-copy">Bear ${escapeHtml(fmtMoney(f36.lower_bound))} · Base ${escapeHtml(fmtMoney(f36.point_forecast))} · Bull ${escapeHtml(fmtMoney(f36.upper_bound))}. LONG_RANGE_SCENARIO_MODEL record. UIP does not extrapolate a shorter forecast into three years.</p><div class="rec-chips"><span class="rec-chip">Scenario ${escapeHtml(f36.scenario??"—")}</span><span class="rec-chip">Confidence raw ${escapeHtml(fmtNumber(f36.confidence_score,3))}</span><span class="rec-chip">Origin ${escapeHtml(f36.forecast_origin_date??f36.origin_date??"—")}</span></div></div><div class="rec-range-chart"><div class="rec-range-head"><div><strong>Bear</strong><span>${escapeHtml(fmtMoney(f36.lower_bound))}</span></div><div><strong>Base</strong><span>${escapeHtml(fmtMoney(f36.point_forecast))}</span></div><div><strong>Bull</strong><span>${escapeHtml(fmtMoney(f36.upper_bound))}</span></div></div><div class="rec-range-scale"><div class="rec-range-band"></div><i class="rec-range-marker bear"></i><i class="rec-range-marker base" style="left:${rangePosition(f36)}%"></i><i class="rec-range-marker bull"></i><div class="rec-range-axis"><span>Bear</span><span>36-month horizon price (USD)</span><span>Bull</span></div></div></div></section><section class="rec-kpi-row"><article class="rec-kpi-card bear"><div class="rec-kpi-label"><span class="rec-kpi-dot">●</span>Bear case</div><strong>${escapeHtml(fmtMoney(f36.lower_bound))}</strong><small class="page-note">36-month bear forecast</small></article><article class="rec-kpi-card base"><div class="rec-kpi-label"><span class="rec-kpi-dot">●</span>Base case</div><strong>${escapeHtml(fmtMoney(f36.point_forecast))}</strong><small class="page-note">36-month base forecast</small></article><article class="rec-kpi-card"><div class="rec-kpi-label"><span class="rec-kpi-dot">●</span>Bull case</div><strong>${escapeHtml(fmtMoney(f36.upper_bound))}</strong><small class="page-note">36-month bull forecast</small></article><article class="rec-kpi-card"><div class="rec-kpi-label"><span class="rec-kpi-dot">↗</span>Expected return (36m)</div><strong class="${Number(f36.expected_return)>0?"positive":"negative"}">${escapeHtml(fmtPercent(f36.expected_return))}</strong><small class="page-note">Nominal return expectation</small></article></section><section class="rec-detail-grid"><div class="rec-forecast-panel"><div class="rec-panel-head"><h4>Forecast path & entry context</h4><p>Short horizons inform accumulation timing; the 36-month horizon remains the strategic objective.</p></div><div class="rec-horizon-tabs">${horizonTabs(detail)}</div><div class="rec-forecast-viz"><div class="rec-line-chart"><div style="display:flex;gap:12px;font-size:8px;color:var(--muted);margin-bottom:8px"><span style="color:var(--warn)">● Base</span><span style="color:var(--accent)">● Bull</span><span style="color:var(--bad)">● Bear</span></div>${forecastChart(detail)}</div><div class="rec-detail-table"><table><thead><tr><th>Horizon</th><th>Method</th><th>Point forecast</th><th>Expected return</th><th>Bear</th><th>Bull</th><th>Confidence raw</th></tr></thead><tbody>${forecastRows(detail)}</tbody></table></div></div><p class="governance-note">Shorter horizons are entry context only and not a UIP-created rank.</p></div><div class="rec-side-stack"><aside class="rec-side-panel"><h4>Why this recommendation</h4><div class="rec-narrative"><div><span>Rationale</span><p>${escapeHtml(recommendation.rationale??"No rationale is populated.")}</p></div><div><span>Risk summary</span><p>${escapeHtml(recommendation.risk_summary??"No narrative risk summary is populated.")}</p></div><div><span>Native recommendation</span><p>${escapeHtml(cleanStatus(nativeStatus(item)))}</p></div></div></aside><aside class="rec-side-panel"><h4>Risk assessment</h4><div class="rec-risk-gauge-wrap"><div class="rec-risk-gauge" style="--risk-angle:${angle}deg"></div><div class="rec-risk-readout"><span>Risk level</span><strong>${escapeHtml(level)}</strong><span>Risk score</span><strong>${escapeHtml(score===null?"—":fmtNumber(score,0))}</strong></div></div><div class="history" style="margin-top:12px">${riskMetrics(detail)}</div><p class="rec-risk-note">Confidence values are shown as raw source values, not percentages. Missing probability-positive values remain missing.</p></aside></div></section></div>`;node("rec-back-crypto").addEventListener("click",()=>{selectedDomain="crypto";selectedStatus="all";searchText="";pageIndex=0;renderDomain()})}

function momentumBar(label,value){const n=Number(value);const finite=Number.isFinite(n);const magnitude=finite?Math.min(50,Math.abs(n)):0;const width=magnitude*1.8;return `<div class="metals-bar-row"><span>${escapeHtml(label)}</span><div class="metals-bar-track">${finite?`<i class="metals-bar-fill ${n<0?"negative":""}" style="width:${width}%"></i>`:""}</div><strong class="${finite&&n<0?"negative":finite&&n>0?"positive":""}">${escapeHtml(fmtPctPoint(value))}</strong></div>`}
async function openMetalsDetail(assetId){ensureMetalsVisualStyles();const item=(catalog?.metals||[]).find(candidate=>candidate.asset_id===assetId);if(!item)return;let detail;try{detail=await readAssetDetail(item)}catch(error){renderBlocked(error.message);return}const renderTactical=window.UIPMetalsTactical?.renderTacticalPanel;if(typeof renderTactical!=="function"){renderBlocked("Certified Metals tactical renderer is unavailable. Long-term recommendation data was not altered.");return}const page=node("recommendations");const recommendation=item.payload||{};const t=tacticalPayload(detail)||{};const forecast=metalsForecast(detail);const score=metalsScore(item);const confidence=metalsConfidence(item);const level=riskLevel(detail,item);const tacticalPanel=renderTactical(detail);const modelComponents=payloads(detail,"metals_model_component");const uncertainty=payloads(detail,"metals_uncertainty_adjusted");const modelNote=modelComponents.length?`${modelComponents.length} certified model component records available.`:"No separate model-component records are populated for this asset.";const uncertaintyNote=uncertainty.length?`${uncertainty.length} uncertainty-adjusted records available.`:"No separate uncertainty-adjusted records are populated for this asset.";page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-detail"><div class="rec-detail-head"><div class="rec-detail-title"><span class="eyebrow">METALS RESEARCH</span><h2>${escapeHtml(displayName(item))}</h2><p>${escapeHtml(item.asset_symbol||item.asset_id||"")} · long-term thesis + bounded tactical context · certified authority</p></div><button type="button" id="rec-back-metals" class="secondary">← Back to Metals</button></div><section class="metals-hero"><div><span class="eyebrow">LONG-TERM METALS OUTLOOK</span><h3>${escapeHtml(cleanStatus(nativeStatus(item)))} · strategic thesis remains the primary authority</h3><p class="metals-hero-copy">${escapeHtml(recommendation.rationale??"No narrative rationale is populated in the recommendation record.")}</p><div class="rec-chips"><span class="rec-chip">Domain score ${escapeHtml(fmtNumber(score))}</span><span class="rec-chip">Confidence ${escapeHtml(fmtNumber(confidence))}</span><span class="rec-chip">Tactical state ${escapeHtml(cleanStatus(tacticalState(detail)))}</span></div></div><div class="metals-hero-side"><div class="metals-hero-metric"><span>Forecast horizon</span><strong>${forecast?`${escapeHtml(fmtNumber(forecast.forecast_horizon_months,0))} mo`:"—"}</strong></div><div class="metals-hero-metric"><span>Expected return</span><strong>${escapeHtml(forecast?fmtPercent(forecast.expected_return):"—")}</strong></div><div class="metals-hero-metric"><span>Risk level</span><strong>${escapeHtml(level)}</strong></div><div class="metals-hero-metric"><span>Current regime</span><strong>${escapeHtml(cleanStatus(tacticalRegime(detail)))}</strong></div></div></section><section class="metals-detail-kpis"><article><span>1M momentum</span><strong>${escapeHtml(fmtPctPoint(t.return_1m_pct))}</strong></article><article><span>3M momentum</span><strong>${escapeHtml(fmtPctPoint(t.return_3m_pct))}</strong></article><article><span>6M momentum</span><strong>${escapeHtml(fmtPctPoint(t.return_6m_pct))}</strong></article><article><span>Current drawdown</span><strong class="${Number(t.current_drawdown_pct)<0?"negative":""}">${escapeHtml(fmtPctPoint(t.current_drawdown_pct))}</strong></article></section><section class="metals-detail-grid"><div style="display:grid;gap:14px"><article class="metals-panel"><h4>Momentum & trend context</h4><p class="metals-panel-sub">Short and medium windows inform timing context. They do not replace the long-term recommendation.</p><div class="metals-momentum-bars">${momentumBar("1 month",t.return_1m_pct)}${momentumBar("3 months",t.return_3m_pct)}${momentumBar("6 months",t.return_6m_pct)}${momentumBar("vs MA50",t.distance_ma50_pct)}${momentumBar("vs MA200",t.distance_ma200_pct)}${momentumBar("Drawdown",t.current_drawdown_pct)}</div></article><article class="metals-panel"><h4>Forecast & model evidence</h4><p class="metals-panel-sub">${escapeHtml(modelNote)} ${escapeHtml(uncertaintyNote)}</p>${allForecasts(detail).length?`<div class="rec-detail-table"><table><thead><tr><th>Horizon</th><th>Method</th><th>Point forecast</th><th>Expected return</th><th>Bear</th><th>Bull</th><th>Confidence raw</th></tr></thead><tbody>${forecastRows(detail)}</tbody></table></div>`:`<div class="empty">No forecast records are populated for this asset.</div>`}</article><article class="metals-panel"><h4>Why this recommendation</h4><div class="rec-narrative"><div><span>Rationale</span><p>${escapeHtml(recommendation.rationale??"No rationale is populated.")}</p></div><div><span>Risk summary</span><p>${escapeHtml(recommendation.risk_summary??"No narrative risk summary is populated.")}</p></div><div><span>Native recommendation</span><p>${escapeHtml(cleanStatus(nativeStatus(item)))}</p></div></div></article></div><div style="display:grid;gap:14px">${tacticalPanel}<aside class="metals-panel"><h4>Risk assessment</h4><div class="history">${riskMetrics(detail)}</div><p class="governance-note">Risk remains independent of tactical state and forecast return.</p></aside><aside class="metals-panel"><h4>Governance boundary</h4><p class="governance-note">Tactical supportive, defensive, or no-overlay states are relative tactical interpretations only. They are not buy/sell instructions, position sizing, automatic execution authority, or replacements for the long-term thesis.</p></aside></div></section></div>`;node("rec-back-metals").addEventListener("click",()=>{selectedDomain="metals";selectedStatus="all";searchText="";pageIndex=0;renderDomain()})}

function renderBlocked(message){const page=node("recommendations");page.innerHTML=`${recommendationDomainSummaryAnchor()}<article class="panel governed-empty"><span class="empty-icon">!</span><h3>Recommendation research is unavailable</h3><p>${escapeHtml(message)}</p></article>`}
async function loadCatalog(force=false){if(loading)return;if(catalog&&!force){selectedDomain==="all"?renderAll():renderDomain();return}loading=true;try{const [crypto,metals,mtg]=await Promise.all(REC_DOMAINS.map(readDomain));catalog={crypto,metals,mtg};detailCache.clear();await hydrateCryptoResearch();selectedDomain==="all"?renderAll():renderDomain()}catch(error){renderBlocked(error.message)}finally{loading=false}}
function openDomain(domain){selectedDomain=domain;selectedStatus="all";searchText="";pageIndex=0;renderDomain()}

document.querySelector('.nav-item[data-page="recommendations"]')?.addEventListener("click",()=>{if(sessionStorage.getItem("uiip-dashboard-key"))loadCatalog(false)});
document.getElementById("refresh")?.addEventListener("click",()=>{if(document.getElementById("recommendations")?.classList.contains("active-page")&&sessionStorage.getItem("uiip-dashboard-key"))loadCatalog(true)});
if(location.hash==="#recommendations"&&sessionStorage.getItem("uiip-dashboard-key"))loadCatalog(false);
})();
