# C5 Host combat — unified ship pair-selection layer — runtime complete — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This checkpoint was originally created before runtime. It is now superseded by:

```text
docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md
docs/handoff/2026-09-09-combat-c5-factual-queue-selection-pending.md
```

## Runtime result

The exact targeted unit-composition gate ran on:

```text
7ac5d70a77f592dfd1d3660c237b244e61795305
```

and passed:

```text
........................................................ [100%]
tests rc=0
```

Suite:

```text
tests/test_combat_order.py
tests/test_combat_eligibility.py
tests/test_combat_selection.py
```

Therefore the canonical pair-level selection composition is now `TESTED`.

## Canonical API

```text
src/planets_lab/rules/combat/selection.py

ShipCombatSideInput
ShipCombatPairDecision
ShipCombatPairPhase
ShipCombatPrestandardKind
decide_ship_combat_pair(...)
```

The layer composes base eligibility, matching-FC/HWM, normal/reciprocal Priority Intercept, Bird C&I constraints, Intercept Interference, standard battle priority and Galactic Power while propagating unresolved dynamic state instead of inventing defaults.

## Boundary

This runtime is deterministic unit composition only. It does not prove that arbitrary co-located candidate pairs can yet be generated from historical state, and it is not a full Host queue differential.

The immediate gate is now the factual-positive ordinary ship queue audit in:

```text
docs/handoff/2026-09-09-combat-c5-factual-queue-selection-pending.md
```

Do not implement mutable queue selection until that factual queue runtime is understood.
