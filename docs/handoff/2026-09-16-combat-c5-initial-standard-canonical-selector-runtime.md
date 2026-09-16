# C5 initial plain-STANDARD canonical selector — runtime PASSED

Branch: `agent/combat-c5-host-phase`

Production implementation:

```text
2f18cb6d2fe8edb5dd0d38ec9ec870a0bafbdefe  combat: add bounded initial STANDARD selector
```

Runtime/fix HEAD:

```text
0225ff7116ca662fdf7e079bedaf58482d7d9f4d
```

## Production API

`src/planets_lab/rules/combat/queue.py` exposes:

```python
InitialStandardPairInput
InitialStandardSelection
select_initial_plain_standard(...)
```

The selector consumes already-composed pair decisions for one battle site. It does not infer cloak, diplomacy, movement, mine, Glory, Loki or race-specific effective state.

Verified plain-STANDARD ordering:

```text
first active = highest STANDARD Combat Priority ship with an eligible pair
first target = highest-priority eligible target for that active ship
```

Equivalently, with smaller priority keys being stronger:

```text
min(active_priority, target_priority)
```

Known blocked pairs are omitted. Any unresolved candidate, eligible pre-standard pair, unsupported priority, duplicate pair or STANDARD side override causes the bounded selector to fail closed rather than silently dropping a potentially higher-priority candidate.

## Corpus differential

Diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_canonical_selector_audit.py
```

It reuses the established `combat_host_initial_standard_target_audit.py` reconstruction and compares the new production selector against the previously proven diagnostic selector on exactly the broad/exact comparable population.

Observed runtime:

```text
strict:
  legacy_broad_sites=225
  canonical_broad_exact=225
  legacy_exact_sites=162
  canonical_exact_set_exact=162

conditional:
  legacy_broad_sites=234
  canonical_broad_exact=234
  legacy_exact_sites=169
  canonical_exact_set_exact=169
```

No adapter errors, canonical unresolved rows or selector mismatches occurred on the comparable population.

Acceptance:

```text
strict:
  broad_population_present=True
  no_adapter_error_on_broad=True
  no_canonical_unresolved_on_broad=True
  canonical_broad_matches_legacy=True
  exact_set_population_present=True
  canonical_exact_set_matches_legacy=True

conditional:
  broad_population_present=True
  no_adapter_error_on_broad=True
  no_canonical_unresolved_on_broad=True
  canonical_broad_matches_legacy=True
  exact_set_population_present=True
  canonical_exact_set_matches_legacy=True

all_profiles_match=True
```

## Unit/regression runtime

The first targeted run exposed only a synthetic fixture issue: the adapter unit helper omitted `race_id`/`hull_id`, leaving Galactic Power state unresolved. Real corpus rows contained the required state and the corpus differential was already fully green.

Fixture-only fix:

```text
0225ff7116ca662fdf7e079bedaf58482d7d9f4d  test: resolve synthetic Galactic Power state in selector adapter
```

After that fix the targeted selector suite completed with:

```text
.................................................. [100%]
```

No production selector or corpus diagnostic code changed after the green corpus differential.

## Evidence status

```text
initial plain-STANDARD stack selector:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

This status applies only to the bounded initial plain-STANDARD selection contract above. It does not promote Galactic Power stack ordering, pre-standard queue ordering, mutable survivor/destruction behavior, second-pass mutation or a generic predictive cloak resolver.

## Next gate

Feed supported **precombat-only** effective-state reconstruction into `ShipCombatSideInput.standard_targetable_by_opponent` without using post-Host `T`, VCR results or Host messages as production inputs.

Privateer ordinary Rob already has a production effective-state helper. Bird ordinary Super Spy currently has the required reconstruction logic only in diagnostics and must be promoted conservatively before stack composition can consume it. Advanced Cloak remains unresolved unless its dynamic precombat decloak path is independently reconstructed.
