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
- Bird population runtime: [`handoff/2026-09-11-combat-c5-bird-super-spy-population-runtime.md`](handoff/2026-09-11-combat-c5-bird-super-spy-population-runtime.md).
- Advanced Cloak visible-context runtime: [`handoff/2026-09-11-combat-c5-bird-advanced-cloak-decisive-context-runtime.md`](handoff/2026-09-11-combat-c5-bird-advanced-cloak-decisive-context-runtime.md).
- Active Advanced Cloak raw-event gate: [`handoff/2026-09-11-combat-c5-bird-advanced-cloak-event-pending.md`](handoff/2026-09-11-combat-c5-bird-advanced-cloak-event-pending.md).

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
511506/T94: active496; extra202; factual332  # Bird ordinary Super Spy
```

Privateer Rob ordinary-cloak directional targetability is `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` within its tested scope. Bird ship202 is `DOCUMENTED + CORPUS_OBSERVED + TESTED` at the focused ordinary-cloak Super Spy targetability boundary.

The combined structural projection closes all four strict/conditional baseline mismatch profiles:

```text
baseline_mismatch_examples=4
privateer_residual_profiles_projected_fixed=2/2
bird_residual_profiles_projected_fixed=2/2
unrelated_baseline_mismatches=0
all_original_broad_mismatches_projected_fixed=True
```

This is structural composition only; canonical selector wiring is still intentionally deferred.

### Bird population checkpoint

Population audit over Bird race3 / mission9 Super Spy / cloak-capable targets:

```text
bird_super_spy_targets_at_factual_sites=30
plain STANDARD one-way opportunities=8

decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
blocked factual-pair regressions=0
```

All hard acceptance checks passed. The original ordinary-cloak ship202 residual is the one decisive match. All three decisive unresolved rows are Advanced Cloak:

```text
620694/T119 ship26 vs74 — expected blocked
620694/T119 ship69 vs74 — expected blocked
680435/T31 ship68 vs26 — factual pair / expected eligible
```

Therefore Advanced Cloak cannot be blanket-blocked.

### Advanced Cloak visible-context checkpoint

Focused full-position/post-movement audit:

```text
focus_rows=3
expected_blocked_rows=2
expected_eligible_rows=1
postmove_active_glory_possible_rows=0
postmove_loki_possible_rows=0
```

All three rows have no visible candidate-set mine-route risk. The factual ship68 and skipped ship26/69 are therefore not separated by visible Glory, Loki or visible mine geometry.

`620694/T119 ship26/69` remain stable at T with damage0 and `iscloaked=true`; this supports continued cloak attribution but T remains post-Host and cannot feed precombat state. `680435/T31 ship68` has no stable T identity because it participates in the factual combat.

Attacker ship26 mission3 is canonical `Kill!`, so the ship68 factual pair is a valid ordinary-STANDARD negative control rather than a phase-classification artifact.

Population-wide Bird Advanced Cloak targetability remains:

```text
UNRESOLVED
```

### Immediate combat work — raw Host events / hidden context

Active gate:

```text
tools/diagnostics/combat_host_bird_advanced_cloak_event_audit.py
tests/test_combat_host_bird_advanced_cloak_event_audit.py
```

The diagnostic inspects narrow raw `.trn` windows around the two decisive cases and inventories only tightly scoped mechanical evidence:

```text
680435: T30/T31/T32; focus ships68/26; site(1984,2266)
620694: T118/T119/T120; focus ships26/69/74; site(1590,1837)
```

It reports owner3 active race/campaign advantages, settings and visible minefields; focus ship timelines; exact-ID/site mechanical messages; sanitized event/report records; and matching VCRs.

Priority hypotheses:

1. explicit mine/web hit or cloak-failure report for factual ship68;
2. Hidden Minefields or another relevant active advantage plus compatible mechanical evidence;
3. typed damage/decloak/Loki/Glory event not represented by the normalized context;
4. another raw Host event that separates ship68 from skipped ship26/69.

**Absence of a message is not proof of no event.** If no positive separator appears, Advanced Cloak stays unresolved/fail-closed rather than being special-cased.

After Advanced Cloak is either resolved or explicitly kept outside the supported targetability scope:

1. compose only supported Privateer/Bird directional targetability states;
2. run the population-wide initial STANDARD selector differential;
3. require all previously exact first selectors to remain exact, zero factual-pair/first-selector regressions and both original residuals fixed;
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
