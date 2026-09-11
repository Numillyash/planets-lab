# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current durable checkpoints

- Reverse progress assessment: [`handoff/2026-09-11-reverse-progress-assessment.md`](handoff/2026-09-11-reverse-progress-assessment.md).
- Host combat phase C5: [`handoff/2026-09-08-combat-c5-host-phase-current.md`](handoff/2026-09-08-combat-c5-host-phase-current.md).
- Candidate-set v2 runtime: [`handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`](handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md).
- Initial plain-STANDARD target-order runtime: [`handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`](handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md).
- Privateer Rob clean fuel-attribution runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-runtime.md).
- Privateer Rob effective-cloak threshold runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-effective-cloak-threshold-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-effective-cloak-threshold-runtime.md).
- Privateer Rob selector-impact runtime: [`handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md`](handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md).
- Active Bird Super Spy gate: [`handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-pending.md`](handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-pending.md).

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

### Residual blocker state

Original broad initial residuals:

```text
360690/T83: active264; extra98; factual190   # Privateer Rob branch
511506/T94: active496; extra202; factual332  # Bird Super Spy branch
```

The **Privateer branch is now closed at the scoped initial-STANDARD targetability boundary**.

Clean fuel attribution rejected a universal `Rob Ship consumes ordinary cloak fuel` rule, but low-fuel threshold controls showed `13/13` ordinary-cloak prior-true rows at or below the reference cost transitioning `true_to_false`.

Effective-cloak threshold differential over all 16 independently reconstructed Rob plain-STANDARD opportunities:

```text
decisive_rows=8
decisive_match=8
decisive_mismatch=0
decisive_unresolved=0
expected blocked -> candidate blocked: 3/3
expected eligible -> candidate eligible: 5/5
```

Selector-impact runtime on source `5bfdecfc090357cd7f38fa69f9cb05d2c6aee611`:

```text
overlay_rows=16
overlay_blocked=7
overlay_eligible=9
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
privateer_residual_profiles_projected_fixed=2/2
bird_residual_profiles_overlay_affected=0/2
```

Acceptance was fully true. Status of the Privateer ordinary-cloak targetability model:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Evidence-scoped helper:

```text
src/planets_lab/rules/combat/effective_state.py
```

Architectural boundary: the Privateer evidence supports a **directional ordinary-STANDARD targetability blocker**, not a symmetric blanket pair-combat cloak blocker. The helper is therefore still not wired directly into `selection.py` or `queue.py`.

### Immediate combat work — Bird Super Spy

The sole remaining original broad initial blocker is `511506/T94/ship202`.

Existing corpus evidence:

```text
ship202:
  Bird race3
  Red Wind cloak-capable hull
  mission9 Super Spy
  T-1 iscloaked=true
  T-1 fuel=37
  ordinary reference cloak cost=5
  same owner/hull at T and T iscloaked=true

ship332 factual target control:
  Bird race3
  Resolute cloak-capable hull
  mission2 (not Super Spy)
  T-1 iscloaked=true
  factual combat against ship496 occurs
```

Thus raw `T-1 iscloaked` remains rejected as a generic blocker.

Official Planets.nu documentation explicitly states that a Bird ship on Super Spy which can cloak attempts to cloak normally, inadequate fuel prevents the cloak, cloaked ships are protected from enemy attack, and damage prevents cloak.

Active gate:

```text
tools/diagnostics/combat_host_bird_super_spy_cloak_context_audit.py
tests/test_combat_host_bird_super_spy_cloak_context_audit.py
```

The gate requires ordinary cloak, damage0, positive fuel margin before and after independently reconstructed normal movement, prior archived cloak=true, and clear T-1 ion/Loki/active-Glory context. T state is attribution-only.

Proceed in this order:

1. run the Bird Super Spy context unit tests;
2. run `combat_host_bird_super_spy_cloak_context_audit.py` on the historical corpus;
3. require ship202 `documented_effective_cloak_supported=True`, ship332 not supported for an explicit non-Super-Spy reason, `raw_prior_cloak_control_separates=True`, and zero race conflicts;
4. if clean, mark Bird target blocker `DOCUMENTED + CORPUS_OBSERVED + TESTED` and project removal of ship202 from both strict/conditional baseline mismatches;
5. after both Privateer and Bird blockers are closed, promote a generic directional STANDARD targetability composition and rerun the full initial-selector differential;
6. only then promote the canonical first selector and move to mutable survivor/destruction state, mutable second-pass orientation, capture continuation and ship-to-planet/planet-base integration;
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