(()=>{
"use strict";
const RECORD_TYPE="tactical_state";
const COMMODITY_EXPLANATION_RECORD_TYPE="metals_commodity_decision_explanation";
const DOMAIN="metals";
const NO_OVERLAY_COPY="No tactical overlay means the frozen directional regime conditions are not currently satisfied; it is not a negative long-term thesis, sell signal, zero expected return, or allocation instruction.";
const UNRESOLVED_COPY="Unsupported fields remain unavailable rather than being synthesized from semantically different evidence.";
const RECOMMENDATION_CHANGE_SUPPORTING_EVIDENCE_LABEL="Recommendation-change evidence:";
const VEHICLE_FORECAST_SEMANTIC_NOTE="Certified vehicle return forecasts are available below. Price-point and bear/base/bull bounds are not populated for this vehicle.";
const URANIUM_FORECAST_UNAVAILABLE_NOTE="No standard commodity forecast is currently available for Uranium; UIP does not infer one from URA or URNM vehicle evidence.";
const COMMODITY_TACTICAL_COPY="Vehicle-level tactical context is not applicable to commodity thesis records. UIP does not synthesize vehicle momentum, drawdown, or tactical state for commodities.";
let pendingDetail=null;
function clean(value){return String(value??"").replaceAll("_"," ").toLowerCase().replace(/(^|\s)\S/g,m=>m.toUpperCase())}
function escapeHtml(value){return String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;")}
function fmtPct(value){if(value===null||value===undefined||value==="")return "—";const n=Number(value);return Number.isFinite(n)?`${n.toFixed(1)}%`:String(value)}
function fmtNumber(value,digits=2){if(value===null||value===undefined||value==="")return "—";const n=Number(value);return Number.isFinite(n)?n.toFixed(digits):String(value)}
function fmtMoney(value){if(value===null||value===undefined||value==="")return "—";const n=Number(value);return Number.isFinite(n)?new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",maximumFractionDigits:2}).format(n):String(value)}
function rows(detail,type){return Array.isArray(detail?.records?.[type])?detail.records[type]:[]}
function payloads(detail,type){return rows(detail,type).map(record=>record.payload||{})}
function firstTactical(detail){const tactical=rows(detail,RECORD_TYPE);return tactical.length?tactical[0].payload||null:null}
function commodityDecisionExplanation(detail){return payloads(detail,COMMODITY_EXPLANATION_RECORD_TYPE)[0]||null}
function uncertaintyRows(detail){return payloads(detail,"metals_uncertainty_adjusted").slice().sort((a,b)=>Number(a.horizon_months)-Number(b.horizon_months))}
function bestUncertainty(detail){const values=uncertaintyRows(detail);return values.length?values[values.length-1]:null}
function recommendationChange(detail){return payloads(detail,"metals_recommendation_change")[0]||null}
function modelComponents(detail){return payloads(detail,"metals_model_component").slice().sort((a,b)=>Number(a.horizon_months)-Number(b.horizon_months)||String(a.model_name||"").localeCompare(String(b.model_name||"")))}
function regimeProbabilities(detail){return payloads(detail,"metals_regime_probability").slice().sort((a,b)=>Number(b.probability)-Number(a.probability))}
function currentPrice(detail){return payloads(detail,"metals_current_price")[0]||null}
function priceHistory(detail){return payloads(detail,"metals_price_history").slice().sort((a,b)=>String(a.observation_date||"").localeCompare(String(b.observation_date||"")))}
function detailAssetId(detail){if(detail?.asset_id)return String(detail.asset_id);for(const type of [COMMODITY_EXPLANATION_RECORD_TYPE,"recommendation","asset","forecast","metals_model_component","metals_current_price","metals_uncertainty_adjusted",RECORD_TYPE]){for(const row of payloads(detail,type)){const value=row.universal_asset_id??row.asset_id??row.universal_vehicle_id;if(value)return String(value)}}return ""}
function isCommodityDetail(detail){return detailAssetId(detail).startsWith("metals:commodity:")||(!firstTactical(detail)&&modelComponents(detail).length>0)}
function tacticalLabel(payload,commodity=false){if(commodity)return "Vehicle-level tactical context not applicable";if(!payload)return "Tactical state unavailable";if(payload.tactical_state==="TACTICAL_SUPPORTIVE")return "Tactical supportive";if(payload.tactical_state==="TACTICAL_DEFENSIVE")return "Tactical defensive";if(payload.tactical_state==="NO_TACTICAL_OVERLAY")return "No tactical overlay";return "Tactical state unavailable"}
function tacticalExplanation(payload,commodity=false){if(commodity)return COMMODITY_TACTICAL_COPY;if(!payload)return "No certified tactical-state record is available for this vehicle.";if(payload.is_reference_control===true)return "Reference/control vehicle; not an opportunity recommendation.";if(payload.tactical_state==="NO_TACTICAL_OVERLAY")return NO_OVERLAY_COPY;return `Current bounded tactical interpretation: ${clean(payload.tactical_state)}. This does not replace the certified long-term recommendation, forecast, risk evidence, or execution controls.`}
function tacticalViewModel(detail){const payload=firstTactical(detail);const commodity=isCommodityDetail(detail);return {recordType:RECORD_TYPE,domain:DOMAIN,label:tacticalLabel(payload,commodity),explanation:tacticalExplanation(payload,commodity),commodity,asOf:payload?.as_of_date??null,regime:payload?.candidate_regime??null,stateReason:payload?.state_reason??null,isReferenceControl:payload?.is_reference_control===true,available:payload?.state_available===true,return1m:payload?.return_1m_pct??null,return3m:payload?.return_3m_pct??null,return6m:payload?.return_6m_pct??null,distanceMa50:payload?.distance_ma50_pct??null,distanceMa200:payload?.distance_ma200_pct??null,drawdown:payload?.current_drawdown_pct??null,volatility3m:payload?.realized_volatility_3m_pct??null};}
function uncertaintyTable(detail){const values=uncertaintyRows(detail);if(!values.length)return "";return `<section class="metals-evidence-block metals-forecast-return-context"><h5>Forecast return context</h5><p class="governance-note">${escapeHtml(VEHICLE_FORECAST_SEMANTIC_NOTE)} Raw and uncertainty-adjusted expected returns are certified vehicle evidence. Penalties are model adjustments, not forecast bounds or generic risk scores.</p><div class="rec-detail-table"><table><thead><tr><th>Horizon</th><th>Raw expected return</th><th>Adjusted expected return</th><th>Uncertainty penalty</th><th>Downside penalty</th></tr></thead><tbody>${values.map(row=>`<tr><td>${fmtNumber(row.horizon_months,0)} mo</td><td>${fmtPct(Number(row.raw_expected_return)*100)}</td><td>${fmtPct(Number(row.adjusted_expected_return)*100)}</td><td>${fmtPct(Number(row.uncertainty_penalty)*100)}</td><td>${fmtPct(Number(row.downside_penalty)*100)}</td></tr>`).join("")}</tbody></table></div></section>`}
function recommendationChangeBlock(detail){const value=recommendationChange(detail);if(!value)return "";return `<section class="metals-evidence-block"><h5>Recommendation evidence</h5><div class="metals-tactical-metrics"><div><span>Previous action</span><strong>${clean(value.previous_action??"unavailable")}</strong></div><div><span>Current action</span><strong>${clean(value.current_action??"unavailable")}</strong></div><div><span>Previous confidence</span><strong>${fmtNumber(value.previous_confidence)}</strong></div><div><span>Current confidence</span><strong>${fmtNumber(value.current_confidence)}</strong></div></div><p class="governance-note">${escapeHtml(RECOMMENDATION_CHANGE_SUPPORTING_EVIDENCE_LABEL)} ${escapeHtml(value.explanation??"No recommendation-change explanation is populated.")}</p></section>`}
function commodityDecisionExplanationBlock(detail){const value=commodityDecisionExplanation(detail);if(!value)return "";if(value.explanation_state!=="AVAILABLE")return `<section class="metals-evidence-block"><h5>Commodity decision explanation</h5><p class="governance-note"><strong>Unavailable.</strong> ${escapeHtml(value.availability_explanation??"Required commodity explanation authority is not currently available.")}</p></section>`;return `<section class="metals-evidence-block" data-evidence-source="${COMMODITY_EXPLANATION_RECORD_TYPE}"><h5>Commodity decision explanation</h5><div class="metals-tactical-metrics"><div><span>${escapeHtml(value.risk_context_semantic_label??"Forecast / regime risk context")}</span><strong>${escapeHtml(value.risk_context_level??"Unavailable")}</strong></div><div><span>Dominant forecast regime</span><strong>${escapeHtml(clean(value.dominant_regime??"unavailable"))}</strong></div><div><span>Regime probability</span><strong>${fmtPct(Number(value.dominant_regime_probability)*100)}</strong></div><div><span>Longest horizon</span><strong>${fmtNumber(value.longest_horizon_months,0)} mo</strong></div></div><p class="governance-note">${escapeHtml(value.risk_context_explanation??"")}</p><p class="governance-note">Source record types: ${escapeHtml((value.source_record_types||[]).join(", "))}.</p></section>`}
function commodityModelBlock(detail){const models=modelComponents(detail);if(!models.length)return "";return `<section class="metals-evidence-block"><h5>Commodity model components</h5><p class="governance-note">Certified component forecasts are shown with their source model weights. They are not synthesized into unsupported price bounds.</p><div class="rec-detail-table"><table><thead><tr><th>Horizon</th><th>Model</th><th>Model forecast</th><th>Weight</th></tr></thead><tbody>${models.map(row=>`<tr><td>${fmtNumber(row.horizon_months,0)} mo</td><td>${clean(row.model_name??"unavailable")}</td><td>${fmtNumber(row.model_forecast,4)}</td><td>${fmtPct(Number(row.model_weight)*100)}</td></tr>`).join("")}</tbody></table></div></section>`}
function commodityRegimeBlock(detail){const regimes=regimeProbabilities(detail);if(!regimes.length)return "";return `<section class="metals-evidence-block"><h5>Commodity regime probabilities</h5><div class="metals-tactical-metrics">${regimes.map(row=>`<div><span>${clean(row.regime??"regime")}</span><strong>${fmtPct(Number(row.probability)*100)}</strong></div>`).join("")}</div><p class="governance-note">These are long-term forecast-regime probabilities, not the vehicle tactical classifier.</p></section>`}
function renderTacticalPanel(detail){pendingDetail=detail;const vm=tacticalViewModel(detail);const asOf=vm.asOf?`<span>As of ${vm.asOf}</span>`:vm.commodity?"<span>Vehicle tactical as-of: not applicable</span>":"<span>As-of date unavailable</span>";const regime=vm.regime?`<span>Regime: ${clean(vm.regime)}</span>`:"";const reason=vm.stateReason?`<small>${clean(vm.stateReason)}</small>`:"";const metrics=vm.commodity?"":`<div class="metals-tactical-metrics"><div><span>1M momentum</span><strong>${fmtPct(vm.return1m)}</strong></div><div><span>3M momentum</span><strong>${fmtPct(vm.return3m)}</strong></div><div><span>6M momentum</span><strong>${fmtPct(vm.return6m)}</strong></div><div><span>Current drawdown</span><strong>${fmtPct(vm.drawdown)}</strong></div><div><span>vs MA50</span><strong>${fmtPct(vm.distanceMa50)}</strong></div><div><span>vs MA200</span><strong>${fmtPct(vm.distanceMa200)}</strong></div><div><span>3M volatility</span><strong>${fmtPct(vm.volatility3m)}</strong></div></div>`;const evidence=vm.commodity?`${commodityDecisionExplanationBlock(detail)}${commodityRegimeBlock(detail)}${commodityModelBlock(detail)}`:`${recommendationChangeBlock(detail)}`;queueMicrotask(()=>enhanceResearchDetail(detail));return `<aside class="rec-tactical-panel metals-tactical-rich ${vm.commodity?"metals-tactical-na":""}" data-record-type="${RECORD_TYPE}"><span class="eyebrow">${vm.commodity?"SUPPORTING CONTEXT":"TACTICAL & SUPPORTING CONTEXT"}</span><h4>${vm.label}</h4><p>${vm.explanation}</p><div class="rec-tactical-meta">${asOf}${regime}</div>${metrics}${reason}${evidence}<p class="governance-note">${UNRESOLVED_COPY}</p></aside>`;}
async function detailRequest(assetId){const key=sessionStorage.getItem("uiip-dashboard-key")||"";if(!key)return null;const response=await fetch(`/v1/presentation/assets/${encodeURIComponent(DOMAIN)}/${encodeURIComponent(assetId)}`,{headers:{"X-API-Key":key,"Accept":"application/json"}});if(!response.ok)return null;return response.json()}
function findKpi(root,label){return [...root.querySelectorAll(".metals-kpi,.metals-hero-metric")].find(node=>node.querySelector("span")?.textContent?.trim()===label)||null}
function setCardForecast(card,detail){const target=findKpi(card,"Forecast return")||findKpi(card,"Adjusted return")||findKpi(card,"Governed return");if(!target)return;const label=target.querySelector("span");const strong=target.querySelector("strong");if(!strong)return;const best=bestUncertainty(detail);if(best){if(label)label.textContent="Adjusted return";strong.textContent=fmtPct(Number(best.adjusted_expected_return)*100);strong.title=`${fmtNumber(best.horizon_months,0)}-month uncertainty-adjusted expected return; raw expected return ${fmtPct(Number(best.raw_expected_return)*100)}`;target.dataset.evidenceSource="metals_uncertainty_adjusted";return}const forecasts=payloads(detail,"forecast").filter(row=>Number.isFinite(Number(row.expected_return)));if(forecasts.length){const longest=forecasts.slice().sort((a,b)=>Number(a.forecast_horizon_months)-Number(b.forecast_horizon_months)).at(-1);if(label)label.textContent="Forecast return";strong.textContent=fmtPct(Number(longest.expected_return)*100);strong.title=`${fmtNumber(longest.forecast_horizon_months,0)}-month governed expected return`;target.dataset.evidenceSource="forecast";return}if(label)label.textContent="Governed return";strong.textContent="Unavailable";strong.title="No governed return forecast is available for this asset; UIP does not infer one.";target.dataset.evidenceSource="unavailable";}
function setCardPrice(card,detail){const value=currentPrice(detail);if(!value)return;let target=card.querySelector(".metals-price-kpi");if(!target){const grid=card.querySelector(".metals-kpis");if(!grid)return;target=document.createElement("div");target.className="metals-kpi metals-price-kpi";target.innerHTML="<span>Current price</span><strong></strong>";grid.appendChild(target)}const strong=target.querySelector("strong");if(strong){strong.textContent=fmtMoney(value.current_price_usd);strong.title=`Observed ${value.observation_date||"date unavailable"} · certified unadjusted close authority`;}target.dataset.evidenceSource="metals_current_price";}
function setCommodityCardState(card,detail){if(!isCommodityDetail(detail))return false;card.classList.add("metals-card-commodity");const drawdown=findKpi(card,"Current drawdown");if(drawdown){const label=drawdown.querySelector("span"),strong=drawdown.querySelector("strong");if(label)label.textContent="Vehicle tactical";if(strong)strong.textContent="N/A";drawdown.dataset.evidenceSource="not_applicable";}const momentum=card.querySelector(".metals-momentum");if(momentum)momentum.outerHTML=`<div class="metals-card-na"><strong>Vehicle-level tactical only</strong><span>Commodity thesis records do not receive vehicle momentum or drawdown metrics.</span></div>`;const track=card.querySelector(".metals-regime-track");const trackContainer=track?.parentElement;if(trackContainer)trackContainer.outerHTML=`<div class="metals-na-callout"><strong>Tactical overlay not applicable</strong><span>Use commodity forecast and regime evidence in Research.</span></div>`;const mini=card.querySelector(".metals-tactical-mini");if(mini)mini.innerHTML="<span>Tactical context</span><strong>Not applicable</strong><span>Vehicle-level policy only</span>";return true;}
function setMomentumMetric(card,label,value){const row=[...card.querySelectorAll(".metals-momentum div")].find(node=>node.querySelector("span")?.textContent?.trim()===label);const strong=row?.querySelector("strong");if(strong){strong.textContent=fmtPct(value);row.dataset.evidenceSource="tactical_state";}}
function setVehicleCardState(card,detail){const tactical=firstTactical(detail);if(!tactical)return;setMomentumMetric(card,"1M momentum",tactical.return_1m_pct);setMomentumMetric(card,"3M momentum",tactical.return_3m_pct);setMomentumMetric(card,"6M momentum",tactical.return_6m_pct);const drawdown=findKpi(card,"Current drawdown");if(drawdown){const strong=drawdown.querySelector("strong");if(strong)strong.textContent=fmtPct(tactical.current_drawdown_pct);drawdown.dataset.evidenceSource="tactical_state";}const mini=card.querySelector(".metals-tactical-mini");if(tactical.tactical_state==="NO_TACTICAL_OVERLAY"){card.classList.add("metals-card-no-overlay");if(mini)mini.innerHTML=`<span>Current tactical state</span><strong>No current overlay</strong><span>${escapeHtml(clean(tactical.candidate_regime??"Neutral or uncertain"))}</span>`;const track=card.querySelector(".metals-regime-track");if(track){const container=track.parentElement;if(container&&!container.querySelector(".metals-overlay-badge")){container.insertAdjacentHTML("afterbegin",'<div class="metals-overlay-badge neutral">No current tactical overlay</div>');}}}}
async function enrichCard(card){if(card.dataset.metalsEvidenceEnriched==="1")return;const button=card.querySelector(".rec-metals-detail[data-asset-id]");const assetId=button?.dataset?.assetId;if(!assetId)return;card.dataset.metalsEvidenceEnriched="pending";try{const detail=await detailRequest(assetId);if(detail){setCardForecast(card,detail);setCardPrice(card,detail);const commodity=setCommodityCardState(card,detail);if(commodity)promoteCommodityOverview(card,detail);else setVehicleCardState(card,detail);promoteUnifiedOverview(card,detail)}card.dataset.metalsEvidenceEnriched="1";}catch(_error){card.dataset.metalsEvidenceEnriched="0";}}
function enrichVisibleCards(){document.querySelectorAll(".metals-card").forEach(card=>{void enrichCard(card)})}
function chartMarkup(detail){const values=priceHistory(detail).filter(row=>Number.isFinite(Number(row.close_usd))&&row.observation_date);if(values.length<2)return "";const stride=Math.max(1,Math.ceil(values.length/180));const sampled=values.filter((_row,index)=>index%stride===0||index===values.length-1);const prices=sampled.map(row=>Number(row.close_usd));const low=Math.min(...prices),high=Math.max(...prices),span=high-low||1;const points=prices.map((value,index)=>`${(index/(prices.length-1))*1000},${190-((value-low)/span)*160}`).join(" ");const first=values[0],last=values[values.length-1];return `<article class="metals-panel metals-price-history-panel" data-evidence-source="metals_price_history"><h4>Historical market price</h4><p class="metals-panel-sub">Certified vehicle history · UNADJUSTED_CLOSE · ${escapeHtml(first.observation_date)} through ${escapeHtml(last.observation_date)} · ${values.length} observations.</p><div class="metals-price-chart-frame"><svg class="metals-price-chart" viewBox="0 0 1000 210" preserveAspectRatio="none"><polyline points="${points}"></polyline></svg></div><div class="metals-tactical-metrics metals-price-history-metrics"><div><span>Start</span><strong>${fmtMoney(first.close_usd)}</strong></div><div><span>Latest</span><strong>${fmtMoney(last.close_usd)}</strong></div><div><span>Period low</span><strong>${fmtMoney(low)}</strong></div><div><span>Period high</span><strong>${fmtMoney(high)}</strong></div></div></article>`}
function addHeroMetric(container,label,value,title=""){const node=document.createElement("div");node.className="metals-hero-metric";node.innerHTML=`<span>${escapeHtml(label)}</span><strong title="${escapeHtml(title)}">${escapeHtml(value)}</strong>`;container.appendChild(node);return node}
function enhanceCommodityHero(detail,side){const forecastRows=payloads(detail,"forecast").filter(row=>Number.isFinite(Number(row.expected_return)));const explanation=commodityDecisionExplanation(detail);const horizon=findKpi(side,"Forecast horizon");const expected=findKpi(side,"Expected return")||findKpi(side,"Standard forecast");const regime=findKpi(side,"Current regime");const risk=findKpi(side,"Risk level")||findKpi(side,"Forecast / regime risk context");if(forecastRows.length){const longest=forecastRows.slice().sort((a,b)=>Number(a.forecast_horizon_months)-Number(b.forecast_horizon_months)).at(-1);if(horizon?.querySelector("strong"))horizon.querySelector("strong").textContent=`${fmtNumber(longest.forecast_horizon_months,0)} mo`;if(expected?.querySelector("strong"))expected.querySelector("strong").textContent=fmtPct(Number(longest.expected_return)*100);}else{if(horizon?.querySelector("strong"))horizon.querySelector("strong").textContent="N/A";if(expected){const label=expected.querySelector("span"),strong=expected.querySelector("strong");if(label)label.textContent="Standard forecast";if(strong)strong.textContent="Unavailable";}}
if(regime){const label=regime.querySelector("span"),strong=regime.querySelector("strong");if(label)label.textContent="Vehicle tactical";if(strong)strong.textContent="N/A";}if(risk){const label=risk.querySelector("span"),strong=risk.querySelector("strong");if(explanation?.risk_context_state==="AVAILABLE"){if(label)label.textContent=explanation.risk_context_semantic_label||"Forecast / regime risk context";if(strong){strong.textContent=explanation.risk_context_level||"Unavailable";strong.title="Derived from commodity forecast-regime authority; not a native typed asset-risk level.";}risk.dataset.evidenceSource=COMMODITY_EXPLANATION_RECORD_TYPE;}else{if(label)label.textContent="Commodity risk context";if(strong){strong.textContent="Unavailable";strong.title=explanation?.availability_explanation||"No governed commodity forecast/regime risk context is available.";}risk.dataset.evidenceSource="unavailable";}}const chips=[...document.querySelectorAll(".metals-hero .rec-chip")];const tacticalChip=chips.find(node=>node.textContent?.trim().startsWith("Tactical state"));if(tacticalChip)tacticalChip.textContent="Tactical: N/A · vehicle-level only";const kpis=document.querySelector(".metals-detail-kpis");if(kpis){kpis.classList.add("metals-commodity-context");kpis.innerHTML='<article class="metals-na-wide"><span>Vehicle-level tactical context</span><strong>Not applicable to commodity thesis</strong><small>Commodity research uses forecast, model-component, and regime evidence instead.</small></article>';}}
function enhanceHero(detail){const hero=document.querySelector(".metals-hero");if(!hero||hero.dataset.decisionUtilityEnhanced==="1")return;const side=hero.querySelector(".metals-hero-side");if(!side)return;if(isCommodityDetail(detail)){enhanceCommodityHero(detail,side);hero.dataset.decisionUtilityEnhanced="1";return}const price=currentPrice(detail);const best=bestUncertainty(detail);if(price){addHeroMetric(side,"Current price",fmtMoney(price.current_price_usd),"Certified vehicle current price");addHeroMetric(side,"Price as of",String(price.observation_date||"—"),"Certified market observation date");}const horizon=findKpi(side,"Forecast horizon");const expected=findKpi(side,"Expected return");if(best){if(horizon?.querySelector("strong"))horizon.querySelector("strong").textContent=`${fmtNumber(best.horizon_months,0)} mo`;if(expected){const label=expected.querySelector("span"),strong=expected.querySelector("strong");if(label)label.textContent="Raw expected return";if(strong)strong.textContent=fmtPct(Number(best.raw_expected_return)*100);}addHeroMetric(side,"Adjusted return",fmtPct(Number(best.adjusted_expected_return)*100),"Raw expected return less certified uncertainty and downside penalties");}hero.dataset.decisionUtilityEnhanced="1";}
function enhanceCommodityMomentumPanel(detail){if(!isCommodityDetail(detail))return;const panels=[...document.querySelectorAll("article.metals-panel")];const panel=panels.find(node=>node.querySelector("h4")?.textContent?.trim()==="Momentum & trend context");if(!panel||panel.dataset.evidenceSource==="not_applicable")return;panel.dataset.evidenceSource="not_applicable";panel.innerHTML='<h4>Vehicle tactical timing context</h4><div class="metals-na-wide"><span>Momentum, moving-average distance, and drawdown</span><strong>Not applicable to commodity thesis</strong><small>Use the commodity forecast, model-component, and regime evidence below. UIP does not infer vehicle tactical metrics into commodity records.</small></div>';}
function enhanceForecastPanel(detail){const panels=[...document.querySelectorAll("article.metals-panel")];const panel=panels.find(node=>node.querySelector("h4")?.textContent?.trim()==="Forecast & model evidence");if(!panel)return;const uncertainty=uncertaintyRows(detail);const models=modelComponents(detail);const assetId=detailAssetId(detail);const empty=panel.querySelector(".empty");if(uncertainty.length){if(empty)empty.remove();if(!panel.querySelector(".metals-forecast-return-context"))panel.insertAdjacentHTML("beforeend",uncertaintyTable(detail));panel.dataset.evidenceSource="metals_uncertainty_adjusted";return}if(models.length){if(empty){empty.textContent="Certified commodity model-component and expected-return evidence is available in Supporting Context. Price-point and forecast bounds are not populated.";empty.dataset.evidenceSource="metals_model_component";}return}if(assetId==="metals:commodity:uranium"&&empty){empty.textContent=URANIUM_FORECAST_UNAVAILABLE_NOTE;empty.dataset.evidenceSource="unavailable";}}
function enhanceRecommendationPanel(detail){const panels=[...document.querySelectorAll("article.metals-panel")];const panel=panels.find(node=>node.querySelector("h4")?.textContent?.trim()==="Why this recommendation");if(!panel)return;const narrative=panel.querySelector(".rec-narrative");if(!narrative)return;const blocks=[...narrative.children];const rationale=blocks.find(node=>node.querySelector("span")?.textContent?.trim()==="Rationale");if(!rationale)return;const paragraph=rationale.querySelector("p");if(!paragraph)return;const explanation=commodityDecisionExplanation(detail);if(explanation){if(explanation.explanation_state==="AVAILABLE"&&explanation.derived_rationale){paragraph.textContent=`${explanation.derived_rationale_semantic_label||"Derived decision rationale"}: ${explanation.derived_rationale}`;rationale.dataset.evidenceSource=COMMODITY_EXPLANATION_RECORD_TYPE;if(!rationale.querySelector(".metals-secondary-copy"))rationale.insertAdjacentHTML("beforeend",'<small class="metals-secondary-copy">Native recommendation rationale remains unpopulated; the text above is a separately typed deterministic explanation from governed Gold evidence.</small>');return}if(explanation.explanation_state==="UNAVAILABLE"){paragraph.textContent=explanation.availability_explanation||"Derived commodity decision explanation is unavailable.";rationale.dataset.evidenceSource="unavailable";if(!rationale.querySelector(".metals-secondary-copy"))rationale.insertAdjacentHTML("beforeend",'<small class="metals-secondary-copy">UIP does not infer commodity rationale or risk context from vehicle evidence.</small>');return}}
const change=recommendationChange(detail);if(!change?.explanation)return;paragraph.textContent=`${RECOMMENDATION_CHANGE_SUPPORTING_EVIDENCE_LABEL} ${change.explanation}`;rationale.dataset.evidenceSource="metals_recommendation_change";if(!rationale.querySelector(".metals-secondary-copy"))rationale.insertAdjacentHTML("beforeend",'<small class="metals-secondary-copy">Full investment-thesis narrative is not populated in the current recommendation authority.</small>');}

function isGoldCommodity(detail){
    return detailAssetId(detail)==="metals:commodity:gold";
}
function availableCommodityExplanation(detail){
    const value=commodityDecisionExplanation(detail);
    return value&&value.explanation_state==="AVAILABLE"?value:null;
}
function conciseGoldThesis(value){
    if(!value)return "";
    const horizon=fmtNumber(value.longest_horizon_months,0);
    const expected=fmtPct(Number(value.longest_horizon_expected_return)*100);
    const regime=clean(value.dominant_regime??"unavailable");
    const probability=fmtPct(Number(value.dominant_regime_probability)*100);
    return `Governed Gold evidence supports a ${horizon}-month expected return of ${expected}. Current forecast / regime risk context is ${value.risk_context_level??"Unavailable"}, with ${regime} at ${probability}.`;
}
function promoteCommodityOverview(card,detail){
    if(!isGoldCommodity(detail))return;
    const value=availableCommodityExplanation(detail);
    if(!value)return;

    const tactical=findKpi(card,"Vehicle tactical");
    if(tactical){
        const label=tactical.querySelector("span");
        const strong=tactical.querySelector("strong");
        if(label)label.textContent="Risk context";
        if(strong){
            strong.textContent=value.risk_context_level??"Unavailable";
            strong.title="Forecast / regime risk context from Gold commodity authority; not a native typed asset-risk score.";
        }
        tactical.dataset.evidenceSource=COMMODITY_EXPLANATION_RECORD_TYPE;
        tactical.classList.add("metals-primary-derived-risk");
    }

    const tableRows=[...document.querySelectorAll(".metals-secondary-table tbody tr")];
    const row=tableRows.find(node=>
        node.textContent?.includes("metals:commodity:gold")
    );

    if(row){
        const cells=[...row.querySelectorAll("td")];
        if(cells.length>=8){
            cells[5].textContent="Derived";
            cells[5].title="Derived decision rationale from governed Gold evidence; native rationale remains unpopulated.";
            cells[5].classList.add("metals-derived-table-value");

            cells[6].textContent=`${value.risk_context_level??"Unavailable"}*`;
            cells[6].title="Forecast / regime risk context; not a native typed asset-risk rating.";
            cells[6].classList.add("metals-derived-table-value");
        }
    }
}
function promoteCommodityDetailHierarchy(detail){
    if(!isGoldCommodity(detail))return;

    const value=availableCommodityExplanation(detail);
    if(!value)return;

    const hero=document.querySelector(".metals-hero");
    if(hero){
        hero.classList.add("metals-derived-gold-hero");

        const copy=hero.querySelector(".metals-hero-copy");
        if(copy){
            copy.textContent=conciseGoldThesis(value);
            copy.dataset.evidenceSource=COMMODITY_EXPLANATION_RECORD_TYPE;
        }

        const side=hero.querySelector(".metals-hero-side");
        if(side){
            const tactical=findKpi(side,"Vehicle tactical");
            if(tactical){
                const label=tactical.querySelector("span");
                const strong=tactical.querySelector("strong");
                if(label)label.textContent="Dominant regime";
                if(strong){
                    strong.textContent=`${clean(value.dominant_regime??"unavailable")} ? ${fmtPct(Number(value.dominant_regime_probability)*100)}`;
                    strong.title="Long-term forecast-regime probability; not vehicle tactical state.";
                }
                tactical.dataset.evidenceSource=COMMODITY_EXPLANATION_RECORD_TYPE;
            }
        }
    }

    const panels=[...document.querySelectorAll("article.metals-panel")];

    const recommendationPanel=panels.find(node=>
        node.querySelector("h4")?.textContent?.trim()==="Why this recommendation"
    );

    if(recommendationPanel){
        recommendationPanel.classList.add("metals-derived-primary-panel");

        const narrative=recommendationPanel.querySelector(".rec-narrative");
        const blocks=narrative?[...narrative.children]:[];

        const rationale=blocks.find(node=>
            node.querySelector("span")?.textContent?.trim()==="Rationale" ||
            node.querySelector("span")?.textContent?.trim()==="Derived decision rationale"
        );

        if(rationale){
            const label=rationale.querySelector("span");
            const paragraph=rationale.querySelector("p");

            if(label)label.textContent="Derived decision rationale";
            if(paragraph)paragraph.textContent=value.derived_rationale??conciseGoldThesis(value);

            rationale.dataset.evidenceSource=COMMODITY_EXPLANATION_RECORD_TYPE;
            rationale.classList.add("metals-derived-rationale-primary");
        }

        const risk=blocks.find(node=>
            node.querySelector("span")?.textContent?.trim()==="Risk summary" ||
            node.querySelector("span")?.textContent?.trim()==="Forecast / regime risk context"
        );

        if(risk){
            const label=risk.querySelector("span");
            const paragraph=risk.querySelector("p");

            if(label)label.textContent="Forecast / regime risk context";

            if(paragraph){
                paragraph.innerHTML=`<strong>${escapeHtml(value.risk_context_level??"Unavailable")}</strong> ? ${escapeHtml(value.risk_context_explanation??"")}`;
            }

            risk.dataset.evidenceSource=COMMODITY_EXPLANATION_RECORD_TYPE;
            risk.classList.add("metals-derived-risk-primary");

            if(!risk.querySelector(".metals-secondary-copy")){
                risk.insertAdjacentHTML(
                    "beforeend",
                    '<small class="metals-secondary-copy">No native recommendation risk_summary or typed risk_metrics_current record is populated for Gold; this is separately typed forecast / regime risk context.</small>'
                );
            }
        }
    }

    const riskPanel=panels.find(node=>
        node.querySelector("h4")?.textContent?.trim()==="Risk assessment"
    );

    if(riskPanel){
        riskPanel.dataset.evidenceSource=COMMODITY_EXPLANATION_RECORD_TYPE;
        riskPanel.classList.add("metals-derived-primary-panel");
        riskPanel.innerHTML=`
            <h4>Forecast / regime risk context</h4>
            <div class="metals-derived-risk-summary">
                <div>
                    <span>Current context</span>
                    <strong>${escapeHtml(value.risk_context_level??"Unavailable")}</strong>
                </div>
                <div>
                    <span>Dominant regime</span>
                    <strong>${escapeHtml(clean(value.dominant_regime??"unavailable"))}</strong>
                </div>
                <div>
                    <span>Regime probability</span>
                    <strong>${fmtPct(Number(value.dominant_regime_probability)*100)}</strong>
                </div>
            </div>
            <p class="metals-panel-sub">${escapeHtml(value.risk_context_explanation??"")}</p>
            <small class="metals-secondary-copy">This is forecast / regime risk context from governed Gold commodity evidence. It is not a native LOW / MEDIUM / HIGH typed asset-risk score and does not populate risk_metrics_current.</small>
        `;
    }
}


/* METALS UNIFIED DECISION TERMINAL 1 */

function unifiedNativeRisk(detail){
    return payloads(detail,"risk")[0]||null;
}

function unifiedRecommendation(detail){
    return payloads(detail,"recommendation")[0]||{};
}

function unifiedLongestForecast(detail){
    const rows=payloads(detail,"forecast")
        .filter(row=>
            Number.isFinite(
                Number(row.expected_return)
            )
        )
        .sort((a,b)=>
            Number(a.forecast_horizon_months)-
            Number(b.forecast_horizon_months)
        );
    return rows.length?rows.at(-1):null;
}

function unifiedTimingState(detail){
    if(isCommodityDetail(detail)){
        return {
            state:"NOT_APPLICABLE",
            label:"N/A",
            note:"Commodity thesis"
        };
    }

    const tactical=firstTactical(detail);

    if(!tactical){
        return {
            state:"UNAVAILABLE",
            label:"Unavailable",
            note:"No certified tactical record"
        };
    }

    if(tactical.tactical_state==="TACTICAL_SUPPORTIVE"){
        return {
            state:"TACTICAL_SUPPORTIVE",
            label:"Supportive",
            note:"Additional timing support"
        };
    }

    if(tactical.tactical_state==="TACTICAL_DEFENSIVE"){
        return {
            state:"TACTICAL_DEFENSIVE",
            label:"Defensive",
            note:"Additional timing caution"
        };
    }

    return {
        state:"NO_TACTICAL_OVERLAY",
        label:"Neutral",
        note:"No additional tactical signal"
    };
}

function unifiedRiskLabel(detail){
    if(isGoldCommodity(detail)){
        const explanation=
            availableCommodityExplanation(detail);

        if(explanation){
            return {
                label:
                    "Forecast / regime risk",
                value:
                    explanation.risk_context_level||
                    "Unavailable",
                semantics:
                    "derived"
            };
        }
    }

    if(isCommodityDetail(detail)){
        return {
            label:"Risk",
            value:"Unavailable",
            semantics:"unavailable"
        };
    }

    const risk=unifiedNativeRisk(detail);

    if(!risk){
        return {
            label:"Risk",
            value:"Unavailable",
            semantics:"unavailable"
        };
    }

    return {
        label:"Risk level",
        value:clean(
            risk.risk_level??
            risk.risk_summary??
            "Unavailable"
        ),
        semantics:"native"
    };
}

function unifiedRemoveLargeTimingBar(card){
    const track=
        card.querySelector(".metals-regime-track");

    if(!track)return;

    const parent=track.parentElement;

    track.remove();

    if(parent){
        const labels=
            parent.querySelector(
                ".metals-track-labels"
            );

        if(labels)labels.remove();

        const badge=
            parent.querySelector(
                ".metals-overlay-badge"
            );

        if(badge)badge.remove();

        if(parent.children.length===0){
            parent.remove();
        }
    }
}

function unifiedCompactCardTiming(card,detail){
    const timing=unifiedTimingState(detail);

    if(
        timing.state==="TACTICAL_SUPPORTIVE" ||
        timing.state==="TACTICAL_DEFENSIVE"
    ){
        card.classList.add(
            "metals-timing-exception"
        );
        return;
    }

    unifiedRemoveLargeTimingBar(card);

    const na=
        card.querySelector(".metals-card-na");

    if(na)na.remove();

    const callout=
        card.querySelector(".metals-na-callout");

    if(callout)callout.remove();

    const mini=
        card.querySelector(
            ".metals-tactical-mini"
        );

    if(mini){
        mini.classList.add(
            "metals-unified-timing-mini"
        );

        mini.innerHTML=`
            <span>Timing</span>
            <strong>${escapeHtml(timing.label)}</strong>
            <span>${escapeHtml(timing.note)}</span>
        `;
    }

    card.classList.add(
        "metals-timing-compact"
    );
}

function unifiedPromoteCardRisk(card,detail){
    const risk=unifiedRiskLabel(detail);

    let target=
        findKpi(card,"Risk context")||
        findKpi(card,"Vehicle tactical")||
        findKpi(card,"Current drawdown")||
        findKpi(card,"Risk level")||
        findKpi(card,"Risk");

    if(!target){
        const grid=
            card.querySelector(".metals-kpis");

        if(grid){
            target=document.createElement("div");
            target.className=
                "metals-kpi metals-unified-risk-kpi";

            target.innerHTML=
                "<span>Risk</span><strong></strong>";

            grid.appendChild(target);
        }
    }

    if(!target)return;

    const label=
        target.querySelector("span");

    const strong=
        target.querySelector("strong");

    if(label){
        label.textContent=risk.label;
    }

    if(strong){
        strong.textContent=risk.value;

        if(risk.semantics==="native"){
            const nativeRisk=
                unifiedNativeRisk(detail);

            const score=
                Number(nativeRisk?.risk_score);

            strong.title=
                Number.isFinite(score)
                ? `Native typed asset risk - score ${score.toFixed(3)}`
                : "Native typed asset risk";
        }

        if(risk.semantics==="derived"){
            strong.title=
                "Derived Gold forecast / regime risk context; not native typed asset risk.";
        }
    }

    target.dataset.evidenceSource=
        risk.semantics==="native"
        ? "risk"
        : risk.semantics==="derived"
        ? COMMODITY_EXPLANATION_RECORD_TYPE
        : "unavailable";

    target.classList.add(
        "metals-unified-risk-kpi"
    );
}

function unifiedUpdateSecondaryTable(detail){
    const assetId=detailAssetId(detail);

    const table=
        document.querySelector(
            ".metals-secondary-table table"
        );

    if(!table)return;

    const headers=[
        ...table.querySelectorAll("thead th")
    ];

    if(headers.length>=8){
        headers[4].textContent="Horizon";
        headers[5].textContent=
            "Rationale / interpretation";
        headers[6].textContent="Risk";
    }

    const row=[
        ...table.querySelectorAll("tbody tr")
    ].find(node=>
        node.textContent?.includes(assetId)
    );

    if(!row)return;

    const cells=[
        ...row.querySelectorAll("td")
    ];

    if(cells.length<8)return;

    const uncertainty=
        bestUncertainty(detail);

    const forecast=
        unifiedLongestForecast(detail);

    if(uncertainty){
        cells[4].textContent=
            `${fmtNumber(
                uncertainty.horizon_months,
                0
            )} mo`;
    }else if(forecast){
        cells[4].textContent=
            `${fmtNumber(
                forecast.forecast_horizon_months,
                0
            )} mo`;
    }

    if(isGoldCommodity(detail)){
        cells[5].textContent="Derived";
    }else if(isCommodityDetail(detail)){
        cells[5].textContent="Unavailable";
    }else{
        cells[5].textContent=
            "Decision view";
    }

    const risk=unifiedRiskLabel(detail);

    cells[6].textContent=
        risk.semantics==="derived"
        ? `${risk.value}*`
        : risk.value;

    cells[5].classList.add(
        "metals-derived-table-value"
    );

    cells[6].classList.add(
        "metals-derived-table-value"
    );
}

function promoteUnifiedOverview(card,detail){
    if(
        card.dataset.unifiedTerminal==="1"
    ){
        return;
    }

    unifiedPromoteCardRisk(card,detail);
    unifiedCompactCardTiming(card,detail);
    unifiedUpdateSecondaryTable(detail);

    card.classList.add(
        "metals-unified-card"
    );

    card.dataset.unifiedTerminal="1";
}

function unifiedForecastInterpretation(detail){
    const value=bestUncertainty(detail);

    if(!value)return null;

    const horizon=
        Number(value.horizon_months);

    const raw=
        Number(value.raw_expected_return)*100;

    const adjusted=
        Number(value.adjusted_expected_return)*100;

    const uncertainty=
        Number(value.uncertainty_penalty)*100;

    const downside=
        Number(value.downside_penalty)*100;

    const gap=adjusted-raw;

    const reverses=
        raw!==0 &&
        adjusted!==0 &&
        Math.sign(raw)!==Math.sign(adjusted);

    let interpretation;

    if(reverses){
        interpretation=
            `The uncertainty adjustment reverses the ${horizon}-month signal from ${fmtPct(raw)} raw to ${fmtPct(adjusted)} adjusted. Long-term upside exists in the raw model, but current uncertainty/downside penalties are large enough to overwhelm it.`;
    }else if(Math.abs(gap)>=25){
        interpretation=
            `The ${horizon}-month adjusted forecast differs materially from the raw forecast: ${fmtPct(raw)} raw versus ${fmtPct(adjusted)} adjusted. Treat the raw upside as highly uncertainty-sensitive.`;
    }else{
        interpretation=
            `The ${horizon}-month raw forecast is ${fmtPct(raw)} and the uncertainty-adjusted forecast is ${fmtPct(adjusted)}. The adjustment does not reverse the directional signal.`;
    }

    return {
        horizon,
        raw,
        adjusted,
        uncertainty,
        downside,
        gap,
        reverses,
        interpretation
    };
}

function unifiedVehicleDecisionText(detail){
    const rec=
        unifiedRecommendation(detail);

    const action=
        clean(
            rec.native_recommendation??
            rec.recommendation??
            "Unavailable"
        );

    const risk=
        unifiedRiskLabel(detail);

    const timing=
        unifiedTimingState(detail);

    const forecast=
        unifiedForecastInterpretation(detail);

    if(!forecast){
        return `${action} remains the certified recommendation. Native risk is ${risk.value}. Current timing is ${timing.label}. No certified uncertainty-adjusted forecast interpretation is available.`;
    }

    return `${action} remains the certified recommendation. At ${forecast.horizon} months, the raw expected return is ${fmtPct(forecast.raw)} and the uncertainty-adjusted return is ${fmtPct(forecast.adjusted)}. Native risk is ${risk.value}. Current timing is ${timing.label.toLowerCase()} - ${timing.note.toLowerCase()}.`;
}

function unifiedFindSection(title){
    return [
        ...document.querySelectorAll(
            "article,section,aside"
        )
    ].find(node=>
        node.querySelector("h4")
            ?.textContent
            ?.trim()===title
    )||null;
}

function unifiedForecastTensionMarkup(detail){
    const value=
        unifiedForecastInterpretation(detail);

    if(!value)return "";

    const state=
        value.reverses
        ? "SIGN REVERSAL"
        : Math.abs(value.gap)>=25
        ? "LARGE ADJUSTMENT"
        : "ADJUSTED OUTLOOK";

    return `
        <section class="metals-forecast-interpretation">
            <div class="metals-forecast-interpretation-head">
                <span>Forecast interpretation</span>
                <strong>${escapeHtml(state)}</strong>
            </div>
            <p>${escapeHtml(value.interpretation)}</p>
            <div class="metals-forecast-interpretation-grid">
                <div>
                    <span>Raw ${fmtNumber(value.horizon,0)}mo</span>
                    <strong>${fmtPct(value.raw)}</strong>
                </div>
                <div>
                    <span>Adjusted ${fmtNumber(value.horizon,0)}mo</span>
                    <strong>${fmtPct(value.adjusted)}</strong>
                </div>
                <div>
                    <span>Uncertainty penalty</span>
                    <strong>${fmtPct(value.uncertainty)}</strong>
                </div>
                <div>
                    <span>Downside penalty</span>
                    <strong>${fmtPct(value.downside)}</strong>
                </div>
            </div>
        </section>
    `;
}

function unifiedPromoteVehicleRecommendation(detail){
    const panel=
        unifiedFindSection(
            "Why this recommendation"
        );

    if(!panel)return;

    panel.classList.add(
        "metals-unified-decision-panel"
    );

    const narrative=
        panel.querySelector(
            ".rec-narrative"
        );

    if(!narrative)return;

    const blocks=[
        ...narrative.children
    ];

    const rationale=
        blocks.find(node=>
            node.querySelector("span")
                ?.textContent
                ?.trim()==="Rationale"
        );

    if(rationale){
        const label=
            rationale.querySelector("span");

        const paragraph=
            rationale.querySelector("p");

        if(label){
            label.textContent=
                "Decision interpretation";
        }

        if(paragraph){
            paragraph.textContent=
                unifiedVehicleDecisionText(detail);
        }

        rationale.dataset.evidenceSource=
            "derived_vehicle_decision_interpretation";

        if(
            !rationale.querySelector(
                ".metals-secondary-copy"
            )
        ){
            rationale.insertAdjacentHTML(
                "beforeend",
                '<small class="metals-secondary-copy">Native recommendation rationale remains unpopulated. This decision interpretation is derived from certified recommendation, forecast, risk, and tactical evidence and is not written back to the native recommendation.</small>'
            );
        }
    }

    const riskBlock=
        blocks.find(node=>
            node.querySelector("span")
                ?.textContent
                ?.trim()==="Risk summary"
        );

    if(riskBlock){
        const risk=
            unifiedNativeRisk(detail);

        const label=
            riskBlock.querySelector("span");

        const paragraph=
            riskBlock.querySelector("p");

        if(label){
            label.textContent=
                "Native risk assessment";
        }

        if(paragraph){
            if(risk){
                const level=
                    clean(
                        risk.risk_level??
                        "Unavailable"
                    );

                const score=
                    Number(risk.risk_score);

                paragraph.textContent=
                    Number.isFinite(score)
                    ? `${level} - risk score ${score.toFixed(3)}. This is the native typed asset-risk authority and remains separate from forecast return and tactical timing.`
                    : `${level}. This is the native typed asset-risk authority and remains separate from forecast return and tactical timing.`;
            }else{
                paragraph.textContent=
                    "No native typed risk record is currently available.";
            }
        }
    }
}

function unifiedCollapseNeutralTactical(detail){
    if(isCommodityDetail(detail))return;

    const tactical=
        firstTactical(detail);

    if(
        !tactical ||
        tactical.tactical_state!==
            "NO_TACTICAL_OVERLAY"
    ){
        const aside=
            document.querySelector(
                ".rec-tactical-panel"
            );

        if(aside){
            aside.classList.add(
                "metals-tactical-exception"
            );
        }

        return;
    }

    const aside=
        document.querySelector(
            ".rec-tactical-panel"
        );

    if(!aside)return;

    const change=
        recommendationChange(detail);

    const changeMarkup=
        change?.explanation
        ? `
          <details class="metals-unified-secondary-details">
            <summary>Supporting recommendation-change evidence</summary>
            <p>${escapeHtml(change.explanation)}</p>
          </details>
        `
        : "";

    aside.className=
        "rec-tactical-panel metals-tactical-compact-detail";

    aside.dataset.recordType=
        RECORD_TYPE;

    aside.innerHTML=`
        <span class="eyebrow">CURRENT TIMING</span>
        <div class="metals-unified-timing-detail">
            <strong>Neutral - no additional tactical signal</strong>
            <span>As of ${escapeHtml(tactical.as_of_date??"date unavailable")}</span>
        </div>
        <p>The tactical classifier has no additional timing opinion right now. The long-term recommendation, forecast, and native risk remain the primary decision authorities.</p>
        <details class="metals-unified-secondary-details">
            <summary>Timing metrics</summary>
            <div class="metals-tactical-metrics">
                <div><span>1M momentum</span><strong>${fmtPct(tactical.return_1m_pct)}</strong></div>
                <div><span>3M momentum</span><strong>${fmtPct(tactical.return_3m_pct)}</strong></div>
                <div><span>6M momentum</span><strong>${fmtPct(tactical.return_6m_pct)}</strong></div>
                <div><span>Drawdown</span><strong>${fmtPct(tactical.current_drawdown_pct)}</strong></div>
                <div><span>vs MA50</span><strong>${fmtPct(tactical.distance_ma50_pct)}</strong></div>
                <div><span>vs MA200</span><strong>${fmtPct(tactical.distance_ma200_pct)}</strong></div>
            </div>
        </details>
        ${changeMarkup}
    `;
}

function unifiedPromoteVehicleResearch(detail){
    const hero=
        document.querySelector(
            ".metals-hero"
        );

    if(hero){
        hero.classList.add(
            "metals-unified-hero"
        );

        const copy=
            hero.querySelector(
                ".metals-hero-copy"
            );

        if(
            copy &&
            (
                copy.textContent.includes(
                    "No narrative rationale"
                ) ||
                copy.textContent.trim()===""
            )
        ){
            copy.textContent=
                unifiedVehicleDecisionText(detail);

            copy.dataset.evidenceSource=
                "derived_vehicle_decision_interpretation";
        }
    }

    const forecastPanel=
        unifiedFindSection(
            "Forecast & model evidence"
        );

    if(
        forecastPanel &&
        !forecastPanel.querySelector(
            ".metals-forecast-interpretation"
        )
    ){
        const markup=
            unifiedForecastTensionMarkup(detail);

        if(markup){
            forecastPanel.insertAdjacentHTML(
                "afterbegin",
                markup
            );
        }
    }

    unifiedPromoteVehicleRecommendation(detail);
    unifiedCollapseNeutralTactical(detail);
}

function unifiedGoldForecastVisual(detail){
    const rows=
        payloads(detail,"forecast")
        .filter(row=>
            Number.isFinite(
                Number(row.expected_return)
            ) &&
            Number.isFinite(
                Number(row.forecast_horizon_months)
            )
        )
        .sort((a,b)=>
            Number(a.forecast_horizon_months)-
            Number(b.forecast_horizon_months)
        );

    if(rows.length<2)return "";

    const values=
        rows.map(row=>
            Number(row.expected_return)*100
        );

    let low=Math.min(0,...values);
    let high=Math.max(0,...values);

    const span=(high-low)||1;

    low-=span*.12;
    high+=span*.12;

    const plotSpan=(high-low)||1;

    const points=
        rows.map((row,index)=>{
            const x=
                54+
                (
                    index/
                    (rows.length-1)
                )*520;

            const value=
                Number(row.expected_return)*100;

            const y=
                176-
                (
                    (value-low)/
                    plotSpan
                )*128;

            return {
                x,
                y,
                value,
                horizon:
                    Number(
                        row.forecast_horizon_months
                    )
            };
        });

    const zeroY=
        176-
        (
            (0-low)/
            plotSpan
        )*128;

    const polyline=
        points
        .map(point=>
            `${point.x},${point.y}`
        )
        .join(" ");

    const dots=
        points.map(point=>`
            <circle
                cx="${point.x}"
                cy="${point.y}"
                r="5"
                class="metals-forecast-dot"
            ></circle>
            <text
                x="${point.x}"
                y="${point.y-12}"
                text-anchor="middle"
                class="metals-svg-value"
            >${escapeHtml(fmtPct(point.value))}</text>
            <text
                x="${point.x}"
                y="202"
                text-anchor="middle"
                class="metals-svg-label"
            >${point.horizon}mo</text>
        `).join("");

    return `
        <article class="metals-panel metals-unified-chart-panel">
            <div class="metals-unified-panel-head">
                <div>
                    <span>RETURN OUTLOOK</span>
                    <h4>Gold forecast path</h4>
                </div>
                <strong>${fmtPct(values.at(-1))}</strong>
            </div>
            <p class="metals-panel-sub">Governed expected-return path across the certified 3, 6, 12, and 24-month horizons.</p>
            <svg
                class="metals-gold-forecast-chart"
                viewBox="0 0 628 220"
                preserveAspectRatio="none"
                aria-label="Gold expected return by horizon"
            >
                <line
                    x1="42"
                    y1="${zeroY}"
                    x2="594"
                    y2="${zeroY}"
                    class="metals-chart-zero"
                ></line>
                <polyline
                    points="${polyline}"
                    class="metals-forecast-line"
                ></polyline>
                ${dots}
            </svg>
        </article>
    `;
}

function unifiedGoldRegimeVisual(detail){
    const rows=
        regimeProbabilities(detail);

    if(!rows.length)return "";

    const markup=
        rows.map(row=>{
            const probability=
                Math.max(
                    0,
                    Math.min(
                        100,
                        Number(row.probability)*100
                    )
                );

            return `
                <div class="metals-regime-visual-row">
                    <div>
                        <span>${escapeHtml(clean(row.regime??"Regime"))}</span>
                        <strong>${fmtPct(probability)}</strong>
                    </div>
                    <svg
                        viewBox="0 0 100 8"
                        preserveAspectRatio="none"
                        aria-hidden="true"
                    >
                        <rect
                            x="0"
                            y="1"
                            width="100"
                            height="6"
                            rx="3"
                            class="metals-regime-bg"
                        ></rect>
                        <rect
                            x="0"
                            y="1"
                            width="${probability}"
                            height="6"
                            rx="3"
                            class="metals-regime-fill"
                        ></rect>
                    </svg>
                </div>
            `;
        }).join("");

    return `
        <article class="metals-panel metals-unified-chart-panel">
            <div class="metals-unified-panel-head">
                <div>
                    <span>RISK CONTEXT</span>
                    <h4>Forecast regime probabilities</h4>
                </div>
            </div>
            <p class="metals-panel-sub">Long-term forecast regimes. These are not vehicle tactical states.</p>
            <div class="metals-regime-visual">
                ${markup}
            </div>
        </article>
    `;
}

function unifiedGoldModelVisual(detail){
    const models=
        modelComponents(detail);

    if(!models.length)return "";

    const horizons=[
        ...new Set(
            models.map(row=>
                Number(row.horizon_months)
            )
        )
    ].sort((a,b)=>a-b);

    const markup=
        horizons.map(horizon=>{
            const rows=
                models.filter(row=>
                    Number(row.horizon_months)===
                    horizon
                );

            const positive=
                rows.filter(row=>
                    Number(row.model_forecast)>0
                ).length;

            const negative=
                rows.filter(row=>
                    Number(row.model_forecast)<0
                ).length;

            return `
                <div class="metals-model-balance-card">
                    <span>${fmtNumber(horizon,0)} mo</span>
                    <strong>${positive} positive - ${negative} negative</strong>
                    <small>${rows.length} certified component models</small>
                </div>
            `;
        }).join("");

    return `
        <article class="metals-panel metals-unified-chart-panel">
            <div class="metals-unified-panel-head">
                <div>
                    <span>MODEL BALANCE</span>
                    <h4>Component direction by horizon</h4>
                </div>
            </div>
            <p class="metals-panel-sub">A compact directional summary of the certified Gold component models. Detailed model rows remain available below for inspection.</p>
            <div class="metals-model-balance-grid">
                ${markup}
            </div>
        </article>
    `;
}

function unifiedGoldRiskAssessment(detail){
    const value=
        availableCommodityExplanation(detail);

    if(!value)return;

    const panel=
        unifiedFindSection(
            "Risk assessment"
        );

    if(!panel)return;

    panel.classList.add(
        "metals-unified-decision-panel"
    );

    panel.dataset.evidenceSource=
        COMMODITY_EXPLANATION_RECORD_TYPE;

    panel.innerHTML=`
        <h4>Forecast / regime risk context</h4>
        <div class="metals-derived-risk-summary">
            <div>
                <span>Current context</span>
                <strong>${escapeHtml(value.risk_context_level??"Unavailable")}</strong>
            </div>
            <div>
                <span>Dominant regime</span>
                <strong>${escapeHtml(clean(value.dominant_regime??"Unavailable"))}</strong>
            </div>
            <div>
                <span>Probability</span>
                <strong>${fmtPct(Number(value.dominant_regime_probability)*100)}</strong>
            </div>
        </div>
        <p class="metals-panel-sub">${escapeHtml(value.risk_context_explanation??"")}</p>
        <small class="metals-secondary-copy">This is separately typed forecast / regime risk context. It is not a native asset-risk score and does not populate risk_metrics_current.</small>
    `;
}

function unifiedGoldResearch(detail){
    const hero=
        document.querySelector(
            ".metals-hero"
        );

    if(!hero)return;

    hero.classList.add(
        "metals-unified-hero",
        "metals-unified-gold"
    );

    const existing=
        document.querySelector(
            ".metals-gold-visual-grid"
        );

    if(!existing){
        const visuals=`
            <section class="metals-gold-visual-grid">
                ${unifiedGoldForecastVisual(detail)}
                ${unifiedGoldRegimeVisual(detail)}
                ${unifiedGoldModelVisual(detail)}
            </section>
        `;

        hero.insertAdjacentHTML(
            "afterend",
            visuals
        );
    }

    const timingPanel=
        unifiedFindSection(
            "Vehicle tactical timing context"
        );

    if(timingPanel){
        timingPanel.classList.add(
            "metals-unified-hidden"
        );
    }

    const kpis=
        document.querySelector(
            ".metals-detail-kpis"
        );

    if(kpis){
        kpis.classList.add(
            "metals-unified-commodity-timing"
        );

        kpis.innerHTML=`
            <article>
                <span>Timing</span>
                <strong>N/A - commodity thesis</strong>
                <small>Vehicle tactical timing is intentionally not inferred into Gold.</small>
            </article>
        `;
    }

    const aside=
        document.querySelector(
            ".rec-tactical-panel.metals-tactical-na"
        );

    if(
        aside &&
        !aside.querySelector(
            ".metals-unified-secondary-details"
        )
    ){
        const original=
            aside.innerHTML;

        aside.classList.add(
            "metals-unified-secondary-context"
        );

        aside.innerHTML=`
            <span class="eyebrow">DETAILED EVIDENCE</span>
            <details class="metals-unified-secondary-details">
                <summary>Open model, regime, and governance evidence</summary>
                <div class="metals-unified-secondary-detail-body">
                    ${original}
                </div>
            </details>
        `;
    }

    unifiedGoldRiskAssessment(detail);
}

function promoteUnifiedResearch(detail){
    if(
        document.body.dataset.metalsUnifiedAsset===
        detailAssetId(detail)
    ){
        return;
    }

    if(isGoldCommodity(detail)){
        unifiedGoldResearch(detail);
    }else if(!isCommodityDetail(detail)){
        unifiedPromoteVehicleResearch(detail);
    }else{
        const aside=
            document.querySelector(
                ".rec-tactical-panel"
            );

        if(aside){
            aside.classList.add(
                "metals-unified-secondary-context"
            );
        }
    }

    document.body.dataset.metalsUnifiedAsset=
        detailAssetId(detail);
}

function enhancePriceHistory(detail){const markup=chartMarkup(detail);if(!markup)return;const panels=[...document.querySelectorAll("article.metals-panel")];if(panels.some(node=>node.classList.contains("metals-price-history-panel")))return;const momentum=panels.find(node=>node.querySelector("h4")?.textContent?.trim()==="Momentum & trend context");if(momentum)momentum.insertAdjacentHTML("afterend",markup);}
function enhanceResearchDetail(detail){if(!document.querySelector(".metals-hero")){pendingDetail=detail;return}enhanceHero(detail);enhanceCommodityMomentumPanel(detail);enhanceForecastPanel(detail);enhanceRecommendationPanel(detail);promoteCommodityDetailHierarchy(detail);promoteUnifiedResearch(detail);enhancePriceHistory(detail);pendingDetail=null;}
const observer=new MutationObserver(()=>{enrichVisibleCards();if(pendingDetail)enhanceResearchDetail(pendingDetail)});
function startEnrichment(){if(!document.body)return;observer.observe(document.body,{childList:true,subtree:true});enrichVisibleCards();if(pendingDetail)enhanceResearchDetail(pendingDetail);}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",startEnrichment,{once:true});else startEnrichment();
window.UIPMetalsTactical={RECORD_TYPE,COMMODITY_EXPLANATION_RECORD_TYPE,DOMAIN,NO_OVERLAY_COPY,UNRESOLVED_COPY,COMMODITY_TACTICAL_COPY,firstTactical,commodityDecisionExplanation,tacticalViewModel,uncertaintyRows,bestUncertainty,recommendationChange,modelComponents,regimeProbabilities,currentPrice,priceHistory,renderTacticalPanel,enrichVisibleCards,enhanceResearchDetail};
})();