# Finite-fuel Tow same-line reconciliation runtime — 2026-09-11

Runtime source:

- candidate: `661f9d9727d79afb1fc02f2bc8638963ad64a3de`
- source gate: `logs/finite-fuel-tow-break-independent-20260911T081659Z-95419561-9063`
- collected gate: `logs/finite-fuel-tow-same-line-reconcile-20260911T083834Z-661f9d97-15295`

All stages completed `0/0`.

The gate consumed exactly the three `same_line_route` rows left after classic-storm, Chunnel, warp-well, Tow-break and independent-movement cleanup:

- `360690/T41` tower `425` -> target `353`
- `360690/T44` tower `291` -> target `417`
- `360690/T185` tower `436` -> target `124`

All three are reachable-waypoint routes, not true-partial routes.

```text
same_line_input=3
cases=3
combined_only=0
both_models=0
tower_only_only=0
neither_model=3
snapshot_combined_exact=0
snapshot_tower_only_exact=0
tower_after_fuel_zero=1
tower_after_reset_supporting_only=0
```

The bounded physical phase-fuel envelope varied tower Tow-phase neutronium across `1..tower tank` and target neutronium across all mass/10 bins reachable within the target tank while holding all non-fuel mass fixed. It tested both combined movement mass and a tower-only counterfactual. Neither reproduced any factual endpoint for any physically allowed fuel state.

This is a negative result for the current proportional finite-fuel Tow candidate, not evidence for an alternative Tow fuel formula. The three same-line rows must not be used as support for combined-mass proportional Tow proration, tower-only proportional Tow proration, or snapshot neutronium as factual Tow-phase fuel.

The next step is external stop-cause cleanup: visible mine/web context, damage/supply traces and hull-special context. Finite-fuel Tow remains **OPEN**. No `planets-intel` transfer is justified by this gate.
