# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-24-chunnel-route-equivalent-ambiguity.md`](handoff/2026-08-24-chunnel-route-equivalent-ambiguity.md).

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

The focused generic fuel-limited audit is complete. Among 216 short same-line candidates, only 16 have insufficient raw-snapshot fuel for the regular move, 12 bracket the observed move, and 7 satisfy the strict fuel-limit signature across six hulls and four games. Fuel-limited/prorated movement is therefore real but a **minor** current residual contributor.

The Warp-0 external-movement audit is also complete:

```text
candidate_rows                               119
has_colocated_same_destination_comover        31
single_colocated_same_destination_comover       7
visible_explicit_tow_target_match               4
has_hidden_or_unresolved_comover                0
has_visible_non_tow_comover                    31
effective_topology_storm_vector_match           0
```

A follow-up structural Chunnel audit found:

```text
structural_chunnel_match                22
numeric_fc_structural_match             22
structural_without_numeric_fc_match      0
existing_classifier_event_match         22
missed_by_existing_event_discovery       0
```

So hidden/private friendly-code event discovery is **not** the missing Chunnel context in this population. All 22 structural Chunnel-shaped rows are already represented by current event discovery.

The active production bug candidate is now **route-equivalent Chunnel event multiplicity**. Production matches are already restricted to identical candidate pre-Chunnel position and identical observed destination, but rows with more than one matching event are currently labeled `ambiguous_matching_events` and left residual. The DB-only pre-fix differential audit is:

```text
tools/diagnostics/chunnel_route_equivalent_ambiguity_audit.py
```

A shared pure helper defining the intended route-equivalent semantics is already present at:

```text
src/planets_lab/corpus/movement_chunnel_match.py
```

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
5. Chunnel context layer — implemented; current work is correcting route-equivalent multi-event residual handling rather than changing the Chunnel mechanic itself;
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

Result: `7` strict signatures among `216` short-forward candidates; real but minor.

Focused Warp-0 external-context test:

```text
tools/diagnostics/warp0_external_move_context_audit.py
```

Result: only 4 visible explicit tow matches, zero hidden/unresolved co-movers, zero effective-topology storm-vector matches, but 31 visible non-tow same-route co-movements.

Focused structural Chunnel-gap test:

```text
tools/diagnostics/warp0_chunnel_gap_audit.py
```

Result: `22` structural matches, all `22` with numeric-FC support and all `22` already represented by existing event discovery. Event-discovery visibility gap rejected.

Pre-fix route-equivalent ambiguity differential:

```text
tools/diagnostics/chunnel_route_equivalent_ambiguity_audit.py
```

Immediate work:

1. run the all-corpus route-equivalent ambiguity audit and preserve complete output;
2. measure `multiple_match_rows`, `multiple_match_post_chunnel`, `multiple_match_final_residual`, match-count distribution and baseline/game/hull coverage;
3. if the population is material, change L2 semantics so any non-empty route-equivalent match set closes Chunnel movement while role ambiguity remains descriptive only;
4. bump compiled context-label schema so old L2 caches invalidate automatically;
5. add deterministic duplicate-initiator/same-route regressions and rebuild L2 normally without `--rebuild`;
6. compare exact post-fix residual deltas against the pre-fix audit;
7. keep the known Chunnel storm-mode/effective-topology caveat separate unless runtime evidence intersects it;
8. keep Horwasp hull IDs `201-213` and closed Mite research out of generic prioritization;
9. update state docs in the same development cycle after every material result.

Deprioritized/rejected leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but only 7 strict signatures in the current generic short-forward residual, so it is not the next production target;
- ordinary visible tow explains only 4/119 Warp-0 external rows and is not the broad missing context;
- effective-topology storm vector explains 0/119 Warp-0 external rows;
- hidden/private-FC Chunnel event discovery explains 0 additional rows in the focused 119-row population;
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

1. run and interpret the all-corpus route-equivalent Chunnel ambiguity audit;
2. if confirmed, fix compiled L2 multi-event handling and verify exact differential closure;
3. otherwise resume generic triage on the non-group Warp-0 external moves;
4. keep reducing movement residuals with cross-game mechanics rather than hull-specific overfit;
5. promote the stabilized movement subset into simulator/ruleset behavior;
6. expand differential mining into economy/mines/combat/race mechanics;
7. build the broader compatibility matrix;
8. only then make M6 AI training a primary workstream.
