# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-25-fuel-proration-v6-runtime-verification.md`](handoff/2026-08-25-fuel-proration-v6-runtime-verification.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean real NuHost transitions.

Unknown mechanics fail closed. Raw facts/topology and evidence-scoped effective interpretations remain separate.

## Current focus

Active milestone: **M5 historical NuHost corpus + compatibility mining**.

Last runtime-verified 12-game movement accounting is still the generated L2 v5 endpoint:

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

Last verified generic endpoint:

```text
final_residual_rows       2226
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               769
generic_games               12
generic_hulls               76
```

Largest coarse signatures:

```text
119  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 45  warp7-9 0.5-1.0x observed=other same_line_forward
```

## Verified movement closures

- warp-well classifier ordering — `TESTED + DIFF_VERIFIED`;
- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multiplicity — `TESTED + DIFF_VERIFIED`;
- strict mine/web interruption v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent visible Tow in L1 v3 — `TESTED + DIFF_VERIFIED`;
- strict damage-limited maximum warp — `DOCUMENTED (legacy Nu page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- Red Mite tracking/fallback — research closed absent new contradictory evidence.

## Fuel proration — source v6 implemented, runtime pending

### Rule correction

The historical fuel audit's strongest heuristic used the maximum affordable whole-light-year frontier. That remains useful correlation evidence but is **not** the documented Planets.nu insufficient-fuel rule.

Documented Nu semantics:

```text
actual distance = waypoint distance * fuel available / fuel required
```

Existing deterministic primitives:

```text
src/planets_lab/rules/fuel.py
src/planets_lab/rules/proration.py
src/planets_lab/sim/normal_movement.py
```

### Exact current-endpoint differential

`tools/diagnostics/fuel_proration_host_differential_audit.py` measured on the verified `2226` endpoint:

```text
raw_mass_insufficient_for_waypoint= 19
nu_proration_endpoint_exact= 6
frontier_endpoint_exact= 3
vgap3_endpoint_exact= 0
```

Rule signatures:

```text
('-', '-', '-')           13
('nu', '-', '-')           3
('nu', 'frontier', '-')    3
```

The six exact Nu rows span four hulls and three games. Three are Nu-only discriminating matches; three are also compatible with the old frontier heuristic. Three of the six lie in the dominant 119-row short-forward family.

Historical next-turn `warp`, waypoint and neutronium are not used as immediate post-Host guards because Time Machine turns preserve saved end-turn orders; editable fields may already reflect later player input. Exact Host `x/y` plus immutable identity continuity is the causal historical observation.

### Global stage-overlap audit

`tools/diagnostics/fuel_proration_global_stage_audit.py` scanned the entire current L1 residual and found:

```text
l1_non_horwasp_warp1_9_rows= 1334
raw_mass_insufficient_for_waypoint= 22
nu_proration_endpoint_exact= 6
nu_only_endpoint_exact= 3
```

All six exact rows partitioned as:

```text
post_mine_strong_residual 6
```

All three Nu-only rows also partitioned as:

```text
post_mine_strong_residual 3
```

There were no exact Nu-proration overlaps with verified Chunnel, Horwasp strong or mine/web strong rows.

### Production architecture

The strict fuel pass is therefore implemented as the **final L2 stage after mine/web**, not in L1.

Module/category:

```text
src/planets_lab/corpus/movement_fuel_context.py
fuel_proration_waypoint_match
```

New L2 fields:

```text
fuel_proration_category
fuel_proration_explained
post_fuel_proration_residual
```

New final view:

```text
movement_post_fuel_proration_residual
```

The previous intermediate control remains:

```text
movement_post_mine_strong_residual
```

Strict first-pass predicate:

```text
survives Chunnel/Horwasp/mine
non-Horwasp
non-Gravitonic
warp 1..9
reachable waypoint within ordinary warp^2 distance
same owner/hull/ship identity after transition
resolved race/engine/raw mass/positive fuel/damage
damage does not reduce requested warp
raw mass predicts insufficient positive fuel
documented Nu waypoint-distance proration
exact Host major/minor x/y endpoint
```

Not included yet:

- partial waypoints;
- zero-fuel movement;
- Gravitonic fuel behavior;
- damage-limited requested warp;
- next-turn editable reset fields;
- frontier-only/VGAP3-style semantics.

### Schema state

Source on current `main`:

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
compiled movement:                 planets-lab.compiled-movement.v3
post-compile L1 context semantics: planets-lab.compiled-movement-storm-context.v3
compiled context labels:           planets-lab.compiled-movement-context-labels.v6
```

