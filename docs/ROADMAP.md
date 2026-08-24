# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-chunnel-route-equivalent-runtime-verification.md`](handoff/2026-08-24-chunnel-route-equivalent-runtime-verification.md).

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

Last runtime-verified 12-game movement accounting:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13956
post_external_residual              3938
chunnel_explained                   1387
post_chunnel_residual               2551
horwasp_strong_explained             240
post_horwasp_strong_residual        2311
```

The scoped sphere-topology integration for game `591478` remains **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**. Raw topology remains `2150x2150`; the evidence-scoped effective `2170x2170` period closes 512 L1 rows and 442 final residual rows after overlap with prior Horwasp strong labels.

Generic post-sphere residual triage established:

- fuel-limited/prorated movement is real but sparse: 7 strict signatures among 216 short same-line candidates;
- ordinary visible tow explains only 4/119 Warp-0 external rows;
- effective-topology storm displacement explains 0/119 Warp-0 external rows;
- a structural Chunnel visibility-gap hypothesis was rejected: all 22 structural Warp-0 Chunnel matches already existed in current event discovery.

The current production fix is **route-equivalent Chunnel multi-event handling**.

Pre-fix all-corpus differential:

```text
labeled_rows                         3938
multiple_match_rows                    34
multiple_match_unexplained             34
multiple_match_post_chunnel             34
multiple_match_final_residual            34
multiple_match_warp0_self_waypoint       22
```

All 34 rows have `chunnel_match_count=2`. They occur only in games `360690` and `591478`, span six hull IDs, and split into:

```text
warp_zero_external_move  22
above_nominal            12
```

The old v3 semantics treated multiple matching events as ambiguous even though the production match predicate had already established the same candidate pre-Chunnel position and the same observed destination. Event identity/role may be ambiguous; the movement route is not.

Production now uses shared route-equivalent semantics:

```text
src/planets_lab/corpus/movement_chunnel_match.py
```

Compiled label schema is bumped to:

```text
planets-lab.compiled-movement-context-labels.v4
```

The standalone Chunnel evaluator is aligned with the same helper and uses game/stats summary schemas v2.

Expected post-fix counts, pending runtime verification:

```text
chunnel_explained             1387 -> 1421
post_chunnel_residual         2551 -> 2517
horwasp_strong_explained       240 ->  240  expected
post_horwasp_strong_residual  2311 -> 2277
```

Do not promote these expected numbers to runtime invariants until the normal v4 label build is measured.

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
```

Verified/closed movement progress:

1. ordinary movement baseline / Host major-minor geometry;
2. gravitonic movement classification;
3. warp-well ordering — `TESTED + DIFF_VERIFIED`;
4. observed tow-target context;
5. Chunnel context layer — route-equivalent multi-event semantic fix implemented, runtime differential pending;
6. Horwasp ballistic strong labels with scoped 2170 topology;
7. Red Mite tracking/fallback — research closed unless new evidence appears;
8. classic ion storms selected by authoritative `settings.nuionstorms` — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
9. scoped ordinary sphere movement for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
10. generic fuel-limited/prorated movement — corpus-observed as a small residual contributor, not yet promoted as an L1 classifier.

Recent verified residual changes:

```text
classic storms:
  post_external_residual    6174 -> 4450
  final strong residual     4477 -> 2753

scoped sphere topology:
  post_external_residual    4450 -> 3938  (-512)
  post_chunnel_residual     3063 -> 2551  (-512)
  horwasp strong             310 ->  240  (-70 overlap)
  final strong residual     2753 -> 2311  (-442)
```

### Current diagnostic sequence

Broad clustering:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

Focused fuel test:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

Result: 7 strict signatures among 216 short-forward candidates; real but minor.

Focused Warp-0 external-context test:

```text
tools/diagnostics/warp0_external_move_context_audit.py
```

Result: only 4 visible explicit tow matches, zero hidden/unresolved co-movers, zero effective-topology storm-vector matches, but 31 visible non-tow same-route co-movements.

Focused structural Chunnel-gap test:

```text
tools/diagnostics/warp0_chunnel_gap_audit.py
```

Result: 22 structural matches, all 22 with numeric-FC support and all 22 already represented by existing event discovery. Event-discovery visibility gap rejected.

All-corpus route-equivalent ambiguity differential:

```text
tools/diagnostics/chunnel_route_equivalent_ambiguity_audit.py
```

Pre-fix result: 34 multiple-match rows, all 34 current Chunnel residuals and all 34 final residuals.

Immediate work:

1. pull the route-equivalent production fix;
2. run targeted Chunnel/compiled-label tests and full pytest;
3. run the L2 label compiler normally without `--rebuild`;
4. verify v4 invalidates old label caches automatically and prepared caches remain reusable;
5. verify exact differential against `+34 Chunnel / -34 final residual`;
6. re-run the ambiguity audit and require zero multiple-match unexplained/final residual rows;
7. rebaseline state docs from measured output;
8. only then resume triage on the remaining generic movement residual.

Deprioritized/rejected leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but only 7 strict signatures in the current generic short-forward residual;
- ordinary visible tow explains only 4/119 Warp-0 external rows;
- effective-topology storm vector explains 0/119 Warp-0 external rows;
- hidden/private-FC Chunnel event discovery explains 0 additional rows in the focused Warp-0 population;
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

1. runtime-verify the route-equivalent Chunnel v4 label fix;
2. close the exact `34`-row differential and update durable corpus counts;
3. resume generic triage on the remaining non-Horwasp residual population;
4. keep reducing movement residuals with cross-game mechanics rather than hull-specific overfit;
5. promote the stabilized movement subset into simulator/ruleset behavior;
6. expand differential mining into economy/mines/combat/race mechanics;
7. build the broader compatibility matrix;
8. only then make M6 AI training a primary workstream.
