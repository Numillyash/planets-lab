# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md`](handoff/2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean attributable NuHost transitions.

Unknown mechanics fail closed. Raw facts and evidence-scoped effective interpretations remain separate.

## Current focus

Active milestone: **M5 — historical NuHost corpus + compatibility mining**.

Runtime-verified movement accounting remains:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13970
post_external_residual              3924
chunnel_explained                   1421
post_chunnel_residual               2503
horwasp_strong_explained             240
post_horwasp_strong_residual        2263
mine_strong_explained                 37
post_mine_strong_residual           2226
fuel_proration_explained               6
post_fuel_proration_residual        2220
label_issues                           0
```

Current schemas:

```text
prepared cache:            planets-lab.prepared-game-cache.v1
L1 movement:               planets-lab.compiled-movement.v3
L1 context semantics:      planets-lab.compiled-movement-storm-context.v3
L2 context labels:         planets-lab.compiled-movement-context-labels.v6
```

## Verified movement closures

- ordinary movement / Host major-minor geometry;
- warp-well ordering — `TESTED + DIFF_VERIFIED`;
- route-equivalent owner-visible Tow — `TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multiplicity — `TESTED + DIFF_VERIFIED`;
- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict mine/web interruption v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict damage-limited maximum warp — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict Nu waypoint-distance fuel proration v6 — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- Red Mite tracking/fallback — research closed absent new evidence.

## Current generic residual landscape

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest coarse family:

```text
116  warp7-9 <0.5x observed=other same_line_forward
```

## Evidence-only / rejected broad leads

- Crystal Web Drain — one end-to-end attributable evidence case; no production label because support remains one game/hull.
- outbound submitted fuel transfer — rejected for the dominant family.
- standard Cloak fuel burn — rejected.
- Privateer Rob Ship — rejected for the dominant family.
- Stellar Cartography speed terrain — rejected as a broad explanation; refined inventory found no active Black Hole or wormhole state in the 12-game corpus.

## Active investigation — sole tech<7 normal-mine survivor

Normal-mine route exposure reduced the 116-row family to 10 route-exposed rows and only two `10*N` geometry candidates. The hull-tech gate then rejected one:

```text
game 360690 / turn 155 / hull 23 -> tech 10 -> documented slowdown impossible
game 511506 / turn 23  / hull 17 -> tech 6  -> survives
```

The surviving hull 17 candidate has a corpus-observed normal-mine damage quantum of 76 and this before/after context:

```text
before damage/supplies = 0 / 53
after damage/supplies  = 66 / 3 (supplies observational)
planned distance       = 43.566 ly
observed distance      = 22.472 ly
deficit                = 21.094 ly
```

One hit plus automatic post-movement supply repair predicts `76 -> 66` damage and `53 -> 3` supplies exactly. Two damage hits do not match that repair trace. Therefore the working hypothesis is no longer "two 10-ly hits"; it is a possible **one hostile normal-mine hit plus an additional/compound movement consequence**.

Active diagnostic:

```text
tools/diagnostics/normal_mine_single_candidate_immunity_repair_audit.py
```

It checks only `game 511506 / turn 23 / ship 160`:

1. exact post-decay normal minefields intersecting the planned route;
2. route intervals through each field;
3. field owners and turn-specific relation pairs;
4. Safe Passage from field owner to target;
5. team identity;
6. any archived minefield Friendly Code values and exact ship/field FC match;
7. one-hit vs two-hit supply-repair predictions.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check/run `normal_mine_single_candidate_immunity_repair_audit.py` without rebuild;
3. inspect `INTERSECTED FIELD ELIGIBILITY` and identify explicitly hostile vs immune vs unresolved fields;
4. inspect `REPAIR TRACE` and confirm whether one-hit prediction matches observed damage;
5. if every intersected field is immune, reject mine attribution;
6. if at least one field is explicitly hostile and one-hit repair trace is exact, retain a one-hit evidence case and investigate the remaining ~11 ly movement discrepancy;
7. if field FC is unavailable, fail closed rather than infer hostility;
8. do not promote a production label from this single transition;
9. keep production accounting fixed at `2220`.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented.
- **M2 economy/planetary Host:** in progress, not current priority.
- **M3 warfare:** partial.
- **M4 race mechanics:** partial.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active through movement differentials.
- **M6 training/AI:** future.
