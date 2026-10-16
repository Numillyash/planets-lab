/*
 * Planets.nu /game/save SCHEMA-ONLY passive observer (M2, research v1).
 *
 * Paste into DevTools Console on your OWN authorized Planets.nu game,
 * BEFORE saving the turn using the ordinary game UI.
 *
 * No additional network requests, no writing, no credentials, no raw HTTP
 * payloads or responses retained, no localStorage, no cookies, no exfiltration.
 * Only a fixed allowlist of known mechanic field NAMES and their TYPES.
 *
 * To inspect:
 *   __planetsM2SaveSchemaProbeV1.report()
 *   __planetsM2SaveSchemaProbeV1.stop()
 *
 * This does NOT attest server-accepted orders, true Host timing, or a cargo
 * transfer model. Never paste a raw HAR, savekey or apikey into an issue.
 */
(function (root) {
  "use strict";
  if (root.__planetsM2SaveSchemaProbeV1) {
    throw new Error("M2 save schema observer already installed; stop it first");
  }
  const SAFE_KEYS = new Set([
    "gameid", "game_id", "id", "turn", "playerid", "player_id",
    "ships", "ship", "shipid", "planets", "planet", "planetid",
    "starbases", "mines", "factories", "defense", "friendlycode",
    "warp", "targetx", "targety", "mission", "mission1target",
    "mission2target", "transfer", "transfers", "transport",
    "beamup", "beamdown", "beam_up", "beam_down", "target",
    "cargo", "neutronium", "duranium", "tritanium", "molybdenum",
    "supplies", "clans", "megacredits", "megacredit",
    "success", "status", "errors", "message", "rst", "data",
    "result", "save", "orders", "shipschanged", "planetschanged",
    "changed", "x", "y", "player", "key"
  ]);
  const SECRET_KEYS = /(?:api.?key|save.?key|pass(?:word)?|cookie|token|session|auth|email|username|security|secret|account.?id)/i;
  const MAX_PARSE_CHARS = 1048576;
  const MAX_DEPTH = 5;
  const MAX_NODES = 320;
  let used = 0;
  const events = [];
  let installed = true;
  const nativeFetch = typeof root.fetch === "function" ? root.fetch : null;
  const xhrProto = root.XMLHttpRequest && root.XMLHttpRequest.prototype;
  const nativeOpen = xhrProto && xhrProto.open;
  const nativeSend = xhrProto && xhrProto.send;

  function endpoint(input) {
    try {
      let url = new URL(typeof input === "string" ? input : input.url, root.location.href);
      const host = url.hostname.toLowerCase();
      return /(^|\.)planets\.nu$/.test(host) && /^\/game\/save\/?$/i.test(url.pathname);
    } catch (_) { return false; }
  }
  function primitiveType(value) {
    if (value === null) return "null";
    if (Array.isArray(value)) return "array";
    const t = typeof value;
    return t === "object" ? "object" :
      (t === "string" || t === "number" || t === "boolean" ? t : "other");
  }
  function structure(value, depth) {
    if (++used > MAX_NODES || depth > MAX_DEPTH) return {type: "truncated"};
    const t = primitiveType(value);
    if (t === "array") {
      // No array sizes or element values: these may reveal game information.
      return {type: "array", item: value.length ? structure(value[0], depth + 1) : {type: "empty"}};
    }
    if (t !== "object") return {type: t};
    const fields = {};
    let redacted = 0, unknown = 0;
    for (const [key, item] of Object.entries(value)) {
      if (SECRET_KEYS.test(key)) { redacted++; continue; }
      if (!SAFE_KEYS.has(key.toLowerCase())) { unknown++; continue; }
      fields[key.toLowerCase()] = structure(item, depth + 1);
    }
    return {type: "object", fields, redacted_key_count: redacted, unknown_key_count: unknown};
  }
  function decodeString(text) {
    if (typeof text !== "string") return null;
    if (text.length > MAX_PARSE_CHARS) return {type: "unparsed_large_body"};
    const clean = text.trim();
    if (clean[0] === "{" || clean[0] === "[") {
      try { return JSON.parse(clean); } catch (_) { return {type: "unparsed_invalid_json"}; }
    }
    if (clean.includes("=")) {
      try {
        const pairs = {};
        for (const [key, value] of new URLSearchParams(clean)) {
          // Only allowlisted, nonsecret names are materialized.
          if (SECRET_KEYS.test(key)) { pairs[key] = null; continue; }
          if (!SAFE_KEYS.has(key.toLowerCase())) { pairs["(unlisted)"] = null; continue; }
          const trimmed = value.trim();
          if ((trimmed.startsWith("{") || trimmed.startsWith("[")) &&
              trimmed.length < MAX_PARSE_CHARS) {
            try { pairs[key] = JSON.parse(trimmed); continue; } catch (_) {}
          }
          // A string's actual value is NEVER persisted.
          pairs[key] = value;
        }
        return pairs;
      } catch (_) { return {type: "unparsed_form"}; }
    }
    return {type: "unknown_encoding"};
  }
  function bodyShape(body) {
    used = 0;
    try {
      if (typeof body === "string") return structure(decodeString(body), 0);
      if (root.URLSearchParams && body instanceof root.URLSearchParams)
        return structure(decodeString(body.toString()), 0);
      if (root.FormData && body instanceof root.FormData) {
        const fields = {};
        let unknown = 0, redacted = 0;
        for (const [key, value] of body.entries()) {
          if (SECRET_KEYS.test(key)) { redacted++; continue; }
          if (!SAFE_KEYS.has(key.toLowerCase())) { unknown++; continue; }
          if (typeof value !== "string") { fields[key.toLowerCase()] = {type: "file_or_binary"}; continue; }
          fields[key.toLowerCase()] = structure(decodeString(value) ?? value, 0);
        }
        return {type: "form", fields, unknown_key_count: unknown, redacted_key_count: redacted};
      }
      return {type: "body_unavailable_or_stream"};
    } catch (_) { return {type: "unparsed"}; }
  }
  function responseShape(textOrObject) {
    used = 0;
    const parsed = typeof textOrObject === "string" ? decodeString(textOrObject) : textOrObject;
    const shape = structure(parsed, 0);
    const flag = parsed && typeof parsed === "object" && typeof parsed.success === "boolean"
      ? parsed.success : null;
    return {shape, reported_success_flag_not_server_acceptance_proof: flag};
  }
  function append(event) {
    if (!installed) return;
    // Bound memory to 6 sanitized observations; never retain unredacted data.
    if (events.length === 6) events.shift();
    events.push(event);
  }
  if (nativeFetch) {
    root.fetch = function (input, init) {
      const watched = endpoint(input);
      const result = nativeFetch.apply(this, arguments);
      if (watched) {
        const capture = {transport: "fetch", method: "POST", request_schema: {type: "not_inspected"}};
        try {
          capture.method = String(init?.method || input?.method || "GET").toUpperCase();
          if (init && Object.hasOwn(init, "body")) capture.request_schema = bodyShape(init.body);
          else if (input && typeof input.clone === "function") {
            input.clone().text().then(t => { capture.request_schema = bodyShape(t); }).catch(() => {});
          }
        } catch (_) {}
        Promise.resolve(result).then(async response => {
          capture.http_status = Number.isInteger(response.status) ? response.status : null;
          try { capture.response = responseShape(await response.clone().text()); }
          catch (_) { capture.response = {shape: {type: "not_decodable"}, reported_success_flag_not_server_acceptance_proof: null}; }
          append(capture);
        }).catch(() => append({...capture, network_error: true}));
      }
      return result;
    };
  }
  if (xhrProto && nativeOpen && nativeSend) {
    const metadata = new WeakMap();
    xhrProto.open = function (method, url) {
      metadata.set(this, endpoint(url) ? {transport: "xhr", method: String(method).toUpperCase()} : null);
      return nativeOpen.apply(this, arguments);
    };
    xhrProto.send = function (body) {
      const capture = metadata.get(this);
      if (capture) {
        capture.request_schema = bodyShape(body);
        this.addEventListener("loadend", () => {
          capture.http_status = Number.isInteger(this.status) ? this.status : null;
          try {
            let data = this.responseType === "json" ? this.response : this.responseText;
            capture.response = responseShape(data);
          } catch (_) {
            capture.response = {shape: {type: "not_decodable"},
              reported_success_flag_not_server_acceptance_proof: null};
          }
          append(capture);
        }, {once: true});
      }
      return nativeSend.apply(this, arguments);
    };
  }
  const api = Object.freeze({
    report() {
      // Return freshly detached schema-only structures, never request bytes.
      return JSON.parse(JSON.stringify({
        schema: "planets-lab.save-schema-observation.v1",
        status: "SCHEMA_ONLY_NOT_SERVER_ORDER_ACK_OR_NUHOST_VERIFIED",
        observed_save_calls: events.length,
        events: events,
        values_logged: false,
        credentials_logged: false,
        submitted_order_mapping_verified: false,
        server_order_acknowledgement_verified: false,
        host_phase_verified: false
      }));
    },
    stop() {
      if (!installed) return;
      installed = false;
      if (nativeFetch) root.fetch = nativeFetch;
      if (xhrProto && nativeOpen) xhrProto.open = nativeOpen;
      if (xhrProto && nativeSend) xhrProto.send = nativeSend;
      delete root.__planetsM2SaveSchemaProbeV1;
    }
  });
  root.__planetsM2SaveSchemaProbeV1 = api;
  // One generic message, no event/body/credentials in developer console.
  if (root.console && typeof root.console.info === "function")
    root.console.info("M2 passive /game/save schema observer installed; report() and stop().");
})(typeof window === "object" ? window : globalThis);
