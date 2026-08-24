# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-route-equivalent-tow-runtime-verification.md`](handoff/2026-08-24-route-equivalent-tow-runtime-verification.md).

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

Last runtime-verified 12-game movement accounting, before the pending Tow v3 rebuild:

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

The active pending change is **route-equivalent visible Tow handling in L1**.

## Post-v5 generic residual landscape

The broad clustering against the verified final view `movement_post_mine_strong_residual` measured:

```text
final_residual_rows       2240
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               783
generic_games               12
generic_hulls               79
```

Largest surviving coarse signatures:

```text
121  warp7-9 <0.5x     observed=other same_line_forward
 97  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 48  warp7-9 0.5-1.0x observed=other same_line_forward
 46  warp7-9 >3.0x     observed=other oblique
```

The mine/web fix materially reduced short-forward residuals but did not eliminate that family. The next investigation switched to target-at-origin external movement because it gives stronger structural evidence about movement by another actor.

## Route-equivalent Tow finding — implemented, runtime pending

Focused diagnostic:

```text
tools/diagnostics/target_origin_tow_residual_audit.py
```

Verified focused runtime result:

```text
candidate_rows                              226
post_warp0                                  116
has_same_origin_destination_comover          35
has_hidden_or_unresolved_comover              0
has_visible_tow_targeter                     92
visible_tow_targeter_other_destination       88
any_visible_matching_tower                    4
single_visible_matching_tower                 0
route_equivalent_multiple_visible_towers      4
```

The four matching rows span four games and four hulls. Each has exactly two owner-visible Tow towers that:

- target the candidate ship;
- start colocated with it;
- finish at its same non-stationary observed destination.

All four targets finish at Warp 0.

The old `_observed_tow_targets()` treated multiple matches as unresolved because tower identity was ambiguous. That is a semantic error: the actual Tow winner may be ambiguous, but the target movement route is already fixed by every matching tower.

Production source now preserves all matching tower IDs and treats any non-empty matching set as movement evidence. It does not choose an arbitrary winning tower.

Implemented schema changes:

```text
movement residual context:
  planets-lab.movement-residual-context-game.v2
  planets-lab.movement-residual-context-stats.v2

compiled L1 movement:
  planets-lab.compiled-movement.v3
```

`compiled-movement.v3` has the same columns as v2; the bump is a semantic cache invalidation marker.

L2 remains:

```text
planets-lab.compiled-movement-context-labels.v5
```

The label cache is still invalidated automatically after the L1 rebuild because label metadata binds to the current source movement schema and exact source movement Parquet hash.

### Global differential required before rebuild

The four focused rows are a lower bound, not yet assumed to be the full corpus delta. The existing Tow helper applies to all external residual geometry, not only target-at-origin rows.

Run first:

```text
tools/diagnostics/tow_route_equivalent_global_differential_audit.py
```

It scans all old `movement_labeled_residual` rows and reports route-equivalent multiple visible Tow matches partitioned by current downstream stage.

Critical negative control:

```text
single_visible_matching_tower = 0
```

If this is non-zero, stop and investigate because ordinary single Tow matches should already have been removed by the verified old L1 external layer.

The global audit, not the four focused examples, defines the expected L1/L2 accounting delta.

If the global population happens to be exactly those four final-residual rows, the conditional expected endpoint is:

```text
external_context_explained  13960
post_external_residual       3934
chunnel_explained            1421
post_chunnel_residual        2513
horwasp_strong_explained      240
post_horwasp_strong_residual 2273
mine_strong_explained          37
post_mine_strong_residual     2236
```

These are **not runtime invariants yet**.

## Mine/web movement interruption — verified v5 mechanic

Mine/web work is closed for the strict subset.

Key independent evidence:

```text
web_nearest_delta_match_after_field        18
normal_nearest_delta_multiple_after_field  19
web_nearest_control_no_after_field          0
normal_nearest_control_no_after_field       0
```

Production reproduced exactly:

```text
post_horwasp_strong_residual  2277
mine_strong_explained           37
post_mine_strong_residual     2240
```

Strict categories:

```text
web_mine_hit_nearest_damage       18
normal_mine_hit_nearest_damage    19
```

