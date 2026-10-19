/* MTG singles: Commander decks and the binder, in the Treasury's counting house.
   Reads /v1/mtg-singles; imports Moxfield exports through /v1/mtg-singles/import (preview, then add);
   moves, sells, removes or re-values a card through /v1/mtg-singles/lots/{id}. */
(()=>{
"use strict";
const S={doc:null,loading:false,open:null,preview:null,act:null,msg:null,busy:false};
const byId=id=>document.getElementById(id);
const esc=v=>{const n=document.createElement("span");n.textContent=String(v??"");return n.innerHTML};
const num=v=>{if(v===null||v===undefined||v==="")return null;const n=Number(v);return Number.isFinite(n)?n:null};
const money=(v,d=2)=>{const n=num(v);return n===null?"\u2014":`${n<0?"\u2212":""}$${Math.abs(n).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d})}`};
const signed=v=>{const n=num(v);return n===null?"\u2014":`${n>=0?"+":"\u2212"}${money(Math.abs(n))}`};
const tone=v=>{const n=num(v);return n===null?"":n>=0?"positive":"negative"};
const FINISH={nonfoil:"",foil:"Foil",etched:"Etched"};
const key=()=>sessionStorage.getItem("uiip-dashboard-key")||"";
async function call(path,options={}){
  const r=await fetch(path,{...options,headers:{"X-API-Key":key(),"Accept":"application/json",...(options.headers||{})}});
  const body=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(body.error?.message||`Request failed (${r.status})`);
  return body;
}
const post=(path,body)=>call(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
const dayLabel=d=>/^\d{4}-\d{2}-\d{2}/.test(String(d||""))?new Date(`${String(d).slice(0,10)}T12:00:00Z`).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"}):"\u2014";

function changed(doc){S.doc=doc;document.dispatchEvent(new CustomEvent("uip:mtg-singles-changed",{detail:doc}));render()}
function load(){
  if(S.loading||!key())return;S.loading=true;
  call("/v1/mtg-singles").then(doc=>{S.loading=false;S.doc=doc;render()}).catch(error=>{S.loading=false;S.msg=["bad",`Singles could not be read: ${error.message}`];render()});
}

/* ---------------- pieces ---------------- */
function printing(c){const set=c.set_code?String(c.set_code).toUpperCase():"";return `${set&&c.collector_number?`${set} \u00b7 #${c.collector_number}`:set||"Printing not given"}${FINISH[c.finish]?` \u00b7 ${FINISH[c.finish]}`:""}`}
function cardsTable(rows,{actions}){
  return `<div class="table-wrap"><table class="singles-table"><thead><tr><th>Card</th><th>Qty</th><th>Price</th><th>Value</th><th>${actions?"Paid each":"Paid"}</th><th>Gain</th>${actions?"<th></th>":""}</tr></thead><tbody>${rows.map(c=>`<tr${S.act===c.lot_id?' class="is-picked"':""}><td><span class="position-name"><strong>${c.scryfall_uri?`<a href="${esc(c.scryfall_uri)}" target="_blank" rel="noopener noreferrer">${esc(c.name)}</a>`:esc(c.name)}</strong><small>${esc(printing(c))}${c.exact_printing?"":" \u00b7 printing not given (Scryfall default)"}</small></span></td><td>${esc(c.quantity)}</td><td>${c.value_source==="UNPRICED"?'<span class="negative">No price</span>':`${money(c.unit_value)}${c.value_source==="MANUAL"?"<small> your value</small>":""}`}</td><td>${money(c.value)}</td><td>${actions?`<span class="singles-paid"><input type="number" min="0" step="0.01" inputmode="decimal" data-paid-lot="${esc(c.lot_id)}" data-paid-was="${c.price_paid===null?"":esc(c.price_paid)}" value="${c.price_paid===null?"":esc(c.price_paid)}" aria-label="${esc(`Price paid each for ${c.name}`)}" placeholder="each"><label class="singles-est"><input type="checkbox" data-paid-est="${esc(c.lot_id)}" data-est-was="${c.paid_estimated?"1":""}"${c.paid_estimated||c.price_paid===null?" checked":""}> est.</label></span>`:c.paid===null?"\u2014":`${money(c.paid)}${c.paid_estimated?"<small> est.</small>":""}`}</td><td class="${tone(c.gain)}">${signed(c.gain)}</td>${actions?`<td><button type="button" class="secondary singles-act" data-singles-act="${esc(c.lot_id)}" aria-expanded="${S.act===c.lot_id}">Change</button></td>`:""}</tr>${actions&&S.act===c.lot_id?`<tr class="singles-act-row"><td colspan="7">${actionForm(c)}</td></tr>`:""}`).join("")}</tbody></table></div>`;
}
function deckOptions(selected,{withNew=true}={}){
  const decks=(S.doc?.decks||[]).map(d=>d.deck);if(!decks.includes("Binder"))decks.push("Binder");
  return `${decks.map(d=>`<option value="${esc(d)}"${d===selected?" selected":""}>${esc(d)}</option>`).join("")}${withNew?`<option value="__new"${selected==="__new"?" selected":""}>New deck\u2026</option>`:""}`;
}
function actionForm(c){
  return `<form class="transaction-form singles-act-form" data-singles-form="${esc(c.lot_id)}"><label>What<select data-sf="action"><option value="move">Move to another deck or the binder</option><option value="sell">Sold</option><option value="remove">Remove (traded, lost, given away)</option><option value="paid">Set the price paid</option><option value="value">Set my own value (no market price)</option></select></label><label>How many<input type="number" min="1" max="${esc(c.quantity)}" step="1" value="${esc(c.quantity)}" data-sf="quantity"></label><label data-sf-show="move">To<select data-sf="deck">${deckOptions(c.deck==="Binder"?"":"Binder")}</select></label><label data-sf-show="move" class="singles-newdeck" hidden>New deck name<input data-sf="new_deck" maxlength="80"></label><label data-sf-show="sell" hidden>Sold for, each (optional)<input type="number" min="0" step="0.01" data-sf="sold_price"></label><label data-sf-show="paid" hidden>Paid, each<input type="number" min="0" step="0.01" data-sf="price_paid" value="${c.price_paid===null?"":esc(c.price_paid)}"></label><label data-sf-show="paid" class="singles-check" hidden><input type="checkbox" data-sf="estimated"${c.paid_estimated?" checked":""}> It's an estimate</label><label data-sf-show="value" hidden>Value, each (blank = market price)<input type="number" min="0" step="0.01" data-sf="manual_value"></label><div class="wide transaction-actions"><button type="submit">Apply</button><button type="button" class="secondary" data-singles-close>Cancel</button></div></form>`;
}
function importForm(){
  const decks=S.doc?.decks||[];
  return `<form class="transaction-form singles-import" data-singles-import><label>Deck<select data-si="deck">${deckOptions(S.open||decks[0]?.deck||"__new")}</select></label><label class="singles-newdeck"${decks.length?" hidden":""}>New deck name<input data-si="new_deck" maxlength="80" placeholder="e.g. Atraxa superfriends"></label><label class="wide">Cards (Moxfield export: Export \u203a Text, or a CSV)<textarea data-si="text" rows="8" placeholder="1 Smothering Tithe (RNA) 22 *F* $18.50&#10;1 Sol Ring (C21) 263 ~$2.00&#10;1 Mana Crypt (2XM) 270"></textarea></label><label>Or a file<input type="file" accept=".txt,.csv,text/plain,text/csv" data-si="file"></label><fieldset class="wide singles-mode"><legend>This list is</legend><label class="singles-check"><input type="radio" name="singles-mode" value="add" data-si="mode" checked> New cards for the deck (an upgrade): add them</label><label class="singles-check"><input type="radio" name="singles-mode" value="match" data-si="mode"> The whole deck (a fresh Moxfield export): add what is new, take out what is gone</label><label class="singles-check"><input type="checkbox" data-si="cut_remove"> Cards taken out leave the collection (otherwise they go to the binder)</label></fieldset><label class="singles-check"><input type="checkbox" data-si="estimated"> Prices paid in this list are estimates</label><p class="wide muted singles-hint">Add a price paid at the end of a line: <code>$18.50</code>, or <code>~$18.50</code> for an estimate. *F* means foil and *E* etched. Lines without a set and number are priced at Scryfall's default printing.</p><div class="wide transaction-actions"><button type="button" class="secondary" data-singles-preview>Preview</button><button type="submit">Add to the deck</button><span class="form-message${S.msg?` ${S.msg[0]==="bad"?"bad":"good"}`:""}" role="status">${S.msg?esc(S.msg[1]):""}</span></div></form>`;
}
function previewBlock(){
  const p=S.preview;if(!p)return "";
  const total=p.cards.reduce((a,c)=>a+(num(c.value)||0),0);
  const warn=[p.not_found?.length?`No market price for: ${p.not_found.slice(0,12).join(", ")}${p.not_found.length>12?"\u2026":""}. You can set your own value after adding them.`:"",p.unread_lines?.length?`Could not read ${p.unread_lines.length} line${p.unread_lines.length===1?"":"s"}: ${p.unread_lines.slice(0,5).join(" | ")}`:"",p.price_error||""].filter(Boolean);
  const y=p.sync,names=list=>list.slice(0,10).map(x=>`${x.quantity>1?`${x.quantity} `:""}${x.name}`).join(", ")+(list.length>10?"\u2026":"");
  const sync=y?`<p class="governance-note singles-sync">${esc(`Matching ${y.deck} to this list: ${count(y.added)} to add${y.added.length?` (${names(y.added)})`:""}; ${count(y.cut)} to take out${y.cut.length?` (${names(y.cut)}), ${y.cut_to==="removed"?"leaving the collection":"into the binder"}`:""}; ${y.kept} already there${y.repriced?`; ${y.repriced} get the price paid from the list`:""}.`)}</p>`:"";
  return `<div class="singles-preview"><h4>Preview \u00b7 ${esc(p.card_count)} cards for ${esc(p.deck)} \u00b7 worth ${money(total)}</h4>${sync}${warn.map(w=>`<p class="governance-note">${esc(w)}</p>`).join("")}${cardsTable(p.cards,{actions:false})}</div>`;
}
function render(){
  const page=byId("portfolio");if(!page)return;
  let panel=page.querySelector(".singles-panel");
  if(!panel){
    panel=document.createElement("section");panel.className="panel singles-panel";
    const after=page.querySelector(".manual-holdings-panel")||page.querySelector(".retirement-accounts-panel");
    if(after)after.insertAdjacentElement("afterend",panel);else page.appendChild(panel);
    bind(panel);
  }
  const d=S.doc;
  if(!d){panel.innerHTML=`<div class="section-title"><div><h3>MTG singles \u00b7 Commander decks</h3></div></div><p class="governance-note">${S.msg?esc(S.msg[1]):"Loading\u2026"}</p>`;load();return}
  const decks=d.decks||[];
  const deckRows=decks.map(g=>`<tr${S.open===g.deck?' class="is-picked"':""}><td><strong>${esc(g.deck)}</strong></td><td>${esc(g.cards)}</td><td>${money(g.value)}</td><td>${num(g.paid_known)?money(g.paid_known):"\u2014"}${g.estimated_paid?"<small> incl. estimates</small>":""}</td><td class="${tone(num(g.paid_known)?g.gain_known:null)}">${num(g.paid_known)?signed(g.gain_known):"\u2014"}</td><td>${g.unpriced?`<span class="negative">${esc(g.unpriced)}</span>`:"0"}</td><td><button type="button" class="secondary" data-singles-open="${esc(g.deck)}" aria-expanded="${S.open===g.deck}">${S.open===g.deck?"Close":"Open"}</button></td></tr>`).join("");
  const open=S.open?d.lots.filter(c=>c.deck===S.open):[];
  const cards=`<div class="portfolio-cards"><article><span>Worth today</span><strong>${money(d.value)}</strong><small>${esc(d.card_count)} cards${d.prices_as_of?` \u00b7 prices ${esc(dayLabel(d.prices_as_of))}`:""}</small></article><article><span>Price paid (where entered)</span><strong>${money(d.paid_known)}</strong><small>cards without one count their value as paid</small></article><article><span>Gain on cards with a price paid</span><strong class="${tone(d.gain_known)}">${signed(d.gain_known)}</strong><small>estimates included</small></article><article><span>After about 12% selling costs</span><strong>${money(d.after_selling_costs)}</strong><small>what the Homestead counts toward the house</small></article></div>`;
  panel.innerHTML=`<div class="section-title"><div><h3>MTG singles \u00b7 Commander decks</h3><span>Each exact printing at today's TCGplayer market price (Scryfall), counted in the Treasury and net worth</span></div><span><button type="button" class="secondary" data-singles-refresh${S.busy?" disabled":""}>Refresh prices</button></span></div>${d.card_count?cards:`<p class="governance-note">No singles yet. Build each deck in Moxfield with the printings you own, then Export \u203a Text (or CSV) and paste it below.</p>`}${decks.length?`<div class="table-wrap"><table class="singles-table"><thead><tr><th>Deck</th><th>Cards</th><th>Value</th><th>Paid</th><th>Gain</th><th>No price</th><th></th></tr></thead><tbody>${deckRows}</tbody></table></div>`:""}${S.open&&open.length?`<h4 class="singles-deck-title">${esc(S.open)} \u00b7 ${open.reduce((a,c)=>a+c.quantity,0)} cards</h4>${cardsTable(open.slice().sort((a,b)=>(num(b.value)||0)-(num(a.value)||0)),{actions:true})}<div class="transaction-actions singles-paid-actions"><button type="button" data-singles-paid-save>Save prices paid</button><span class="muted">Type what you paid for each copy; leave a box empty if you don't know. Ticked "est." marks it as an estimate.</span></div>`:""}<h4 class="singles-deck-title">Add cards \u00b7 a new deck or an upgrade</h4>${importForm()}${previewBlock()}`;
}

/* ---------------- actions ---------------- */
const count=list=>(list||[]).reduce((a,x)=>a+(x.quantity||0),0);
function readImport(form){
  const sel=form.querySelector('[data-si="deck"]').value;
  const deck=sel==="__new"?form.querySelector('[data-si="new_deck"]').value.trim():sel;
  const mode=form.querySelector('[data-si="mode"]:checked')?.value||"add";
  return {deck,text:form.querySelector('[data-si="text"]').value,estimated:form.querySelector('[data-si="estimated"]').checked,mode,cut_to:form.querySelector('[data-si="cut_remove"]').checked?"remove":"binder"};
}
async function runImport(form,save){
  const body=readImport(form);
  if(!body.deck){S.msg=["bad","Name the deck first."];render();return}
  if(!body.text.trim()){S.msg=["bad","Paste the cards or choose a file."];render();return}
  S.msg=["ok",save?"Adding the cards\u2026":"Pricing the list\u2026"];render();
  try{
    const out=await post("/v1/mtg-singles/import",{...body,save});
    if(save){S.preview=null;S.open=out.deck;const y=out.sync;S.msg=["ok",y?`${out.deck} now matches the list: ${count(y.added)} added, ${count(y.cut)} taken out${y.cut.length?` (${y.cut_to==="removed"?"left the collection":"moved to the binder"})`:""}, ${y.kept} unchanged.`:`Added ${out.card_count} cards to ${out.deck}.${out.not_found.length?` ${out.not_found.length} have no market price yet.`:""}`];changed(out.collection)}
    else{S.preview=out;S.msg=null;render();const f=byId("portfolio")?.querySelector("[data-singles-import] [data-si=text]");if(f)f.value=body.text}
  }catch(error){S.msg=["bad",error.message];render()}
}
function bind(panel){
  panel.addEventListener("click",async event=>{
    const t=event.target.closest("button");if(!t||!panel.contains(t))return;
    if(t.dataset.singlesOpen!==undefined){S.open=S.open===t.dataset.singlesOpen?null:t.dataset.singlesOpen;S.act=null;render();return}
    if(t.dataset.singlesAct){S.act=S.act===t.dataset.singlesAct?null:t.dataset.singlesAct;render();return}
    if(t.hasAttribute("data-singles-close")){S.act=null;render();return}
    if(t.hasAttribute("data-singles-preview")){runImport(t.closest("form"),false);return}
    if(t.hasAttribute("data-singles-paid-save")){
      const updates=[];
      panel.querySelectorAll("[data-paid-lot]").forEach(el=>{const id=el.dataset.paidLot;const est=panel.querySelector(`[data-paid-est="${CSS.escape(id)}"]`);const value=el.value.trim(),was=el.dataset.paidWas||"";const estimated=!!est?.checked&&value!=="";const estWas=!!(est?.dataset.estWas)&&was!=="";if(value===was&&estimated===estWas)return;updates.push({lot_id:id,price_paid:value,estimated})});
      if(!updates.length){S.msg=["ok","No prices paid changed."];render();return}
      try{const out=await post("/v1/mtg-singles/paid",{updates});S.msg=["ok",`Saved ${out.updated} price${out.updated===1?"":"s"} paid.`];changed(out)}catch(error){S.msg=["bad",error.message];render()}
      return}
    if(t.hasAttribute("data-singles-refresh")){S.busy=true;render();try{const out=await post("/v1/mtg-singles/refresh-prices",{});S.busy=false;S.msg=["ok",`Prices refreshed: ${out.refresh.priced} of ${out.refresh.printings} printings priced.`];changed(out)}catch(error){S.busy=false;S.msg=["bad",error.message];render()}}
  });
  panel.addEventListener("change",event=>{
    const el=event.target;
    if(el.matches('[data-si="deck"],[data-sf="deck"]')){const box=el.closest("form").querySelector(".singles-newdeck");if(box)box.hidden=el.value!=="__new"}
    if(el.matches('[data-sf="action"]')){const f=el.closest("form");f.querySelectorAll("[data-sf-show]").forEach(x=>{x.hidden=x.dataset.sfShow!==el.value||(x.classList.contains("singles-newdeck")&&f.querySelector('[data-sf="deck"]').value!=="__new")})}
    if(el.matches('[data-si="file"]')&&el.files?.[0]){const reader=new FileReader();reader.onload=()=>{const box=el.closest("form").querySelector('[data-si="text"]');box.value=String(reader.result||"")};reader.readAsText(el.files[0])}
  });
  panel.addEventListener("submit",async event=>{
    event.preventDefault();const form=event.target;
    if(form.hasAttribute("data-singles-import")){runImport(form,true);return}
    const id=form.dataset.singlesForm;if(!id)return;
    const v=k=>form.querySelector(`[data-sf="${k}"]`);
    const action=v("action").value,body={action,quantity:Number(v("quantity").value||1)};
    if(action==="move"){body.deck=v("deck").value==="__new"?v("new_deck").value.trim():v("deck").value;if(!body.deck){S.msg=["bad","Name the new deck."];render();return}}
    if(action==="sell")body.sold_price=v("sold_price").value;
    if(action==="paid"){body.price_paid=v("price_paid").value;body.estimated=v("estimated").checked}
    if(action==="value")body.manual_value=v("manual_value").value;
    try{const doc=await post(`/v1/mtg-singles/lots/${encodeURIComponent(id)}`,body);S.act=null;S.msg=["ok","Saved."];changed(doc)}catch(error){S.msg=["bad",error.message];render()}
  });
}
function watch(){
  const page=byId("portfolio");if(!page)return;
  let queued=false;
  new MutationObserver(()=>{if(queued||page.querySelector(".singles-panel"))return;queued=true;queueMicrotask(()=>{queued=false;if(!page.querySelector(".singles-panel")&&page.querySelector(".manual-holdings-panel,.retirement-accounts-panel"))try{render()}catch(error){console.error("[singles]",error)}})}).observe(page,{childList:true,subtree:true});
  document.addEventListener("uip:home-rendered",event=>{const doc=event.detail?.mtgSingles;if(doc&&!S.doc){S.doc=doc}if(page.querySelector(".manual-holdings-panel,.retirement-accounts-panel"))render()});
  document.addEventListener("click",event=>{if(!event.target.closest(".singles-jump"))return;const panel=page.querySelector(".singles-panel");if(!panel)return;const details=panel.closest("details");if(details)details.open=true;panel.scrollIntoView({behavior:"smooth",block:"start"})});
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",watch);else watch();
window.UIPSingles={state:S,render,load};
})();
