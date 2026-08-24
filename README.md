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

Route-equivalent visible Tow is now **TESTED + DIFF_VERIFIED**. A global pre-build differential over all `3938` old external residual rows found exactly four multiple-Tow matches and zero missed single-Tow matches. All four were old final-residual rows. The normal L1 v3 build reproduced the exact predicted `+4/-4` external-context delta, the normal L2 v5 build invalidated from the changed L1 source schema/hash, and every downstream count matched the prediction exactly. A post-fix global audit found zero remaining visible Tow matches in the residual.

Mine/web context v5 remains **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED** with `18` strict web + `19` strict normal-mine rows. Chunnel route-equivalent handling remains **TESTED + DIFF_VERIFIED**. Closed mechanics are not reopened without fresh evidence.

Both the targeted Tow/compiled/cache regression set and the full pytest suite are green. L1 v2 -> v3 cache migration produced `0/12` compiled hits and `12/12` prepared-cache hits; the following L2 v5 rebuild likewise produced `0/12` compiled-label hits and `12/12` prepared-cache hits.

The previous post-v5 generic rebaseline (`2240` final / `783` generic / `79` generic hulls) is now historical. The immediate next step is to rerun broad generic clustering on the new `2236` final endpoint before selecting another mechanic family.

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-24-route-equivalent-tow-verified.md`](docs/handoff/2026-08-24-route-equivalent-tow-verified.md) — latest movement/corpus handoff;
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
