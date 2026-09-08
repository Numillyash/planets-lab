# Intel / finite-fuel movement handoff — 2026-09-08

GitHub `main` is the only source of truth for `Numillyash/planets-lab`.

## Current source checkpoint

The latest implementation/test checkpoint relevant to this handoff is:

```text
d002858e3eb2fe06a0f2c1876f14cfdaa3cd3ea1
tests: lock partial fuel nominal basis anchors
```

Its parent implementation commit is:

```text
993e76046c3ffaa40acf4b0aa7286d5bd9573480
sim: use nominal leg for partial fuel cost
```

GitHub Actions `tests` run `34237920543` completed successfully for `d002858e`.
A documentation commit recording this checkpoint is newer than the code commit. Always inspect actual `main` before work.

## Finite-fuel Intercept evidence

Historical differential over finite-fuel archives found only three strict snapshot-fuel-limited Intercept cases.

### 620636 / T60 / ship44 — strong support

```text
Hull: Gemini Class Transport
Warp: 8
Snapshot fuel: 1 KT
Candidate full cost: 3 KT
Observed endpoint: (1716, 1599)
Geometry-only endpoint: (1705, 1589)
Fuel-proration endpoint: (1716, 1599)
After fuel: 0
```

The phase-fuel scan found that exactly 1 KT reproduces the observed endpoint. Targeted confounder audit found no strict mine, storm, damage-limited-warp, observed Tow-route or Chunnel-target explanation.

Interpretation: strong evidence that finite-fuel Intercept can use proportional fuel-limited movement.

### 360690 / T69 / ship391 — snapshot fuel is not phase fuel

```text
Hull: Biocide Class Carrier
Warp: 9
Snapshot fuel: 64 KT
Candidate full cost: 66 KT
Observed endpoint = geometry endpoint
Snapshot-fuel prorated endpoint differs
Minimum phase fuel compatible with factual endpoint: 66 KT
After fuel: 171 KT
```

No visible incoming transfer/Tow candidate was found in the owner-visible snapshot, but absence is not proof of no hidden/earlier Host mutation.

Interpretation: do not treat pre-Host `loadturn.neutronium` as guaranteed Intercept-phase fuel.

### 620694 / T73 / ship278 — true partial route / cost-basis discriminator

```text
Hull: Nova Class Super-dreadnought
Warp: 9
Origin: (2758, 2098)
Intercept target final observed: (2717, 2026)
Target distance: ~82.855 ly
Nominal max: 81 ly
Observed endpoint: (2742, 2070)
Snapshot fuel: 29 KT
After fuel: 0
```

No known strict mine/storm/damage/Tow/Chunnel explanation was found.

Dedicated model comparison:

```text
integer projected one-turn distance ~80.623 -> required cost 71
continuous nominal 81-ly leg            -> required cost 72
full target waypoint cost               -> required cost 72

29/71 rasterizes to (2741,2069)  [not factual]
29/72 rasterizes to (2742,2070)  [factual]
```

This supports a continuous nominal one-turn cost basis before integer endpoint rasterization.

## Diagnostic corrections

Do not equate `NormalMovePlan.partial` with `waypoint_distance > effective max distance`.

`partial` can also be true for a geometrically reachable waypoint shortened due to fuel shortage. A true partial route must be classified geometrically from target distance versus effective max movement.

A second diagnostic bug was found and fixed in `partial_move_fuel_cost_move_most_audit.py`: a model cost of exactly zero must mean that fuel does not limit the candidate endpoint. The old helper returned `None` for `fuel_required <= 0`, which created a false projected-vs-nominal discriminator at `511506/T95/ship445`.

```text
89b5b0f1c06869a0d03d04cba76caa78bc4b10ce
fix: handle zero-cost Move Most candidates
```

## Move Most population audit — corrected runtime result

Use:

```text
tools/diagnostics/partial_move_fuel_cost_move_most_audit.py
```

Corrected runtime population result over the available finite-fuel, non-Sphere archives:

