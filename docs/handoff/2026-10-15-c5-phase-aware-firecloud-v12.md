# Ordinary C5 — phase-aware Firecloud Chunnel residual screen V12

Canonical: Numillyash/planets-lab, main. Do not switch to
research/external-engine-analysis. This is OBSERVATIONAL ONLY;
do not modify the combat executor, production planets-intel,
the corpus CURRENT, or draft PR #28.

## V11 runtime evidence and crucial correction

Successful V11 runtime published:
`runtime-logs/combat-c5-chunnel-endpoint-screen-v11/20261015T063624Z_7f717965ce28`.
Source HEAD `7f717965ce28292f3b2f8255504f2878d8b77d59`;
exit_code=0. Immutable pinned V11 report Git blob
`98e31ff87b615af1e60d9e120317cbbe8c756d4e`.

V11 compared T−1 starts against Chunnel source positions and
found 4 endpoint matches (G245123/T75), 9 without a starting-site
source. BUT all four candidates at their actual T−1 START were
**non-Firecloud passengers** with a numeric FC, not proven Chunnel
initiators. Stock Firecloud #293 at (2513,1946) independently names
Firecloud #646 at (2504,1351); Firecloud #377 at (2653,2074)
independently names Firecloud #581 at (3074,1914).
The published T−1 ordinary-route model ends at the first Firecloud
source for the two groups:
- G245123/T75, residual ships 325/360/912/923:
  T−1 start (2512,1947), conditional normal pre-move endpoint
  (2513,1946), post-Host T (2504,1351).
- G306971/T116, residual ships 211/285/369:
  T−1 start (2652,2075), ordinary normal pre-move endpoint
  (2653,2074), post-Host T (3074,1914).

A third possible source edge is visible for G476826/T96:
Firecloud #458 at (1629,2491) targeting Firecloud #340
at (1525,2374); residual ship #358 has a conditional normal
endpoint (1629,2491). These form three potential episodes, not
eight independent confirmations. The G245123 risk class still
has unresolved mine route effects.

NuHost's official Warp Chunnel help states that ordinary movement
takes place before Chunnel, allowing ships arriving at a Firecloud
source to travel through it, conditional on valid endpoints and
eligibility:
https://help.planets.nu/mis-warp-chunnel
Official Firecloud ability descriptions:
https://help.planets.nu/abil-chunnel-initiator
https://help.planets.nu/abil-chunnel-target

## V12 scientific gate

Pin exact V11 report and 13 original V9 residuals; freeze all six
independent **exact T−1** owner-current candidate edge graphs BEFORE
reading any T owner-current ship data.

- Discard every numeric-FC source/target edge not comprised of
  documented STOCK Firecloud hulls (both IDs 56); report them as
  negative candidate controls. Other custom hulls and abilities
  remain UNKNOWN, not proof of absence of transport.
- Require same owner, initiator fuel >=50, target warp0/fuel>0
  and >=100 LY (reused V11 gate). Any T−1 tow order on the
  endpoints remains a blocker; missing intermediate phase state
  remains unverified.
- Instead of comparing the residual vessel's T−1 **start** to the
  Firecloud source, use its previously pinned independent
  `frozen_normal_model_endpoint`. The normal endpoint was computed
  before observing the T comparator in V9, not fitted to Chunnel.
  This is only a model of pre-Chunnel arrival, not a factual one.
- Only AFTER all six source candidate graphs are frozen compare
  separately archived post-Host T ship positions. Also report
  archival owner-current T actor/target positions and possible
  initiator fuel delta 50 KT as evidence without granting proof
  of execution: other Host processing may intervene.
- Never score preselected cases as independent holdout trials.
  These are all posthoc V9 residuals; positive or negative matches
  must remain observational. A zero-match cohort also cannot
  exclude unknown customized Chunnel/Temporal abilities.

## One server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-phase-aware-firecloud-v12-with-evidence.sh
```

Report: `artifacts/combat/c5-phase-aware-firecloud-v12/published/report.json`.
Evidence: `runtime-logs/combat-c5-phase-aware-firecloud-v12/`.

Follow-up: If V12 supports the three Firecloud source-target
episodes, test the source ship's FC, T−1 warp, actor fuel and T
position, and non-residual colocated passengers, then compare a
preregistered held-out population of Firecloud pairs and ordinary
movement to validate a genuine post-movement passenger rule.
Only after independent validation should NuHost movement pipeline
be altered; no C5 combat queue promotion from this run.
