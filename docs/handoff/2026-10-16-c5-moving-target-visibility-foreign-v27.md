# V27: moving target, disappearing owner-current, foreign routes — single evidence run

Canonical source `Numillyash/planets-lab` main, research only. DO
NOT touch production `planets-intel`, combat executor, external engine
research, PR #28 or immutable corpus CURRENT.

## Verified evidence

V26: `runtime-logs/combat-c5-new-corpus-exception-batch-v26/20261016T105213Z_9375bbeab989`
(complete/clean, exit 0). V26 pinned Git blobs:
- manifest `1b44aa0d1f885a3adbf58bdf7fffd065d18e42f8`
- exception_routes `65816f42bd5030da8cd58ca8fb76cf0eea3f864a`
- archive_visibility `327af41f73a4415650cc2c07ac08a30a5c7d6105`
- passenger_episodes `8c55051e98ab0b4a6484054d494316ad81db95e9`

V25 exact public8 immutable DuckDB:
`/root/projects/planets-corpus-db/generations/corpus-v2compact-c5-v25-public8-20261016.duckdb`
SHA256
`af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a`.

Published V25 report blobs:
manifest `2c89d5320b31b2f12d9235192a8ac31240549052`,
actors `423e6123496068b8d2987bd27fe0b455fee4c1df`,
fields `b559901540ee1a906811ed4e510629be70aae365`,
passengers `ebe8e812d91a80e4fd3c9ccdbc99df0edcc98145`.

### Key V26 observation

V25 heldout-by-game: 58 eligible long actor candidates, 55
at frozen Tminus1 target, 1 elsewhere, 2 T owner-current unavailable.
22 episode windows in three new games. V26 discovered that the ONLY
long actor elsewhere, G403181/T60 #143 owner1, ended at
(2198,1799), and **its target Firecloud #202 moved to exactly the
same new coordinate**, from Tminus1 (2326,2181), despite frozen
target Warp0. Thus original V25 55/1/2 scoring against Tminus1
target remains correct, but the apparent one Host activation
failure may instead be a later movement of *the target and actor*
together. A shared postHost destination is STILL NOT independent
proof of Chunnel execution or phase ordering.

Two other unavailable G521268/T116 actors #388 (owner7),
#577 (owner4), and their targets #192/#240 are missing
owner-current T, **although all 12 player perspectives are in both
Tminus1 and T archives**. Absence is not automatically a missing
source-member archive or ship death.

V25 foreign-owner source colocations: 8 ships, 7 at their
episode's frozen target in FOUR of FIVE episodes; all are
from ONE G521268 game and all foreign ships are owner6.
Ship count is not independent episode count and none proves
a specific alliance/Chunnel passenger rule.

## V27 ONE batch / THREE reports

1. `moving_targets.json`: for ALL 58 original long
   actors in the 33 V25 exposed game-turn windows, freeze exact
   Tminus1 actor+target IDs, owners and coordinates, then AFTER
   all Tminus1 contexts freeze, compare BOTH T actor and T
   target owner-current positions. Cross-tab against original
   V25 55/1/2 buckets. Report whether #143 and #202 remain
   colocated, count other T targets that actually moved.
   DO NOT alter the original frozen-target validation score;
   posthoc T target is not an independently forecast target
   movement or a direct phase trace.
2. `identity_provenance.json`: confirm full 12-player T
   archive perspective metadata for #388 and #577, their own
   target ship owner-current availability, and optionally
   inspect EXACT T+1 **owner-current ship state only** as
   explicitly retrospective identity provenance (no N+1
   VCR). T+1 never changes the V25 frozen score and does NOT
   prove destruction or Host Chunnel action. If no eligible
   T+1 archive, ABSTAIN explicitly.
3. `foreign_routes.json`: independently rebuild the five
   V25-selected foreign-owner source episodes, eight foreign
   Tminus1 ship owner/hull/Warp/fuel/waypoint/mission/Tow
   orders, freeze before T, compare original V25 T owner-current
   endpoints for all eight, and test whether a direct waypoint
   warp route to the Chunnel target is geometrically possible.
   No claim that foreign ownership means diplomacy, successful
   passage, Tow, fuel transfer or passenger eligibility.

Reuses `v26.select_roster` across ALL 33 original V25 active
windows and checks complete V25/V26 published evidence chain.
One SHA256 verification of existing new public8 DB, read-only.
Global pre-T barrier also holds for T+1 followup. Three
distinct JSON reports + SHA256 manifest published in one
`run-with-runtime-evidence.sh` invocation.

This is POSTHOC explanation, NOT new dataset, NOT new
held-out trial, and no Host Chunnel activation proof.

## One exact server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-moving-target-visibility-foreign-v27-with-evidence.sh
```

Reports:
`artifacts/combat/c5-moving-target-visibility-foreign-v27/published/`.
Evidence:
`runtime-logs/combat-c5-moving-target-visibility-foreign-v27/`.
No new archive download or DuckDB generation. Single manual invocation.
