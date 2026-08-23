(()=>{
  const byId=id=>document.getElementById(id);
  const page=byId("recommendations");
  if(!page)return;

  const credentialKey="uiip-dashboard-key";
  const state={summary:null,domain:"crypto",query:"",status:"",rankType:"",hasForecast:"",hasRisk:"",hasPrice:"",manualCheck:"",offset:0,limit:50,list:null,detail:null,busy:false};

  const escape=value=>{const node=document.createElement("span");node.textContent=String(value??"");return node.innerHTML};
  const present=value=>value!==null&&value!==undefined&&value!=="";
  const fmt=value=>present(value)?String(value):"Not published";
  const money=value=>present(value)?new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",maximumFractionDigits:2}).format(Number(value)):"Not published";
  const bool=value=>value===true?"Yes":value===false?"No":"Not published";
  const key=()=>sessionStorage.getItem(credentialKey)||"";
  const api=async path=>{
    const credential=key();
    if(!credential)throw new Error("Connect to UIP to load certified recommendations.");
    const response=await fetch(path,{headers:{"X-API-Key":credential,"Accept":"application/json"}});
    const body=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(body.error?.message||`Request failed (${response.status})`);
    return body;
  };

  const injectStyles=()=>{
    if(byId("rec-ui-1-styles"))return;
    const style=document.createElement("style");
    style.id="rec-ui-1-styles";
    style.textContent=`
      .rec-shell{display:grid;gap:14px}.rec-governance{padding:14px 16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between}.rec-governance p{margin:0;color:var(--muted);font-size:10.5px;line-height:1.5}.rec-tabs{display:flex;gap:7px;flex-wrap:wrap}.rec-tab{background:transparent;color:var(--muted);border:1px solid var(--line);padding:7px 11px}.rec-tab.active{color:var(--accent);border-color:rgba(99,230,190,.35);background:rgba(99,230,190,.08)}.rec-layout{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(360px,.75fr);gap:14px}.rec-list-panel,.rec-detail-panel{padding:20px}.rec-filter-grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px;margin:15px 0}.rec-filter-grid label,.rec-evidence-filters label{display:grid;gap:6px;color:var(--muted);font-size:10px}.rec-filter-grid input,.rec-filter-grid select{width:100%;background:#071310;color:var(--text);border:1px solid #34584f;border-radius:8px;padding:9px 10px}.rec-evidence-filters{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 14px}.rec-evidence-filters label{display:flex;align-items:center;gap:6px}.rec-evidence-filters input{accent-color:var(--accent)}.rec-results{display:grid;border-top:1px solid var(--line)}.rec-row{appearance:none;width:100%;text-align:left;background:transparent;color:var(--text);border:0;border-bottom:1px solid rgba(36,65,59,.62);border-radius:0;padding:13px 2px;display:grid;grid-template-columns:minmax(220px,1fr) 150px 110px 100px;gap:12px;align-items:center}.rec-row:hover,.rec-row.selected{background:rgba(99,230,190,.05)}.rec-row strong{font-size:11.5px}.rec-row small{display:block;color:var(--muted);font-size:9.5px;margin-top:3px;overflow-wrap:anywhere}.rec-cell{font-size:10px;color:var(--muted)}.rec-status{color:var(--text);font-weight:700}.rec-pagination{display:flex;align-items:center;justify-content:space-between;gap:10px;padding-top:14px}.rec-pagination span{font-size:10px;color:var(--muted)}.rec-detail-panel{min-height:520px}.rec-detail-head{display:grid;gap:6px;padding-bottom:14px;border-bottom:1px solid var(--line)}.rec-detail-head h3{margin:0;font-size:17px}.rec-detail-head code{font-size:9px;color:var(--muted);overflow-wrap:anywhere}.rec-detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:14px 0}.rec-detail-grid div{background:var(--surface);padding:11px}.rec-detail-grid span,.rec-native-payload span{display:block;color:var(--muted);font-size:9px}.rec-detail-grid strong{display:block;margin-top:4px;font-size:11px;overflow-wrap:anywhere}.rec-section{margin-top:16px}.rec-section h4{font-size:11px;margin:0 0 8px;color:var(--muted)}.rec-record{padding:10px 0;border-bottom:1px solid rgba(36,65,59,.62);font-size:10px}.rec-record:last-child{border-bottom:0}.rec-record code{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted)}.rec-native-payload{padding:11px;border:1px solid var(--line);border-radius:9px;background:#071310}.rec-native-payload code{display:block;margin-top:7px;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--text);font-size:9px;line-height:1.45}.rec-error{color:var(--bad);font-size:11px;padding:18px 0}.rec-summary-line{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}.rec-summary-chip{border:1px solid var(--line);border-radius:999px;padding:5px 8px;color:var(--muted);font-size:9px}.rec-summary-chip strong{color:var(--text)}
      @media(max-width:1050px){.rec-layout{grid-template-columns:1fr}.rec-detail-panel{min-height:0}}@media(max-width:760px){.rec-filter-grid{grid-template-columns:1fr}.rec-row{grid-template-columns:1fr 1fr}.rec-detail-grid{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  };

  const triValue=element=>element.checked?"true":"";
  const queryString=()=>{
    const params=new URLSearchParams({domain:state.domain,limit:String(state.limit),offset:String(state.offset)});
    if(state.query)params.set("query",state.query);
    if(state.status)params.set("native_status",state.status);
    if(state.rankType)params.set("native_rank_type",state.rankType);
    if(state.hasForecast)params.set("has_forecast",state.hasForecast);
    if(state.hasRisk)params.set("has_risk",state.hasRisk);
    if(state.hasPrice)params.set("current_price_authority_available",state.hasPrice);
    if(state.manualCheck)params.set("manual_execution_price_check_required",state.manualCheck);
    return params.toString();
  };

  const domainSummary=()=>state.summary?.domains?.find(item=>item.domain_id===state.domain)||null;
  const renderChrome=()=>{
    const summary=domainSummary();
    const domains=state.summary?.domains||[];
    page.innerHTML=`<div class="page-heading"><div><span class="eyebrow">RECOMMENDATIONS</span><h2>Domain-native opportunities</h2></div><span class="page-note">REC-UI-1 · certified presentation</span></div><div class="rec-shell"><section class="panel rec-governance"><div><strong>Native semantics preserved</strong><p>No universal cross-domain score or rank. Native ranks are comparable only inside the same native rank type. Missing fields stay missing.</p></div><span class="pill good">AUTOMATIC EXECUTION OFF</span></section><div class="rec-tabs">${domains.map(item=>`<button class="rec-tab ${item.domain_id===state.domain?"active":""}" data-rec-domain="${escape(item.domain_id)}">${escape(item.domain_id.toUpperCase())} · ${escape(item.recommendation_count)}</button>`).join("")}</div>${summary?`<div class="rec-summary-line"><span class="rec-summary-chip"><strong>${escape(summary.recommendation_count)}</strong> recommendations</span><span class="rec-summary-chip">Forecast ${escape(summary.forecast_coverage)}</span><span class="rec-summary-chip">Risk ${escape(summary.risk_coverage)}</span><span class="rec-summary-chip">Certified price authority ${escape(summary.certified_current_price_authority_count)}</span><span class="rec-summary-chip">Manual execution price check ${escape(summary.manual_price_check_required_count)}</span></div>`:""}<div class="rec-layout"><section class="panel rec-list-panel"><div class="section-title"><div><h3>${escape(state.domain.toUpperCase())} recommendations</h3><span>Stable asset identity order · not native-rank sorted</span></div><span id="rec-result-count">Loading…</span></div><div class="rec-filter-grid"><label>Search<input id="rec-search" value="${escape(state.query)}" placeholder="Asset name, symbol, or ID"></label><label>Native status<select id="rec-status"><option value="">All native statuses</option>${Object.entries(summary?.native_statuses||{}).map(([status,count])=>`<option value="${escape(status)}" ${status===state.status?"selected":""}>${escape(status)} (${escape(count)})</option>`).join("")}</select></label><label>Native rank type<select id="rec-rank-type"><option value="">All native rank types</option>${Object.entries(summary?.native_rank_types||{}).map(([rankType,count])=>`<option value="${escape(rankType)}" ${rankType===state.rankType?"selected":""}>${escape(rankType)} (${escape(count)})</option>`).join("")}</select></label></div><div class="rec-evidence-filters"><label><input id="rec-has-forecast" type="checkbox" ${state.hasForecast?"checked":""}> Has forecast</label><label><input id="rec-has-risk" type="checkbox" ${state.hasRisk?"checked":""}> Has risk</label><label><input id="rec-has-price" type="checkbox" ${state.hasPrice?"checked":""}> Certified current price</label><label><input id="rec-manual-check" type="checkbox" ${state.manualCheck?"checked":""}> Manual execution price check</label></div><div id="rec-results" class="rec-results"><div class="empty">Loading certified recommendations…</div></div><div class="rec-pagination"><button id="rec-prev" class="secondary" type="button">Previous</button><span id="rec-page-label">—</span><button id="rec-next" class="secondary" type="button">Next</button></div></section><aside class="panel rec-detail-panel" id="rec-detail"><div class="empty">Select a recommendation to inspect its exact governed detail.</div></aside></div></div>`;
    bindControls();
  };

  const renderList=()=>{
    const document=state.list;
    const container=byId("rec-results");
    if(!container||!document)return;
    byId("rec-result-count").textContent=`${document.total} result${document.total===1?"":"s"}`;
    const start=document.total?document.offset+1:0;
    const end=Math.min(document.offset+document.items.length,document.total);
    byId("rec-page-label").textContent=`${start}-${end} of ${document.total}`;
    byId("rec-prev").disabled=document.offset<=0;
    byId("rec-next").disabled=document.offset+document.limit>=document.total;
    if(!document.items.length){container.innerHTML='<div class="empty">No recommendations match these domain-native filters.</div>';return;}
    container.innerHTML=document.items.map(item=>{const selected=state.detail&&state.detail.asset_id===item.asset_id;const rank=present(item.native_rank)?`${item.native_rank}${item.native_rank_type?` · ${item.native_rank_type}`:""}`:"Not published";const evidence=`Forecast ${item.forecast_record_count} · Risk ${item.risk_record_count}`;return `<button class="rec-row ${selected?"selected":""}" type="button" data-rec-asset="${escape(item.asset_id)}"><div><strong>${escape(item.asset_name||item.asset_symbol||item.asset_id)}</strong><small>${escape(item.asset_symbol||item.asset_id)}${item.asset_subclass?` · ${escape(item.asset_subclass)}`:""}</small></div><div class="rec-cell rec-status">${escape(fmt(item.native_status))}<small>${escape(item.native_status_source_field||"No native status field")}</small></div><div class="rec-cell">Rank ${escape(rank)}<small>Native scope only</small></div><div class="rec-cell">${escape(item.current_price_authority_available?money(item.current_price_usd):"Unpriced")}<small>${escape(evidence)}</small></div></button>`}).join("");
    container.querySelectorAll("[data-rec-asset]").forEach(button=>button.addEventListener("click",()=>loadDetail(button.dataset.recAsset)));
  };

  const recordsHtml=(records,label)=>{if(!records?.length)return `<div class="rec-record">No certified ${escape(label.toLowerCase())} records published for this asset.</div>`;return records.map(record=>`<div class="rec-record"><strong>${escape(record.record_key)}</strong><code>${escape(JSON.stringify(record.payload,null,2))}</code></div>`).join("")};

  const renderDetail=()=>{
    const detail=state.detail;
    const container=byId("rec-detail");
    if(!container)return;
    if(!detail){container.innerHTML='<div class="empty">Select a recommendation to inspect its exact governed detail.</div>';return;}
    const rank=present(detail.native_rank)?String(detail.native_rank):"Not published";
    const confidence=present(detail.confidence_score)?String(detail.confidence_score):"Not published";
    container.innerHTML=`<div class="rec-detail-head"><span class="eyebrow">GOVERNED DETAIL</span><h3>${escape(detail.asset_name||detail.asset_symbol||detail.asset_id)}</h3><code>${escape(detail.asset_id)}</code></div><div class="rec-detail-grid"><div><span>Domain</span><strong>${escape(detail.domain_id.toUpperCase())}</strong></div><div><span>Lane / subclass</span><strong>${escape(fmt(detail.asset_subclass))}</strong></div><div><span>Native status</span><strong>${escape(fmt(detail.native_status))}</strong></div><div><span>Status source field</span><strong>${escape(fmt(detail.native_status_source_field))}</strong></div><div><span>Native rank</span><strong>${escape(rank)}</strong></div><div><span>Native rank type</span><strong>${escape(fmt(detail.native_rank_type))}</strong></div><div><span>Confidence</span><strong>${escape(confidence)}</strong></div><div><span>Certified current price</span><strong>${escape(detail.current_price_authority_available?money(detail.current_price_usd):"Not authoritative")}</strong></div><div><span>Manual execution price check</span><strong>${escape(bool(detail.manual_execution_price_check_required))}</strong></div><div><span>Automatic execution</span><strong>${detail.automatic_purchase_execution?"Yes":"No"}</strong></div></div><div class="rec-section"><h4>Recommendation payload · preserved native fields</h4><div class="rec-native-payload"><span>No normalization or universal score applied</span><code>${escape(JSON.stringify(detail.recommendation_payload,null,2))}</code></div></div><div class="rec-section"><h4>Certified forecast records (${escape(detail.forecast_records.length)})</h4>${recordsHtml(detail.forecast_records,"Forecast")}</div><div class="rec-section"><h4>Certified risk records (${escape(detail.risk_records.length)})</h4>${recordsHtml(detail.risk_records,"Risk")}</div>`;
  };

  const loadList=async()=>{
    if(!state.summary)return;
    try{
      state.busy=true;
      const container=byId("rec-results");if(container)container.innerHTML='<div class="empty">Loading certified recommendations…</div>';
      state.list=await api(`/v1/presentation/recommendation-list?${queryString()}`);
      renderList();
    }catch(error){const container=byId("rec-results");if(container)container.innerHTML=`<div class="rec-error">${escape(error.message)}</div>`}
    finally{state.busy=false;}
  };

  const loadDetail=async assetId=>{
    try{
      const container=byId("rec-detail");if(container)container.innerHTML='<div class="empty">Loading exact governed detail…</div>';
      state.detail=await api(`/v1/presentation/recommendation-detail?domain=${encodeURIComponent(state.domain)}&asset_id=${encodeURIComponent(assetId)}`);
      renderList();renderDetail();
    }catch(error){const container=byId("rec-detail");if(container)container.innerHTML=`<div class="rec-error">${escape(error.message)}</div>`}
  };

  const filtersChanged=()=>{state.query=byId("rec-search").value.trim();state.status=byId("rec-status").value;state.rankType=byId("rec-rank-type").value;state.hasForecast=triValue(byId("rec-has-forecast"));state.hasRisk=triValue(byId("rec-has-risk"));state.hasPrice=triValue(byId("rec-has-price"));state.manualCheck=triValue(byId("rec-manual-check"));state.offset=0;state.detail=null;loadList();renderDetail();};

  const bindControls=()=>{
    page.querySelectorAll("[data-rec-domain]").forEach(button=>button.addEventListener("click",()=>{state.domain=button.dataset.recDomain;state.query="";state.status="";state.rankType="";state.hasForecast="";state.hasRisk="";state.hasPrice="";state.manualCheck="";state.offset=0;state.detail=null;renderChrome();loadList();}));
    const search=byId("rec-search");let searchTimer=null;search.addEventListener("input",()=>{clearTimeout(searchTimer);searchTimer=setTimeout(filtersChanged,250)});
    ["rec-status","rec-rank-type","rec-has-forecast","rec-has-risk","rec-has-price","rec-manual-check"].forEach(id=>byId(id).addEventListener("change",filtersChanged));
    byId("rec-prev").addEventListener("click",()=>{state.offset=Math.max(0,state.offset-state.limit);loadList()});
    byId("rec-next").addEventListener("click",()=>{state.offset+=state.limit;loadList()});
  };

  const loadRecommendations=async()=>{
    if(!key())return;
    injectStyles();
    try{
      state.summary=await api("/v1/presentation/recommendation-summary");
      const domains=state.summary.domains||[];
      if(!domains.some(item=>item.domain_id===state.domain)&&domains.length)state.domain=domains[0].domain_id;
      renderChrome();
      await loadList();
    }catch(error){page.innerHTML=`<div class="page-heading"><div><span class="eyebrow">RECOMMENDATIONS</span><h2>Domain-native opportunities</h2></div><span class="page-note">REC-UI-1 · blocked</span></div><article class="panel governed-empty"><span class="empty-icon">!</span><h3>Recommendation authority is unavailable</h3><p>${escape(error.message)}</p></article>`;}
  };

  const authForm=byId("auth-form");
  const refresh=byId("refresh");
  if(authForm)authForm.addEventListener("submit",()=>setTimeout(loadRecommendations,0));
  if(refresh)refresh.addEventListener("click",()=>setTimeout(loadRecommendations,0));
  document.querySelectorAll('[data-page="recommendations"]').forEach(button=>button.addEventListener("click",()=>{if(key()&&!state.summary)loadRecommendations()}));
  if(key())loadRecommendations();
})();
