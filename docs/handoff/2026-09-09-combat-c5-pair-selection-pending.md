# C5 Host combat — unified ship pair-selection layer pending runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

## Preceding boundary

Matching Friendly Code research is closed at the current corpus boundary:

- positive runtime: 55 factual same-FC ship battles, all documented MKT/LFM exceptions;
- strict suppression runtime: no clean negative-control population survives the non-cloaking/diplomacy filters;
- ordinary matching-FC suppression remains `DOCUMENTED + TESTED`, not historical `DIFF_VERIFIED`;
- no ordinary HWM factual candidate is present.

See:

- `docs/handoff/2026-09-09-combat-c5-matching-fc-positive-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-matching-fc-suppression-runtime.md`

## Objective

Move from isolated mechanics primitives to a small deterministic pair-level Host decision layer without yet implementing a mutable stack queue or pairwise combat resolution.

The layer must distinguish:

1. whether a candidate ship pair is known eligible / blocked / unresolved;
2. whether a documented pre-standard branch applies;
3. which ship is the phase attacker when attributable;
4. which left/right assignment is attributable;
5. which dynamic Host fact remains unknown when the answer cannot be established.

Unknown facts must propagate rather than be replaced by defaults.

## Committed canonical layer — pending runtime

New module:

```text
src/planets_lab/rules/combat/selection.py
```

Public API:

```text
ShipCombatSideInput
ShipCombatPairDecision
ShipCombatPairPhase
ShipCombatPrestandardKind
decide_ship_combat_pair(...)
```

`src/planets_lab/rules/combat/__init__.py` now exports the selection API and previously bounded order/eligibility primitives so future stack logic does not depend on diagnostic/internal imports.

Regression module:

```text
tests/test_combat_selection.py
```

Do **not** label the new selection layer `TESTED` before user runtime.

## Composition currently encoded

### Base engagement eligibility

Known blockers:

- same owner;
- different location;
- either ship known to have no fuel;
- ordinary exact matching Friendly Code when not overridden by documented exceptions/HWM;
- no effective Kill!/Primary-Enemy combat request from either side after directed diplomacy is applied.

Unknown co-location, fuel, matching-FC/HWM state or directed attack permission remains unresolved.

### Matching FC / HWM

Uses the already runtime-tested `matching_ship_friendly_code_blocks_combat(...)` and `harmonic_weapon_modulation_applies(...)` primitives. Effective HWM state remains an explicit input; Bird race alone does not imply activation.

### Normal Priority Intercept

Uses the bounded normal PIA signature and requires:

- effective directed attack permission for the interceptor;
- target not protected by Intercept Interference.

Known Intercept Interference demotes PIA priority to ordinary/standard combat; it does not cancel normal Intercept movement.

The pair-level normal-PIA attacker is assigned right based on the ordinary corpus boundary `37/37` linked PIA attackers on the right.

### Reciprocal Priority Intercept

Uses the documented reciprocal branch where the intercepted target would itself combat the interceptor.

The phase/pair attribution is known, but the new API deliberately does **not** promote a universal reciprocal-specific left/right rule: the current ordinary reciprocal-only population contains only Case1. Therefore a reciprocal-only decision reports the PIA phase and attacker but leaves sides unresolved with:

```text
reciprocal_priority_intercept_side_unverified
```

### Bird Cloak-and-Intercept

Requires all of:

- documented C&I order signature;
- effective C&I advantage enabled;
- explicit era/static `cloak_and_intercept_hull_eligible`;
- active cloak retained at the Intercept step;
- effective directed attack permission;
- target not protected by Intercept Interference.

The explicit hull-eligibility input is required because current Planets.nu documentation scopes modern C&I to hulls buildable by the Birds rather than every captured cloak-capable hull.

Known Intercept Interference breaks the C&I intercept lock; if the pair is otherwise co-located/hostile it may still fall through to standard combat.

The ordinary factual C&I attacker is assigned right only on the established `7/7` corpus boundary.

### Standard side assignment

Uses `standard_battle_priority_key(...)`; the higher-priority combatant is placed on the right. Unsupported numeric-looking FC shapes such as `000` keep standard phase known but side assignment unresolved.

### Galactic Power

Applies `galactic_power_forces_left(...)` after the base side assignment. Effective advantage state is still explicit and tri-state. An enabled Evil-Empire-owned Gorbie is forced left; unknown eligible GP state leaves sides unresolved. Dual forced-left remains fail-closed.

### Multiple / mixed pre-standard candidates

Two normal PIA candidates use the documented reverse Ship ID order. Mixed PIA/C&I/reciprocal combinations remain unresolved rather than being guessed.

## Regression coverage committed

`tests/test_combat_selection.py` covers:

- co-location and zero-fuel blockers;
- ordinary same-FC blocking;
- MKT exception;
- active/unknown Bird HWM;
- one-sided directed diplomacy blocking the sole aggressor;
- normal PIA and Intercept Interference demotion;
- reciprocal PIA with deliberately unresolved side;
- C&I enabled/active-cloak/hull-eligibility boundaries;
- Intercept Interference against C&I;
- standard priority/right-side assignment;
- Galactic Power forced-left and unknown state;
- two normal PIA attackers / reverse Ship ID order;
- unsupported `000` standard side failure.

## Runtime gate

Run only the canonical composition regressions:

```text
tests/test_combat_order.py
tests/test_combat_eligibility.py
tests/test_combat_selection.py
```

This gate is deterministic/unit-level. It is not a historical stack differential and must not be described as such.

If these pass, promote the pair-selection composition to `TESTED` and proceed to a factual stack-level queue audit. That audit should consume the pair-level API while keeping unavailable dynamic inputs explicit instead of hard-coding diagnostic assumptions into canonical mechanics.

## After runtime

1. build the stack-level ordinary queue audit over factual co-located states;
2. measure how much of factual PIA / reciprocal PIA / C&I / standard pair ordering is attributable with currently resolvable dynamic context;
3. only then implement a mutable stack queue;
4. handle capture/reinsertion;
5. place between-phase repair before ship-vs-planet combat;
6. integrate planet/base participation using C4 persistence.
