# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This file is intentionally a compact pointer. Detailed evidence is in dated handoffs and Git history.

## Stable C5 evidence

- 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.
- Ordinary factual queue: 3,132 sites; ship combat precedes planet combat in all observed ordinary queues.
- Owner-current `T-1` is the pre-combat order source for battle turn `T`; `T` survivor state is post-combat.
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, raw `enemy = Primary Enemy`.
- Direct isolated standard classification remains 413/413 right-higher after documented special branches are removed.
- Factual isolated C&I attacker is 7/7 right.
- Ordinary linked normal-PIA pairs are 37/37 before regular ship combat and 37/37 with the PIA attacker on the right.

## Latest detailed checkpoints

Read first:

- `docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md`
- `docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-factual-queue-selection-pending.md`

## Former mission-7 residuals — removed from standard tuning

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Galactic Power forced-left Gorbie
```

Case 1 is closed for pair/pre-standard attribution as `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; the single reciprocal-only corpus row is insufficient to promote a universal reciprocal-specific side rule.

Case 2 is closed as the Standard-game Evil-Empire Gorbie Galactic Power forced-left exception. Do not weaken standard priority, Intercept semantics, diplomacy or FC parsing to fit either former residual.

## Matching Friendly Code / HWM — bounded

Positive runtime found 55 factual same-FC ship battles: all 54 ordinary rows plus the one `591478` row are documented MKT/LFM exceptions. No ordinary exact-match HWM candidate exists; NTP is simply unobserved in the current corpus.

Strict suppression runtime on source `8bef008342c8760e6f33d450335f1b3fb95443bf` passed tests/audit with zero payload conflicts but produced no clean negative-control population:

```text
stationary_colocated_pairs=199341
different_owner_pairs=21307
ordinary_exact_matching_fc_pairs=11
hostile_order_pairs=1
resolved_nonbird_pairs=1
known_noncloaking_pairs=0
strict_directed_relation_pair_vcr_absent_rows=0
strict_isolated_no_ship_vcr_rows=0
same_turn_directed_relation_rows=0
same_turn_directed_relation_isolated_rows=0
```

Evidence status:

```text
matching-FC suppression text:                DOCUMENTED
MKT/NTP/LFM exception text:                  DOCUMENTED
matching-FC/HWM eligibility primitives:      TESTED
55 factual same-FC VCR rows:                 CORPUS_OBSERVED
54/54 ordinary factual rows MKT/LFM:         CORPUS_OBSERVED
ordinary HWM factual support:                NOT PRESENT IN CURRENT CORPUS
ordinary exact matching-FC suppression:      DOCUMENTED + TESTED
historical suppression differential:         NOT AVAILABLE IN CURRENT CORPUS
```

Do not reopen this gate merely to relax controls unless future end-to-end evidence contradicts the documented rule or new historical data adds a clean pair.

## Unified pair-level selection — RUNTIME COMPLETE

User runtime on source:

```text
7ac5d70a77f592dfd1d3660c237b244e61795305
```

Artifact:

```text
artifacts/combat-c5-pair-selection-20260909-201758
```

passed:

```text
tests/test_combat_order.py
tests/test_combat_eligibility.py
tests/test_combat_selection.py
........................................................ [100%]
tests rc=0
```

Therefore `src/planets_lab/rules/combat/selection.py` and the canonical pair-level composition are now `TESTED`.

The API exposes:

```text
ShipCombatSideInput
ShipCombatPairDecision
ShipCombatPairPhase
ShipCombatPrestandardKind
decide_ship_combat_pair(...)
```

Dynamic facts remain explicit tri-state inputs: combat eligibility, directed diplomacy/Safe Passage, HWM enablement, C&I enablement, modern C&I hull eligibility, active cloak at the Intercept step, Intercept Interference protection and Galactic Power enablement. The runtime validates composition/fail-closed propagation only; it is not a historical candidate-set differential.

## Immediate runtime gate — factual ship-vs-ship queue differential

Committed, **not yet user-runtime-validated**:

```text
tools/diagnostics/combat_host_factual_queue_selection_audit.py
tests/test_combat_host_factual_queue_selection_audit.py
```

Schema:

```text
planets-lab.combat-host-factual-queue-selection-audit.v1
```

This gate consumes actual ordinary ship-vs-ship VCR queues and the canonical pair-selection API. It deliberately does **not** claim to predict pair existence.

Two scopes are reported:

1. `strict` — directed diplomacy is supplied only from a different one-sided factual combat under the same unique T-1 relation signature and aggression direction; otherwise it remains `None`;
2. `conditional` — for a factual VCR only, raw Kill!/PE requests are treated as effective so phase/side composition can be measured conditional on an engagement that already happened.

Additional dynamic boundaries remain fail-closed:

- Intercept Interference is false when no same-owner SSC/SSC-II began at the target's T-1 position; a source is treated as active only in the previously public-verified Standard game contexts, false in verified Classic, and unknown otherwise;
- the prior public game-context mapping supplies Galactic Power state only for the six already audited Empire-Gorbie games;
- mission20 establishes the historical C&I order, but modern buildable-hull eligibility and active cloak at the later Intercept step remain unresolved from T-1 alone.

The audit reports row-level phase/side results, unresolved reasons, site-level pre-standard prefix consistency, normal-PIA reverse-ID comparables, and explicit Case1/Case2 rows. Game `591478` is excluded.

## Next order

1. run the factual queue selection tests/audit;
2. if the resolved rows show coherent phase/side behavior, design candidate-set prediction from reconstructed post-movement stacks;
3. only after candidate-set evidence, implement mutable queue selection;
4. handle capture/reinsertion and ownership changes;
5. place between-phase repair before ship-vs-planet combat;
6. integrate planet/base participation using C4 persistence;
7. keep game `591478` separate.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
