# Architecture

## Purpose

`planets-lab` is a headless, deterministic simulation and ML/RL research environment for Planets.nu-style games.

It is intentionally separate from `planets-intel`, which owns the web application, API, persistence, observations, historical statistics and user-facing intelligence features.

## Core boundary

The simulator works with a full-information canonical `GameState`:

```text
GameState + TurnOrders + seed
             |
             v
        HostEngine
             |
             v
   GameState' + events
```

`HostEngine.step()` must be deterministic for identical state, orders, ruleset and RNG seed.

The input state must not be mutated. A completed host turn returns a new state.

## Information boundary

`GameState` is omniscient simulator state and must not be passed directly to an autonomous player in normal training/evaluation.

The future observation layer will expose only information available to one player:

```text
GameState
   |
   v
Observer(player_id, memory)
   |
   v
PlayerObservation
   |
   v
Agent
   |
   v
PlayerOrders
```

Historical facts and inferred enemy state must remain distinguishable.

## Host phases

Host mechanics are implemented as explicit ordered phases rather than one monolithic `step()` function.

```text
orders
  -> phase 1
  -> phase 2
  -> ...
  -> phase N
  -> next turn
```

This is required for:

- reproducing NuHost host order;
- unit-testing mechanics independently;
- differential testing against reference outcomes;
- enabling/disabling ruleset features without spreading race/ruleset conditionals throughout the engine.

## Rules and uncertainty

A rule/mechanic should eventually carry evidence status in the specification layer:

- `DOCUMENTED` — stated in primary Planets.nu documentation;
- `INFERRED` — reconstructed from observations or secondary material;
- `TESTED` — covered by a local scenario test;
- `DIFF_VERIFIED` — matched against a NuHost reference scenario.

Unknown mechanics must not be silently guessed in simulator code.

## Repository boundaries

```text
src/planets_lab/
  core/       canonical omniscient state
  sim/        host pipeline and host phases
  rules/      ruleset constants/abilities/order
  observer/   player-limited observations
  data/       import/export and dataset conversion
  ai/         agent/environment interfaces

tests/        unit tests
validation/   golden and differential host scenarios
docs/         design and rule notes
```

## Initial milestones

### M0 — deterministic skeleton

- canonical `GameState`;
- immutable turn-order contracts;
- deterministic seeded `HostEngine.step()`;
- validation and baseline tests.

### M1 — minimal sandbox

- Planets.nu JSON -> canonical state adapter;
- cargo transfer;
- basic movement;
- fuel calculation;
- colonization;
- minimal planet economy;
- golden scenarios for every implemented mechanic.

### M2 — economy

- mining;
- factories and supplies;
- natives and taxation;
- starbases;
- ship construction.

### M3 — warfare

- combat;
- towing;
- minefields;
- missions;
- fighters/torpedoes.

### M4 — race mechanics

Race-specific behavior is implemented through explicit ruleset modules/hooks, not global `if race == ...` conditionals.

### M5 — Nu compatibility

Build a differential suite of small deterministic scenarios and measure compatibility by mechanic.

### M6 — training

- scripted baseline agents;
- player observation environment;
- historical imitation/value models;
- parallel self-play;
- policy/value training.
