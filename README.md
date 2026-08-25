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

The dominant short-forward family is now `119` Warp 7-9 `<0.5x` same-line-forward rows.

The current focused mechanic is **documented Planets.nu insufficient-fuel waypoint proration**. On the current final residual, the exact Host-endpoint differential found:

```text
raw-mass insufficient candidates   19
Nu waypoint-proration exact         6
affordable-frontier exact           3
VGAP3-style exact                    0
Nu-only exact                        3
```

The six Nu exact rows span four hulls and three games; three belong to the dominant 119-row family. This is direct corpus discrimination in favor of the documented Nu waypoint-distance rule rather than the old affordable-frontier correlation.

Historical next-turn owner snapshots are **not** treated as immediate post-Host frames for editable `warp`, waypoint or fuel fields. Planets.nu Time Machine preserves historical end-turn orders, so those fields may already reflect the player's next submitted orders/transfers. Host outcome `x/y` remains the primary exact movement observation.

No fuel production label has been promoted yet. The immediate task is `tools/diagnostics/fuel_proration_global_stage_audit.py`, which scans the full current L1 residual and partitions exact Nu matches by downstream Chunnel/Horwasp/mine/final stage while conservatively excluding raw damage-limited rows. This determines whether fuel can safely enter the early L1 context stack or should first remain a later evidence-layer label.

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-25-fuel-proration-global-stage-pending.md`](docs/handoff/2026-08-25-fuel-proration-global-stage-pending.md) — latest movement/corpus handoff;
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
