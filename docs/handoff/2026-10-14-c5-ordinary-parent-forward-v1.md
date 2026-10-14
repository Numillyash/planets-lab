# C5 ordinary parent STANDARD queue — exploratory N-to-N+1 forward V1

**Date:** 2026-10-14. Research repo `Numillyash/planets-lab`, canonical branch `main`.

## Published broad census (verified)

`runtime-logs/combat-c5-public100-site-coverage-v1/20261014T041550Z_fb5c5dfcc89e`

Exact report Git blob SHA1 `fda92475988d2f7dfbc7b93606de4f8cec909806`.

Independent metadata-preselected 48 games / 96 windows / 809 VCR:
253 ordinary ship–ship; 299 ship–planet candidates; 257 Horwasp
explicitly excluded. 27 ordinary ship-only multi-VCR sites; 26
have at least one adjacent VCR-ID pair, 63 adjacent-ID transitions.
All 376 unique ordinary ship identity targets had T−1 owner order
consensus in the census.

These 27 sites are **observationally conditioned on having multiple
ordinary VCRs**, not a fresh held-out outcome split. Their site locations
and VCR IDs were read from factual VCR only AFTER the independent game/turn
preselection. We must not call them a truly blind queue validation set.

## What is now implemented

Research-only diagnostic
`tools/diagnostics/combat_c5_ordinary_parent_forward_v1.py`.

Preserve exactly all 27 frozen sites and 63 candidate transitions;
never choose examples based on replay or prediction success. For each
adjacent N/N+1 separately:

1. Derive the site's independent T−1 predicted ship membership, owner
   orders, diplomacy and planned movement context using the existing
   `combat_public_capture_o_layer_probe` builder. No VCR N+1 is used
   to construct the site roster.
2. Truncate the factual queue strictly at N. Reconstruct state through
   all earlier factual VCR IDs < N using the existing
   `_initial_state_before_window` history-anchored path.
3. Record factual pair N, then calculate terminal by
   `build_site_terminal_replay_batch` using current VCR N's factual
   seed/static setup and independently carried start. Apply its
   state mutation.
4. **If capture occurred**, abstain
   `ABSTAIN_CAPTURE_TEMPORARY_ORDER_NOT_INDEPENDENT`. Do not call
   `_fixture_order`, guess order from the future, or claim C/O branch
   validated. Likewise abstain for missing start/terminal/owner/order,
   unresolved movement or parent selection.
5. Without a capture, assemble full parent STANDARD candidate states
   via `build_parent_standard_pair_inputs` with diplomacy limited to
   `through_vcr_id=N`, then select with
   `site_executor.select_parent_resume`. This is the computed N+1
   pair, sides and occurrence index; no factual N+1 values enter.
6. **Only after the prediction** read the stored factual N+1 pair and
   sides to evaluate exact/mismatch. Each transition is independently
   reconstructed from its historical prefix to avoid silently
   correcting a prior mismatch with future state.

Count abstentions and site-context failures against the entire
63-transition denominator. An evaluator that produces 0/63 predictions
is a meaningful limitation, not a success. Compare only available
independent selector results; do not invent exactness by observing
future cases.

The earlier 400330/T141 3/3 capture-specific fixture remains
a separate bounded checkpoint. **This V1 deliberately tests the
general non-capture parent branch first**. Capture continuation and
planet engagement are explicit next C5 work, not silently counted
as resolved here. Race 12 Horwasp remains paused.

## Immutable corpus and run

Pinned DB:
`/root/projects/planets-corpus-db/generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb`,
SHA256
`3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`.
Verify once before opening DuckDB read-only. Never mutate CURRENT.

One server command:

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-ordinary-parent-forward-v1-with-evidence.sh
```

Output:
`artifacts/combat/c5-ordinary-parent-forward-v1/published/report.json`.

Evidence:
`runtime-logs/combat-c5-ordinary-parent-forward-v1/`.

Tests:
`tests/test_combat_c5_ordinary_parent_forward_v1.py`
cover prefix truncation, no-oracle comparator invariance,
replay/capture abstentions, mismatches, 27-site/63-transition
frozen population, and runner syntax.

## Evidence and limitations

This evaluates a novel *computed* ordinary parent next pair, but
uses factual VCR **N** setup/seed for replay and factual VCR
**earlier than N** as history anchors. Site identity came from the
already-open census and the official source builder can use
T−1/current archives as otherwise documented. It is **not**
a complete autonomous Host, an independently proven VCR execution
ordering, or a new blind cross-game validation cohort.

Avoid performance tuning to these 27 sites; the next dataset/holdout
must be pre-registered separately. No `planets-intel` production,
combat executor, race12 or other unverified game mechanics promoted.

Preserve old draft/open PR #28 unmerged.
