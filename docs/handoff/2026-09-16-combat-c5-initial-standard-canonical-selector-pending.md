# C5 initial plain-STANDARD canonical selector — pending runtime

Branch: `agent/combat-c5-host-phase`

Pair-level directional targetability is already runtime-validated; see:

```text
docs/handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md
```

## New production layer

The repository previously had no production first-pair stack selector. `src/planets_lab/rules/combat/queue.py` only contained repeated-pair side projection after a pair had already been selected.

New bounded production API:

```python
InitialStandardPairInput
InitialStandardSelection
select_initial_plain_standard(...)
```

Implementation commit:

```text
2f18cb6d2fe8edb5dd0d38ec9ec870a0bafbdefe  combat: add bounded initial STANDARD selector
```

Exports were added from `planets_lab.rules.combat` in:

```text
63fc0c87367685fd44c3dfa7e8c3cbf21109f200
```

## Evidence-scoped selector contract

Input is a complete pair-candidate set for one site after each pair has already been composed by `decide_ship_combat_pair`, including any pair-specific directional STANDARD targetability.

Within the verified **plain STANDARD** scope:

```text
first active = highest STANDARD Combat Priority ship with an eligible pair
first target = highest-priority eligible target for that active ship
```

Since smaller `standard_battle_priority_key` values are higher priority, the implementation chooses the lexicographic minimum:

```text
(active_priority, target_priority)
```

Known blocked pairs are ignored. Unknown pairs are **not** ignored: any unresolved pair makes the whole initial selection unresolved because it may outrank the apparent winner.

The bounded selector also fails closed if an eligible input is:

- pre-standard PIA/C&I rather than STANDARD;
- unsupported static priority;
- STANDARD with a side override/unresolved side assignment, including the currently separate Galactic Power stack-order branch;
- duplicated as the same unordered pair.

This keeps the new primitive within exactly the population for which active-then-target ordering was established.

## New unit coverage

```text
tests/test_combat_initial_standard_selector.py
```

Covers:

1. highest-priority active ship wins across independent pairs;
2. highest-priority target wins within the top active ship;
3. directional targetability can remove rank-1 target and expose rank-2 target;
4. reciprocal request preserves a pair when only one attack direction is suppressed;
5. unresolved pair fails the whole selection closed;
6. eligible pre-standard pair is not silently dropped;
7. Galactic Power side override remains outside the plain selector scope;
8. all-known-blocked set returns no engagement;
9. duplicate pair input fails closed.

## Corpus differential

New read-only diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_canonical_selector_audit.py
```

It deliberately reuses the existing `combat_host_initial_standard_target_audit.py` archive reconstruction and proven site-level baseline. An adapter converts the already-composed projected pair rows into the production selector API. No second archive/candidate reconstruction is implemented.

Comparison scope is only baseline `broad_comparable` / `exact_comparable`, where engagement is fully resolved, every eligible pair is plain STANDARD, static side orientation is resolved, factual positions are exact and the factual pair set is covered.

Acceptance requires for both `strict` and `conditional` profiles:

```text
broad_population_present=True
no_adapter_error_on_broad=True
no_canonical_unresolved_on_broad=True
canonical_broad_matches_legacy=True
exact_set_population_present=True
canonical_exact_set_matches_legacy=True
```

and globally:

```text
all_profiles_match=True
```

Expected baseline population from the already-established diagnostic:

```text
strict broad sites=225
strict exact-set sites=162
conditional broad sites=234
conditional exact-set sites=169
```

The corpus gate must produce zero production-vs-legacy selector mismatches on those comparable sites.

## Evidence boundary

This gate validates the **stack selection algorithm**, not new effective-cloak inference. It does not encode historical Advanced-Cloak ship IDs, T state or Host messages into production. Directional cloak/Rob/Super-Spy state remains an upstream pair-specific input.

After this selector equivalence gate passes, the next composition gate is to feed supported precombat effective-state reconstruction into pair inputs without using post-Host evidence. Only then should C5 move into mutable survivor/destruction state and second-pass queue mutation.
