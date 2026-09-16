# C5 directional STANDARD targetability — canonical wiring gate closed

GitHub branch: `agent/combat-c5-host-phase`

Population evidence gate: **PASSED**; see `2026-09-16-combat-c5-directional-targetability-population-runtime.md`.

Canonical pair-level wiring commits:

```text
1386966ff1a4674140b4ba5404602b8e94d535d8  combat: wire directional STANDARD targetability
c4701ebae04568fb74755ebf6c41c3c9bf159d2f  test: cover directional STANDARD targetability
```

Runtime gate: **PASSED** at source HEAD:

```text
606971df33aad68d6e1c2a998e24288bed49e538
```

Durable runtime:

```text
docs/handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md
```

## Production boundary

`ShipCombatSideInput` has one explicit pair-specific input:

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

## Runtime result

Targeted canonical tests were fully green. Population regression retained:

```text
supported_block_rows=10
supported_block_conflicts=0
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
baseline_mismatch_profiles=4
baseline_mismatch_profiles_fixed=4
privateer residual profiles=2/2 fixed
bird residual profiles=2/2 fixed
unrelated baseline mismatches=0
```

Every population acceptance flag passed and strict/conditional exact-set controls remained `162/162` and `169/169` respectively.

## Next composition layer

Pair-level wiring is no longer pending. The repository now proceeds to the bounded initial plain-STANDARD stack selector described in:

```text
docs/handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-pending.md
```

That layer consumes already-composed pair decisions. It does not invent upstream cloak state and does not yet model mutable survivor/destruction state.
