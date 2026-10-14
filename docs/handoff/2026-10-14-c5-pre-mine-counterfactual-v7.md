# C5 pre-mine normal route conditional replay V7 (research only)

Repository: `Numillyash/planets-lab`, branch `main`. Separate
`research/external-engine-analysis` remains untouched. No production
`planets-intel`, no canonical combat executor, no database CURRENT writes.

## Source confirmation

V6 successful runtime in GitHub:
`runtime-logs/combat-c5-tminus1-site-ingress-residence-v6/20261014T125645Z_f7a25b043997`,
`exit_code=0`, source main `f7a25b043997aa155d06f5188f619fc6da52c6b2`.

Frozen source report Git blob:
`51d21132e4db89511be59805ebe2be14014b3e7a`.

V6: 27 sites, 63 adjacent transitions, 56 evaluated, 7 unavailable;
25 NO_PAIR statuses: 13 have waypoint-only uncertainty, 3 are
T−1 site residence/departure, 1 is earlier-VCR carry uncertainty,
8 have no indexed witnesses. The NO_PAIR waypoint-only subset has
**18 unique site-ship witnesses**, but **12 normal_mine_route_risk
witnesses all belong to one site** in G421276/T115. The other six
are Tow (5) or Sphere (1). Do NOT claim 12 independent games/episodes.

## New V7 causal question

Under **conditional absence of mine interference**, would the existing
normal-movement planner place a waypoint-only witness at the frozen
combat site? This is not the ship's factual Host position, and not a
prediction of whether an unknown random mine hit happened.

`_visit_targeted_site_contexts` in
`combat_public_capture_o_layer_probe.py` gains a default-OFF diagnostic
flag `collect_pre_mine_counterfactual`. With the flag ON, it records
the planner's normal destination **before** the foreign-mine risk
sets the original predicted position to None. With flag OFF its
outputs/queue logic are unchanged. The original mine risk remains
fully active when flag ON as well.

The V7 evaluator selects exactly 12 frozen candidates by pinned V6
ship/site/owner/source, then compares the T−1 no-mine hypothetical
endpoint with the already-fixed current-N site. It verifies the source
is still `normal_mine_route_risk`, position still unresolved, archived
start differs from site, archived waypoint equals site and original
owner/ship IDs match. Missing prediction abstains; discrepancies fail
closed. Neither future N+1 opponent nor current combat outcome enters
the evaluator.

Also report two **model-internal controls** from independent T−1
known ordinary movement: destinations at the site and destinations
elsewhere. These are NOT independently confirmed Host position
truth labels. No queue or battle predictions are created. All data
are from the already-open site; there is no new held-out game
validation. Do not promote results even if all 12 hypothetical
routes land at the site.

## Run command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-pre-mine-route-counterfactual-v7-with-evidence.sh
```

Output:
`artifacts/combat/c5-pre-mine-route-counterfactual-v7/published/report.json`.

Evidence:
`runtime-logs/combat-c5-pre-mine-route-counterfactual-v7/`.

## Next causal milestone

Recover independent minefield/movement phase events or host post-turn
ship positions to test no-hit versus stopped/damaged outcomes across
different games, with preregistered mine exposure, no-mine controls,
and route geometry. Do not import post-turn coordinates into
pre-movement features. Only after a successful held-out causal gate
may site arrival membership or selection be reconsidered.
