// Used by tests/delivery/test_treasury_sealed_in_boxes.py. Synthetic holdings only.
// Runs the Treasury's inventoryItems() on a portfolio with a certified Collector box, a Secret Lair,
// an ETF and two sealed MTG manual holdings, and prints the resulting tiles as JSON.
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const start = src.indexOf("function inventoryItems(d){");
const end = src.indexOf("function guildNote(h){");
const body = src.slice(start, end);
const num = v => (v === null || v === undefined || v === "" || isNaN(Number(v))) ? null : Number(v);
const qty = v => String(num(v) ?? "");
const make = new Function("num", "qty", "dayLabel", "assetLabel", "guildNote", "CALL_TEXT", "state", body + "\nreturn inventoryItems;");
const inventoryItems = make(num, qty, () => "Nov 23", (d, id) => id, () => "note", {}, {});
const d = {
  portfolio: { positions: [
    { domain_id: "mtg", asset_id: "COLLECTOR_V1|C-1", asset_subclass: "COLLECTOR_BOOSTER", asset_name: "Test Set Collector Booster Display", quantity: "2", cost_basis: "600", market_value: "640", recommendation: "HOLD" },
    { domain_id: "mtg", asset_id: "SECRET_LAIR_V1_1|SL-1", asset_subclass: "SECRET_LAIR", asset_name: "Test Lair", quantity: "1", cost_basis: "40", market_value: "45" },
  ] },
  manualHoldings: { mtg_sealed_value: "560", items: [
    { asset_type: "ETF", symbol: "VTEST", asset_name: "Test ETF", shares: "3", cost_basis: "300", current_value: "310", valuation_source: "ETF_PACKAGE_CLOSE" },
    { asset_type: "MTG_SEALED", symbol: "111", tcgplayer_name: "Test Set - Play Booster Display", shares: "5", cost_basis: "500", current_value: "480", valuation_source: "TCGPLAYER_MARKET" },
    { asset_type: "MTG_SEALED", symbol: "222", asset_name: "Test Starter Kit", shares: "1", cost_basis: "20", current_value: "80", valuation_source: "TCGPLAYER_MARKET" },
  ] },
};
const out = inventoryItems(d).map(i => ({ symbol: i.symbol, kind: i.kind, count: i.count, held: i.held, paid: i.paid, worth: i.worth, ledger: i.ledger && i.ledger[1], members: (i.members || []).map(m => m.name) }));
console.log(JSON.stringify(out));
