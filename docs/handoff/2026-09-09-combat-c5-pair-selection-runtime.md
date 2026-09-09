# C5 Host combat — unified ship pair-selection runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

## Runtime source

User runtime was executed on:

```text
7ac5d70a77f592dfd1d3660c237b244e61795305
```

Artifact:

```text
artifacts/combat-c5-pair-selection-20260909-201758
```

Runtime result:

```text
===== PAIR-SELECTION TESTS =====
........................................................ [100%]

tests rc=0
```

The exact targeted suite was:

```text
tests/test_combat_order.py
tests/test_combat_eligibility.py
tests/test_combat_selection.py
```

This is a deterministic unit-composition gate, not a historical stack differential.

## Promotion

The canonical pair-level Host decision composition is now `TESTED`.

Canonical files:

```text
src/planets_lab/rules/combat/order.py
src/planets_lab/rules/combat/eligibility.py
src/planets_lab/rules/combat/selection.py
src/planets_lab/rules/combat/__init__.py
```

The selection layer exposes:

```text
ShipCombatSideInput
ShipCombatPairDecision
ShipCombatPairPhase
ShipCombatPrestandardKind
decide_ship_combat_pair(...)
```

## Tested composition boundary

The green suite covers composition of the already bounded mechanics:

- same-owner, co-location, fuel and directed Kill!/Primary-Enemy request boundaries;
- exact matching Friendly Code blocker and documented MKT/NTP/LFM exceptions;
- Bird Harmonic Weapon Modulation explicit enablement/unknown propagation;
- normal Priority Intercept and Intercept Interference demotion;
- reciprocal Priority Intercept phase attribution with side deliberately unresolved;
- Bird Cloak-and-Intercept explicit advantage, active-cloak and modern hull-eligibility inputs;
- C&I Intercept Interference failure/fall-through;
- standard battle priority/right-side assignment;
- Galactic Power forced-left and unknown-state propagation;
- reverse Ship ID handling when both pair members are normal PIA candidates;
- unsupported standard Friendly Code shapes such as `000` failing closed for side assignment.

This does not mean all dynamic Host inputs are reconstructed. The following remain explicit tri-state inputs and must not be guessed by stack logic:

```text
same-location fact for arbitrary candidates
post-movement combat fuel state
directed diplomacy / Safe Passage
HWM effective enablement
C&I effective enablement
C&I era/static hull eligibility
active cloak at the Intercept step
Intercept Interference protection
Galactic Power effective enablement
```

## Immediate next gate — factual ship queue differential

Build a read-only ordinary historical audit over factual ship-vs-ship VCR queues that consumes `decide_ship_combat_pair(...)` without claiming to predict pair existence yet.

The first stack-level audit must distinguish two scopes:

1. **strict attributable scope** — dynamic facts such as directed diplomacy are supplied only when independently controlled; unresolved rows stay unresolved;
2. **conditional factual-positive scope** — factual VCR presence is used only as an oracle that the pair reached combat eligibility, so the audit can measure phase and side composition conditional on an engagement that actually occurred. This scope must never be described as predicting the VCR set.

The audit should report, per factual ship-vs-ship VCR row and per site queue:

- pair decision phase (`priority_intercept`, `cloak_intercept`, `standard`, unresolved);
- pre-standard kind;
- side assignment exact/mismatch/unresolved;
- unresolved-reason inventory;
- whether resolved pre-standard rows form a factual prefix before resolved standard rows;
- normal-PIA attacker order where comparable;
- explicit Case1 reciprocal and Case2 Galactic-Power checks;
- special game `591478` excluded.

Do not implement a mutable Host queue until this factual queue gate establishes that the pair-level API composes sensibly across real multi-VCR sites.

## Evidence status

```text
pair-level selection composition: TESTED
historical factual queue differential: NOT YET RUN
candidate-set prediction: NOT YET IMPLEMENTED
mutable Host combat queue: NOT YET IMPLEMENTED
```
