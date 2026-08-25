# Web Drain diplomacy / game-era follow-up

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **fuel-proration v6 remains verified at post-fuel endpoint 2220. Crystal-owner filtering preserved the sole Web Drain exact case, but Web Drain is not production-promoted. The active task is diplomacy/game-era verification for the four raw-sufficient -> Crystal-web-insufficient candidates.**

This handoff supersedes `2026-08-25-web-drain-crystal-owner-followup.md` for active work.

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

Fuel-proration v6: **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

## Crystal-owner Web Drain result

The refined owner-aware audit kept the exact case intact:

```text
all_enemy_web_at_origin                 79
crystal_owner_web_at_origin             79
non_crystal_owner_web_at_origin          0
crystal_web_raw_sufficient_to_insufficient 4
crystal_web_drain_causal_exact           1
```

Inside the dominant 116-row family:

```text
crystal_owner_web_at_origin             61
crystal_web_raw_sufficient_to_insufficient 3
crystal_web_drain_causal_exact           1
```

The sole exact case remains game 360690 / turn 44 / hull 53. It is exact only when 25 KT is removed from both available fuel and movement mass. This is strong corpus evidence, but one game / one hull is insufficient for promotion.

## Why diplomacy/game era is required

Current Planets.nu documentation states:

- Web Drain requires a web field owned by a Crystal player;
- drain is 25 KT per qualifying field using the post-decay circle plus 1 ly;
- Standard system-generated web diplomacy semantics changed over time;
- before 2021, Safe Passage / Full Alliance semantics could protect ships;
- from 2021-01-01, Standard web fields stopped honoring Safe Passage / Full Alliance;
- from 2023-12-09, Full Alliance was partially restored for Standard web fields while Safe Passage remained excluded.

Therefore the exact case must be checked against the actual game creation era and the actual relation/team state.

## Active diagnostic

```text
tools/diagnostics/web_drain_diplomacy_followup_audit.py
```

It inspects the four runtime-verified raw-sufficient -> Crystal-web-insufficient candidates:

```text
360690 / turn 44 / ship 489
360690 / turn 122 / ship 237
360690 / turn 172 / ship 51
511506 / turn 47 / ship 375
```

For each it reports:

```text
target owner slot / race
Crystal web owner slot(s)
player race/team metadata
same-nonzero-team direct Full Alliance signal
game/settings metadata including hoststart where present
raw relations records between target owner and web owner
relationto / relationfrom / conflictlevel
```

Numeric relation levels are intentionally not interpreted until runtime payload is observed.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/web_drain_diplomacy_followup_audit.py`;
3. run it against the current v6 generated corpus;
4. inspect game 360690 creation/host-start era;
5. inspect target/web owner team IDs and raw relation records for turn 44;
6. apply the documented web-diplomacy rule appropriate to that game era;
7. if the exact case is diplomacy-immune, reject Web Drain as explanation for that row;
8. if the exact case is not immune, retain Web Drain as strong evidence-only unless additional cross-game exact evidence appears.

Do not change production schemas/accounting during this pass. Closed mechanics remain closed absent contradictory evidence.
