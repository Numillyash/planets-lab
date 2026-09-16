# C5 directional STANDARD targetability — canonical wiring pending runtime

GitHub branch: `agent/combat-c5-host-phase`

Population evidence gate: **PASSED** at source HEAD `23e3b672d4e7c513f348eefd3d0493cc7e21cfef`; see `2026-09-16-combat-c5-directional-targetability-population-runtime.md`.

Canonical pair-level wiring commits:

```text
1386966ff1a4674140b4ba5404602b8e94d535d8  combat: wire directional STANDARD targetability
c4701ebae04568fb74755ebf6c41c3c9bf159d2f  test: cover directional STANDARD targetability
```

## Production boundary

`ShipCombatSideInput` now has one explicit pair-specific input:

```python
standard_targetable_by_opponent: bool | None = True
```

Semantics: this side may be selected as the target of the *other side's ordinary STANDARD attack request*.

The default is `True` so existing ordinary non-cloak callers are unaffected. An upstream branch which has identified a potentially-cloaked target must explicitly provide:

```text
True  -> targetable in ordinary STANDARD combat
False -> opponent's ordinary STANDARD request against this side is suppressed
None  -> targetability unresolved; fail closed if that is the only possible STANDARD request
```

This field is deliberately **not** an `effective_cloak` flag. Race/mission/fuel/mine/Glory/Loki reconstruction stays outside pure pair composition.

## Ordering invariant

The implementation order is:

```text
base pair blockers / directed order+diplomacy requests
    -> PIA / reciprocal PIA / C&I classification
    -> only if no pre-standard branch applies:
       filter each directed STANDARD request by the opponent's targetability
    -> STANDARD side assignment / Galactic Power handling
```

Consequences:

- targetability is not added to `_base_engagement`;
- PIA/C&I behavior is unchanged;
- targetability is directional, not a symmetric pair blocker;
- a non-targetable ship's *own* attack request remains intact;
- if one direction is suppressed but the reciprocal request survives, ordinary STANDARD combat still occurs;
- unknown targetability cannot silently become `True` for an explicitly unresolved potentially-cloaked branch.

## New unit coverage

`tests/test_combat_standard_targetability.py` covers:

1. sole ordinary aggressor cannot attack a non-targetable opponent;
2. bidirectional pair remains eligible when only one direction is suppressed;
3. unknown targetability fails closed for the sole request;
4. normal Priority Intercept remains pre-standard despite STANDARD non-targetability;
5. Cloak & Intercept remains pre-standard despite STANDARD non-targetability;
6. default targetability preserves existing ordinary STANDARD behavior.

The existing `tests/test_combat_selection.py` must also remain fully green.

## Runtime gate

Run at least:

```text
tests/test_combat_selection.py
tests/test_combat_standard_targetability.py
tests/test_combat_host_initial_standard_directional_targetability_audit.py
```

Then rerun `combat_host_initial_standard_directional_targetability_audit.py` and require the previously passed population acceptance to remain all true.

This runtime proves the pair-level canonical primitive does not regress prior C5 composition. It does **not** claim that a production stack queue already reconstructs every upstream cloak state: the stack-level target-list/queue remains the next composition layer.
