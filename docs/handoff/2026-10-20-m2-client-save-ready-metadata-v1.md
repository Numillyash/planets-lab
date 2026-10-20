# M2 browser-local save → turnready chronology (metadata only)

Date: 2026-10-20.

## Baseline checkpoint

Validated `runtime-logs/m2-local-save-readiness-synthetic-v1/20261019T234441Z_2bf7ed40e76d`: clean source `2bf7ed40e76d198429ba5771c0bd4b238f50dec5`, `exit_code=0`, no corpus reads, no sensitive payload publication. Aggregate counts were 4 retained fake save observations, 2 parseable bodies, 1 client-visible HTTP+JSON `success:true`, 1 app-level failure, 1 HTTP failure, 1 unknown outcome, 2 overwritten save records. No independent receipt, Host clock or execution verified.

The existing owner-approved `tools/client/planets_nu_save_payload_capture_v1.js` retains sanitized **full request/response bodies**, with unavoidable residual privacy concerns for unknown strategic fields. Its save counter and turnready counter alone cannot establish which save preceded a particular turnready request.

## New metadata-only passive browser instrument

The independent `tools/client/planets_nu_save_ready_metadata_v1.js` observes only network calls to exact same-provider `/game/save` and `/game/turnready` endpoints. No request body, URL, key, header, response body or game/player identifier is ever persisted or returned. It invokes original `fetch` and XHR operations unmodified, with no new requests. It temporarily parses at most one bounded response body to extract **only** a boolean top-level `success` flag, and retains: route type, transport, allowlisted HTTP method, local performance-clock timestamps, response HTTP status, app success bool/null and transport outcome. The bounded 64-event in-memory chronology explicitly records dropped metadata events.

`report()` returns only event totals and a conservative *candidate client-side sequence* count. A candidate requires: completed HTTP 2xx + JSON `success:true` for a save before the next ready was dispatched; all earlier saves have settled before ready; and a successful ready response. If the log is truncated, the latest save overlaps the ready request, the response is missing/ambiguous or a save fails, the ready event is marked ambiguous. A user may inspect `trace()` locally; the trace contains the same allowlisted metadata, never payload contents.

**Crucial:** A client's save/ready successful-shaped responses DO NOT certify accepted orders, server-side transaction commit, actual ready state or NuHost execution. JS `performance.now()` timestamps are client-local and not a certified Host-start clock. No historical `DIFF_VERIFIED` claims are created by this script, even with a clean candidate sequence.

## Developer validation, without real user data

CI invokes `tests/js/test_planets_nu_save_ready_metadata_v1.cjs` through a Python regression with a fully fake browser. Tests verify initial passive installation, sequential save then ready, ready before save, HTTP failure, app failure, concurrent save/ready fetches, foreign endpoints, bounded-trace invalidation, snapshot detachment and restoration of original functions. Secret-like strings and fake strategic fields embedded in request/response are asserted **absent** in `report()` and `trace()`.

An optional synthetic-only server smoke publishes no live browser data:

```bash
cd /root/projects/planets-lab
git pull --ff-only origin main
bash tools/run-m2-save-ready-metadata-synthetic-v1-with-evidence.sh
```

This uses Node.js and the fake transport suite. It publishes `runtime-logs/m2-save-ready-metadata-synthetic-v1/` only if a user chooses to run it. No DuckDB/corpus/HAR/owner orders.

## Optional real opt-in, not needed for this PR

On **your own authorized** Planets.nu game page, the user may manually paste the script from the repository into DevTools **before** a normal save or ready operation, then call:
```js
__planetsM2SaveReadyMetadataV1.report()
__planetsM2SaveReadyMetadataV1.trace()
__planetsM2SaveReadyMetadataV1.stop()
```

The trace is local-only and should not be automatically published to GitHub. The script does not record request bodies, and the legacy full-payload probe does not need to be installed for it to operate. No need to perform a deliberate game experiment now.

No C5, canonical combat, production IntelBoard, corpus CURRENT, historical entity reads or heldout32 changes.
