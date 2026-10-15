# C5 V10 — inspect V9 residual correlation against independent T−1 orders

Repository `Numillyash/planets-lab`, main. Research-only. Do not touch
`research/external-engine-analysis`, production `Numillyash/planets-intel`,
combat executor or the corpus `CURRENT`; PR #28 remains draft.

## Frozen V9 server result

Evidence: `runtime-logs/combat-c5-site-disjoint-movement-validation-v9/20261015T054556Z_be125d6ec3fc`.
Checked GitHub metadata exit_code=0, main HEAD
`be125d6ec3fce47693915ce82589fab980683c93`, pinned
`public100` immutable read-only DB.

Pinned V9 report Git blob `4e7d707123586311456cc14e78ff774a851caa48`.

V9 selection: 8 games (ZERO overlap with the 17 C5 site games),
16 exact adjacent T−1/T windows chosen using only archive metadata.
7,727 T−1 owner-current ships, 3,191 normal-movement endpoint
forecasts. Fourteen windows were eligible for context reconstruction;
G2466 T60 and T111 abstained because T−1 sphere topology was
unavailable. Do not count those two windows as validated.
G350094 has no final matched/mismatched rows in the aggregate:
inspect window-specific input exclusions before claiming independent
performance for eight games.

Comparable post-Host T results (not precombat positions):
- T−1 normal mine-route risk, conditional **no hit**:
  551 matches and 9 mismatches = 551/560 (98.39%), plus 4 owner drift
  and 10 owner-current T unavailable.
- Normal model without an indexed mine risk: 2,584 matches and
  4 mismatches = 2,584/2,588 (99.85%), plus 18 owner drift and
  11 owner-current T unavailable.
These rows are highly clustered; percentages are CONDITIONAL on
stable owner-current T visibility. They do not prove 100% mine
avoidance, classify hit RNG, or establish precombat site presence.

### Residual preanalysis (published observations, not mechanics)

Exactly 13 mismatches, all preserved from pinned V9 report.
**Nine** mine-risk misses (six G245123/T75, one each in
G306971/T231, G476826/T96, G663317/T54).
**Four** normal misses (one G245123/T38, three G306971/T116).
Four mine-risk G245123/T75 ships share both:
model end (2513,1946), observed T (2504,1351).
Three normal G306971/T116 ships likewise share:
model end (2653,2074), observed T (3074,1914).
This is **two correlated end-point clusters**, 7/13 ships,
not seven independent mismatches. Neither cluster proves Tow,
Chunnel, a mine hit or any particular Host phase.

## V10 exact diagnostic

Pin the full V9 report via Git blob SHA1 and insist that both
cohort denominator/mismatch counts and all 16 original metadata-only
windows remain unchanged. Copy only its 13 mismatch IDs, T−1 owner/
hull IDs, normal conditional endpoints and independently recorded
post-Host T positions.

PHASE ONE: retrieve exact T−1 owner-current snapshots for the 6
affected game-turn windows. For each case, record archived start,
waypoint, mission, warp, fuel, damage, number of colocated ships,
same-waypoint ships and T−1 Tow mission-6 orders explicitly
targeting it. A request to tow is NOT evidence Tow occurred.
Record unknown T−1 context as abstention.

PHASE TWO: separately reread owner-current T archive positions
and identity. Must agree with pinned V9 published T comparison.
Report distance/residual/damage changes ONLY as observations.
A mismatch, a Tow request or post-turn damage change is not
mine-hit evidence. All 13 retain ABSTAIN as their mechanic
attribution unless external terminal/phase evidence is obtained.

There are no new prospective predictions or new causal mechanics.
Do NOT use post-hoc cluster membership as a feature in a
generative movement predictor. V10 is an attribution inventory.

## Execution (one command)

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-posthost-residual-coupling-v10-with-evidence.sh
```

Report:
`artifacts/combat/c5-posthost-residual-coupling-v10/published/report.json`.

Evidence:
`runtime-logs/combat-c5-posthost-residual-coupling-v10/`.

## Next

After real V10 runtime, determine whether any confirmed T−1 tow
requests, co-movement or source-geometry conflict are found.
Select an independent *prospective movement and mine-hit outcome*
cohort with minefield geometry frozen at T−1 and post-T damage/
movement outcomes used only as labels. Keep true mine-hit
mechanism unknown without reliable damage, immunity, repairs,
friendly code, overlapping fields, and processing order evidence.
