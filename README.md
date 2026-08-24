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

Last runtime-verified movement accounting:

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

Route-equivalent visible Tow is **TESTED + DIFF_VERIFIED**. Mine/web v5 remains **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED** with `18` strict web + `19` strict normal-mine rows. Chunnel route-equivalent handling remains **TESTED + DIFF_VERIFIED**. Closed mechanics are not reopened without fresh evidence.

The verified post-v3 generic endpoint is:

```text
final_residual_rows       2236
generic_rows               779
generic_games               12
generic_hulls               78
```

The dominant cross-hull/cross-game residual remains `121` Warp 7-9 short same-line-forward rows.

The current production change is a narrow **damage-limited maximum-warp** L1 context pass. Independent runtime evidence found `10` exact raw-damage-limited Host-major/minor endpoints across `9` games, `8` hulls and `6` races, with both undamaged and not-damage-limited exact controls equal to zero. All `10` exact rows have `<5 KT` visible onboard supplies. Only `2` of the `121` dominant short-forward rows are explained, so damage-limited warp is a real sparse generic mechanic rather than the main cause of that family.

Production category:

```text
damage_limited_warp_match
```

The pass runs only on still-unresolved L1 rows after authoritative storm mode and scoped sphere geometry. Repair-bracket-only cases are not promoted. Physical L1 remains `planets-lab.compiled-movement.v3`; the ordered post-compile semantic marker is bumped to `planets-lab.compiled-movement-storm-context.v3` for cache invalidation. Runtime L1/L2 rebuild verification is pending. If production reproduces the independent diagnostic exactly, the final residual will change `2236 -> 2226`.

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-25-damage-limited-warp-runtime-verification.md`](docs/handoff/2026-08-25-damage-limited-warp-runtime-verification.md) — latest movement/corpus handoff;
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
