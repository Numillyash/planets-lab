# NuHost reverse progress assessment — 2026-09-11

This is an engineering progress estimate, **not** an evidence label and not a percentage derived from test count. It exists to distinguish two different questions:

1. how much of the mechanics is understood/reconstructed;
2. how much of the historical corpus can already be predicted end-to-end from independent pre-Host inputs.

GitHub remains the source of truth. At this checkpoint `main` is `bc3b767330dc23ed09303eed766365fa53877209`; PR #28 remains draft/open and unmerged. The active C5 branch is intentionally not rebased/merged with current `main` inside this checkpoint.

## Executive estimate

```text
combat mechanics reconstruction (C1-C5 knowledge):     ~70-80%
ordinary ship-combat independent end-to-end coverage:  ~20-25%
movement ordinary-core reconstruction:                  ~80-90%
whole NuHost reverse across the roadmap:                ~40-50%
```

The ranges are deliberately broad. They are planning estimates, not promoted mechanics evidence.

## Why combat knowledge is already ~70-80%

Checkpointed / strongly constrained layers now include:

- classic deterministic combat replay foundation (C1/C2);
- ordinary ship battle sequence work (C3);
- planet/starbase sequence checkpoint (C4);
- STANDARD Combat Priority and Friendly Code parsing;
- Priority Intercept phase placement and side semantics;
- scoped Cloak & Intercept attribution;
- scoped Galactic Power side override;
- matching-FC exceptions;
- repeated-pair second-pass side reversal;
- repaired storm-aware precombat position reconstruction;
- candidate-set v2 pair composition;
- canonical pair eligibility with zero conditionally hard-blocked candidate-covered factual pairs;
- clean first STANDARD active-ship / target ordering (`169/169` conditional exact-set, `162/162` strict exact-set, `15/15` informative target-rank controls).

The major remaining C5 mechanics are concentrated rather than broad:

1. reconstruct current-Host effective targetability state, especially cloak-like blockers (`Privateer Rob` and separate Bird `Super Spy` residuals);
2. promote the first selector only after those blockers close;
3. mutable target-list state after each battle;
4. survivor / destruction / capture continuation;
5. compose already-closed second-pass side reversal into mutable replay;
6. ship-to-planet repair boundary;
7. planet/base participation in the generated Host queue.

This is why combat is materially advanced even though C5 is not complete.

## Why end-to-end combat coverage is only ~20-25%

The current candidate-set v2 historical checkpoint is:

```text
factual unique pairs=1986
candidate-covered=428
conditional factual eligible=427 unresolved=1 blocked=0
strict factual eligible=420 unresolved=8 blocked=0
```

Thus only `428 / 1986 = 21.6%` of factual ship-vs-ship pairs currently reach the independently reconstructed candidate-set boundary. The low coverage is mostly an input/state reconstruction limitation, not a demonstrated error rate in the canonical eligibility rule.

Likewise position v3 predicts:

```text
factual ship occurrences=3204
position predicted=1810
position exact=1806
position mismatch=4
position uncovered=1383
```

So when the deterministic position layer makes a prediction it is highly accurate, but many special/stochastic movement cases still fail closed.

## Current C5 blocker state

Initial STANDARD target-order is already strongly supported **when the eligible set is correct**. The current reverse effort is therefore no longer primarily about ordering; it is about missing effective-state blockers.

Privateer Rob investigation has isolated three clean first-decision skips:

```text
360690/T57 ship46
360690/T57 ship280
360690/T83 ship98
```

The full prior-true stable Privateer mission9/cloak-capable population contains a large exact ordinary-cloak-reference fuel-debit signal:

```text
stable prior-true rows=1413
exact_reference_debit=545
zero_debit=90
other_debit=778
exact true_to_true=541/545
```

This is `CORPUS_OBSERVED + TESTED` correlation, **not** a promoted `Rob Ship consumes cloak fuel` mechanic.

The first cloak/fuel attribution runtime attempt on source `180429508419581cf5082bb5363e1b8c528dd14f` was invalid before execution because pytest collection failed with `ModuleNotFoundError: No module named 'tools'`. It produced no mechanics evidence (`tests rc=2`, `audit rc=99`). The test import regression is fixed on the active branch; the attribution gate remains pending rerun.

## Wider roadmap estimate

Approximate subsystem status for planning only:

```text
M0 deterministic skeleton:              ~90%+
M1 minimal sandbox / infrastructure:     ~80-90%
M2 economy / planetary Host:             ~35-50%
M3 warfare overall:                      ~65-75%
M4 race-specific mechanics:              ~35-50%
M5A historical corpus pipeline:          ~75-85%
M5B Nu compatibility / differential:     ~60-75%
M6 training / AI:                        intentionally later / not a completion target yet
```

`M3 warfare` is lower than the combat-only estimate because minefield lifecycle and several special/race interactions are not fully integrated end-to-end.

## Whole-NuHost estimate

A reasonable current engineering estimate is **~40-50% of the full reverse-engineering roadmap**.

The strongest completed/advanced areas are movement, deterministic combat replay, ship battle sequence evidence, precombat position reconstruction and combat ordering/eligibility research.

Large remaining areas include:

- planet economy and starbase/ship production;
- complete minefield lifecycle;
- general missions and special ship abilities integrated in Host order;
- diplomacy/Safe Passage/alliance semantics across every subsystem;
- full race-specific mechanics integration;
- observer/visibility/fog/shared-intel model;
- full-turn end-to-end differential validation;
- training environment only after simulator fidelity is sufficient.

Therefore the project is past the exploratory phase and already has a substantial reconstructed core, but it is **not** close to a complete NuHost clone yet.

## Branch integration note

At assessment time `main` has advanced independently with additional movement/Tow work. The C5 branch is intentionally long-lived and diverged. Do not interpret branch divergence as missing reverse progress: evaluate the union of merged `main` checkpoints plus the current draft C5 research branch. Integrate/rebase only as an explicit maintenance step, not during a historical mechanics gate.
