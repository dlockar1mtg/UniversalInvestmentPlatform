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
function fmtPriceBound(value){if(value===null||value===undefined||value==="")return fmtMoney(value);const parsed=Number(value);return Number.isFinite(parsed)&&parsed<0?"Below $0 (model range not meaningful)":fmtMoney(value)}
function fmtPercent(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?`${(parsed*100).toFixed(1)}%`:String(value)}
function fmtPctPoint(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?`${parsed.toFixed(1)}%`:String(value)}
function nativeStatus(item){const payload=item.payload||{};return item.domain_id==="mtg"?(payload.native_purchase_status??null):(payload.native_recommendation??payload.recommendation??null)}
function displayStatus(item){const payload=item.payload||{};return item.domain_id==="metals"?(payload.final_action??payload.native_recommendation??payload.recommendation??null):nativeStatus(item)}
function statusFilterLabel(domain){return domain==="metals"?"Decision status":"Native status"}
function statusFilterAllLabel(domain){return domain==="metals"?"All decision statuses":"All native statuses"}
function recommendationColumnLabel(domain){return domain==="metals"?"Final decision":"Native recommendation"}

function displayName(item){return item.asset_name||item.asset_symbol||item.asset_id||"Unknown governed asset"}
function searchKey(item){const payload=item.payload||{};return [item.asset_name,item.asset_symbol,item.asset_id,item.asset_subclass,displayStatus(item),payload.purchase_semantic,payload.evidence_state,payload.actionability_state].filter(Boolean).join(" ").toLowerCase()}
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

function cryptoCard(item){const detail=detailCache.get(detailKey(item));const f=crypto36(detail);const level=riskLevel(detail,item);const status=cleanStatus(displayStatus(item));const returnValue=f?.expected_return;const positive=Number(returnValue)>0;return `<article class="rec-asset-card"><div class="rec-asset-head"><div class="rec-asset-id"><span class="rec-coin">${escapeHtml(coinLabel(item))}</span><span class="rec-asset-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_symbol||item.asset_id||"")}</small></span></div><span class="rec-status ${String(status).toLowerCase()}">${escapeHtml(status)}</span></div><div class="rec-card-kpis"><div class="rec-card-kpi"><span>3Y expected return</span><strong class="${positive?"positive":""}">${escapeHtml(fmtPercent(returnValue))}</strong></div><div class="rec-card-kpi"><span>3Y base forecast</span><strong>${escapeHtml(fmtMoney(f?.point_forecast))}</strong></div></div><div class="rec-scenario-labels"><span>Bear</span><span>Base</span><span>Bull</span></div><div class="rec-scenario-values"><span>${escapeHtml(fmtPriceBound(f?.lower_bound))}</span><span>${escapeHtml(fmtMoney(f?.point_forecast))}</span><span>${escapeHtml(fmtMoney(f?.upper_bound))}</span></div><div class="rec-range"><i class="rec-range-dot" style="left:${rangePosition(f)}%"></i></div>${svgSparkline(detail)}<div class="rec-card-foot"><div class="rec-risk-mini"><span>Long-term risk</span><strong>${escapeHtml(level)}</strong>${riskBars(level)}</div><button type="button" class="rec-research-button rec-crypto-detail" data-asset-id="${escapeHtml(item.asset_id)}">Research ↗</button></div></article>`}
function renderExplainer(){return `<aside class="rec-explainer"><h4>Why this view is useful</h4><div class="rec-explainer-item"><span class="rec-explainer-icon">↗</span><div><strong>3-Year strategic outlook</strong><p>Start with the 36-month scenario return and range. It is a long-range scenario, not a validated forecast.</p></div></div><div class="rec-explainer-item"><span class="rec-explainer-icon">◈</span><div><strong style="color:var(--warn)">Long-term risk</strong><p>Risk evidence stays separate from return so upside and downside can be evaluated together.</p></div></div><div class="rec-explainer-item"><span class="rec-explainer-icon">◎</span><div><strong style="color:var(--accent2)">Current entry context</strong><p>Shorter horizons inform accumulation timing while 36 months remains the strategic objective.</p></div></div><div class="rec-governance-callout">Research is domain-native. Execution is not authorized by UIP. Rows are not a UIP-created rank.</div></aside>`}

function isBil(item){const symbol=String(item?.asset_symbol||"").toUpperCase();const id=String(item?.asset_id||"").toUpperCase();return symbol==="BIL"||id.endsWith(":BIL")||id.includes("VEHICLE:BIL")}
function tacticalPayload(detail){return firstPayload(detail,"tactical_state")||null}
function commodityTechnicalContext(detail,assetId){
  const rows=payloads(detail,"metals_commodity_technical_context");
  if(assetId==="metals:commodity:uranium"){
    if(rows.length!==0)throw new Error("Uranium monthly commodity technical context must remain unavailable under V1.");
    return null;
  }
  if(rows.length!==1)throw new Error("Certified monthly commodity technical context must contain exactly one record for supported Metals commodities.");
  const row=rows[0];
  if(row.authority_id!=="UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1")throw new Error("Unexpected Metals commodity technical-context authority.");
  if(String(row.universal_asset_id||"")!==assetId)throw new Error("Metals commodity technical-context identity mismatch.");
  if(String(row.source_provider||"").toLowerCase()!=="world_bank"||String(row.source_frequency||"").toLowerCase()!=="monthly")throw new Error("Metals commodity technical context requires certified monthly World Bank authority.");
  if(String(row.ma50_supported).toLowerCase()!=="false"||String(row.ma200_supported).toLowerCase()!=="false")throw new Error("Daily moving averages are not authorized by the monthly commodity technical-context source.");
  return row;
}
function technicalReturn(row,key){return row?fmtPercent(row[key]):"Unavailable"}
function technicalDrawdown(row){return row?fmtPercent(row.current_drawdown):"Unavailable"}
function tacticalState(detail){return tacticalPayload(detail)?.tactical_state??"TACTICAL_STATE_UNAVAILABLE"}
function tacticalRegime(detail){return tacticalPayload(detail)?.candidate_regime??"REGIME_UNAVAILABLE"}
function tacticalPosition(detail){const state=tacticalState(detail);if(state==="TACTICAL_DEFENSIVE")return 12;if(state==="TACTICAL_SUPPORTIVE")return 88;return 50}
function metalsForecasts(detail){return allForecasts(detail).filter(row=>[3,6,12,24].includes(Number(row.forecast_horizon_months)))}
function metalsForecast(detail){const rows=metalsForecasts(detail);return rows.find(row=>Number(row.forecast_horizon_months)===24)||rows.at(-1)||null}
function metalsForecastRows(detail){return metalsForecasts(detail).map(f=>`<tr><td>${escapeHtml(`${fmtNumber(f.forecast_horizon_months,0)} mo`)}</td><td style="text-align:left">${escapeHtml(f.forecast_method??"—")}</td><td>${escapeHtml(fmtMoney(f.point_forecast))}</td><td>${escapeHtml(fmtPercent(f.expected_return))}</td><td>${escapeHtml(fmtPriceBound(f.lower_bound))}</td><td>${escapeHtml(fmtMoney(f.upper_bound))}</td><td>${escapeHtml(fmtNumber(f.confidence_score,3))}</td></tr>`).join("")}
function metalsScore(item){const p=item.payload||{};return p.normalized_score??p.domain_score??null}
function metalsConfidence(item){const p=item.payload||{};return p.confidence_score??p.confidence??null}
function metalsCard(item){const detail=detailCache.get(detailKey(item));const technical=commodityTechnicalContext(detail,item.asset_id);const f=metalsForecast(detail);const status=cleanStatus(displayStatus(item));const native=cleanStatus(nativeStatus(item));const score=metalsScore(item);const confidence=metalsConfidence(item);const forecastLabel=f?`${fmtNumber(f.forecast_horizon_months,0)}M expected return`:"Forecast authority";const forecastValue=f?fmtPercent(f.expected_return):"Unavailable";return `<article class="metals-card"><div class="metals-card-head"><div class="metals-asset-id"><span class="metals-symbol">${escapeHtml(metalLabel(item))}</span><span class="metals-asset-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_symbol||item.asset_id||"")}</small></span></div><span class="metals-status">${escapeHtml(status)}</span></div><div class="metals-kpis"><div class="metals-kpi"><span>Domain score</span><strong>${escapeHtml(fmtNumber(score))}</strong></div><div class="metals-kpi"><span>Confidence</span><strong>${escapeHtml(fmtNumber(confidence))}</strong></div><div class="metals-kpi"><span>${escapeHtml(forecastLabel)}</span><strong>${escapeHtml(forecastValue)}</strong></div><div class="metals-kpi"><span>Native recommendation</span><strong>${escapeHtml(native)}</strong></div></div><div><div class="metals-momentum"><div><span>1M return</span><strong>${escapeHtml(technicalReturn(technical,"return_1m"))}</strong></div><div><span>3M return</span><strong>${escapeHtml(technicalReturn(technical,"return_3m"))}</strong></div><div><span>6M return</span><strong>${escapeHtml(technicalReturn(technical,"return_6m"))}</strong></div></div><div style="margin-top:12px"><div class="metals-regime-track"><i class="metals-regime-dot" style="left:${tacticalPosition(detail)}%"></i></div><div class="metals-track-labels"><span>Defensive</span><span>Neutral</span><span>Supportive</span></div></div></div><div class="metals-card-foot"><div class="metals-tactical-mini"><span>Tactical context</span><strong>${escapeHtml(cleanStatus(tacticalState(detail)))}</strong><span>${escapeHtml(cleanStatus(tacticalRegime(detail)))}</span></div><button type="button" class="rec-research-button rec-metals-detail" data-asset-id="${escapeHtml(item.asset_id)}">Research ↗</button></div></article>`}
function renderMetalsExplainer(){return `<aside class="metals-explainer"><h4>Why this view is useful</h4><div class="metals-explainer-item"><span class="metals-explainer-icon">↗</span><div><strong>Long-term thesis first</strong><p>The governed final decision is primary. Native recommendation, forecast, and risk remain supporting evidence.</p></div></div><div class="metals-explainer-item"><span class="metals-explainer-icon">◎</span><div><strong>Current tactical context</strong><p>1M/3M/6M momentum, drawdown, trend distance, and regime interpretation help frame current conditions.</p></div></div><div class="metals-explainer-item"><span class="metals-explainer-icon">◇</span><div><strong>Separate decision layers</strong><p>No tactical overlay is not a sell signal and does not erase a constructive long-term thesis.</p></div></div><div class="metals-reference-note"><strong>BIL is reference/control only.</strong><br>It remains available in the secondary research table but is excluded from featured opportunity cards.</div></aside>`}

