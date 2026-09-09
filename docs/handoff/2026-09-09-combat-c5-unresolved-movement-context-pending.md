# C5 Host combat — focused unresolved movement context pending runtime

Date: 2026-09-09

This is an attribution-only follow-up to the ten-row v2 movement-position residual audit. It does not alter the independent T-1 position predictor.

## Input population

The bounded residual runtime on source:

```text
1d880ca6e0a1e0784f2fae4437c981ce71ac49ed
```

left exactly four rows unresolved after six exact classic ion-storm matches:

```text
360690/T54/ship26 owner6 hull52
511506/T95/ship332 owner5 hull31
620694/T62/ship83 owner8 hull69
680910/T14/ship65 owner8 hull1102
```

Input artifact:

```text
artifacts/combat-c5-normal-movement-position-residual-20260909-231621/report.json
```

## Diagnostic

```text
tools/diagnostics/combat_host_normal_movement_unresolved_context_audit.py
tests/test_combat_host_normal_movement_unresolved_context_audit.py
```

Schema:

```text
planets-lab.combat-host-normal-movement-unresolved-context-audit.v1
```

The diagnostic intentionally uses factual/post-movement evidence only to attribute already-known residuals. Those facts must never become candidate-set predictor inputs.

### Probe A — route-equivalent Chunnel

The audit reuses:

```text
extract_stable_chunnel_abilities(...)
discover_observed_chunnel_events(...)
route_equivalent_chunnel_category(...)
```

It asks whether an independently discovered observed Chunnel event has:

```text
pre_chunnel_position == v2 predicted position
and
destination == factual combat site
```

This specifically tests whether a ship can first reach its normal post-navigation position and then be transported by the later Chunnel phase. It does not infer Chunnel solely from a large displacement.

### Probe B — field-backed scaled-floor normal-mine geometry

For each unresolved row the audit reuses the existing empirical helper:

```text
scaled_floor_normal_mine_endpoint(...)
```

and checks:

- planar topology;
- factual hull tech/mass from archive static specs;
- exact factual endpoint equality for one or more slowdown-hit counts;
- hostile normal minefield intersection in before-turn and/or battle-turn evidence;
- factual combat-start VCR damage when available;
- normal-mine nearest damage quantum from the existing classifier.

A mine candidate family requires all of:

```text
hull tech < 7
exact scaled-floor endpoint
visible hostile normal-field route crossing
```

Even a positive candidate remains attribution-only because mine-hit occurrence is random until the relevant minefield phase/RNG state is independently reconstructed.

## Pre-runtime geometry leads

Two rows have exact one-hit scaled-floor geometry before any field evidence is considered:

```text
620694/T62/ship83
origin=(1744,1460)
target=(1783,1437)
warp=7
nominal=49
regular_distance≈45.2769256907
one-hit penalty=floor(10*49/regular)=10
exact endpoint=(1773,1443) == factual site

680910/T14/ship65
origin=(2315,1984)
target=(2312,1924)
warp=9
nominal=81
regular_distance≈60.0749531835
one-hit penalty=floor(10*81/regular)=13
exact endpoint=(2313,1937) == factual site
```

These are `INFERRED` leads only until historical field/VCR evidence is produced by the runtime audit.

The other two rows receive no pre-runtime promotion. In particular, the large `360690/T54/ship26` displacement is only a Chunnel hypothesis until an independently observed route-equivalent event matches it.

## Required runtime

Run this focused audit together with the full storm-aware position v3 gate. Required outputs:

- targeted test result / rc;
- full v3 position summary and every remaining mismatch example;
- focused unresolved-context summary and all four context rows;
- zero VCR payload conflicts for any factual combat-start evidence used.

Do not promote any candidate family before that runtime.
