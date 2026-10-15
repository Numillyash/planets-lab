# Ordinary C5 V16 — Firecloud Chunnel single-gate negative controls

Canonical `Numillyash/planets-lab`, `main`. Never touch
`research/external-engine-analysis`, production `planets-intel`,
combat executor, `CURRENT`, or draft PR #28.

## V15 published evidence

`runtime-logs/combat-c5-chunnel-actor-outcome-audit-v15/20261015T114241Z_8d6ab268c390`
verified `exit_code=0`, source `8d6ab268c390321db8cea28f745065974107e345`,
published report Git blob
`59f39fdb73779a80c14148d07e30c84e27d699d3`.

Exactly 60 frozen V14 windows, 20 games, 95 T−1 candidate stock
Firecloud actor/target edges; **95/95** actors at frozen target T,
all targets also at their original point T. 55 passenger observations
reproduced from V14, including 22 passenger-bearing actor edges.
Net change in initiator fuel is exactly −50 KT for 50/95 and
something else for 45/95. Counts include net gains; net-50 is
a supportive observation, NOT a required archive-to-archive
signature. Eight regular negative control endpoint mismatches
remain; three share one source and destination in G253449/T128,
but those 8 are NOT automatically attributed to Chunnel.

V15 is a necessary-gates-PASS cohort. No valid inference about
Host Chunnel specificity can follow without pre-outcome gate-failure
controls.

## V16 locked protocol

Pin V15 entire report by Git SHA1, freeze its **same 60 windows**
and check exact 95 original actor-target identities. Use only
exact T−1 owner-current roster from pinned immutable public100.
For each STOCK Firecloud hull56 initiator with numeric 3-digit FC,
find unique same-owner STOCK Firecloud hull56 target whose full ID
has the matching last-three digits.

If missing, ambiguous, moving initiator, or missing pre-Host
geometry/warp/fuel => explicit abstention (NOT a negative).

For stationary initiators and a unique stock target, classify
all five T−1 necessary-condition tests independently:
1. Initiator has >=50 KT neutronium;
2. Target has >=1 KT;
3. Target has Warp 0;
4. source–target distance is >=100 LY;
5. no observed T−1 Tow order targets either endpoint.

No failed tests => positive cohort. Exactly ONE failed test =>
observational negative control, with its name recorded.
Two or more => multi-gate abstention (not falsely independent).
Tow order is not proof of a successful Tow lock, and target
Warp/movement/fuel at Chunnel PHASE may change after T−1.
This is a conservative T−1 screen, NOT an actual execution gate.

Freeze all cases and gate reason counts from T−1 **before** any
T archive read. The positive identity set must agree exactly
with pinned V15 95 source actors and their independent outcomes.
After the full freeze compare owner-current T actor/target positions,
classify at preselected target, still at source, elsewhere, or
owner/hull/stale abstain. Net fuel change is recorded for context,
not used to label an outcome.

This cohort is SAME V15 historical public100 (not a new
game-disjoint holdout). All negative labels are T−1 state,
not proven Chunnel-phase invalidity. A failure to find sufficient
negative controls will be reported as low power, not confirmation.
Avoid non-stock/custom Chunnel target misclassification: other
legal targets (B41b, Lorean, Dungeon Stargate) are outside scope.
Documented target-ID alias priority chooses lowest **valid**
full ship ID, but this study intentionally abstains on duplicate
same-owner stock target suffixes.

Official source:
https://help.planets.nu/mis-warp-chunnel

## One command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-chunnel-single-gate-controls-v16-with-evidence.sh
```

Report:
`artifacts/combat/c5-chunnel-single-gate-controls-v16/published/report.json`.
Evidence:
`runtime-logs/combat-c5-chunnel-single-gate-controls-v16/`.

## Next

If negative controls are informative, consider an independently
sampled new game/turn set with pre-registered actor activation
evaluation, exact targeting on owner-current T−1 data and
time-indexed target movement constraints. If most single-gate
controls nonetheless arrive at a target, inspect intervening Host
phases, ambiguous names/abilities, and ensure regular movement
is not mistaken for Chunnel before modifying any resolver.

Never automatically promote NuHost Chunnel or C5 combat queue
behavior from retrospective observations, including 95/95.
