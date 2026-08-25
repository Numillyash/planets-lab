# Stellar Cartography raw feature inventory follow-up

Date: 2026-08-26

Repository: `Numillyash/planets-lab`

Status: **production movement endpoint remains unchanged at 2220. Cloak fuel and Privateer Rob Ship are rejected for the dominant 116-row short-forward family. The active task is a raw Stellar Cartography feature/schema inventory before any terrain-specific movement model is attempted.**

This handoff supersedes `2026-08-26-rob-ship-exposure-pending.md` for active work.

## Verified production baseline

```text
post_fuel_proration_residual = 2220
generic_rows                 = 763
generic_hulls                = 76
dominant short-forward       = 116
```

No L1/L2 schema or accounting change is part of this follow-up.

## Rejected lead — Cloak fuel

Runtime audit over `movement_post_fuel_proration_residual` found:

```text
target_short_cloak_mission = 0
target_short_standard_cloak_fuel_burn_candidate = 0
target_short_cloak_causal_exact = 0
synthetic_cloak_cost_noncloak_mission_exact_control = 0
```

Globally, mission `10` residual rows existed, but the evaluated mission-10 rows were not on static cloak-capable hulls. Standard Cloak therefore cannot explain the dominant 116-row family.

## Rejected lead — Privateer Rob Ship

The exposure-only audit found:

```text
rob_exposure_candidate = 1
rob_exposure_positive_victim_fuel = 1

target_short_privateer_mission9_at_origin = 1
target_short_rob_exposure_candidate = 0
target_short_rob_exposure_positive_victim_fuel = 0
```

The sole global exposure is game `360690`, turn `39`, hull `99`, outside the dominant family. No second Rob simulator pass is justified for the 116-row target.

## Active follow-up — raw Stellar Cartography inventory

Planets.nu documentation describes the common Stellar Cartography features as follows:

- nebulae primarily alter visibility and some abilities;
- star clusters can destroy ships / irradiate crews;
- debris disks can destroy large ships and disrupt towing;
- wormholes require the explicit Enter Wormhole mission;
- Black Hole ergospheres are described as inhibiting warp speed.

Before writing any terrain movement classifier, inventory which of these feature families are actually present in the raw `.trn` archives and whether their payload paths occur on archive turns that contain the surviving 116-row short-forward family.

Diagnostic:

```text
tools/diagnostics/stellar_cartography_raw_feature_inventory.py
```

It scans one deterministic raw perspective per archive turn and reports only feature-related schema paths and mechanically safe scalar excerpts. It does not emit account identity, messages, secrets, or arbitrary player text.

Required guards:

```text
residual_view = movement_post_fuel_proration_residual
target_short_forward_rows = 116
```

Decision rule:

- if black-hole / other speed-modifying terrain paths are absent across the corpus, reject the terrain-speed lead;
- if relevant paths exist but never on target-family turns, reject them for the dominant family;
- only if a relevant feature is present on target-family turns should a narrow geometry/timing audit be built from the observed raw schema and documented mechanic.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check and run `stellar_cartography_raw_feature_inventory.py`;
3. inspect `GLOBAL FEATURE PATHS` first;
4. identify whether any black-hole/ergosphere payload exists at all;
5. inspect target-turn occurrence counts for any movement-relevant terrain path;
6. do not add a terrain classifier from schema presence alone;
7. keep production accounting at `2220` throughout.

## Invariants

- GitHub `main` is source of truth.
- L1 schema remains `planets-lab.compiled-movement.v3`.
- L1 context marker remains `planets-lab.compiled-movement-storm-context.v3`.
- L2 schema remains `planets-lab.compiled-movement-context-labels.v6`.
- Web Drain remains a one-row fully attributable evidence-only case.
- outbound fuel transfer, Cloak fuel, and Rob Ship are rejected for the current dominant 116-row family absent new evidence.
