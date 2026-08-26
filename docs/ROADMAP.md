# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-26-normal-mine-slowdown-exposure-pending.md`](handoff/2026-08-26-normal-mine-slowdown-exposure-pending.md).

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
- outbound submitted fuel transfer — rejected for the dominant family (`target_short_outbound_fuel_transfer=0`).
- standard Cloak fuel burn — rejected (`target_short_cloak_mission=0`).
- Privateer Rob Ship — rejected for the dominant family (`target_short_rob_exposure_candidate=0`).
- Stellar Cartography speed terrain — rejected as a broad explanation after refined active inventory.

Refined Stellar inventory reproduced `target_short_forward_rows=116` exactly and found:

```text
blackholes active_turns = 0
blackholes target_active_turns = 0
wormholes active_turns = 0
wormholes target_active_turns = 0
```

Active nebula/debris state appears on only seven target turns and is not documented as a generic normal-movement speed limiter.

## Active investigation — repair-hidden normal-mine slowdown exposure

Planets.nu documents a 10-ly movement slowdown per normal mine hit for hull tech below 7 when enough travel remains. Hull tech 7+ is not slowed. Strict mine/web v5 already labels attributable hits where damage evidence survives, so the current question is the complementary residual:

```text
normal mine hit
  -> low-tech hull loses 10 ly per hit
  -> route ends short
  -> later repair / historical snapshot semantics hide damage evidence
```

First-pass diagnostic:

```text
tools/diagnostics/normal_mine_slowdown_exposure_audit.py
```

This pass is deliberately only an upper-bound population test. It does not yet infer mine-hit RNG, historical diplomacy, hull tech or repair. It measures owner-different normal-mine route exposure and whether the movement deficit is approximately `10 * N` light-years.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check/run `normal_mine_slowdown_exposure_audit.py` without rebuild;
3. require `target_short_forward_rows = 116`;
4. inspect target route exposure by game/hull;
5. inspect `target_short_deficit_near_10n`;
6. if either exposure or 10*N geometry is sparse, reject the lead;
7. only if both are material, build a second pass with hull tech <7, historical diplomacy and damage/repair evidence;
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
