(()=>{
  const byId=id=>document.getElementById(id);
  const domainInput=byId("txn-domain");
  const assetInput=byId("txn-asset");
  const form=byId("transaction-form");
  const message=byId("txn-form-message");
  const authForm=byId("auth-form");
  const refreshButton=byId("refresh");
  if(!domainInput||!assetInput||!form)return;

  const credentialKey="uiip-dashboard-key";
  const domainSelect=document.createElement("select");
  domainSelect.id="txn-domain";
  domainSelect.required=true;
  domainSelect.innerHTML='<option value="">Connect to load certified domains</option>';
  domainInput.replaceWith(domainSelect);

  const dataList=document.createElement("datalist");
  dataList.id="txn-asset-options";
  assetInput.setAttribute("list",dataList.id);
  assetInput.setAttribute("autocomplete","off");
  assetInput.placeholder="Type to search the certified asset catalog";
  assetInput.insertAdjacentElement("afterend",dataList);

  let matches=new Map();
  let searchTimer=null;
  let searchGeneration=0;

  const currentKey=()=>sessionStorage.getItem(credentialKey)||"";
  const api=async path=>{
    const key=currentKey();
    if(!key)throw new Error("Connect to UIP before loading certified domains.");
    const response=await fetch(path,{headers:{"X-API-Key":key,"Accept":"application/json"}});
    const body=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(body.error?.message||`Request failed (${response.status})`);
    return body;
  };

  const displayLabel=item=>{
    const symbol=item.asset_symbol?` (${item.asset_symbol})`:"";
    const subtype=item.asset_subclass?` · ${item.asset_subclass}`:"";
    return `${item.asset_name||item.asset_id}${symbol}${subtype} · ${item.asset_id}`;
  };

  const clearAssets=()=>{
    matches=new Map();
    dataList.innerHTML="";
    assetInput.value="";
    assetInput.dataset.assetId="";
  };

  const loadDomains=async()=>{
    if(!currentKey()){
      domainSelect.innerHTML='<option value="">Connect to load certified domains</option>';
      return;
    }
    domainSelect.innerHTML='<option value="">Loading certified domains…</option>';
    try{
      const document=await api("/v1/presentation/domains");
      const domains=document.items||[];
      if(!domains.length)throw new Error("No certified asset domains are active.");
      domainSelect.innerHTML='<option value="">Select certified domain</option>'+domains.map(item=>`<option value="${String(item.domain_id).replace(/"/g,"&quot;")}">${String(item.domain_id).toUpperCase()}</option>`).join("");
      message.className="form-message";
      if(message.textContent.includes("domain")||message.textContent.includes("Connect to UIP"))message.textContent="";
    }catch(error){
      domainSelect.innerHTML='<option value="">Certified domains unavailable</option>';
      message.className="form-message bad";
      message.textContent=error.message;
    }
  };

  const searchAssets=async()=>{
    const domain=domainSelect.value;
    const query=assetInput.value.trim();
    const exactExisting=matches.get(query);
    if(exactExisting&&String(exactExisting.domain_id)===domain){
      assetInput.dataset.assetId=String(exactExisting.asset_id);
      return;
    }
    const generation=++searchGeneration;
    assetInput.dataset.assetId="";
    if(!domain||query.length<1){dataList.innerHTML="";matches=new Map();return;}
    try{
      const document=await api(`/v1/presentation/assets?domain=${encodeURIComponent(domain)}&query=${encodeURIComponent(query)}&limit=50`);
      if(generation!==searchGeneration)return;
      const next=new Map();
      dataList.innerHTML=(document.items||[]).map(item=>{
        const label=displayLabel(item);
        next.set(label,item);
        next.set(String(item.asset_id),item);
        return `<option value="${label.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}"></option>`;
      }).join("");
      matches=next;
      const exact=matches.get(assetInput.value.trim());
      assetInput.dataset.assetId=exact?String(exact.asset_id):"";
    }catch(error){
      if(generation!==searchGeneration)return;
      dataList.innerHTML="";
      matches=new Map();
      message.className="form-message bad";
      message.textContent=error.message;
    }
  };

  domainSelect.addEventListener("change",()=>{
    clearAssets();
    message.className="form-message";
    message.textContent=domainSelect.value?"Type part of the governed asset name, symbol, or ID and choose an exact match.":"";
  });

  assetInput.addEventListener("input",()=>{
    const exact=matches.get(assetInput.value.trim());
    clearTimeout(searchTimer);
    if(exact&&String(exact.domain_id)===domainSelect.value){
      assetInput.dataset.assetId=String(exact.asset_id);
      message.className="form-message";
      message.textContent="Governed asset selected.";
      return;
    }
    assetInput.dataset.assetId="";
    searchTimer=setTimeout(searchAssets,180);
  });

  assetInput.addEventListener("change",()=>{
    const exact=matches.get(assetInput.value.trim());
    assetInput.dataset.assetId=exact?String(exact.asset_id):"";
  });

  document.addEventListener("submit",event=>{
    if(event.target!==form)return;
    const selected=matches.get(assetInput.value.trim());
    if(!domainSelect.value){
      event.preventDefault();
      event.stopImmediatePropagation();
      message.className="form-message bad";
      message.textContent="Select a certified domain.";
      return;
    }
    if(!selected||String(selected.domain_id)!==domainSelect.value||assetInput.dataset.assetId!==String(selected.asset_id)){
      event.preventDefault();
      event.stopImmediatePropagation();
      message.className="form-message bad";
      message.textContent="Choose an exact governed asset from the certified search results.";
      return;
    }
    clearTimeout(searchTimer);
    const visibleLabel=assetInput.value;
    const canonicalAssetId=String(selected.asset_id);
    assetInput.value=canonicalAssetId;
    assetInput.dataset.assetId=canonicalAssetId;
    queueMicrotask(()=>{if(assetInput.value===canonicalAssetId)assetInput.value=visibleLabel;});
  },true);

  if(authForm)authForm.addEventListener("submit",()=>setTimeout(loadDomains,0));
  if(refreshButton)refreshButton.addEventListener("click",()=>setTimeout(loadDomains,0));
  loadDomains();
})();
