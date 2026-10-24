# planets-lab

Deterministic Planets.nu simulation, reverse-engineering and AI research environment.

GitHub `main` is the source of truth. Always query actual HEAD before continuing.
Raw historical archives, prepared caches and compiled datasets remain local/gitignored.

## Resuming work in a new chat — mandatory per-PR handoff

**Start here:** [Copy-ready next-chat prompt](docs/CONTINUE_HERE.md).
The current prompt lives in Git and is revised in **every pull request**
alongside [PR change history](docs/PR_CHANGELOG.md) and relevant project
documentation. You do **not** need to forward prior chats or invent a
new handoff each time; paste the canonical prompt or ask the new
ChatGPT session to read it directly from GitHub.

For agents and contributors, [AGENTS.md](AGENTS.md),
[docs/WORKFLOW.md](docs/WORKFLOW.md) and the
[PR checklist](.github/PULL_REQUEST_TEMPLATE.md) define the mandatory
contract. CI rejects PRs without a fresh continuation file, a numbered
PR changelog entry and a separate meaningful documentation change.

The current standard Host research includes conditional multi-starbase
Classic queue, saved ordinary build pointer and single uncontested
priority PBP assembly (#259–261). These are local TESTED models,
**not** independently validated NuHost execution/phase order.
Review the roadmap and continuation prompt for current scope.

**Project-wide visual status:** [Progress map and evidence-qualified roadmap](docs/PROJECT_PROGRESS_MAP.md) — M0–M6, movement, combat, economy, queues, minefields, corpus, Host blockers and external PlanetDashboard (not audited here).

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
- **Research focus as of 2026-10-14:** Horwasp-specific mass/clan/terminal
  phase analysis is **paused, not solved**. Preserve its frozen evidence and
  explicit abstentions; do not spend the next iteration on Horwasp residual
  fitting. Continue broad ordinary non-Horwasp C5 combat queue/capture and
  independent next-VCR integration; see
  [Horwasp pause and C5 restart](docs/handoff/2026-10-14-horwasp-park-c5-restart.md).
- No `planets-intel` production transfer is implied by a lab evidence promotion;
  production use must preserve the same evidence and scope boundaries.
- Corpus Game / Host Feature Index v1 is implemented as normalized typed Parquet +\n  DuckDB selection infrastructure. The settings-strict `ordinary-classic` profile\n  currently selects games `360690`, `511506`, and `620694`; index membership is\n  not a mechanics evidence promotion.\n
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
6. [Corpus feature index v1](docs/handoff/2026-09-21-corpus-feature-index-v1.md)\n7. [Workflow](docs/WORKFLOW.md)

To reproduce the bounded ordinary partial-fuel historical gate on a clean server
checkout with the existing local archives/caches:

```bash
bash tools/run-partial-fuel-historical-gate.sh
```

The finite-fuel Tow evidence chain is preserved in tracked `tools/run-*.sh`
runners and the 2026-09-11 handoffs. Broad movement residual hunting remains
closed unless a bounded contradiction or interaction requires reopening it.


### Predictive Host combat queue gate

The evidence-backed C5 order/selection/mutable-queue primitives have been
reintegrated over current `main`. A selector-backed held-out next-VCR gate is
tracked in `tools/run-combat-predictive-queue-gate.sh`. It runs the shared
`combat-planar-no-horwasp` FeatureScope acceptance first, then validates
multi-step ordinary STANDARD queue prediction. Fresh archive-host acceptance is
still required before recording a new runtime checkpoint.


The selector-backed predictive ordinary ship queue now has fresh archive-host
runtime acceptance on the 11-game `combat-planar-no-horwasp` population:
22/22 held-out next-VCR transitions exact in both strict and conditional
profiles, with zero mismatch. The only exact-set continuation exclusion is
capture, which is the next active combat gate.


## Archive-host runtime evidence

For long local corpus runs, prefer the tracked evidence wrapper so raw logs and
JSON artifacts are pushed to the dedicated orphan `runtime-logs` branch rather
than pasted into chat.

Current capture command:

```bash
bash tools/run-combat-capture-reintegration-with-evidence.sh
```

Source code and accepted handoffs remain on `main`; machine-generated evidence
lives only on `runtime-logs`.
