/* Tests for the browser save schema probe. No live network or credentials. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.resolve(__dirname, "../../tools/client/planets_nu_save_schema_probe_v1.js"), "utf8"
);
const syntheticSecrets = [
  "MY_SECRET_API_KEY_XYZ", "MY_SECRET_SAVEKEY_XYZ",
  "PRIVATE_CARGO_VALUE_12345", "MY_PLAYER_USERNAME_SECRET",
  "THIS_IS_A_PRIVATE_CARGO_NOTE", "MY_SESSION_COOKIE_ABC"
];

class FakeXHR {
  constructor() {
    this.status = 200;
    this.responseType = "";
    this.listeners = new Map();
    this.responseText = JSON.stringify({
      success: true, savekey: syntheticSecrets[1], note: syntheticSecrets[4],
      data: {planets: [{supplies: 7654321, hidden: syntheticSecrets[2]}]}
    });
  }
  open(method, url) { this.method = method; this.url = url; }
  addEventListener(event, cb) { this.listeners.set(event, cb); }
  send(body) {
    this.sent = body; this.listeners.get("loadend")?.();
    return "ORIGINAL_SEND_RESULT";
  }
}
let requests = 0;
const originalFetch = async function () {
  requests++;
  return {
    status: 200,
    clone() {
      return {text: async () => JSON.stringify({
        success: false, error: "PRIVATE_RESPONSE_DO_NOT_LOG",
        ships: [{supplies: 987654321, password: syntheticSecrets[0]}]
      })};
    }
  };
};
const infoLog = [];
const browser = {
  location: {href: "https://planets.nu/#/game"},
  URLSearchParams, FormData: global.FormData,
  XMLHttpRequest: FakeXHR, fetch: originalFetch,
  console: {info: (...args) => infoLog.push(args)}
};
const initialXHRSend = FakeXHR.prototype.send;
const initialXHROpen = FakeXHR.prototype.open;
const context = {window: browser, URL, URLSearchParams, FormData: global.FormData};
vm.runInNewContext(source, context);
const probe = browser.__planetsM2SaveSchemaProbeV1;
assert.ok(probe);
assert.throws(() => vm.runInNewContext(source, context), /already installed/);
assert.equal(infoLog.length, 1);
assert.doesNotMatch(JSON.stringify(infoLog), /SECRET/);

// Ignore unrelated traffic by exact URL path, not a substring.
const ignored = new FakeXHR();
ignored.open("POST", "https://api.planets.nu/game/save-not-really");
ignored.send("apikey=MY_SECRET_API_KEY_XYZ");
assert.equal(probe.report().observed_save_calls, 0);
assert.equal(probe.report().diagnostics.planets_requests_total, 1);
assert.equal(probe.report().diagnostics.planets_post_requests, 1);
assert.equal(probe.report().diagnostics.route_categories.game_other, 1);

// Near-save routes and turnready should be counted in broad diagnostics,
// but must NEVER have body/response contents copied into public events.
const candidate = new FakeXHR();
candidate.open("POST", "https://api.planets.nu/game/savegame?savekey=" + syntheticSecrets[1]);
candidate.send("apikey=" + syntheticSecrets[0] + "&privatevalue=" + syntheticSecrets[2]);
const turnready = new FakeXHR();
turnready.open("POST", "https://api.planets.nu/game/turnready?apikey=" + syntheticSecrets[0]);
turnready.send("gameid=12345678&private=" + syntheticSecrets[3]);
const account = new FakeXHR();
account.open("POST", "https://api.planets.nu/account/login?token=" + syntheticSecrets[5]);
account.send("password=" + syntheticSecrets[0]);
assert.equal(probe.report().observed_save_calls, 0);
assert.equal(probe.report().diagnostics.route_categories.game_save_candidate, 1);
assert.equal(probe.report().diagnostics.route_categories.game_turnready, 1);
assert.equal(probe.report().diagnostics.route_categories.account_other, 1);
assert.equal(probe.report().diagnostics.planets_post_requests, 4);

const xhr = new FakeXHR();
xhr.open("POST", "https://api.planets.nu/game/save?apikey=MY_SECRET_API_KEY_XYZ");
const payload = JSON.stringify({
  ships: [{
    id: 12, supplies: 987654321, clans: 1024, note: syntheticSecrets[4],
    friendlycode: "MY_PRIVATE_FRIENDLY_CODE", targetx: 999999
  }],
  planets: [{id: 42, megacredits: 9999999}],
  apikey: syntheticSecrets[0], savekey: syntheticSecrets[1]
});
assert.equal(xhr.send(
  "apikey=" + encodeURIComponent(syntheticSecrets[0]) +
  "&data=" + encodeURIComponent(payload) +
  "&gameid=203343"
), "ORIGINAL_SEND_RESULT");
assert.equal(probe.report().observed_save_calls, 1);
assert.equal(probe.report().events[0].transport, "xhr");
assert.equal(probe.report().events[0].response.reported_success_flag_not_server_acceptance_proof, true);

(async () => {
  const response = await browser.fetch("https://api.planets.nu/game/save", {
    method: "POST",
    body: new URLSearchParams({playerid: "9", password: syntheticSecrets[0]})
  });
  assert.equal(response.status, 200);
  await new Promise(resolve => setImmediate(resolve));
  const report = probe.report();
  assert.equal(requests, 1, "no additional API calls");
  assert.equal(report.observed_save_calls, 2);
  assert.equal(report.diagnostics.planets_requests_total, 6);
  assert.equal(report.diagnostics.planets_post_requests, 6);
  assert.equal(report.diagnostics.xhr_requests, 5);
  assert.equal(report.diagnostics.fetch_requests, 1);
  assert.equal(report.diagnostics.route_categories.game_save_exact, 2);
  assert.equal(report.diagnostics.route_categories.game_save_candidate, 1);
  assert.equal(report.diagnostics.route_categories.game_turnready, 1);
  assert.equal(report.diagnostics.route_categories.game_other, 1);
  assert.equal(report.diagnostics.route_categories.account_other, 1);
  assert.equal(report.diagnostics.route_discovery_only_not_server_ack, true);
  assert.equal(report.status, "SCHEMA_ONLY_NOT_SERVER_ORDER_ACK_OR_NUHOST_VERIFIED");
  assert.equal(report.values_logged, false);
  assert.equal(report.credentials_logged, false);
  assert.equal(report.submitted_order_mapping_verified, false);
  assert.equal(report.server_order_acknowledgement_verified, false);
  assert.equal(report.events[1].response.reported_success_flag_not_server_acceptance_proof, false);
  assert.equal(report.events[0].request_schema.type, "object");
  const text = JSON.stringify(report);
  for (const value of syntheticSecrets) {
    assert.ok(!text.includes(value), "secret value must not be included");
  }
  for (const value of ["987654321", "7654321", "9999999", "203343", "MY_PRIVATE_FRIENDLY_CODE"]) {
    assert.ok(!text.includes(value), "game or cargo value must not be included");
  }
  assert.ok(text.includes("supplies"), "schema should contain allowlisted mechanic names");
  assert.ok(!text.includes("PRIVATE_RESPONSE_DO_NOT_LOG"));
  assert.ok(!text.includes("note"), "unlisted keys must not be emitted");
  assert.ok(!text.includes("savekey"), "credential field name should not be emitted");
  assert.ok(!text.includes("apikey"), "credential field name should not be emitted");
  assert.ok(!text.includes("password"), "credential field name should not be emitted");
  assert.ok(!text.includes("/game/savegame"), "URL paths must not be emitted");
  assert.ok(!text.includes("gameid=12345678"), "URL query strings must not be emitted");

  // Reports must be detached: client mutation does not rewrite internal counters.
  const copy = probe.report();
  copy.diagnostics.route_categories.game_save_exact = 9999;
  assert.equal(probe.report().diagnostics.route_categories.game_save_exact, 2);

  probe.stop();
  assert.equal(browser.fetch, originalFetch);
  assert.equal(FakeXHR.prototype.open, initialXHROpen);
  assert.equal(FakeXHR.prototype.send, initialXHRSend);
  assert.equal(browser.__planetsM2SaveSchemaProbeV1, undefined);
  assert.equal(browser.fetch !== originalFetch, false);
  console.log("M2 passive save-schema probe: no secret leakage, no extra requests, clean restore");
})().catch(err => {console.error(err); process.exitCode = 1});
