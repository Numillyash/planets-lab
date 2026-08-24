# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-25-damage-limited-warp-followup.md`](handoff/2026-08-25-damage-limited-warp-followup.md).

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

The active focused investigation is now **damage-limited maximum warp in the current generic movement residual**.

## Route-equivalent Tow v3 — verified closure

A focused target-origin audit exposed four false residuals with exactly two owner-visible matching Tow towers and zero single-match misses. The global pre-build differential over all old external residual rows then found exactly:

```text
any_visible_matching_tower                    4
single_visible_matching_tower                 0
route_equivalent_multiple_visible_towers      4
```

All four were in the old final residual. Normal L1 v3 and L2 v5 builds reproduced the exact predicted accounting delta, with `0/12` compiled-cache reuse and `12/12` prepared-cache reuse at both layers. Post-fix global and target-origin Tow controls are zero.

Status: **TESTED + DIFF_VERIFIED**. Do not reopen without fresh contradictory evidence.

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

Compared with the historical post-v5/pre-Tow-v3 baseline:

```text
final residual  2240 -> 2236  (-4)
generic rows      783 ->  779  (-4)
generic hulls      79 ->   78  (-1)
```

The four Tow rows came entirely from the Warp-0 target-at-origin family. The main coarse signatures are now:

```text
121  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 48  warp7-9 0.5-1.0x observed=other same_line_forward
 46  warp7-9 >3.0x     observed=other oblique
```

The dominant short-forward family is unchanged by Tow and spans `26` hulls across `7` games, making it the highest-yield current generic target.

## Damage-limited maximum warp — runtime audit pending

Official Planets.nu documentation states that sufficiently damaged starships have reduced maximum warp. Standard races lose maximum speed through successive 10% damage bands after the first; Lizards use their separate extended-damage table. Host Order places `Mass check, repair, & MKT` before Tow/Most Ships Move, so supply/starbase repair can alter the effective damage before movement.

New focused diagnostic:

```text
tools/diagnostics/damage_limited_warp_residual_audit.py
```

It scans the current `movement_post_mine_strong_residual` generic non-Horwasp Warp 1-9 population and reports the 121-row short-forward family separately.

The audit combines:

- requested warp;
- owner race and explicit Lizard handling;
- raw before-turn damage;
- documented damage-limited maximum warp;
- Gravitonic distance doubling;
- evidence-scoped effective sphere topology;
- Host-major/minor destination projection;
- same-identity continuity;
- a conservative repair bracket from currently onboard supplies (`5 KT = 1%`);
- negative controls for undamaged and non-damage-limited ships.

Strong pre-production evidence requires:

```text
requested_warp > damage_limited_max_warp
AND exact Host-major/minor destination match
```

The low-supply subset (`supplies < 5`) is especially useful because currently onboard supplies cannot visibly repair even 1% before movement.

The current-supplies repair bracket remains evidence-only. Transfers, starbase repair and other Host-order effects can alter the state before movement and are not yet fully reconstructed.

Critical negative controls:

```text
raw_not_damage_limited_endpoint_exact_control
undamaged_endpoint_exact_control
```

They must be zero or fully explained before any production classifier is considered.

## Mine/web movement interruption — verified v5 mechanic

Mine/web work is closed for the strict subset. Independent diagnostics predicted `18` strict web + `19` strict normal-mine rows and production reproduced exactly `37` strong rows.

Historical NuHost evidence selects positive nearest-integer mine damage rather than the documentation's literal round-up wording. Keep that compatibility distinction explicit. Repair-bracket-only mine rows remain outside production until repair reconstruction is independently validated.

## Chunnel v4 — verified closure

Route-equivalent Chunnel multiplicity is **TESTED + DIFF_VERIFIED**. The pre-fix differential predicted 34 false residuals and production reproduced the exact `+34/-34` accounting change. Do not reopen without fresh evidence.

## Test state

The repository source state and current compiled corpus are aligned on:

```text
L1: planets-lab.compiled-movement.v3
L2: planets-lab.compiled-movement-context-labels.v5
```

The Tow/compiled/cache targeted regression set and the full pytest suite were green at the verified v3 closure. The newly added damage-limited diagnostic is evidence-only and does not change production schemas or accounting.

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
8. classic ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
9. scoped ordinary sphere movement for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
10. generic fuel-limited/prorated movement — corpus-observed as a small residual contributor, not promoted as a broad classifier;
11. mine/web interruption + nearest damage rounding — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for the strict v5 subset.

### Immediate work

1. pull current `main` and confirm a clean tree;
2. syntax-check `tools/diagnostics/damage_limited_warp_residual_audit.py`;
3. run it on the current `movement_post_mine_strong_residual` corpus;
4. confirm `target_short_forward_rows = 121` as a population guard;
5. inspect raw exact damage-limit matches across hulls/games/races and effective-warp buckets;
6. inspect `raw_exact_low_supply` and the current-supplies repair bracket separately;
7. require the undamaged/not-limited negative controls to be zero or fully explained;
8. only if the differential is material and causal, implement a narrow regression-backed production context layer;
9. otherwise leave damage-limit unpromoted and parameterize/revisit fuel or another generic family.

Deprioritized/rejected/closed leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
- fuel proration is real but sparse in the previously audited generic short-forward population;
- the historical fuel diagnostic still reads the pre-mine Horwasp endpoint and must be parameterized before reuse for current accounting;
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

1. run the damage-limited-warp differential on the current 2236/779 endpoint;
2. promote only a narrow causal subset if exact cross-game evidence supports it;
3. continue reducing movement residuals with generic mechanics rather than hull-specific rules;
4. promote the stabilized movement subset into simulator/ruleset behavior;
5. expand differential mining into economy/mines/combat/race mechanics;
6. build the broader compatibility matrix;
7. only then make M6 AI training a primary workstream.
