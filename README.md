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
fuel_proration_explained               6
post_fuel_proration_residual        2220
label_issues                           0
```

Recently closed/integrated movement work includes warp-well ordering, scoped Red Mite fallback evidence, Horwasp ballistic topology, classic-vs-cloudy ion-storm handling, evidence-scoped sphere-aware ordinary movement for game `591478`, route-equivalent Chunnel multi-event handling, strict mine/web interruption context, route-equivalent visible Tow handling, strict damage-limited maximum warp, and documented insufficient-fuel waypoint proration.

Verified status:

- route-equivalent visible Tow — **TESTED + DIFF_VERIFIED**;
- strict mine/web v5 — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- route-equivalent Chunnel — **TESTED + DIFF_VERIFIED**;
- strict damage-limited maximum warp — **DOCUMENTED (legacy Nu help page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict Nu waypoint-distance fuel proration v6 — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

Fuel-proration v6 reproduced its independently predicted six-row differential exactly. All six rows came from the pre-existing `post_mine_strong_residual`; Chunnel/Horwasp/mine overlap guards were zero. The v5 -> v6 label-schema bump produced 0/12 label-cache hits and 12/12 prepared-cache hits, as intended.

Current generic endpoint:

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest surviving coarse families:

```text
116  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 43  warp7-9 0.5-1.0x observed=other same_line_forward
```

The Crystal Web Drain investigation is now closed as one fully attributable **DOCUMENTED + CORPUS_OBSERVED strong evidence-only** transition. For game `360690`, turn `44`, the exact relation-pair / game-era audit proved that the Crystal-owned web was not diplomacy-immune and that subtracting the documented 25 KT from both available fuel and movement mass produces the exact already-verified Nu-proration endpoint. It is intentionally not production-promoted because support remains one game / one hull.

The subsequent outbound submitted fuel-transfer pass was negative for the dominant family:

```text
target_short_outbound_fuel_transfer = 0
target_short_transfer_causal_exact = 0
```

Only two outbound fuel-transfer rows existed globally in the post-v6 generic Warp 1..9 population, and neither reached a current-visible co-located transfer target. This lead is closed absent new evidence.

The active focused mechanic is now **standard Cloak fuel consumption before movement feeding verified Nu waypoint proration**. Planets.nu documents that Cloak occurs before movement, standard Cloak burns `max(5, floor(hull_mass / 20))` KT fuel, that burn reduces movement mass, Advanced Cloak burns no fuel, and ships already damaged at the start of the turn do not spend cloak fuel.

Active diagnostic:

```text
tools/diagnostics/cloak_fuel_proration_audit.py
```

It tests submitted mission `10` only, requires static standard-cloak capability and zero raw damage, compares fuel-only vs. fuel+mass endpoints, and uses synthetic cloak-cost subtraction on cloak-capable non-Cloak rows as a specificity control. No production schema/accounting change is allowed during this first pass.

Current schemas:

```text
L1 physical movement:       planets-lab.compiled-movement.v3
L1 context semantics:       planets-lab.compiled-movement-storm-context.v3
L2 context labels:          planets-lab.compiled-movement-context-labels.v6
```

Read these first:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — operational roadmap and current priorities;
- [`docs/handoff/2026-08-26-cloak-fuel-proration-pending.md`](docs/handoff/2026-08-26-cloak-fuel-proration-pending.md) — latest movement/corpus handoff;
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
