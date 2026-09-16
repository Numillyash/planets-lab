# C5 mutable ship queue — pending runtime

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 remains draft/open. Game `591478` remains isolated.

## Preconditions already closed

The following are not part of this gate and should not be reopened absent contradiction:

- C3 noncaptured ship state carry-over: `TESTED + DIFF_VERIFIED` on the clean owner-certain chain subset;
- ordinary repeated STANDARD pair second occurrence side reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- pair-level directional STANDARD targetability: runtime passed;
- initial plain-STANDARD production selector: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- ordinary Privateer Rob and ordinary Bird Super Spy precombat targetability are production-ready in their tested scopes.

Latest effective-state runtime:

```text
docs/handoff/2026-09-16-combat-c5-production-effective-state-runtime.md
```

## New production primitive

Module:

```text
src/planets_lab/rules/combat/mutable_queue.py
```

API:

```python
ShipQueueMutationResult
apply_ship_terminal_batch(...)
```

Implementation commits include:

```text
df0052933213eb76029dd4541599909f69c46fa3  combat: add atomic ship queue mutation
ce4b553e1760e567243d5a8a7c075854ca8f711f  combat: fail closed on incomplete survivor state
f93cd9b10d2b03dcdf555f1b9f73d2c0618eb651  combat: export mutable queue mutation
```

The primitive receives the current active ship map plus terminal states for a resolved ship combat. It does not infer terminal results.

Supported mutation:

```text
destroyed=True, captured=False
  -> remove ship from active map

survivor: destroyed=False, captured=False
  -> require complete C3 dynamic vector
     shield/damage/crew/torpedoes/fighters
  -> carry via carry_ship_to_next_engagement(...)

captured=True
  -> unresolved / fail closed
```

## Atomicity

Mutation is all-or-nothing.

If any terminal has:

- `captured=True`;
- missing/non-boolean destroyed/captured flags;
- incomplete/non-integer survivor carry state;
- a carry transition error;

then the original active map is returned unchanged and no sibling deletion/carry is committed.

This avoids continuing the Host queue from partially applied combat outcomes.

## Unit coverage

```text
tests/test_combat_mutable_queue.py
tests/test_combat_host_mutable_ship_queue_audit.py
```

Covers:

- destroyed removal + survivor carry + unrelated ship preservation;
- two surviving combatants;
- reuse of the C3 Federation between-combat shield recovery;
- capture atomic fail-closed;
- unknown terminal flags;
- incomplete survivor vector;
- inactive terminal programming error;
- corpus adapter projection for survivor/destroyed/captured/unknown states.

## Corpus transition diagnostic

```text
tools/diagnostics/combat_host_mutable_ship_queue_audit.py
```

It reuses `tools/diagnostics/combat_ship_chain_audit.py` rather than rebuilding VCR replay.

For every same-turn same-location reappearance transition, it projects the predecessor replay terminal through the production mutable-queue primitive.

Scope:

```text
survivor predecessor
  -> production must remain resolved and ship must remain active

captured predecessor
  -> production must be unresolved and retain baseline membership atomically

destroyed predecessor followed by another factual VCR
  -> production must remove it; the factual reappearance is surfaced as an
     explicit control/contradiction candidate rather than normalized away
```

The exact dynamic terminal->next-start field match remains the independent C3 differential's responsibility. This gate tests C5 membership/continuation only.

Absence of destroyed-reappearance rows is **not** treated as independent proof of destruction ordering; destruction removal is unit-tested mechanically and any informative corpus rows are reported separately.

Required acceptance:

```text
survivor_population_present=True
survivor_membership_exact=True
capture_fail_closed_if_observed=True
destroyed_removal_if_reappearance_observed=True
no_production_mutation_errors=True
no_terminal_flag_unknowns=True
mutable_ship_queue_transition_gate_passed=True
```

## Explicit exclusions

This gate does not yet model:

- next-pair selection after mutation;
- occurrence counting or second-pass eligibility;
- capture ownership/hostility continuation;
- ship-to-planet / planet-base queue insertion;
- post-Host T as queue input.

## Next gate if green

Compose active membership mutation with the already-tested initial selector and repeated-pair occurrence-aware side helper, then differentially validate the second ordinary STANDARD queue step.

Capture remains a separate branch and must not be silently treated as destruction.