Generated local corpus is still v5 until runtime verification. L1 does not need rebuilding.

### Independent expected v6 differential

```text
external_residual_rows             3924   unchanged
chunnel_explained                  1421   unchanged
post_chunnel_residual              2503   unchanged
horwasp_strong_explained            240   unchanged
post_horwasp_strong_residual       2263   unchanged
mine_strong_explained                37   unchanged
post_mine_strong_residual          2226   unchanged
fuel_proration_explained              6
post_fuel_proration_residual       2220
label_issues                          0
```

Expected broad rebaseline:

```text
generic_rows             769 -> 763
dominant short-forward   119 -> 116
```

Do not guess the new generic hull count before runtime.

## Cache semantics

L1 remains untouched.

The L2 schema bump v5 -> v6 should force all old label metadata to miss on a normal build:

```text
compiled_label_cache_hits            0
compiled_label_cache_misses         12
prepared_cache_hits_on_compile      12
prepared_cache_misses_on_compile     0
```

No manual cache deletion and no L1 `--rebuild` are required.

## Test state

Last fully verified source/corpus state had the damage/storm/compiled targeted regression set (`27 passed`) and full pytest green.

New v6 source adds/changes:

```text
src/planets_lab/corpus/movement_fuel_context.py
src/planets_lab/corpus/compiled_movement_labels.py
src/planets_lab/corpus/compiled_movement_labels_corpus_cli.py
tests/test_movement_fuel_context.py
tests/test_compiled_movement_labels.py
tests/test_movement_chunnel_route_equivalent.py
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

Targeted/full pytest and the v6 label build are pending.

## M0 — deterministic skeleton

Status: **substantially complete**.

Canonical state, immutable turn-order contracts, deterministic `HostEngine.step()` and regression/scenario infrastructure exist.

## M1 — movement-capable sandbox

Status: **largely implemented for the current movement subset**.

Implemented/partial families include normal movement, movement mass/fuel, documented fuel proration, warp wells, Tow/Intercept/HYP, pre-movement repair and damage-limited speed, ion storms and minimal economy.

Movement mechanics continue to be promoted from M5 evidence rather than guessed.

## M2 — economy and planetary host

Status: **in progress / not current priority**.

## M3 — warfare

Status: **partial**.

Mines/webs, combat, missions and aftermath remain broader target families.

## M4 — race mechanics

Status: **partial**.

Race-specific behavior belongs in explicit ruleset modules/hooks.

## M5A — historical NuHost corpus

Status: **active**.

Current foundation:

- 12 recent unique finished games across configured account histories;
- privacy-safe manifest v2 tracked in Git;
- immutable `/game/loadall` archives local/gitignored;
- prepared cache;
- compiled movement Parquet + DuckDB catalog;
- separate L2 context-label layer.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check v6 fuel/context/CLI/clustering source and tests;
3. run targeted fuel + compiled-label + Chunnel regression tests;
4. run full pytest;
5. do not rebuild L1;
6. run a normal L2 v6 build without `--rebuild`;
7. require 0/12 label hits and 12/12 prepared hits;
8. require all pre-fuel intermediate counts unchanged;
9. require `fuel_proration_explained=6` and final `2220`;
10. require all fuel overlap guards zero;
11. rebaseline generic clustering on `movement_post_fuel_proration_residual`;
12. require `generic_rows=763`, dominant short-forward `116`, and measure generic hull count;
13. only then mark fuel proration `TESTED + DIFF_VERIFIED` and choose the next residual family.

## Deprioritized / guardrails

- affordable-frontier fuel matching is correlation-only, not the Nu production rule;
- partial/zero-fuel/Gravitonic fuel cases require separate evidence;
- multi-waypoint queue did not explain the old hull-79 cluster;
- hidden/private-FC Chunnel discovery added no coverage;
- ordinary owner-visible Intercept is already excluded from Move Most residuals;
- target-origin visible non-Tow co-movement is evidence only;
- mine and damage repair-bracket-only cases remain outside strict production subsets;
- never generalize game `591478`'s 2170 period;
- do not reopen Red Mite/Tow/Chunnel/mine closures absent fresh evidence;
- hull count alone is not a mechanic identifier.

## M5B — compatibility matrix

Status: **active through movement differential validation**.

Mechanics should end in explicit `MATCH`, `MISMATCH`, `SKIPPED_AMBIGUOUS` or `UNSUPPORTED` states with ruleset/settings splits and permanent regressions.

## M6 — training and AI

Status: **future**.

Scripted baselines, player-limited observations, historical pretraining/evaluation and self-play follow broader simulator compatibility.
