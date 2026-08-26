# planets-lab

Deterministic Planets.nu simulation, reverse-engineering and AI research environment.

## Goals

- represent game state in one canonical schema;
- implement a deterministic, testable Host simulator;
- build rule/specification and differential-validation tooling;
- import historical Planets.nu game data into privacy-safe derived datasets;
- expose player-limited observations for AI agents;
- support scripted bots, self-play and ML/RL experiments.

## Current state

The active workstream is historical NuHost corpus mining and movement compatibility validation across 12 recent finished games.

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

Verified recent closures include route-equivalent Tow and Chunnel handling, classic/cloudy ion storms, scoped sphere geometry, strict mine/web hit context, strict damage-limited warp and strict Nu waypoint-distance fuel proration.

Current generic endpoint:

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest surviving coarse families:

```text
116  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 43  warp7-9 0.5-1.0x observed=other same_line_forward
```

Crystal Web Drain is closed as one fully attributable `DOCUMENTED + CORPUS_OBSERVED` evidence-only transition (`game 360690`, turn 44, hull 53). Ownership, historical diplomacy/game era, 25 KT fuel/mass reduction and exact Nu-prorated endpoint are all attributable, but one game/hull is insufficient for a production label.

Three subsequent pre-movement fuel leads are rejected for the dominant 116-row family:

```text
outbound submitted fuel transfer:
  target_short_outbound_fuel_transfer = 0

standard Cloak fuel burn:
  target_short_cloak_mission = 0

Privateer Rob Ship:
  target_short_rob_exposure_candidate = 0
```

The sole global Rob exposure is outside the dominant family, so no exact Rob simulator pass is justified for the current target.

The active task is now a **refined Stellar Cartography active-feature inventory**:

```text
tools/diagnostics/stellar_cartography_raw_feature_inventory.py
```

The first inventory run is not valid for target attribution: it measured 126 short-forward rows instead of the authoritative 116 because its local ratio bucket omitted the clustering audit's `~0.5x` tolerance. It also counted path existence rather than active feature presence, so values such as `blackholes: []` and `settings.blackholes = 0` were incorrectly counted as Black Hole occurrences.

The corrected diagnostic must reproduce:

```text
target_short_forward_rows = 116
```

and separates `present_turns` from active/non-empty/non-zero `active_turns` / `active_values`, including target-turn equivalents. Only an active movement-relevant terrain feature on target-family turns can justify a geometry/timing follow-up. Schema presence alone is not mechanics evidence.

Current schemas:

```text
L1 physical movement:       planets-lab.compiled-movement.v3
L1 context semantics:       planets-lab.compiled-movement-storm-context.v3
L2 context labels:          planets-lab.compiled-movement-context-labels.v6
```

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/handoff/2026-08-26-stellar-cartography-active-inventory-pending.md`](docs/handoff/2026-08-26-stellar-cartography-active-inventory-pending.md)
- [`docs/COMPILED_CORPUS.md`](docs/COMPILED_CORPUS.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

GitHub `main` is the source of truth. Raw historical archives, prepared caches and compiled datasets remain local/gitignored; Git contains privacy-safe manifests, code, schemas and reproducible summaries.
