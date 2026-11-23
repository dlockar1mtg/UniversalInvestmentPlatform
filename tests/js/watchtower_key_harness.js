// Used by tests/presentation/test_watchtower_waits_for_key.py. Synthetic key only.
// Drive watchtower.js with a fake DOM: open on #watchtower with no key, then enter the key and navigate.
const fs = require("fs");
const store = {}; const listeners = {}; let fetches = 0;
const page = { appendChild(v){ this.child = v; } };
const view = { id: "rpg-watchtower", innerHTML: "", addEventListener(){} };
global.sessionStorage = { getItem: k => store[k] ?? null };
global.location = { hash: "#watchtower" };
global.window = { UIPRealm: {} };
global.document = {
  readyState: "complete",
  getElementById: id => id === "watchtower" ? page : (id === "rpg-watchtower" ? (page.child || null) : null),
  createElement: tag => tag === "span" ? { set textContent(v){ this.innerHTML = v; }, innerHTML: "" } : view,
  addEventListener: (t, f) => { (listeners[t] = listeners[t] || []).push(f); },
};
global.fetch = async () => { fetches++; const ok = !!store["uiip-dashboard-key"];
  return { ok, status: ok ? 200 : 401, json: async () => ok ? { available: false } : { error: { message: "valid credentials are required" } } }; };
const src = fs.readFileSync(process.argv[2], "utf8");
new Function("byId", "esc", src)(id => document.getElementById(id), s => String(s));
const tick = () => new Promise(r => setTimeout(r, 5));
(async () => {
  await tick(); await tick();
  console.log("no key:", JSON.stringify(view.innerHTML.slice(-80)), "fetches", fetches);
  store["uiip-dashboard-key"] = "synthetic";
  const click = { target: { closest: sel => sel.includes("watchtower") ? {} : null } };
  listeners.click.forEach(f => f(click)); await tick(); await tick(); await tick();
  console.log("after key + nav:", JSON.stringify(view.innerHTML.slice(-120)), "fetches", fetches);
})();
