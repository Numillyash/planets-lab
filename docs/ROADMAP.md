# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-chunnel-route-equivalent-verified.md`](handoff/2026-08-24-chunnel-route-equivalent-verified.md).

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
```

The scoped sphere-topology integration for game `591478` remains **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**. Raw topology remains `2150x2150`; the evidence-scoped effective `2170x2170` period closes 512 L1 rows and 442 final residual rows after overlap with prior Horwasp strong labels.

The route-equivalent Chunnel v4 semantic fix is also **TESTED + DIFF_VERIFIED**. A pre-fix all-corpus audit measured exactly 34 false residuals with `chunnel_match_count=2`; the normal v4 label build closed exactly those 34 rows:

```text
chunnel_explained             1387 -> 1421  (+34)
post_chunnel_residual         2551 -> 2517  (-34)
horwasp_strong_explained       240 ->  240  (unchanged)
post_horwasp_strong_residual  2311 -> 2277  (-34)
```

Post-fix validation:

```text
multiple_match_rows                 34
multiple_match_unexplained           0
multiple_match_post_chunnel           0
multiple_match_final_residual          0
old_ambiguous_category                0
```

Generic post-sphere residual triage established:

- fuel-limited/prorated movement is real but sparse: 7 strict signatures among 216 short same-line candidates;
- ordinary visible tow explained only 4/119 pre-v4 Warp-0 external rows;
- effective-topology storm displacement explained 0/119 pre-v4 Warp-0 external rows;
- hidden/private-FC Chunnel event discovery added 0 rows;
- 22 of the 119 pre-v4 Warp-0 rows were Chunnel route-equivalent false residuals and are now closed by v4.

The active task is therefore **post-v4 generic residual re-triage**, not another immediate production rule.

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
5. Chunnel context layer, including route-equivalent multi-event handling — `TESTED + DIFF_VERIFIED`;
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

route-equivalent Chunnel v4:
  chunnel_explained         1387 -> 1421  (+34)
  post_chunnel_residual     2551 -> 2517  (-34)
  final strong residual     2311 -> 2277  (-34)
```

### Current diagnostic sequence

Existing broad generic clustering:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

Existing Warp-0 external-context audit:

```text
tools/diagnostics/warp0_external_move_context_audit.py
```

Immediate work:

1. rerun the broad generic clustering audit against the v4 `2277` final residual;
2. rerun the Warp-0 external-context audit after removal of the 22 Chunnel false residuals;
3. compare the refreshed short-forward, Warp-0, displacement-vector, hull and game distributions;
4. choose the next target only if it is cross-game/cross-hull and causally testable;
5. keep Horwasp hull IDs `201-213` and closed Mite research out of generic prioritization;
6. preserve the verified fuel-proration examples but do not promote a broad fuel classifier from 7 strict signatures;
7. update durable state docs after each material runtime result.

Deprioritized/rejected leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but sparse in the current generic short-forward population;
- ordinary visible tow was not the broad pre-v4 Warp-0 cause;
- effective-topology storm displacement was not the broad pre-v4 Warp-0 cause;
- hidden/private-FC Chunnel event discovery added no coverage in the focused population;
- route-equivalent Chunnel multiplicity is now fixed/closed;
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

1. refresh generic clustering on the post-v4 final residual;
2. select the next cross-game mechanic/context from measured evidence;
3. keep reducing movement residuals with generic mechanics rather than hull-specific overfit;
4. promote the stabilized movement subset into simulator/ruleset behavior;
5. expand differential mining into economy/mines/combat/race mechanics;
6. build the broader compatibility matrix;
7. only then make M6 AI training a primary workstream.
