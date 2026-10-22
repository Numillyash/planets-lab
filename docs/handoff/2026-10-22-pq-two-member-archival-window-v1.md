# PR #279 — privacy-minimal PQ/PPQ two-member public archive field-sufficiency

Date 2026-10-22. Sources: `src/planets_lab/corpus/pq_window_field_sufficiency.py`, CLI `tools/diagnostics/pq_window_field_sufficiency.py`, tests `tests/test_pq_window_field_sufficiency.py`.

## Purpose

After #278's strict read-only existing feature-index/canonical frozen allowlist **metadata** triage, this stage is the **first deliberately bounded payload-level data-read tool** for PQ/PPQ history. It does NOT claim to have run against the server's 26+ GiB public100 cache: runtime archives may not be mounted in GitHub Actions or this chat. Its purpose is to let the existing corpus host operator safely measure exactly one predeclared, already-approved public `/game/loadall` consecutive perspective pair, without broad rescans or opening sealed M2 heldout32.

## Inputs and scope

The tool requires every argument:

```bash
python -m tools.diagnostics.pq_window_field_sufficiency \
  --feature-index validation/corpus/compiled/v1/metadata/game_features.parquet \
  --frozen-cohort /path/to/predeclared-allowed-public-cohort.json \
  --archive-dir validation/corpus/cache/loadall \
  --game-id <APPROVED_GAME_ID> --player-slot <APPROVED_PLAYER_SLOT> \
  --turn-before <APPROVED_T_MINUS_1> \
  --output artifacts/pq/windows/<LOCAL_REPORT_NAME>.json
```

For the existing tracked twelve-game nonheldout public control cohort use `validation/corpus/manifests/pq-public-control12-frozen-cohort.v1.json`. It freezes the 12 existing IDs without changing the current manifest (8 PPQ / 4 nonqueue controls). This is NOT a public68 or public100 sampling claim. Do not use a guessed game, player or turn. The allowlist JSON is `planets-lab.pq-historical-frozen-cohort.v1` (from #278). The script recomputes the strict cohort-index metadata readiness before touching an archive; the requested game MUST be an admitted observational candidate, and the file must be exactly `game-<approved_id>.zip` in the specified existing archive directory. ZIP opened directly, but ONLY `player<slot>-turn<Tminus1>.trn` and `player<slot>-turn<T>.trn` are read (CRC on accessed members). Duplicate names, nonconsecutive/mismatching embedded IDs/turns, missing members, malformed/gzip data, unbounded decoded members and invalid types are refused. Other perspectives/turns/archives are never decoded. No reindex, no web/API, no cache writes.

## Output and inference boundaries

The JSON contains only game/slot/turn identifiers from the explicit request, queue mode from public manifest, hashes of cohort/index, the number of visible rows in each of the `planets`, `starbases`, `ships` arrays, **fresh explicit-owner rows only if typed `infoturn` matches requested embedded turn**, separate owner records *without* infoturn (never equated with freshness), malformed/unknown owner rows and explicit missing-array reasons. It never emits raw values, planet names, ship coordinates, email, username, savekey, orders, messages or API keys.

A valid array shape is **not** a full fleet/queue/PP/warehouse inventory. Public perspective snapshots are not guaranteed to contain all hidden ships, completed component ledgers or server-accepted orders; ownerless bases or absent infoturn must not be automatically promoted to trusted owner/current. Regardless of field counts, each report explicitly sets:

```
causal_queue_replay_admitted = false
host_accepted_orders_verified = false
owner_pp_ledger_independently_complete = false
starbase_component_warehouses_independently_complete = false
complete_global_fleet_and_base_roster_verified = false
host_phase_boundary_independent = false
evidence = PUBLIC_ARCHIVE_TWO_MEMBER_SHAPE_ONLY_NOT_DIFF_VERIFIED
```

This stage can help plan a future **bounded observational** queue comparison on an allowed, frozen public slice if a real source field exists, but cannot establish actual NuHost chosen base/RNG, build price, ship ID assignment, server acceptance, or phase timing. Genuine attributable `DIFF_VERIFIED` stays deferred to [issue #247](https://github.com/Numillyash/planets-lab/issues/247). A missing record is explicit ABSTAIN/UNKNOWN, never falsely 0.

## Next

Check final PR #279 CI and push main CI before claiming success. On the corpus-bearing runtime, freeze a small permitted cohort and candidate windows **before** opening data; start with existing 12-game indexed metadata or authorized public68 manifests. Run first safe two-member observational reports and log aggregate qualification counts only, preserving `CURRENT`. If the host is inaccessible, do not pretend these reports ran: repository CLI/handoff is ready, raw files stay on user's host. Continue to a strict window-by-window entity-identity/observable-field gate only when public provenance and sufficient actual fields justify it; do not preemptively scan public100.

Per #262 each later PR must have fully replaced `docs/CONTINUE_HERE.md`, current PR changelog entry and substantive docs before exact-green CI, merge and postmerge verification.
