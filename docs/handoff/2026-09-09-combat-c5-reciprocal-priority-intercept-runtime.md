# C5 Host combat — reciprocal Priority Intercept runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains excluded from ordinary-mechanics tuning.

## Runtime provenance

User-operated WSL/Docker runtime source:

```text
1576dd083b2691464b98e3260d7c6474fb2ed339
```

Targeted tests:

```text
................................ [100%]
tests rc=0
```

Reciprocal Priority Intercept audit:

```text
audit rc=0
payload_conflicts=0
archives_considered=11
candidate_rows=1
target_case_rows=1
```

Artifact:

```text
artifacts/combat-c5-reciprocal-pia-20260909-143602/
```

## Exact historical row

The only ordinary reciprocal-only candidate is the former Case 1 itself:

```text
game 511506 / battle T19 / VCR13 / (2565,1729)

LEFT  Firecloud80 owner6 race6 hull56
      mission3 Kill / PE5 / FC027 / fuel150

RIGHT Meteor89 owner5 race5 hull46
      cloak-capable / mission7 target80 / PE0 / FC2eC / fuel26
```

Audit classification:

```text
interceptor_side:          right: 1
standard_relation:         left_higher_priority: 1
target_aggression_shape:   kill_and_pe: 1
site_first_ship_vcr:       True: 1
site_ship_vcr_count:       1: 1
multi_vcr_site_rows:       0
```

Thus the row that previously appeared as a standard-side contradiction is the only corpus row matching the documented reciprocal Priority Intercept branch.

## Documentation boundary

Primary Planets.nu Priority Intercept documentation states two relevant facts:

1. a cloak-capable Intercept ship with matching PE can fight its target before ordinary combat;
2. **if the intercepted starship would combat the intercepting starship, that combat also occurs before other combats at the same location**.

Primary references:

```text
https://help.planets.nu/cloak-intercept
https://help.planets.nu/battle-order
```

The Order Of Battle page also states the general principle that the more aggressive combatant fights first and from the right side, and that Priority Intercept Attack ships fight their targets before ordinary ship combat.

A secondary VGA Planets Wiki description explicitly says successful Priority Intercept engages the target from the right-hand side, but that secondary statement is not promoted as a standalone primary rule.

## What is closed

Case 1 no longer belongs to the standard battle-priority residual bucket.

The factual stacked context plus documented Intercept relation explain why Meteor89 is the selected opponent for Firecloud80 even though Meteors29/102 and ship73 are physically present: ship89 is uniquely linked to ship80 by mission7 Intercept, while Firecloud80 itself requests combat with owner5 through Kill!/PE5.

Scoped status:

```text
reciprocal Priority Intercept branch text:       DOCUMENTED
Case1 stacked context / factual pair:             CORPUS_OBSERVED
priority_intercept_reciprocal_target_signature:  TESTED
Case1 reciprocal pair/pre-standard attribution:  DIFF_VERIFIED
```

This is a **scoped attribution of the historical pair/phase**, not a promotion of a universal new side rule.

## What is not established

The corpus contains no independent reciprocal-only control row:

```text
candidate_rows=1
```

Therefore do **not** promote any of the following from this runtime alone:

- `reciprocal interceptor always RIGHT` as an independently diff-verified universal rule;
- reverse-ID ordering for reciprocal-only multi-attacker sites;
- multi-VCR-site queue ordering for this branch (`multi_vcr_site_rows=0`);
- omitted dynamic blockers such as diplomacy, matching FC, fuel, cloak interference, or other eligibility interactions.

The canonical helper remains fail-closed and consumes `target_would_combat_interceptor` as already-resolved dynamic hostility rather than inventing full engagement eligibility.

## Consequence for the two former mission-7 left-higher residuals

Both are now removed from ordinary standard-priority tuning for distinct documented reasons:

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Gorbie
```

Do not weaken `standard_battle_priority_key(...)` or Friendly Code parsing to fit either row.

## Next C5 gate

Proceed to matching Friendly Code suppression and Harmonic Weapon Modulation boundaries, then integrate normal PIA, reciprocal Priority Intercept and Bird C&I into one dynamic pair-selection layer.
