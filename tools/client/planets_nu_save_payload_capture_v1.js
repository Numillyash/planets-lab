/*
 * Planets.nu authorized /game/save FULL GAME-DATA observation, M2 research.
 *
 * This is deliberately NOT the previous schema-only probe. It keeps
 * non-secret game values (tax, resources, ship IDs, unknown fields, etc.)
 * for differential reverse engineering of YOUR OWN or authorized test game.
 * All known auth/credential field names are redacted recursively.
 *
 * It is passive: NO network requests, API writes, clicks, storage, clipboard,
 * console payload output, cookies, headers, query strings or telemetry.
 * DO NOT send the output without reviewing it for unexpected secrets.
 *
 * Install in game DevTools Console before an ordinary in-game change.
 *   __planetsM2SavePayloadCaptureV1.report()
 *   __planetsM2SavePayloadCaptureV1.diff(0, 1)
 *   __planetsM2SavePayloadCaptureV1.stop()
 *
 * In the same tab stop the previous schema observer first, if installed.
 */
(function (root) {
  "use strict";
  const NAME = "__planetsM2SavePayloadCaptureV1";
  if (root[NAME]) throw new Error("M2 payload capture already installed");

  const SCHEMA = "planets-lab.save-payload-capture.v1";
  const MAX_EVENTS = 10;
  const MAX_BODY_CHARS = 2_000_000;
  const MAX_NODES = 60000;
  const MAX_DEPTH = 30;
  const MAX_DIFFS = 250;
  const HIDDEN = "<REDACTED_CREDENTIAL>";
  const SECRET_KEY = /(?:^key$|(?:^|[_-])(?:auth|token|secret|password|passwd|cookie|session|credential|bearer|csrf|signature)(?:$|[_-])|api[_-]?key|save[_-]?key|access[_-]?token|refresh[_-]?token|authorization|authkey|account[_-]?password)/i;
  const SUSPICIOUS_ASSIGNMENT = /(?:api[_-]?key|save[_-]?key|authorization|access[_-]?token|refresh[_-]?token|password)\s*[:=]/i;
  const events = [];
  const routeCounts = {save: 0, turnready: 0};
  let active = true;
  const originalFetch = typeof root.fetch === "function" ? root.fetch : null;
  const XHR = root.XMLHttpRequest && root.XMLHttpRequest.prototype;
  const originalOpen = XHR && XHR.open;
  const originalSend = XHR && XHR.send;
  const xhrMeta = new WeakMap();

  function endpoint(input) {
    try {
      const url = new URL(
        typeof input === "string" || input instanceof URL ? input : input && input.url,
        root.location.href
      );
      if (!/(^|\.)planets\.nu$/i.test(url.hostname)) return null;
      if (/^\/game\/save\/?$/i.test(url.pathname)) return "save";
      if (/^\/game\/turnready\/?$/i.test(url.pathname)) return "turnready";
    } catch (_) {}
    return null;
  }
  function scrubString(value, depth, budget) {
    if (value.length > MAX_BODY_CHARS) return "<OMITTED_OVERSIZE_STRING>";
    const s = value.trim();
    if (depth < MAX_DEPTH && s && (s[0] === "{" || s[0] === "[")) {
      try {
        const parsed = JSON.parse(s);
        if (parsed && typeof parsed === "object")
          return sanitize(parsed, depth + 1, budget);
      } catch (_) {}
    }
    // Nested application/x-www-form-urlencoded, rather than JSON, is
    // occasionally used as a value. Parse only if it looks like pairs.
    if (depth < MAX_DEPTH && s.includes("=") && (s.includes("&") ||
        /^(?:api[_-]?key|save[_-]?key|gameid|playerid|turn)=/i.test(s))) {
      const nested = parseForm(s, depth + 1, budget);
      if (nested !== null) return nested;
    }
    // We cannot guarantee token detection in arbitrary proprietary strings.
    // If it visibly looks like inline credentials, omit the entire field.
    if (SUSPICIOUS_ASSIGNMENT.test(s)) return HIDDEN;
    return value;
  }
  function sanitize(value, depth, budget) {
    if (++budget.nodes > MAX_NODES) return "<OMITTED_NODE_LIMIT>";
    if (depth > MAX_DEPTH) return "<OMITTED_DEPTH_LIMIT>";
    if (value === null || typeof value === "boolean" || typeof value === "number")
      return Number.isFinite(value) || value === null ? value : null;
    if (typeof value === "string") return scrubString(value, depth, budget);
    if (Array.isArray(value))
      return value.map(item => sanitize(item, depth + 1, budget));
    if (typeof value === "object") {
      const out = {};
      for (const [key, item] of Object.entries(value)) {
        if (SECRET_KEY.test(key)) {
          out[key] = HIDDEN;
        } else {
          out[key] = sanitize(item, depth + 1, budget);
        }
      }
      return out;
    }
    return "<UNSUPPORTED_VALUE>";
  }
  function parseForm(body, depth, budget) {
    // We only call this on syntactically plausible form data.
    try {
      const out = {};
      let matched = false;
      for (const [key, value] of new URLSearchParams(body)) {
        if (key === body && !body.includes("=")) return null;
        matched = true;
        const item = SECRET_KEY.test(key) ? HIDDEN : scrubString(value, depth + 1, budget);
        // Repeated form parameters are preserved as repeated values.
        if (Object.hasOwn(out, key)) {
          if (!Array.isArray(out[key])) out[key] = [out[key]];
          out[key].push(item);
        } else {
          out[key] = item;
        }
      }
      return matched ? out : null;
    } catch (_) { return null; }
  }
  function safeBody(body) {
    const budget = {nodes: 0};
    try {
      if (typeof body === "string" || (root.URLSearchParams && body instanceof root.URLSearchParams)) {
        const s = String(body);
        if (s.length > MAX_BODY_CHARS) return {encoding: "oversize", body: "<OMITTED_OVERSIZE_BODY>"};
        const trimmed = s.trim();
        if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
          try { return {encoding: "json", body: sanitize(JSON.parse(s), 0, budget)}; }
          catch (_) { return {encoding: "text", body: scrubString(s, 0, budget)}; }
        }
        const form = parseForm(s, 0, budget);
        if (form !== null) return {encoding: "form", body: form};
        return {encoding: "text", body: scrubString(s, 0, budget)};
      }
      if (root.FormData && body instanceof root.FormData) {
        const out = {};
        for (const [key, value] of body.entries()) {
          const item = SECRET_KEY.test(key) ? HIDDEN :
            (typeof value === "string" ? scrubString(value, 1, budget) : "<OMITTED_FILE_OR_BLOB>");
          if (Object.hasOwn(out, key)) {
            if (!Array.isArray(out[key])) out[key] = [out[key]];
            out[key].push(item);
          } else out[key] = item;
        }
        return {encoding: "multipart-form", body: out};
      }
    } catch (_) { return {encoding: "error", body: "<PARSING_FAILED>"}; }
    return {encoding: "unavailable", body: "<STREAM_OR_BINARY_NOT_DECODED>"};
  }
  function safeResponse(raw) {
    if (typeof raw === "object" && raw !== null)
      return {encoding: "json", body: sanitize(raw, 0, {nodes: 0})};
    return safeBody(raw);
  }
  function addObservation(item) {
    if (!active) return;
    // Bound retained game-data snapshots to avoid long browser sessions.
    if (events.length >= MAX_EVENTS) events.shift();
    events.push(item);
  }
  if (originalFetch) {
    root.fetch = function (input, init) {
      const route = endpoint(input);
      if (route) routeCounts[route]++;
      const result = originalFetch.apply(this, arguments);
      if (active && route === "save") {
        const item = {
          transport: "fetch", method: String(init?.method || input?.method || "GET").toUpperCase(),
          request: {encoding: "unavailable", body: "<REQUEST_BODY_UNAVAILABLE>"},
          http_status: null, response: null
        };
        try {
          if (init && Object.hasOwn(init, "body")) item.request = safeBody(init.body);
          else if (input && typeof input.clone === "function") {
            input.clone().text().then(s => {
              if (active) item.request = safeBody(s);
            }).catch(() => {});
          }
        } catch (_) {}
        Promise.resolve(result).then(async response => {
          if (!active) return;
          item.http_status = Number.isInteger(response.status) ? response.status : null;
          try { item.response = safeResponse(await response.clone().text()); }
          catch (_) { item.response = {encoding: "unavailable", body: "<RESPONSE_UNREADABLE>"}; }
          addObservation(item);
        }).catch(() => addObservation({...item, transport_error: true}));
      }
      return result;
    };
  }
  if (XHR && originalOpen && originalSend) {
    XHR.open = function (method, url) {
      xhrMeta.set(this, {route: endpoint(url), method: String(method).toUpperCase()});
      return originalOpen.apply(this, arguments);
    };
    XHR.send = function (body) {
      const meta = xhrMeta.get(this);
      if (meta && meta.route) routeCounts[meta.route]++;
      if (active && meta && meta.route === "save") {
        const item = {
          transport: "xhr", method: meta.method,
          request: safeBody(body), http_status: null, response: null
        };
        this.addEventListener("loadend", () => {
          if (!active) return;
          item.http_status = Number.isInteger(this.status) ? this.status : null;
          try {
            const raw = this.responseType === "json" ? this.response : this.responseText;
            item.response = safeResponse(raw);
          } catch (_) {
            item.response = {encoding: "unavailable", body: "<RESPONSE_UNREADABLE>"};
          }
          addObservation(item);
        }, {once: true});
      }
      return originalSend.apply(this, arguments);
    };
  }
  function detached(value) {
    return JSON.parse(JSON.stringify(value));
  }
  function compareValues(before, after, path, changes, control) {
    if (changes.length >= MAX_DIFFS) { control.truncated = true; return; }
    if (Object.is(before, after)) return;
    const aObj = before !== null && typeof before === "object";
    const bObj = after !== null && typeof after === "object";
    if (aObj && bObj && Array.isArray(before) === Array.isArray(after)) {
      const keys = Array.isArray(before)
        ? Array.from({length: Math.max(before.length, after.length)}, (_, i) => i)
        : [...new Set([...Object.keys(before), ...Object.keys(after)])].sort();
      for (const key of keys) {
        if (changes.length >= MAX_DIFFS) { control.truncated = true; break; }
        const segment = typeof key === "number" ? "[" + key + "]" : "." + key;
        compareValues(before[key], after[key], path + segment, changes, control);
      }
      return;
    }
    changes.push({
      path: path || "$",
      before: before === undefined ? "<MISSING>" : before,
      after: after === undefined ? "<MISSING>" : after
    });
  }
  const API = Object.freeze({
    report() {
      return detached({
        schema: SCHEMA, status: "CLIENT_PAYLOAD_CAPTURE_NOT_NUHOST_ORDER_ACK",
        observed_save_calls_retained: events.length,
        observations: events,
        route_counters: {...routeCounts},
        redaction_scope: "KNOWN_CREDENTIAL_FIELD_NAMES_ONLY_REVIEW_BEFORE_SHARING",
        no_extra_requests: true,
        verified_NuHost_order_mapping: false
      });
    },
    diff(indexA, indexB) {
      if (!Number.isInteger(indexA) || !Number.isInteger(indexB) ||
          indexA < 0 || indexB < 0 || indexA >= events.length || indexB >= events.length) {
        throw new RangeError("Choose two valid indices from report().observations");
      }
      const a = events[indexA], b = events[indexB];
      const changes = [], control = {truncated: false};
      compareValues(a.request, b.request, "$.request", changes, control);
      return detached({
        schema: "planets-lab.save-payload-diff.v1",
        status: "CLIENT_REQUEST_DIFFERENTIAL_NOT_NUHOST_HOST_VERIFIED",
        indices: [indexA, indexB], change_count: changes.length,
        truncated: control.truncated, changes
      });
    },
    stop() {
      if (!active) return;
      active = false;
      if (originalFetch) root.fetch = originalFetch;
      if (XHR && originalOpen) XHR.open = originalOpen;
      if (XHR && originalSend) XHR.send = originalSend;
      delete root[NAME];
    }
  });
  root[NAME] = API;
  if (root.console && typeof root.console.info === "function")
    root.console.info("M2 game-data capture ready; use report(), diff(0,1), stop(). Review before sharing.");
})(typeof window === "object" ? window : globalThis);
