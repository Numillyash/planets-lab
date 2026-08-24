# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-route-equivalent-tow-verified.md`](handoff/2026-08-24-route-equivalent-tow-verified.md).

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
external_context_explained         13960
post_external_residual              3934
chunnel_explained                   1421
post_chunnel_residual               2513
horwasp_strong_explained             240
post_horwasp_strong_residual        2273
mine_strong_explained                 37
post_mine_strong_residual           2236
label_issues                           0
```

Verified recent closures:

- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multi-event handling — `TESTED + DIFF_VERIFIED`;
- strict mine/web interruption context v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent visible Tow handling in L1 v3 — `TESTED + DIFF_VERIFIED`.

The active task is now **post-v3 generic residual rebaseline** against `movement_post_mine_strong_residual`.

## Route-equivalent Tow v3 — verified closure

Focused target-origin evidence first exposed four false residuals with exactly two owner-visible matching Tow towers and zero single-match misses.

The global pre-build differential then scanned all old `3938` external residual rows and found exactly:

```text
any_visible_matching_tower                    4
single_visible_matching_tower                 0
route_equivalent_multiple_visible_towers      4
```

All four were in the old final residual and all had `warp_zero_external_move` baseline geometry. The predicted production delta was therefore:

```text
external_context_explained       +4
post_external_residual           -4
chunnel_explained                 0
horwasp_strong_explained          0
mine_strong_explained             0
post_mine_strong_residual        -4
```

Normal L1 v3 build without `--rebuild` produced:

```text
compiled_cache_hits                0
compiled_cache_misses             12
prepared_cache_hits_on_compile    12
prepared_cache_misses_on_compile   0
```

Normal L2 v5 build then produced:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
```

Every resulting layer count matched the independently calculated expectation exactly, with runtime result:

```text
ACCOUNTING DIFFERENTIAL: EXACT MATCH
```

Post-fix global Tow audit:

```text
external_residual_rows= 3934
any_visible_matching_tower= 0
single_visible_matching_tower= 0
route_equivalent_multiple_visible_towers= 0
```

Status: **TESTED + DIFF_VERIFIED**. Do not reopen without fresh contradictory evidence.

## Generic residual landscape

The previous broad clustering was measured before the Tow v3 fix:

```text
final_residual_rows       2240
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               783
generic_games               12
generic_hulls               79
```

Largest coarse families at that historical endpoint included:

```text
121  warp7-9 <0.5x     observed=other same_line_forward
 97  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 48  warp7-9 0.5-1.0x observed=other same_line_forward
 46  warp7-9 >3.0x     observed=other oblique
```

Those counts are no longer the active selection baseline because four final-residual Tow rows were removed. Rerun:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

against the current `2236` final endpoint before choosing the next mechanic family.

## Mine/web movement interruption — verified v5 mechanic

Mine/web work is closed for the strict subset.

Independent evidence predicted exactly:

```text
web_nearest_delta_match_after_field        18
normal_nearest_delta_multiple_after_field  19
web_nearest_control_no_after_field          0
normal_nearest_control_no_after_field       0
```

Production still classifies:

```text
web_mine_hit_nearest_damage       18
normal_mine_hit_nearest_damage    19
mine_strong_explained             37
```

Historical NuHost evidence selects positive nearest-integer mine damage rather than the documentation's literal round-up wording. Keep that distinction explicit.

Repair-bracket-only rows remain outside production until repair reconstruction is independently validated.

## Chunnel v4 — verified closure

The pre-fix route-equivalent Chunnel audit predicted 34 false residuals and production reproduced exactly the predicted Chunnel delta. Status: **TESTED + DIFF_VERIFIED**. Do not reopen without fresh evidence.

## Test state

The route-equivalent Tow migration was verified with:

```text
targeted regression set: 26 passed
full pytest suite:        green
```

The repository source state and current compiled corpus are aligned on L1 v3 + L2 v5.

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

Current schemas:

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
4. owner-visible Tow target context including route-equivalent multiplicity — `TESTED + DIFF_VERIFIED`;
5. Chunnel route-equivalent multi-event handling — `TESTED + DIFF_VERIFIED`;
6. Horwasp ballistic strong labels with scoped 2170 topology;
7. Red Mite tracking/fallback — research closed absent new evidence;
8. classic ion storms selected by authoritative `settings.nuionstorms` — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
9. scoped ordinary sphere movement for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
10. generic fuel-limited/prorated movement — corpus-observed as a small residual contributor, not promoted as a broad classifier;
11. mine/web interruption + nearest damage rounding — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for the strict v5 subset.

### Immediate work

1. pull current `main` and confirm a clean tree;
2. run `tools/diagnostics/post_sphere_generic_residual_clustering_audit.py` on `movement_post_mine_strong_residual`;
3. record the new final/generic row counts and largest cross-hull/cross-game signatures;
4. compare the new clustering against the historical `2240/783/79` baseline and identify exactly which family lost the four Tow rows;
5. choose the next generic residual family only from the new endpoint;
6. build a focused differential before changing production classification.

Deprioritized/rejected/closed leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but sparse in the generic short-forward population;
- hidden/private-FC Chunnel event discovery added no coverage;
- route-equivalent Chunnel multiplicity is fixed/closed;
- route-equivalent visible Tow multiplicity is fixed/closed;
- ordinary owner-visible Intercept is already excluded from the Move Most corpus layer;
- target-origin visible non-Tow co-movement is evidence only, not a Tow classifier;
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

1. rebaseline the final generic residual after Tow v3;
2. continue reducing movement residuals with generic mechanics rather than hull-specific rules;
3. promote the stabilized movement subset into simulator/ruleset behavior;
4. expand differential mining into economy/mines/combat/race mechanics;
5. build the broader compatibility matrix;
6. only then make M6 AI training a primary workstream.
