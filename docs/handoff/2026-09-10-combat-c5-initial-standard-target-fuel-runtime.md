# C5 Host combat — initial STANDARD target residual fuel runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded from ordinary promotion.

## Runtime

User runtime source:

```text
55ad7c5799f52d8bc703f3247cf7ed179dbb18f9
```

Artifact:

```text
artifacts/combat-c5-initial-target-residual-fuel-20260910-150055
```

Result:

```text
tests rc=0
audit rc=0
summary:
  target_sites=2
  rows_found=2
  missing_archives=0
  extra_target_postmove_fuel_zero=0
  extra_target_postmove_fuel_nonzero=2
  extra_target_postmove_fuel_unresolved=0
```

Resolved extra targets:

```text
360690/T83 ship98:
  T-1 fuel=45
  ordinary movement distance=0
  fuel_used=0
  reconstructed postmove_fuel=45

511506/T94 ship202:
  T-1 fuel=37
  ordinary normal-move fuel_used=8
  reconstructed postmove_fuel=29
```

The factual targets and active ships also retain positive reconstructed ordinary post-movement fuel.

## Conclusion

The post-movement zero-fuel hypothesis is rejected for both broad initial-target residuals. It is not a reason to modify candidate-set fuel semantics for these rows, and target ordering remains unchanged.

The runtime exposed a stronger shared clue instead:

```text
extra targets 98 and 202 both have raw mission=9
```

For the first residual, stationary ship98 changes visible fuel `45 -> 40` between T-1 and T without normal movement, which is compatible with the documented minimum ordinary cloak fuel cost. The factual target ship190 has only 4 kt at T-1 and changes owner by T. This motivates a focused Bird/Super-Spy/effective-cloak attribution gate rather than a target-order change.

For the second residual, ship202 also has mission=9 and survives under the same owner at the combat site while factual target332 changes owner by T. Race and hull capability must be resolved from the archive rather than inferred from owner slot.

Do not treat T state as a generic same-physical-ship oracle: post-combat build-slot reuse can reuse a destroyed Ship ID later in the same Host. T state is attribution/control only and must be identity-bounded.

## Next gate

Read:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-pending.md
```

Focused diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_target_cloak_residual_audit.py
tests/test_combat_host_initial_standard_target_cloak_residual_audit.py
```

It resolves archive race/hull identity, static cloak capability, T-1/T `iscloaked`, documented basic cloak fuel sufficiency and scalar VCR outcome for only the same two residual sites. It does not yet modify canonical pair eligibility.