```text
prefilter_true_partial_rows=32371
true_partial_route=15560
prefilter_false_positive=1495
same_integer_cost=12633
cost_basis_differs=2927
fuel_relation:below_both=3
fuel_relation:between_costs=0
fuel_relation:sufficient_both=2924
projected_cost_endpoint_exact=2811
nominal_cost_endpoint_exact=2812
discriminating_endpoint=1
discriminating_nominal_cost_support=1
discriminating_projected_cost_support=0
discriminating_with_post_reset=0
```

The single surviving independent Move Most discriminator is `360690/T164/ship41`.

Two other `below_both` rows are not discriminators:

- `511506/T32/ship45`: snapshot fuel 0, observed endpoint is not reproduced by either candidate; post-reset is true.
- `511506/T70/ship406`: snapshot fuel 68, after fuel 163, observed endpoint is not reproduced by either candidate; snapshot fuel is not sufficient movement-phase evidence there.

Do **not** run the old broad `partial_move_fuel_cost_population_audit.py` again.

## 360690 / T164 / ship41 — targeted forensic runtime result

Dedicated diagnostic:

```text
tools/diagnostics/partial_move_fuel_cost_case_audit.py
```

Code commit:

```text
887c67061b8280ccaac1520b475b1904a039f811
diagnostics: add targeted Move Most fuel case audit
```

Runtime completed successfully (`audit rc=0`, `tee rc=0`).

Factual case:

```text
game=360690
turn=164 -> 165
ship=41
hull=23
owner=2
owner_race=2
warp=9
origin=(1949,2950)
target=(2008,3067)
observed=(1959,2969)
waypoint_distance=131.034347
max_distance=81
true_partial_route=True
snapshot_fuel=11
after_fuel=0
snapshot movement mass=517
projected-distance cost=40
continuous-nominal cost=41
```

At snapshot fuel 11:

```text
projected endpoint = (1959,2970) [not factual]
nominal endpoint   = (1959,2969) [factual]
```

The phase-fuel scan recomputed movement mass for every hypothetical fuel value from 0 through 5000 KT:

```text
projected_exact_phase_fuel_ranges=()
nominal_exact_phase_fuel_ranges=((11,11),)
both_exact_phase_fuel_ranges=()
projected_only_phase_fuel_ranges=()
nominal_only_phase_fuel_ranges=((11,11),)
projected_exact_post_fuel_ranges=()
nominal_exact_post_fuel_ranges=((0,0),)
```

Changing only movement-phase neutronium cannot rescue the projected/rasterized-distance cost model anywhere in the scanned physical range. Continuous-nominal cost reproduces the factual endpoint uniquely at exactly the factual snapshot fuel and predicts post-move fuel 0, matching the next factual state.

Owner-visible pre-Host context:

```text
ship_order_fields={}
visible_incoming_transfer_candidates=[]
visible_incoming_tow_tower_ids=()
colocated_planets=[]
```

Three other same-owner hull-23 ships were co-located at the origin, but none had visible transfer/load-like order fields targeting ship41. Co-location alone is not a transfer fact.

Known external movement confounders:

```text
baseline_category='partial_other'
before_damage=0
after_damage=0
damage_warp_limit=9
damage_effective_warp=9
mine_evidence=None
storm_status='not_affected'
storm_category=None
observed_tow_route_towers=()
observed_chunnel_target_events=()
known_external_flags=()
```

### Evidence interpretation

`360690/T164/ship41` is a **strong independent Move Most empirical anchor** for continuous-nominal true-partial fuel-cost basis.

It is stronger than a snapshot-only discriminator because:

1. projected cost fails for every scanned phase-fuel value while recomputing mass;
2. nominal cost succeeds only at 11 KT;
3. 11 KT is also the factual pre-Host snapshot fuel;
4. nominal prediction leaves 0 KT and the next factual fuel is 0;
5. no owner-visible transfer/load fuel order explains a state mutation;
6. no currently modelled mine/storm/damage/Tow/Chunnel mechanic explains the endpoint.

The remaining caveat is general Host incompleteness: an unknown mechanic could still alter movement mass/geometry/state. `known_external_flags=()` excludes only the already-modelled factual confounders.

Combined with independent Intercept `620694/T73/ship278`, evidence consistently points to the same rule across different games/hulls/mission contexts: when a route is geometrically longer than the effective one-turn maximum, fuel requirement uses the **continuous nominal one-turn leg before integer endpoint rasterization**, then insufficient fuel prorates that one-turn leg.

