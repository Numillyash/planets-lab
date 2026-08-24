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
external_context_explained         13960
post_external_residual              3934
chunnel_explained                   1421
post_chunnel_residual               2513
horwasp_strong_explained             240
post_horwasp_strong_residual        2273
mine_strong_explained                 37
post_mine_strong_residual           2236
label_issues                           0
```

Recently closed/integrated movement work includes warp-well ordering, scoped Red Mite fallback evidence, Horwasp ballistic topology, classic-vs-cloudy ion-storm handling, evidence-scoped sphere-aware ordinary movement for game `591478`, route-equivalent Chunnel multi-event handling, strict mine/web interruption context, and route-equivalent visible Tow handling in the L1 external-context layer.

Route-equivalent visible Tow is **TESTED + DIFF_VERIFIED**. Its global pre-build differential found exactly four false residuals and zero missed single-Tow matches; the L1 v3/L2 v5 rebuild reproduced the exact predicted delta and the post-fix Tow controls are all zero.

Mine/web context v5 remains **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED** with `18` strict web + `19` strict normal-mine rows. Chunnel route-equivalent handling remains **TESTED + DIFF_VERIFIED**. Closed mechanics are not reopened without fresh evidence.

The post-v3 generic residual rebaseline is now verified on the `2236` final endpoint:

```text
final_residual_rows       2236
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               779
generic_games               12
generic_hulls               78
```

The Tow fix removed only four Warp-0 target-at-origin rows (`97 -> 93`). The dominant short-forward family is unchanged at `121` rows across `26` hulls and `7` games. The active focused hypothesis is now documented **damage-limited maximum warp**. `tools/diagnostics/damage_limited_warp_residual_audit.py` tests raw-damage exact Host-major/minor destinations, a conservative current-supplies repair bracket, Lizard race handling, Gravitonic distance and negative controls before any production change.

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-25-damage-limited-warp-followup.md`](docs/handoff/2026-08-25-damage-limited-warp-followup.md) — latest movement/corpus handoff;
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
