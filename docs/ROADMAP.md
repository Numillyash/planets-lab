# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-mine-damage-rounding-followup.md`](handoff/2026-08-24-mine-damage-rounding-followup.md).

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

Current runtime-verified 12-game movement accounting remains:

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
```

Verified recent closures:

- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multi-event handling — `TESTED + DIFF_VERIFIED`.

The Chunnel v4 differential closed exactly as predicted:

```text
chunnel_explained             1387 -> 1421  (+34)
post_chunnel_residual         2551 -> 2517  (-34)
horwasp_strong_explained       240 ->  240
post_horwasp_strong_residual  2311 -> 2277  (-34)
```

## Post-v4 generic residual landscape

Measured after Chunnel v4:

```text
final_residual_rows       2277
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               820
generic_games               12
generic_hulls               81
```

Largest generic signatures include:

```text
warp7-9  <0.5x    observed=other  same_line_forward   133 rows / 26 hulls / 7 games
warp0    nominal<=0 target=origin target_is_origin     97 rows / 33 hulls / 8 games
warp7-9  0.5-1.0x observed=other  same_line_forward    70 rows / 26 hulls / 8 games
warp7-9  <0.5x    observed=origin observed_stationary   64 rows / 30 hulls / 5 games
warp7-9  >3.0x    target=origin   target_is_origin      52 rows / 15 hulls / 4 games
warp7-9  >3.0x    observed=other  oblique               46 rows / 21 hulls / 4 games
```

Warp-0 remains heterogeneous after the exact Chunnel subtraction:

```text
candidate_rows                                97
has_colocated_same_destination_comover        11
single_colocated_same_destination_comover      3
visible_explicit_tow_target_match              4
has_hidden_or_unresolved_comover               0
has_visible_non_tow_comover                   11
effective_topology_storm_vector_match          0
```

## Active focused target — mine/web interruption and NuHost damage rounding

The strongest generic family is short movement along the intended waypoint line. Prior fuel analysis explains only seven strict fuel-limit examples among 216 non-Gravitonic short same-line rows. Ordinary owner-visible Intercept is already excluded by the corpus intent classifier.

Two mine/web diagnostics are now runtime-complete:

```text
tools/diagnostics/mine_hit_residual_audit.py
tools/diagnostics/mine_hit_hostorder_differential_audit.py
```

Host-order population reconciliation:

```text
generic_non_horwasp_warp1_9_rows  718
raw_short_same_line                235
raw_short_non_gravitonic           216
raw_short_gravitonic                19
effective_short_same_line          238
effective_short_non_gravitonic     216
effective_short_gravitonic          22
after_identity_break                 0
same_identity_after                238
```

### Web evidence

```text
web_state_signature                       19
web_after_field_strong                    18
owner_after_visible_web_at_observed      140
persistent_web_at_observed                94
```

The 18 field-backed stop-state rows span all three corpus games with observed web records. This is material cross-hull/cross-game `CORPUS_OBSERVED` evidence for web interruption.

### Normal-mine evidence

```text
normal_mine_10ly_geometry                 54
normal_after_field_strong                 25
normal_exact_distance_damage               7
normal_exact_damage_after_field             7
normal_exact_damage_no_after_field          0
```

The 25 field-backed rows combine low-tech ~10-ly slowdown, damage increase and after-turn enemy normal-mine corridor crossing across multiple hulls and games.

### Documentation/implementation discrepancy under investigation

Planets.nu documentation states mine-impact damage is rounded up:

```text
normal: 10000 / (Hull Mass + 1)
web:     1000 / (Hull Mass + 1)
```

But historical field-backed examples repeatedly look like nearest-integer rounding instead of unconditional ceiling, for example:

```text
1000/121   = 8.264...  -> observed 8
10000/181  = 55.249... -> observed 55
10000/161  = 62.112... -> observed 62 / 124
1000/251   = 3.984...  -> observed 4
```

This is currently `INFERRED`, not a production rule.

Repair is an explicit confounder: five supplies repair one damage percentage point, and Host Order performs a repair phase after Most Ships Move. Therefore the strongest damage-rounding evidence is an undamaged-start row with fewer than five supplies.

Focused rounding diagnostic:

```text
tools/diagnostics/mine_hit_damage_rounding_audit.py
```

It compares `ceil`, `floor` and positive nearest rounding on field-backed rows and reports no-field controls before any label or simulator rule is promoted.

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
- separate L2 context-label layer for Chunnel/Horwasp evidence.

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
  planets-lab.compiled-movement-context-labels.v4
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
10. generic fuel-limited/prorated movement — corpus-observed as a small residual contributor, not yet promoted;
11. mine/web movement interruption — `DOCUMENTED + CORPUS_OBSERVED`, production integration pending exact rounding/repair differential.

Recent verified residual changes remain:

```text
classic storms:
  post_external_residual    6174 -> 4450
  final strong residual     4477 -> 2753

scoped sphere topology:
  post_external_residual    4450 -> 3938  (-512)
  post_chunnel_residual     3063 -> 2551  (-512)
  horwasp strong             310 ->  240  (-70 overlap)
  final strong residual     2753 -> 2311  (-442)

route-equivalent Chunnel v4:
  chunnel_explained         1387 -> 1421  (+34)
  post_chunnel_residual     2551 -> 2517  (-34)
  final strong residual     2311 -> 2277  (-34)
```

Mine diagnostics have not changed these production counts.

### Current diagnostic sequence

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
tools/diagnostics/warp0_external_move_context_audit.py
tools/diagnostics/mine_hit_residual_audit.py
tools/diagnostics/mine_hit_hostorder_differential_audit.py
tools/diagnostics/mine_hit_damage_rounding_audit.py
```

Immediate work:

1. run the damage-rounding differential against the current `2277` final residual;
2. compare `ceil`, `floor` and positive-nearest matches on web/normal field-backed rows;
3. require cross-hull/cross-game separation and sparse no-after-field controls;
4. treat rows with >=5 supplies as repair-contaminated unless separately reconstructed;
5. if nearest-integer wins decisively, record a NuHost/documentation compatibility discrepancy and add deterministic regression cases;
6. only then implement a narrow mine/web context classifier and measure its exact corpus delta;
7. if rounding does not separate cleanly, investigate repair/impact-order details before production changes;
8. keep Horwasp hull IDs `201-213`, Red Mite and closed Chunnel work out of generic prioritization.

Deprioritized/rejected leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but sparse in the generic short-forward population;
- ordinary visible tow is not the broad Warp-0 cause;
- effective-topology storm displacement is not the broad Warp-0 cause;
- hidden/private-FC Chunnel event discovery added no coverage;
- route-equivalent Chunnel multiplicity is fixed/closed;
- ordinary owner-visible Intercept is already excluded from this Move Most corpus layer;
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

1. resolve mine/web damage rounding on field-backed corpus rows;
2. promote only a cross-game causal signature that survives Host-order and repair controls;
3. add regression-backed mine/web context if supported;
4. otherwise resume generic residual triage rather than overfit minefields;
5. keep reducing movement residuals with generic mechanics rather than hull-specific rules;
6. promote stabilized movement behavior into simulator/ruleset code;
7. expand differential mining into economy/mines/combat/race mechanics;
8. build the broader compatibility matrix;
9. only then make M6 AI training a primary workstream.
