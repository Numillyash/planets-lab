# C5 Host combat — storm-aware T-1 position v3 pending runtime

Date: 2026-09-09

This checkpoint stages the full-corpus rerun after the bounded residual audit identified six exact classic ion-storm displacements.

## Why v3 exists

The v2 position audit independently predicted 1,810 ordinary factual ship occurrences and matched 1,800, leaving ten movement-position residuals. The bounded residual audit then showed that six of those ten are exact classic ion-storm drag under authoritative `nuionstorms=False`.

A residual-only patch is not acceptable: adding storm mechanics can also change rows that were previously exact. Therefore the entire ordinary factual position population must be rerun with the storm phase integrated before candidate-set v2.

## Implementation

Canonical reusable helper:

```text
src/planets_lab/corpus/movement_storm_context.py
storm_offset_for_mode(...)
```

The helper exposes the already-validated deterministic storm vector without consuming factual post-turn coordinates:

- no storms -> `(0,0)` even if mode is unknown;
- `nuionstorms=True` -> existing cloudy/Nu offset logic;
- `nuionstorms=False` -> existing classic constant-voltage offset logic;
- non-empty storms + unknown mode -> fail closed;
- extreme unresolved storm transport -> fail closed through the existing offset semantics.

The existing `storm_expected_category_for_mode(...)` now composes through the same helper, preserving its classifier behavior.

Combat audit:

```text
tools/diagnostics/combat_host_normal_movement_position_audit.py
```

Schema:

```text
planets-lab.combat-host-normal-movement-position-audit.v3
```

The v3 order for ordinary self-movement is:

```text
T-1 raw ship/orders
-> strict effective requested warp
-> canonical Host normal navigation / Gravitonic distance
-> authoritative ion-storm drag
-> warp-well snapping
-> compare only against factual battle-site coordinate
```

Stationary ordinary ships also receive the authoritative storm vector because ion storms can move a ship whose own navigation displacement is zero.

Storm state is read from prepared historical snapshots for battle turn `T`, matching the existing movement-context convention; `nuionstorms` is resolved conservatively from archived mechanics payloads. Storm conflicts/invalid state fail closed.

The predictor still leaves the following outside this v3 scope:

- Tow actor/target movement;
- Intercept and Cloak & Intercept movement;
- HYP;
- obvious Chunnel source stacks;
- explicit inbound/outbound transfer mutation;
- MKT pre-movement mass mutation;
- sphere topology;
- fuel-prorated ordinary movement;
- random mine-hit outcomes unless a separate T-1-visible risk gate is later added.

## Required runtime gate

Run the canonical storm tests plus the combat position tests and then rerun the full ordinary position differential. Success requires:

1. all tests `rc=0`;
2. audit `rc=0`;
3. zero payload conflicts;
4. all six previously identified classic-storm rows become exact or otherwise safely uncovered for an independently justified reason;
5. no regression among the 1,800 previously exact occurrences;
6. any remaining mismatch population is fully enumerated and remains outside candidate-set v2.

Do not call the v3 combat-position layer `TESTED` or `DIFF_VERIFIED` before this runtime.

## After v3

If the full population is zero-mismatch or the only nonzero rows can be conservatively made `uncovered` from T-1-visible context, integrate the validated position sources into candidate-set v2.

If residuals remain predicted-but-wrong, investigate only those rows. Do not weaken combat eligibility, battle priority, Friendly Code, diplomacy, PIA/C&I or Galactic Power mechanics to absorb movement errors.

PR #28 remains open/draft/unmerged. Game `591478` remains excluded from ordinary tuning.
