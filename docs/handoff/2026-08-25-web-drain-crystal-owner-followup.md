# Crystal-owner Web Drain follow-up

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **fuel-proration L2 v6 is verified. The first post-v6 Web Drain differential produced one exact causal-compatible row, but Web Drain is not promoted: the first diagnostic counted every enemy web field, while current Planets.nu documentation states that the 25 KT/field drain is produced by web minefields owned by a Crystal player. A Crystal-owner-aware follow-up is now the active task.**

This handoff supersedes `2026-08-25-fuel-proration-v6-verified-web-drain-followup.md` for active work.

## Verified v6 endpoint

```text
post_mine_strong_residual           2226
fuel_proration_explained               6
post_fuel_proration_residual        2220
label_issues                           0

generic_rows                         763
generic_hulls                         76
dominant short-forward               116
```

Fuel-proration v6 status: **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

## First Web Drain differential

Diagnostic:

```text
tools/diagnostics/web_drain_fuel_proration_audit.py
```

Population guard:

```text
residual_view= movement_post_fuel_proration_residual
generic_non_horwasp_warp1_9_rows= 665
target_short_forward_rows= 116
```

Global result:

```text
visible_enemy_web_at_origin= 98
reachable_waypoint= 250
raw_fuel_sufficient= 228
raw_fuel_insufficient= 22
raw_proration_exact_control= 0

documented_web_drain_rows= 79
web_drain_to_zero_fuel= 12
web_drain_positive_fuel= 67
raw_sufficient_to_web_insufficient= 4
web_drain_fuel_only_endpoint_exact= 0
web_drain_fuel_mass_endpoint_exact= 1
web_drain_causal_exact= 1
fuel_mass_exact_not_fuel_only= 1
synthetic_25_no_web_exact_control= 0
```

Inside the dominant 116-row short-forward family:

```text
visible_enemy_web_at_origin= 65
reachable_waypoint= 92
raw_fuel_sufficient= 90
raw_fuel_insufficient= 2
raw_proration_exact_control= 0

documented_web_drain_rows= 61
web_drain_to_zero_fuel= 2
web_drain_positive_fuel= 59
raw_sufficient_to_web_insufficient= 3
web_drain_fuel_only_endpoint_exact= 0
web_drain_fuel_mass_endpoint_exact= 1
web_drain_causal_exact= 1
synthetic_25_no_web_exact_control= 0
```

The sole exact row is:

```text
game 360690
turn 44
hull 53
one visible web under the first-pass model
fuel 55 -> 30
mass 1274 -> 1249
raw movement fuel required 45
post-drain movement fuel required 44
```

It is exact only when the drained 25 KT is removed from both available fuel and movement mass. This is mechanically coherent with the documented movement-mass formula, but one game / one hull is not enough for production promotion.

## Documentation correction / guardrail

Current Planets.nu Minefields documentation states:

- Web Drain uses the **post-decay circle**;
- a ship inside or within 1 ly of the post-decay web circle loses 25 KT per qualifying field;
- the draining web minefield must be **owned by a Crystal player**;
- web minefields owned by non-Crystal players do not have the 25 KT/turn fuel-drain effect;
- current Standard rules can honor Full Alliance for web fields, so diplomacy compatibility must be checked before a strict production predicate is considered.

Therefore the first-pass `visible_enemy_web_at_origin` count is only a broad geometric lead, not yet a causal Web Drain count.

## Active diagnostic

```text
tools/diagnostics/web_drain_crystal_owner_followup_audit.py
```

It keeps the current v6 endpoint fixed and adds:

```text
Crystal-owner race filter
Crystal-target conservative exclusion
post-decay (after-turn) field geometry
non-Crystal-owned web control
before-turn Crystal-web count for timing context
raw-sufficient -> Crystal-web-insufficient candidates
strict fuel+mass Nu-proration endpoint match
```

It deliberately does **not** reconstruct Full-Alliance immunity yet. Even a surviving Crystal-owner exact row remains evidence-only until diplomacy compatibility is checked.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/web_drain_crystal_owner_followup_audit.py`;
3. require `target_short_forward_rows = 116`;
4. compare `all_enemy_web_at_origin` with `crystal_owner_web_at_origin` and `non_crystal_owner_web_at_origin`;
5. inspect `crystal_web_raw_sufficient_to_insufficient`;
6. inspect `crystal_web_drain_causal_exact` and all candidate rows;
7. if the sole previous exact disappears under the Crystal-owner filter, reject the first-pass causal interpretation;
8. if it survives, inspect diplomacy/Full-Alliance state before considering any production label;
9. do not change L1/L2 schemas or accounting during this follow-up.

Closed work remains closed absent contradictory evidence: fuel-proration v6, strict mine/web hit v5, route-equivalent Tow, Chunnel multiplicity, damage-limited warp, classic/cloudy storms, scoped sphere topology, Horwasp strong context and Red Mite.
