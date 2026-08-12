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

## Status

Bootstrap stage. The first milestone is a stable canonical `GameState` plus a minimal deterministic `HostEngine.step()` contract.
