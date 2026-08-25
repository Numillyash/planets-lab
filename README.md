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
label_issues                           0
```

Recently closed/integrated movement work includes warp-well ordering, scoped Red Mite fallback evidence, Horwasp ballistic topology, classic-vs-cloudy ion-storm handling, evidence-scoped sphere-aware ordinary movement for game `591478`, route-equivalent Chunnel multi-event handling, strict mine/web interruption context, route-equivalent visible Tow handling, and strict damage-limited maximum warp.

Verified status:

- route-equivalent visible Tow — **TESTED + DIFF_VERIFIED**;
- strict mine/web v5 — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- route-equivalent Chunnel — **TESTED + DIFF_VERIFIED**;
- strict damage-limited maximum warp — **DOCUMENTED (legacy Nu help page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

The damage-limited L1 pass independently predicted and production reproduced exactly `10` strict rows. The accounting differential was an exact match; post-build damage audit found zero remaining exact eligible matches. Targeted tests (`27 passed`) and the full pytest suite are green.

Current generic endpoint:

```text
final_residual_rows       2226
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               769
generic_games               12
generic_hulls               76
```

The dominant short-forward family changed only `121 -> 119`, confirming damage-limited warp is real but sparse rather than the main cause of that family.

The current focused task is an exact **fuel-proration Host differential**. A current-endpoint rerun of the historical fuel audit still found seven strong fuel-limited correlations overall and three inside the surviving 119-row family, but its `affordable_frontier_match` criterion is not the documented Planets.nu proration rule. Planets.nu documents waypoint-distance proration (`waypoint distance * fuel available / fuel required`) and explicitly distinguishes it from VGAP3 maximum-distance behavior. `tools/diagnostics/fuel_proration_host_differential_audit.py` now compares documented Nu proration, the historical affordable-frontier heuristic and a VGAP3-style control using exact Host-major/minor endpoints plus out-of-fuel post-state evidence. No production fuel label is promoted pending that differential.

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-25-fuel-proration-host-differential-pending.md`](docs/handoff/2026-08-25-fuel-proration-host-differential-pending.md) — latest movement/corpus handoff;
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
