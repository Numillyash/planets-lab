# C5 V17 — discriminate Chunnel gate failures before observing T

Canonical: `Numillyash/planets-lab`, main. Do not change
`research/external-engine-analysis`, `Numillyash/planets-intel`,
combat executor, corpus `CURRENT` or draft PR #28.

## V16 runtime observation and essential correction

`runtime-logs/combat-c5-chunnel-single-gate-controls-v16/20261015T115607Z_eb8acb1e798b`
successful, exit_code 0, source
`eb8acb1e798b3bd0443dd470ccc84e24f97e02f0`;
published V16 Git blob
`9b12fde64ca175d3ac29b7135606cf2c73c24119`.

95/95 frozen T−1 gate-pass actors at distinct (>=100 LY) targets
after Host. Original V16 published 27 single-failed-gate T−1
negative controls, including 15 with distance below 100 LY.
**Fourteen of those fifteen** have EXACT source==target at T−1:
their T archive actor is also at that point, so apparent "at
target" is a TAUTOLOGY, not movement or false activation.
One remaining short-distance case has distance ~3.16 LY and
actor is elsewhere at T. No distance<100 negative has a
discriminating observed endpoint at its original target.

Of the 13 truly source/target-distinguishable negative controls:
- Initiator fuel <50 KT: 3/3 stayed at origin;
- Target Warp !=0 at T−1: 4/4 stayed at origin;
- Tow order on source/target at T−1: 2/5 stayed at source,
  3/5 elsewhere; none at original target;
- Distance 0<d<100 LY: 1/1 elsewhere.
These are OBSERVATIONAL negative controls, not independently
verified phase conditions. In one short-distance case both
actors' target ship moved, and the actor's net fuel dropped
50 KT, so post-T evidence is not a causal Chunnel log.

Official rule: Chunnel source/target must be at least 100 LY
apart and both have fuel; target Warp 0; initiator >=50 KT;
a successful Tow lock blocks Chunnel:
https://help.planets.nu/mis-warp-chunnel

## V17 new preregistered protocol

Exclude all 17 C5 V6 games, 8 V9 validation games, 12 V13
validation games and 20 V14/V15/V16 games = **57 different games**.
Using ONLY public100 source_members game/turn metadata, choose 16
further eligible games spaced by sorted game ID, and three
adjacent T−1/T windows per game = 48 windows. This is
game-disjoint but from the SAME existing public100 corpus,
not a newly collected independent validation dataset.

From every exact T−1 owner-current roster, preselect stock
Firecloud hull56 owner + numeric friendly code + unique stock
target hull56, stationary actor, one-gate failure/zero-gate
cohorts using V16 conservative predicates. Missing/ambiguous
target, multiple gate failures, moving actor or missing
T−1 settings are ABSTAIN with counts.

**CRITICAL**: freeze `source != target` as a mandatory
discriminative criterion at T−1, independent of all T outcome
knowledge. If `source == target`, classify
`NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET` and NEVER
count an "actor at target" as Chunnel support. Valid
distance>=100 gate-pass controls are inherently discriminative.

Freeze ALL 48 T−1 candidate sets and failure reasons
BEFORE reading ANY owner-current T archive.
Only afterward evaluate observed actor T as
at distinct target / at source / elsewhere / unavailable,
and target T positions + net fuel changes for context.
Report separate denominators per game, gate and
coincident pair population. Zero actual negative cases
is reported as low evidence; do NOT infer specificity.

PR tests must include adversarial same-coordinate actor+target
even with net 50KT loss, distinct-source negative outcomes,
missing/owner drift, source-provenance guard, fixed game exclusions,
and absolute T−1-before-T phase barrier.

No VCR N+1, no combat queue promotion, no causal Chunnel
activation attribution. Tow request is not proven Tow lock,
T−1 target Warp may change before Host Chunnel phase,
and different abilities/custom hulls remain out of scope.

## Server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-disjoint-discriminative-chunnel-gates-v17-with-evidence.sh
```

Report:
`artifacts/combat/c5-disjoint-discriminative-chunnel-gates-v17/published/report.json`.
Evidence:
`runtime-logs/combat-c5-disjoint-discriminative-chunnel-gates-v17/`.

## Future research

If new game-disjoint negative gate failures are observed,
compare sensitivity and specificity at the **episode/window
level**, not per co-located ship. Then build an experimental
T−1 phase-aware Chunnel state machine with formal abstention
handling for Tow, moving actors, target movement, target aliases,
and other valid Chunnel-target abilities. Validate on a newly
captured immutable corpus not used in V6–V17 before considering
canonical Host movement or combat queue changes.
