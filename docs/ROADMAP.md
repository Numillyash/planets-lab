# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Reverse progress assessment: [`handoff/2026-09-11-reverse-progress-assessment.md`](handoff/2026-09-11-reverse-progress-assessment.md).
- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Privateer Rob selector-impact runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md).
- Bird Super Spy cloak-context runtime: [`handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-runtime.md`](handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-runtime.md).
- Combined blocker projection runtime: [`handoff/2026-09-11-combat-c5-initial-standard-combined-blocker-projection-runtime.md`](handoff/2026-09-11-combat-c5-initial-standard-combined-blocker-projection-runtime.md).
- Active Bird population gate: [`handoff/2026-09-11-combat-c5-bird-super-spy-population-pending.md`](handoff/2026-09-11-combat-c5-bird-super-spy-population-pending.md).

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

When the eligible set is correct:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not invert target ordering.

### Original broad initial blockers — independently closed

The two original broad mismatches were:

```text
360690/T83: active264; extra98; factual190   # Privateer Rob
511506/T94: active496; extra202; factual332  # Bird Super Spy
```

Privateer Rob ordinary-cloak directional targetability is `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` within its tested scope. Bird ship202 is `DOCUMENTED + CORPUS_OBSERVED + TESTED` at the focused ordinary-cloak Super Spy targetability boundary.

The combined structural projection runtime now closes all four strict/conditional baseline mismatch profiles:

```text
baseline_mismatch_examples=4
privateer_residual_profiles=2
privateer_residual_profiles_projected_fixed=2
bird_residual_profiles=2
bird_residual_profiles_projected_fixed=2
unrelated_baseline_mismatches=0
```

Acceptance:

```text
privateer_gate_still_clean=True
bird_context_gate_clean=True
privateer_residual_all_profiles_projected_fixed=True
bird_residual_all_profiles_projected_fixed=True
no_unrelated_baseline_mismatches=True
all_original_broad_mismatches_projected_fixed=True
```

This is a structural composition checkpoint only. It does not yet justify a corpus-wide Bird rule or canonical selector wiring.

### Immediate combat work — Bird Super Spy population differential

Active diagnostic:

```text
tools/diagnostics/combat_host_bird_super_spy_attack_opportunity_audit.py
tests/test_combat_host_bird_super_spy_attack_opportunity_audit.py
```

The gate reconstructs all one-way hostile plain-STANDARD opportunities against Bird race3 / mission9 Super Spy / cloak-capable targets at factual combat sites. It uses the same position-v3/candidate-set-v2, diplomacy and canonical pair-decision primitives as the existing initial STANDARD and Privateer diagnostics.

Each target is evaluated conservatively for documented ordinary cloak using damage, fuel, independently reconstructed reference movement, prior archived cloak, ion storm, possible planet Ion Pulse, Loki and active Glory context. Advanced/unresolved state fails closed.

Queue-decisive labels remain limited to:

```text
initial_pair_vcr                       -> expected eligible
initial_skip_target_outranks_factual  -> expected blocked
```

Acceptance requires:

```text
no_race_conflicts=True
no_payload_conflicts=True
no_blocked_factual_pair_regressions=True
no_decisive_mismatch=True
target_residual_present=True
target_residual_supported=True
```

`decisive_unresolved>0` is not automatically a contradiction because the model deliberately fails closed, but every unresolved decisive row must be inspected before promotion.

If the Bird population gate is clean enough:

1. compose supported Bird states with the already DIFF_VERIFIED Privateer targetability overlay;
2. run a population-wide directional STANDARD targetability differential over the full initial selector baseline;
3. require all previously exact first selectors to remain exact, zero factual-pair regressions, zero first-selector regressions and both original residuals fixed;
4. only then wire directional targetability into the canonical first STANDARD selector;
5. proceed to mutable survivor/destruction state, second-pass orientation, capture continuation and ship-to-planet/planet-base integration;
6. keep game `591478` separate.

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
