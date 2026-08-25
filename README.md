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

Last runtime-verified movement accounting remains:

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
label_issues                           0
```

Recently closed/integrated movement work includes warp-well ordering, scoped Red Mite fallback evidence, Horwasp ballistic topology, classic-vs-cloudy ion-storm handling, evidence-scoped sphere-aware ordinary movement for game `591478`, route-equivalent Chunnel multi-event handling, strict mine/web interruption context, route-equivalent visible Tow handling, and strict damage-limited maximum warp.

Verified status:

- route-equivalent visible Tow — **TESTED + DIFF_VERIFIED**;
- strict mine/web v5 — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- route-equivalent Chunnel — **TESTED + DIFF_VERIFIED**;
- strict damage-limited maximum warp — **DOCUMENTED (legacy Nu help page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

The last verified generic endpoint is:

```text
final_residual_rows       2226
generic_rows               769
generic_games               12
generic_hulls               76
```

The dominant short-forward family is `119` Warp 7-9 `<0.5x` same-line-forward rows.

### Fuel-proration v6 — implemented, runtime pending

Planets.nu documents insufficient-fuel movement as waypoint-distance proration. The current endpoint differential found:

```text
raw-mass insufficient candidates   19
Nu waypoint-proration exact         6
affordable-frontier exact           3
VGAP3-style exact                    0
Nu-only exact                        3
```

The six exact Nu rows span four hulls and three games; three lie inside the dominant 119-row family. A global stage audit then found all six only in `post_mine_strong_residual`, with zero overlap against Chunnel, Horwasp strong or strict mine/web labels.

Historical next-turn owner snapshots are not treated as immediate post-Host frames for editable `warp`, waypoint or fuel fields. Planets.nu Time Machine reproduces saved end-of-turn orders, so exact Host `x/y` outcome is the causal observation used for promotion.

The strict production-compatible subset is now implemented as the **last L2 context stage after mine/web**, not as an early L1 pass. This preserves all already verified L1 and L2 intermediate layers.

New category/view:

```text
fuel_proration_waypoint_match
movement_post_fuel_proration_residual
```

Source schema is now:

```text
L1 physical movement:       planets-lab.compiled-movement.v3
L1 context semantics:       planets-lab.compiled-movement-storm-context.v3
L2 context labels source:   planets-lab.compiled-movement-context-labels.v6
```

Generated local data has not yet been rebuilt to v6, so `2226` remains the authoritative runtime endpoint until verification completes. Independent expected v6 differential:

```text
post_mine_strong_residual        2226   unchanged
fuel_proration_explained            6
post_fuel_proration_residual      2220
label_issues                         0

generic_rows                      769 -> 763
dominant short-forward            119 -> 116
```

Because only the L2 label schema changed, no L1 rebuild is required. A normal v6 label build should invalidate all 12 v5 label partitions by schema while reusing the prepared cache.

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-25-fuel-proration-v6-runtime-verification.md`](docs/handoff/2026-08-25-fuel-proration-v6-runtime-verification.md) — latest movement/corpus handoff;
- [`docs/COMPILED_CORPUS.md`](docs/COMPILED_CORPUS.md) — compiled corpus schemas, cache semantics and current invariants;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — architecture and evidence boundaries.

GitHub `main` is the source of truth. Do not reconstruct current project state from old chat history when these documents are available.

## Layout

```text
src/planets_lab/
  core/         canonical game state and shared domain types
  sim/          deterministic Host engine
  rules/        mechanics/ruleset definitions
  observer/     player observations / fog of war
  data/         static specs/importers/datasets
  corpus/       historical acquisition, reconstruction and differential layers
  ai/           agent/environment interfaces

tests/          unit, regression and scenario tests
docs/           architecture, roadmap, rule notes and handoffs
tools/          diagnostics and reproducible audit scripts
validation/     manifests, golden evidence and local compiled corpus tree
```

## Development setup

Docker is the recommended environment.

Run the full test suite:

```bash
docker compose run --rm -T lab pytest -q
```

Open a shell:

```bash
docker compose run --rm lab bash
```

For local development without Docker, Python 3.11+ is supported:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest
```

Raw historical archives, prepared caches and compiled datasets remain local/gitignored. Git contains privacy-safe manifests, code, schemas, compact evidence and reproducible summaries rather than private raw game data.
