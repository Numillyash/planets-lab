# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Privateer Rob attack-opportunity runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md).
- Privateer Rob initial-decision runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md).
- Privateer Rob initial cloak-context runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-initial-cloak-context-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-initial-cloak-context-runtime.md).
- Active Rob cloak/fuel-state population gate: [`handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-pending.md`](handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-pending.md).
- Repaired storm-aware precombat position runtime: [`handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md`](handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md).
- movement checkpoint: [`handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md`](handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md).
- Classic combat replay coverage: [`handoff/2026-09-07-combat-c2-classic-replay-coverage.md`](handoff/2026-09-07-combat-c2-classic-replay-coverage.md).
- ship battle sequences: [`handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md`](handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md).
- planet/starbase sequences: [`handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md`](handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean attributable NuHost transitions.

Unknown mechanics fail closed. Raw facts and evidence-scoped effective interpretations remain separate.

## Current focus

Active milestone remains **M5 — historical NuHost corpus + compatibility mining**.

Combat C1-C4 are checkpointed. C5 is immediate: reconstruct the Host phase around the deterministic resolver rather than merely replaying supplied VCRs.

Stable C5 layers include pair composition, factual phase ordering, normal/reciprocal Priority Intercept attribution, scoped Galactic Power, matching-FC exceptions, repaired precombat positions, candidate-set v2, repeated-pair side reversal and clean first-target ordering. Closed gates are not reopened absent direct contradiction.

### Position / candidate checkpoint

```text
position v3:
  factual ship occurrences=3204
  predicted=1810 exact=1806 mismatch=4 uncovered=1383
  factual pairs exact=678 mismatch=4 unresolved=1304

candidate-set v2:
  factual unique pairs=1986
  candidate-covered=428
  conditional factual eligible=427 unresolved=1 blocked=0
  strict factual eligible=420 unresolved=8 blocked=0
```

### Initial target-order checkpoint

```text
conditional exact-set: 169/169 first pair exact
strict exact-set:      162/162 first pair exact
informative exact-set target-order controls: 15/15 rank1
```

When the eligible set is correct, evidence strongly supports:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not invert target ordering.

### Residual blocker state

The two original broad initial residuals remain:

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

Bird ship202 remains a separate Super Spy/effective-cloak branch. Privateer ship98 is narrowed through Rob controls.

Initial-decision runtime isolated three clean first-decision missing-state residuals:

```text
360690/T57 ship46
360690/T57 ship280
360690/T83 ship98
```

Matched same-site prior-false Meteors are actually fought by the same attackers. The only clean prior-true initial fought control is `620694/T64/ship118` with T-1 fuel `5 KT`.

The completed cloak-context runtime source `fe9f1575b81d7ea4c922426c8f56d689dbd66ef3` rejected the hoped damage / normal-movement fuel / Loki discriminator:

```text
all four: damage=0
all four: normal move distance=0, fuel_used=0
all four: no active Loki within 10 ly
```

It exposed a stronger corpus correlation on the three stable skipped Meteors:

```text
ship46:  58 -> 53  exact -5 KT, T iscloaked=true
ship280:  9 ->  4  exact -5 KT, T iscloaked=true
ship98:  45 -> 40  exact -5 KT, T iscloaked=true
```

Meteor ordinary-cloak reference cost is 5 KT. Ship118 starts with exactly 5 KT, so a hypothetical reference debit would exhaust it exactly.

Evidence status is only:

```text
CORPUS_OBSERVED + INFERRED
```

Do **not** encode `Rob Ship consumes cloak fuel`. Privateer mission9 is Rob Ship, not the documented ordinary Cloak mission; T is post-Host; the older ordinary cloak-fuel diagnostic uses mission10 as the causal branch.

### Immediate combat work

Proceed in this order:

1. run `tools/diagnostics/combat_host_privateer_rob_cloak_fuel_state_audit.py` and its targeted test;
2. measure exact ordinary-cloak-reference fuel debit prevalence across the full stable prior-true Privateer Rob cloak-capable population;
3. split by `true_to_true/true_to_false`, stationary/moved, PE0/nonzero, VCR/no-VCR, game and hull;
4. inspect whether exact debit is a broad structured state signal or a sparse coincidence;
5. keep ship118 `5 -> 0` hypothetical only because its T physical identity is not stable;
6. if the signal is strong, run a second clean attribution pass controlling Rob/transfer exposure and documented decloak contexts including ion disturbance and Glory Device;
7. if the signal is weak/noisy, reject the 5-KT threshold explanation and search another hidden state discriminator;
8. keep Bird Super Spy ship202 separate from Privateer Rob ship98;
9. no `selection.py` or `queue.py` change until current-Host effective state can be reconstructed without blindly copying archived prior `iscloaked`;
10. after initial blocker closure, promote the canonical first selector and rerun candidate/target differentials;
11. compose mutable survivor/destruction state, second-pass orientation and capture continuation;
12. place ship-to-planet repair boundary and integrate planet/base participation;
13. keep game `591478` separate.

The target remains prediction of the **set, order and sides of VCRs Host will generate** from reconstructed precombat state.

## Wider Host reconstruction order

1. Movement checkpoint — substantially reconstructed; reopen only for bounded contradictions/interactions.
2. Classic pairwise combat C1/C2.
3. Ordinary ship battle sequences C3.
4. Planet/starbase sequences C4.
5. Full Host combat ordering / engagement selection C5 — current immediate focus.
6. Planet economy + starbases + ship production.
7. Minefield lifecycle.
8. General missions + special ship abilities.
9. Diplomacy / Safe Passage / alliance / team semantics across all subsystems.
10. Race-specific mechanics integrated vertically.
11. Observer / visibility / fog-of-war / shared intel.
12. End-to-end Host-order differential validation over complete turns.
13. Training environment and AI after simulator/observer fidelity is sufficient.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented.
- **M2 economy/planetary Host:** in progress.
- **M3 warfare:** materially advanced; full Host engagement ordering remains open.
- **M4 race mechanics:** partial; Federation recovery and scoped Galactic Power have differential evidence.
- **M5A historical corpus:** active and operational.
- **M5B Nu compatibility matrix:** active.
- **M6 training/AI:** later, after required simulation/observer surfaces are sufficiently faithful.

Do not shortcut unresolved Host rules merely to begin training sooner.
