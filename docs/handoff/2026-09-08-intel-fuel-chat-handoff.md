# Intel / finite-fuel movement handoff — 2026-09-08

GitHub `main` is the only source of truth for `Numillyash/planets-lab`.

## Current source checkpoint

The latest code checkpoint relevant to this handoff is:

```text
887c67061b8280ccaac1520b475b1904a039f811
diagnostics: add targeted Move Most fuel case audit
```

A documentation commit recording the runtime result is newer than that code checkpoint. Always inspect actual `main` before work.

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

The previous normal planner reports `insufficient_fuel_partial_waypoint`, but a dedicated model comparison showed:

```text
integer projected one-turn distance ~80.623 -> required cost 71
continuous nominal 81-ly leg            -> required cost 72
full target waypoint cost               -> required cost 72

29/71 rasterizes to (2741,2069)  [not factual]
29/72 rasterizes to (2742,2070)  [factual]
```

This is evidence that true partial-route fuel cost may be based on the continuous nominal leg before Host endpoint rasterization. By itself it was not enough to promote a general rule.

## Diagnostic corrections

Do not equate `NormalMovePlan.partial` with `waypoint_distance > effective max distance`.

`partial` can also be true for a geometrically reachable waypoint shortened due to fuel shortage. A true partial route must be classified geometrically from target distance versus effective max movement.

A second diagnostic bug was found and fixed in `partial_move_fuel_cost_move_most_audit.py`: a model cost of exactly zero must mean that fuel does not limit the candidate endpoint. The old helper returned `None` for `fuel_required <= 0`, which created a false projected-vs-nominal discriminator at `511506/T95/ship445`. Commit:

```text
89b5b0f1c06869a0d03d04cba76caa78bc4b10ce
fix: handle zero-cost Move Most candidates
```

## Move Most population audit — corrected runtime result

Use the fast diagnostic:

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

Runtime command completed successfully with `audit rc=0`, `tee rc=0` against source HEAD `030f7489fd94a2af8e60a7da710c9b28b207f152` (that HEAD included the code plus the previous handoff update).

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

The targeted phase-fuel scan recomputed movement mass separately for every hypothetical fuel value from 0 through 5000 KT. Result:

```text
projected_exact_phase_fuel_ranges=()
nominal_exact_phase_fuel_ranges=((11,11),)
both_exact_phase_fuel_ranges=()
projected_only_phase_fuel_ranges=()
nominal_only_phase_fuel_ranges=((11,11),)
projected_exact_post_fuel_ranges=()
nominal_exact_post_fuel_ranges=((0,0),)
```

This resolves the simple phase-fuel ambiguity for this event: changing only movement-phase neutronium cannot rescue the projected/rasterized-distance cost model anywhere in the scanned physical range. Continuous-nominal cost reproduces the factual endpoint uniquely at exactly the factual snapshot fuel, and predicts post-move fuel 0, matching the next factual state.

Owner-visible pre-Host context:

```text
ship_order_fields={}
visible_incoming_transfer_candidates=[]
visible_incoming_tow_tower_ids=()
colocated_planets=[]
```

There were three other same-owner hull-23 ships co-located at the origin, but none had visible transfer/load-like order fields targeting ship41. Co-location alone is not a transfer fact.

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

`360690/T164/ship41` is now a **strong independent Move Most empirical anchor** for continuous-nominal true-partial fuel-cost basis.

It is stronger than a snapshot-only discriminator because:

1. projected cost fails for every scanned phase-fuel value while recomputing mass;
2. nominal cost succeeds only at 11 KT;
3. 11 KT is also the factual pre-Host snapshot fuel;
4. nominal prediction leaves 0 KT and the next factual fuel is 0;
5. no owner-visible transfer/load fuel order explains a state mutation;
6. no currently modelled mine/storm/damage/Tow/Chunnel mechanic explains the endpoint.

The remaining caveat is general Host incompleteness: an unknown mechanic could still alter movement mass/geometry/state. `known_external_flags=()` excludes only the already-modelled factual confounders; it is not proof that no unknown Host behavior exists.

Combined with the independent Intercept case `620694/T73/ship278`, the evidence now points consistently to the same rule across different games/hulls/mission contexts: when a route is geometrically longer than the effective one-turn maximum, fuel requirement appears to use the **continuous nominal one-turn leg before integer endpoint rasterization**, and fuel shortage then prorates movement against that cost.

No observed discriminator supports projected/rasterized endpoint distance as the fuel-cost basis.

## Current implementation mismatch

At this checkpoint, `src/planets_lab/sim/normal_movement.py` still computes `fuel_required` from the rasterized destination distance and explicitly returns `insufficient_fuel_partial_waypoint` instead of applying fuel proration when the route is already geometrically partial.

That implementation therefore does not yet encode the newly strengthened empirical rule.

Before changing it, inspect all callers and regression tests for `plan_full_normal_move`, especially normal movement, Intercept and Tow. The change belongs in `planets-lab` reconstruction first. Do not silently promote it into `planets-intel` production inference until lab regression/corpus verification is complete.

## Immediate next step

1. Audit `src/planets_lab/sim/normal_movement.py` and its callers/tests.
2. Implement the continuous-nominal cost basis for geometrically partial routes in `planets-lab` only.
3. Add explicit regression tests reproducing at least:
   - `360690/T164/ship41` Move Most anchor;
   - `620694/T73/ship278` Intercept anchor or an equivalent unit-level construction with the same 71-vs-72 distinction.
4. Run the complete test suite.
5. Re-run the relevant targeted/corpus diagnostics and compare residuals before considering broader promotion.

## Promotion policy

Do not modify `planets-intel` production finite-fuel inference yet.

For `planets-lab`, the rule now has enough cross-context empirical support to justify an implementation candidate and full regression/differential validation. Promotion beyond the lab still requires confirming that the implementation does not regress established movement/Tow/Intercept behavior.

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
