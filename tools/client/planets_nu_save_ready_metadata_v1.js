/*
 * M2 passive save/turnready sequencing metadata probe.
 *
 * Captures timing, HTTP status and only a boolean response success flag.
 * NEVER captures request bodies, response bodies, URLs, tokens, headers,
 * cookies, strategy text or player/ship/game IDs. It sends NO requests.
 *
 * On your authorized Planets.nu game page install in DevTools, then:
 *   __planetsM2SaveReadyMetadataV1.report()
 *   __planetsM2SaveReadyMetadataV1.trace()
 *   __planetsM2SaveReadyMetadataV1.stop()
 *
 * Local clock readings are NOT independent Host timestamp witnesses.
 * Save/ready client success flags do NOT prove server acceptance of
 * individual orders, actual Host execution, or a complete player bundle.
 */
(function (root) {
  "use strict";
  const NAME = "__planetsM2SaveReadyMetadataV1";
  if (root[NAME]) throw new Error("M2 metadata observer already installed");
  const SCHEMA = "planets-lab.client-save-ready-metadata.v1";
  const MAX_EVENTS = 64;
  const MAX_RESPONSE_CHARS = 524288;
  const events = [];
  const counts = {save: 0, turnready: 0};
  let dropped = 0, nextId = 1, active = true;
  const originalFetch = typeof root.fetch === "function" ? root.fetch : null;
  const XHR = root.XMLHttpRequest && root.XMLHttpRequest.prototype;
  const originalOpen = XHR && XHR.open;
  const originalSend = XHR && XHR.send;
  const xhrMeta = new WeakMap();

  function clock() {
    if (root.performance && typeof root.performance.now === "function")
      return root.performance.now();
    return Date.now();
  }
  function endpoint(input) {
    try {
      const candidate = typeof input === "string" || input instanceof URL
        ? input : input && input.url;
      const url = new URL(candidate, root.location.href);
      if (!/(^|\.)planets\.nu$/i.test(url.hostname)) return null;
      if (/^\/game\/save\/?$/i.test(url.pathname)) return "save";
      if (/^\/game\/turnready\/?$/i.test(url.pathname)) return "turnready";
    } catch (_) {}
    return null;
  }
  function methodLabel(method) {
    const upper = String(method || "GET").toUpperCase();
    return ["GET", "POST", "PUT", "PATCH", "DELETE"].includes(upper)
      ? upper : "OTHER";
  }
  function begin(route, transport, method) {
    if (!active || !route) return null;
    counts[route]++;
    const item = {
      id: nextId++, route, transport, method: methodLabel(method),
      started_ms: clock(), settled_ms: null,
      http_status: null, app_success: null, outcome: "PENDING"
    };
    if (events.length === MAX_EVENTS) {events.shift(); dropped++;}
    events.push(item);
    return item;
  }
  function successFlag(raw) {
    try {
      const parsed = typeof raw === "string"
        ? raw.length <= MAX_RESPONSE_CHARS ? JSON.parse(raw) : null
        : raw;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) &&
        typeof parsed.success === "boolean" ? parsed.success : null;
    } catch (_) {return null;}
  }
  function finish(item, status, appSuccess, error) {
    if (!active || !item || item.outcome !== "PENDING") return;
    item.settled_ms = clock();
    item.http_status = Number.isInteger(status) && status >= 100 && status <= 599
      ? status : null;
    item.app_success = typeof appSuccess === "boolean" ? appSuccess : null;
    item.outcome = error ? "TRANSPORT_ERROR" : "HTTP_RESPONSE";
    if (error) {item.http_status = null; item.app_success = null;}
  }
  if (originalFetch) {
    root.fetch = function (input, init) {
      const route = endpoint(input);
      const item = begin(route, "fetch", init?.method || input?.method);
      let result;
      try {
        result = originalFetch.apply(this, arguments);
      } catch (error) {
        finish(item, null, null, true);
        throw error;
      }
      if (item) {
        // Observer never replaces or awaits the original fetch result.
        Promise.resolve(result).then(response => {
          const status = response && response.status;
          try {
            return Promise.resolve(response.clone().text()).then(raw => {
              finish(item, status, successFlag(raw), false);
            }).catch(() => finish(item, status, null, false));
          } catch (_) {finish(item, status, null, false);}
        }).catch(() => finish(item, null, null, true));
      }
      return result;
    };
  }
  if (XHR && originalOpen && originalSend) {
    XHR.open = function (method, url) {
      xhrMeta.set(this, {route: endpoint(url), method: methodLabel(method)});
      return originalOpen.apply(this, arguments);
    };
    XHR.send = function () {
      const metadata = xhrMeta.get(this);
      const item = metadata && begin(metadata.route, "xhr", metadata.method);
      if (item) {
        this.addEventListener("loadend", () => {
          let flag = null;
          try {
            const raw = this.responseType === "json" ? this.response : this.responseText;
            flag = successFlag(raw);
          } catch (_) {}
          finish(item, this.status, flag, false);
        }, {once: true});
        this.addEventListener("error", () => finish(item, null, null, true),
          {once: true});
        this.addEventListener("abort", () => finish(item, null, null, true),
          {once: true});
        this.addEventListener("timeout", () => finish(item, null, null, true),
          {once: true});
      }
      try {return originalSend.apply(this, arguments);}
      catch (error) {finish(item, null, null, true); throw error;}
    };
  }
  function clientSuccess(item) {
    return item && item.outcome === "HTTP_RESPONSE" &&
      item.http_status >= 200 && item.http_status < 300 &&
      item.app_success === true;
  }
  function readiness() {
    let candidates = 0, ambiguous = 0;
    const readyEvents = events.filter(e => e.route === "turnready");
    for (const ready of readyEvents) {
      // Missing earlier entries mean we cannot establish a continuous
      // client-side sequence. Never treat this as host-order evidence.
      if (dropped !== 0 || !clientSuccess(ready)) {ambiguous++; continue;}
      const earlierSaves = events.filter(e =>
        e.route === "save" && e.id < ready.id);
      if (!earlierSaves.length) {ambiguous++; continue;}
      const latest = earlierSaves[earlierSaves.length - 1];
      if (!clientSuccess(latest) || latest.settled_ms === null ||
          latest.settled_ms > ready.started_ms ||
          earlierSaves.some(e => e.settled_ms === null ||
            e.settled_ms > ready.started_ms)) {
        ambiguous++;
        continue;
      }
      candidates++;
    }
    return {candidates, ambiguous, total: readyEvents.length};
  }
  function snapshot() {
    const sequence = readiness();
    return {
      schema: SCHEMA,
      status: "CLIENT_SEQUENCE_OBSERVED_NOT_NUHOST_ORDER_RECEIPT",
      local_clock_provenance: "UNWITNESSED_CLIENT_PERFORMANCE_CLOCK",
      total_save_calls: counts.save,
      total_turnready_calls: counts.turnready,
      retained_metadata_events: events.length,
      dropped_metadata_events: dropped,
      pending_events: events.filter(e => e.outcome === "PENDING").length,
      transport_error_events: events.filter(e => e.outcome === "TRANSPORT_ERROR").length,
      client_visible_save_success_events: events.filter(e =>
        e.route === "save" && clientSuccess(e)).length,
      client_visible_ready_success_events: events.filter(e =>
        e.route === "turnready" && clientSuccess(e)).length,
      candidate_ordered_client_sequences_not_host_verified: sequence.candidates,
      ambiguous_or_unconfirmed_ready_events: sequence.ambiguous,
      verified_server_order_acceptance: false,
      independently_witnessed_host_start: false,
      nuhost_execution_verified: false,
      no_extra_network_requests: true,
      request_or_response_payloads_retained: false
    };
  }
  function detached(value) {return JSON.parse(JSON.stringify(value));}
  const API = Object.freeze({
    report() {return detached(snapshot());},
    trace() {
      // Only fixed metadata keys; no input URL or request/response data.
      return detached({schema: SCHEMA, status: "LOCAL_CLIENT_TIMELINE_NOT_HOST_PROOF",
        events: events.map(e => ({...e}))});
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
    root.console.info("M2 metadata-only observer ready. Use report(), trace(), stop(). No request bodies captured.");
})(typeof window === "object" ? window : globalThis);
