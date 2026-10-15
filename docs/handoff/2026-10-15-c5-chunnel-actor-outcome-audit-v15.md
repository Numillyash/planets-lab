# Ordinary C5 V15 — all candidate Chunnel actors and eight negative controls

Repository: `Numillyash/planets-lab` `main`, not
`research/external-engine-analysis`. Keep production `planets-intel`,
combat executor, PR #28 Draft/Open, immutable corpus CURRENT untouched.

## Published V14 source

Evidence: `runtime-logs/combat-c5-conditional-chunnel-holdout-v14/20261015T112807Z_1108fd27e83d`.
Exit_code=0, source main `1108fd27e83db31e325ea4f5f17a6e9dd1d51a8a`.
Git blob SHA1 of the published report:
`60aeb5ae5ccc828116911bbc61bd752374bc2df7`.

20 games disjoint from V6/V9/V13, 60 metadata-only selected T−1/T windows,
95 T−1 Firecloud source/target eligible edges.
55 unambiguous conditional passengers: **55/55** T owner-current
coordinates agree with conditional Chunnel target, none with ordinary
no-Chunnel model endpoint; 54 no-indexed-mine-risk, 1 mine-risk.
These were distributed over 15 windows, 10 games and 22 individual
actor/target edge episodes. This is 22 episodes, NOT 55 independent
mechanic verifications.

Normal negative controls: 526 matched ordinary baseline,
8 mismatched, and 6 abstained (1 no owner-current T, 1 hull
identity drift, 4 owner drift). Note ID-ordered (first ten)
controls are NOT a statistically random sample.

Do NOT confuse 55/55 *conditional target accuracy* with ability to
predict actual Chunnel activation before Host. The V14 output does
not report T actor/target endpoints or 50KT net fuel; V15 adds that.

## V15 strict protocol

Pin V14 by Git blob and verify its full 60-window, 95-edge, 55-passenger,
540-control sample. Verify V6, V9 and V13 source Git blobs and game
exclusions. Reconstruct EXACT SAME 60 windows from immutable public100
using T−1 archive state only. Build every Firecloud edge and negative
control, including the previously selected 55 passengers, before any
T archive is accessed.

After all 60 T−1 feature contexts are successfully frozen:
- For all 95 eligible actor/target edges, compare T actor owner/hull,
  T target owner/hull and endpoint; classify actor at frozen destination,
  at original source, elsewhere, or missing/owner/hull drift.
- Observe, but do NOT require, exactly 50KT net actor fuel decrease.
  Transfers, refuelling, and chained multi-Chunnel phases can alter
  the post-Host net fuel.
- Independently recompare all 55 passenger and 540 normal-negative
  rows against published V14. Fail closed on any changed
  ship status / owner / hull / endpoint comparison.
- Preserve and individually examine the eight negative controls
  that disagree with the ordinary movement baseline. Retrieve
  their archived T−1 starting point, waypoint, Warp, mission and
  fuel. Record proximity to pre-frozen Firecloud sources, and
  posthoc matches to pre-frozen Firecloud targets without converting
  these associations into a new Host prediction.
- Count actor episodes by **game** and **game/turn**; never
  count multiple passengers as independent activations.

IMPORTANT documented boundary discovered after V14:
https://help.planets.nu/mis-warp-chunnel states that if multiple
valid Chunnel target ship IDs have the same last three digits, the
valid target with the **lowest full Ship ID** is chosen. Current
V13/V14 fail-closed on ambiguous target IDs. That policy is
conservative but incomplete; V15 does NOT retroactively
resolve ambiguity, alter cohort definitions, or apply an untested
priority model.

If a T actor is no longer at the original target, do not call
its prior Chunnel invalid: it may have been moved by another
Chunnel or Host phase. Likewise net-50KT is supportive, not
necessary, and T after Host cannot serve as an independent
Chunnel activation log.

## One command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-chunnel-actor-outcome-audit-v15-with-evidence.sh
```

Report: `artifacts/combat/c5-chunnel-actor-outcome-audit-v15/published/report.json`.
Evidence: `runtime-logs/combat-c5-chunnel-actor-outcome-audit-v15/`.

Next: if most actor edges agree but some are displaced or fuel-change
conflicted, design a *new* metadata-selected game/turn cohort with
pre-registered multi-Chunnel transition graph and explicit host
ordering tests. Do not promote C5 combat site arrival or canonical
movement machinery until phase ordering and self-consistency are
independently established.