function bindDomainButtons(page){page.querySelectorAll(".rec-open-domain").forEach(button=>button.addEventListener("click",()=>openDomain(button.dataset.recDomain)));page.querySelectorAll(".rec-crypto-detail").forEach(button=>button.addEventListener("click",()=>openCryptoDetail(button.dataset.assetId)));page.querySelectorAll(".rec-metals-detail").forEach(button=>button.addEventListener("click",()=>openMetalsDetail(button.dataset.assetId)))}
function renderAll(){const page=node("recommendations");const crypto=catalog?.crypto||[];page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-shell"><section class="rec-hero"><div class="rec-intro"><span class="eyebrow">RECOMMENDATIONS</span><h2>Investment research ✦</h2><p>Domain-native research, long-term thesis first. Current entry context second.</p><span class="rec-intro-link">How we research ↗</span></div><div class="rec-domain-grid">${REC_DOMAINS.map(domain=>renderDomainSummary(domain,catalog[domain]||[])).join("")}</div></section><section><div class="rec-section-head"><div><span class="eyebrow">FEATURED DOMAIN</span><h3>Crypto research <span class="rec-count-chip">${crypto.length} assets</span></h3></div><div class="rec-section-head-actions"><button type="button" class="secondary rec-open-domain" data-rec-domain="crypto">View all crypto research</button></div></div><div class="rec-crypto-layout" style="margin-top:14px"><div class="rec-asset-grid">${crypto.map(cryptoCard).join("")}</div>${renderExplainer()}</div></section><p class="governance-note">UIP keeps Crypto, Metals, and MTG as separate decision systems. This surface exposes certified investment evidence without manufacturing a universal score, cross-domain ranking, or automatic purchase decision.</p></div>`;bindDomainButtons(page)}

let mtgLane="secret_lair";

function ensureMtgPremiumVisualStyles(){
  return;
}

function mtgLaneForItem(item){
  const id=String(item?.asset_id||"");

  if(id.startsWith("SECRET_LAIR_V1_1|"))return "secret_lair";
  if(id.startsWith("COLLECTOR_V1|"))return "collector";
  if(id.startsWith("PRE_COLLECTOR_V1|"))return "pre_collector";

  return "other";
}

function mtgLaneLabel(lane){
  if(lane==="secret_lair")return "Secret Lair";
  if(lane==="collector")return "Collector Boosters";
  if(lane==="pre_collector")return "Pre-Collector";
  return "Other";
}

function mtgLaneCount(items,lane){
  return items.filter(
    item=>mtgLaneForItem(item)===lane
  ).length;
}

function mtgStatusPriority(item){
  const status=String(
    nativeStatus(item)||""
  ).toUpperCase();

  if(status.includes("BUY"))return 0;
  if(status.includes("STRONG PURCHASE"))return 0;
  if(status.includes("WAIT"))return 1;

  return 2;
}

function mtgInvestmentSort(items){
  return [...items].sort(
    (a,b)=>{
      const statusDifference=
        mtgStatusPriority(a)-mtgStatusPriority(b);

      if(statusDifference!==0){
        return statusDifference;
      }

      const rankDifference=
        mtgNativeRankNumber(a)-mtgNativeRankNumber(b);

      if(rankDifference!==0){
        return rankDifference;
      }

      return String(
        displayName(a)
      ).localeCompare(
        String(displayName(b))
      );
    }
  );
}

function mtgNativeRankNumber(item){
  const p=
    mtgNativePayload(item);

  const rank=
    Number(p.native_rank);

  return Number.isFinite(rank)
    ?rank
    :Number.POSITIVE_INFINITY;
}

function mtgNativePresentationPriority(item){
  const p=
    mtgNativePayload(item);

  if(mtgNativeHasValue(p.native_rank)){
    return 0;
  }

  if(
    mtgNativeBoolean(
      p.current_price_authority_available
    )
  ){
    return 1;
  }

  return 2;
}

function mtgNativeInvestmentSort(items){
  return items
    .slice()
    .sort(
      (a,b)=>{
        const priorityDifference=
          mtgNativePresentationPriority(a)-
          mtgNativePresentationPriority(b);

        if(priorityDifference!==0){
          return priorityDifference;
        }

        const rankDifference=
          mtgNativeRankNumber(a)-
          mtgNativeRankNumber(b);

        if(rankDifference!==0){
          return rankDifference;
        }

        return String(
          displayName(a)
        ).localeCompare(
          String(displayName(b))
        );
      }
    );
}
function mtgIsBuyCandidate(item){
  const status=String(
    nativeStatus(item)||""
  ).toUpperCase();

  return (
    status.includes("BUY")||
    status.includes("STRONG PURCHASE")
  );
}

function mtgIsWaitCandidate(item){
  return String(
    nativeStatus(item)||""
  ).toUpperCase().includes("WAIT");
}

function mtgEvidenceLabel(premium){
  if(!premium)return "Native authority";

  const own=cleanStatus(
    premium.own_history_evidence_class
  );

  const exact=Number(
    premium.exact_structural_comparable_product_count||0
  );

  const global=Number(
    premium.global_comparable_product_count||0
  );

  if(
    own&&
    own!=="MISSING"&&
    exact>=3
  ){
    return "Strong";
  }

  if(exact>0||global>=3){
    return "Supported";
  }

  return own||"Limited";
}

function mtgDistanceToQ10(premium){
  const current=Number(
    premium?.current_tcg_market_price_usd
  );

  const q10=Number(
    premium?.y1_q10_break_even_entry_price_usd
  );

  if(
    !Number.isFinite(current)||
    !Number.isFinite(q10)
  ){
    return null;
  }

  return q10-current;
}

function mtgGovernedQ10State(premium){
  const raw=
    premium?.current_price_vs_q10_break_even_state;

  if(raw==null||raw===""){
    return "MISSING";
  }

  return cleanStatus(raw);
}

function mtgEntryPercent(premium){
  const current=Number(
    premium?.current_tcg_market_price_usd
  );

  const q10=Number(
    premium?.y1_q10_break_even_entry_price_usd
  );

  if(
    !Number.isFinite(current)||
    !Number.isFinite(q10)||
    q10<=0
  ){
    return 50;
  }

  const ratio=
    current/q10;

  return Math.max(
    5,
    Math.min(
      95,
      50+(ratio-1)*220
    )
  );
}

function bindMtgLaneTabs(page){
  page.querySelectorAll(
    "[data-mtg-lane]"
  ).forEach(
    button=>{
      button.addEventListener(
        "click",
        ()=>{
          mtgLane=String(
            button.dataset.mtgLane||"secret_lair"
          );

          pageIndex=0;
          renderDomain();
        }
      );
    }
  );
}

function mtgEntryStateClass(value){
  const state=String(value||"").toUpperCase();
  if(state.includes("BELOW")||state.includes("AT_Q10")||state.includes("BUY"))return "entry";
  return "wait";
}


function mtgPremiumCard(item){
  const p=item.payload||{};
  const premium=mtgPremiumPayload(item);

  if(!premium){
    return mtgNativeCard(item);
  }

  const status=
    cleanStatus(nativeStatus(item));

  const buy=
    mtgIsBuyCandidate(item);

  const wait=
    mtgIsWaitCandidate(item);

  const distance=
    mtgDistanceToQ10(premium);

  const governedQ10State=
    mtgGovernedQ10State(premium);

  const q10Class=
    buy
      ?"buy"
      :wait
        ?"wait"
        :"neutral";

  const distanceLabel=
    distance==null
      ?"?"
      :distance>=0
        ?`${fmtMoney(distance)} below Q10`
        :`${fmtMoney(Math.abs(distance))} above Q10`;

  return `<article class="rec-asset-card mtg-investment-card ${q10Class}">
    <div class="rec-asset-head">
      <div class="rec-asset-id">
        <div class="rec-coin mtg-product-icon">MTG</div>
        <div class="rec-asset-name">
          <strong>${escapeHtml(premium.product_name||displayName(item))}</strong>
          <small>Secret Lair &middot; Native rank ${escapeHtml(p.native_rank==null?"Not ranked":fmtNumber(p.native_rank,0))}</small>
        </div>
      </div>
      <span class="rec-status mtg-decision ${q10Class}">${escapeHtml(status)}</span>
    </div>

    <div class="rec-card-kpis mtg-primary-kpis">
      <div class="rec-card-kpi">
        <span>Current price</span>
        <strong>${escapeHtml(fmtMoney(premium.current_tcg_market_price_usd))}</strong>
      </div>
      <div class="rec-card-kpi">
        <span>Certified 1Y</span>
        <strong class="${Number(premium.certified_1y_point_return)>=0?"positive":""}">
          ${escapeHtml(fmtPercent(premium.certified_1y_point_return))}
        </strong>
      </div>
    </div>

    <div class="mtg-q10-summary">
      <div>
        <span>Governed Q10 entry</span>
        <strong>${escapeHtml(fmtMoney(premium.y1_q10_break_even_entry_price_usd))}</strong>
      </div>
      <div class="mtg-q10-distance ${q10Class}">
        <strong>${escapeHtml(governedQ10State)}</strong>
        <span>${escapeHtml(distanceLabel)}</span>
      </div>
    </div>

    <div class="mtg-entry-scale" aria-label="Current price versus governed Q10 entry">
      <span class="mtg-entry-scale-track"></span>
      <span class="mtg-entry-scale-q10"></span>
      <span
        class="mtg-entry-scale-current ${q10Class}"
        style="left:${mtgEntryPercent(premium)}%"
      ></span>
    </div>

    <div class="mtg-card-risk-row">
      <div>
        <span>1Y loss risk</span>
        <strong>${escapeHtml(fmtPercent(premium.y1_probability_of_loss))}</strong>
      </div>
      <div>
        <span>Evidence</span>
        <strong>${escapeHtml(mtgEvidenceLabel(premium))}</strong>
      </div>
    </div>

    <div class="mtg-scenario-preview">
      <div>
        <span>3Y scenario</span>
        <strong>${escapeHtml(fmtPercent(premium.y3_median_total_return_scenario))}</strong>
      </div>
      <div>
        <span>5Y scenario</span>
        <strong>${escapeHtml(fmtPercent(premium.y5_median_total_return_scenario))}</strong>
      </div>
    </div>

    <div class="rec-card-foot">
      <div class="mtg-card-policy">
        Q10 governs purchase eligibility
      </div>
      <button
        type="button"
        class="rec-research-button rec-mtg-premium-detail"
        data-asset-id="${escapeHtml(item.asset_id)}"
      >
        Open investment research &rarr;
      </button>
    </div>
  </article>`;
}


function mtgNativeBoolean(value){
  return value===true||String(value).toLowerCase()==="true";
}

function mtgNativeHasValue(value){
  return !(
    value===null||
    value===undefined||
    value===""
  );
}

function mtgNativeAvailability(value){
  return mtgNativeBoolean(value)
    ?"Available"
    :"Unavailable";
}

function mtgNativeCardState(item){
  const p=mtgNativePayload(item);

  if(
    mtgNativeBoolean(p.current_price_authority_available)&&
    mtgNativeBoolean(p.forecast_authority_available)&&
    mtgNativeHasValue(p.native_rank)
  ){
    return "research-ready";
  }

  if(
    mtgNativeBoolean(p.current_price_authority_available)||
    mtgNativeBoolean(p.forecast_authority_available)||
    mtgNativeHasValue(p.native_rank)
  ){
    return "partial";
  }

  return "blocked";
}

function mtgNativePayload(item){
  if(
    item&&
    item.__mtg_native_payload&&
    typeof item.__mtg_native_payload==="object"
  ){
    return item.__mtg_native_payload;
  }

  return item?.payload||{};
}

function mtgNativeRecordPayload(detail,type){
  const rows=
    Array.isArray(detail?.records?.[type])
      ?detail.records[type]
      :[];

  if(!rows.length){
    return {};
  }

  const row=rows[0];

  if(
    row&&
    typeof row.payload==="object"&&
    row.payload!==null
  ){
    return row.payload;
  }

  return row&&typeof row==="object"
    ?row
    :{};
}

function mtgNativeRecordPayloads(detail,type){
  const rows=
    Array.isArray(detail?.records?.[type])
      ?detail.records[type]
      :[];

  return rows.map(
    row=>{
      if(
        row&&
        typeof row.payload==="object"&&
        row.payload!==null
      ){
        return row.payload;
      }

      return row&&typeof row==="object"
        ?row
        :{};
    }
  );
}

function mtgNativeDisplayValue(value,formatter=null){
  if(!mtgNativeHasValue(value)){
    return "Missing";
  }

  return typeof formatter==="function"
    ?formatter(value)
    :cleanStatus(value);
}

function mtgNativeRankDisplay(value){
  return mtgNativeHasValue(value)
    ?`#${fmtNumber(value,0)}`
    :"Not ranked";
}

function mtgNativeCollectorHorizonChart(horizons){
  const rows=
    horizons
      .map(
        row=>({
          horizon:Number(row.horizon_days),
          p10:Number(row.p10_price),
          median:Number(row.median_price),
          p90:Number(row.p90_price)
        })
      )
      .filter(
        row=>
          Number.isFinite(row.horizon)&&
          Number.isFinite(row.p10)&&
          Number.isFinite(row.median)&&
          Number.isFinite(row.p90)
      );

  if(rows.length<2){
    return "";
  }

  const width=760;
  const height=235;
  const left=52;
  const right=18;
  const top=20;
  const bottom=40;

  const minHorizon=
    Math.min(
      ...rows.map(row=>row.horizon)
    );

  const maxHorizon=
    Math.max(
      ...rows.map(row=>row.horizon)
    );

  const allPrices=
    rows.flatMap(
      row=>[
        row.p10,
        row.median,
        row.p90
      ]
    );

  const minPrice=
    Math.min(...allPrices);

  const maxPrice=
    Math.max(...allPrices);

  const horizonSpan=
    maxHorizon-minHorizon||1;

  const priceSpan=
    maxPrice-minPrice||1;

  const x=
    horizon=>
      left+
      (
        (horizon-minHorizon)/
        horizonSpan
      )*
      (width-left-right);

  const y=
    price=>
      top+
      (
        1-
        (
          (price-minPrice)/
          priceSpan
        )
      )*
      (height-top-bottom);

  const points=
    key=>
      rows.map(
        row=>
          `${x(row.horizon).toFixed(1)},${y(row[key]).toFixed(1)}`
      ).join(" ");

  const horizonLabels=
    rows.map(
      row=>`
        <text
          x="${x(row.horizon).toFixed(1)}"
          y="${height-12}"
          text-anchor="middle"
        >
          ${escapeHtml(`${fmtNumber(row.horizon,0)}d`)}
        </text>`
    ).join("");

  const grid=
    [0,.25,.5,.75,1].map(
      portion=>{
        const gridY=
          top+
          portion*
          (height-top-bottom);

        return `
          <line
            class="mtg-native-horizon-grid"
            x1="${left}"
            x2="${width-right}"
            y1="${gridY.toFixed(1)}"
            y2="${gridY.toFixed(1)}"
          ></line>`;
      }
    ).join("");

  return `
    <div class="mtg-native-horizon-viz">

      <div class="mtg-native-horizon-viz-head">

        <div>
          <span>Modeled horizon path</span>
          <strong>
            Governed P10 / Median / P90
          </strong>
        </div>

        <div class="mtg-native-horizon-legend">
          <span class="p10">P10</span>
          <span class="median">Median</span>
          <span class="p90">P90</span>
        </div>

      </div>

      <svg
        viewBox="0 0 ${width} ${height}"
        role="img"
        aria-label="Collector governed P10, median, and P90 modeled prices across populated horizons"
      >

        ${grid}

        <polyline
          class="mtg-native-horizon-line p10"
          points="${points("p10")}"
        ></polyline>

        <polyline
          class="mtg-native-horizon-line p90"
          points="${points("p90")}"
        ></polyline>

        <polyline
          class="mtg-native-horizon-line median"
          points="${points("median")}"
        ></polyline>

        ${horizonLabels}

      </svg>

      <p>
        Exact populated horizons only.
        No missing horizon is interpolated.
      </p>

    </div>`;
}

function mtgNativeCollectorResearchPanel(detail){
  const product=
    mtgNativeRecordPayload(
      detail,
      "mtg_collector_research"
    );

  const horizons=
    mtgNativeRecordPayloads(
      detail,
      "mtg_collector_forecast_horizon"
    )
      .slice()
      .sort(
        (a,b)=>
          Number(a.horizon_days)-
          Number(b.horizon_days)
      );

  if(!Object.keys(product).length){
    return `
      <article class="rec-side-panel mtg-native-rich-panel">
        <div class="mtg-native-rich-heading">
          <div>
            <span class="eyebrow">COLLECTOR NATIVE RESEARCH</span>
            <h4>Research detail unavailable</h4>
          </div>
        </div>
        <p class="governance-note">
          No Collector lane-native research record is available for this
          product. Missing research is not replaced with synthetic values.
        </p>
      </article>`;
  }

  const score=
    mtgNativeDisplayValue(
      product.final_governed_score,
      value=>fmtNumber(value,3)
    );

  const prePenalty=
    mtgNativeDisplayValue(
      product.weighted_score_before_penalty,
      value=>fmtNumber(value,3)
    );

  const finalRank=
    mtgNativeRankDisplay(
      product.final_rank
    );

  const purchaseStatus=
    mtgNativeDisplayValue(
      product.purchase_status
    );

  const rankTier=
    mtgNativeDisplayValue(
      product.rank_tier
    );

  const calibration365=
    mtgNativeDisplayValue(
      product.calibration_status_365
    );

  const calibration1095=
    mtgNativeDisplayValue(
      product.calibration_status_1095
    );

  const rankingStageEligibility=
    mtgNativeHasValue(
      product.purchase_eligible_at_this_stage
    )
      ?(
          mtgNativeBoolean(
            product.purchase_eligible_at_this_stage
          )
            ?"Eligible"
            :"Not eligible"
        )
      :"Missing";

  const limitations=
    mtgNativeHasValue(
      product.limitations
    )
      ?cleanStatus(
          product.limitations
        )
      :"No populated limitations text.";

  const horizonRows=
    horizons.length
      ?horizons.map(
          row=>`
            <tr>
              <td>${escapeHtml(`${fmtNumber(row.horizon_days,0)}d`)}</td>
              <td>${escapeHtml(fmtMoney(row.median_price))}</td>
              <td>${escapeHtml(fmtPercent(row.median_expected_return))}</td>
              <td>${escapeHtml(fmtMoney(row.p10_price))}</td>
              <td>${escapeHtml(fmtMoney(row.p90_price))}</td>
              <td>${escapeHtml(fmtPercent(row.probability_of_loss))}</td>
              <td>${escapeHtml(fmtPercent(row.probability_of_50pct_gain))}</td>
              <td>${escapeHtml(fmtPercent(row.probability_of_doubling))}</td>
            </tr>`
        ).join("")
      :`
        <tr>
          <td colspan="8">
            <div class="mtg-native-rich-empty">
              No governed Collector forecast-horizon records are available.
              This product remains current-price-only where applicable.
            </div>
          </td>
        </tr>`;

  return `
    <article class="rec-side-panel mtg-native-rich-panel mtg-native-collector-rich">

      <div class="mtg-native-rich-heading">
        <div>
          <span class="eyebrow">
            COLLECTOR NATIVE RESEARCH
          </span>
          <h4>
            Ranking, calibration & modeled horizon evidence
          </h4>
        </div>

        <span class="mtg-native-rich-count">
          ${horizons.length} horizon${horizons.length===1?"":"s"}
        </span>
      </div>

      <div class="mtg-native-rich-kpis">

        <div>
          <span>Final Collector rank</span>
          <strong>${escapeHtml(finalRank)}</strong>
          <small>Governed Collector ranking only</small>
        </div>

        <div>
          <span>Final governed score</span>
          <strong>${escapeHtml(score)}</strong>
          <small>Lane-native score; not a UIP universal score</small>
        </div>

        <div>
          <span>Pre-penalty score</span>
          <strong>${escapeHtml(prePenalty)}</strong>
          <small>weighted_score_before_penalty</small>
        </div>

        <div>
          <span>Purchase status</span>
          <strong>${escapeHtml(purchaseStatus)}</strong>
          <small>Final purchase-authority record</small>
        </div>

        <div>
          <span>Rank tier</span>
          <strong>${escapeHtml(rankTier)}</strong>
          <small>Collector ranking tier</small>
        </div>

        <div>
          <span>Ranking-stage eligibility</span>
          <strong>${escapeHtml(rankingStageEligibility)}</strong>
          <small>
            Context only; final purchase authority is separate
          </small>
        </div>

      </div>

      <div class="mtg-native-calibration-grid">

        <div>
          <span>365d calibration</span>
          <strong>${escapeHtml(calibration365)}</strong>
        </div>

        <div>
          <span>1095d calibration</span>
          <strong>${escapeHtml(calibration1095)}</strong>
        </div>

      </div>

      <div class="mtg-native-limitations">
        <span>Model limitations</span>
        <p>${escapeHtml(limitations)}</p>
      </div>

      ${mtgNativeCollectorHorizonChart(horizons)}

      <div class="mtg-native-rich-table-wrap">
        <table class="mtg-native-rich-table">
          <thead>
            <tr>
              <th>Horizon</th>
              <th>Median price</th>
              <th>Median return</th>
              <th>P10</th>
              <th>P90</th>
              <th>P(loss)</th>
              <th>P(+50%)</th>
              <th>P(2x)</th>
            </tr>
          </thead>
          <tbody>
            ${horizonRows}
          </tbody>
        </table>
      </div>

      <p class="governance-note">
        These are the governed Collector horizon records actually present for
        this product. UIP does not interpolate missing horizons or manufacture
        Bear/Base/Bull scenarios.
      </p>

    </article>`;
}

function mtgNativePreCollectorResearchPanel(detail){
  const product=
    mtgNativeRecordPayload(
      detail,
      "mtg_precollector_research"
    );

  const scenarios=
    mtgNativeRecordPayloads(
      detail,
      "mtg_precollector_scenario_horizon"
    )
      .slice()
      .sort(
        (a,b)=>
          Number(a.monte_carlo_horizon_years)-
          Number(b.monte_carlo_horizon_years)
      );

  if(!Object.keys(product).length){
    return `
      <article class="rec-side-panel mtg-native-rich-panel">
        <div class="mtg-native-rich-heading">
          <div>
            <span class="eyebrow">PRE-COLLECTOR NATIVE RESEARCH</span>
            <h4>Research detail unavailable</h4>
          </div>
        </div>
        <p class="governance-note">
          No Pre-Collector lane-native research record is available.
          Missing ranks and scenarios remain missing.
        </p>
      </article>`;
  }

  const purchaseRank=
    mtgNativeRankDisplay(
      product.purchase_rank
    );

  const highConfidenceRank=
    mtgNativeRankDisplay(
      product.high_confidence_rank
    );

  const speculativeRank=
    mtgNativeRankDisplay(
      product.speculative_rank
    );

  const combinedScore=
    mtgNativeDisplayValue(
      product.combined_purchase_score,
      value=>fmtNumber(value,3)
    );

  const tier=
    mtgNativeDisplayValue(
      product.investment_tier
    );

  const forecast365=
    mtgNativeDisplayValue(
      product.forecast_price_365d,
      fmtMoney
    );

  const scenarioCards=
    scenarios.length
      ?scenarios.map(
          row=>{
            const years=
              fmtNumber(
                row.monte_carlo_horizon_years,
                0
              );

            const directlyBacktested=
              mtgNativeBoolean(
                row.directly_backtested_at_this_horizon
              );

            const modelRank=
              mtgNativeRankDisplay(
                row.model_rank
              );

            return `
              <article class="mtg-native-scenario-card">

                <div class="mtg-native-scenario-head">
                  <div>
                    <span>${escapeHtml(`${years}Y scenario`)}</span>
                    <strong>${escapeHtml(fmtMoney(row.terminal_price_median))} terminal median</strong>
                  </div>

                  <span class="mtg-native-scenario-badge ${directlyBacktested?"direct":"scenario"}">
                    ${
                      directlyBacktested
                        ?"Directly backtested"
                        :"Scenario only - not directly backtested"
                    }
                  </span>
                </div>

                <div class="mtg-native-scenario-primary">

                  <div>
                    <span>Terminal median</span>
                    <strong>${escapeHtml(fmtMoney(row.terminal_price_median))}</strong>
                  </div>

                  <div>
                    <span>Median CAGR</span>
                    <strong>${escapeHtml(fmtPercent(row.median_cagr))}</strong>
                  </div>

                  <div>
                    <span>Loss probability</span>
                    <strong>${escapeHtml(fmtPercent(row.probability_capital_loss))}</strong>
                  </div>

                </div>

                <div class="mtg-native-scenario-metrics">

                  <div>
                    <span>P(positive return)</span>
                    <strong>${escapeHtml(fmtPercent(row.probability_positive_return))}</strong>
                  </div>

                  <div>
                    <span>Downside CVaR10</span>
                    <strong>${escapeHtml(fmtPercent(row.return_cvar10))}</strong>
                  </div>

                  <div>
                    <span>Median max drawdown</span>
                    <strong>${escapeHtml(fmtPercent(row.median_max_drawdown))}</strong>
                  </div>

                </div>

                <div class="mtg-native-scenario-foot">

                  <span>
                    Model rank ${escapeHtml(modelRank)}
                  </span>

                  <span>
                    ${escapeHtml(cleanStatus(row.scenario_classification))}
                  </span>

                  <span>
                    Confidence ${escapeHtml(cleanStatus(row.confidence_quartile))}
                  </span>
                </div>

              </article>`;
          }
        ).join("")
      :`
        <div class="mtg-native-rich-empty">
          No certified 3Y/5Y scenario rows are available for this product.
          No long-range scenario is inferred.
        </div>`;

  return `
    <article class="rec-side-panel mtg-native-rich-panel mtg-native-pre-rich">

      <div class="mtg-native-rich-heading">
        <div>
          <span class="eyebrow">
            PRE-COLLECTOR NATIVE RESEARCH
          </span>
          <h4>
            Purchase ranking & long-range scenario evidence
          </h4>
        </div>

        <span class="mtg-native-rich-count">
          ${scenarios.length} scenario${scenarios.length===1?"":"s"}
        </span>
      </div>

      <div class="mtg-native-rich-kpis">

        <div>
          <span>Purchase rank</span>
          <strong>${escapeHtml(purchaseRank)}</strong>
          <small>Primary governed purchase ranking</small>
        </div>

        <div>
          <span>High-confidence rank</span>
          <strong>${escapeHtml(highConfidenceRank)}</strong>
          <small>Separate certified 88-product subset</small>
        </div>

        <div>
          <span>Speculative rank</span>
          <strong>${escapeHtml(speculativeRank)}</strong>
          <small>Separate certified 6-product subset</small>
        </div>

        <div>
          <span>Combined purchase score</span>
          <strong>${escapeHtml(combinedScore)}</strong>
          <small>Pre-Collector native score</small>
        </div>

        <div>
          <span>Investment tier</span>
          <strong>${escapeHtml(tier)}</strong>
          <small>Pre-Collector lane-native tier</small>
        </div>

        <div>
          <span>Certified 365d price</span>
          <strong>${escapeHtml(forecast365)}</strong>
          <small>Separate from 3Y/5Y Monte Carlo scenarios</small>
        </div>

      </div>

      <div class="mtg-native-scenario-grid">
        ${scenarioCards}
      </div>

      <p class="governance-note">
        Purchase rank, high-confidence rank, speculative rank, and per-horizon
        model rank are separate governed concepts. The 3Y/5Y rows are scenario
        evidence and are not relabeled as directly backtested forecasts.
      </p>

    </article>`;
}

function mtgNativeRichResearchPanel(item,detail){
  const lane=
    mtgLaneForItem(item);

  if(lane==="collector"){
    return mtgNativeCollectorResearchPanel(
      detail
    );
  }

  if(lane==="pre_collector"){
    return mtgNativePreCollectorResearchPanel(
      detail
    );
  }

  return "";
}

function mtgNormalizeNativeDetailAuthority(item,detail){
  const normalized={
    ...(item?.payload||{})
  };

  const asset=
    mtgNativeRecordPayload(
      detail,
      "asset"
    );

  const forecast=
    mtgNativeRecordPayload(
      detail,
      "forecast"
    );

  const recommendation=
    mtgNativeRecordPayload(
      detail,
      "recommendation"
    );

  const risk=
    mtgNativeRecordPayload(
      detail,
      "risk"
    );

  const collectorResearch=
    mtgNativeRecordPayload(
      detail,
      "mtg_collector_research"
    );

  const preCollectorResearch=
    mtgNativeRecordPayload(
      detail,
      "mtg_precollector_research"
    );

  for(const field of [
    "final_governed_score",
    "final_rank",
    "rank_tier",
    "median_price_365",
    "median_return_365",
    "probability_of_loss_365",
    "purchase_status",
    "recommended_quantity",
    "candidate_entry_ceiling",
    "strong_entry_ceiling",
    "calibration_status_365",
    "calibration_status_1095",
    "limitations",
    "purchase_eligible_at_this_stage",
    "weighted_score_before_penalty"
  ]){
    if(
      Object.prototype.hasOwnProperty.call(
        collectorResearch,
        field
      )
    ){
      normalized[field]=collectorResearch[field];
    }
  }

  for(const field of [
    "purchase_rank",
    "high_confidence_rank",
    "speculative_rank",
    "combined_purchase_score",
    "investment_tier",
    "forecast_price_365d",
    "median_cagr_3y",
    "median_cagr_5y",
    "probability_positive_3y",
    "probability_positive_5y",
    "downside_cvar10_3y",
    "downside_cvar10_5y",
    "confidence_quartile",
    "not_ranked_reason"
  ]){
    if(
      Object.prototype.hasOwnProperty.call(
        preCollectorResearch,
        field
      )
    ){
      normalized[field]=preCollectorResearch[field];
    }
  }

  const observedPriceAuthority=
    mtgNativeBoolean(
      asset.current_price_authority_available
    );

  if(observedPriceAuthority){
    normalized.current_price_authority_available=true;

    if(mtgNativeHasValue(asset.current_price_usd)){
      normalized.current_price_usd=
        asset.current_price_usd;
    }
  }

  if(mtgNativeHasValue(asset.lane_authority_state)){
    normalized.lane_authority_state=
      asset.lane_authority_state;
  }

  const observedForecastAuthority=
    mtgNativeBoolean(
      forecast.forecast_authority_available
    );

  if(observedForecastAuthority){
    normalized.forecast_authority_available=true;

    if(mtgNativeHasValue(forecast.point_forecast)){
      normalized.forecast_1y_price_usd=
        forecast.point_forecast;
    }

    if(mtgNativeHasValue(forecast.expected_return)){
      normalized.forecast_1y_return=
        forecast.expected_return;
    }

    if(mtgNativeHasValue(forecast.forecast_horizon_months)){
      normalized.forecast_horizon_months=
        forecast.forecast_horizon_months;
    }

    if(mtgNativeHasValue(forecast.forecast_method)){
      normalized.forecast_method=
        forecast.forecast_method;
    }
  }

  if(
    mtgNativeBoolean(
      risk.risk_authority_available
    )
  ){
    normalized.risk_authority_available=true;
  }

  for(const field of [
    "native_rank",
    "native_rank_type",
    "native_purchase_status",
    "purchase_semantic",
    "evidence_state",
    "actionability_state",
    "native_asset_id",
    "native_authority_pointer",
    "native_authority_sha256",
    "lane_authority_state",
    "manual_execution_price_check_required",
    "execution_ready_purchase_certified",
    "snapshot_population_is_permanent"
  ]){
    if(mtgNativeHasValue(recommendation[field])){
      normalized[field]=
        recommendation[field];
    }
  }

  return normalized;
}
async function mtgHydrateNativeResearch(items){
  await Promise.all(
    items.map(
      async item=>{
        if(item.__mtg_native_detail_attempted){
          return;
        }

        item.__mtg_native_detail_attempted=true;

        try{
          const detail=
            await readAssetDetail(item);

          item.__mtg_native_detail=
            detail;

          item.__mtg_native_payload=
            mtgNormalizeNativeDetailAuthority(
              item,
              detail
            );

          item.__mtg_native_detail_error=
            null;
        }catch(error){
          item.__mtg_native_detail=
            null;

          item.__mtg_native_payload={
            ...(item.payload||{})
          };

          item.__mtg_native_detail_error=
            String(
              error?.message||
              error||
              "Generic asset-detail request failed."
            );
        }
      }
    )
  );
}
function mtgNativeAuthorityCount(p){
  return [
    p.current_price_authority_available,
    p.forecast_authority_available,
    p.risk_authority_available
  ].filter(mtgNativeBoolean).length;
}

function mtgNativeReturnDirection(p){
  if(
    !mtgNativeBoolean(
      p.forecast_authority_available
    )
  ){
    return "missing";
  }

  const value=
    Number(p.forecast_1y_return);

  if(!Number.isFinite(value)){
    return "missing";
  }

  if(value>0){
    return "positive";
  }

  if(value<0){
    return "negative";
  }

  return "flat";
}

function mtgNativePriceJourney(p){
  const priceAvailable=
    mtgNativeBoolean(
      p.current_price_authority_available
    );

  const forecastAvailable=
    mtgNativeBoolean(
      p.forecast_authority_available
    );

  if(
    !priceAvailable||
    !forecastAvailable||
    !mtgNativeHasValue(p.current_price_usd)||
    !mtgNativeHasValue(p.forecast_1y_price_usd)
  ){
    return `
      <div class="mtg-native-journey mtg-native-journey-missing">
        <div class="mtg-native-journey-message">
          Current-to-target visualization unavailable
        </div>
      </div>`;
  }

  const current=
    Number(p.current_price_usd);

  const target=
    Number(p.forecast_1y_price_usd);

  const direction=
    target>=current
      ?"up"
      :"down";

  return `
    <div class="mtg-native-journey mtg-native-journey-${direction}">
      <div class="mtg-native-journey-values">
        <div>
          <span>Current</span>
          <strong>${escapeHtml(fmtMoney(current))}</strong>
        </div>

        <div>
          <span>1Y target</span>
          <strong>${escapeHtml(fmtMoney(target))}</strong>
        </div>
      </div>

      <div class="mtg-native-journey-track">
        <i class="current"></i>
        <span></span>
        <i class="target"></i>
      </div>

      <div class="mtg-native-journey-axis">
        <span>Market today</span>
        <span>Governed 12M model</span>
      </div>
    </div>`;
}

function mtgNativeAuthorityVisual(p){
  const count=
    mtgNativeAuthorityCount(p);

  return `
    <div class="mtg-native-authority-visual">
      <div>
        <span>Authority coverage</span>
        <strong>${count}/3</strong>
      </div>

      <div class="mtg-native-authority-dots" aria-label="${count} of 3 authority categories available">
        ${[0,1,2].map(
          index=>`
            <i class="${index<count?"on":""}"></i>`
        ).join("")}
      </div>
    </div>`;
}
function mtgNativeCard(item){
  const p=
    mtgNativePayload(item);

  const rank=
    p.native_rank==null
      ?"Not ranked"
      :fmtNumber(
          p.native_rank,
          0
        );

  const lane=
    mtgLaneLabel(
      mtgLaneForItem(item)
    );

  const state=
    mtgNativeCardState(item);

  const currentAvailable=
    mtgNativeBoolean(
      p.current_price_authority_available
    );

  const forecastAvailable=
    mtgNativeBoolean(
      p.forecast_authority_available
    );

  const currentPrice=
    currentAvailable
      ?fmtMoney(p.current_price_usd)
      :"Missing";

  const targetPrice=
    forecastAvailable
      ?fmtMoney(p.forecast_1y_price_usd)
      :"Missing";

  const expectedReturn=
    forecastAvailable
      ?fmtPercent(p.forecast_1y_return)
      :"Missing";

  const returnDirection=
    mtgNativeReturnDirection(p);

  return `
    <article class="rec-asset-card mtg-native-card mtg-native-${state} mtg-native-visual-parity">

      <div class="rec-asset-head">

        <div class="rec-asset-id">

          <div class="rec-coin mtg-product-icon">
            MTG
          </div>

          <div class="rec-asset-name">
            <strong>
              ${escapeHtml(displayName(item))}
            </strong>

            <small>
              ${escapeHtml(lane)}
            </small>
          </div>

        </div>

        <div class="mtg-native-rank-status">

          <span class="mtg-native-rank-badge">
            #${escapeHtml(rank)}
          </span>

          <span class="rec-status">
            ${escapeHtml(
              cleanStatus(
                p.native_purchase_status||
                nativeStatus(item)
              )
            )}
          </span>

        </div>

      </div>

      <div class="mtg-native-card-thesis">

        <div>
          <span>Expected 1Y return</span>

          <strong class="mtg-native-return-${returnDirection}">
            ${escapeHtml(expectedReturn)}
          </strong>

          <small>
            ${
              forecastAvailable
                ?"Governed native 12-month model"
                :"Forecast authority unavailable"
            }
          </small>
        </div>

        <div class="mtg-native-card-target">
          <span>1Y modeled target</span>
          <strong>${escapeHtml(targetPrice)}</strong>

          <small>
            Current ${escapeHtml(currentPrice)}
          </small>
        </div>

      </div>

      ${mtgNativePriceJourney(p)}

      <div class="mtg-native-card-foot">

        ${mtgNativeAuthorityVisual(p)}

        <button
          type="button"
          class="rec-research-button rec-mtg-native-detail"
          data-asset-id="${escapeHtml(item.asset_id)}"
        >
          Open research &rarr;
        </button>

      </div>

      <details class="mtg-native-card-secondary">

        <summary>
          Decision context
        </summary>

        <div class="mtg-native-card-semantics">

          <div>
            <span>Native purchase tier</span>
            <strong>
              ${escapeHtml(
                cleanStatus(
                  p.native_purchase_status
                )
              )}
            </strong>
          </div>

          <div>
            <span>Ranking evidence state</span>
            <strong>
              ${escapeHtml(
                cleanStatus(
                  p.evidence_state
                )
              )}
            </strong>
          </div>

          <div>
            <span>Actionability</span>
            <strong>
              ${escapeHtml(
                cleanStatus(
                  p.actionability_state
                )
              )}
            </strong>
          </div>

        </div>

        <p class="mtg-native-card-governance">
          Lane-native ranking only
          &middot;
          Manual execution only
        </p>

      </details>

    </article>`;
}
/* MTG_FINAL_UX_REFINEMENT_V1 */
function mtgNativeMissingReasons(item){
  const p=mtgNativePayload(item);
  const reasons=[];

  if(
    !mtgNativeBoolean(
      p.current_price_authority_available
    )
  ){
    reasons.push(
      "No governed current-price authority is available."
    );
  }

  if(
    !mtgNativeBoolean(
      p.forecast_authority_available
    )
  ){
    reasons.push(
      "No governed one-year forecast authority is available."
    );
  }

  if(
    !mtgNativeBoolean(
      p.risk_authority_available
    )
  ){
    reasons.push(
      "No governed risk authority is available."
    );
  }

  if(!mtgNativeHasValue(p.native_rank)){
    reasons.push(
      "No native lane rank is available for this asset."
    );
  }

  return reasons;
}

function mtgNativeObservedRecordPanel(detail){
  const records=
    detail&&
    typeof detail.records==="object"&&
    detail.records!==null
      ?detail.records
      :{};

  const types=
    Object.keys(records)
      .filter(
        type=>
          Array.isArray(records[type])&&
          records[type].length
      )
      .sort();

  if(!types.length){
    return `
      <details class="rec-side-panel mtg-native-observed-records">
        <summary>Technical provenance</summary>

        <div class="mtg-native-observed-empty">
          Generic UIP presentation records unavailable.
        </div>
      </details>`;
  }

  return `
    <details class="rec-side-panel mtg-native-observed-records">
      <summary>
        Technical provenance
        &middot;
        Generic UIP presentation records
      </summary>

      <div class="mtg-native-observed-record-list">
        ${types.map(
          type=>{
            const rows=
              records[type];

            return `
              <div class="mtg-native-observed-record-row">
                <span>${escapeHtml(cleanStatus(type))}</span>
                <strong>${escapeHtml(fmtNumber(rows.length,0))} record${rows.length===1?"":"s"}</strong>
              </div>`;
          }
        ).join("")}
      </div>
    </details>`;
}
async function openMtgNativeDetail(page,item){
  const lane=
    mtgLaneForItem(item);

  if(
    lane!=="collector"&&
    lane!=="pre_collector"
  ){
    throw new Error(
      "Native MTG detail renderer received a non-native-lane asset."
    );
  }

  page.innerHTML=`
    <div class="rec-shell">
      <div class="mtg-detail-loading">
        Loading native MTG research...
      </div>
    </div>`;

  let detail=
    item.__mtg_native_detail||null;

  let detailError=
    item.__mtg_native_detail_error||null;

  if(!item.__mtg_native_detail_attempted){
    try{
      detail=
        await readAssetDetail(item);

      item.__mtg_native_detail=
        detail;

      item.__mtg_native_detail_attempted=
        true;

      item.__mtg_native_detail_error=
        null;

      detailError=null;
    }catch(error){
      item.__mtg_native_detail_attempted=
        true;

      detailError=
        String(
          error?.message||
          error||
          "Generic asset-detail request failed."
        );

      item.__mtg_native_detail_error=
        detailError;
    }
  }

  const p=
    mtgNormalizeNativeDetailAuthority(
      item,
      detail
    );

  item.__mtg_native_payload=p;

  const rank=
    p.native_rank==null
      ?"Not ranked"
      :fmtNumber(
          p.native_rank,
          0
        );

  const laneLabel=
    mtgLaneLabel(lane);

  const status=
    cleanStatus(
      p.native_purchase_status||
      p.actionability_state||
      nativeStatus(item)
    );

  const currentPriceAvailable=
    mtgNativeBoolean(
      p.current_price_authority_available
    );

  const forecastAvailable=
    mtgNativeBoolean(
      p.forecast_authority_available
    );

  const riskAvailable=
    mtgNativeBoolean(
      p.risk_authority_available
    );

  const missing=
    mtgNativeMissingReasons(item);

  const currentPrice=
    currentPriceAvailable
      ?fmtMoney(p.current_price_usd)
      :"Missing";

  const forecastPrice=
    forecastAvailable
      ?fmtMoney(p.forecast_1y_price_usd)
      :"Missing";

  const forecastReturn=
    forecastAvailable
      ?fmtPercent(p.forecast_1y_return)
      :"Missing";

  const returnDirection=
    mtgNativeReturnDirection(p);

  const heroHeadline=
    forecastAvailable
      ?`<span class="return mtg-native-return-${returnDirection}">${escapeHtml(forecastReturn)}</span> modeled 1Y return`
      :`1Y forecast authority <span class="mtg-native-return-missing">unavailable</span>`;

  const authorityClass=
    missing.length===0
      ?"research-ready"
      :(
          missing.length>=3
            ?"blocked"
            :"partial"
        );

  page.innerHTML=`
    ${recommendationDomainSummaryAnchor()}

    <div class="rec-shell rec-detail mtg-native-detail mtg-native-detail-visual-parity">

      <div class="rec-detail-head">

        <div class="rec-detail-title">

          <span class="eyebrow">
            MTG
            &middot;
            ${escapeHtml(laneLabel.toUpperCase())}
            INVESTMENT RESEARCH
          </span>

          <h2>
            ${escapeHtml(displayName(item))}
          </h2>

          <p>
            Native lane rank ${escapeHtml(rank)}
            &middot;
            ${escapeHtml(status)}
          </p>

        </div>

        <button
          type="button"
          id="mtg-native-back"
          class="secondary"
        >
          &#8592; Back to ${escapeHtml(laneLabel)}
        </button>

      </div>

      <section class="rec-strategic-hero mtg-native-detail-hero mtg-native-detail-${authorityClass}">

        <div class="mtg-native-strategic-copy">

          <span class="eyebrow">
            GOVERNED 1-YEAR OUTLOOK
          </span>

          <h3>
            ${heroHeadline}
          </h3>

          <p class="rec-strategic-copy">
            ${
              forecastAvailable&&currentPriceAvailable
                ?`Current market ${escapeHtml(currentPrice)} versus governed 1Y modeled target ${escapeHtml(forecastPrice)}.`
                :"Only governed values available for this native MTG lane are displayed."
            }
          </p>

          <div class="rec-chips">

            <span class="rec-chip mtg-rank-chip">
              Native rank ${escapeHtml(rank)}
            </span>

            <span class="rec-chip">
              ${escapeHtml(status)}
            </span>

            <span class="rec-chip">
              ${
                mtgNativeHasValue(p.lane_authority_state)
                  ?`Lane authority ${escapeHtml(cleanStatus(p.lane_authority_state))}`
                  :"Lane authority unavailable"
              }
            </span>

          </div>

        </div>

        <div class="mtg-native-detail-journey">

          ${mtgNativePriceJourney(p)}

          ${mtgNativeAuthorityVisual(p)}

        </div>

      </section>

      <section class="rec-kpi-row mtg-native-detail-kpis mtg-native-visual-kpis">

        <article class="rec-kpi-card">
          <div class="rec-kpi-label">
            <span class="rec-kpi-dot">$</span>
            Current market
          </div>

          <strong>
            ${escapeHtml(currentPrice)}
          </strong>

          <small class="page-note">
            ${
              currentPriceAvailable
                ?"Governed current-price authority"
                :"Authority unavailable"
            }
          </small>
        </article>

        <article class="rec-kpi-card base">
          <div class="rec-kpi-label">
            <span class="rec-kpi-dot">&#8594;</span>
            Native 1Y forecast
            &middot;
            1Y modeled target
          </div>

          <strong>
            ${escapeHtml(forecastPrice)}
          </strong>

          <small class="page-note">
            ${
              forecastAvailable
                ?escapeHtml(
                    cleanStatus(
                      p.forecast_method||
                      "mtg_native_1y"
                    )
                  )
                :"Forecast unavailable"
            }
          </small>
        </article>

        <article class="rec-kpi-card">
          <div class="rec-kpi-label">
            <span class="rec-kpi-dot">&#8599;</span>
            Expected 1Y return
          </div>

          <strong class="mtg-native-return-${returnDirection}">
            ${escapeHtml(forecastReturn)}
          </strong>

          <small class="page-note">
            ${
              forecastAvailable
                ?`${escapeHtml(String(p.forecast_horizon_months||12))} month horizon`
                :"Forecast unavailable"
            }
          </small>
        </article>

        <article class="rec-kpi-card">
          <div class="rec-kpi-label">
            <span class="rec-kpi-dot">#</span>
            Native lane rank
          </div>

          <strong>
            ${escapeHtml(rank)}
          </strong>

          <small class="page-note">
            ${escapeHtml(cleanStatus(p.native_rank_type))}
          </small>
        </article>

      </section>

      <section class="rec-detail-grid">

        <div class="mtg-detail-main">

          <article class="rec-forecast-panel mtg-native-thesis-panel">

            <div class="rec-panel-head">
              <h4>Why this product ranks here</h4>

              <p>
                Separate governed recommendation, ranking-evidence,
                and actionability fields are shown without reconciliation.
              </p>
            </div>

            <div class="mtg-native-thesis-grid">

              <div>
                <span>Native purchase tier</span>
                <strong>
                  ${escapeHtml(cleanStatus(p.native_purchase_status))}
                </strong>

                <p>
                  Governed lane-specific purchase classification.
                </p>
              </div>

              <div>
                <span>Ranking evidence state</span>
                <strong>
                  ${escapeHtml(cleanStatus(p.evidence_state))}
                </strong>

                <p>
                  Source ranking-evidence field; it is not the purchase tier.
                </p>
              </div>

              <div>
                <span>Actionability</span>
                <strong>
                  ${escapeHtml(cleanStatus(p.actionability_state))}
                </strong>

                <p>
                  Governed recommendation actionability state.
                </p>
              </div>

              <div>
                <span>Purchase semantic</span>
                <strong>
                  ${escapeHtml(cleanStatus(p.purchase_semantic))}
                </strong>

                <p>
                  Native semantic retained exactly from certified authority.
                </p>
              </div>

            </div>

          </article>

          <article class="rec-forecast-panel">

            <div class="rec-panel-head">
              <h4>Certified native authority</h4>

              <p>
                Primary investment authority used by this research view.
              </p>
            </div>

            <div class="mtg-native-authority-table">

              <div>
                <span>Lane authority</span>

                <strong>
                  ${escapeHtml(
                    mtgNativeHasValue(p.lane_authority_state)
                      ?cleanStatus(p.lane_authority_state)
                      :"Unavailable"
                  )}
                </strong>
              </div>

              <div>
                <span>Current price authority</span>
                <strong>
                  ${currentPriceAvailable?"AVAILABLE":"UNAVAILABLE"}
                </strong>
              </div>

              <div>
                <span>Forecast authority</span>
                <strong>
                  ${forecastAvailable?"AVAILABLE":"UNAVAILABLE"}
                </strong>
              </div>

              <div>
                <span>Risk authority</span>
                <strong>
                  ${riskAvailable?"AVAILABLE":"UNAVAILABLE"}
                </strong>
              </div>

              <div>
                <span>Manual price check</span>
                <strong>
                  ${
                    mtgNativeBoolean(
                      p.manual_execution_price_check_required
                    )
                      ?"REQUIRED"
                      :"NOT REQUIRED"
                  }
                </strong>
              </div>

              <div>
                <span>Execution certification</span>
                <strong>
                  ${
                    mtgNativeBoolean(
                      p.execution_ready_purchase_certified
                    )
                      ?"CERTIFIED"
                      :"NOT CERTIFIED"
                  }
                </strong>
              </div>

            </div>

          </article>

          <div class="mtg-native-provenance-heading">
            <span>Lane-native research</span>
            <small>Governed product and horizon evidence</small>
          </div>

          ${mtgNativeRichResearchPanel(item,detail)}
          ${mtgNativeObservedRecordPanel(detail)}

        </div>

        <aside class="mtg-detail-side">

          <details class="rec-side-panel mtg-native-methodology-disclosure">

            <summary>

              <div>
                <strong>Authority & methodology</strong>
                <span>
                  ${mtgNativeAuthorityCount(p)}/3 authority categories
                  &middot;
                  native lineage retained
                </span>
              </div>

              ${mtgNativeAuthorityVisual(p)}

            </summary>

            <div class="mtg-native-methodology-body">

              <section>
                <h5>Authority coverage</h5>

                <div class="mtg-native-authority-list">

                  <div>
                    <span>Current market</span>
                    <strong>
                      ${currentPriceAvailable?"Available":"Missing"}
                    </strong>
                  </div>

                  <div>
                    <span>1Y forecast</span>
                    <strong>
                      ${forecastAvailable?"Available":"Missing"}
                    </strong>
                  </div>

                  <div>
                    <span>Risk authority</span>
                    <strong>
                      ${riskAvailable?"Available":"Missing"}
                    </strong>
                  </div>

                </div>
              </section>

              <section>
                <h5>Authority gaps</h5>

                <div class="mtg-native-missing-list">

                  ${
                    missing.length
                      ?missing.map(
                          reason=>`
                            <div>
                              <span>UNAVAILABLE</span>
                              <p>${escapeHtml(reason)}</p>
                            </div>`
                        ).join("")
                      :`
                        <div class="available">
                          <span>AVAILABLE</span>
                          <p>
                            All governed native fields tracked by this
                            availability gate are present.
                          </p>
                        </div>`
                  }

                </div>
              </section>

              <section>
                <h5>Authority lineage</h5>

                <div class="mtg-evidence-list">

                  <div>
                    <span>Native asset ID</span>
                    <strong>
                      ${escapeHtml(p.native_asset_id||"Missing")}
                    </strong>
                  </div>

                  <div>
                    <span>Authority pointer</span>
                    <strong class="mtg-source-authority">
                      ${escapeHtml(p.native_authority_pointer||"Missing")}
                    </strong>
                  </div>

                  <div>
                    <span>Generic detail read</span>
                    <strong>
                      ${detailError
                        ?"REQUEST FAILED"
                        :"COMPLETE"}
                    </strong>
                  </div>

                </div>

                ${
                  detailError
                    ?`
                      <div class="mtg-native-detail-error">
                        Generic presentation detail could not be loaded:
                        ${escapeHtml(detailError)}
                      </div>`
                    :""
                }

              </section>

              <section class="mtg-native-methodology-governance">

                <h5>Governance boundary</h5>

                <p>
                  ${
                    lane==="collector"
                      ?"Collector authority remains native."
                      :"Pre-Collector authority remains native."
                  }
                </p>

                <p>
                  Missing authority remains missing.
                </p>

                <p>
                  Secret Lair premium fields are not synthesized for this lane.
                  Secret Lair premium fields and Q10 purchase policy do not apply to this lane.
                </p>

                <p>
                  No universal MTG rank or cross-domain rank is created.
                </p>

                <p>
                  Recommendation does not authorize execution.
                </p>

              </section>

            </div>

          </details>

        </aside>

      </section>

    </div>`;

  const back=
    page.querySelector(
      "#mtg-native-back"
    );

  if(back){
    back.addEventListener(
      "click",
      ()=>{
        mtgLane=lane;
        renderDomain();
      }
    );
  }
}
async function renderMtgDomain(page,all,filtered,statusOptions,start,maxPage){
  ensureMtgPremiumVisualStyles();

  const laneTotals={
    secret_lair:mtgLaneCount(all,"secret_lair"),
    collector:mtgLaneCount(all,"collector"),
    pre_collector:mtgLaneCount(all,"pre_collector")
  };

  let laneFiltered=
    filtered.filter(
      item=>mtgLaneForItem(item)===mtgLane
    );

  if(mtgLane==="secret_lair"){
    laneFiltered=
      mtgInvestmentSort(laneFiltered);
  }

  if(
    mtgLane==="collector"||
    mtgLane==="pre_collector"
  ){
    laneFiltered=
      mtgNativeInvestmentSort(
        laneFiltered
      );
  }

  const laneMaxPage=
    Math.max(
      0,
      Math.ceil(
        laneFiltered.length/REC_PAGE_SIZE
      )-1
    );

  if(pageIndex>laneMaxPage){
    pageIndex=laneMaxPage;
  }

  const laneStart=
    pageIndex*REC_PAGE_SIZE;

  const visible=
    laneFiltered.slice(
      laneStart,
      laneStart+REC_PAGE_SIZE
    );

  if(mtgLane==="secret_lair"){
    await hydrateMtgPremiumResearch(
      visible
    );
  }

  if(
    mtgLane==="collector"||
    mtgLane==="pre_collector"
  ){
    await mtgHydrateNativeResearch(
      visible
    );
  }

  if(selectedDomain!=="mtg"){
    return;
  }

  const buyCount=
    laneFiltered.filter(
      mtgIsBuyCandidate
    ).length;

  const waitCount=
    laneFiltered.filter(
      mtgIsWaitCandidate
    ).length;

  const premiumVisible=
    visible.filter(
      item=>mtgPremiumPayload(item)
    );

  const visibleReturns=
    premiumVisible
      .map(
        item=>Number(
          mtgPremiumPayload(item)?.certified_1y_point_return
        )
      )
      .filter(
        Number.isFinite
      )
      .sort(
        (a,b)=>a-b
      );

  const medianVisibleReturn=
    visibleReturns.length
      ?visibleReturns[
          Math.floor(
            visibleReturns.length/2
          )
        ]
      :null;

  const laneTabs=`
    <div class="mtg-lane-tabs" role="tablist">
      <button
        type="button"
        data-mtg-lane="secret_lair"
        class="mtg-lane-tab ${mtgLane==="secret_lair"?"active":""}"
      >
        <span>Secret Lair</span>
        <strong>${laneTotals.secret_lair}</strong>
      </button>

      <button
        type="button"
        data-mtg-lane="collector"
        class="mtg-lane-tab ${mtgLane==="collector"?"active":""}"
      >
        <span>Collector Boosters</span>
        <strong>${laneTotals.collector}</strong>
      </button>

      <button
        type="button"
        data-mtg-lane="pre_collector"
        class="mtg-lane-tab ${mtgLane==="pre_collector"?"active":""}"
      >
        <span>Pre-Collector</span>
        <strong>${laneTotals.pre_collector}</strong>
      </button>
    </div>`;

  let hero="";

  if(mtgLane==="secret_lair"){
    hero=`
      <article class="rec-strategic-hero mtg-research-hero">
        <div>
          <span class="eyebrow">SECRET LAIR PREMIUM RESEARCH</span>
          <h3>
            Buy quality products at
            <span class="return">disciplined entry prices.</span>
          </h3>

          <p class="rec-strategic-copy">
            Current market price and the governed Q10 entry threshold lead the decision.
            The one-year outlook is certified. Three- and five-year outputs are scenario
            distributions, not direct certified forecasts.
          </p>

          <div class="rec-chips">
            <span class="rec-chip">Q10 purchase gate</span>
            <span class="rec-chip">Certified 1Y forecast</span>
            <span class="rec-chip">3Y / 5Y scenarios</span>
            <span class="rec-chip">Manual execution only</span>
          </div>
        </div>

        <div class="mtg-hero-kpis">
          <article>
            <span>BUY candidates</span>
            <strong>${buyCount}</strong>
            <small>Current price satisfies native/Q10 conditions</small>
          </article>

          <article>
            <span>WAIT for Q10</span>
            <strong>${waitCount}</strong>
            <small>Research-worthy, entry not yet satisfied</small>
          </article>

          <article>
            <span>Visible 1Y median</span>
            <strong>${medianVisibleReturn==null?"?":escapeHtml(fmtPercent(medianVisibleReturn))}</strong>
            <small>Certified 1Y outlook for loaded cards</small>
          </article>

          <article>
            <span>Premium universe</span>
            <strong>${laneTotals.secret_lair}</strong>
            <small>Certified Secret Lair research records</small>
          </article>
        </div>
      </article>`;
  }

  if(mtgLane==="collector"){
    hero=`
      <article class="mtg-native-lane-hero">
        <div>
          <span class="eyebrow">COLLECTOR BOOSTERS</span>
          <h3>Collector sealed-product research</h3>
          <p>
            Native Collector authority is shown independently from Secret Lair premium research.
            The certified Collector core remains available; the separate ranking identity bridge
            remains fail-closed where required.
          </p>
        </div>
        <div class="mtg-native-lane-count">
          <strong>${laneTotals.collector}</strong>
          <span>Collector records</span>
        </div>
      </article>`;
  }

  if(mtgLane==="pre_collector"){
    hero=`
      <article class="mtg-native-lane-hero">
        <div>
          <span class="eyebrow">PRE-COLLECTOR SEALED</span>
          <h3>Historical sealed-product research</h3>
          <p>
            Pre-Collector products remain visible through their native authority.
            The certification bridge remains fail-closed; no Secret Lair premium fields are synthesized.
          </p>
        </div>
        <div class="mtg-native-lane-count">
          <strong>${laneTotals.pre_collector}</strong>
          <span>Pre-Collector records</span>
        </div>
      </article>`;
  }

  page.innerHTML=`
    ${recommendationDomainSummaryAnchor()}

    <div class="rec-shell mtg-research-shell">

      <div class="rec-section-head">
        <div>
          <span class="eyebrow">MTG INVESTMENT RESEARCH</span>
          <h3>
            ${escapeHtml(mtgLaneLabel(mtgLane))}
            <span class="rec-count-chip">
              ${laneFiltered.length} matching
            </span>
          </h3>
        </div>

        <div class="rec-section-head-actions">
          <button
            type="button"
            id="rec-all-domains"
            class="secondary"
          >
            All domains
          </button>
        </div>
      </div>

      ${laneTabs}

      ${hero}

      <div class="rec-toolbar mtg-research-toolbar">
        <input
          id="rec-search"
          value="${escapeHtml(searchText)}"
          placeholder="Search ${escapeHtml(mtgLaneLabel(mtgLane))} products..."
        >

        <select id="rec-status">
          ${statusOptions}
        </select>
      </div>

      <div class="mtg-compact-governance">
        <strong>MTG-native research.</strong>
        Native rank remains lane-specific.
        Q10 governs Secret Lair purchase eligibility.
        3Y/5Y values are scenarios.
        Recommendation does not authorize execution.
      </div>

      <div class="rec-asset-grid mtg-research-grid">
        ${visible.map(
          item=>
            mtgLane==="secret_lair"
              ?mtgPremiumCard(item)
              :mtgNativeCard(item)
        ).join("")}
      </div>

      <div class="mtg-pagination">
        <span class="page-note">
          Rows ${laneFiltered.length?laneStart+1:0}-${Math.min(
            laneStart+REC_PAGE_SIZE,
            laneFiltered.length
          )} of ${laneFiltered.length}
        </span>

        <div>
          <button
            type="button"
            id="rec-prev"
            class="secondary"
            ${pageIndex===0?"disabled":""}
          >
            Previous
          </button>

          <button
            type="button"
            id="rec-next"
            class="secondary"
            ${pageIndex>=laneMaxPage?"disabled":""}
          >
            Next
          </button>
        </div>
      </div>
    </div>`;

  bindDomainControls(
    page,
    laneMaxPage
  );

  bindMtgLaneTabs(page);

  if(mtgLane==="secret_lair"){
    bindMtgPremiumButtons(
      page,
      visible
    );
  }

  if(
    mtgLane==="collector"||
    mtgLane==="pre_collector"
  ){
    bindMtgNativeButtons(
      page,
      visible
    );
  }
}


function bindMtgPremiumButtons(page,items){
  const byAssetId=
    new Map(
      (items||[]).map(
        item=>[
          String(item.asset_id),
          item
        ]
      )
    );

  page.querySelectorAll(
    ".rec-mtg-premium-detail"
  ).forEach(
    button=>{
      button.addEventListener(
        "click",
        async event=>{
          event.preventDefault();
          event.stopPropagation();

          const assetId=
            String(
              button.dataset.assetId||
              ""
            );

          const item=
            byAssetId.get(assetId);

          if(!item){
            console.error(
              "Secret Lair research item not found for asset ID:",
              assetId
            );
            return;
          }

          await openMtgPremiumDetail(
            page,
            item
          );
        }
      );
    }
  );
}
function bindMtgNativeButtons(page,items){
  const byAssetId=
    new Map(
      (items||[]).map(
        item=>[
          String(item.asset_id),
          item
        ]
      )
    );

  page.querySelectorAll(
    ".rec-mtg-native-detail"
  ).forEach(
    button=>{
      button.addEventListener(
        "click",
        async event=>{
          event.preventDefault();
          event.stopPropagation();

          const assetId=
            String(
              button.dataset.assetId||
              ""
            );

          const item=
            byAssetId.get(assetId);

          if(!item){
            console.error(
              "Native MTG research item not found for asset ID:",
              assetId
            );
            return;
          }

          await openMtgNativeDetail(
            page,
            item
          );
        }
      );
    }
  );
}
async function openMtgPremiumDetail(page,item){
  ensureMtgPremiumVisualStyles();

  let detail=
    mtgPremiumDetail(item);

  if(!detail){
    page.innerHTML=`
      <div class="rec-shell">
        <div class="mtg-detail-loading">
          Loading certified Secret Lair research...
        </div>
      </div>`;

    detail=
      await readMtgPremiumResearch(item);
  }

  const premium=
    detail?.premium_research||null;

  const p=
    item.payload||{};

  if(!premium){
    page.innerHTML=`
      ${recommendationDomainSummaryAnchor()}

      <div class="rec-shell rec-detail">
        <div class="rec-detail-head">
          <div class="rec-detail-title">
            <span class="eyebrow">MTG RESEARCH</span>
            <h2>${escapeHtml(displayName(item))}</h2>
            <p>Premium research unavailable for this lane.</p>
          </div>

          <button
            type="button"
            id="mtg-premium-back"
            class="secondary"
          >
            Back to MTG research
          </button>
        </div>

        <article class="rec-side-panel">
          <h4>Native authority only</h4>
          <p>
            UIP does not synthesize Secret Lair premium authority
            for Collector or Pre-Collector records.
          </p>
        </article>
      </div>`;

    const back=
      page.querySelector(
        "#mtg-premium-back"
      );

    if(back){
      back.addEventListener(
        "click",
        ()=>renderDomain()
      );
    }

    return;
  }

  const rank=
    p.native_rank==null
      ?"Not ranked"
      :fmtNumber(
          p.native_rank,
          0
        );

  const status=
    cleanStatus(
      nativeStatus(item)
    );

  const distance=
    mtgDistanceToQ10(premium);

  const distanceLabel=
    distance==null
      ?"?"
      :distance>=0
        ?`${fmtMoney(distance)} below Q10`
        :`${fmtMoney(Math.abs(distance))} above Q10`;

  const governedQ10State=
    mtgGovernedQ10State(premium);

  const buy=
    mtgIsBuyCandidate(item);

  const q10Class=
    buy
      ?"buy"
      :"wait";

  page.innerHTML=`
    ${recommendationDomainSummaryAnchor()}

    <div class="rec-shell rec-detail mtg-detail">

      <div class="rec-detail-head">
        <div class="rec-detail-title">
          <span class="eyebrow">MTG &middot; SECRET LAIR RESEARCH</span>
          <h2>${escapeHtml(premium.product_name||displayName(item))}</h2>
          <p>
            Native rank ${escapeHtml(rank)}
            &middot; ${escapeHtml(status)}
          </p>
        </div>

        <button
          type="button"
          id="mtg-premium-back"
          class="secondary"
        >
          Back to Secret Lair
        </button>
      </div>

      <article class="rec-strategic-hero mtg-detail-strategic-hero">
        <div>
          <div class="mtg-detail-status-row">
            <span class="rec-status mtg-decision ${q10Class}">
              ${escapeHtml(status)}
            </span>

            <span class="rec-chip">
              ${escapeHtml(mtgEvidenceLabel(premium))} evidence
            </span>
          </div>

          <h3>
            Current market
            <span class="return">
              ${escapeHtml(distanceLabel)}
            </span>
          </h3>

          <p class="rec-strategic-copy">
            The governed one-year Q10 threshold determines entry eligibility.
            Native MTG rank adds lane context but cannot override the governed Q10 purchase policy.
          </p>

          <div class="rec-chips">
            <span class="rec-chip">Q10 purchase gate</span>
            <span class="rec-chip">Certified 1Y</span>
            <span class="rec-chip">3Y scenario</span>
            <span class="rec-chip">5Y scenario</span>
          </div>
        </div>

        <div class="mtg-price-decision">
          <div class="mtg-price-pair">
            <article>
              <span>Current market</span>
              <strong>${escapeHtml(fmtMoney(premium.current_tcg_market_price_usd))}</strong>
            </article>

            <article>
              <span>Governed Q10 entry</span>
              <strong>${escapeHtml(fmtMoney(premium.y1_q10_break_even_entry_price_usd))}</strong>
            </article>
          </div>

          <div class="mtg-detail-entry-scale">
            <span class="track"></span>
            <span class="q10">
              <i></i>
              <small>Q10</small>
            </span>
            <span
              class="current ${q10Class}"
              style="left:${mtgEntryPercent(premium)}%"
            >
              <i></i>
              <small>Current</small>
            </span>
          </div>

          <div class="mtg-entry-caption">
            ${escapeHtml(governedQ10State)}
            &middot; ${escapeHtml(distanceLabel)}
          </div>
        </div>
      </article>

      <div class="rec-kpi-row mtg-detail-kpis">
        <article class="rec-kpi-card">
          <div class="rec-kpi-label">
            Certified 1Y forecast
          </div>
          <strong>${escapeHtml(fmtMoney(premium.certified_1y_point_forecast_usd))}</strong>
          <span>${escapeHtml(fmtPercent(premium.certified_1y_point_return))} total return</span>
        </article>

        <article class="rec-kpi-card">
          <div class="rec-kpi-label">
            1Y loss probability
          </div>
          <strong>${escapeHtml(fmtPercent(premium.y1_probability_of_loss))}</strong>
          <span>Modeled downside probability</span>
        </article>

        <article class="rec-kpi-card">
          <div class="rec-kpi-label">
            Positive-return probability
          </div>
          <strong>${escapeHtml(fmtPercent(premium.y1_probability_of_positive_return))}</strong>
          <span>One-year modeled probability</span>
        </article>

        <article class="rec-kpi-card">
          <div class="rec-kpi-label">
            Evidence support
          </div>
          <strong>${escapeHtml(mtgEvidenceLabel(premium))}</strong>
          <span>${escapeHtml(fmtNumber(premium.historical_observation_count,0))} historical observations</span>
        </article>
      </div>

      <div class="rec-detail-grid">

        <div class="mtg-detail-main">

          <article class="rec-forecast-panel">
            <div class="rec-panel-head">
              <h4>Certified 1Y distribution</h4>
              <p>
                Direct certified one-year forecast distribution.
              </p>
            </div>

            <div class="mtg-distribution-cards">
              <article class="bear">
                <span>Q10 downside</span>
                <strong>${escapeHtml(fmtMoney(premium.y1_q10_terminal_value_usd))}</strong>
              </article>

              <article class="base">
                <span>Q50 median</span>
                <strong>${escapeHtml(fmtMoney(premium.y1_q50_terminal_value_usd))}</strong>
              </article>

              <article class="bull">
                <span>Q90 upside</span>
                <strong>${escapeHtml(fmtMoney(premium.y1_q90_terminal_value_usd))}</strong>
              </article>
            </div>

            <div class="mtg-distribution-line">
              <span class="bear"></span>
              <span class="base"></span>
              <span class="bull"></span>
            </div>
          </article>

          <article class="rec-forecast-panel">
            <div class="rec-panel-head">
              <h4>3Y scenario</h4>
              <p>
                Scenario distribution only &middot; not a direct certified forecast
                and not a purchase trigger.
              </p>
            </div>

            <div class="mtg-scenario-kpis">
              <article>
                <span>Q10 terminal</span>
                <strong>${escapeHtml(fmtMoney(premium.y3_q10_terminal_value_scenario_usd))}</strong>
              </article>

              <article>
                <span>Q50 terminal</span>
                <strong>${escapeHtml(fmtMoney(premium.y3_q50_terminal_value_scenario_usd))}</strong>
              </article>

              <article>
                <span>Q90 terminal</span>
                <strong>${escapeHtml(fmtMoney(premium.y3_q90_terminal_value_scenario_usd))}</strong>
              </article>

              <article>
                <span>Median return</span>
                <strong>${escapeHtml(fmtPercent(premium.y3_median_total_return_scenario))}</strong>
              </article>

              <article>
                <span>Loss probability</span>
                <strong>${escapeHtml(fmtPercent(premium.y3_probability_of_loss_scenario))}</strong>
              </article>
            </div>
          </article>

          <article class="rec-forecast-panel">
            <div class="rec-panel-head">
              <h4>5Y scenario</h4>
              <p>
                Longer-horizon scenario distribution only.
              </p>
            </div>

            <div class="mtg-scenario-kpis">
              <article>
                <span>Q10 terminal</span>
                <strong>${escapeHtml(fmtMoney(premium.y5_q10_terminal_value_scenario_usd))}</strong>
              </article>

              <article>
                <span>Q50 terminal</span>
                <strong>${escapeHtml(fmtMoney(premium.y5_q50_terminal_value_scenario_usd))}</strong>
              </article>

              <article>
                <span>Q90 terminal</span>
                <strong>${escapeHtml(fmtMoney(premium.y5_q90_terminal_value_scenario_usd))}</strong>
              </article>

              <article>
                <span>Median return</span>
                <strong>${escapeHtml(fmtPercent(premium.y5_median_total_return_scenario))}</strong>
              </article>

              <article>
                <span>Loss probability</span>
                <strong>${escapeHtml(fmtPercent(premium.y5_probability_of_loss_scenario))}</strong>
              </article>
            </div>
          </article>
        </div>

        <aside class="mtg-detail-side">

          <article class="rec-side-panel">
            <div class="rec-panel-head">
              <h4>Evidence strength</h4>
              <p>
                Historical depth and comparable support.
              </p>
            </div>

            <div class="mtg-evidence-list">
              <div>
                <span>Own-history class</span>
                <strong>${escapeHtml(cleanStatus(premium.own_history_evidence_class))}</strong>
              </div>

              <div>
                <span>History span</span>
                <strong>${escapeHtml(fmtNumber(premium.history_span_days,0))} days</strong>
              </div>

              <div>
                <span>Observations</span>
                <strong>${escapeHtml(fmtNumber(premium.historical_observation_count,0))}</strong>
              </div>

              <div>
                <span>Exact comparable products</span>
                <strong>${escapeHtml(fmtNumber(premium.exact_structural_comparable_product_count,0))}</strong>
              </div>

              <div>
                <span>Global comparable products</span>
                <strong>${escapeHtml(fmtNumber(premium.global_comparable_product_count,0))}</strong>
              </div>

              <div>
                <span>Exact comparable events</span>
                <strong>${escapeHtml(fmtNumber(premium.exact_structural_comparable_event_count,0))}</strong>
              </div>

              <div>
                <span>Source authority</span>
                <strong class="mtg-source-authority">${escapeHtml(premium.source_authority_path||"?")}</strong>
              </div>
            </div>
          </article>

          <article class="rec-side-panel mtg-governance-panel">
            <div class="rec-panel-head">
              <h4>Method & governance</h4>
            </div>

            <p>
              Q10 is the governed Secret Lair purchase threshold.
              Q25 and Q50 are diagnostic context only.
            </p>

            <p>
              3Y and 5Y are scenarios only. They remain scenario distributions, not direct certified forecasts.
            </p>

            <p>
              MTG native rank is used only inside MTG.
              No universal MTG rank or cross-domain rank is created.
            </p>

            <p>
              Recommendation does not authorize execution.
            </p>
          </article>
        </aside>
      </div>
    </div>`;

  const back=
    page.querySelector(
      "#mtg-premium-back"
    );

  if(back){
    back.addEventListener(
      "click",
      ()=>{
        mtgLane="secret_lair";
        renderDomain();
      }
    );
  }
}



function filteredDomainItems(){let items=[...(catalog[selectedDomain]||[])];if(selectedDomain==="mtg"){items.sort((a,b)=>{const ar=Number(a.payload?.native_rank);const br=Number(b.payload?.native_rank);const aRank=Number.isFinite(ar);const bRank=Number.isFinite(br);if(aRank&&bRank&&ar!==br)return ar-br;if(aRank!==bRank)return aRank?-1:1;return String(a.record_key||"").localeCompare(String(b.record_key||""))})}if(selectedStatus!=="all")items=items.filter(item=>((selectedDomain==="mtg"?nativeStatus(item):displayStatus(item))||"MISSING")===selectedStatus);if(searchText)items=items.filter(item=>searchKey(item).includes(searchText));return items}
function genericRows(items){return items.map(item=>{const p=item.payload||{};const horizon=p.time_horizon_months==null?"—":`${fmtNumber(p.time_horizon_months,0)} mo`;return `<tr><td><span class="position-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_symbol||item.asset_id||"")}</small></span></td><td>${escapeHtml(cleanStatus(displayStatus(item)))}</td><td>${escapeHtml(fmtNumber(p.normalized_score))}</td><td>${escapeHtml(fmtNumber(p.confidence_score))}</td><td>${escapeHtml(horizon)}</td><td style="text-align:left;max-width:320px">${escapeHtml(p.rationale??"—")}</td><td style="text-align:left;max-width:260px">${escapeHtml(p.risk_summary??"—")}</td><td><button type="button" class="secondary rec-metals-detail" data-asset-id="${escapeHtml(item.asset_id)}">Research ↗</button></td></tr>`}).join("")}
function metalsRows(items){return items.map(item=>{const p=item.payload||{};return `<tr><td><span class="position-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_symbol||item.asset_id||"")}</small></span></td><td>${escapeHtml(cleanStatus(displayStatus(item)))}</td><td>${escapeHtml(cleanStatus(nativeStatus(item)))}</td><td>${escapeHtml(fmtNumber(p.normalized_score??p.domain_score))}</td><td>${escapeHtml(fmtNumber(p.confidence_score??p.confidence))}</td><td><button type="button" class="secondary rec-metals-detail" data-asset-id="${escapeHtml(item.asset_id)}">Research ↗</button></td></tr>`}).join("")}
function mtgRows(items){return items.map(item=>{const p=item.payload||{};const rank=p.native_rank==null?"—":`${fmtNumber(p.native_rank,0)}${p.native_rank_type?` · ${p.native_rank_type}`:""}`;return `<tr><td><span class="position-name"><strong>${escapeHtml(displayName(item))}</strong><small>${escapeHtml(item.asset_subclass||item.asset_id||"")}</small></span></td><td>${escapeHtml(cleanStatus(displayStatus(item)))}</td><td>${escapeHtml(rank)}</td><td>${escapeHtml(p.evidence_state??"—")}</td><td>${escapeHtml(p.actionability_state??"—")}</td><td>${p.manual_execution_price_check_required===true?"Required":p.manual_execution_price_check_required===false?"No":"—"}</td><td>${p.execution_ready_purchase_certified===true?"Yes":p.execution_ready_purchase_certified===false?"No":"—"}</td><td>${p.automatic_purchase_execution===true?"Yes":p.automatic_purchase_execution===false?"No":"—"}</td></tr>`}).join("")}
function bindDomainControls(page,maxPage){node("rec-all-domains")?.addEventListener("click",()=>{selectedDomain="all";selectedStatus="all";searchText="";pageIndex=0;renderAll()});node("rec-search")?.addEventListener("input",event=>{searchText=event.target.value.trim().toLowerCase();pageIndex=0;renderDomain()});node("rec-status")?.addEventListener("change",event=>{selectedStatus=event.target.value;pageIndex=0;renderDomain()});node("rec-prev")?.addEventListener("click",()=>{if(pageIndex>0){pageIndex-=1;renderDomain()}});node("rec-next")?.addEventListener("click",()=>{if(pageIndex<maxPage){pageIndex+=1;renderDomain()}});page.querySelectorAll(".rec-crypto-detail").forEach(button=>button.addEventListener("click",()=>openCryptoDetail(button.dataset.assetId)));page.querySelectorAll(".rec-metals-detail").forEach(button=>button.addEventListener("click",()=>openMetalsDetail(button.dataset.assetId)))}
function renderCryptoDomain(page,all,filtered,statusOptions){page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-shell"><div class="rec-section-head"><div><span class="eyebrow">RECOMMENDATIONS</span><h3>Crypto research <span class="rec-count-chip">${filtered.length} matching · ${all.length} total</span></h3></div><button type="button" id="rec-all-domains" class="secondary">All domains</button></div><p class="governance-note">Crypto is presented 3-year first. Rows are not a UIP-created rank; shorter horizons are entry context only. Recommendation does not authorize execution.</p><div class="rec-toolbar"><input id="rec-search" value="${escapeHtml(searchText)}" placeholder="Search asset, symbol, or status..."><select id="rec-status" aria-label="${escapeHtml(statusFilterLabel(selectedDomain))}">${statusOptions}</select><button type="button" class="secondary" disabled>36-month strategic outlook</button></div><div class="rec-crypto-layout"><div class="rec-asset-grid">${filtered.map(cryptoCard).join("")}</div>${renderExplainer()}</div></div>`;bindDomainControls(page,0)}
function renderMetalsDomain(page,all,filtered,statusOptions,start,maxPage){ensureMetalsVisualStyles();const featured=filtered.filter(item=>!isBil(item));const visibleTable=filtered.slice(start,start+REC_PAGE_SIZE);const table=`<table style="min-width:980px"><thead><tr><th>Asset</th><th>Final decision</th><th>Native recommendation</th><th>Domain score</th><th>Confidence</th><th>Detail</th></tr></thead><tbody>${metalsRows(visibleTable)}</tbody></table>`;page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-shell"><div class="rec-section-head"><div><span class="eyebrow">METALS RESEARCH</span><h3>Long-term thesis + tactical opportunity <span class="rec-count-chip">${featured.length} featured · ${all.length} total</span></h3></div><button type="button" id="rec-all-domains" class="secondary">All domains</button></div><p class="governance-note">Metals is long-term thesis first, tactical context second. Featured cards exclude BIL. Tactical states do not authorize execution.</p><div class="rec-toolbar"><input id="rec-search" value="${escapeHtml(searchText)}" placeholder="Search metal, vehicle, or status..."><select id="rec-status" aria-label="${escapeHtml(statusFilterLabel(selectedDomain))}">${statusOptions}</select><button type="button" class="secondary" disabled>Long-term + tactical</button></div><div class="metals-layout"><div class="metals-card-grid">${featured.map(metalsCard).join("")}</div>${renderMetalsExplainer()}</div><details class="metals-secondary-table" open><summary>All Metals research · secondary evidence table</summary><div class="table-wrap">${table}</div><div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:14px"><span class="page-note">Rows ${filtered.length?start+1:0}-${Math.min(start+REC_PAGE_SIZE,filtered.length)} of ${filtered.length}</span><div style="display:flex;gap:8px"><button type="button" id="rec-prev" class="secondary" ${pageIndex===0?"disabled":""}>Previous</button><button type="button" id="rec-next" class="secondary" ${pageIndex>=maxPage?"disabled":""}>Next</button></div></div></details></div>`;bindDomainControls(page,maxPage)}
function renderDomain(){const page=node("recommendations");const all=catalog[selectedDomain]||[];const statuses=[...new Set(all.map(item=>(selectedDomain==="mtg"?nativeStatus(item):displayStatus(item))||"MISSING"))].sort();const filtered=filteredDomainItems();const maxPage=Math.max(0,Math.ceil(filtered.length/REC_PAGE_SIZE)-1);if(pageIndex>maxPage)pageIndex=maxPage;const start=pageIndex*REC_PAGE_SIZE;const visible=filtered.slice(start,start+REC_PAGE_SIZE);const statusLabel=statusFilterAllLabel(selectedDomain);const statusOptions=[`<option value="all">${statusLabel}</option>`,...statuses.map(status=>`<option value="${escapeHtml(status)}"${selectedStatus===status?" selected":""}>${escapeHtml(cleanStatus(status))}</option>`)].join("");if(selectedDomain==="crypto"){renderCryptoDomain(page,all,filtered,statusOptions);return}if(selectedDomain==="metals"){renderMetalsDomain(page,all,filtered,statusOptions,start,maxPage);return}if(selectedDomain==="mtg"){renderMtgDomain(page,all,filtered,statusOptions,start,maxPage);return}let orderNote="Catalog order is presentation order; UIP does not manufacture a rank for this domain.";let utilityNote="Certified recommendation, rationale, and risk evidence.";let table=`<table style="min-width:1380px"><thead><tr><th>Asset</th><th>Native recommendation</th><th>Domain score</th><th>Confidence</th><th>Horizon</th><th>Rationale</th><th>Risk</th><th>Detail</th></tr></thead><tbody>${genericRows(visible)}</tbody></table>`;if(selectedDomain==="mtg"){table=`<table style="min-width:1450px"><thead><tr><th>Asset</th><th>Native status</th><th>Native rank</th><th>Evidence</th><th>Actionability</th><th>Manual price check</th><th>Execution ready</th><th>Automatic execution</th></tr></thead><tbody>${mtgRows(visible)}</tbody></table>`;orderNote="MTG native rank is used only inside MTG where provided. Unranked native records remain visible.";utilityNote="Native MTG authority remains unchanged; richer price and forecast presentation follows in the MTG utility pass."}page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-shell"><div class="rec-section-head"><div><span class="eyebrow">RECOMMENDATIONS</span><h3>${escapeHtml(selectedDomain.toUpperCase())} research</h3></div><button type="button" id="rec-all-domains" class="secondary">All domains</button></div><article class="rec-domain-table panel"><div class="section-title"><div><h3>${escapeHtml(utilityNote)}</h3><span>${escapeHtml(filtered.length)} matching · ${escapeHtml(all.length)} total</span></div></div><p class="governance-note">${escapeHtml(orderNote)} Recommendation does not authorize execution.</p><div class="transaction-form" style="grid-template-columns:1fr 1fr;margin:16px 0"><label>Search<input id="rec-search" value="${escapeHtml(searchText)}" placeholder="Asset, ID, lane, status..."></label><label>Native status<select id="rec-status" aria-label="${escapeHtml(statusFilterLabel(selectedDomain))}">${statusOptions}</select></label></div><div class="table-wrap">${table}</div><div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:14px"><span class="page-note">Rows ${filtered.length?start+1:0}-${Math.min(start+REC_PAGE_SIZE,filtered.length)} of ${filtered.length}</span><div style="display:flex;gap:8px"><button type="button" id="rec-prev" class="secondary" ${pageIndex===0?"disabled":""}>Previous</button><button type="button" id="rec-next" class="secondary" ${pageIndex>=maxPage?"disabled":""}>Next</button></div></div></article></div>`;bindDomainControls(page,maxPage)}

function forecastRows(detail){const rows=allForecasts(detail);return rows.map(f=>`<tr class="${Number(f.forecast_horizon_months)===36&&f.forecast_method==="LONG_RANGE_SCENARIO_MODEL"?"strategic":""}"><td>${escapeHtml(`${fmtNumber(f.forecast_horizon_months,0)} mo`)}</td><td style="text-align:left">${escapeHtml(f.forecast_method??"—")}</td><td>${escapeHtml(fmtMoney(f.point_forecast))}</td><td>${escapeHtml(fmtPercent(f.expected_return))}</td><td>${escapeHtml(fmtPriceBound(f.lower_bound))}</td><td>${escapeHtml(fmtMoney(f.upper_bound))}</td><td>${escapeHtml(fmtNumber(f.confidence_score,3))}</td></tr>`).join("")}
function riskMetrics(detail){const risk=firstPayload(detail,"risk")||{};const candidates=[["Risk level",risk.risk_level],["Risk score",risk.risk_score],["Volatility",risk.volatility],["Downside",risk.downside_risk],["Max drawdown",risk.max_drawdown],["VaR",risk.var],["Expected shortfall",risk.expected_shortfall],["Beta",risk.beta],["Liquidity",risk.liquidity],["Concentration",risk.concentration]];const rows=candidates.filter(([,value])=>value!==null&&value!==undefined&&value!=="");if(!rows.length)return `<p class="governance-note">No separately populated risk metrics are available in this presentation record.</p>`;return rows.map(([label,value])=>`<div class="history-row"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(typeof value==="number"?fmtNumber(value,3):value)}</span></div>`).join("")}
function chartPoints(rows,key,width,height,pad=16){const valid=rows.filter(r=>Number.isFinite(Number(r[key])));if(valid.length<2)return "";const xs=valid.map(r=>Number(r.forecast_horizon_months));const ys=valid.map(r=>Number(r[key]));const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),xSpan=maxX-minX||1,ySpan=maxY-minY||1;return valid.map(r=>{const x=pad+((Number(r.forecast_horizon_months)-minX)/xSpan)*(width-pad*2);const y=height-pad-((Number(r[key])-minY)/ySpan)*(height-pad*2);return `${x.toFixed(1)},${y.toFixed(1)}`}).join(" ")}
function forecastChart(detail){const rows=longRangeForecasts(detail).filter(f=>Number(f.forecast_horizon_months)<=36);if(rows.length<2)return `<div class="empty">No multi-horizon long-range series is available.</div>`;const width=270,height=190;const horizons=[...new Set(rows.map(r=>Number(r.forecast_horizon_months)))];const lines=[40,85,130,175].map(y=>`<line class="grid-line" x1="16" y1="${y}" x2="254" y2="${y}"></line>`).join("");const labels=horizons.filter((_,i)=>i===0||i===horizons.length-1||i%2===0).map(h=>{const x=16+((h-Math.min(...horizons))/(Math.max(...horizons)-Math.min(...horizons)||1))*238;return `<text x="${x}" y="187" text-anchor="middle">${h}m</text>`}).join("");return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Long-range forecast path through 36 months">${lines}<polyline class="bear-line" points="${chartPoints(rows,"lower_bound",width,height)}"></polyline><polyline class="base-line" points="${chartPoints(rows,"point_forecast",width,height)}"></polyline><polyline class="bull-line" points="${chartPoints(rows,"upper_bound",width,height)}"></polyline>${labels}</svg>`}
function horizonTabs(detail){const available=new Set(allForecasts(detail).map(f=>Number(f.forecast_horizon_months)));return [1,3,6,12,24,36].map(h=>`<div class="rec-horizon-tab ${h===36?"strategic":""}"><strong>${h}m</strong><span>${h===36?"Strategic objective":available.has(h)?h>=24?"Mid-term view":"Entry context":"Not populated"}</span></div>`).join("")}

function openCryptoDetail(assetId){const item=(catalog?.crypto||[]).find(candidate=>candidate.asset_id===assetId);if(!item)return;const detail=detailCache.get(detailKey(item));if(!detail){renderBlocked("Certified Crypto detail is not available in the local presentation cache.");return}const page=node("recommendations");const f36=crypto36(detail)||{};const recommendation=item.payload||{};const risk=firstPayload(detail,"risk")||{};const score=riskScore(detail);const level=riskLevel(detail,item);const angle=score===null?-145:-175+Math.max(0,Math.min(100,score))*1.7;page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-detail"><div class="rec-detail-head"><div class="rec-detail-title"><span class="eyebrow">CRYPTO RESEARCH</span><h2>${escapeHtml(displayName(item))}</h2><p>${escapeHtml(item.asset_symbol||item.asset_id||"")} · domain-native research · certified authority</p></div><button type="button" id="rec-back-crypto" class="secondary">← Back to Crypto</button></div><section class="rec-strategic-hero"><div><span class="eyebrow">3-YEAR GROWTH OUTLOOK</span><h3><span class="return">${escapeHtml(fmtPercent(f36.expected_return))}</span> expected return over the 36-month scenario horizon</h3><p class="rec-strategic-copy">Bear ${escapeHtml(fmtPriceBound(f36.lower_bound))} · Base ${escapeHtml(fmtMoney(f36.point_forecast))} · Bull ${escapeHtml(fmtMoney(f36.upper_bound))}. LONG_RANGE_SCENARIO_MODEL record. UIP does not extrapolate a shorter forecast into three years.</p><div class="rec-chips"><span class="rec-chip">Scenario ${escapeHtml(f36.scenario??"—")}</span><span class="rec-chip">Confidence raw ${escapeHtml(fmtNumber(f36.confidence_score,3))}</span><span class="rec-chip">Origin ${escapeHtml(f36.forecast_origin_date??f36.origin_date??"—")}</span></div></div><div class="rec-range-chart"><div class="rec-range-head"><div><strong>Bear</strong><span>${escapeHtml(fmtPriceBound(f36.lower_bound))}</span></div><div><strong>Base</strong><span>${escapeHtml(fmtMoney(f36.point_forecast))}</span></div><div><strong>Bull</strong><span>${escapeHtml(fmtMoney(f36.upper_bound))}</span></div></div><div class="rec-range-scale"><div class="rec-range-band"></div><i class="rec-range-marker bear"></i><i class="rec-range-marker base" style="left:${rangePosition(f36)}%"></i><i class="rec-range-marker bull"></i><div class="rec-range-axis"><span>Bear</span><span>36-month horizon price (USD)</span><span>Bull</span></div></div></div></section><section class="rec-kpi-row"><article class="rec-kpi-card bear"><div class="rec-kpi-label"><span class="rec-kpi-dot">●</span>Bear case</div><strong>${escapeHtml(fmtPriceBound(f36.lower_bound))}</strong><small class="page-note">36-month bear forecast</small></article><article class="rec-kpi-card base"><div class="rec-kpi-label"><span class="rec-kpi-dot">●</span>Base case</div><strong>${escapeHtml(fmtMoney(f36.point_forecast))}</strong><small class="page-note">36-month base forecast</small></article><article class="rec-kpi-card"><div class="rec-kpi-label"><span class="rec-kpi-dot">●</span>Bull case</div><strong>${escapeHtml(fmtMoney(f36.upper_bound))}</strong><small class="page-note">36-month bull forecast</small></article><article class="rec-kpi-card"><div class="rec-kpi-label"><span class="rec-kpi-dot">↗</span>Expected return (36m)</div><strong class="${Number(f36.expected_return)>0?"positive":"negative"}">${escapeHtml(fmtPercent(f36.expected_return))}</strong><small class="page-note">Nominal return expectation</small></article></section><section class="rec-detail-grid"><div class="rec-forecast-panel"><div class="rec-panel-head"><h4>Forecast path & entry context</h4><p>Short horizons inform accumulation timing; the 36-month horizon remains the strategic objective.</p></div><div class="rec-horizon-tabs">${horizonTabs(detail)}</div><div class="rec-forecast-viz"><div class="rec-line-chart"><div style="display:flex;gap:12px;font-size:8px;color:var(--muted);margin-bottom:8px"><span style="color:var(--warn)">● Base</span><span style="color:var(--accent)">● Bull</span><span style="color:var(--bad)">● Bear</span></div>${forecastChart(detail)}</div><div class="rec-detail-table"><table><thead><tr><th>Horizon</th><th>Method</th><th>Point forecast</th><th>Expected return</th><th>Bear</th><th>Bull</th><th>Confidence raw</th></tr></thead><tbody>${forecastRows(detail)}</tbody></table></div></div><p class="governance-note">Shorter horizons are entry context only and not a UIP-created rank.</p></div><div class="rec-side-stack"><aside class="rec-side-panel"><h4>Why this recommendation</h4><div class="rec-narrative"><div><span>Rationale</span><p>${escapeHtml(recommendation.rationale??"No rationale is populated.")}</p></div><div><span>Risk summary</span><p>${escapeHtml(recommendation.risk_summary??"No narrative risk summary is populated.")}</p></div><div><span>Native recommendation</span><p>${escapeHtml(cleanStatus(displayStatus(item)))}</p></div></div></aside><aside class="rec-side-panel"><h4>Risk assessment</h4><div class="rec-risk-gauge-wrap"><div class="rec-risk-gauge" style="--risk-angle:${angle}deg"></div><div class="rec-risk-readout"><span>Risk level</span><strong>${escapeHtml(level)}</strong><span>Risk score</span><strong>${escapeHtml(score===null?"—":fmtNumber(score,0))}</strong></div></div><div class="history" style="margin-top:12px">${riskMetrics(detail)}</div><p class="rec-risk-note">Confidence values are shown as raw source values, not percentages. Missing probability-positive values remain missing.</p></aside></div></section></div>`;node("rec-back-crypto").addEventListener("click",()=>{selectedDomain="crypto";selectedStatus="all";searchText="";pageIndex=0;renderDomain()})}

function momentumBar(label,value){const n=Number(value);const finite=Number.isFinite(n);const magnitude=finite?Math.min(50,Math.abs(n)):0;const width=magnitude*1.8;return `<div class="metals-bar-row"><span>${escapeHtml(label)}</span><div class="metals-bar-track">${finite?`<i class="metals-bar-fill ${n<0?"negative":""}" style="width:${width}%"></i>`:""}</div><strong class="${finite&&n<0?"negative":finite&&n>0?"positive":""}">${escapeHtml(fmtPctPoint(value))}</strong></div>`}
async function openMetalsDetail(assetId){ensureMetalsVisualStyles();const item=(catalog?.metals||[]).find(candidate=>candidate.asset_id===assetId);if(!item)return;let detail;try{detail=await readAssetDetail(item)}catch(error){renderBlocked(error.message);return}const renderTactical=window.UIPMetalsTactical?.renderTacticalPanel;const page=node("recommendations");const recommendation=item.payload||{};const technical=commodityTechnicalContext(detail,item.asset_id);const forecast=metalsForecast(detail);const score=metalsScore(item);const confidence=metalsConfidence(item);const level=riskLevel(detail,item);const tacticalPanel=typeof renderTactical==="function"?renderTactical(detail):`<aside class="metals-panel"><h4>Tactical context</h4><p class="governance-note">Certified tactical presentation is unavailable. The governed long-term final decision remains authoritative.</p></aside>`;const modelComponents=payloads(detail,"metals_model_component");const uncertainty=payloads(detail,"metals_uncertainty_adjusted");const modelNote=modelComponents.length?`${modelComponents.length} certified model component records available.`:"No separate model-component records are populated for this asset.";const uncertaintyNote=uncertainty.length?`${uncertainty.length} uncertainty-adjusted records available.`:"No separate uncertainty-adjusted records are populated for this asset.";page.innerHTML=`${recommendationDomainSummaryAnchor()}<div class="rec-detail"><div class="rec-detail-head"><div class="rec-detail-title"><span class="eyebrow">METALS RESEARCH</span><h2>${escapeHtml(displayName(item))}</h2><p>${escapeHtml(item.asset_symbol||item.asset_id||"")} · long-term thesis + bounded tactical context · certified authority</p></div><button type="button" id="rec-back-metals" class="secondary">← Back to Metals</button></div><section class="metals-hero"><div><span class="eyebrow">LONG-TERM METALS OUTLOOK</span><h3>${escapeHtml(cleanStatus(displayStatus(item)))} · strategic thesis remains the primary authority</h3><p class="metals-hero-copy">${escapeHtml(recommendation.rationale??"No narrative rationale is populated in the recommendation record.")}</p><div class="rec-chips"><span class="rec-chip">Domain score ${escapeHtml(fmtNumber(score))}</span><span class="rec-chip">Confidence ${escapeHtml(fmtNumber(confidence))}</span><span class="rec-chip">Tactical state ${escapeHtml(cleanStatus(tacticalState(detail)))}</span></div></div><div class="metals-hero-side"><div class="metals-hero-metric"><span>Forecast horizon</span><strong>${forecast?`${escapeHtml(fmtNumber(forecast.forecast_horizon_months,0))} mo`:"—"}</strong></div><div class="metals-hero-metric"><span>Expected return</span><strong>${escapeHtml(forecast?fmtPercent(forecast.expected_return):"—")}</strong></div><div class="metals-hero-metric"><span>Risk level</span><strong>${escapeHtml(level)}</strong></div><div class="metals-hero-metric"><span>Current regime</span><strong>${escapeHtml(cleanStatus(tacticalRegime(detail)))}</strong></div></div></section><section class="metals-detail-kpis"><article><span>1M return</span><strong>${escapeHtml(technicalReturn(technical,"return_1m"))}</strong></article><article><span>3M return</span><strong>${escapeHtml(technicalReturn(technical,"return_3m"))}</strong></article><article><span>6M return</span><strong>${escapeHtml(technicalReturn(technical,"return_6m"))}</strong></article><article><span>Current drawdown</span><strong class="${technical&&Number(technical.current_drawdown)<0?"negative":""}">${escapeHtml(technicalDrawdown(technical))}</strong></article></section><section class="metals-detail-grid"><div style="display:grid;gap:14px"><article class="metals-panel"><h4>Monthly commodity technical context</h4><p class="metals-panel-sub">Certified direct commodity-benchmark context. Exact calendar-month returns do not replace the long-term recommendation.</p><div class="metals-momentum-bars">${technical?momentumBar("1 month return",Number(technical.return_1m)*100):momentumBar("1 month return",null)}${technical?momentumBar("3 months return",Number(technical.return_3m)*100):momentumBar("3 months return",null)}${technical?momentumBar("6 months return",Number(technical.return_6m)*100):momentumBar("6 months return",null)}${momentumBar("MA50",null)}${momentumBar("MA200",null)}${technical?momentumBar("Drawdown",Number(technical.current_drawdown)*100):momentumBar("Drawdown",null)}</div><p class="governance-note">${technical?"MA50 and MA200 are unsupported by monthly source cadence. No interpolation, forward fill, vehicle proxy, or cross-provider imputation is used.":"Monthly commodity technical context is unavailable under V1 for Uranium because the certified EIA source is annual. No vehicle proxy is used."}</p></article><article class="metals-panel"><h4>Forecast & model evidence</h4><p class="metals-panel-sub">${escapeHtml(modelNote)} ${escapeHtml(uncertaintyNote)}</p>${metalsForecasts(detail).length?`<div class="rec-detail-table"><table><thead><tr><th>Horizon</th><th>Method</th><th>Point forecast</th><th>Expected return</th><th>Bear</th><th>Bull</th><th>Confidence raw</th></tr></thead><tbody>${metalsForecastRows(detail)}</tbody></table></div>`:`<div class="empty">Forecast authority unavailable for this asset. No missing forecast is synthesized.</div>`}</article><article class="metals-panel"><h4>Why this recommendation</h4><div class="rec-narrative"><div><span>Rationale</span><p>${escapeHtml(recommendation.rationale??"No rationale is populated.")}</p></div><div><span>Risk summary</span><p>${escapeHtml(recommendation.risk_summary??"No narrative risk summary is populated.")}</p></div><div><span>Native recommendation</span><p>${escapeHtml(cleanStatus(nativeStatus(item)))}</p></div></div></article></div><div style="display:grid;gap:14px">${tacticalPanel}<aside class="metals-panel"><h4>Risk assessment</h4><div class="history">${riskMetrics(detail)}</div><p class="governance-note">Risk remains independent of tactical state and forecast return.</p></aside><aside class="metals-panel"><h4>Governance boundary</h4><p class="governance-note">Tactical supportive, defensive, or no-overlay states are relative tactical interpretations only. They are not buy/sell instructions, position sizing, automatic execution authority, or replacements for the long-term thesis.</p></aside></div></section></div>`;node("rec-back-metals").addEventListener("click",()=>{selectedDomain="metals";selectedStatus="all";searchText="";pageIndex=0;renderDomain()})}

function renderBlocked(message){const page=node("recommendations");page.innerHTML=`${recommendationDomainSummaryAnchor()}<article class="panel governed-empty"><span class="empty-icon">!</span><h3>Recommendation research is unavailable</h3><p>${escapeHtml(message)}</p></article>`}
async function loadCatalog(force=false){if(loading)return;if(catalog&&!force){selectedDomain==="all"?renderAll():renderDomain();return}loading=true;try{const [crypto,metals,mtg]=await Promise.all(REC_DOMAINS.map(readDomain));catalog={crypto,metals,mtg};detailCache.clear();await hydrateCryptoResearch();selectedDomain==="all"?renderAll():renderDomain()}catch(error){renderBlocked(error.message)}finally{loading=false}}
async function openDomain(domain){selectedDomain=domain;selectedStatus="all";searchText="";pageIndex=0;if(domain==="metals"){try{await hydrateMetalsResearch()}catch(error){renderBlocked(error.message);return}}renderDomain()}

document.querySelector('.nav-item[data-page="recommendations"]')?.addEventListener("click",()=>{if(sessionStorage.getItem("uiip-dashboard-key"))loadCatalog(false)});
document.getElementById("refresh")?.addEventListener("click",()=>{if(document.getElementById("recommendations")?.classList.contains("active-page")&&sessionStorage.getItem("uiip-dashboard-key"))loadCatalog(true)});
if(location.hash==="#recommendations"&&sessionStorage.getItem("uiip-dashboard-key"))loadCatalog(false);
})();
