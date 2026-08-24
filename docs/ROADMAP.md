# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-target-origin-tow-followup.md`](handoff/2026-08-24-target-origin-tow-followup.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean real NuHost transitions.

Unknown mechanics fail closed rather than being silently guessed. Raw game/settings/topology facts and evidence-scoped effective overrides remain separate.

## Current focus

The active milestone is **M5: historical NuHost corpus + compatibility mining**, with movement as the most mature mechanic family.

Current runtime-verified 12-game movement accounting:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13956
post_external_residual              3938
chunnel_explained                   1421
post_chunnel_residual               2517
horwasp_strong_explained             240
post_horwasp_strong_residual        2277
mine_strong_explained                 37
post_mine_strong_residual           2240
```

Verified recent closures:

- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multi-event handling — `TESTED + DIFF_VERIFIED`;
- strict mine/web interruption context v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`.

The Chunnel v4 differential closed exactly as predicted:

```text
chunnel_explained             1387 -> 1421  (+34)
post_chunnel_residual         2551 -> 2517  (-34)
horwasp_strong_explained       240 ->  240
post_horwasp_strong_residual  2311 -> 2277  (-34)
```

The mine/web v5 differential also closed exactly as independently predicted:

```text
post_horwasp_strong_residual  2277 -> 2277  unchanged
mine_strong_explained            0 ->   37
post_mine_strong_residual      2277 -> 2240  (-37)
```

The strict split is:

```text
normal_mine_hit_nearest_damage  19
web_mine_hit_nearest_damage     18
```

All mine/Chunnel/Horwasp overlap guards were zero.

## Post-v5 generic residual landscape

The generic clustering audit now reads `movement_post_mine_strong_residual` by default and measured:

```text
final_residual_rows       2240
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               783
generic_games               12
generic_hulls               79
```

The expected arithmetic `820 - 37 = 783` was confirmed exactly, so every strict mine/web closure left the generic non-Horwasp triage population as intended.

Largest current coarse cross-game signatures:

```text
warp7-9  <0.5x    observed=other   same_line_forward   121
warp0    nominal<=0 target=origin  target_is_origin     97
warp7-9  <0.5x    observed=origin  stationary           64
warp7-9  >3.0x    target=origin    target_is_origin     52
warp7-9  0.5-1.0x observed=other   same_line_forward    48
warp7-9  >3.0x    observed=other   oblique              46
```

Useful aggregate totals:

```text
baseline above_nominal          265
baseline reachable_other        255
baseline warp_zero_external     102
baseline partial_other           84
baseline reachable_stayed        52
baseline partial_stayed          25

target_relation target=origin   226
direction same_line_forward     245
direction stationary             77
```

Short-forward movement remains large after strict mine removal, but it is still heterogeneous. The next focused lead is target-at-origin external movement because it directly indicates movement not explained by the candidate ship's own waypoint.

Intercept was checked against corpus intent classification and rejected as the broad Move Most explanation because owner mission `7` is already classified as `INTERCEPT` and excluded before this residual layer.

## Target-origin tow follow-up

Current observed-tow external context is deliberately fail-closed. `_observed_tow_targets()` collects owner-visible Tow attempts whose tower and target start together and finish together, but it only explains the target when exactly one matching tower exists. Multiple matching towers are counted as ambiguous and remain residual.

That creates a possible route-equivalent semantic gap analogous to Chunnel v4: tower identity may be ambiguous while the movement route is already unambiguous because every matching tower shares the same observed start and destination.

Focused diagnostic:

```text
tools/diagnostics/target_origin_tow_residual_audit.py
```

It reads the final v5 residual and audits all non-Horwasp rows that moved while retaining their waypoint at the origin. The broad clustering predicts:

```text
candidate_rows = 226
```

Priority outputs:

```text
post_warp0
has_same_origin_destination_comover
has_hidden_or_unresolved_comover
has_visible_non_tow_comover
has_visible_tow_targeter
any_visible_matching_tower
single_visible_matching_tower
route_equivalent_multiple_visible_towers
post_warp0_with_visible_matching_tower
post_warp0_with_multiple_visible_towers
post_warp0_with_comover
post_warp0_hidden_comover_without_visible_tow
post_warp0_without_comover
```

Do not promote hidden/unresolved co-movement to tow. A clean `route_equivalent_multiple_visible_towers` population with near-zero unexpected single matches would justify a narrow semantic differential first.

## Mine/web movement interruption — verified v5 mechanic

The short same-line family produced strong minefield evidence across several diagnostics.

First focused audit:

```text
tools/diagnostics/mine_hit_residual_audit.py
```

Runtime result:

