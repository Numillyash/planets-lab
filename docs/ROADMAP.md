# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-generic-fuel-followup.md`](handoff/2026-08-24-generic-fuel-followup.md).

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
chunnel_explained                   1387
post_chunnel_residual               2551
horwasp_strong_explained             240
post_horwasp_strong_residual        2311
```

The scoped sphere-topology integration for game `591478` is **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**. Raw topology remains `2150x2150`; the evidence-scoped effective `2170x2170` period closes 512 L1 rows and 442 final residual rows after overlap with prior Horwasp strong labels.

The broad generic post-sphere clustering audit has now been run. After excluding known Horwasp hull IDs `201-213`, the generic residual contains `854` rows across all 12 games and 82 hull IDs.

The current active hypothesis is **generic fuel-limited / prorated movement**. The strongest cross-game geometry is short movement that stays aligned with the waypoint, especially:

```text
warp7-9, <0.5x, same_line_forward       133 rows / 26 hulls / 7 games
warp7-9, 0.5-1.0x, same_line_forward     70 rows / 26 hulls / 8 games
warp7-9, ~0.5x, same_line_forward         29 rows / 15 hulls / 7 games
```

Focused diagnostic:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

It is implemented and awaiting runtime output. It tests fuel-before/after, engine fuel factor, raw mass, formula affordability, maximum affordable whole-ly distance and same-identity continuity across all non-Horwasp short-forward rows. Game `591478` uses the already-verified effective 2170 topology in this diagnostic so sphere geometry does not contaminate the fuel hypothesis.

The main fallback generic cluster if fuel coverage is weak is:

```text
warp0, target=origin, external move      119 rows / 35 hulls / 8 games
```

That family likely represents an external displacement/transport effect and should be split into hidden tow / storm / other pre-movement context only after the fuel hypothesis is resolved.

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

Race-specific behavior belongs in explicit ruleset modules/hooks. Important families include Privateer gravitonic/rob, Crystal webs, Cyborg chunnel, Fascist pillage/glory, Bird cloak/super-spy, Rebel RGA, Colonial fighter sweep and Horwasp mechanics.

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
  planets-lab.compiled-movement-context-labels.v3
```

Verified/closed movement progress:

1. ordinary movement baseline / Host major-minor geometry;
2. gravitonic movement classification;
3. warp-well ordering — `TESTED + DIFF_VERIFIED`;
4. observed tow-target context;
5. Chunnel context layer;
6. Horwasp ballistic strong labels with scoped 2170 topology;
7. Red Mite tracking/fallback — research closed unless new evidence appears;
8. classic ion storms selected by authoritative `settings.nuionstorms` — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
9. scoped ordinary sphere movement for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`.

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

Runtime result established two high-value generic families: short same-line-forward movement and warp-zero external displacement.

Focused fuel test:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

Immediate work:

1. run the focused fuel diagnostic and preserve complete output;
2. measure `short_same_line_forward`, `formula_brackets_observed`, `strong_fuel_limit_signature`, distinct hull/game coverage and sufficient-fuel false negatives;
3. promote a production fuel-proration context only if the strong signature is broad, causal and fail-closed;
4. if fuel coverage is sparse, move directly to the `warp0 + target=origin + external move` family;
5. keep Horwasp hull IDs `201-213` and closed Mite research out of generic prioritization;
6. update state docs in the same development cycle after every material result.

Deprioritized/rejected leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
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

1. run and interpret the generic fuel-limited residual audit;
2. either integrate fuel proration if strongly supported or pivot to warp-zero external displacement;
3. keep reducing movement residuals with cross-game mechanics rather than hull-specific overfit;
4. promote the stabilized movement subset into simulator/ruleset behavior;
5. expand differential mining into economy/mines/combat/race mechanics;
6. build the broader compatibility matrix;
7. only then make M6 AI training a primary workstream.
