# Web Drain evidence closure and outbound fuel-transfer follow-up

Date: 2026-08-26

Repository: `Numillyash/planets-lab`

Status: **strict Nu fuel-proration v6 remains the production endpoint at 2220. The sole post-v6 Crystal Web Drain exact case has now passed Crystal ownership, historical game-era, and exact turn-specific diplomacy attribution. It is retained as strong evidence-only because support remains one game / one hull. The active generic follow-up is outbound submitted fuel transfer before movement feeding the already verified Nu fuel-proration rule.**

This handoff supersedes `2026-08-26-web-drain-relation-pair-pending.md` for active work.

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

No production schema or accounting change is made by the Web Drain evidence closure.

## Web Drain evidence closure

Earlier post-v6 diagnostics established:

```text
crystal_owner_web_at_origin                 79
non_crystal_owner_web_at_origin              0
crystal_web_raw_sufficient_to_insufficient   4
crystal_web_drain_causal_exact               1
```

The sole exact case is:

```text
game 360690
turn 44
ship 489
hull 53
target owner slot 6 / race 6
Crystal web owner slot 7 / race 7
one qualifying Crystal-owned web
fuel 55 -> 30
movement mass 1274 -> 1249
raw movement fuel required 45
post-drain movement fuel required 44
```

It matches the observed endpoint only when the drained 25 KT is removed from both available fuel and movement mass. Raw Nu-proration and synthetic no-web controls were zero in the earlier differential.

### Historical era / diplomacy attribution

Raw `.trn` evidence showed:

```text
game 360690 datecreated = 2020-03-03
iscustom = false
turn 44 relation pair selected by exact keys:
  playerid   = 6
  playertoid = 7
  relationto   = -1  # target -> Crystal
  relationfrom = -1  # Crystal -> target
  conflictlevel = 0
```

The exact relation-pair / era audit classified:

```text
era = pre_2021_classic
web_diplomacy_immune = False
web_drain_allowed = True
exact_case_web_drain_allowed = True
exact_case_diplomacy_guard = PASSED
```

For comparison, the non-exact game `511506` candidate is a Standard game created in 2022 and falls in the 2021-to-2023 era where Standard web fields ignore Safe Passage / Full Alliance for this purpose.

### Evidence status

The Web Drain chain is now attributable end-to-end for one transition:

```text
Crystal-owned web
  -> no historical diplomacy immunity
  -> documented 25 KT fuel drain
  -> movement mass reduced by the same 25 KT
  -> raw-fuel-sufficient becomes positive-but-insufficient
  -> documented Nu waypoint-distance fuel proration
  -> exact observed Host x/y endpoint
```

Status: **DOCUMENTED + CORPUS_OBSERVED strong evidence case; evidence-only, not production-promoted.**

Reason for no production label: only one independent game / hull exact transition is currently attributable. Do not overfit the production classifier to this row.

## Active follow-up — outbound fuel transfer before movement

Planets.nu Host order places both own cargo updates and ship-to-foreign-ship transfers before mass check and normal movement. Historical raw ship records contain submitted transfer fields including:

```text
transferneutronium
transfertargetid
transfertargettype
```

A submitted outbound fuel transfer can therefore create the same mechanical pattern as the verified Web Drain case:

```text
raw snapshot fuel sufficient
  -> pre-movement fuel transfer removes neutronium
  -> movement mass falls by the transferred fuel mass
  -> remaining fuel becomes insufficient
  -> already verified Nu waypoint proration
  -> short same-line move
```

New diagnostic:

```text
tools/diagnostics/outbound_fuel_transfer_proration_audit.py
```

It runs against `movement_post_fuel_proration_residual` and preserves the population guard:

```text
target_short_forward_rows = 116
```

The audit requires current-visible co-located transfer targets before treating a submitted transfer as a mechanical candidate. It separately reports whether receiver fuel-tank capacity is directly confirmable from the sender perspective; unresolved foreign receiver capacity remains evidence-only.

Important counters:

```text
outbound_fuel_transfer
transfer_target_current_visible
transfer_target_colocated
transfer_target_same_owner
transfer_target_foreign_owner
receiver_full_transfer_capacity_confirmed
receiver_capacity_unresolved_or_insufficient
raw_sufficient_to_transfer_insufficient
transfer_fuel_only_endpoint_exact
transfer_fuel_mass_endpoint_exact
transfer_causal_exact
transfer_strict_confirmed_exact
fuel_mass_exact_not_fuel_only
raw_proration_exact_control
```

The strongest possible result is cross-game / cross-hull exact support where the submitted transfer is directly attributable and `fuel+mass` outperforms `fuel-only`, while the post-v6 raw-proration control remains zero.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/outbound_fuel_transfer_proration_audit.py`;
3. run it without rebuilding L1 or L2;
4. require `residual_view = movement_post_fuel_proration_residual` and `target_short_forward_rows = 116`;
5. inspect transfer target-type distribution before assuming numeric target-type semantics;
6. inspect current-visible / co-located target coverage;
7. inspect raw-sufficient -> transfer-insufficient candidates and exact endpoints;
8. promote nothing from the first pass unless there is independent, attributable support;
9. keep Web Drain evidence-only and do not reopen its already resolved ownership/diplomacy attribution absent contradictory evidence.

## Invariants

- GitHub `main` is source of truth.
- Current L1 schema remains `planets-lab.compiled-movement.v3`.
- Current L1 context marker remains `planets-lab.compiled-movement-storm-context.v3`.
- Current L2 schema remains `planets-lab.compiled-movement-context-labels.v6`.
- Current authoritative final movement residual remains `2220`.
- Closed mechanics stay closed absent new contradictory evidence.
