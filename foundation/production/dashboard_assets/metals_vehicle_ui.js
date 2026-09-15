(()=>{
"use strict";

const RECORD_TYPE="metals_vehicle_implementation";
const PREFERRED_LABEL="PREFERRED_IMPLEMENTATION_CANDIDATE";
const ONLY_LABEL="ONLY_REGISTERED_IMPLEMENTATION";
let lastMetalsAssetId=null;
let requestSerial=0;

function escapeHtml(value){const span=document.createElement("span");span.textContent=String(value??"");return span.innerHTML;}
function fmtNumber(value,digits=2){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?new Intl.NumberFormat(undefined,{maximumFractionDigits:digits}).format(parsed):String(value);}
function fmtExpense(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?`${parsed.toFixed(2)}%`:String(value);}
function fmtPctFraction(value,digits=1){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?`${(parsed*100).toFixed(digits)}%`:String(value);}
function fmtUsd(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);if(!Number.isFinite(parsed))return String(value);return new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",notation:"compact",maximumFractionDigits:2}).format(parsed);}
function clean(value){return String(value??"").replaceAll("_"," ");}

function ensureStyles(){
  if(document.getElementById("metals-vehicle-ui-styles"))return;
  const style=document.createElement("style");style.id="metals-vehicle-ui-styles";
  style.textContent=`
    .metals-vehicle-panel{margin:14px 0;border:1px solid var(--line);border-radius:16px;padding:18px;background:linear-gradient(145deg,rgba(18,37,34,.96),rgba(8,22,20,.98));box-shadow:var(--shadow)}
    .metals-vehicle-panel-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;margin-bottom:14px}.metals-vehicle-panel-head h4{margin:4px 0 0;font-size:18px}.metals-vehicle-panel-head p{margin:5px 0 0;color:var(--muted);font-size:9px;line-height:1.5;max-width:760px}
    .metals-vehicle-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.metals-vehicle-card{border:1px solid rgba(36,65,59,.9);border-radius:12px;padding:14px;background:rgba(7,19,16,.48);display:grid;gap:10px}.metals-vehicle-card.is-preferred{border-color:rgba(99,230,190,.55);background:rgba(99,230,190,.055)}.metals-vehicle-card.is-only{border-color:rgba(255,207,102,.5);background:rgba(255,207,102,.045)}
    .metals-vehicle-card-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.metals-vehicle-id{display:flex;gap:9px;align-items:center}.metals-vehicle-rank{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;border:1px solid var(--line);font-size:9px;color:var(--muted)}.metals-vehicle-id strong{font-size:14px}.metals-vehicle-id small{display:block;color:var(--muted);font-size:8px;margin-top:2px}.metals-vehicle-label{border-radius:999px;border:1px solid rgba(99,230,190,.4);padding:4px 7px;font-size:8px;color:var(--accent);text-transform:uppercase}.metals-vehicle-label.only{border-color:rgba(255,207,102,.45);color:var(--warn)}
    .metals-vehicle-metrics,.metals-vehicle-breakdown,.metals-vehicle-evidence{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.metals-vehicle-metric{border-top:1px solid rgba(36,65,59,.55);padding-top:8px}.metals-vehicle-metric span{display:block;color:var(--muted);font-size:8px}.metals-vehicle-metric strong{display:block;margin-top:3px;font-size:12px}
    .metals-vehicle-subhead{font-size:9px;font-weight:700;margin-top:2px}.metals-vehicle-breakdown .metals-vehicle-metric strong,.metals-vehicle-evidence .metals-vehicle-metric strong{font-size:10px}.metals-vehicle-source{font-size:8px;color:var(--muted);line-height:1.45}.metals-vehicle-source a{color:var(--accent);text-decoration:none}.metals-vehicle-note,.metals-vehicle-caveat{margin-top:12px;border:1px dashed rgba(255,207,102,.38);border-radius:10px;padding:10px 12px;background:rgba(255,207,102,.045);font-size:9px;color:var(--muted);line-height:1.5}.metals-vehicle-note strong,.metals-vehicle-caveat strong{color:var(--text)}
    @media(max-width:1000px){.metals-vehicle-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:680px){.metals-vehicle-grid{grid-template-columns:1fr}.metals-vehicle-panel-head{display:grid}}
  `;document.head.appendChild(style);
}

function validatedUrl(value){try{const url=new URL(String(value||""),window.location.origin);return url.protocol==="https:"||url.protocol==="http:"?url.href:null;}catch(_){return null;}}
function recordsFrom(detail){const records=Array.isArray(detail?.records?.[RECORD_TYPE])?detail.records[RECORD_TYPE]:[];const payloads=records.map(record=>record?.payload||{}).slice();payloads.sort((a,b)=>Number(a.certified_rank_within_commodity)-Number(b.certified_rank_within_commodity));return payloads;}

function validate(records,assetId){
  if(!records.length)return false;
  const tickers=new Set();let preferredCount=0;
  for(const row of records){
    if(row.commodity_id!==assetId)throw new Error("Metals vehicle presentation commodity identity mismatch.");
    if(!row.ticker||tickers.has(row.ticker))throw new Error("Metals vehicle presentation contains missing or duplicate ticker evidence.");tickers.add(row.ticker);
    if(row.automatic_execution_authorized!==false||row.portfolio_allocation_authorized!==false||row.position_sizing_authorized!==false||row.central_publication_cron_restoration_authorized!==false)throw new Error("Metals vehicle presentation refuses execution, allocation, sizing, or cron-restoration authority.");
    if(!row.ranking_component_evidence_authority_id)throw new Error("Metals vehicle presentation is missing certified component evidence authority.");
    if(row.presentation_label===PREFERRED_LABEL)preferredCount+=1;
  }
  if(preferredCount>1)throw new Error("Metals vehicle presentation contains more than one preferred implementation candidate.");
  const upstreamRecommendation=String(records[0].upstream_recommendation||"");const upstreamTactical=String(records[0].upstream_tactical_state||"");
  if(preferredCount===1&&(!["BUY","STRONG_BUY"].includes(upstreamRecommendation)||upstreamTactical!=="TACTICAL_SUPPORTIVE"))throw new Error("Metals vehicle presentation would override the upstream commodity thesis.");
  if(assetId==="metals:commodity:silver"&&preferredCount!==0)throw new Error("Defensive Silver may not display a preferred implementation label.");
  return true;
}

function scoreMetric(label,value,weight){return `<div class="metals-vehicle-metric"><span>${escapeHtml(label)}${weight!==undefined?` · ${escapeHtml(fmtNumber(Number(weight)*100,0))}%`:""}</span><strong>${escapeHtml(fmtNumber(value,1))}</strong></div>`;}
function evidenceMetric(label,value){return `<div class="metals-vehicle-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;}

function card(row){
  const preferred=row.presentation_label===PREFERRED_LABEL;const only=row.presentation_label===ONLY_LABEL;const official=validatedUrl(row.official_url);const label=preferred?"Preferred implementation candidate":only?"Only registered implementation":null;const className=preferred?" is-preferred":only?" is-only":"";const w=row.ranking_weights||{};
  const indirect=["miners_etf","thematic_equity_etf"].includes(String(row.vehicle_type||""));
  const scoreText=only?"Not competitively scored":fmtNumber(row.certified_implementation_score,2);
  return `<article class="metals-vehicle-card${className}">
    <div class="metals-vehicle-card-top"><div class="metals-vehicle-id"><span class="metals-vehicle-rank">#${escapeHtml(row.certified_rank_within_commodity)}</span><div><strong>${escapeHtml(row.ticker)}</strong><small>${escapeHtml(row.vehicle_name||row.vehicle_id||"")}</small></div></div>${label?`<span class="metals-vehicle-label ${only?"only":""}">${escapeHtml(label)}</span>`:""}</div>
    <div class="metals-vehicle-metrics">
      <div class="metals-vehicle-metric"><span>Certified score</span><strong>${escapeHtml(scoreText)}</strong></div><div class="metals-vehicle-metric"><span>Expense ratio</span><strong>${escapeHtml(fmtExpense(row.expense_ratio_pct))}</strong></div>
      <div class="metals-vehicle-metric"><span>Exposure type</span><strong>${escapeHtml(clean(row.vehicle_type)||"—")}</strong></div><div class="metals-vehicle-metric"><span>Role</span><strong>${escapeHtml(clean(row.role)||"—")}</strong></div>
    </div>
    <div class="metals-vehicle-subhead">Why this ranks here</div>
    <div class="metals-vehicle-breakdown">${scoreMetric("Exposure fidelity",row.exposure_fidelity_score,w.exposure_fidelity)}${scoreMetric("Cost efficiency",row.cost_efficiency_score,w.cost_efficiency)}${scoreMetric("Liquidity / friction",row.liquidity_implementation_friction_score,w.liquidity_implementation_friction)}${scoreMetric("Risk efficiency",row.risk_efficiency_score,w.risk_efficiency)}</div>
    <div class="metals-vehicle-subhead">Certified implementation evidence</div>
    <div class="metals-vehicle-evidence">${evidenceMetric("30-session ADV",fmtUsd(row.average_dollar_volume_usd))}${evidenceMetric("Bid/ask spread",row.bid_ask_spread_bps===null||row.bid_ask_spread_bps===undefined?"—":`${fmtNumber(row.bid_ask_spread_bps,2)} bps`)}${evidenceMetric("Annualized volatility",fmtPctFraction(row.volatility))}${evidenceMetric("Downside volatility",fmtPctFraction(row.downside_volatility))}${evidenceMetric("Max drawdown",fmtPctFraction(row.maximum_drawdown_magnitude))}${evidenceMetric("Historical 95% VaR",fmtPctFraction(row.value_at_risk))}</div>
    ${indirect?`<div class="metals-vehicle-caveat"><strong>Indirect equity exposure.</strong> This vehicle does not represent direct physical or futures ownership of the commodity; company and sector effects can materially differ from the commodity price.</div>`:""}
    <div class="metals-vehicle-source">Cost evidence: ${escapeHtml(row.source_authority||"—")}${row.source_as_of?` · ${escapeHtml(row.source_as_of)}`:""}${official?` · <a href="${escapeHtml(official)}" target="_blank" rel="noopener noreferrer">Official fund page ↗</a>`:""}</div>
  </article>`;
}

function renderPanel(detail,assetId){
  const records=recordsFrom(detail);if(!validate(records,assetId))return;const host=document.querySelector("#recommendations .rec-detail");const hero=host?.querySelector(".metals-hero");if(!host||!hero||host.querySelector(".metals-vehicle-panel"))return;ensureStyles();
  const upstreamRecommendation=String(records[0].upstream_recommendation||"");const upstreamTactical=String(records[0].upstream_tactical_state||"");const defensive=assetId==="metals:commodity:silver"||records.every(row=>row.presentation_label!==PREFERRED_LABEL)&&records.length>1;
  const note=defensive?`<div class="metals-vehicle-note"><strong>Implementation research only.</strong> Upstream commodity state is ${escapeHtml(clean(upstreamRecommendation))} / ${escapeHtml(clean(upstreamTactical))}. No preferred-buy implementation label is authorized.</div>`:`<div class="metals-vehicle-note">Vehicle ranking is downstream of the commodity thesis. It identifies an implementation candidate only; it does not create a new commodity recommendation, allocation, position size, or execution authority.</div>`;
  hero.insertAdjacentHTML("afterend",`<section class="metals-vehicle-panel" aria-label="Ways to invest"><div class="metals-vehicle-panel-head"><div><span class="eyebrow">IMPLEMENTATION OPTIONS</span><h4>Ways to invest in this commodity</h4><p>Certified within-commodity vehicle ordering with transparent score components and implementation evidence. The commodity recommendation remains the controlling investment authority.</p></div><span class="metals-status">${escapeHtml(records.length)} governed vehicle${records.length===1?"":"s"}</span></div><div class="metals-vehicle-grid">${records.map(card).join("")}</div>${note}</section>`);
}

async function loadAndRender(assetId){const serial=++requestSerial;const key=sessionStorage.getItem("uiip-dashboard-key")||"";if(!key||!assetId)return;try{const response=await fetch(`/v1/presentation/assets/metals/${encodeURIComponent(assetId)}`,{headers:{"X-API-Key":key,"Accept":"application/json"}});if(!response.ok)return;const detail=await response.json();if(serial!==requestSerial||lastMetalsAssetId!==assetId)return;renderPanel(detail,assetId);}catch(_){}}
function maybeRender(){if(!lastMetalsAssetId)return;const detail=document.querySelector("#recommendations .rec-detail .metals-hero");if(!detail)return;if(document.querySelector("#recommendations .metals-vehicle-panel"))return;loadAndRender(lastMetalsAssetId);}
document.addEventListener("click",event=>{const button=event.target.closest?.(".rec-metals-detail");if(button?.dataset?.assetId){lastMetalsAssetId=button.dataset.assetId;setTimeout(maybeRender,0);}const back=event.target.closest?.("#rec-back-metals");if(back){lastMetalsAssetId=null;requestSerial+=1;}},true);
const observer=new MutationObserver(()=>maybeRender());observer.observe(document.documentElement,{childList:true,subtree:true});
window.UIPMetalsVehicleImplementation={recordType:RECORD_TYPE,renderPanel};
})();
