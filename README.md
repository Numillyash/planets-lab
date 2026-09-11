# planets-lab

Deterministic Planets.nu simulation, reverse-engineering and AI research environment.

GitHub `main` is the source of truth. Always query actual HEAD before continuing.
Raw historical archives, prepared caches and compiled datasets remain local/gitignored.

## Current checkpoints

- Movement: ordinary geometry, warp wells, route-equivalent Tow/Chunnel, scoped
  storms/sphere behavior, strict mine interruption, damage-limited warp and
  waypoint-distance fuel proration have explicit evidence-scoped closures.
- The continuous nominal-leg partial-fuel rule is historical-corpus
  `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for ordinary Move Most and
  Intercept. The effective one-turn leg is charged before integer endpoint
  rasterization.
- Base finite-fuel Tow movement is now
  `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`: the cleaned
  `360690/T41` discriminator selects **post-Alchemy combined tower+towed mass**
  and proportional insufficient-fuel movement, rejecting both pre-Alchemy
  combined mass and tower-only mass. Tow contests/chains/cycles and external
  interaction ordering remain separately scoped/fail-closed.
- The old `511506/T23/ship160` mine investigation is closed as one normal-mine
  hit plus automatic supply repair. Do not resume its obsolete pending handoff.
- Classic pairwise combat, ordinary ship-chain carry and attributable
  planet/starbase-chain checkpoints are recorded in the roadmap. Full Host
  engagement ordering remains the immediate major workstream.
- No `planets-intel` production transfer is implied by a lab evidence promotion;
  production use must preserve the same evidence and scope boundaries.

## Recorded compiled-layer runtime counts

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
mine_strong_explained                 60
post_mine_strong_residual           2203
fuel_proration_explained               6
post_fuel_proration_residual        2197
label_issues                           0
```

These are the recorded compiled-layer checkpoint; later bounded historical gates
read the existing corpus without rebuilding L1/L2. Generic residuals: 740 rows /
12 games / 75 hulls; largest coarse family: 113. See
`docs/COMPILED_CORPUS.md` for schemas, scope and evidence boundaries.

## Start here

1. [Finite-fuel Tow documented reconciliation](docs/handoff/2026-09-11-finite-fuel-tow-documented-reconciliation-runtime.md)
2. [Verified partial-fuel historical gate](docs/handoff/2026-09-09-partial-fuel-historical-gate-verified.md)
3. [Roadmap](docs/ROADMAP.md)
4. [Compiled corpus](docs/COMPILED_CORPUS.md)
5. [Architecture](docs/ARCHITECTURE.md)
6. [Workflow](docs/WORKFLOW.md)

To reproduce the bounded ordinary partial-fuel historical gate on a clean server
checkout with the existing local archives/caches:

```bash
bash tools/run-partial-fuel-historical-gate.sh
```

The finite-fuel Tow evidence chain is preserved in tracked `tools/run-*.sh`
runners and the 2026-09-11 handoffs. Broad movement residual hunting remains
closed unless a bounded contradiction or interaction requires reopening it.
