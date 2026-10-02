(()=>{
"use strict";

const RECORD_TYPE="metals_vehicle_implementation";
const MODEL_COMPONENT_TYPE="metals_model_component";
const UNCERTAINTY_TYPE="metals_uncertainty_adjusted";
const REGIME_TYPE="metals_regime_probability";
const TECHNICAL_CONTEXT_TYPE="metals_commodity_technical_context";
const PREFERRED_LABEL="PREFERRED_IMPLEMENTATION_CANDIDATE";
const ONLY_LABEL="ONLY_REGISTERED_IMPLEMENTATION";
const EXPECTED_COMPONENTS=["uip_native_benchmark_momentum","uip_native_vehicle_confirmation","uip_native_data_completeness_adjustment"];
const EXPECTED_HORIZONS=[12,36,60];
const EXPECTED_REGIMES=["POSITIVE_TREND","NEUTRAL_OR_MIXED","NEGATIVE_TREND"];
let lastMetalsAssetId=null;
let requestSerial=0;

function escapeHtml(value){const span=document.createElement("span");span.textContent=String(value??"");return span.innerHTML;}
function fmtNumber(value,digits=2){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?new Intl.NumberFormat(undefined,{maximumFractionDigits:digits}).format(parsed):String(value);}
function fmtExpense(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?`${parsed.toFixed(2)}%`:String(value);}
function fmtPctFraction(value,digits=1){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);return Number.isFinite(parsed)?`${(parsed*100).toFixed(digits)}%`:String(value);}
function fmtUsd(value){if(value===null||value===undefined||value==="")return "—";const parsed=Number(value);if(!Number.isFinite(parsed))return String(value);return new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",notation:"compact",maximumFractionDigits:2}).format(parsed);}
function clean(value){return String(value??"").replaceAll("_"," ");}
function title(value){return clean(value).toLowerCase().replace(/(^|\s)\S/g,m=>m.toUpperCase());}
function payloads(detail,type){const rows=Array.isArray(detail?.records?.[type])?detail.records[type]:[];return rows.map(record=>record?.payload||{});}
function presentationAssetId(row){return String(row?._presentation_asset_id||row?.universal_asset_id||"");}

function ensureStyles(){
  if(document.getElementById("metals-vehicle-ui-styles"))return;
  const style=document.createElement("style");style.id="metals-vehicle-ui-styles";
  style.textContent=`
    .metals-vehicle-panel,.metals-research-evidence-panel{margin:14px 0;border:1px solid var(--line);border-radius:16px;padding:18px;background:linear-gradient(145deg,rgba(18,37,34,.96),rgba(8,22,20,.98));box-shadow:var(--shadow)}
    .metals-vehicle-panel-head,.metals-research-evidence-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;margin-bottom:14px}.metals-vehicle-panel-head h4,.metals-research-evidence-head h4{margin:4px 0 0;font-size:18px}.metals-vehicle-panel-head p,.metals-research-evidence-head p{margin:5px 0 0;color:var(--muted);font-size:9px;line-height:1.5;max-width:820px}
    .metals-vehicle-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.metals-vehicle-card{border:1px solid rgba(36,65,59,.9);border-radius:12px;padding:14px;background:rgba(7,19,16,.48);display:grid;gap:10px}.metals-vehicle-card.is-preferred{border-color:rgba(99,230,190,.55);background:rgba(99,230,190,.055)}.metals-vehicle-card.is-only{border-color:rgba(255,207,102,.5);background:rgba(255,207,102,.045)}
    .metals-vehicle-card-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.metals-vehicle-id{display:flex;gap:9px;align-items:center}.metals-vehicle-rank{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;border:1px solid var(--line);font-size:9px;color:var(--muted)}.metals-vehicle-id strong{font-size:14px}.metals-vehicle-id small{display:block;color:var(--muted);font-size:8px;margin-top:2px}.metals-vehicle-label{border-radius:999px;border:1px solid rgba(99,230,190,.4);padding:4px 7px;font-size:8px;color:var(--accent);text-transform:uppercase}.metals-vehicle-label.only{border-color:rgba(255,207,102,.45);color:var(--warn)}
    .metals-vehicle-metrics,.metals-vehicle-breakdown,.metals-vehicle-evidence{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.metals-vehicle-metric{border-top:1px solid rgba(36,65,59,.55);padding-top:8px}.metals-vehicle-metric span{display:block;color:var(--muted);font-size:8px}.metals-vehicle-metric strong{display:block;margin-top:3px;font-size:12px}
    .metals-vehicle-subhead{font-size:9px;font-weight:700;margin-top:2px}.metals-vehicle-breakdown .metals-vehicle-metric strong,.metals-vehicle-evidence .metals-vehicle-metric strong{font-size:10px}.metals-vehicle-source{font-size:8px;color:var(--muted);line-height:1.45}.metals-vehicle-source a{color:var(--accent);text-decoration:none}.metals-vehicle-note,.metals-vehicle-caveat,.metals-research-evidence-note{margin-top:12px;border:1px dashed rgba(255,207,102,.38);border-radius:10px;padding:10px 12px;background:rgba(255,207,102,.045);font-size:9px;color:var(--muted);line-height:1.5}.metals-vehicle-note strong,.metals-vehicle-caveat strong,.metals-research-evidence-note strong{color:var(--text)}
    .metals-research-horizons{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.metals-research-horizon{border:1px solid rgba(36,65,59,.9);border-radius:12px;padding:14px;background:rgba(7,19,16,.48);display:grid;gap:10px}.metals-research-horizon h5{margin:0;font-size:13px}.metals-research-horizon-sub{color:var(--muted);font-size:8px}
    .metals-research-signal-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.metals-research-signal{border-top:1px solid rgba(36,65,59,.55);padding-top:8px}.metals-research-signal span{display:block;color:var(--muted);font-size:8px;line-height:1.35}.metals-research-signal strong{display:block;margin-top:3px;font-size:11px}
    .metals-research-adjusted{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.metals-research-adjusted div{border:1px solid rgba(36,65,59,.55);border-radius:9px;padding:8px;background:rgba(18,37,34,.38)}.metals-research-adjusted span{display:block;color:var(--muted);font-size:8px}.metals-research-adjusted strong{display:block;margin-top:3px;font-size:11px}
    .metals-regime-evidence{margin-top:14px;border-top:1px solid rgba(36,65,59,.75);padding-top:14px}.metals-regime-evidence h5{margin:0 0 8px;font-size:12px}.metals-regime-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.metals-regime-cell{border:1px solid rgba(36,65,59,.7);border-radius:10px;padding:10px;background:rgba(7,19,16,.42)}.metals-regime-cell span{display:block;color:var(--muted);font-size:8px}.metals-regime-cell strong{display:block;margin-top:4px;font-size:14px}.metals-regime-cell.is-dominant{border-color:rgba(99,230,190,.45);background:rgba(99,230,190,.05)}
    .metals-technical-context-panel{margin:14px 0;border:1px solid var(--line);border-radius:16px;padding:18px;background:linear-gradient(145deg,rgba(18,37,34,.96),rgba(8,22,20,.98));box-shadow:var(--shadow)}.metals-technical-context-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;margin-bottom:14px}.metals-technical-context-head h4{margin:4px 0 0;font-size:18px}.metals-technical-context-head p{margin:5px 0 0;color:var(--muted);font-size:9px;line-height:1.5;max-width:820px}.metals-technical-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}.metals-technical-metric{border:1px solid rgba(36,65,59,.65);border-radius:10px;padding:10px;background:rgba(7,19,16,.42)}.metals-technical-metric span{display:block;color:var(--muted);font-size:8px;line-height:1.35}.metals-technical-metric strong{display:block;margin-top:4px;font-size:13px}.metals-technical-context-source{margin-top:12px;color:var(--muted);font-size:8px;line-height:1.5}.metals-technical-context-note{margin-top:12px;border:1px dashed rgba(255,207,102,.38);border-radius:10px;padding:10px 12px;background:rgba(255,207,102,.045);font-size:9px;color:var(--muted);line-height:1.5}.metals-technical-context-note strong{color:var(--text)}
    @media(max-width:1000px){.metals-vehicle-grid,.metals-research-horizons{grid-template-columns:repeat(2,minmax(0,1fr))}.metals-technical-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:780px){.metals-research-signal-grid,.metals-research-adjusted,.metals-regime-grid{grid-template-columns:1fr 1fr}.metals-technical-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:680px){.metals-vehicle-grid,.metals-research-horizons,.metals-technical-grid{grid-template-columns:1fr}.metals-vehicle-panel-head,.metals-research-evidence-head,.metals-technical-context-head{display:grid}.metals-research-signal-grid,.metals-research-adjusted,.metals-regime-grid{grid-template-columns:1fr}}
  `;document.head.appendChild(style);
}

function validatedUrl(value){try{const url=new URL(String(value||""),window.location.origin);return url.protocol==="https:"||url.protocol==="http:"?url.href:null;}catch(_){return null;}}
function recordsFrom(detail){const rows=payloads(detail,RECORD_TYPE).slice();rows.sort((a,b)=>Number(a.certified_rank_within_commodity)-Number(b.certified_rank_within_commodity));return rows;}

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

function validateResearchEvidence(detail,assetId){
  const components=payloads(detail,MODEL_COMPONENT_TYPE);const uncertainty=payloads(detail,UNCERTAINTY_TYPE);const regimes=payloads(detail,REGIME_TYPE);
  if(!components.length&&!uncertainty.length&&!regimes.length)return null;
  if(components.length!==9||uncertainty.length!==3||regimes.length!==3)throw new Error("Metals research evidence record count mismatch.");
  const componentKeys=new Set();
  for(const row of components){
    if(row.authority_id&&row.authority_id!=="UIP_NATIVE_METALS_MODEL_COMPONENT_V1")throw new Error("Unexpected Metals model component authority.");
    const horizon=Number(row.horizon_months);const name=String(row.model_name||"");if(!EXPECTED_HORIZONS.includes(horizon)||!EXPECTED_COMPONENTS.includes(name))throw new Error("Unexpected Metals model component grain.");
    const key=`${horizon}|${name}`;if(componentKeys.has(key))throw new Error("Duplicate Metals model component evidence.");componentKeys.add(key);
  }
  for(const horizon of EXPECTED_HORIZONS){for(const name of EXPECTED_COMPONENTS){if(!componentKeys.has(`${horizon}|${name}`))throw new Error("Missing Metals model component evidence.");}}
  const uncertaintyByHorizon=new Map();
  for(const row of uncertainty){
    if(row.authority_id&&row.authority_id!=="UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1")throw new Error("Unexpected Metals uncertainty-adjusted authority.");
    const presentationId=presentationAssetId(row);if(presentationId&&presentationId!==assetId)throw new Error("Metals uncertainty-adjusted identity mismatch.");
    const horizon=Number(row.horizon_months);if(!EXPECTED_HORIZONS.includes(horizon)||uncertaintyByHorizon.has(horizon))throw new Error("Unexpected Metals uncertainty-adjusted grain.");uncertaintyByHorizon.set(horizon,row);
  }
  const regimeByName=new Map();
  for(const row of regimes){
    if(row.authority_id&&row.authority_id!=="UIP_NATIVE_METALS_REGIME_PROBABILITY_V1")throw new Error("Unexpected Metals regime authority.");
    const presentationId=presentationAssetId(row);if(presentationId&&presentationId!==assetId)throw new Error("Metals regime identity mismatch.");
    const regime=String(row.regime||"");if(!EXPECTED_REGIMES.includes(regime)||regimeByName.has(regime))throw new Error("Unexpected Metals regime probability grain.");regimeByName.set(regime,row);
  }
  return {components,uncertaintyByHorizon,regimeByName};
}

function componentFor(components,horizon,name){return components.find(row=>Number(row.horizon_months)===horizon&&row.model_name===name)||null;}
function signal(label,row){return `<div class="metals-research-signal"><span>${escapeHtml(label)} · weight ${escapeHtml(fmtPctFraction(row?.model_weight,0))}</span><strong>${escapeHtml(fmtPctFraction(row?.model_forecast,1))}</strong></div>`;}
function researchHorizonCard(evidence,horizon){
  const u=evidence.uncertaintyByHorizon.get(horizon);const benchmark=componentFor(evidence.components,horizon,"uip_native_benchmark_momentum");const vehicle=componentFor(evidence.components,horizon,"uip_native_vehicle_confirmation");const completeness=componentFor(evidence.components,horizon,"uip_native_data_completeness_adjustment");
  return `<article class="metals-research-horizon"><div><h5>${horizon} month forecast evidence</h5><div class="metals-research-horizon-sub">${horizon>12?"Extrapolated: the 12-month model rate compounded, not a separate forecast.":"Explanatory decomposition of the 12-month forecast."}</div></div><div class="metals-research-signal-grid">${signal("Benchmark momentum",benchmark)}${signal("Vehicle confirmation",vehicle)}${signal("Neutral anchor (toward 0)",completeness)}</div><div class="metals-research-adjusted"><div><span>Raw expected return</span><strong>${escapeHtml(fmtPctFraction(u?.raw_expected_return))}</strong></div><div><span>Confidence</span><strong>${escapeHtml(fmtPctFraction(u?.confidence,0))}</strong></div><div><span>Uncertainty haircut</span><strong>${escapeHtml(fmtPctFraction(u?.uncertainty_penalty))}</strong></div><div><span>Adjusted expected return</span><strong>${escapeHtml(fmtPctFraction(u?.adjusted_expected_return))}</strong></div></div></article>`;
}

function falseFlag(value){return value===false||String(value??"").toLowerCase()==="false";}
function technicalContext(detail,assetId){
  const rows=payloads(detail,TECHNICAL_CONTEXT_TYPE);
  if(assetId==="metals:commodity:uranium"){
    if(rows.length!==0)throw new Error("Uranium technical context must remain unavailable under V1.");
    return {unavailable:true};
  }
  if(rows.length!==1)throw new Error("Metals commodity technical context must contain exactly one record for supported commodities.");
  const row=rows[0];
  if(row.authority_id!=="UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1")throw new Error("Unexpected Metals commodity technical context authority.");
  if(presentationAssetId(row)!==assetId)throw new Error("Metals commodity technical context identity mismatch.");
  if(String(row.source_provider||"").toLowerCase()!=="world_bank")throw new Error("Metals commodity technical context must use World Bank source authority.");
  if(String(row.source_frequency||"").toLowerCase()!=="monthly")throw new Error("Metals commodity technical context source frequency mismatch.");
  if(!falseFlag(row.ma50_supported)||!falseFlag(row.ma200_supported))throw new Error("Metals commodity technical context refuses unauthorized daily moving averages.");
  if(row.presentation_semantics!=="DESCRIPTIVE_COMMODITY_TECHNICAL_CONTEXT_NOT_RECOMMENDATION_NOT_EXECUTION")throw new Error("Metals commodity technical context presentation semantics mismatch.");
  return {unavailable:false,row};
}
function technicalMetric(label,value){return `<div class="metals-technical-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;}
function renderTechnicalContext(detail,assetId){
  const context=technicalContext(detail,assetId);const host=document.querySelector("#recommendations .rec-detail");const hero=host?.querySelector(".metals-hero");if(!host||!hero||host.querySelector(".metals-technical-context-panel"))return;ensureStyles();
  const anchor=host.querySelector(".metals-research-evidence-panel")||host.querySelector(".metals-vehicle-panel")||hero;
  if(context.unavailable){
    anchor.insertAdjacentHTML("afterend",`<section class="metals-technical-context-panel" aria-label="Commodity technical context"><div class="metals-technical-context-head"><div><span class="eyebrow">COMMODITY TECHNICAL CONTEXT</span><h4>Commodity technical context</h4><p>Direct commodity-benchmark technical context is shown only when the certified source cadence can support it.</p></div><span class="metals-status">Unavailable</span></div><div class="metals-technical-context-note"><strong>Uranium is unavailable in V1.</strong> The certified EIA source is annual and cannot support governed monthly 1M / 3M / 6M technical context. No vehicle proxy, interpolation, or cross-provider substitution is used.</div></section>`);
    return;
  }
  const row=context.row;const asOf=row.as_of_date?String(row.as_of_date):"—";const observations=row.observation_count===null||row.observation_count===undefined||row.observation_count===""?"—":fmtNumber(row.observation_count,0);
  const sourceSeries=row.source_series_id?String(row.source_series_id):"—";
  anchor.insertAdjacentHTML("afterend",`<section class="metals-technical-context-panel" aria-label="Commodity technical context"><div class="metals-technical-context-head"><div><span class="eyebrow">COMMODITY TECHNICAL CONTEXT</span><h4>Official monthly benchmark context</h4><p>Descriptive World Bank monthly commodity-benchmark context. These measurements explain recent benchmark behavior and do not change the commodity recommendation or authorize execution.</p></div><span class="metals-status">As of ${escapeHtml(asOf)}</span></div><div class="metals-technical-grid">${technicalMetric("1 month return",fmtPctFraction(row.return_1m))}${technicalMetric("3 month return",fmtPctFraction(row.return_3m))}${technicalMetric("6 month return",fmtPctFraction(row.return_6m))}${technicalMetric("Current drawdown",fmtPctFraction(row.current_drawdown))}${technicalMetric("MA50","Unsupported by monthly source cadence")}${technicalMetric("MA200","Unsupported by monthly source cadence")}</div><div class="metals-technical-context-source">World Bank Pink Sheet monthly benchmark · ${escapeHtml(sourceSeries)} · ${escapeHtml(observations)} official monthly observations · historical peak ${escapeHtml(fmtNumber(row.historical_peak_value,4))} on ${escapeHtml(row.historical_peak_date||"—")}</div><div class="metals-technical-context-note"><strong>Interpretation boundary.</strong> Exact-calendar-month comparisons only. No interpolation, forward fill, vehicle proxy, or cross-provider imputation is used. MA50 and MA200 are intentionally not calculated from monthly data.</div></section>`);
}

function renderResearchEvidence(detail,assetId){
  const evidence=validateResearchEvidence(detail,assetId);if(!evidence)return;const host=document.querySelector("#recommendations .rec-detail");const hero=host?.querySelector(".metals-hero");if(!host||!hero||host.querySelector(".metals-research-evidence-panel"))return;ensureStyles();
  const regimeRows=EXPECTED_REGIMES.map(name=>evidence.regimeByName.get(name));const dominant=String(regimeRows[0]?.dominant_regime||regimeRows[1]?.dominant_regime||regimeRows[2]?.dominant_regime||"");
  const regimeHtml=regimeRows.map(row=>`<div class="metals-regime-cell ${row?.regime===dominant?"is-dominant":""}"><span>${escapeHtml(title(row?.regime||""))}${row?.regime===dominant?" · dominant":""}</span><strong>${escapeHtml(fmtPctFraction(row?.probability))}</strong></div>`).join("");
  const anchor=host.querySelector(".metals-vehicle-panel")||hero;
  anchor.insertAdjacentHTML("afterend",`<section class="metals-research-evidence-panel" aria-label="Certified forecast evidence"><div class="metals-research-evidence-head"><div><span class="eyebrow">FORECAST EVIDENCE</span><h4>Certified forecast evidence</h4><p>The current UIP-native forecast is decomposed into its governed inputs, confidence-adjusted return, and descriptive regime support. These records explain the commodity thesis; they do not create a separate recommendation.</p></div><span class="metals-status">12 governed evidence rows</span></div><div class="metals-research-horizons">${EXPECTED_HORIZONS.map(h=>researchHorizonCard(evidence,h)).join("")}</div><div class="metals-regime-evidence"><h5>Current regime support</h5><div class="metals-regime-grid">${regimeHtml}</div></div><div class="metals-research-evidence-note"><strong>Interpretation boundary.</strong> The adjusted return is a one-sided confidence haircut, not a bear/bull interval. Regime values are descriptive normalized support, not statistically calibrated probabilities. Vehicle Risk V1 remains vehicle-only and is not projected onto the commodity.</div></section>`);
}

async function loadAndRender(assetId){
  const serial=++requestSerial;const key=sessionStorage.getItem("uiip-dashboard-key")||"";if(!key||!assetId)return;
  try{const response=await fetch(`/v1/presentation/assets/metals/${encodeURIComponent(assetId)}`,{headers:{"X-API-Key":key,"Accept":"application/json"}});if(!response.ok)return;const detail=await response.json();if(serial!==requestSerial||lastMetalsAssetId!==assetId)return;renderPanel(detail,assetId);renderResearchEvidence(detail,assetId);renderTechnicalContext(detail,assetId);}catch(_){}
}
function maybeRender(){if(!lastMetalsAssetId)return;const detail=document.querySelector("#recommendations .rec-detail .metals-hero");if(!detail)return;const hasVehicles=document.querySelector("#recommendations .metals-vehicle-panel");const hasResearch=document.querySelector("#recommendations .metals-research-evidence-panel");const hasTechnical=document.querySelector("#recommendations .metals-technical-context-panel");if(hasVehicles&&hasResearch&&hasTechnical)return;loadAndRender(lastMetalsAssetId);}
document.addEventListener("click",event=>{const button=event.target.closest?.(".rec-metals-detail");if(button?.dataset?.assetId){lastMetalsAssetId=button.dataset.assetId;setTimeout(maybeRender,0);}const back=event.target.closest?.("#rec-back-metals");if(back){lastMetalsAssetId=null;requestSerial+=1;}},true);
const observer=new MutationObserver(()=>maybeRender());observer.observe(document.documentElement,{childList:true,subtree:true});
window.UIPMetalsVehicleImplementation={recordType:RECORD_TYPE,technicalContextType:TECHNICAL_CONTEXT_TYPE,renderPanel,renderResearchEvidence,renderTechnicalContext};
})();
