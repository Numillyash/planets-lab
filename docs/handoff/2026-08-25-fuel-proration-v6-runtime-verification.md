# Fuel-proration L2 v6 — runtime verification pending

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **documented Planets.nu waypoint-distance fuel proration is strongly corpus-observed and discriminates against both the historical affordable-frontier heuristic and a VGAP3-style control. A strict six-row-compatible L2 v6 context stage is implemented on `main`; targeted/full tests and the normal L2 cache-invalidating build are still required before promotion to TESTED + DIFF_VERIFIED.**

This handoff supersedes `2026-08-25-fuel-proration-global-stage-pending.md` for active work. Damage-limited warp, route-equivalent Tow, Chunnel multiplicity, strict mine/web context, classic/cloudy ion storms, scoped sphere topology and Red Mite remain closed absent fresh contradictory evidence.

## Last runtime-verified generated corpus

Generated local data is still L1 v3/context-v3 + L2 v5:

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

Dominant generic family:

```text
119  warp7-9 <0.5x observed=other same_line_forward
```

## Historical fuel-correlation audit

The current-endpoint rerun of:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

still found the historical affordable-frontier signal:

```text
strong_fuel_limit_signature= 7
```

with three such rows inside the dominant 119-row family.

Those seven rows are retained as correlation evidence only. The old criterion asks whether observed travel is near the maximum whole-light-year distance affordable under the fuel formula. That is not the documented Planets.nu insufficient-fuel movement rule.

## Documented Nu rule and competing-rule differential

Planets.nu documents ordinary insufficient-fuel movement as:

```text
actual distance = waypoint distance * fuel available / fuel required
```

The existing repository primitives already implement the documented mechanics:

```text
src/planets_lab/rules/fuel.py
src/planets_lab/rules/proration.py
src/planets_lab/sim/normal_movement.py
```

The exact differential:

```text
tools/diagnostics/fuel_proration_host_differential_audit.py
```

was run against `movement_post_mine_strong_residual` and measured:

```text
generic_non_horwasp_warp1_9_rows= 671
raw_mass_insufficient_for_waypoint= 19

nu_proration_endpoint_exact= 6
frontier_endpoint_exact= 3
vgap3_endpoint_exact= 0
```

Combined rule signatures:

```text
('-', '-', '-')           13
('nu', '-', '-')           3
('nu', 'frontier', '-')    3
```

Thus all six exact candidates match documented Nu waypoint proration, three are discriminating Nu-only matches, and none match the VGAP3-style rule.

Coverage:

```text
hulls: 96 (2), 17 (2), 31 (1), 78 (1)
games: 620694 (4), 360690 (1), 620636 (1)
```

Three of the six exact rows belong to the dominant 119-row short-forward family.

## Why next-turn Warp/waypoint/fuel is not a production guard

The exact differential reported zero rows satisfying an immediate-looking next-turn reset predicate.

This is not treated as a mechanical contradiction. Historical Time Machine/loadall turns reproduce saved end-of-turn state and orders. Editable fields in the next saved turn may therefore already reflect later player orders or transfers rather than the immediate state at the end of the movement phase.

For historical compatibility mining:

- `x/y` is the immutable Host movement outcome used for exact matching;
- same owner/hull/ship identity is used as a continuity guard;
- next-turn editable `warp`, waypoint and neutronium are observational context only and are not required by the production predicate.

The documented out-of-fuel reset remains a simulator/rule property; this historical corpus layer simply does not claim to observe its transient immediate phase boundary reliably.

## Global downstream-stage overlap audit

Diagnostic:

```text
tools/diagnostics/fuel_proration_global_stage_audit.py
```

Runtime population over the full current L1 residual:

```text
l1_non_horwasp_warp1_9_rows= 1334
reachable_waypoint= 1073
same_identity_after= 861
identity_break_after= 212
raw_damage_limited_excluded= 0
formula_ready= 861
zero_required_fuel= 407
zero_fuel_separate_mechanic= 9
raw_mass_sufficient_for_waypoint= 423
raw_mass_insufficient_for_waypoint= 22
nu_proration_endpoint_exact= 6
nu_only_endpoint_exact= 3
```

Critical stage partition:

```text
NU EXACT BY DOWNSTREAM STAGE:
post_mine_strong_residual 6

NU-ONLY EXACT BY DOWNSTREAM STAGE:
post_mine_strong_residual 3
```

There are no exact Nu-proration overlaps with verified Chunnel, Horwasp strong or mine/web strong rows. This is the decisive architecture result.

## Production architecture choice

Fuel proration is added as the **last L2 context stage after strict mine/web**, not as an early L1 pass.

Reasons:

