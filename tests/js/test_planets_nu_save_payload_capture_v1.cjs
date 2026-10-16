"use strict";
/*
 * Synthetic browser tests for M2 real-payload observation.
 * Absolutely no live Planets.nu requests, auth data or game accounts.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(
  path.resolve(__dirname, "../../tools/client/planets_nu_save_payload_capture_v1.js"), "utf8"
);
const SECRET = "TEST_SECRET_API_KEY_NEVER_EXPOSE_ME";
const SAVE = "TEST_SECRET_SAVEKEY_NEVER_EXPOSE_ME";
const COOKIE = "TEST_SESSION_TOKEN_NEVER_EXPOSE_ME";
const RAW_NOTES = "Own-game strategic details may be included by authorization";
let sends = 0;
let fetchCalls = 0;
class XHR {
  constructor() {
    this.status = 200;
    this.responseType = "";
    this.responseText = JSON.stringify({
      success: true, result: 22,
      savekey: SAVE,
      nested: {authorization: "Bearer " + COOKIE, message: "Saved."}
    });
    this.handlers = new Map();
  }
  open(method, url) {this.opened = {method, url};}
  addEventListener(name, cb) {this.handlers.set(name, cb);}
  send(body) {
    this.body = body;
    sends++;
    this.handlers.get("loadend")?.();
    return "NATIVE_SEND_RESULT";
  }
}
const originalOpen = XHR.prototype.open;
const originalSend = XHR.prototype.send;
const originalFetch = async () => {
  fetchCalls++;
  return {
    status: 200,
    clone() {
      return {text: async () => JSON.stringify({
        success: true, apikey: SECRET, elapsed: 5,
      })};
    }
  };
};
const installLogs = [];
const window = {
  location: {href: "https://planets.nu/#/game"},
  fetch: originalFetch, XMLHttpRequest: XHR, URLSearchParams, FormData,
  console: {info: (...args) => installLogs.push(args)}
};
vm.runInNewContext(source, {window, URL, URLSearchParams, FormData});
const probe = window.__planetsM2SavePayloadCaptureV1;
assert.ok(probe);
assert.equal(installLogs.length, 1);
assert.equal(sends, 0);
assert.equal(fetchCalls, 0);

const makeTurn = tax => JSON.stringify({
  planets: [
    {id: 210, ownerid: 9, colonisttaxrate: tax, supplies: 932, friendlycode: "x1x"},
    {id: 340, colonisttaxrate: 7, natives: {nativetaxrate: 12}}
  ],
  ships: [{id: 14, neutronium: 38, clans: 49, mission: 2}],
  apikey: SECRET,
  auth: {savekey: SAVE, token: COOKIE},
  meta: RAW_NOTES
});
function submit(body) {
  const xhr = new XHR();
  xhr.open("POST", "https://api.planets.nu/game/save?savekey=" + SAVE);
  assert.equal(xhr.send(body), "NATIVE_SEND_RESULT");
}
const first = new URLSearchParams({
  gameid: "203343", playerid: "9",
  turn: makeTurn(5),
  apikey: SECRET,
  savekey: SAVE,
  unknownShipNotes: "This is regular content from my test game.",
  extraNumber: "9223"
}).toString();
const second = new URLSearchParams({
  gameid: "203343", playerid: "9",
  turn: makeTurn(6),
  apikey: SECRET,
  savekey: SAVE,
  unknownShipNotes: "This is regular content from my test game.",
  extraNumber: "9223"
}).toString();
submit(first);
submit(second);

const readiness = new XHR();
readiness.open("POST", "https://api.planets.nu/game/turnready");
readiness.send("savekey=" + SAVE);

const ignored = new XHR();
ignored.open("POST", "https://untrusted.example.com/game/save");
ignored.send("apikey=" + SECRET + "&turn=SHOULD_NOT_CAPTURE");

const report = probe.report();
assert.equal(report.schema, "planets-lab.save-payload-capture.v1");
assert.equal(report.status, "CLIENT_PAYLOAD_CAPTURE_NOT_NUHOST_ORDER_ACK");
assert.equal(report.observed_save_calls_retained, 2);
assert.equal(report.route_counters.save, 2);
assert.equal(report.route_counters.turnready, 1);
assert.equal(sends, 4, "observer must never create new requests");
assert.equal(fetchCalls, 0);
assert.equal(report.observations[0].request.encoding, "form");
assert.equal(report.observations[0].request.body.gameid, "203343");
assert.equal(report.observations[0].request.body.extraNumber, "9223");
assert.equal(report.observations[0].request.body.turn.planets[0].colonisttaxrate, 5);
assert.equal(report.observations[1].request.body.turn.planets[0].colonisttaxrate, 6);
assert.equal(report.observations[0].request.body.turn.ships[0].neutronium, 38);
assert.equal(report.observations[0].request.body.unknownShipNotes,
  "This is regular content from my test game.");
assert.equal(report.observations[0].request.body.turn.meta, RAW_NOTES);
assert.equal(report.observations[0].request.body.apikey, "<REDACTED_CREDENTIAL>");
assert.equal(report.observations[0].request.body.savekey, "<REDACTED_CREDENTIAL>");
assert.equal(report.observations[0].request.body.turn.auth.savekey, "<REDACTED_CREDENTIAL>");
assert.equal(report.observations[0].request.body.turn.auth.token, "<REDACTED_CREDENTIAL>");
assert.equal(report.observations[0].response.body.savekey, "<REDACTED_CREDENTIAL>");
assert.equal(report.observations[0].http_status, 200);

const diff = probe.diff(0, 1);
assert.equal(diff.status, "CLIENT_REQUEST_DIFFERENTIAL_NOT_NUHOST_HOST_VERIFIED");
assert.equal(diff.change_count, 1);
assert.equal(diff.truncated, false);
assert.equal(diff.changes[0].path, "$.request.body.turn.planets[0].colonisttaxrate");
assert.equal(diff.changes[0].before, 5);
assert.equal(diff.changes[0].after, 6);
assert.throws(() => probe.diff(0, 5), RangeError);

// Detached reports cannot be used to tamper with retained observations.
report.observations[0].request.body.turn.planets[0].colonisttaxrate = 999;
assert.equal(probe.report().observations[0].request.body.turn.planets[0].colonisttaxrate, 5);

const output = JSON.stringify(probe.report()) + JSON.stringify(diff);
for (const secret of [SECRET, SAVE, COOKIE, "SHOULD_NOT_CAPTURE"]) {
  assert.ok(!output.includes(secret), "leaked credential or foreign origin payload: " + secret);
}
assert.ok(!output.includes("https://api.planets.nu/game/save"), "raw URL leaked");
assert.ok(!output.includes("Bearer " + COOKIE), "auth header leaked");

(async () => {
  await window.fetch("https://api.planets.nu/game/save", {
    method: "POST",
    body: JSON.stringify({
      gameid: 3,
      planets: [{id: 1, colonisttaxrate: 25}],
      apiKey: SECRET, save_key: SAVE,
      nested: {refresh_token: COOKIE}
    })
  });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(fetchCalls, 1);
  assert.equal(probe.report().observed_save_calls_retained, 3);
  const last = probe.report().observations[2];
  assert.equal(last.request.encoding, "json");
  assert.equal(last.request.body.planets[0].colonisttaxrate, 25);
  assert.equal(last.request.body.apiKey, "<REDACTED_CREDENTIAL>");
  assert.equal(last.request.body.save_key, "<REDACTED_CREDENTIAL>");
  assert.equal(last.request.body.nested.refresh_token, "<REDACTED_CREDENTIAL>");
  assert.equal(last.response.body.apikey, "<REDACTED_CREDENTIAL>");

  probe.stop();
  assert.equal(XHR.prototype.open, originalOpen);
  assert.equal(XHR.prototype.send, originalSend);
  assert.equal(window.fetch, originalFetch);
  assert.equal(window.__planetsM2SavePayloadCaptureV1, undefined);
  assert.ok(!JSON.stringify(installLogs).includes(SECRET));
  console.log("M2 real-payload probe synthetic XHR/fetch, secret redaction, state differential: OK");
})().catch(err => {console.error(err); process.exitCode = 1});
