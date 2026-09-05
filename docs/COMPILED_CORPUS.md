# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

New chats should start from:

[`handoff/2026-09-05-new-chat-context.md`](handoff/2026-09-05-new-chat-context.md)

Detailed active mechanics handoff:

[`handoff/2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md`](handoff/2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md)

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

Rejected broad post-v6 leads for the dominant family: outbound fuel transfer, standard Cloak fuel burn, Privateer Rob Ship, and Stellar Cartography speed terrain.

## Normal-mine slowdown reduction

The upper-bound route/geometry pass found:

```text
target_short_rows = 116
target_short_normal_mine_route_exposure = 10
target_short_deficit_near_10n = 2
```

The hull-tech gate then resolved:

```text
candidate_rows_found       = 2
tech_eligible_candidates   = 1
tech_ineligible_candidates = 1
```

Rejected:

```text
game 360690 / turn 155 / ship 447 / hull 23
hull tech = 10
```

Nu documents that hull tech 7+ is not slowed by normal mine impacts.

Sole surviving candidate:

```text
game 511506 / turn 23 / ship 160 / hull 17
hull tech = 6
hull mass = 130
planned distance = 43.566 ly
observed distance = 22.472 ly
deficit = 21.094 ly
normal-mine corpus damage quantum = 76
before damage/supplies = 0 / 53
after damage/supplies  = 66 / 3 (supplies observational)
```

One hit plus submitted-supply auto-repair is exactly compatible with the observed damage:

```text
raw damage after one hit = 76
available repair from 53 supplies = 10%
predicted damage after repair = 66
predicted remaining supplies = 3
```

Two mine damage hits would instead imply raw damage 152 and a very different post-supply-repair state. Therefore the previous `21 ly ~= 2 * 10 ly` geometry is only a candidate signature, not evidence for two impacts.

## Active strict survivor audit

```text
tools/diagnostics/normal_mine_single_candidate_immunity_repair_audit.py
```

It evaluates only the sole tech<7 candidate and reports:

- exact post-decay normal minefields intersecting the planned segment;
- field IDs/owners and route intervals;
- turn-specific Safe Passage relation from each mine owner to the target;
- team identity;
- minefield Friendly Code values exposed by archived perspectives;
- exact ship-to-field FC matching;
- one-hit and two-hit supply-repair predictions.

Normal-mine immunity fails closed. Safe Passage or matching field FC makes a field immune. The ship's universal `MFx` possibility is also checked structurally. If a field FC is not exposed, absence alone is not treated as hostility.

No mine-hit RNG or new production label is inferred from this single transition. No schema/cache/accounting change is permitted during the audit.

## Current test state

```text
fuel v6 targeted regression set: 16 passed
full pytest suite:              green
```
