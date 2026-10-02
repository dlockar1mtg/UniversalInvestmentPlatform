(()=>{
"use strict";
const RECORD_TYPE="tactical_state";
const DOMAIN="metals";
const NO_OVERLAY_COPY="No tactical overlay means the frozen directional regime conditions are not currently satisfied; it is not a negative long-term thesis, sell signal, zero expected return, or allocation instruction.";
function clean(value){return String(value??"").replaceAll("_"," ").toLowerCase().replace(/(^|\s)\S/g,m=>m.toUpperCase())}
function firstTactical(detail){const rows=Array.isArray(detail?.records?.[RECORD_TYPE])?detail.records[RECORD_TYPE]:[];return rows.length?rows[0].payload||null:null}
function tacticalLabel(payload){if(!payload)return "Tactical state unavailable";if(payload.tactical_state==="TACTICAL_SUPPORTIVE")return "Tactical supportive";if(payload.tactical_state==="TACTICAL_DEFENSIVE")return "Tactical defensive";if(payload.tactical_state==="NO_TACTICAL_OVERLAY")return "No tactical overlay";return payload.tactical_state?clean(payload.tactical_state):"Tactical state unavailable"}
function tacticalExplanation(payload){if(!payload)return "No tactical-state record is available for this asset.";if(payload.is_reference_control===true)return "Reference/control vehicle; not an opportunity recommendation.";if(payload.tactical_state==="NO_TACTICAL_OVERLAY")return NO_OVERLAY_COPY;return `Current bounded tactical interpretation: ${clean(payload.tactical_state)}. This does not replace the long-term recommendation, forecast, risk evidence, or execution controls.`}
function tacticalViewModel(detail){const payload=firstTactical(detail);return {recordType:RECORD_TYPE,domain:DOMAIN,label:tacticalLabel(payload),explanation:tacticalExplanation(payload),asOf:payload?.as_of_date??null,regime:payload?.candidate_regime??null,stateReason:payload?.state_reason??null,isReferenceControl:payload?.is_reference_control===true,available:payload?.state_available===true};}
function renderTacticalPanel(detail){const vm=tacticalViewModel(detail);const asOf=vm.asOf?`<span>As of ${vm.asOf}</span>`:"<span>As-of date unavailable</span>";const regime=vm.regime?`<span>Regime: ${clean(vm.regime)}</span>`:"";const reason=vm.stateReason?`<small>${clean(vm.stateReason)}</small>`:"";return `<aside class="rec-tactical-panel" data-record-type="${RECORD_TYPE}"><span class="eyebrow">TACTICAL CONTEXT</span><h4>${vm.label}</h4><p>${vm.explanation}</p><div class="rec-tactical-meta">${asOf}${regime}</div>${reason}</aside>`;}
window.UIPMetalsTactical={RECORD_TYPE,DOMAIN,NO_OVERLAY_COPY,firstTactical,tacticalViewModel,renderTacticalPanel};
if(!document.querySelector('script[data-uip-metals-vehicle-ui]')){
  const script=document.createElement("script");
  script.src="/dashboard/assets/metals_vehicle_ui.js";
  script.defer=true;
  script.dataset.uipMetalsVehicleUi="1";
  document.head.appendChild(script);
}
})();
