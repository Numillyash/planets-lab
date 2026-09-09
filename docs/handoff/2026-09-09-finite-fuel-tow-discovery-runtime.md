# Finite-fuel Tow historical discovery — runtime result

Date: 2026-09-09

GitHub `main` remains the source of truth. This handoff records the first completed historical finite-fuel Tow discovery gate and the prepared follow-up. It does **not** promote finite-fuel Tow.

## Server gate

Runner:

```text
tools/run-finite-fuel-tow-historical-gate.sh
```

Collected server log directory:

```text
logs/finite-fuel-tow-20260909T105441Z-f5f97756-11257
```

All stages completed successfully:

```text
inputs          0 / 0
tooling         0 / 0
pytest          0 / 0
tow-discovery   0 / 0
summary         0 / 0
```

Full test suite:

```text
371 passed
```

No archive was missing.

## Strict finite-fuel Tow population

The 12-game corpus split as:

```text
finite_fuel_games                 4
sphere_excluded_games             1
unlimited_fuel_excluded_games     7
fuel_setting_unknown_games        0
```

Strict route filtering produced:

```text
observed_tow_attempt_records      8281
observed_route_targets            4765
route_identity_ambiguous             2
same-target contests excluded       21
tow chains excluded                 20
lock_nonfuel_proven               4576
lock_nonfuel_unresolved              8
target_visible_to_tower_owner     4499
fuel_model_ready                  4499
```

The non-fuel Four Fingers proofs were:

```text
target_waypoint_within_warp_square 4046
target_lt2_engines                  421
target_effectively_slower           109
lock_depends_on_target_phase_fuel     8
```

## Fuel differential result

Route geometry split:

```text
true_partial_route                1080
reachable_route                   3419
geometry_exact                    1871
geometry_differs                  2628
```

Snapshot-level cost comparison:

```text
snapshot_projected_exact          1868
snapshot_nominal_exact            1868
snapshot_nominal_only                0
snapshot_projected_only              0
snapshot_both                     1868
snapshot_neither                  2631
```

Broad physical Tow-phase neutronium envelope, while holding non-fuel mass fixed:

```text
phase_both_possible               1914
phase_nominal_only_possible          0
phase_projected_only_possible        0
phase_neither_possible            2585
```

The important negative result is therefore explicit:

```text
No nominal-vs-rasterized cost-basis discriminator was found for finite-fuel Tow.
```

This does **not** falsify the continuous nominal-leg rule. It means the current strict Tow population does not isolate the cost-basis choice. The already `DIFF_VERIFIED` normal-movement result for Move Most + Intercept must not be transferred to Tow from this gate.

## Interpretation of the residual

The direct phase envelope explains 1914 strict routes under both cost bases and leaves 2585 strict routes unreachable under either fuel-cost hypothesis.

Many displayed `phase_neither_possible` examples have factual endpoints displaced only a few light-years from the direct Tow endpoint. That is a strong discovery hypothesis for ordinary warp-well capture, but it is **not yet evidence status** because the first pass did not join those endpoints to the historically eligible per-turn planet set.

The next pass must use the canonical warp-well eligibility boundary:

- game `nowarpwells` setting;
- only ordinary planets with stable `debrisdisk == 0`;
- ambiguity fails closed.

Only after that should the remaining residual be sent to transfer/mine/storm/damage/Chunnel analysis.

## Prepared warp-well follow-up

Diagnostic:

```text
tools/diagnostics/tow_finite_fuel_warp_well_audit.py
```

Runner:

```text
tools/run-finite-fuel-tow-warp-well-gate.sh
```

The runner re-runs the strict Tow discovery with a complete example capture into a gitignored server log, then consumes the entire `phase_neither_possible` population and applies ordinary warp-well capture to:

1. full-geometry Tow endpoint;
2. snapshot projected/nominal fuel endpoints;
3. the broad physical Tow-phase fuel envelope.

Key follow-up counters are:

```text
observed_is_eligible_planet
geometry_warpwell_exact
snapshot_warpwell_both_exact
snapshot_warpwell_nominal_only
snapshot_warpwell_projected_only
phase_warpwell_both_possible
phase_warpwell_nominal_only_possible
phase_warpwell_projected_only_possible
phase_warpwell_neither_possible
phase_warpwell_ambiguous_cases
```

A nominal-only or projected-only result after warp-well handling is still only a discovery signature. It must receive targeted transfer/mine/storm/damage/Chunnel and phase-state attribution before any Tow promotion.

## Status

```text
finite-fuel Tow: OPEN
first historical discovery gate: COMPLETED
nominal-vs-projected Tow discriminator: NONE FOUND
warp-well follow-up: PREPARED, NOT YET RUN
planets-intel Tow transfer: BLOCKED
```

Do not change production Tow behavior from this checkpoint.
