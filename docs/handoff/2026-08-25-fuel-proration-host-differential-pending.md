# Fuel-proration Host differential — pending runtime

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **damage-limited warp is closed. The current final endpoint remains 2226 rows / 769 generic rows. A current-endpoint fuel audit confirmed that fuel-limited movement is still present, but also exposed that the historical `affordable_frontier_match` criterion is not the documented Planets.nu proration rule. A new rule-discriminating Host differential is implemented and runtime pending.**

This handoff supersedes `2026-08-25-damage-limited-warp-verified-fuel-followup.md` for active work.

## Current verified movement accounting

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

Current generic endpoint:

```text
final_residual_rows       2226
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               769
generic_games               12
generic_hulls               76
```

Dominant coarse family:

```text
119  warp7-9 <0.5x observed=other same_line_forward
```

## Current-endpoint historical fuel audit rerun

Diagnostic:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

Runtime population:

```text
residual_view= movement_post_mine_strong_residual
generic_non_horwasp_warp1_9_rows= 671

target_short_forward_rows= 119
target_short_gravitonic_excluded= 15
target_short_non_gravitonic= 104
target_short_fuel_geometry_candidate= 97
target_short_same_identity_after= 96
target_short_identity_break_after= 1
target_short_formula_ready= 97
```

Fuel evidence inside the 119-row family:

```text
target_short_insufficient_for_regular= 6
target_short_observed_affordable= 96
target_short_formula_brackets_observed= 5
target_short_affordable_frontier_match= 3
target_short_depleted_after= 22
target_short_strong_fuel_limit_signature= 3
```

Those three historical-criterion strong rows span:

```text
hulls: 17 (2), 61 (1)
games: 511506, 620636, 620694
```

Across the wider non-Gravitonic short-same-line population, the old criterion still finds exactly seven strong signatures:

```text
strong_fuel_limit_signature= 7
```

across six hulls and four games. Therefore later mine/Tow/damage closures did not make the old fuel signal disappear.

## Critical rule correction

The old audit's strongest predicate includes:

```text
observed distance near maximum affordable whole-light-year frontier
```

That is **not** the documented Planets.nu insufficient-fuel movement rule.

Planets.nu `Fuel Consumption Details` documents:

```text
actual distance = waypoint distance * fuel available / fuel required
```

and explicitly gives the example that a 60-ly trip requiring 12 KT travels 55 ly with 11 KT, even though 11 KT could otherwise afford 59 ly.

The Planets.nu/VGAP3 differences page also states the distinction:

- VGAP3 uses `warp^2 * fuel / fuel_required` as the maximum distance;
- Planets.nu uses the waypoint-distance ratio instead.

Therefore the old `affordable_frontier_match` result is retained as historical correlation/evidence only. It must not be promoted as the Nu production rule.

## Existing simulator/rules implementation

The repository already contains the documented primitives:

```text
src/planets_lab/rules/fuel.py
src/planets_lab/rules/proration.py
src/planets_lab/sim/normal_movement.py
```

`movement_fuel_use()` implements the documented nested-TRUNC fuel formula.

`prorate_waypoint_distance()` implements:

```text
waypoint_distance * fuel_available / fuel_required
```

`project_toward_waypoint()` implements the previously differential-tested Host major/minor integer endpoint projection.

No simulator rule needs to be guessed for the next audit.

## New exact differential

New diagnostic:

```text
tools/diagnostics/fuel_proration_host_differential_audit.py
```

It reads the current final view and restricts the strongest comparison to:

```text
non-Horwasp
non-Gravitonic
warp 1..9
reachable waypoint within the normal per-turn distance
same-identity owner state after movement
raw mass / engine / fuel formula ready
positive fuel
raw mass predicts insufficient fuel for waypoint
```

Partial waypoints, Gravitonic movement and zero-fuel movement are deliberately excluded from this first causal differential.

For every raw-mass-insufficient candidate, the audit compares exact Host-major/minor endpoints for three competing models:

1. documented Nu waypoint proration:

```text
waypoint_distance * fuel_available / fuel_required
```

2. historical affordable-whole-LY frontier heuristic;

3. VGAP3-style maximum-distance ratio:

```text
warp^2 * fuel_available / fuel_required
```

The strongest Nu evidence additionally requires the documented normal out-of-fuel post-state:

```text
fuel_after = 0
warp_after = 0
waypoint_after = observed current position
```

Key outputs:

```text
nu_proration_endpoint_exact
frontier_endpoint_exact
vgap3_endpoint_exact
nu_proration_strong

target_short_nu_proration_endpoint_exact
target_short_frontier_endpoint_exact
target_short_vgap3_endpoint_exact
target_short_nu_proration_strong
```

and a combined `RULE SIGNATURES` section showing overlaps between the three models.

## Promotion threshold

Do not promote fuel proration from the historical seven-row criterion alone.

A production candidate requires:

- exact documented-Nu endpoint matches;
- out-of-fuel reset on the strongest subset;
- cross-game / cross-hull support;
- clear discrimination against the affordable-frontier and VGAP3 controls;
- no dependence on partial-waypoint semantics or Gravitonic behavior in the first pass;
- no assumption that raw snapshot mass is always exact pre-movement mass.

If documented Nu proration does not clearly beat the controls, keep fuel evidence-only and move to another residual family.

## Immediate work

1. pull current `main` and confirm clean status;
2. syntax-check `fuel_proration_host_differential_audit.py`;
3. run it on the current local compiled corpus;
4. require `target_short_forward_rows = 119` as the broad-family population guard;
5. inspect Nu vs frontier vs VGAP3 endpoint exact counts and rule signatures;
6. inspect `nu_proration_strong` hull/game spread;
7. inspect how many strong Nu rows belong to the 119 family;
8. do not change production accounting until this rule differential is understood.

## Guardrails

- Damage-limited warp remains closed.
- The old seven `strong_fuel_limit_signature` rows are historical correlation, not production truth.
- Do not promote affordable-frontier semantics as Planets.nu fuel proration.
- Keep partial waypoints, zero-fuel movement and Gravitonic fuel behavior outside the first exact differential.
- Do not reopen Tow/Chunnel/mine/Red Mite without fresh evidence.
- Do not generalize game `591478`'s 2170 period.
- Preserve private raw state locally; output only derived mechanical evidence.
