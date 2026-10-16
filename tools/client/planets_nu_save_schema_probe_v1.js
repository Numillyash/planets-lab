/*
 * Planets.nu /game/save SCHEMA-ONLY passive observer (M2, research v1).
 *
 * Paste into DevTools Console on your OWN authorized Planets.nu game,
 * BEFORE saving the turn using the ordinary game UI.
 *
 * No additional network requests, no writing, no credentials, no raw HTTP
 * payloads or responses retained, no localStorage, no cookies, no exfiltration.
 * Only a fixed allowlist of known mechanic field NAMES and their TYPES.
 * v1.1 reports category-only traffic counts when observed_save_calls is 0.
 * v1.2 profiles (up to two) unknown field VALUE TYPES and allowed nested
 * field names. Unknown field names and ALL actual values remain redacted.
 * A JSON-looking field does NOT establish that the server applied any order.
 * No raw URL paths, query strings, request bodies or other-site traffic are
 * emitted in its diagnostics; the exact save path is still the ONLY endpoint
 * whose schema is inspected.
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

  // Coarse transport census: only fixed route-category labels are recorded.
  // Never retain URLs, paths, query strings, HTTP bodies, or request headers.
  const CLASS_NAMES = [
    "game_save_exact", "game_save_candidate", "game_turnready",
    "game_other", "account_other", "planets_other"
  ];
  const counters = {
    planets_requests_total: 0,
    planets_post_requests: 0,
    fetch_requests: 0,
    xhr_requests: 0,
    by_class: Object.fromEntries(CLASS_NAMES.map(name => [name, 0]))
  };
  function routeClass(input) {
    try {
      const rawUrl = typeof input === "string" || input instanceof URL
        ? input : input && input.url;
      const url = new URL(rawUrl, root.location.href);
      if (!/(^|\.)planets\.nu$/i.test(url.hostname)) return null;
      const pathname = url.pathname.replace(/\/+$|^\/+$/g, "") || "/";
      if (/^\/game\/save$/i.test(pathname)) return "game_save_exact";
      if (/^\/(?:api\/)?game\/(?:save|savegame|saveorders|saveturn|save-turn|submit|submitturn|submit-turn|orders)$/i.test(pathname))
        return "game_save_candidate";
      if (/^\/game\/turnready$/i.test(pathname)) return "game_turnready";
      if (/^\/(?:api\/)?game\//i.test(pathname)) return "game_other";
      if (/^\/(?:api\/)?account\//i.test(pathname)) return "account_other";
      return "planets_other";
    } catch (_) { return null; }
  }
  function countRequest(route, transport, method) {
    if (route === null) return;
    counters.planets_requests_total++;
    if (method === "POST") counters.planets_post_requests++;
    if (transport === "fetch") counters.fetch_requests++;
    else counters.xhr_requests++;
    counters.by_class[route]++;
  }
  function primitiveType(value) {
    if (value === null) return "null";
    if (Array.isArray(value)) return "array";
    const t = typeof value;
    return t === "object" ? "object" :
      (t === "string" || t === "number" || t === "boolean" ? t : "other");
  }
  // Unlisted field names are NEVER emitted, even when they contain arbitrary
  // account data. The only permitted signal is a bounded type/shape profile.
  function opaqueValueProfile(value, depth) {
    const t = primitiveType(value);
    if (depth > MAX_DEPTH) return {outer_type: t, content: "depth_limit"};
    if (t === "object" || t === "array")
      return {outer_type: t, sanitized_inner_shape: structure(value, depth + 1)};
    if (t !== "string") return {outer_type: t};
    if (value.length > MAX_PARSE_CHARS)
      return {outer_type: "string", content: "too_large"};
    const trimmed = value.trim();
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed && typeof parsed === "object")
          return {
            outer_type: "string",
            content: Array.isArray(parsed) ? "json_array" : "json_object",
            sanitized_inner_shape: structure(parsed, depth + 1)
          };
      } catch (_) {
        return {outer_type: "string", content: "invalid_json"};
      }
    }
    return {outer_type: "string", content: "not_json"};
  }
  function formValueProfiles(text) {
    if (text.length > MAX_PARSE_CHARS) return null;
    // URLSearchParams values can themselves be JSON documents. Inspect ONLY
    // value types and allowed nested field NAMES, never raw value or field name.
    const profiles = [];
    let unknown = 0;
    let redacted = 0;
    try {
      for (const [key, value] of new URLSearchParams(text)) {
        if (SECRET_KEYS.test(key)) { redacted++; continue; }
        if (SAFE_KEYS.has(key.toLowerCase())) continue;
        unknown++;
        if (profiles.length < 2) profiles.push(opaqueValueProfile(value, 1));
      }
    } catch (_) { return null; }
    return {unknown_field_count: unknown, secret_field_count: redacted,
      opaque_field_value_profiles: profiles};
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
    const opaque = [];
    for (const [key, item] of Object.entries(value)) {
      if (SECRET_KEYS.test(key)) { redacted++; continue; }
      if (!SAFE_KEYS.has(key.toLowerCase())) {
        unknown++;
        if (depth <= 1 && opaque.length < 2)
          opaque.push(opaqueValueProfile(item, depth + 1));
        continue;
      }
      fields[key.toLowerCase()] = structure(item, depth + 1);
    }
    return {type: "object", fields, redacted_key_count: redacted,
      unknown_key_count: unknown, opaque_field_value_profiles: opaque};
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
      if (typeof body === "string" ||
          (root.URLSearchParams && body instanceof root.URLSearchParams)) {
        const text = typeof body === "string" ? body : body.toString();
        const shape = structure(decodeString(text), 0);
        const trimmed = text.trim();
        if (!(trimmed.startsWith("{") || trimmed.startsWith("[")) &&
            trimmed.includes("=")) {
          // Up to two anonymized unknown-form-field profiles; no key names.
          const summary = formValueProfiles(text);
          if (summary) shape.opaque_form_fields = summary;
        }
        return shape;
      }
      if (root.FormData && body instanceof root.FormData) {
        const fields = {};
        let unknown = 0, redacted = 0;
        const opaque = [];
        for (const [key, value] of body.entries()) {
          if (SECRET_KEYS.test(key)) { redacted++; continue; }
          if (!SAFE_KEYS.has(key.toLowerCase())) {
            unknown++;
            if (opaque.length < 2) opaque.push(
              typeof value === "string" ? opaqueValueProfile(value, 1) : {outer_type: "file_or_binary"}
            );
            continue;
          }
          if (typeof value !== "string") { fields[key.toLowerCase()] = {type: "file_or_binary"}; continue; }
          fields[key.toLowerCase()] = structure(decodeString(value) ?? value, 0);
        }
        return {type: "form", fields, unknown_key_count: unknown,
          redacted_key_count: redacted, opaque_field_value_profiles: opaque};
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
      const route = routeClass(input);
      const method = String(init?.method || input?.method || "GET").toUpperCase();
      countRequest(route, "fetch", method);
      const result = nativeFetch.apply(this, arguments);
      if (route === "game_save_exact") {
        const capture = {transport: "fetch", method, request_schema: {type: "not_inspected"}};
        try {
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
      const route = routeClass(url);
      const normalizedMethod = String(method).toUpperCase();
      metadata.set(this, {route, method: normalizedMethod});
      return nativeOpen.apply(this, arguments);
    };
    xhrProto.send = function (body) {
      const meta = metadata.get(this);
      if (meta) countRequest(meta.route, "xhr", meta.method);
      const capture = meta && meta.route === "game_save_exact"
        ? {transport: "xhr", method: meta.method} : null;
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
        diagnostics: {
          planets_requests_total: counters.planets_requests_total,
          planets_post_requests: counters.planets_post_requests,
          fetch_requests: counters.fetch_requests,
          xhr_requests: counters.xhr_requests,
          route_categories: {...counters.by_class},
          // These counters are transport observations, not saved-order evidence.
          route_discovery_only_not_server_ack: true
        },
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