```text
short_same_line_forward               235
web_state_signature                    19
web_strong                             18
normal_mine_10ly_geometry              55
normal_mine_strong                     25
```

All 429532 observed minefield records in this corpus pass expose an explicit radius and are parseable; production does not need radius inference here.

Host-order-aware second pass:

```text
tools/diagnostics/mine_hit_hostorder_differential_audit.py
```

Runtime result:

```text
effective_short_same_line          238
same_identity_after                238
after_identity_break                 0
web_after_field_strong              18
normal_after_field_strong           25
```

The raw 235 vs effective 238 difference is fully attributable to Gravitonic effective-distance handling. The older fuel audit's 216 short candidates excluded Gravitonic hulls; no corpus regression is implied.

### NuHost mine damage rounding compatibility finding

Rounding differential:

```text
tools/diagnostics/mine_hit_damage_rounding_audit.py
```

Runtime results strongly reject literal `ceil` as NuHost compatibility behavior:

```text
web_ceil_delta_match_after_field        3
web_floor_delta_match_after_field      15
web_nearest_delta_match_after_field    18
web_nearest_not_ceil_delta             15
web_nearest_control_no_after_field      0

normal_ceil_delta_multiple_after_field        7
normal_floor_delta_multiple_after_field      13
normal_nearest_delta_multiple_after_field    19
normal_nearest_repair_bracket_from_zero      22
normal_nearest_not_ceil_from_zero            10
normal_nearest_damage_hits_differ_from_slow_hits 1
normal_nearest_control_no_after_field         0
```

Planets.nu documentation says mine damage is rounded up. Historical NuHost corpus evidence instead selects positive nearest-integer rounding for both web and normal mine damage. Keep this as an explicit compatibility distinction; do not silently rewrite the documentation claim.

Repair remains a real post-movement confounder: 5 supplies can repair 1 percentage point. Repair-bracket rows are supportive evidence but are deliberately excluded from the strict production classifier.

Damage-hit multiplicity is not forced to equal the 10-ly slowdown count. The verified strict v5 rows include one `2 damage hits / 1 slowdown` case and one `2 / 2` case.

## Mine context labels v5 — verified

Production module:

```text
src/planets_lab/corpus/movement_mine_context.py
```

Compiled label schema:

```text
planets-lab.compiled-movement-context-labels.v5
```

The v5 classifier is fail-closed and labels only strict field-backed nearest-damage evidence.

Strict categories:

```text
web_mine_hit_nearest_damage
normal_mine_hit_nearest_damage
```

Derived fields:

```text
mine_category
mine_damage_hits
mine_slowdown_hits
mine_strong_explained
post_mine_strong_residual
```

No minefield IDs, owners, coordinates or friendly codes are exported.

Layer order:

```text
post_external_residual
  -> Chunnel
  -> post_chunnel_residual
  -> Horwasp strong
  -> post_horwasp_strong_residual
  -> strict mine/web strong
  -> post_mine_strong_residual
```

The pre-mine `movement_post_horwasp_strong_residual` view remains intact as a differential control. The new final view is:

```text
movement_post_mine_strong_residual
```

Normal v5 build cache behavior was exactly as designed:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
```

The production differential exactly reproduced the independent strict subset:

```text
mine_strong_explained       37
post_mine_strong_residual 2240
```

## Test-suite state

After correcting the stale Chunnel shared-schema sentinel, both requested runs are green on a clean tree:

```text
targeted v5 regression: 17 passed
full pytest suite:       all passed
```

No corpus rebuild followed the test-only fix and none was required.

## M0 — deterministic skeleton

Status: **substantially complete**.

- canonical full-information `GameState`;
- immutable turn-order contracts;
- deterministic seeded `HostEngine.step()`;
- baseline tests and scenario infrastructure.

## M1 — minimal sandbox

Status: **largely implemented for the movement subset**.

Implemented or partially implemented:

- Planets.nu JSON -> canonical state adapter;
- cargo transfer and colonization primitives;
- ordinary movement, movement mass, fuel use and fuel proration primitives;
- warp wells;
- tow / intercept / HYP movement phases;
- pre-movement repair and damage-limited speed;
- ion-storm displacement;
- minimal planet economy;
- deterministic golden scenarios.

Movement rules should continue to be promoted from M5 differential evidence rather than guessed directly in the simulator.

## M2 — economy and planetary host

Status: **in progress / not current priority**.

Target coverage includes factories/supplies, taxes/happiness, natives/growth, assimilation, mining, riots/civil war, starbases and ship construction, with differential validation before promotion.

## M3 — warfare

Status: **partial**.

Target coverage includes towing interactions, minefields/webs, combat, missions, fighters/torpedoes, ground combat and post-combat aftermath.

## M4 — race mechanics

Status: **partial**.

Race-specific behavior belongs in explicit ruleset modules/hooks. Important families include Privateer gravitonic/rob, Crystal webs, Cyborg Chunnel, Fascist pillage/glory, Bird cloak/super-spy, Rebel RGA, Colonial fighter sweep and Horwasp mechanics.

## M5A — historical NuHost corpus

Status: **active; acquisition and movement compilation operational**.

Current corpus foundation:

- 12 recent unique finished games across four configured account histories;
- privacy-safe manifest v2 tracked in Git;
- immutable `/game/loadall` archives cached locally and gitignored;
- prepared cache for normalized historical snapshots;
- compiled movement Parquet + DuckDB catalog;
- separate L2 context-label layer.

Current schemas:

```text
corpus manifest:
  planets-lab.corpus-game.v2
