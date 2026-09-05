# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-09-05-normal-mine-slowdown-candidate-gate-pending.md`](handoff/2026-09-05-normal-mine-slowdown-candidate-gate-pending.md).

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

## Evidence-only / rejected leads

- Crystal Web Drain — one end-to-end attributable evidence case; no production label because support remains one game/hull.
- outbound submitted fuel transfer — rejected for the dominant family.
- standard Cloak fuel burn — rejected.
- Privateer Rob Ship — rejected for the dominant family.
- Stellar Cartography speed terrain — rejected as a broad explanation; refined inventory found no active Black Hole or wormhole state in the 12-game corpus.

## Active investigation — normal-mine slowdown candidate gate

The exposure pass found:

```text
target_short_rows = 116
target_short_normal_mine_route_exposure = 10
target_short_normal_mine_multi_field_route_exposure = 2
target_short_positive_planned_distance_deficit = 10
target_short_deficit_near_10n = 2
```

Only two target rows survive the upper-bound route + geometry filter:

```text
game 360690 / turn 155 / ship 447 / hull 23 / deficit 30.575 / implied 3 hits
game 511506 / turn 23  / ship 160 / hull 17 / deficit 21.094 / implied 2 hits
```

Planets.nu documents that normal-mine hits slow only hull tech below 7; tech 7+ is not slowed. Therefore the next hard gate is static hull tech before any diplomacy/FC/RNG/repair reconstruction.

Active diagnostic:

```text
tools/diagnostics/normal_mine_slowdown_candidate_gate_audit.py
```

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check/run `normal_mine_slowdown_candidate_gate_audit.py` without rebuild;
3. inspect `hull_tech`, `hull_mass`, and `slowdown_tech_eligible` for both candidates;
4. inspect the corpus-observed normal-mine damage quantum and before/after damage/supplies context;
5. reject every candidate with hull tech >=7 immediately;
6. only tech<7 survivors advance to historical Safe Passage / minefield friendly-code compatibility, exact field intersection, RNG multiplicity and repair reconstruction;
7. do not promote a label from one or two candidates without independent attributable support;
8. keep production accounting fixed at `2220`.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented.
- **M2 economy/planetary Host:** in progress, not current priority.
- **M3 warfare:** partial.
- **M4 race mechanics:** partial.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active through movement differentials.
- **M6 training/AI:** future.