No observed discriminator supports projected/rasterized endpoint distance as the fuel-cost basis.

## Lab implementation candidate

Caller audit confirmed that ordinary Move Most, Intercept and Tow share `plan_full_normal_move()`:

- `NormalMovementPhase` passes the ship movement mass;
- `InterceptMovementPhase` uses the same planner toward the target's phase-current position;
- `TowMovementPhase` uses the same planner with `movement_mass_override=combined_mass`.

The candidate implementation is therefore centralized rather than mission-specific.

Commit:

```text
993e76046c3ffaa40acf4b0aa7286d5bd9573480
sim: use nominal leg for partial fuel cost
```

Behavior change in `src/planets_lab/sim/normal_movement.py`:

- geometrically reachable route: unchanged; fuel basis is the continuous waypoint distance;
- geometrically partial route: integer endpoint is still projected with the verified Host major/minor-axis geometry at the effective one-turn range;
- its `fuel_required` is now computed from the **continuous effective one-turn range**, not `hypot(rasterized_endpoint-origin)`;
- if fuel is insufficient and expanded/proration mode is enabled, the movement is no longer rejected as `insufficient_fuel_partial_waypoint`;
- instead, the continuous one-turn leg is prorated by `fuel_available / fuel_required`, then projected to integer coordinates using the same Host geometry;
- `NormalMovePlan.distance` remains the actual rasterized endpoint distance, while `fuel_required` may intentionally be based on a slightly larger continuous nominal leg.

This change automatically applies the candidate law to Move Most, Intercept and Tow while preserving Tow's combined movement mass.

## Regression anchors and CI

Commit:

```text
d002858e3eb2fe06a0f2c1876f14cfdaa3cd3ea1
tests: lock partial fuel nominal basis anchors
```

New `tests/test_partial_fuel_nominal_basis.py` contains two explicit diagonal/rasterization discriminators:

1. `360690/T164/ship41`-geometry equivalent:
   - movement mass 517;
   - rasterized-distance cost 40;
   - continuous 81-ly cost 41;
   - 11 KT must produce `(1959,2969)` and then reset to 0 fuel / warp 0.
2. `620694/T73/ship278` Intercept-geometry equivalent:
   - movement mass 900 synthetic equivalent;
   - rasterized-distance cost 71;
   - continuous 81-ly cost 72;
   - 29 KT must produce `(2742,2070)`.

GitHub Actions:

```text
workflow: tests
run id: 34237920543
head: d002858e3eb2fe06a0f2c1876f14cfdaa3cd3ea1
status: completed
conclusion: success
```

This proves the candidate is internally regression-clean against the repository test suite, but does **not** replace historical corpus/runtime differential validation.

## Immediate next step — server historical validation

Pull actual `main` on `/opt/planets-lab`, run the complete pytest suite there, then re-run:

1. `partial_move_fuel_cost_case_audit.py` for the strong Move Most anchor;
2. `partial_move_fuel_cost_move_most_audit.py` for population consistency;
3. the finite-fuel Intercept diagnostics most directly affected by `plan_full_normal_move()` — at minimum the historical differential / targeted external-confounder path.

Compare against the recorded baselines rather than accepting a green unit suite alone.

Only after those historical diagnostics remain coherent should `docs/rules/fuel-proration.md` / movement rule status be updated to the new differential-verified semantics.

## Promotion policy

Do not modify `planets-intel` production finite-fuel inference yet.

For `planets-lab`, the rule has enough cross-context empirical support for this implementation candidate and full regression/differential validation. Promotion beyond the lab still requires confirming no regression of established Move Most/Tow/Intercept historical behavior.

Core evidence discipline remains:

- known zero != unknown;
- fact != inference != simulation;
- missing data != zero;
- pre-Host snapshot fuel is not automatically movement-phase fuel;
- unsupported Host behavior fails closed.

## Cross-repo context

Companion production/client handoff:

```text
Numillyash/planets-intel
docs/handoff/2026-09-08-chat-handoff.md
```

The production client currently has only unlimited-fuel current games, so historical archives in `planets-lab` remain the evidence source for finite-fuel reconstruction.
