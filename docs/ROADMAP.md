# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Reverse progress assessment: [`handoff/2026-09-11-reverse-progress-assessment.md`](handoff/2026-09-11-reverse-progress-assessment.md).
- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial target-order evidence runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Directional targetability population runtime: [`handoff/2026-09-16-combat-c5-directional-targetability-population-runtime.md`](handoff/2026-09-16-combat-c5-directional-targetability-population-runtime.md).
- Canonical pair-level targetability runtime: [`handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md`](handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md).
- Canonical initial plain-STANDARD selector runtime: [`handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-runtime.md`](handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-runtime.md).
- Active production effective-state gate: [`handoff/2026-09-16-combat-c5-production-effective-state-pending.md`](handoff/2026-09-16-combat-c5-production-effective-state-pending.md).
- Advanced Cloak decisive historical closure: [`handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-runtime.md`](handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-runtime.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status: `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED`. Unknown mechanics fail closed. Post-Host `T`, factual VCR outcomes and Host messages may provide historical attribution but must not become production precombat state inputs.

## Engineering progress estimate

Planning estimates only:

```text
combat mechanics reconstruction (C1-C5 knowledge):     ~75-85%
ordinary ship-combat independent candidate coverage:    ~20-25%
movement ordinary-core reconstruction:                  ~80-90%
whole NuHost reverse across the roadmap:                ~40-50%
```

Candidate-set v2 independently covers `428 / 1986 = 21.6%` factual ship-vs-ship pairs, with zero conditionally hard-blocked covered factual pairs. Position v3 predicts 1810/3204 factual ship occurrences, 1806 exact and 4 mismatch.

Whole-NuHost progress remains lower because economy/starbase production, minefield lifecycle, general missions/special abilities, race mechanics, cross-subsystem diplomacy, observer/visibility and complete-turn differential validation remain major work.

## Current focus

Active milestone remains **M5 — historical NuHost corpus + compatibility mining**. Combat C1-C4 are checkpointed. C5 remains immediate.

Stable C5 layers now include:

- pair composition and factual phase ordering;
- normal/reciprocal Priority Intercept attribution;
- scoped Galactic Power and matching-FC exceptions;
- repaired precombat positions and candidate-set v2;
- repeated-pair side reversal;
- directional ordinary-STANDARD targetability at pair level;
- production initial plain-STANDARD stack selector.

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

### Initial STANDARD selector — production closed

Evidence rule:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Production API:

```python
select_initial_plain_standard(...)
```

Corpus differential:

```text
strict:      225/225 broad, 162/162 exact-set
conditional: 234/234 broad, 169/169 exact-set
```

Status:

```text
initial plain-STANDARD stack selector:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

### Directional targetability — pair/selector boundary closed

Population gate:

```text
supported blocks=10
conflicts=0
blocked factual pairs=0
potential first-selector regressions=0
baseline mismatch profiles fixed=4/4
unrelated mismatches=0
```

Canonical input:

```python
ShipCombatSideInput.standard_targetable_by_opponent: bool | None
```

It applies only to incoming ordinary STANDARD requests after PIA/C&I classification. It is directional, preserves the target ship's own attack request and does not misuse fuel as cloak state.

### Current combat work — production precombat effective state

Privateer ordinary Rob already has production reconstruction:

```python
privateer_rob_ordinary_cloak_state(...)
```

Bird ordinary Super Spy now has production reconstruction:

```python
bird_super_spy_ordinary_cloak_state(...)
standard_targetability_from_effective_cloak(...)
```

Implementation commit:

```text
0b88541df32c441ead4b9b9d6054af04fd2fee7a
```

The Bird helper uses only precombat-resolvable state: T-1 damage/fuel/prior cloak, ordinary reference cost, independently reconstructed reference movement and remaining fuel, ion/Loki/Glory/planet-pulse context. Advanced Cloak remains unresolved.

Active diagnostic:

```text
tools/diagnostics/combat_host_bird_super_spy_production_effective_state_audit.py
```

Required acceptance:

```text
population_no_race_conflicts=True
population_no_payload_conflicts=True
population_no_blocked_factual_pair_regressions=True
population_no_decisive_mismatch=True
population_target_residual_present=True
population_target_residual_supported=True
production_targetability_blocks_target_residual=True
advanced_rows_remain_unresolved=True
production_effective_state_gate_passed=True
```

Expected retained Bird population:

```text
one-way plain-STANDARD opportunities=8
decisive rows=4
match=1 mismatch=0 unresolved=3
blocked factual-pair regressions=0
```

The three unresolved rows must remain Advanced Cloak. Historical explanation of those rows does not yet constitute a predictive production resolver.

### After the active gate

If production effective-state runtime is green, leave the initial cloak/targetability loop and proceed with mutable C5 queue reconstruction:

1. survivor/destruction mutation;
2. mutable second-pass pair eligibility and side reversal;
3. capture continuation;
4. ship-to-planet / planet-base queue integration;
5. keep game `591478` separate.

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
