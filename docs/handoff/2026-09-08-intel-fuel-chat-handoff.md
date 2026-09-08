# Intel / finite-fuel movement handoff — 2026-09-08

GitHub `main` is the only source of truth for `Numillyash/planets-lab`.

## Current source checkpoint

At the latest handoff update, GitHub `main` is expected to be at or after:

```text
887c67061b8280ccaac1520b475b1904a039f811
diagnostics: add targeted Move Most fuel case audit
```

Always inspect actual `main` before work.

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

This is evidence that true partial-route fuel cost may be based on the continuous nominal leg before Host endpoint rasterization. One case is not enough to promote a production rule.

## Diagnostic corrections

Do not equate `NormalMovePlan.partial` with `waypoint_distance > effective max distance`.

`partial` can also be true for a geometrically reachable waypoint shortened due to fuel shortage. A true partial route must be classified geometrically from target distance versus effective max movement.

A second diagnostic bug was found and fixed in `partial_move_fuel_cost_move_most_audit.py`: a model cost of exactly zero must mean that fuel does not limit the candidate endpoint. The old helper returned `None` for `fuel_required <= 0`, which created a false projected-vs-nominal discriminator at `511506/T95/ship445`. Commit:

```text
89b5b0f1c06869a0d03d04cba76caa78bc4b10ce
fix: handle zero-cost Move Most candidates
```

## Move Most population audit — runtime result

Use the fast diagnostic:

```text
tools/diagnostics/partial_move_fuel_cost_move_most_audit.py
```

The corrected runtime population result over the available finite-fuel, non-Sphere archives is:

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

The single surviving independent Move Most discriminator is:

```text
game=360690
turn=164 -> 165
ship=41
hull=23
warp=9
origin=(1949,2950)
target=(2008,3067)
observed=(1959,2969)
nominal one-turn endpoint=(1985,3022)
waypoint distance=131.034347
nominal max distance=81
rasterized one-turn distance=80.498447
snapshot fuel=11
after fuel=0
snapshot movement mass=517
projected-distance cost=40
continuous-nominal cost=41
11/40 endpoint=(1959,2970) [not factual]
11/41 endpoint=(1959,2969) [factual]
```

This is potentially an independent Move Most anchor for the same continuous-nominal cost basis suggested by `620694/T73/ship278`. It is **not yet promoted** because pre-Host snapshot fuel is not guaranteed to equal movement-phase fuel and an external/earlier Host mechanic still needs to be excluded for this exact event.

Two other `below_both` rows are not discriminators:

- `511506/T32/ship45`: snapshot fuel 0, observed endpoint is not reproduced by either candidate; post-reset is true.
- `511506/T70/ship406`: snapshot fuel 68, after fuel 163, observed endpoint is not reproduced by either candidate; clear evidence that snapshot fuel is not sufficient phase-state evidence here.

## Targeted Move Most forensic audit

A dedicated exact-case diagnostic now exists:

```text
tools/diagnostics/partial_move_fuel_cost_case_audit.py
```

Commit:

```text
887c67061b8280ccaac1520b475b1904a039f811
diagnostics: add targeted Move Most fuel case audit
```

It defaults to `360690/T164/ship41` and checks:

- hypothetical movement-phase fuel values while recomputing movement mass for each value;
- projected-raster-distance cost and continuous-nominal-distance cost separately;
- phase-fuel ranges that reproduce the factual endpoint under either/both models;
- predicted post-move fuel only as supporting evidence;
- owner-visible transfer/load/unload/beam-up-like order fields;
- co-located ships and planets;
- visible incoming transfer and Tow candidates;
- strong mine-hit evidence;
- damage-limited warp;
- ion-storm movement;
- observed Tow route;
- targeted Chunnel route.

Run after pulling `main`:

```bash
cd /opt/planets-lab

git fetch origin
git pull --ff-only origin main

echo "===== HEAD ====="
git rev-parse HEAD
git status --short

echo
echo "===== TARGETED MOVE MOST FUEL CASE ====="

docker compose run --rm -T lab \
  python -u tools/diagnostics/partial_move_fuel_cost_case_audit.py \
  | tee logs/partial-move-fuel-cost-case-360690-t164-ship41.log

RC=("${PIPESTATUS[@]}")
echo "audit rc=${RC[0]}"
echo "tee rc=${RC[1]}"
```

Do **not** run the old broad `partial_move_fuel_cost_population_audit.py` again.

The next evidence decision should be based on this targeted audit output. In particular inspect:

```text
projected_exact_phase_fuel_ranges
nominal_exact_phase_fuel_ranges
both_exact_phase_fuel_ranges
projected_only_phase_fuel_ranges
nominal_only_phase_fuel_ranges
visible_incoming_transfer_candidates
known_external_flags
```

If another movement-phase fuel value allows the projected-cost model to reproduce the endpoint, the snapshot-fuel discriminator remains phase-state ambiguous even if 11 KT favors nominal cost. If nominal cost remains uniquely compatible over plausible phase states and known external mechanics are absent, the case becomes a substantially stronger independent anchor, but still should not by itself force a production law.

## Promotion policy

Do not change production finite-fuel Intercept/Tow/Move Most law from these examples alone.

Desired independent evidence:

- multiple true partial Move Most / normal-movement cases where projected-vs-nominal cost differs;
- phase-fuel ambiguity either resolved or explicitly bounded;
- preferably cases with post-move fuel reset/consumption evidence;
- no already-verified external movement mechanic explaining the same endpoint;
- consistent preference for one cost basis across independent games/hulls.

Keep unsupported phase-fuel state fail-closed in `planets-intel`.

## Cross-repo context

Companion production/client handoff:

```text
Numillyash/planets-intel
docs/handoff/2026-09-08-chat-handoff.md
```

The production client currently has only unlimited-fuel current games, so do not repeatedly request a current finite-fuel runtime sample. Historical archives here are the evidence source.
