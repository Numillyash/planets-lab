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
post_external_residual              3938
post_chunnel_residual               2517
post_horwasp_strong_residual        2277
mine_strong_explained                 37
post_mine_strong_residual           2240
```

Recently closed/integrated movement work includes warp-well ordering, scoped Red Mite fallback evidence, Horwasp ballistic topology, classic-vs-cloudy ion-storm handling, evidence-scoped sphere-aware ordinary movement for game `591478`, route-equivalent Chunnel multi-event handling, and strict mine/web interruption context.

Mine/web context v5 is **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**. An independent rounding differential predicted exactly 37 strict field-backed rows (`18` web + `19` normal); the normal v5 build closed exactly those 37 rows and changed the final residual `2277 -> 2240` while all Chunnel/Horwasp accounting remained unchanged. Historical NuHost evidence strongly selects positive nearest-integer mine damage rather than the documentation's literal round-up wording; this is tracked as an explicit compatibility distinction.

The v5 build verified cache semantics (`0/12` compiled-label hits, `12/12` prepared-cache hits). After correcting a stale Chunnel shared-schema sentinel, both the targeted v5 regression set and the full pytest suite are green on a clean tree.

The post-v5 generic rebaseline is now complete on `movement_post_mine_strong_residual`: `2240` final rows, `783` generic non-Horwasp rows, `79` generic hulls and all `12` games. The next focused lead is target-at-origin external movement. `tools/diagnostics/target_origin_tow_residual_audit.py` tests whether the current fail-closed tow layer is leaving route-equivalent multiple visible tow matches unresolved, while keeping hidden/unresolved co-movement as evidence-only.

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-24-target-origin-tow-followup.md`](docs/handoff/2026-08-24-target-origin-tow-followup.md) — latest movement/corpus handoff;
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
