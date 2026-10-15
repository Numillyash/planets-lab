# C5 V14 — game-disjoint conditional Firecloud vs normal movement comparator

Source of truth: `Numillyash/planets-lab` `main`. Keep
`research/external-engine-analysis`, production `planets-intel`,
combat executor and corpus `CURRENT` untouched; PR #28 remains Draft.

## Verified V13 runtime and evidence delivery

Evidence `runtime-logs/combat-c5-firecloud-disjoint-validation-v13/20261015T110316Z_8323d5ba1ebd`.
`exit_code=0`, source `8323d5ba1ebd52954e43c59c00726fde5cd2b59f`.
An SSH 443 timeout occurred during evidence-push retry, but evidence
was later published successfully in branch `runtime-logs`. No server
rerun is required. Pinned V13 report Git blob:
`29309650f770b60dab2ec9aaedba3bcbbb652982`.

V13: 12 previously C5/V9-disjoint games, 36 metadata-selected windows,
52 preselected conventional stock Firecloud edges (9 games), 28
T−1 passenger candidates (16 distinct edge episodes, 9 windows,
4 games). All 28 reached the conditional Chunnel target in T owner-current
archives; 12 came from normal no-indexed-mine-risk routes and 16 from
risk-masked conditional no-hit routes. All 28 DIFFER from the corresponding
baseline normal no-Chunnel endpoint, meaning this comparison is
discriminative in observed T location.

Conventional actor at target + target unchanged + observed net 50KT
fuel delta found for 26/52 edges, not all passenger-bearing edges.
Among 16 edges with passengers, only seven had this full joint
signature; nine did NOT. In the official rules Chunnel opening costs
50KT, but **net** archival fuel change can be affected by other
operations (transfers, refuelling, losses), so net-50 is a
*supportive condition*, not a necessary archival signature.
There was one edge where the actor did not reach its original target;
potential multi-Chunnel sequencing should be investigated, but
one mismatched result does not prove chaining.

All 265 comparable T−1 regular-movement negative controls matched
their ordinary T endpoints; 2 lacked owner-current T record and
3 showed owner drift. These controls are sampled from the **first**
ten ID-ordered eligible ships per window and are not a random
population. Report their denominator and sampling restriction.

## V14 preregistered conditional validation

Metadata-only selection from public100 `source_members`: exclude
all 17 frozen C5 V6 games, 8 V9 games, and 12 V13 games,
then choose **20 further games × 3 adjacent windows** (60 total)
evenly over sorted numeric game IDs. NO VCR, post-T observations,
Chunnel success or mine hit enters game/window selection.

For all windows, first freeze exact T−1 owner-current roster,
historical static catalog, conservative conventional Firecloud gates,
ordinary-route model, mine risk, candidate passenger/actor/target
IDs and baseline positions via existing V13 functions.

Unlike the original V13 evaluation, explicitly compare:
- Conditional T−1 Chunnel passenger endpoint, assuming valid
  Chunnel activation and actual arrival at the source;
- independently frozen normal no-Chunnel T−1 endpoint.
A candidate is a T−1 ship whose ordinary movement model puts it at
the source (including *conditional no mine hit* cases). It is NOT
a claim that Host will activate the Chunnel or physically deliver
the passenger there.
If a ship has multiple eligible source edges in the same turn,
classify as ambiguous and exclude from unambiguous scoring.

Only AFTER **all** 60 windows freeze independently read the T
owner-current archive to compare the two conditional endpoints.
Separate classifications: Chunnel-only match, normal-baseline-only
match, neither, and explicit missing/owner/hull abstentions.
Report per-game and per T−1 mine-risk class and zero-exposure
denominators. Keep up to ten preselected V13 nonexposed
ordinary-route controls per completed window, no T outcomes
used in their selection.

This remains a same-public100 retrospective corpus partition, NOT
a newly collected independent test set. Matching T after Host is
not a proof of actual Chunnel execution; 50KT net difference is
not a required activation witness. No production executor, combat
queue or mine RNG changes allowed by the experiment.

## One command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-conditional-chunnel-holdout-v14-with-evidence.sh
```

Report: `artifacts/combat/c5-conditional-chunnel-holdout-v14/published/report.json`.
Evidence: `runtime-logs/combat-c5-conditional-chunnel-holdout-v14/`.

Next steps depend on prospective conditional-vs-baseline performance.
If inconsistent, inspect priority, multiple Firecloud edges per
source, mine-route stopping, Tow and movement-phase ordering.
If consistent across multiple games/episodes, implement a
**research-only** phase-aware movement predictor with explicit
uncertainty and compare against a newly frozen corpus generation
before considering canonical Host engine changes.
