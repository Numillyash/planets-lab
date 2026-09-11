# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Reverse progress assessment: [`handoff/2026-09-11-reverse-progress-assessment.md`](handoff/2026-09-11-reverse-progress-assessment.md).
- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Privateer Rob selector-impact runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md).
- Bird Super Spy cloak-context runtime: [`handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-runtime.md`](handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-runtime.md).

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

### Original broad initial blockers — CLOSED independently

The two original broad mismatches were:

```text
360690/T83: active264; extra98; factual190   # Privateer Rob
511506/T94: active496; extra202; factual332  # Bird Super Spy
```

#### Privateer Rob

Scoped ordinary-cloak state:

```text
Privateer race5 + mission9 Rob + ordinary cloak-capable hull:
  prior false                         -> not effectively cloaked
  prior true + fuel <= reference cost -> not effectively cloaked
  prior true + fuel >  reference cost -> effectively cloaked
  advanced cloak                      -> unresolved
```

Differential evidence:

```text
queue-decisive rows=8
matches=8
mismatches=0

selector impact:
  blocked_factual_pair_rows=0
  potential_first_selector_regression_rows=0
  privateer_residual_profiles_projected_fixed=2/2
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

#### Bird Super Spy

Focused runtime source:

```text
6cf47de46fadcbe1619c6a6eee5731d51866c12e
```

Runtime:

```text
21 targeted tests passed
focus_row_found=True
archive_found=True
race_conflicts=0
extra_ship_documented_effective_cloak_supported=True
factual_ship_documented_effective_cloak_supported=False
raw_prior_cloak_control_separates=True
```

For ship202:

```text
Bird race3 / Red Wind / mission9 Super Spy
damage=0
fuel 37, reference cloak cost 5
reference normal move fuel used 8, remaining 29
prior iscloaked=true
ion storm=False
planet Super-Spy Ion Pulse=False
Loki=False
active Glory=False
```

Status at focused ordinary-STANDARD targetability boundary:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED
```

Matched factual ship332 has prior `iscloaked=true` but mission2 and actually fights, so raw archived cloak remains rejected as a blanket blocker.

### Immediate combat work — generic directional STANDARD targetability

The next gate is **not** another ship-specific patch.

Proceed in this order:

1. compose evidence-scoped Privateer and Bird cloak states into a directional STANDARD-targetability projection;
2. keep symmetric pair eligibility and PIA/C&I/pre-standard semantics unchanged;
3. apply the projection across reconstructed relevant target opportunities, not only the two known residual ship IDs;
4. rerun the full initial STANDARD selector differential;
5. require all previously exact first selectors to stay exact;
6. require zero blocked factual-pair regressions and zero first-selector regressions;
7. require both original broad residuals to project fixed in every comparable strict/conditional profile;
8. unresolved/advanced/out-of-scope effective state must fail closed and must not silently block combat;
9. only after this passes, promote the canonical first STANDARD selector;
10. then move to mutable survivor/destruction state, mutable second-pass orientation, capture continuation and ship-to-planet/planet-base integration;
11. keep game `591478` separate.

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