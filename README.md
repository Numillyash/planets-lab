# planets-lab

Deterministic Planets.nu simulation and AI research environment.

## Goals

- represent game state in one canonical schema;
- implement a deterministic, testable host simulator;
- build rule/specification and differential-validation tooling;
- import historical Planets.nu game data for datasets;
- expose player-limited observations for AI agents;
- support scripted bots, self-play and ML/RL experiments.

## Initial layout

```text
src/planets_lab/
  core/         canonical game state and shared domain types
  sim/          deterministic host engine
  rules/        ruleset definitions
  observer/     player observations / fog of war
  data/         importers and datasets
  ai/           agent/environment interfaces

tests/          unit and scenario tests
docs/           architecture and rule notes
validation/     differential/golden scenarios
```

## Development setup

Python 3.11+ is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest
```

## Current bootstrap

The repository now contains:

- canonical full-information `GameState`, `Player`, `Planet`, `Ship`, `Starbase` and resource models;
- immutable turn-order contracts;
- a deterministic, seeded `HostEngine.step()` pipeline;
- order ownership/duplicate validation;
- baseline tests for deterministic execution and input-state immutability.

Actual NuHost mechanics are intentionally not guessed at this stage. They will be introduced as explicit host phases backed by documented/tested scenarios.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for boundaries and milestones.
