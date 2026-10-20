# M2 client save→ready chronology: one fresh save window + atomic independent consistency audit

Date: 2026-10-20.

## Baseline, verified and immutable

`runtime-logs/m2-save-ready-metadata-synthetic-v1/20261020T134314Z_1d0f3cfafa32` completed with `exit_code=0`, `source_dirty=false`, and exact source `1d0f3cfafa327800096ea9528985860f2cbe2858`; its published `gate.log` says that the fake-browser metadata chronology tests passed. The baseline remains valid **for the V1 test suite**, not necessarily for stronger subsequent logic.

## Correctness defect and repair

The V1 observer classified each `turnready` by searching the **entire retained history** of earlier saves, so the very same earlier successful save could support multiple ready candidates. A later successful save could also mask a previous failed save (or one overlapping the ready) if it was merely the latest save. Those are misleading even for a limited client-local evidence claim.

The patched `tools/client/planets_nu_save_ready_metadata_v1.js` partitions saves into distinct windows bounded by successive `turnready` requests. For a candidate, a window must contain at least one fresh save, **every** save in the window must finish with HTTP 2xx and top-level JSON `success:true` before the ready starts, and the ready itself must succeed. Ready overlap, a save started while ready remains pending, bad/nonmonotonic local timestamps, dropped events and failed/ambiguous save responses force ABSTAIN. Extra counters track repeated ready requests without any new save and failed/overlapping save windows. All outcomes are still **client transport assertions, not signed server order receipts, independent Host-start time, or NuHost execution**.

The observer now supplies `bundle()`: an atomic, detached, metadata-only `report` plus `trace` captured in a single event-loop read. Calling `report()` and `trace()` separately previously risked a mid-capture mismatch due to in-flight requests. Original functions, endpoint allowlist, no extra requests and zero retention of raw request/response bodies remain unchanged.

## Independently recomputed local report

`src/planets_lab/sim/planetary_client_sequence_audit.py` validates strict allowlisted JSON keys/field types, counter consistency, consecutive event IDs, temporal ordering, declared event outcomes, fixed noncausal provenance flags and exact recomputation of all sequence metrics. Unknown fields, injected credentials, forged success counts or promoted `nuhost_execution_verified` claims cause a generic ABSTAIN. The output exposes **only integer counts and false provenance booleans**; it never returns raw trace, local timestamps, raw payloads, URLs, game IDs, tokens or key material.

`tools/diagnostics/m2_client_sequence_audit_v1.py` supports two exclusive modes. `--synthetic` obtains a fake atomic bundle from `tests/js/test_planets_nu_save_ready_metadata_v1.cjs --emit-synthetic-bundle` in memory; the independent Python auditor recomputes its fields. `--private-bundle` reads a user-owned, regular `chmod 600` JSON file outside the repo with the existing no-symlink and size limits. **Never** pass a private file to any public `runtime-logs` or send its contents to GitHub. Client clock observations may still reveal private activity timing even without game identifiers.

## Optional synthetic-only server command

```bash
cd /root/projects/planets-lab
git pull --ff-only origin main
bash tools/run-m2-client-sequence-audit-synthetic-v1-with-evidence.sh
```

This executes only fake-browser Node and the Python consistency audit, without Planets.nu or a live user's browser. It publishes an aggregate-only evidence log.

## What cannot be concluded

A self-consistent client bundle is not independently authenticated. `success:true` cannot confirm the server accepted each order or that every owner's complete orders were submitted. `performance.now()` is not an external time witness. No pre/post Host state is supplied. **No `DIFF_VERIFIED` promotion, Host phase order attribution or causal claim is supported** by this stage.

No M2 historical DuckDB corpus read, `CURRENT`, heldout32, C5/canonical combat or production IntelBoard change.