prepared cache:
  planets-lab.prepared-game-cache.v1
compiled movement:
  planets-lab.compiled-movement.v2
post-compile external-context semantics:
  planets-lab.compiled-movement-storm-context.v2
compiled context labels:
  planets-lab.compiled-movement-context-labels.v5
standalone Chunnel game summary:
  planets-lab.movement-chunnel-context-game.v2
standalone Chunnel aggregate summary:
  planets-lab.movement-chunnel-context-stats.v2
```

Verified/closed movement progress:

1. ordinary movement baseline / Host major-minor geometry;
2. gravitonic movement classification;
3. warp-well ordering — `TESTED + DIFF_VERIFIED`;
4. observed tow-target context;
5. Chunnel context including route-equivalent multi-event handling — `TESTED + DIFF_VERIFIED`;
6. Horwasp ballistic strong labels with scoped 2170 topology;
7. Red Mite tracking/fallback — research closed unless new evidence appears;
8. classic ion storms selected by authoritative `settings.nuionstorms` — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
9. scoped ordinary sphere movement for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
10. generic fuel-limited/prorated movement — corpus-observed as a small residual contributor, not promoted as a broad classifier;
11. mine/web interruption + nearest damage rounding — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for the strict v5 subset.

### Immediate work

1. run `tools/diagnostics/target_origin_tow_residual_audit.py` on the current `movement_post_mine_strong_residual` corpus;
2. measure route-equivalent multiple visible tow matches, unexpected single visible matches and post-state `warp=0` overlap;
3. if multiple visible matches form a clean attributable subset, build an independent exact differential before touching production tow labels;
4. keep hidden/unresolved co-movement evidence-only until a stronger causal discriminator exists;
5. continue with generic mechanics rather than hull-specific overfitting;
6. keep repair-bracket-only mine rows out of production until repair reconstruction is independently validated.

Deprioritized/rejected leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but sparse in the generic short-forward population;
- ordinary visible tow is not the broad Warp-0 cause; the current target-origin audit is specifically about fail-closed ambiguous/route-equivalent tow evidence;
- effective-topology storm displacement is not the broad Warp-0 cause;
- hidden/private-FC Chunnel event discovery added no coverage;
- route-equivalent Chunnel multiplicity is fixed/closed;
- ordinary owner-visible Intercept is already excluded from this Move Most corpus layer;
- repair-bracket mine rows are not part of strict v5 until repair reconstruction is validated;
- do not generalize game `591478`'s 2170 period to other games;
- do not reopen Red Mite research without new evidence;
- hull count alone is not a mechanic identifier.

## M5B — Nu compatibility matrix

Status: **active through movement differential validation**.

Required outputs include mechanic-level `MATCH`, `MISMATCH`, `SKIPPED_AMBIGUOUS`, `UNSUPPORTED`, ruleset/settings splits, permanent regressions and `DIFF_VERIFIED` promotion only from clean attributable samples.

## M6 — training and AI

Status: **future**.

- scripted baseline agents;
- player-limited observation environment;
- historical imitation/value models;
- parallel self-play;
- policy/value training;
- historical-corpus offline evaluation/pretraining without hidden-information leakage.

## Working order

Unless new evidence changes priorities:

1. resolve the target-origin tow residual lead with a focused route-equivalent differential;
2. return to the largest surviving post-v5 generic families using `movement_post_mine_strong_residual` as the authoritative endpoint;
3. continue reducing movement residuals with generic mechanics rather than hull-specific rules;
4. promote the stabilized movement subset into simulator/ruleset behavior;
5. expand differential mining into economy/mines/combat/race mechanics;
6. build the broader compatibility matrix;
7. only then make M6 AI training a primary workstream.
