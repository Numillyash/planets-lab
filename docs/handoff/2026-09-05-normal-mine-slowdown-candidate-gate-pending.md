# Normal mine slowdown candidate gate follow-up

Date: 2026-09-05

Repository: `Numillyash/planets-lab`

Status: **production movement endpoint remains unchanged at 2220. Stellar Cartography terrain-speed is rejected as a broad explanation. The normal-mine slowdown exposure pass found only two target-family rows with route exposure plus a distance deficit near 10*N ly. The active task is a hard candidate gate: hull tech first, then only surviving rows advance to diplomacy/friendly-code/RNG/repair reconstruction.**

## Verified production baseline

```text
post_fuel_proration_residual = 2220
generic_rows                 = 763
generic_hulls                = 76
dominant short-forward       = 116
```

## Closed terrain-speed lead

Refined active-feature inventory reproduced `target_short_forward_rows = 116` and found:

```text
blackholes active_turns = 0
blackholes target_active_turns = 0
wormholes active_turns = 0
wormholes target_active_turns = 0
```

Nebula/debris are active on only seven target turns and are not a broad ordinary Move Most speed mechanism. No terrain classifier is justified.

## Normal-mine slowdown exposure result

Runtime exposure audit over the current post-v6 target family:

```text
target_short_rows = 116
target_short_normal_mine_route_exposure = 10
target_short_normal_mine_multi_field_route_exposure = 2
target_short_positive_planned_distance_deficit = 10
target_short_deficit_near_10n = 2
```

The two surviving geometry candidates are:

```text
game 360690 / turn 155 / ship 447 / hull 23 / deficit 30.575 / implied 3 hits
game 511506 / turn 23  / ship 160 / hull 17 / deficit 21.094 / implied 2 hits
```

This is not yet mine-hit evidence. The first pass used owner-different field exposure as an upper bound and did not apply historical diplomacy, minefield friendly-code immunity, hull-tech eligibility, exact hit RNG or repair reconstruction.

## Active diagnostic

```text
tools/diagnostics/normal_mine_slowdown_candidate_gate_audit.py
```

It evaluates only the two runtime-derived candidates and reports:

```text
hull_tech
hull_mass
slowdown_tech_eligible
normal_mine_damage_quantum
owner / enemy field IDs / owners
before damage/supplies/fuel/mass
observational after damage/supplies/fuel/mass
observed damage delta
```

Documented hard gate:

```text
hull tech >= 7 -> normal-mine hit does not cause the 10 ly slowdown
```

Therefore no diplomacy/FC/RNG/repair work is justified for a tech-ineligible candidate.

## Decision rule

1. If `tech_eligible_candidates = 0`, reject repair-hidden normal-mine slowdown for the dominant family.
2. If one or two candidates have hull tech `<7`, keep only those candidates.
3. For each survivor, next reconstruct historical Safe Passage and minefield/ship friendly-code compatibility against the exact intersected field owners/IDs.
4. Only after immunity is ruled out should exact route-field geometry, mine-hit multiplicity probability and repair compatibility be evaluated.
5. Do not create a production label from one or two candidates without independent cross-game support and a clean attributable differential.

## Invariants

- GitHub `main` is source of truth.
- L1 schema remains `planets-lab.compiled-movement.v3`.
- L1 context marker remains `planets-lab.compiled-movement-storm-context.v3`.
- L2 schema remains `planets-lab.compiled-movement-context-labels.v6`.
- Production accounting remains `2220` during this follow-up.
- Web Drain remains one attributable evidence-only case.
- outbound transfer, Cloak fuel, Rob Ship and terrain-speed remain closed for the current dominant family absent new evidence.
