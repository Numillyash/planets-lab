# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

Current active handoff:

[`handoff/2026-09-05-normal-mine-slowdown-candidate-gate-pending.md`](handoff/2026-09-05-normal-mine-slowdown-candidate-gate-pending.md)

## Current verified schema state

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v6
```

Raw `/game/loadall` archives remain unchanged. Prepared projection stays privacy-minimal; raw `.trn` evidence is read directly only by diagnostics that need narrowly scoped historical metadata.

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

## Current generic final endpoint

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest coarse family:

```text
116  warp7-9 <0.5x observed=other same_line_forward
```

## Verified / closed recent mechanics

- damage-limited warp — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict mine/web hit v5 — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- route-equivalent Tow / Chunnel — **TESTED + DIFF_VERIFIED**;
- Nu waypoint-distance fuel proration v6 — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- Crystal Web Drain — one end-to-end attributable `DOCUMENTED + CORPUS_OBSERVED` evidence-only transition.

Rejected broad post-v6 leads for the dominant family: outbound fuel transfer, standard Cloak fuel burn, Privateer Rob Ship, and Stellar Cartography speed terrain. The refined terrain inventory reproduced 116 rows exactly and found no active Black Hole or wormhole state anywhere in the current 12-game corpus.

## Normal-mine slowdown candidate gate

The upper-bound exposure/geometry pass produced:

```text
target_short_rows = 116
target_short_normal_mine_route_exposure = 10
target_short_normal_mine_multi_field_route_exposure = 2
target_short_positive_planned_distance_deficit = 10
target_short_deficit_near_10n = 2
```

Only two rows survive:

```text
game 360690 / turn 155 / ship 447 / hull 23 / deficit 30.575 / implied 3 slowdown hits
game 511506 / turn 23  / ship 160 / hull 17 / deficit 21.094 / implied 2 slowdown hits
```

Active diagnostic:

```text
tools/diagnostics/normal_mine_slowdown_candidate_gate_audit.py
```

It uses the same authoritative static hull specs and mine context as strict v5 and reports:

```text
hull_tech
hull_mass
slowdown_tech_eligible
normal_mine_damage_quantum
enemy normal field IDs / owners
before damage/supplies/fuel/mass
observational after damage/supplies/fuel/mass
observed damage delta
```

Hard rule: hull tech 7+ cannot receive the documented 10-ly normal-mine slowdown. Any such candidate is rejected before diplomacy/friendly-code/RNG/repair work.

For tech<7 survivors only, the next layer is historical Safe Passage / minefield friendly-code compatibility, exact route-field attribution, mine-hit multiplicity probability and conservative repair compatibility. One or two rows are insufficient for a production label without independent attributable support.

No schema/cache/accounting change is permitted during this candidate gate.

## Current test state

```text
fuel v6 targeted regression set: 16 passed
full pytest suite:              green
```
