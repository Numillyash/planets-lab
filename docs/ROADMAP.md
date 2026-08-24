# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-25-damage-limited-warp-runtime-verification.md`](handoff/2026-08-25-damage-limited-warp-runtime-verification.md).

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

The active production change is now **strict damage-limited maximum warp in the ordered L1 external-context stack**, implemented but runtime rebuild verification pending.

## Current generic residual landscape — post-v3

Broad clustering against the current final view `movement_post_mine_strong_residual` measured:

```text
final_residual_rows       2236
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               779
generic_games               12
generic_hulls               78
```

Main coarse signatures:

```text
121  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 48  warp7-9 0.5-1.0x observed=other same_line_forward
 46  warp7-9 >3.0x     observed=other oblique
```

The dominant short-forward family spans `26` hulls across `7` games.

## Damage-limited maximum warp — implemented, runtime pending

Independent diagnostic:

```text
tools/diagnostics/damage_limited_warp_residual_audit.py
```

Runtime result on the verified `2236` endpoint:

```text
generic_non_horwasp_warp1_9_rows  681
target_short_forward_rows          121
same_identity_after                444
identity_break_after               237
formula_ready                      444
damaged_before                      61
undamaged_before                   383
raw_damage_limited                  11
raw_not_damage_limited             433
```

Exact differential:

```text
raw_damage_limited_endpoint_exact                10
raw_exact_low_supply                             10
raw_not_damage_limited_endpoint_exact_control      0
undamaged_endpoint_exact_control                   0
```

Coverage of the 10 exact rows:

```text
9 games
8 hulls
6 races
effective warp buckets: 1, 3, 4, 5, 6, 7, 8
```

Only `2` of the dominant `121` short-forward rows are explained. Thus damage-limited warp is a real sparse generic mechanic, not the main explanation of that family.

### Strict production predicate

Implemented module:

```text
src/planets_lab/corpus/movement_damage_context.py
```

Category:

```text
damage_limited_warp_match
```

Only rows still unresolved after existing L1 contexts are eligible. Production requires:

```text
non-Horwasp hull
resolved owner/race
same ship identity after transition
requested warp 1..9
visible supplies < 5 KT
documented raw-damage max warp < requested warp
exact Host-major/minor endpoint at effective warp
```

Gravitonic distance and scoped effective sphere geometry are preserved. Repair-bracket-only rows are excluded.

The Planets.nu `Damage - Details` page documents the speed table but marks itself outdated/superseded; therefore promotion is grounded primarily in the corpus differential plus zero controls rather than documentation alone. Host Order independently confirms that mass-check/repair occurs before Tow and Most Ships Move.

### L1 semantic cache migration

Physical L1 remains:

```text
planets-lab.compiled-movement.v3
```

The historical post-compile marker now represents the ordered stack:

```text
authoritative storm mode
  -> scoped effective sphere geometry
  -> strict damage-limited warp
```

and is bumped:

```text
planets-lab.compiled-movement-storm-context.v2
  -> planets-lab.compiled-movement-storm-context.v3
```

L2 remains `planets-lab.compiled-movement-context-labels.v5`; changed source Parquet hashes must invalidate stale labels automatically.

### Expected differential

All 10 independent exact rows currently survive to the final post-mine residual. Expected normal-build accounting:

```text
external_context_explained        13960 -> 13970
post_external_residual             3934 ->  3924
chunnel_explained                  1421 ->  1421
post_chunnel_residual              2513 ->  2503
horwasp_strong_explained            240 ->   240
post_horwasp_strong_residual       2273 ->  2263
mine_strong_explained                37 ->    37
post_mine_strong_residual          2236 ->  2226
label_issues                          0 ->     0
```

Expected generic rows after the strict pass: `779 -> 769`. Expected dominant short-forward count: `121 -> 119`. Do not assert a generic-hull count until rebaseline.

## Route-equivalent Tow v3 — verified closure

Global pre-build differential found four multiple visible Tow matches and zero single-match misses. Normal L1/L2 builds reproduced the exact `+4/-4` accounting change; post-fix controls are zero. Status: **TESTED + DIFF_VERIFIED**.

## Mine/web movement interruption — verified v5 mechanic

Independent diagnostics predicted `18` strict web + `19` strict normal-mine rows and production reproduced exactly `37` strong rows. Historical NuHost evidence selects positive nearest-integer mine damage rather than the documentation's literal round-up wording. Repair-bracket-only mine rows remain outside production.

## Chunnel v4 — verified closure

Route-equivalent Chunnel multiplicity is **TESTED + DIFF_VERIFIED**. The pre-fix differential predicted 34 false residuals and production reproduced the exact `+34/-34` accounting change.

## Test state

Last fully verified source/corpus state was L1 v3 + post-compile context v2 + L2 v5, with the Tow/compiled/cache targeted regression set and full pytest green.

New damage-limited source state adds:

```text
src/planets_lab/corpus/movement_damage_context.py
tests/test_movement_damage_context.py
```

and post-compile context marker v3. Targeted/full pytest and corpus rebuild are pending.

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
- Tow / Intercept / HYP movement phases;
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

Source schemas/semantic markers on current `main`:

```text
corpus manifest:
  planets-lab.corpus-game.v2
prepared cache:
  planets-lab.prepared-game-cache.v1
compiled movement:
  planets-lab.compiled-movement.v3
post-compile external-context semantics:
  planets-lab.compiled-movement-storm-context.v3
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
8. classic ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
9. scoped ordinary sphere movement for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
10. generic fuel-limited/prorated movement — corpus-observed as a small residual contributor, not promoted as a broad classifier;
11. mine/web interruption + nearest damage rounding — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for the strict v5 subset;
12. strict damage-limited warp — corpus differential complete, production/runtime verification pending.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check new damage context source, changed context stack and tests;
3. run targeted damage/storm/compiled/cache tests;
4. run full pytest;
5. run normal L1 build without `--rebuild` and verify 0/12 compiled hits + 12/12 prepared hits;
6. run normal L2 v5 build without `--rebuild` and verify 0/12 label hits + 12/12 prepared hits;
7. compare resulting accounting exactly with the independent `10`-row prediction;
8. rerun damage audit and generic clustering on the rebuilt endpoint;
9. if exact, promote damage-limited warp to `TESTED + DIFF_VERIFIED`;
10. continue triage on the remaining `119` short-forward rows rather than broadening damage repair inference.

Deprioritized/rejected/closed leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but sparse in the previously audited generic short-forward population;
- the historical fuel diagnostic still reads the pre-mine Horwasp endpoint and must be parameterized before reuse for current accounting;
- hidden/private-FC Chunnel event discovery added no coverage;
- route-equivalent Chunnel multiplicity is fixed/closed;
- route-equivalent visible Tow multiplicity is fixed/closed;
- ordinary owner-visible Intercept is already excluded from the Move Most corpus layer;
- target-origin visible non-Tow co-movement is evidence only, not a Tow classifier;
- repair-bracket mine rows are not part of strict v5;
- damage repair-bracket rows are not part of the strict damage-limited pass;
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

1. close strict damage-limited warp through tests + exact L1/L2 differential verification;
2. rebaseline the remaining generic residual and the 119-row short-forward family;
3. parameterize/revisit fuel or another generic mechanic from the new endpoint;
4. promote stabilized movement semantics into simulator/ruleset behavior;
5. expand differential mining into economy/mines/combat/race mechanics;
6. build the broader compatibility matrix;
7. only then make M6 AI training a primary workstream.