1. all six independently identified exact rows already lie exclusively in the post-mine final stage;
2. the post-mine placement cannot steal any verified Chunnel/Horwasp/mine classifications;
3. L2 already has access to the historical archive/prepared state required for engine specs and raw movement mass evidence;
4. L1 physical and post-compile semantic state stays unchanged;
5. the old `movement_post_mine_strong_residual` view remains an explicit intermediate control.

New module:

```text
src/planets_lab/corpus/movement_fuel_context.py
```

New category:

```text
fuel_proration_waypoint_match
```

New final view:

```text
movement_post_fuel_proration_residual
```

The previous intermediate view remains:

```text
movement_post_mine_strong_residual
```

## Strict production predicate

The first production subset is deliberately narrow:

```text
row survives Chunnel + Horwasp strong + mine/web strong
AND non-Horwasp hull
AND non-Gravitonic
AND requested warp in 1..9
AND waypoint is reachable within ordinary warp^2 distance this turn
AND same owner/hull/ship identity after the transition
AND owner race / engine / raw mass / positive fuel / damage are available
AND current damage does not reduce maximum warp below requested warp
AND raw mass predicts fuel_required > fuel_available > 0
AND documented Nu waypoint-distance proration
AND exact Host major/minor endpoint equals observed x/y
```

Explicitly excluded from this first pass:

- partial waypoints beyond ordinary per-turn range;
- zero-fuel movement;
- Gravitonic movement;
- Horwasp hulls;
- raw-damage-limited requested warp;
- affordable-frontier-only matches;
- VGAP3-style semantics;
- any requirement on next saved turn's editable Warp/waypoint/fuel state.

Only the derived fuel category/flags are exported. Raw fuel amount, raw mass and computed fuel requirement stay local/private.

## Source schema state

Current source on `main`:

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v6
```

New L2 columns:

```text
fuel_proration_category
fuel_proration_explained
post_fuel_proration_residual
```

L1 source and generated L1 data are unchanged. Only L2 needs a normal build.

## Regression coverage

New:

```text
tests/test_movement_fuel_context.py
```

Covers:

- documented 60-ly / 12-KT-required / 11-KT-available -> 55-ly proration;
- exact Host endpoint requirement;
- sufficient-fuel rejection;
- partial-waypoint rejection;
- damage-limited requested-warp rejection;
- Gravitonic and Horwasp rejection;
- stable production category.

Updated:

```text
tests/test_compiled_movement_labels.py
tests/test_movement_chunnel_route_equivalent.py
```

The compiled-label regression now verifies fuel-layer accounting, privacy-safe schema and the new post-fuel view. The Chunnel test only advances the shared L2 schema sentinel to v6; standalone Chunnel semantics remain unchanged.

## Independent pre-build prediction

Because the global differential found exactly six strict-compatible rows and all six are post-mine residuals, the independent expected v6 accounting is:

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

Expected generic accounting:

```text
generic_rows                  769 -> 763
dominant short-forward        119 -> 116
```

Do not pre-assert a new generic hull count; measure it after the v6 build.

## Cache expectation

Do **not** rebuild L1.

The L2 label schema changes v5 -> v6, so a normal label build without `--rebuild` should produce:

```text
compiled_label_cache_hits            0
compiled_label_cache_misses         12
prepared_cache_hits_on_compile      12
prepared_cache_misses_on_compile     0
```

Unlike the earlier damage-context migration, this invalidation is directly caused by the label schema change; all v5 metadata must fail the v6 label-schema check even when the source L1 Parquet is byte-identical.

## Required runtime verification

1. pull current `main` and confirm clean status;
2. syntax-check the new fuel context, compiled-label code/CLI, changed clustering diagnostic and tests;
3. run targeted fuel/compiled-label/Chunnel regression tests;
4. run the full pytest suite;
5. do **not** rebuild L1;
6. run a normal L2 build without `--rebuild`;
7. require 0/12 v6 label cache hits and 12/12 prepared-cache hits;
8. require all pre-fuel intermediate accounting to remain exactly unchanged;
9. require `fuel_proration_explained=6` and `post_fuel_proration_residual=2220`;
10. require fuel/Chunnel, fuel/Horwasp and fuel/mine overlaps to remain zero;
11. run broad generic clustering on the default post-fuel view;
12. require `generic_rows=763` and dominant short-forward `116`; measure, do not guess, the generic hull count.

## Guardrails

- Do not promote the historical affordable-frontier heuristic as the Nu rule.
- Do not require next-turn editable Warp/waypoint/fuel reset fields from Time Machine snapshots.
- Do not broaden v6 into partial-waypoint, zero-fuel or Gravitonic fuel behavior without separate differentials.
- Do not move fuel ahead of verified Chunnel/Horwasp/mine layers without new contradictory evidence.
- Damage-limited warp remains closed.
- Do not reopen Tow/Chunnel/mine/Red Mite without new evidence.
- Keep game `591478`'s 2170 effective sphere period scoped to that game.
- Preserve private raw state locally and export only derived mechanical evidence.
