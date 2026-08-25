# Web Drain relation-pair / game-era follow-up

Date: 2026-08-26

Repository: `Numillyash/planets-lab`

Status: **fuel-proration v6 remains verified at post-fuel endpoint 2220. Raw `.trn` discovery recovered the historical game-era and relation payload needed to resolve the remaining Web Drain diplomacy guard. A narrow relation-pair audit is now the active task.**

This handoff supersedes `2026-08-25-web-drain-raw-metadata-discovery.md` for active work.

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

Web Drain is still evidence-only. The Crystal-owner-aware differential currently has one exact causal-compatible row:

```text
crystal_owner_web_at_origin                 79
non_crystal_owner_web_at_origin              0
crystal_web_raw_sufficient_to_insufficient   4
crystal_web_drain_causal_exact               1
```

The exact row is game `360690`, turn `44`, hull `53`, and matches only when the drained 25 KT is removed from both available fuel and movement mass.

## Raw `.trn` metadata discovery result

The raw loadall payload contains the metadata that the privacy-safe prepared projection intentionally strips.

For game `360690` / turn `44` / target slot `6` / Crystal slot `7`:

```text
game.datecreated = 3/3/2020 10:18:00 PM
game.iscustom    = false
settings.maxsafepassage = 35
settings.hoststart = 5/28/2020 12:01:24 AM
player/team ids = 0 for both target and Crystal
relations list present, len=11
```

The same game remains a pre-2021 Standard game at the later turn-122 and turn-172 candidates. At turn 172 the raw settings explicitly include:

```text
webdiplomacylevel = 0
```

Game `511506` / turn `47` is also Standard:

```text
game.datecreated = 8/19/2022 12:00:21 PM
game.iscustom    = false
settings.webdiplomacylevel = 0
team ids = 0
relations list present
```

The raw discovery printed relation levels in list order, but the final attribution must not rely on array index. It must select the exact pair by `playerid` / `playertoid`.

## Documented/client evidence used for the guard

Current Planets.nu Minefields documentation states that Standard system-generated games **created after 2021-01-01** stopped honoring Safe Passage / Full Alliance for web fields, with Full Alliance partially restored for games created after 2023-12-09.

The historical Planets.nu client relation scale is consistent with:

```text
2 = Safe Passage
3 = Share Intel
4 = Full Alliance
```

and client code uses `relationfrom` as the other player -> current player direction. Therefore, for a pre-2021 Standard game, the material question is whether the Crystal owner granted the target Safe Passage or higher (`relationfrom >= 2`).

## Active diagnostic

```text
tools/diagnostics/web_drain_relation_pair_audit.py
```

It reads the raw `.trn` member for exactly the four already-identified candidates and:

1. selects the relation object by exact `playerid == target_slot` and `playertoid == Crystal_slot`;
2. reports only the safe relation fields;
3. interprets `relationto` as target -> Crystal and `relationfrom` as Crystal -> target;
4. applies the Standard game-era rule from `game.datecreated`;
5. reports `web_diplomacy_immune` and `web_drain_allowed` per candidate;
6. reports a dedicated `exact_case_diplomacy_guard` summary for game `360690` turn `44`.

No production schema/accounting change is made by this audit.

## Expected decision

The raw discovery already strongly suggests that the exact turn-44 relation toward Crystal slot 7 is below Safe Passage, but the array order is not used as evidence. The new audit must resolve the exact pair directly.

If the result is:

```text
exact_case_web_drain_allowed= True
exact_case_diplomacy_guard= PASSED
```

then the diplomacy/game-era guard is closed and the exact Web Drain chain is attributable:

```text
Crystal-owned post-decay web
-> 25 KT drain
-> fuel and movement mass both decrease
-> formerly sufficient fuel becomes insufficient
-> verified Nu waypoint proration
-> exact observed endpoint
```

Even then, Web Drain remains evidence-only because support is still only one game / one hull. Do not promote a one-row production label merely because the diplomacy guard passes.

If the exact pair is Safe Passage-or-higher under the pre-2021 rule, reject Web Drain as the cause of that row.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/web_drain_relation_pair_audit.py`;
3. run it against the current local raw archives;
4. require `candidate_relation_pairs_found = 4`;
5. inspect the exact game `360690` / turn `44` relation pair and era decision;
6. close the diplomacy guard from the exact keyed relation record;
7. keep production accounting at `2220` regardless of outcome;
8. if the guard passes, archive Web Drain as strong evidence-only and return to broad residual triage unless a second independent exact Web Drain case can be found.
