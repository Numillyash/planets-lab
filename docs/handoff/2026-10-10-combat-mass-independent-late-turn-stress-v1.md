# Independent early/late mass-component stress (V1)

## Frozen success from PR #166

Full successful runtime evidence:
runtime-logs/combat-mass-tminus1-race-bonus-audit-v1/20261010T195013Z_3b779a2a6bd8

12 independent earlier games / 15 ship VCRs / 30 sides. All 30 T-1
historical owner races independently resolved. Exactly four sides had
factual VCR mass +50KT above the independently known hull component.
All four were Federation raceid=1 by archived T-1 roster, while the
remaining 26 were non-Federation and had +0KT delta. Combined
T-1 hull mass plus conditional documented race bonus matched all
30 factual masses. Full combat mass predictions made: zero.

This was early-game observational testing, NOT proof of the full
NuHost combat phase. Federation player slot and race ID are different.

## Pre-registered independent temporal stress

Research-only code:
tools/diagnostics/combat_mass_independent_late_turn_stress_v1.py

1. Byte-check BOTH prerequisite published reports against the precise
   git blob hashes on runtime-logs; detect retroactive baseline changes.
2. SHA256-check immutable public100 database once, open read-only, never
   touch CURRENT or production/client databases.
3. Exclude ENTIRE games from the 14 targeted static-control game/turn
   pairs (11 unique game IDs), plus all 12 earlier held-out games.
4. Without reading ANY factual combat mass, current VCR race or residual,
   select new eligible games using only archived game-turn metadata:
   at least 6 VCR-bearing adjacent T-1/T pairs spanning 20 turns.
   Sample up to 24 game IDs at deterministic even quantiles.
5. Preselect 2 periods per game: chronological 20th and 85th percentile
   of VCR-bearing archived turns. These time windows are not selected
   based on forecast performance.
6. Current ship VCRs provide target owner/hull identity only; T-1 player
   rosters and hull catalogs provide features. Require exact T-1 and
   agreement across ALL observed perspectives. Missing, malformed,
   contradictory or absent inputs must ABSTAIN, not silently backfill.
7. Build static hull component, then conditional Federation +50KT
   increment from historical T-1 raceid=1 (other races +0KT).
   Current VCR mass and raceid enter ONLY AFTER candidate calculation,
   solely for comparison and visibility of phase changes.
8. Report all included and excluded VCRs, coverage, abstentions, and
   differences by early and late strata. No residual calibration.
   Positive and negative controls are inherited from fixed historical
   Federation / non-Federation races and independently selected games.

The documented +50KT Federation crew advantage is a conditional
component, not proof of campaign-specific effect activation, actual
battle-phase owner continuity or total combat mass. Shield Generators,
Horwasp clans, carrier RNG, capture and mutable combat site remain
outstanding. No production executor/rule promotion.

## Single server run

    cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-mass-independent-late-turn-stress-v1-with-evidence.sh

Report:
artifacts/combat/mass-independent-late-turn-stress-v1/published/report.json

Evidence:
runtime-logs/combat-mass-independent-late-turn-stress-v1/

Real external DB evaluation must still be executed. CI alone does not
confirm how often the conditional component matches complex late turns.
