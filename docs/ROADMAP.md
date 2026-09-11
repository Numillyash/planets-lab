# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Reverse progress assessment: [`handoff/2026-09-11-reverse-progress-assessment.md`](handoff/2026-09-11-reverse-progress-assessment.md).
- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Privateer Rob selector-impact runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md).
- Bird Super Spy population runtime: [`handoff/2026-09-11-combat-c5-bird-super-spy-population-runtime.md`](handoff/2026-09-11-combat-c5-bird-super-spy-population-runtime.md).
- Advanced Cloak visible-context runtime: [`handoff/2026-09-11-combat-c5-bird-advanced-cloak-decisive-context-runtime.md`](handoff/2026-09-11-combat-c5-bird-advanced-cloak-decisive-context-runtime.md).
- Advanced Cloak raw-event runtime: [`handoff/2026-09-12-combat-c5-bird-advanced-cloak-raw-event-runtime.md`](handoff/2026-09-12-combat-c5-bird-advanced-cloak-raw-event-runtime.md).
- Advanced Cloak decisive closure runtime: [`handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-runtime.md`](handoff/2026-09-12-combat-c5-bird-advanced-cloak-decisive-closure-runtime.md).
- Active directional targetability population gate: [`handoff/2026-09-12-combat-c5-directional-targetability-population-pending.md`](handoff/2026-09-12-combat-c5-directional-targetability-population-pending.md).

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

Candidate-set v2 independently covers `428 / 1986 = 21.6%` factual ship-vs-ship pairs, with zero conditionally hard-blocked covered factual pairs. Position v3 predicts 1810/3204 factual ship occurrences, 1806 exact and 4 mismatch.

Whole-NuHost progress is lower because economy/starbase production, minefield lifecycle, general missions/special abilities, race mechanics, cross-subsystem diplomacy, observer/visibility and complete-turn differential validation remain major work.

## Current focus

Active milestone remains **M5 — historical NuHost corpus + compatibility mining**. Combat C1-C4 are checkpointed. C5 remains immediate.

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

When the eligible set is correct:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not invert target ordering.

### Directional targetability evidence checkpoint

Original broad initial mismatches:

```text
360690/T83: active264; extra98; factual190   # Privateer Rob
511506/T94: active496; extra202; factual332  # Bird ordinary Super Spy
```

Privateer Rob ordinary cloak is `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` within scope. Bird ordinary Super Spy ship202 is `DOCUMENTED + CORPUS_OBSERVED + TESTED` at the focused targetability boundary.

Bird population hard-contradiction scan:

```text
bird_super_spy_targets_at_factual_sites=30
plain STANDARD one-way opportunities=8

decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
blocked factual-pair regressions=0
```

The three decisive unresolved rows were Advanced Cloak. They are now historically explained:

```text
680435/T31 ship68:
  explicit mine hit -> damage55 -> same damage in factual VCR -> combat eligible

620694/T119 ship26:
  stable same-owner/same-hull T attribution, damage0, iscloaked=true -> skipped

620694/T119 ship69:
  stable same-owner/same-hull T attribution, damage0, iscloaked=true -> skipped
```

Advanced closure runtime acceptance:

```text
factual_mine_decloak_closed=True
blocked_advanced_controls_closed=True
all_decisive_advanced_rows_explained=True
```

This closes the historical contradiction but does not create a universal predictive Advanced-Cloak resolver. Dynamic state must eventually come from reconstructed movement/mine/Glory/Loki/fuel phases rather than Host messages or T state.

### Immediate combat work — population directional STANDARD targetability

Active diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_directional_targetability_audit.py
tests/test_combat_host_initial_standard_directional_targetability_audit.py
```

Supported block inputs are deliberately narrow:

1. DIFF_VERIFIED Privateer Rob ordinary-cloak helper=True rows;
2. documented/corpus-tested Bird ordinary Super Spy `candidate_blocked=True` rows;
3. the two historically closed Advanced-Cloak blocked controls;
4. mine-hit ship68 retained only as an explicit eligible control.

Every block is directional `(attacker -> target)`. Do not turn this into symmetric pair eligibility. Preserve the cloaked ship's own attack request and leave pre-standard C&I/PIA untouched.

Acceptance requires:

```text
privateer_gate_clean=True
bird_population_gate_clean=True
advanced_decisive_closure_clean=True
no_supported_block_conflicts=True
no_supported_blocked_factual_pairs=True
no_potential_first_selector_regressions=True
strict_and_conditional_exact_set_controls_preserved=True
all_baseline_mismatch_profiles_fixed=True
privateer_residual_all_profiles_fixed=True
bird_residual_all_profiles_fixed=True
no_unrelated_baseline_mismatches=True
advanced_mine_hit_eligible_control_preserved=True
directional_targetability_population_gate_passed=True
```

Expected broad mismatch projection:

```text
baseline mismatch profiles=4
privateer fixed=2/2
bird fixed=2/2
unrelated=0
```

If the population gate passes:

1. record runtime and update PR/handoff;
2. wire a **directional ordinary-STANDARD targetability input** into canonical pair/selector composition;
3. do not encode cloak by abusing `has_fuel=False`;
4. keep effective-state reconstruction outside pure pair composition;
5. rerun full initial selector regression suite;
6. then proceed to mutable survivor/destruction state, mutable second-pass orientation, capture continuation and ship-to-planet/planet-base integration;
7. keep game `591478` separate.

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
