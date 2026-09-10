# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

This is the compact current pointer; dated handoffs contain full evidence and runtime details.

## Stable C5 facts

- established corpus: 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts;
- ordinary Host ordering: ship combat precedes planet combat;
- owner-current `T-1` is the precombat order/state source for battle turn `T`; factual `T` ship state is postcombat;
- mission 3 = Kill!, mission 7 = Intercept, mission 20 = Bird Cloak and Intercept, raw `enemy` = Primary Enemy;
- direct isolated ordinary standard relation: 413/413 higher static priority on RIGHT after documented special branches;
- ordinary normal PIA linked population: 37/37 before regular combat and 37/37 attacker RIGHT;
- isolated C&I factual attacker: 7/7 RIGHT.

## Closed combat gates — do not reopen absent contradiction

```text
docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md
docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md
docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md
docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md
docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md
docs/handoff/2026-09-09-combat-c5-factual-queue-runtime.md
docs/handoff/2026-09-09-combat-c5-repeated-pair-side-runtime.md
```

Former standard-side residuals stay closed:

```text
511506/T19/VCR13 -> reciprocal Priority Intercept pre-standard pair
621896/T28/VCR67 -> Standard Galactic Power forced-left Evil-Empire Gorbie
```

Do not weaken standard priority, Friendly Code parsing, Intercept semantics or diplomacy to fit later queue residuals.

## Canonical pair / repeated-pair layers

```text
src/planets_lab/rules/combat/selection.py
```

Deterministic pair composition: `TESTED`.

```text
src/planets_lab/rules/combat/queue.py
standard_pair_sides_for_occurrence(...)
```

Runtime source `de824ab4ecc0bc8cd32784ce4d3df9021eddd71b` passed. Complete ordinary repeated-pair population is two groups/four VCRs; both have first RIGHT = static higher priority and second RIGHT = opposite ship. Scoped reversal is `CORPUS_OBSERVED + DIFF_VERIFIED`; static priority remains unchanged.

## Factual-positive queue differential — closed

Runtime source `31509d2c9e9f4af89f80e5088597452d40f393c1`:

```text
factual_ship_vcr_rows=1968
sites=1216
multi_vcr_sites=348
payload_conflicts=0
known phase-prefix violations=0
```

Existing VCR presence was a positive oracle in this gate, so it is not candidate-set prediction.

## Repaired T-1 -> precombat position layer — runtime checkpoint

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md
docs/handoff/2026-09-09-combat-c5-unresolved-movement-context-runtime.md
```

Runtime source `14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c`:

```text
tests rc=0
audit rc=0
payload_conflicts=0
storm modes: false=10 true=1

ship occurrences: factual=3204 predicted=1810 exact=1806 mismatch=4 uncovered=1383
factual pairs:     total=1986 exact=678 mismatch=4 unresolved=1304
sites:             total=1220 fully position-exact=346 mismatch sites=4
```

All six classic-ion-storm residuals from position v2 are independently exact in v3. Four rows remain bounded:

```text
360690/T54/ship26    -> unresolved
511506/T95/ship332   -> unresolved
620694/T62/ship83    -> stochastic normal-mine hit, DIFF_VERIFIED attribution
680910/T14/ship65    -> stochastic normal-mine hit, DIFF_VERIFIED attribution
```

No factual endpoint is injected into the predictor.

## Candidate-set v1 — closed as coverage-limited

Runtime source `1ef175f77419970b244c5d69df2863a06390ab6c` covered only `1/1986` factual pairs. Read `docs/handoff/2026-09-09-combat-c5-candidate-set-v1-runtime.md`.

## Candidate-set v2 — runtime complete

Read:

```text
docs/handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md
```

Runtime source:

```text
c804575f4275f4454dbb282d9fcfc99fad0700d6
```

Artifact:

```text
artifacts/combat-c5-candidate-set-v2-20260910-003515
```

Result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
factual unique pairs=1986
candidate-covered factual pairs=428
candidate-uncovered factual pairs=1558
candidate pairs=1092

strict factual:      eligible=420 unresolved=8 blocked=0
conditional factual: eligible=427 unresolved=1 blocked=0
conditional eligible nonfactual=331

all factual positions covered sites=242
conditional factual subset of eligible=236
conditional eligible exactly factual=171
strict factual subset of eligible=227
strict eligible exactly factual=164
```

The one conditional factual unresolved row is `360690/T140 [198,458]` with `left_fuel_unknown`; it is a coverage gap, not a contradiction.

Most important closure:

```text
candidate-covered factual pair conditionally hard-blocked = 0
```

Candidate-set v2 therefore gives a broad positive differential for canonical pair eligibility without using factual VCR existence as the positive eligibility input. `eligible_nonfactual` is not an error yet because target order and outcome mutation are not modeled.

## Immediate gate — initial plain-STANDARD target selection

Read:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-pending.md
```

New diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_target_audit.py
tests/test_combat_host_initial_standard_target_audit.py
```

Schema:

```text
planets-lab.combat-host-initial-standard-target-audit.v1
```

This is deliberately narrower than mutable queue replay. It reconstructs the same v2 candidate stack and compares only the **first plain STANDARD VCR before any battle outcome mutation**.

Primary documented order supports the hypothesis:

```text
first active ship = highest standard Combat Priority with an eligible target
first target      = highest-priority eligible target for that active ship
```

Strong comparison requires exact factual positions, resolved candidate engagements, only plain STANDARD eligible rows with supported static priority, no side override, and factual pairs contained in the eligible candidate set. An exact-set control additionally requires equality of the predicted eligible and factual unordered pair sets.

The audit reports strict/conditional broad and exact-set populations, first-pair/right exactness, pair/target ranks, and a deliberately wrong low-priority-target control.

If first-selection is clean, only then add a canonical selector and move to mutable survivor/destruction/capture continuation. Second-pass repeated-pair side reversal is already separately closed; capture continuation and ship-to-planet repair boundary remain later work.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.