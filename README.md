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
```

Recently closed/integrated movement work includes warp-well ordering, scoped Red Mite fallback evidence, Horwasp ballistic topology, classic-vs-cloudy ion-storm handling, evidence-scoped sphere-aware ordinary movement for game `591478`, and route-equivalent Chunnel multi-event handling.

The Chunnel v4 semantic fix is **TESTED + DIFF_VERIFIED**. A pre-fix DB audit found exactly 34 route-equivalent multi-event false residuals; the normal v4 L2 build closed exactly those 34 rows and changed the final residual `2311 -> 2277` while Horwasp strong accounting stayed unchanged.

Post-v4 generic re-triage isolated short-forward movement as the strongest generic family. Two mine/web diagnostics now provide substantial **CORPUS_OBSERVED** evidence: 18/19 web stop-state signatures are backed by an after-turn enemy web field, and 25 normal-mine candidates combine low-tech ~10-ly slowdown, damage increase and an after-turn enemy normal-mine corridor crossing.

The current focused task is a NuHost damage-rounding compatibility differential. Planets.nu documentation says mine-impact damage is rounded up, but historical field-backed examples systematically look like nearest-integer rounding for many hull masses. `tools/diagnostics/mine_hit_damage_rounding_audit.py` compares `ceil`, `floor` and positive nearest rounding with repair and no-field controls before any production mine/web label is promoted.

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-24-mine-damage-rounding-followup.md`](docs/handoff/2026-08-24-mine-damage-rounding-followup.md) — latest movement/corpus handoff;
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
