# Handoff — strict normal-mine survivor audit pending

Date: 2026-09-05

GitHub `main` is source of truth.

## Runtime-verified production baseline

```text
post_fuel_proration_residual = 2220
generic_rows                 = 763
dominant short-forward       = 116
```

No schema/cache/accounting changes are active.

## Closed/rejected recent broad leads

- Crystal Web Drain: one end-to-end attributable evidence-only transition; no production label.
- outbound submitted fuel transfer: rejected for dominant 116.
- standard Cloak fuel burn: rejected for dominant 116.
- Privateer Rob Ship: rejected for dominant 116.
- Stellar Cartography speed terrain: rejected after refined active inventory; active Black Hole/wormhole population is zero.

## Normal-mine slowdown first pass

`tools/diagnostics/normal_mine_slowdown_exposure_audit.py` reproduced the authoritative target population and found:

```text
target_short_rows                              116
target_short_normal_mine_route_exposure         10
target_short_normal_mine_multi_field_route_exposure 2
target_short_positive_planned_distance_deficit  10
target_short_deficit_near_10n                    2
```

The two `10*N` geometry candidates were:

```text
game 360690 turn 155 ship 447 hull 23 deficit 30.575 ly
game 511506 turn  23 ship 160 hull 17 deficit 21.094 ly
```

This is not a broad explanation for the 116-row family.

## Hull-tech gate

`tools/diagnostics/normal_mine_slowdown_candidate_gate_audit.py` resolved the first hard prerequisite:

```text
candidate_rows_found       2
tech_eligible_candidates   1
tech_ineligible_candidates 1
```

### Rejected candidate

`360690 / 155 / ship 447 / hull 23`:

```text
hull tech = 10
```

Nu documents no 10-ly slowdown for hull tech 7+, so this candidate is rejected regardless of mine geometry, diplomacy, RNG or repair.

### Surviving candidate

`511506 / 23 / ship 160 / hull 17`:

```text
hull tech = 6
hull mass = 130
normal-mine corpus damage quantum = 76
before damage = 0
before supplies = 53
after damage = 66
after supplies (observational) = 3
planned distance = 43.566 ly
observed distance = 22.472 ly
deficit = 21.094 ly
```

The damage/supply trace is strikingly compatible with **one** normal-mine hit plus automatic post-movement supply repair:

```text
0 + 76 damage
53 supplies -> repair 10% using 50 supplies
predicted final damage = 66
predicted supplies = 3
```

Two ordinary mine damage hits would instead imply raw damage 152 and, with only 53 submitted supplies, a post-supply-repair damage near 142. Therefore the old `21 ly ~= 2 * 10 ly` heuristic must not be treated as two confirmed impacts.

Current working question is narrower:

```text
one hostile normal-mine hit
  -> +76 damage
  -> documented low-tech slowdown / possible compound movement consequence
  -> post-movement supply repair 76 -> 66
```

## Active diagnostic

```text
tools/diagnostics/normal_mine_single_candidate_immunity_repair_audit.py
```

It checks only `511506 / turn 23 / ship 160` and reports:

1. exact post-decay normal minefields intersecting the planned segment;
2. field IDs/owners and route intervals;
3. turn-specific target-to-field-owner diplomacy;
4. whether field owners grant Safe Passage (`relationfrom >= 2`);
5. target and field-owner team IDs;
6. any minefield Friendly Code values exposed by archived perspectives;
7. exact ship-to-field FC match;
8. one-hit and two-hit supply-repair predictions.

Normal mine immunity rules are fail-closed:

- Safe Passage from the mine owner to the target grants passage;
- exact minefield Friendly Code match grants passage;
- universal `MFx` can only matter when the ship itself uses an `MFx`-shaped code;
- if field FC is not exposed, do not infer hostility from absence alone.

## Immediate work

Run without rebuild:

```bash
python -u tools/diagnostics/normal_mine_single_candidate_immunity_repair_audit.py
```

Key output:

```text
===== INTERSECTED FIELD ELIGIBILITY =====
===== REPAIR TRACE =====
===== SUMMARY =====
```

Decision:

- if all intersected fields are diplomacy/FC immune, reject mine attribution;
- if at least one field is explicitly hostile and the one-hit repair trace is exact, retain one-hit mine evidence and next investigate the remaining movement-distance discrepancy;
- if field FC remains unavailable, keep attribution evidence-only/unresolved rather than guessing;
- do not promote a new production label from this single transition.
