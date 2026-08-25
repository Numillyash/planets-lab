# Rob Ship exposure follow-up

Date: 2026-08-26

Repository: `Numillyash/planets-lab`

Status: **production movement endpoint remains unchanged at `post_fuel_proration_residual = 2220`. Crystal Web Drain is closed as one fully attributable evidence-only case. Outbound submitted fuel transfer and standard Cloak fuel consumption are rejected for the dominant 116-row short-forward family. The active generic follow-up is a population/exposure audit for Privateer Rob Ship before movement.**

This handoff supersedes `2026-08-26-cloak-fuel-proration-pending.md` for active work.

## Verified production baseline

```text
post_mine_strong_residual           2226
fuel_proration_explained               6
post_fuel_proration_residual        2220
label_issues                           0

generic_rows                         763
generic_hulls                         76
dominant short-forward               116
```

No production schema/accounting change is made by the rejected transfer/Cloak leads or by this Rob exposure pass.

## Closed/rejected recent evidence leads

### Crystal Web Drain

One game `360690` / turn `44` / hull `53` transition remains a fully attributable `DOCUMENTED + CORPUS_OBSERVED` evidence-only chain:

```text
Crystal-owned web
  -> no historical diplomacy immunity
  -> 25 KT fuel drain
  -> movement mass reduced by 25 KT
  -> raw sufficient becomes positive-but-insufficient
  -> verified Nu waypoint proration
  -> exact Host x/y
```

It is not production-promoted because support remains one independent game/hull.

### Outbound submitted fuel transfer

Runtime over current post-v6 generic Warp 1..9 rows:

```text
outbound_fuel_transfer = 2
transfer_target_current_visible = 0
raw_sufficient_to_transfer_insufficient = 0
transfer_causal_exact = 0

target_short_outbound_fuel_transfer = 0
target_short_transfer_causal_exact = 0
```

Rejected for the dominant family.

### Standard Cloak fuel consumption

Runtime differential:

```text
target_short_forward_rows = 116
target_short_cloak_capable_hull = 6
target_short_standard_cloak_hull = 2
target_short_cloak_mission = 0
target_short_standard_cloak_fuel_burn_candidate = 0
target_short_cloak_causal_exact = 0
```

Globally, residual rows with mission `10` existed, but all eight relevant mission-10 rows were on hulls lacking static cloak capability. There were no standard-Cloak fuel-burn candidates. Cloak therefore cannot explain the dominant family and is rejected absent new evidence.

## Active follow-up — Privateer Rob Ship exposure

Planets.nu documents Rob Ship as a Privateer special mission that executes in the early Mission-9 block before all ship movement. A robber:

- must be able to perform Rob Ship;
- needs beams;
- robs fuel before other cargo;
- fills its own fuel tank/hold;
- acts in ascending robber ship ID, with targets robbed in ascending target ship ID;
- cannot rob cloaked ships or ships protected by Safe Passage-or-higher from the robber owner;
- can fail with a documented 1% chance.

Before implementing that full ordering/diplomacy/failure model, the current pass measures only whether the residual population was exposed at all to a mechanically plausible co-located Privateer Mission-9 ship.

New diagnostic:

```text
tools/diagnostics/rob_ship_exposure_audit.py
```

Population guards:

```text
residual_view = movement_post_fuel_proration_residual
target_short_forward_rows = 116
privateer_race_id = 5
special_mission_id = 9
```

A `rob_exposure_candidate` requires a co-located owner-record ship whose owner race is Privateer, mission is 9, static hull has beams, current fuel is positive, and its fuel tank has free capacity.

The diagnostic intentionally does **not** yet apply:

```text
ascending robber/target ID robbery simulation
Safe Passage diplomacy immunity
victim Host-phase cloak state
Protofield destruction
1% Rob failure chance
```

Important outputs:

```text
privateer_mission9_at_origin
rob_exposure_candidate
rob_exposure_static_noncloak_victim
rob_exposure_positive_victim_fuel

target_short_privateer_mission9_at_origin
target_short_rob_exposure_candidate
target_short_rob_exposure_static_noncloak_victim
```

If `target_short_rob_exposure_candidate = 0`, reject Rob Ship for the 116-row family immediately. If exposure exists, only then build a second-pass exact robbery-order/diplomacy audit.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/rob_ship_exposure_audit.py`;
3. run it without rebuilding L1/L2;
4. require `target_short_forward_rows = 116`;
5. inspect target-family Rob exposure before doing any exact robbery simulation;
6. if exposure is zero, reject Rob and move to the next broad pre-movement external-state mechanism;
7. if exposure is nonzero, inspect examples and then reconstruct exact robbery order/diplomacy only for exposed rows;
8. keep production accounting at `2220` throughout.

## Invariants

- GitHub `main` is source of truth.
- L1 schema remains `planets-lab.compiled-movement.v3`.
- L1 context marker remains `planets-lab.compiled-movement-storm-context.v3`.
- L2 schema remains `planets-lab.compiled-movement-context-labels.v6`.
- Authoritative final movement residual remains `2220`.
- Closed mechanics remain closed absent contradictory evidence.
