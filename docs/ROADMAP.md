# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-warp0-external-movement-followup.md`](handoff/2026-08-24-warp0-external-movement-followup.md).

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

The broad generic post-sphere clustering audit has been run. After excluding known Horwasp hull IDs `201-213`, the generic residual contains `854` rows across all 12 games and 82 hull IDs.

The focused generic fuel-limited audit is also complete. Among 216 short same-line candidates, only 16 have insufficient raw-snapshot fuel for the regular move, 12 bracket the observed move, and 7 satisfy the strict fuel-limit signature across six hulls and four games. Fuel-limited/prorated movement is therefore a real but **minor** current residual contributor, not the main generic closure opportunity.

The current active target is now:

```text
warp0, target=origin, external move      119 rows / 35 hulls / 8 games
```

Focused diagnostic:

```text
tools/diagnostics/warp0_external_move_context_audit.py
```

It separates visible explicit tow, hidden/unresolved co-moving ships, visible non-tow co-movement, effective-topology ion-storm vector matches, and genuinely unexplained external displacement.

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

Runtime result established two high-value generic families: short same-line-forward movement and warp-zero external displacement.

Focused fuel test:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

Runtime result:

```text
short_same_line_forward          216
insufficient_for_regular          16
formula_brackets_observed         12
affordable_frontier_match          8
strong_fuel_limit_signature        7
```

Strong signatures cross six hulls and four games, confirming the mechanic as real but too sparse to explain the 216-row family broadly.

Focused warp-zero external-context test:

```text
tools/diagnostics/warp0_external_move_context_audit.py
```

Immediate work:

1. run the warp-zero external-movement audit and preserve complete output;
2. compare rates for colocated same-destination co-movers, visible explicit tow targeting, hidden/unresolved co-movers, and effective-topology storm vector matches;
3. if tow/shared movement dominates, build a fail-closed hidden-tow/context diagnostic before touching production classification;
4. if storm-vector matches dominate in sphere game `591478`, fix the topology handling in the storm layer rather than adding a new mechanic;
5. if neither dominates, inspect the remaining examples for another pre-movement transport/context family;
6. keep Horwasp hull IDs `201-213` and closed Mite research out of generic prioritization;
7. update state docs in the same development cycle after every material result.

Deprioritized/rejected leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but only 7 strict signatures in the current generic short-forward residual, so it is not the next production target;
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

1. run and interpret the warp-zero external-movement context audit;
2. resolve whether the 119-row family is primarily hidden tow/shared movement, storm-topology leakage, or another transport effect;
3. promote only the causal, fail-closed generic context that survives focused testing;
4. keep reducing movement residuals with cross-game mechanics rather than hull-specific overfit;
5. promote the stabilized movement subset into simulator/ruleset behavior;
6. expand differential mining into economy/mines/combat/race mechanics;
7. build the broader compatibility matrix;
8. only then make M6 AI training a primary workstream.
