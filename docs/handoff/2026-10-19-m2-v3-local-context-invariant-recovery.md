# M2 V3 runtime fail-closed: cumulative versus planet-local joint context

Date: 2026-10-19.

## Published failure, not a successful V3 observation

Published `runtime-logs/m2-public100-surface-context-v1/20261019T120152Z_0a0fd5686aaa` on clean source `0a0fd5686aaacea4571c49398e7fd103d6d46856` has `metadata.json: exit_code=1`, `gate.log` records `M2_SURFACE_JOINT_CARGO_BASE_INVARIANT_FAILURE`, and both requested `m2-public100-surface-residual-context-v3/report.json` and `triage.json` are listed as missing. This is NOT a validated V3 census and must not be counted as a scientific result. The last valid V2 report remains available unchanged on `runtime-logs`.

## Root cause and repair

In `profile_surface_residual_context`, `dst` is a **cumulative** Counter indexed by mineral and residual class for every planet already processed in one T−1/T perspective pair. PR #236 V3 interpreted `bool(dst["one_ship..."])`, `bool(dst["multiple_ship..."])`, `bool(dst["ownerless_planetlinked_tech_changed_observed"])`, `bool(dst["planetlinked_base_both_any_owner_provenance"])`, and `bool(dst["owner_ship_observed_at_site_both"])` as if they were **current planet-mineral** booleans. Once any earlier planet had a match, later planets in the same class inherited the positive flag, inflating the joint partition relative to the separately counted cargo/base marginals.

The fix obtains each ship observation in a local `ship_here` Counter, updates the aggregate `dst` only for reporting, and calculates joint flags using `ship_here` plus current `pid` base membership and current linked tech fields. Aggregate invariants remain strict; no relaxation or backfilling, and no Host order claim is made.

The new three-planet regression deliberately places (1) overlapping single+multiship candidate with base-tech change, (2) mineral residual with neither ship nor base, and (3) base-tech change without ship/cargo match. It verifies disjoint mineral-level classes and planet-window dedup *through* `analyze_corpus_coverage` so the original invariant failure is exercised.

## Recovery boundary

The failed V3 run has no `report.json`. Thus neither the existing report recovery mode nor offline `triage.json` regeneration can recreate V3 overlap counts; a new bounded 136-pair corpus V3 pass is needed only **after** the fix is merged and CI validated. The 26.65-GiB immutable generation and `CURRENT` are not modified; heldout32 entity data remain sealed. Preserve the failed evidence as a fail-closed checkpoint, publish new V3 evidence in its own dated `runtime-logs` run.

Command after successful merge and main CI:

```bash
cd /root/projects/planets-lab
git pull --ff-only origin main
M2_CORPUS_COVERAGE_OUTPUT=artifacts/planetary/m2-public100-surface-residual-context-v3/report.json \
  bash tools/run-m2-public100-surface-context-v1-with-evidence.sh
```
