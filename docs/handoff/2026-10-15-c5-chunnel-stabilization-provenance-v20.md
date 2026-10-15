# Ordinary C5 Chunnel V20 — T−1 stabilization field provenance

Repository `Numillyash/planets-lab`, `main`. Do NOT change production
`planets-intel`, `CURRENT`, the canonical combat executor, open
draft PR #28, or the external-engine branch.

## Published V19 evidence

`runtime-logs/combat-c5-chunnel-chain-graph-audit-v19/20261015T200120Z_9a5d0366c6ed`
published with exit_code=0, source commit
`9a5d0366c6edf41b200de814865ba46487e40d60`.
Pinned report Git blob `572d14d348235694402148273c7085d212301eac`.
Preceding V17 source Git blob
`a6256b70dc63b9b7126a211245bc65ce20ece863`.

V19: exactly 2 short-to-long two-edge T−1 graph chains;
one first actor at downstream long-distance destination
(G338264/T50 #204->#116->#129), the other first actor
remained at start (G467386/T75 #215->#254->#189).
G467386/T75 #467->#80 25LY was NOT part of either chain.
Exact owner-current T of ship #467 AND three other owner-6
ships #193,#235,#405, initially colocated with #467 and
Warp9, ended at #80. #467 fuel 51->3 (net -48KT); target #80
and passengers #193/#235/#405 each fuel 1->3 (+2KT).
This is strongly Chunnel-like but previously unexplained by
the default minimum distance 100LY.

## Important new official rules

Default Warp Chunnel minimum distance 100LY:
https://help.planets.nu/mis-warp-chunnel

Short Format Rules give the Cyborg a mapwide Chunnel
Stabilization Field, decreasing minimum to **1LY** and allowing
moving Cyborg ships as passengers:
https://help.planets.nu/short-format

A Dungeon Class Stargate (hull ID 108 in normal static catalog)
has the Chunnel Stabilizer ability with 150..550LY radius
depending on engine tech 1..9, also decreasing the minimum
to **1LY** inside its field:
https://help.planets.nu/abil-chunnel-stabilizer

These may resolve apparent 25LY anomaly within documented
rules. Do NOT assume G467386 used Short Format or had
a Dungeon Stabilizer without archival verification.

## V20 frozen protocol

Pin V17+V19 published report Git blobs; preserve V17 original
48 windows/113 candidate edges and V19 2-chain result.
Specifically freeze **all 13** V17 one-gate short-distance
stock Firecloud edges across **9 game/turn windows**,
including 4 distinct-source/target and 9 colocated cases.

For every source window, read ONLY exact T−1 owner-current
snapshots and original raw game `settings` + `game`
fields. Extract only explicit mechanical boolean
Short Format/Stabilizer keys, numeric game-type hints,
and perspective race IDs; NEVER copy free-text descriptions,
account/host settings, saved keys, player names, raw FCs
or private messages. Missing rule flag is ABSTAIN, not disabled.

Independently cross-check frozen initiator/target hull 56 and
T−1 coordinates. Scan T−1 owner-current ships for hull108
confirmed by exact historical hull name Dungeon Class
Stargate, engine ID and position. Calculate documentary
stabilization radius 100+50*engine tech (150..550LY), and
geometrically compare distances to each short-edge actor.
A possible nearby field is NOT proof it was active in Host,
especially with other owners or unobserved Host phases.

Before reading any post-T archive, freeze these game-rule
metadata and field candidates for all 9 windows. Only then
compare each actor T owner-current endpoint with pinned V17
observations, retaining owner/hull/unavailable abstentions.
Report each case's status and the key G467386/T75 actor467
coverage. NEVER automatically rewrite historic V17 100LY
failed-gate labels or claim Host executes short Chunnels
under standard rules.

## Server

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-chunnel-stabilization-provenance-v20-with-evidence.sh
```

Report:
`artifacts/combat/c5-chunnel-stabilization-provenance-v20/published/report.json`
Evidence:
`runtime-logs/combat-c5-chunnel-stabilization-provenance-v20/`

Next after V20: If field provenance positive, design an independent
rule-profile-aware short-distance Chunnel predictor on a NEW,
prospectively frozen corpus, including negative field controls.
If no field provenance is available, keep ABSTAIN and investigate
other game modifiers or mid-host state changes without retrofitting
a special short Chunnel rule.
