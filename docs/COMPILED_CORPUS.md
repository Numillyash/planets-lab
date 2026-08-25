# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-08-26-stellar-cartography-feature-inventory-pending.md`](handoff/2026-08-26-stellar-cartography-feature-inventory-pending.md)

## Current verified schema state

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v6
```

Raw `/game/loadall` archives remain unchanged. Prepared projection stays privacy-minimal; raw `.trn` evidence is read directly only by diagnostics that need narrowly scoped historical metadata or feature schema.

## Current runtime-verified 12-game invariants

L1:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13970
post_external_residual         3924
damage_limited_warp_match       10
```

L2:

```text
external_residual_rows             3924
chunnel_explained                  1421
post_chunnel_residual              2503
horwasp_strong_explained            240
post_horwasp_strong_residual       2263
mine_strong_explained                37
post_mine_strong_residual          2226
fuel_proration_explained              6
post_fuel_proration_residual       2220
label_issues                          0
```

Fuel-proration overlap guards remain zero.

## Current generic final endpoint

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest coarse families:

```text
116  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 43  warp7-9 0.5-1.0x observed=other same_line_forward
```

## Verified / closed recent mechanics

- damage-limited warp: independent 10-row prediction reproduced exactly — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict mine/web hit v5: 37 exact rows — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- route-equivalent Tow / Chunnel: exact independent differentials — **TESTED + DIFF_VERIFIED**;
- Nu waypoint-distance fuel proration v6: `Nu exact=6`, `frontier=3`, `VGAP3=0`, production `2226 -> 2220` — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- Crystal Web Drain: one end-to-end attributable transition — **DOCUMENTED + CORPUS_OBSERVED strong evidence-only**, no production label.

## Rejected post-v6 leads for dominant 116-row family

### Outbound fuel transfer

```text
target_short_outbound_fuel_transfer = 0
target_short_transfer_causal_exact = 0
```

### Standard Cloak fuel burn

```text
target_short_cloak_mission = 0
target_short_standard_cloak_fuel_burn_candidate = 0
target_short_cloak_causal_exact = 0
```

### Privateer Rob Ship

```text
rob_exposure_candidate = 1
target_short_privateer_mission9_at_origin = 1
target_short_rob_exposure_candidate = 0
```

The sole global Rob exposure is outside the target family, so no second-pass Rob simulator is justified for the current residual cluster.

## Active raw Stellar Cartography inventory

Diagnostic:

```text
tools/diagnostics/stellar_cartography_raw_feature_inventory.py
```

Purpose: determine which terrain/stellar feature schemas are actually present in the raw 12-game archive before implementing another movement classifier.

The diagnostic searches feature-related raw paths for:

```text
blackhole / black_hole
wormhole
nebula
debris
starcluster / star_cluster
stellar
```

and reports safe mechanical excerpts plus whether each path occurs on turns containing the dominant 116-row family.

Interpretation:

- schema presence alone is not explanatory evidence;
- absence of black-hole/other speed-modifying terrain paths rejects that lead;
- presence outside target-family turns rejects it for the dominant family;
- only an observed raw schema plus a documented movement effect justifies a narrow geometry/timing audit.

No schema/cache/accounting change is permitted during this inventory.

## Current test state

```text
fuel v6 targeted regression set: 16 passed
full pytest suite:              green
```
