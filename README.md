# planets-lab

Deterministic Planets.nu simulation, reverse-engineering and AI research environment.

GitHub `main` is the source of truth. Always query actual HEAD before continuing.
Raw historical archives, prepared caches and compiled datasets remain local/gitignored.

## Current checkpoints

- Movement: ordinary geometry, warp wells, route-equivalent Tow/Chunnel, scoped
  storms/sphere behavior, strict mine interruption, damage-limited warp and
  waypoint-distance fuel proration have explicit evidence-scoped closures.
- The old `511506/T23/ship160` mine investigation is closed as one normal-mine
  hit plus automatic supply repair. Do not resume its obsolete pending handoff.
- Classic pairwise combat, ordinary ship-chain carry and attributable
  planet/starbase-chain checkpoints are recorded in the roadmap. Full Host
  engagement ordering remains a major workstream.
- The continuous nominal-leg partial-fuel rule is now historical-corpus
  `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for ordinary Move Most and
  Intercept. The effective one-turn leg is charged before integer endpoint
  rasterization. Finite-fuel Tow remains separate and OPEN; do not inherit
  this evidence into Tow automatically.
- No `planets-intel` production transfer is implied by the lab promotion.

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

These are the recorded compiled-layer checkpoint; the later bounded
partial-fuel historical gate read the existing corpus without rebuilding L1/L2.
Generic residuals: 740 rows / 12 games / 75 hulls; largest coarse family: 113.
See `docs/COMPILED_CORPUS.md` for schemas, scope and evidence boundaries.

## Start here

1. [Verified partial-fuel historical gate](docs/handoff/2026-09-09-partial-fuel-historical-gate-verified.md)
2. [Detailed finite-fuel evidence](docs/handoff/2026-09-08-intel-fuel-chat-handoff.md)
3. [Roadmap](docs/ROADMAP.md)
4. [Compiled corpus](docs/COMPILED_CORPUS.md)
5. [Architecture](docs/ARCHITECTURE.md)
6. [Workflow](docs/WORKFLOW.md)

To reproduce the bounded historical gate on a clean server checkout with the
existing local archives/caches:

```bash
bash tools/run-partial-fuel-historical-gate.sh
```

The runner collects evidence and logs without rebuilding corpus layers or
changing production inference. Finite-fuel Tow still requires a separate
attributable empirical pass.
