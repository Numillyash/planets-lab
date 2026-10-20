"use strict";
/* Fully fake XHR/fetch: no browser, real Planets.nu requests or credentials. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.resolve(
  __dirname, "../../tools/client/planets_nu_save_ready_metadata_v1.js"
), "utf8");
const SECRET = "FAKE_BEARER_TOKEN_DO_NOT_EMIT";
const STRATEGY = "FICTIONAL_GAME_STRATEGY_SHOULD_NOT_BE_CAPTURED";
let fetchCalls = 0, xhrSends = 0, tick = 0;
let deferredSaveResolve;
let slowSaveNext = false;
function response(status, success) {
  return {
    status,
    clone() {
      return {text: async () => JSON.stringify({
        success, savekey: SECRET, gameid: 8771, notes: STRATEGY
      })};
    }
  };
}
function fetch(url) {
  fetchCalls++;
  if (slowSaveNext && /\/game\/save/.test(String(url))) {
    slowSaveNext = false;
    return new Promise(resolve => {deferredSaveResolve = () => resolve(response(200, true));});
  }
  return Promise.resolve(response(200, true));
}
class XHR {
  constructor() {
    this.status = 200;
    this.responseType = "";
    this.responseText = JSON.stringify({
      success: true, savekey: SECRET, notes: STRATEGY,
    });
    this.callbacks = new Map();
  }
  open(method, url) {this.opened = {method, url}; return "ORIGINAL_OPEN";}
  addEventListener(name, handler) {
    if (!this.callbacks.has(name)) this.callbacks.set(name, []);
    this.callbacks.get(name).push(handler);
  }
  fire(name) {
    for (const handler of this.callbacks.get(name) || []) handler();
  }
  send(body) {
    this.nativeBody = body;
    xhrSends++;
    this.fire("loadend");
    return "ORIGINAL_SEND";
  }
}
const originalOpen = XHR.prototype.open, originalSend = XHR.prototype.send;
const root = {
  location: {href: "https://planets.nu/#/game"},
  XMLHttpRequest: XHR, fetch, URL, performance: {now: () => ++tick},
  console: {info: () => {}}
};
vm.runInNewContext(source, {window: root, URL, Promise});
const observer = root.__planetsM2SaveReadyMetadataV1;
assert.ok(observer);
assert.equal(xhrSends, 0);
assert.equal(fetchCalls, 0);

function sendXHR(path, {status=200, success=true}={}) {
  const x = new XHR();
  assert.equal(x.open("POST", "https://api.planets.nu" + path), "ORIGINAL_OPEN");
  x.status = status;
  x.responseText = JSON.stringify({success, credentials: SECRET, notes: STRATEGY});
  assert.equal(x.send("apiKey=" + SECRET + "&privateOrders=" + STRATEGY), "ORIGINAL_SEND");
}
function assertPrivateAbsent() {
  const data = JSON.stringify(observer.report()) + JSON.stringify(observer.trace());
  for (const value of [SECRET, STRATEGY, "8771", "privateOrders", "credentials",
    "gameid", "savekey", "apiKey=", "api.planets.nu"]) {
    assert.ok(!data.includes(value), "sensitive input leaked: " + value);
  }
}
sendXHR("/game/turnready");
sendXHR("/game/save?savekey=" + SECRET);
sendXHR("/game/turnready?savekey=" + SECRET);
let result = observer.report();
assert.equal(result.total_save_calls, 1);
assert.equal(result.total_turnready_calls, 2);
assert.equal(result.candidate_ordered_client_sequences_not_host_verified, 1);
assert.equal(result.ambiguous_or_unconfirmed_ready_events, 1);
assert.equal(result.client_visible_save_success_events, 1);
assert.equal(result.client_visible_ready_success_events, 2);
assert.equal(result.independently_witnessed_host_start, false);
assert.equal(result.verified_server_order_acceptance, false);
assert.equal(result.nuhost_execution_verified, false);
assertPrivateAbsent();

// Request failure and app failure must never turn into inferred success.
sendXHR("/game/save", {status: 500});
sendXHR("/game/turnready", {status: 200});
result = observer.report();
assert.equal(result.candidate_ordered_client_sequences_not_host_verified, 1);
assert.equal(result.ambiguous_or_unconfirmed_ready_events, 2);
sendXHR("/game/save", {success: false});
sendXHR("/game/turnready");
assert.equal(observer.report().candidate_ordered_client_sequences_not_host_verified, 1);

(async () => {
  slowSaveNext = true;
  const pending = root.fetch("https://api.planets.nu/game/save", {
    method: "POST", body: "token=" + SECRET + "&notes=" + STRATEGY
  });
  const ready = root.fetch("https://api.planets.nu/game/turnready", {method: "POST"});
  await ready;
  await new Promise(resolve => setImmediate(resolve));
  deferredSaveResolve();
  await pending;
  await new Promise(resolve => setImmediate(resolve));
  result = observer.report();
  assert.equal(result.candidate_ordered_client_sequences_not_host_verified, 1);
  assert.ok(result.ambiguous_or_unconfirmed_ready_events >= 4);
  assert.equal(result.pending_events, 0);

  // Ignore foreign origin even if path matches, no forwarding changes.
  const oldSaveCount = observer.report().total_save_calls;
  sendXHR("/irrelevant"); // non-target API path
  await root.fetch("https://evil.example.com/game/save", {method: "POST"});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(observer.report().total_save_calls, oldSaveCount);

  // Defensive snapshots: detached objects cannot edit internal probe.
  const trace = observer.trace();
  trace.events[0].route = "hijacked";
  assert.equal(observer.trace().events[0].route, "turnready");
  assertPrivateAbsent();

  // Bounded chronology must not claim any full sequence after eviction.
  for (let i=0;i<80;i++) sendXHR("/game/save");
  sendXHR("/game/turnready");
  result = observer.report();
  assert.equal(result.retained_metadata_events, 64);
  assert.ok(result.dropped_metadata_events > 0);
  assert.equal(result.candidate_ordered_client_sequences_not_host_verified, 0);
  assert.equal(result.no_extra_network_requests, true);
  assert.equal(xhrSends, 89); // seven initial, one ignored, 80 saves, one final ready
  assertPrivateAbsent();

  observer.stop();
  assert.equal(root.fetch, fetch);
  assert.equal(XHR.prototype.open, originalOpen);
  assert.equal(XHR.prototype.send, originalSend);
  assert.equal(root.__planetsM2SaveReadyMetadataV1, undefined);
  console.log("M2 metadata-only save/ready chronology synthetic browser tests: OK");
})().catch(err => {console.error(err); process.exitCode = 1});
