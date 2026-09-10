# Finite-fuel Tow passenger-Chunnel incomplete runtime — 2026-09-10

This records the first server attempt of the bounded passenger-Chunnel / special-relocation gate after the classic multi-root storm audit.

## Runtime provenance

- repository candidate: `16eb3c4c3ddf6bedb24ec8696a2e5e0aed213af7`
- source multi-root gate: `logs/finite-fuel-tow-classic-multiroot-20260909T213519Z-4f2dfa83-22450`
- collected failed gate: `logs/finite-fuel-tow-passenger-chunnel-20260910T102745Z-16eb3c4c-31144`

The input and tooling stages completed successfully. The passenger-Chunnel stage processed games `360690` and `511506`, then stopped before processing game `620694` because `extract_stable_chunnel_abilities()` reported that the first/last archive Chunnel ability catalogs were not identical.

Observed partial output before the stop:

```text
game 360690: 6 cases, all lead:no_chunnel_lead
game 511506: 2 cases
  lead:same_destination_observed_chunnel_only=1
  lead:structural_origin_chunnel=1
  rows_with_observed_chunnel_destination=2
  rows_with_structural_origin_chunnel=1
```

This is an **incomplete runtime**. The partial counters must not be treated as nine-row accounting and do not change finite-fuel Tow evidence status.

## Diagnostic correction

`extract_stable_chunnel_abilities()` already returns the intersection of the first/last ability sets together with `ability_sets_consistent`. The first version of the passenger-Chunnel diagnostic incorrectly converted `ability_sets_consistent=false` into a fatal error.

The corrected gate keeps the stable intersection as a conservative catalog for positive evidence. It records changed-catalog games explicitly and, when a row in such a game otherwise has no Chunnel lead, classifies it as `ability_catalog_changed_unresolved` rather than a negative `no_chunnel_lead`. This preserves fail-closed evidence semantics: a changing catalog may hide a turn-specific ability, so absence of a match under the stable intersection is not treated as exclusion.

No `planets-intel` change is implied. Finite-fuel Tow remains **OPEN** pending a completed corrected runtime.
