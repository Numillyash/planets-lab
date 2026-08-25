# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-25-damage-limited-warp-verified-fuel-followup.md`](handoff/2026-08-25-damage-limited-warp-verified-fuel-followup.md).

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
external_context_explained         13970
post_external_residual              3924
chunnel_explained                   1421
post_chunnel_residual               2503
horwasp_strong_explained             240
post_horwasp_strong_residual        2263
mine_strong_explained                 37
post_mine_strong_residual           2226
label_issues                           0
```

Verified recent closures:

- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multi-event handling — `TESTED + DIFF_VERIFIED`;
- strict mine/web interruption context v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent visible Tow handling in L1 v3 — `TESTED + DIFF_VERIFIED`;
- strict damage-limited maximum warp — `DOCUMENTED (legacy Nu page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`.

The active focused investigation is now **fuel-proration / insufficient-fuel signatures on the current 2226 final endpoint**, especially within the surviving 119-row short-forward family.

## Current generic residual landscape

Broad clustering against `movement_post_mine_strong_residual` now measures:

```text
final_residual_rows       2226
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               769
generic_games               12
generic_hulls               76
```

Main coarse signatures:

```text
119  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 45  warp7-9 0.5-1.0x observed=other same_line_forward
```

The strict damage pass changed the dominant family only `121 -> 119` and generic rows `779 -> 769`.

## Damage-limited maximum warp — verified closure

Independent pre-build diagnostic found:

```text
raw_damage_limited                  11
raw_damage_limited_endpoint_exact   10
raw_exact_low_supply                10
raw_not_damage_limited_endpoint_exact_control  0
undamaged_endpoint_exact_control               0
```

The 10 exact rows spanned 9 games, 8 hulls, 6 races and effective maximum warps 1, 3, 4, 5, 6, 7 and 8. Only two belonged to the dominant 121-row short-forward family.

Production module:

```text
src/planets_lab/corpus/movement_damage_context.py
```

Category:

```text
damage_limited_warp_match
```

Strict production predicate:

```text
still unresolved after previous L1 contexts
non-Horwasp hull
resolved owner/race
same ship identity after transition
requested warp 1..9
visible supplies < 5 KT
raw-damage max warp < requested warp
exact Host-major/minor endpoint at effective warp
```

Repair-bracket-only rows remain evidence-only. Gravitonic distance and scoped effective sphere geometry are preserved.

Normal L1 build reproduced exactly:

```text
external_context_explained        13960 -> 13970
post_external_residual             3934 ->  3924
```

Normal L2 accounting then reproduced every independently predicted downstream count exactly:

```text
post_chunnel_residual             2513 -> 2503
post_horwasp_strong_residual      2273 -> 2263
mine_strong_explained               37 ->   37
post_mine_strong_residual         2236 -> 2226
label_issues                         0 ->    0

ACCOUNTING DIFFERENTIAL: EXACT MATCH
```

Post-build damage audit found zero remaining exact production-eligible damage matches. Status: **DOCUMENTED (legacy help page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

## Cache semantics after damage context v3

The ordered post-compile L1 context marker is:

```text
planets-lab.compiled-movement-storm-context.v3
```

L1 normal build:

```text
compiled_cache_hits                0
compiled_cache_misses             12
prepared_cache_hits_on_compile    12
prepared_cache_misses_on_compile   0
```

L2 normal build:

```text
compiled_label_cache_hits           3
compiled_label_cache_misses         9
prepared_cache_hits_on_compile      9
prepared_cache_misses_on_compile    0
```

This is correct. L2 validity is keyed by label schema, source movement schema, archive/settings identity and exact source movement Parquet SHA-256. Physical L1 schema remained v3. Three rebuilt games produced byte-identical source Parquet because the new damage pass changed no row there, so their existing labels were still valid. The other nine source hashes changed and missed.

Do not force L2 cache misses when the source bytes and source schema are unchanged.

## Current fuel-proration follow-up

Historical diagnostic:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

Its old result established that fuel-prorated movement exists but is sparse. However, it was previously hard-wired to the historical pre-mine `movement_post_horwasp_strong_residual`, so those old population counts are not current accounting.

The diagnostic is now parameterized. Default:

```text
--residual-view movement_post_mine_strong_residual
```

Historical reproduction remains available with:

```text
--residual-view movement_post_horwasp_strong_residual
```

It also reports the exact current coarse-family population independently:

```text
target_short_forward_rows = 119   # expected guard
```

Fuel-specific evidence inside that family includes:

```text
target_short_gravitonic_excluded
target_short_non_gravitonic
target_short_fuel_geometry_candidate
target_short_same_identity_after
target_short_formula_ready
target_short_insufficient_for_regular
target_short_formula_brackets_observed
target_short_affordable_frontier_match
target_short_depleted_after
target_short_strong_fuel_limit_signature
```

Strong fuel evidence still requires same-identity continuity, insufficient fuel for the regular move, affordability of the observed move, observed distance near the maximum affordable whole-light-year frontier, and fuel depletion to zero. Raw snapshot mass is a correlation input, not yet a reconstructed exact pre-movement mass.

## Route-equivalent Tow v3 — verified closure

Global pre-build differential found four multiple visible Tow matches and zero single-match misses. Normal L1/L2 builds reproduced the exact `+4/-4` accounting change; post-fix controls are zero. Status: **TESTED + DIFF_VERIFIED**.

## Mine/web movement interruption — verified v5

Independent diagnostics predicted `18` strict web + `19` strict normal-mine rows and production reproduced exactly `37`. Historical NuHost evidence selects positive nearest-integer mine damage rather than the documentation's literal round-up wording. Repair-bracket-only mine rows remain outside production.

## Chunnel v4 — verified closure

Route-equivalent Chunnel multiplicity is **TESTED + DIFF_VERIFIED**. The pre-fix differential predicted 34 false residuals and production reproduced the exact `+34/-34` accounting change.

## Test state

Current source/corpus state is aligned on:

```text
L1 physical schema:       planets-lab.compiled-movement.v3
L1 context semantics:     planets-lab.compiled-movement-storm-context.v3
L2 context labels:        planets-lab.compiled-movement-context-labels.v5
```

Damage migration verification:

```text
targeted regression set: 27 passed
full pytest suite:        green
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

Current schemas/markers:

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
10. mine/web interruption + nearest damage rounding — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for strict v5;
11. strict damage-limited warp — `DOCUMENTED (legacy page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
12. generic fuel-limited/prorated movement — known real but current endpoint coverage pending rerun.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/generic_fuel_limited_residual_audit.py`;
3. run it on the default current final view;
4. require `target_short_forward_rows = 119` as a population guard;
5. compare current strong fuel count with the historical `7` signatures;
6. inspect how many strong signatures lie inside the 119-row family and their hull/game spread;
7. inspect bracketed/false-negative cases before considering any production classifier;
8. do not broaden fuel logic solely to maximize residual coverage.

Deprioritized/rejected/closed leads:

- multi-waypoint queue did not explain the old hull-79 cluster;
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

1. rerun fuel-proration differential on the current 2226/769 endpoint;
2. quantify strong fuel evidence specifically inside the surviving 119-row short-forward family;
3. promote only a narrow causal subset if independent evidence supports it;
4. continue reducing movement residuals with generic mechanics rather than hull-specific rules;
5. promote stabilized movement semantics into simulator/ruleset behavior;
6. expand differential mining into economy/mines/combat/race mechanics;
7. build the broader compatibility matrix;
8. only then make M6 AI training a primary workstream.
