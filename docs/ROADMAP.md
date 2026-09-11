# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Reverse progress assessment: [`handoff/2026-09-11-reverse-progress-assessment.md`](handoff/2026-09-11-reverse-progress-assessment.md).
- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Privateer Rob cloak/fuel-state population runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md).
- Active Rob cloak/fuel attribution gate: [`handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-pending.md`](handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-pending.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status: `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED`. Unknown mechanics fail closed.

## Engineering progress estimate

Planning estimates only:

```text
combat mechanics reconstruction (C1-C5 knowledge):     ~70-80%
ordinary ship-combat independent candidate coverage:    ~20-25%
movement ordinary-core reconstruction:                  ~80-90%
whole NuHost reverse across the roadmap:                ~40-50%
```

The combat coverage number refers to the independent candidate-set boundary, not final full Host VCR prediction. Candidate-set v2 independently covers `428 / 1986 = 21.6%` factual ship-vs-ship pairs, with zero conditionally hard-blocked covered factual pairs. Position v3 predicts 1810/3204 factual ship occurrences, 1806 exact and 4 mismatch. Mechanics knowledge is therefore substantially ahead of full independent historical coverage.

Whole-NuHost progress is lower because economy/starbase production, minefield lifecycle, general missions/special abilities, race mechanics, cross-subsystem diplomacy, observer/visibility and complete-turn differential validation remain major work. See `docs/handoff/2026-09-11-reverse-progress-assessment.md`.

## Current focus

Active milestone remains **M5 — historical NuHost corpus + compatibility mining**. Combat C1-C4 are checkpointed. C5 is immediate.

Stable C5 layers include pair composition, factual phase ordering, normal/reciprocal Priority Intercept attribution, scoped Galactic Power, matching-FC exceptions, repaired precombat positions, candidate-set v2, repeated-pair side reversal and clean first-target ordering.

### Position / candidate checkpoint

```text
position v3:
  factual ship occurrences=3204
  predicted=1810 exact=1806 mismatch=4 uncovered=1383

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

Population fuel-state runtime source `cf52a264c31418a8247987a64332c54e50e07a91` is complete:

```text
stable prior-true rows=1413
exact_reference_debit=545
zero_debit=90
other_debit=778
true_to_true=1378
true_to_false=35
threshold equals reference cost=3
threshold below reference cost=11
```

The exact ordinary-cloak-reference debit is strongly structured:

```text
545 / 1413 = 38.6% overall
541 / 545 = 99.3% exact-debit rows are true_to_true
same-position damage0 PE0 no-VCR bucket:
  515 exact / 112 other / 86 zero
```

This is `CORPUS_OBSERVED + TESTED` correlation only. Do not encode `Rob Ship consumes cloak fuel` or raw prior `iscloaked` as a blocker.

### Immediate combat work

The first cloak/fuel attribution runtime attempt on source `180429508419581cf5082bb5363e1b8c528dd14f` is **invalid** as mechanics evidence: pytest collection failed with `ModuleNotFoundError: No module named 'tools'` (`tests rc=2`, `audit rc=99`). Both new tests now use the established `tools/diagnostics` import convention.

Proceed in this order:

1. rerun `tools/diagnostics/combat_host_privateer_rob_cloak_fuel_attribution_audit.py` and its targeted tests on the repaired HEAD;
2. inspect the clean stationary/no-visible-fuel-mutation population;
3. inspect all 14 stable low-fuel controls (`3 == reference cost`, `11 < reference cost`) including ion/Loki/Glory context;
4. if a coherent threshold transition survives, define an evidence-scoped effective-state helper and rerun initial-target differential;
5. otherwise reject the threshold explanation rather than special-case ship118;
6. keep Bird Super Spy ship202 separate from Privateer Rob ship98;
7. after blocker closure, promote the canonical first selector, then compose mutable survivor/destruction state, second-pass orientation, capture continuation and ship-to-planet/planet-base integration;
8. keep game `591478` separate.

## Wider Host reconstruction order

1. Movement checkpoint — substantially reconstructed.
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
13. Training environment and AI after simulator/observer surfaces are sufficiently faithful.

## Wider milestones

```text
M0 deterministic skeleton:          ~90%+
M1 minimal sandbox/infrastructure: ~80-90%
M2 economy/planetary Host:         ~35-50%
M3 warfare overall:                ~65-75%
M4 race-specific mechanics:        ~35-50%
M5A historical corpus pipeline:    ~75-85%
M5B Nu compatibility/differential: ~60-75%
M6 training/AI:                    intentionally later
```

Do not shortcut unresolved Host rules merely to begin training sooner.
