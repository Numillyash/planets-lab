# C5 V11 — V10 residuals: exact T−1 Chunnel endpoint screen

Repository `Numillyash/planets-lab`, source `main`. Do not switch
to `research/external-engine-analysis`. Production `planets-intel`,
`CURRENT`, combat executor, Horwasp and PR #28 remain untouched.

## Runtime source frozen

V10 successfully published:
`runtime-logs/combat-c5-posthost-residual-coupling-v10/20261015T060552Z_8df1ec5ca63f`
(exit_code=0; source `8df1ec5ca63f9838359be696389520e6a2822fec`).
Published report Git blob SHA1:
`9f2fc93e189b264ebdd1d78b0cd0c39517bb2386`.

All original 13 V9 endpoint mismatches (6 game-turns/4 games)
have exact T−1 owner-current snapshots and reverified T coordinates.
None had a known T−1 Tow request targeting the residual vessel.
Two correlated endpoint clusters cover 7 of 13 ships:
- G245123 T75, ships 325/360/912/923: start (2512,1947),
  waypoint (2513,1946), Warp 1, T observed (2504,1351),
  displacement roughly 596 LY.
- G306971 T116, ships 211/285/369: start (2652,2075),
  waypoint (2653,2074), Warp 1, T observed (3074,1914),
  displacement roughly 452 LY.
These are TWO observational episodes, NOT seven independent
confirmations. No Tow orders, mine-hit outcomes or Chunnel status
were proven. An additional standalone G245123 T38 ship 364,
mission 23 and no waypoint displacement, moved ~379 LY;
keep separate from the two clusters.

## V11 falsifiable necessary-condition screen

Official conventional Warp Chunnel documentation:
https://help.planets.nu/mis-warp-chunnel .
This explains how a Chunnel *may* carry same-owner ships
at arbitrary Warp without normal fuel movement, after ordinary
movement phases. Neither shared start nor shared endpoint
by itself identifies a Chunnel.

Freeze exact V10 cases by Git blob. For each of the SIX preselected
game-turn windows, independently read only T−1 owner-current
ships and exact archived hull names. Build a hypothetical actor/target
edge graph from the T−1 roster, requiring:
- Initiator numerical three-character friendly code identifying a
  same-owner target by last-three-digit Ship ID.
- Initiator T−1 fuel >=50 KT and known source position.
- Target owner is the same, fuel >=1 KT, Warp=0, and at
  least 100 LY away in the T−1 snapshot.
- Record hull name mentions of Firecloud as **hints only**;
  names do not establish abilities in Campaign games.
- Record any Tow order on candidate endpoints as a known blocker;
  no inference of successful/failed Tow.

**Critical phase order:** build ALL SIX T−1 graphs before reading
ANY archived T position. Then independently reverify each of the
13 V10 owner-current T endpoints; compute *post-hoc* intersection
with candidate target coordinates. Also count actor edges whose
T−1 source is not one of the residual ship starts as source
controls. The T coordinates MUST NEVER select or build the graph.
Matching an edge to a later T observed endpoint is observational,
not an independent Host Chunnel execution prediction.

A valid conventional edge may be absent because of incomplete
perspectives, unnamed/custom hull abilities, movement before
Chunnel, Tow interruption, modified game rules or another effect.
Absence is not proof of absence of any transportation.

Keep reports small and privacy-safe: publish ONLY numeric friendly
code target IDs and supporting conditions, never raw friendly code,
messages or private player fields. The corpus is previously
collected historical evidence only, not a new holdout.

## One server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-chunnel-endpoint-screen-v11-with-evidence.sh
```

Published report:
`artifacts/combat/c5-chunnel-endpoint-screen-v11/published/report.json`.
Evidence:
`runtime-logs/combat-c5-chunnel-endpoint-screen-v11/`.

## Future acceptance

Do not promote any mechanic from merely matching numeric code
and destination. Require independent initiator/target capability,
archived friendly-code/Host order details and independently
resolved pre-movement versus post-Chunnel actor positions;
otherwise persist `ABSTAIN`. Validate across different
game-turns and new cohorts before replacing risk-masked C5
arrivals or publishing a new movement model.
