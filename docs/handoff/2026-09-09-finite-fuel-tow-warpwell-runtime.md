# Finite-fuel Tow warp-well follow-up — runtime result

Date: 2026-09-09

GitHub `main` is the source of truth. This handoff records the completed warp-well follow-up at candidate `7974ba8c29551d085348963328de03713eeca5d5`. It does **not** promote finite-fuel Tow.

## Server gate

Runner:

```text
tools/run-finite-fuel-tow-warp-well-gate.sh
```

Collected server log directory:

```text
logs/finite-fuel-tow-warpwell-20260909T112928Z-7974ba8c-22147
```

All stages completed successfully:

```text
inputs              0 / 0
tooling             0 / 0
pytest              0 / 0
discovery-full      0 / 0
warp-well-followup  0 / 0
summary             0 / 0
```

Full test suite:

```text
371 passed
```

The strict Tow discovery was reproduced with:

```text
phase_neither_possible = 2585
```

## Warp-well result

The complete direct `phase_neither_possible` population was consumed:

```text
phase_neither_input                    2585
cases                                  2585
observed_is_eligible_planet            2531
observed_not_eligible_planet             54
geometry_warpwell_exact                2529
geometry_warpwell_ambiguous               0
snapshot_warpwell_both_exact           2494
snapshot_warpwell_nominal_only            0
snapshot_warpwell_projected_only          0
snapshot_warpwell_neither                91
snapshot_warpwell_ambiguous               0
phase_warpwell_both_possible           2529
phase_warpwell_nominal_only_possible      0
phase_warpwell_projected_only_possible    0
phase_warpwell_neither_possible          56
phase_warpwell_ambiguous_cases            0
owner_snapshot_missing                    0
imported_ship_missing                     0
hull_spec_missing                         0
engine_spec_missing                       0
```

Per-game residual accounting:

```text
game 360690  input 819  warp-well both 777  residual 42
game 511506  input 977  warp-well both 971  residual  6
game 620636  input  37  warp-well both  37  residual  0
game 620694  input 752  warp-well both 744  residual  8
```

Ordinary historically eligible warp wells therefore explain `2529 / 2585` of the direct phase-neither population, about `97.83%`.

Exactly 54 residual factual endpoints are not eligible planets. Two additional residuals do land on an eligible planet but are not reproduced by the direct Tow geometry plus ordinary warp-well capture. This follows from the independent counters `observed_not_eligible_planet=54`, `phase_warpwell_neither_possible=56`, and `geometry_warpwell_exact=2529` versus `observed_is_eligible_planet=2531`.

The broad phase-fuel envelope explains 35 more rows than the snapshot-fuel state after warp-well handling (`2529 - 2494`). This remains phase-state evidence only; the witness fuel values are not factual Tow-phase neutronium.

## Cost-basis result

The negative cost-basis result remains unchanged after warp-well handling:

```text
snapshot_warpwell_nominal_only             0
snapshot_warpwell_projected_only           0
phase_warpwell_nominal_only_possible       0
phase_warpwell_projected_only_possible     0
```

So the current corpus still contains **no finite-fuel Tow discriminator** between continuous nominal one-turn costing and rasterized-endpoint-distance costing.

This does not contradict the already differential-verified Move Most + Intercept rule. It only means that rule still cannot be transferred to finite-fuel Tow from the available strict Tow population.

## Remaining 56

The remaining population is small enough for a targeted external-mechanics pass rather than another broad movement scan.

Current residual distribution:

```text
game 360690   42
game 511506    6
game 620694    8
```

The next audit should classify these exact 56 against already-modelled context only:

- ion storms;
- strong mine/web interaction;
- damage-limited movement;
- Chunnel participation / route-equivalent relocation;
- submitted outbound/inbound cargo or fuel transfers that can alter Tow-phase mass or fuel;
- any remaining known external movement path.

Do not reinterpret a transfer flag as proof of the resulting Tow-phase state. It is a confounder boundary unless the order, target, amount/capacity and resulting state are independently attributable.

## Status

```text
finite-fuel Tow: OPEN
first historical discovery gate: COMPLETED
warp-well follow-up: COMPLETED
warp-well explanation of prior phase-neither: 2529 / 2585
post-warp-well residual: 56
nominal-vs-projected Tow discriminator: NONE FOUND
planets-intel Tow transfer: BLOCKED
```

No production Tow behavior changes from this checkpoint.
