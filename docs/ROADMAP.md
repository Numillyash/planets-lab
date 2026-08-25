# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md). The latest movement/corpus handoff is [`handoff/2026-08-26-stellar-cartography-feature-inventory-pending.md`](handoff/2026-08-26-stellar-cartography-feature-inventory-pending.md).

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

Current runtime-verified movement accounting:

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
manifest:                  planets-lab.corpus-game.v2
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

Largest coarse families:

```text
116  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 43  warp7-9 0.5-1.0x observed=other same_line_forward
```

## Closed evidence-only lead — Crystal Web Drain

One transition (`game 360690`, turn 44, hull 53) is attributable end-to-end to Crystal Web Drain feeding Nu fuel proration. Historical ownership, game era, exact relation pair and lack of diplomacy immunity were all resolved. Status: **DOCUMENTED + CORPUS_OBSERVED strong evidence; evidence-only** because support remains one independent game/hull.

## Rejected post-v6 leads

### Outbound fuel transfer

```text
target_short_outbound_fuel_transfer = 0
target_short_transfer_causal_exact = 0
```

### Standard Cloak fuel burn

```text
target_short_cloak_mission = 0
target_short_standard_cloak_fuel_burn_candidate = 0
target_short_cloak_causal_exact = 0
```

### Privateer Rob Ship

Exposure audit:

```text
rob_exposure_candidate = 1
rob_exposure_positive_victim_fuel = 1

target_short_privateer_mission9_at_origin = 1
target_short_rob_exposure_candidate = 0
target_short_rob_exposure_positive_victim_fuel = 0
```

The sole global exposure is outside the 116-row family. No exact Rob simulator pass is justified for the current target.

## Active investigation — Stellar Cartography raw feature inventory

Before implementing any terrain-specific movement model, inventory which relevant raw feature families actually occur in the 12-game evidence archives.

Planets.nu documentation indicates:

- nebulae primarily alter visibility / abilities;
- star clusters primarily cause destruction/radiation;
- debris disks can destroy ships and disrupt towing;
- wormholes require the explicit Enter Wormhole mission;
- Black Hole ergospheres directly inhibit warp speed.

Active diagnostic:

```text
tools/diagnostics/stellar_cartography_raw_feature_inventory.py
```

It reports feature-related raw payload paths and safe scalar excerpts from one deterministic perspective per archive turn, plus whether each path occurs on turns containing the dominant 116-row family.

### Immediate work

1. pull current `main` and confirm clean tree;
2. syntax-check/run `stellar_cartography_raw_feature_inventory.py` without rebuild;
3. require `target_short_forward_rows = 116`;
4. inspect `GLOBAL FEATURE PATHS` first;
5. determine whether black-hole/ergosphere payloads exist at all;
6. inspect target-turn occurrences for any movement-relevant terrain path;
7. build no geometry classifier unless exact raw schema and a documented movement effect are both present;
8. keep production accounting fixed at `2220`.

## Deprioritized / closed leads

- old affordable-whole-LY fuel frontier is correlation evidence only;
- outbound transfer, standard Cloak and Rob Ship are negative for the dominant family;
- Crystal Web Drain remains one attributable evidence-only row;
- multi-waypoint queue did not explain the old hull-79 cluster;
- hidden/private-FC Chunnel discovery added no coverage;
- owner-visible Intercept is already excluded from Move Most residuals;
- repair-bracket mine and damage rows remain evidence-only;
- do not generalize game `591478`'s 2170 period;
- do not reopen Red Mite without new evidence.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented.
- **M2 economy/planetary Host:** in progress, not current priority.
- **M3 warfare:** partial.
- **M4 race mechanics:** partial.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active through movement differentials.
- **M6 training/AI:** future.
