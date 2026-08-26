# planets-lab

Deterministic Planets.nu simulation, reverse-engineering and AI research environment.

## Current movement/corpus state

The active workstream is historical NuHost movement compatibility mining across 12 finished games.

Runtime-verified accounting:

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

Current generic endpoint:

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest surviving coarse family:

```text
116  warp7-9 <0.5x observed=other same_line_forward
```

Verified recent production closures include route-equivalent Tow/Chunnel, classic/cloudy ion storms, scoped sphere geometry, strict mine/web hit context, strict damage-limited warp, and strict Nu waypoint-distance fuel proration v6.

Crystal Web Drain is retained as one fully attributable `DOCUMENTED + CORPUS_OBSERVED` evidence-only transition. Outbound submitted fuel transfer, standard Cloak fuel burn, Privateer Rob Ship and Stellar Cartography speed terrain are rejected as broad explanations for the dominant 116-row family.

The refined Stellar Cartography inventory reproduced the exact 116-row population and found no active Black Hole or wormhole state anywhere in the current 12-game corpus. Active nebula/debris state occurs on only seven target turns and is not a documented generic normal-movement speed limiter.

The active diagnostic is now:

```text
tools/diagnostics/normal_mine_slowdown_exposure_audit.py
```

It tests the complementary possibility left outside strict mine/web v5: normal-mine hits on hull tech below 7 can slow a ship by 10 ly per hit, while later repair/historical snapshot semantics may hide the damage evidence. The first pass is exposure-only and checks route intersection plus movement deficits near `10 * N` ly before any hull-tech/diplomacy/repair reconstruction.

Current schemas:

```text
L1 physical movement:       planets-lab.compiled-movement.v3
L1 context semantics:       planets-lab.compiled-movement-storm-context.v3
L2 context labels:          planets-lab.compiled-movement-context-labels.v6
```

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/handoff/2026-08-26-normal-mine-slowdown-exposure-pending.md`](docs/handoff/2026-08-26-normal-mine-slowdown-exposure-pending.md)
- [`docs/COMPILED_CORPUS.md`](docs/COMPILED_CORPUS.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

GitHub `main` is the source of truth. Raw historical archives, prepared caches and compiled datasets remain local/gitignored; Git contains privacy-safe manifests, code, schemas and reproducible summaries.