Historical NuHost evidence selects positive nearest-integer mine damage rather than the documentation's literal round-up wording. Keep that distinction explicit.

Repair-bracket-only rows remain outside production until repair reconstruction is independently validated.

## Chunnel v4 — verified closure

The pre-fix route-equivalent Chunnel audit predicted 34 false residuals. Production reproduced exactly:

```text
chunnel_explained             1387 -> 1421
post_chunnel_residual         2551 -> 2517
horwasp_strong_explained       240 ->  240
post_horwasp_strong_residual  2311 -> 2277
```

Status: **TESTED + DIFF_VERIFIED**. Do not reopen without fresh evidence.

## Test state

Before the active Tow source changes, targeted v5 tests and the full pytest suite were green on a clean tree.

The new Tow route-equivalence regression is implemented in:

```text
tests/test_movement_residual_context.py
```

The new v3 source state still requires targeted and full pytest runtime verification before it is marked `TESTED`.

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
- ordinary movement, movement mass, fuel use and fuel-proration primitives;
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

Implemented schemas on `main`:

```text
corpus manifest:
  planets-lab.corpus-game.v2
prepared cache:
  planets-lab.prepared-game-cache.v1
compiled movement:
  planets-lab.compiled-movement.v3
post-compile external-context semantics:
  planets-lab.compiled-movement-storm-context.v2
compiled context labels:
  planets-lab.compiled-movement-context-labels.v5
movement residual context:
  planets-lab.movement-residual-context-game.v2
  planets-lab.movement-residual-context-stats.v2
standalone Chunnel:
  planets-lab.movement-chunnel-context-game.v2
  planets-lab.movement-chunnel-context-stats.v2
```

Verified/closed movement progress:

1. ordinary movement baseline / Host major-minor geometry;
2. gravitonic movement classification;
3. warp-well ordering — `TESTED + DIFF_VERIFIED`;
4. owner-visible Tow target context — current multiplicity fix pending runtime verification;
5. Chunnel route-equivalent multi-event handling — `TESTED + DIFF_VERIFIED`;
6. Horwasp ballistic strong labels with scoped 2170 topology;
7. Red Mite tracking/fallback — research closed absent new evidence;
8. classic ion storms selected by authoritative `settings.nuionstorms` — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
9. scoped ordinary sphere movement for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
10. generic fuel-limited/prorated movement — corpus-observed as a small residual contributor, not promoted as a broad classifier;
11. mine/web interruption + nearest damage rounding — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for the strict v5 subset.

### Immediate work

1. pull current `main` and confirm clean tree;
2. run syntax check;
3. run `tow_route_equivalent_global_differential_audit.py` against the still-old verified corpus **before** L1 rebuild;
4. confirm `single_visible_matching_tower = 0` and record the global multiple-match stage distribution;
5. run targeted tests and full pytest;
6. run normal L1 v3 build without `--rebuild` and verify 0/12 compiled-cache reuse + 12/12 prepared-cache reuse;
7. run normal L2 v5 build without `--rebuild` and verify source-schema/hash invalidation;
8. compare layer accounting exactly with the global differential;
9. rerun target-origin audit and broad generic clustering on the rebuilt final view;
10. choose the next generic residual family only after that rebaseline.

Deprioritized/rejected leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but sparse in the generic short-forward population;
- hidden/private-FC Chunnel event discovery added no coverage;
- route-equivalent Chunnel multiplicity is fixed/closed;
- ordinary owner-visible Intercept is already excluded from the Move Most corpus layer;
- target-origin visible non-Tow co-movement is evidence only, not a Tow classifier;
- the focused Tow audit found no hidden/unresolved co-movers;
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

1. close route-equivalent Tow v3 with the global pre-build differential and normal L1/L2 runtime builds;
2. rebaseline the final generic residual;
3. continue reducing movement residuals with generic mechanics rather than hull-specific rules;
4. promote the stabilized movement subset into simulator/ruleset behavior;
5. expand differential mining into economy/mines/combat/race mechanics;
6. build the broader compatibility matrix;
7. only then make M6 AI training a primary workstream.
