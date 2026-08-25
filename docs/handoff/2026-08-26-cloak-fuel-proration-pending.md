# Cloak fuel -> Nu proration follow-up

Date: 2026-08-26

Repository: `Numillyash/planets-lab`

Status: **fuel-proration v6 remains the verified production endpoint at 2220. The Web Drain chain is closed as one fully attributable evidence-only case. Outbound submitted fuel transfer was tested and rejected as a useful explanation for the dominant 116-row short-forward family. The active generic follow-up is standard Cloak fuel consumption before movement feeding the already verified Nu waypoint-proration rule.**

This handoff supersedes `2026-08-26-web-drain-evidence-closed-transfer-followup.md` for active work.

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

No production schema/accounting change is made by the Web Drain or transfer investigations.

## Web Drain evidence closure

The sole exact Web Drain transition is fully attributable:

```text
game 360690 / turn 44 / ship 489 / hull 53
Crystal-owned web count = 1
fuel 55 -> 30
movement mass 1274 -> 1249
raw required 45
post-drain required 44
exact Nu-prorated endpoint
```

Historical raw `.trn` evidence and the keyed relation-pair audit established:

```text
game created 2020-03-03
iscustom = false
era = pre_2021_classic
relation playerid=6 -> playertoid=7
relationto = -1       # target -> Crystal
relationfrom = -1     # Crystal -> target
web_diplomacy_immune = false
web_drain_allowed = true
exact_case_diplomacy_guard = PASSED
```

Status: **DOCUMENTED + CORPUS_OBSERVED strong evidence case; evidence-only, not production-promoted** because independent support remains one game / one hull.

## Rejected lead — outbound submitted fuel transfer

Runtime audit:

```text
residual_view = movement_post_fuel_proration_residual
generic_non_horwasp_warp1_9_rows = 665
target_short_forward_rows = 116
```

Global:

```text
outbound_fuel_transfer = 2
transfer_target_id_missing = 1
transfer_target_not_current_visible = 1
transfer_target_current_visible = 0
raw_sufficient_to_transfer_insufficient = 0
transfer_fuel_mass_endpoint_exact = 0
transfer_causal_exact = 0
```

Inside the dominant 116-row family:

```text
target_short_outbound_fuel_transfer = 0
target_short_transfer_causal_exact = 0
```

Conclusion: outbound `transferneutronium` is not a useful explanation for the dominant family and needs no follow-up absent new evidence.

## Active follow-up — standard Cloak fuel consumption

Current Planets.nu documentation establishes:

- Cloak runs before ordinary movement;
- classic Cloak mission ID is 10;
- standard Cloak consumes `max(5, floor(hull_mass / 20))` KT Neutronium;
- the cloak fuel burn reduces the mass used in the later movement fuel calculation;
- Advanced Cloak consumes no fuel;
- a ship already damaged at the start of the turn cannot cloak and does not consume cloak fuel.

This creates the same general causal pattern as the verified Web Drain case, but using fully owner-visible local state:

```text
raw fuel sufficient
  -> submitted Cloak mission
  -> standard cloak burns fuel
  -> movement mass falls by the same fuel amount
  -> remaining fuel becomes insufficient
  -> verified Nu waypoint proration
  -> short same-line move
```

New diagnostic:

```text
tools/diagnostics/cloak_fuel_proration_audit.py
```

It runs against `movement_post_fuel_proration_residual` and preserves:

```text
target_short_forward_rows = 116
```

Strict inputs:

```text
mission == 10
static hull can_cloak == true
static hull is not Advanced Cloak
raw damage == 0
positive fuel remains after cloak cost
reachable waypoint
same immutable ship identity after turn
non-Gravitonic / non-Horwasp
```

It compares:

```text
raw_proration_exact_control
cloak_fuel_only_endpoint_exact
cloak_fuel_mass_endpoint_exact
cloak_causal_exact
fuel_mass_exact_not_fuel_only
```

Specificity control:

```text
synthetic_cloak_cost_noncloak_mission_exact_control
```

This applies the same documented cloak cost to otherwise eligible cloak-capable ships whose submitted mission is not Cloak. A strong result should have real mission-10 exact matches while this synthetic control remains sparse/zero.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/cloak_fuel_proration_audit.py`;
3. run it without rebuilding L1/L2;
4. require `residual_view = movement_post_fuel_proration_residual` and `target_short_forward_rows = 116`;
5. inspect mission distribution, especially mission 10 within the target family;
6. inspect standard-vs-Advanced-Cloak counts;
7. inspect `raw_sufficient_to_cloak_insufficient`, exact counts and synthetic non-Cloak controls;
8. promote nothing from the first pass unless exact support is cross-game/cross-hull and specific to actual Cloak mission rows;
9. keep Web Drain evidence-only and outbound transfer closed absent contradictory evidence.

## Invariants

- GitHub `main` is source of truth.
- Current L1 schema remains `planets-lab.compiled-movement.v3`.
- Current L1 context marker remains `planets-lab.compiled-movement-storm-context.v3`.
- Current L2 schema remains `planets-lab.compiled-movement-context-labels.v6`.
- Current authoritative final movement residual remains `2220`.
- Closed mechanics stay closed absent new contradictory evidence.
