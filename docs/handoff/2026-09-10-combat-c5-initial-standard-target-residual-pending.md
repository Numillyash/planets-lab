# C5 Host combat — initial STANDARD target residual fuel gate

GitHub is the source of truth. PR #28 remains draft/open. Game `591478` remains excluded.

The initial target-order runtime is recorded in:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md
```

Exact-set scope is clean (`169/169` conditional and `162/162` strict first-pair exact; all `15/15` informative exact-set targets rank 1). Only two broad residuals remain, each caused by one extra reconstructed eligible target:

```text
360690/T83: active 264; extra target 98; factual target 190
511506/T94: active 496; extra target 202; factual target 332
```

Do not change target ordering from these rows.

## Current hypothesis

Candidate-set v2 still derives combat `has_fuel` from positive T-1 neutronium. Normal movement occurs before combat and can consume the final kt, so an arriving ship with post-movement fuel `0` may be falsely retained as combat-eligible.

Focused read-only diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_target_residual_audit.py
tests/test_combat_host_initial_standard_target_residual_audit.py
```

It evaluates only the two residual sites. For active, extra-target and factual-target ships it reports owner-current T-1 navigation/fuel/mass/order state and reconstructs ordinary normal-movement `fuel_required`, `fuel_used` and `postmove_fuel` with the existing `plan_full_normal_move(...)` machinery. T state is printed only as attribution/control.

Interpretation:

- `extra_target_postmove_fuel_zero=True` is direct support that the pair should have been blocked by the documented zero-fuel combat condition after movement;
- positive post-movement fuel means the fuel hypothesis does not explain that residual;
- unresolved projection is a coverage gap and must not be converted to zero fuel;
- transfers/MKT/special movement remain fail-closed confounders;
- no target selector or candidate-set semantics are changed by this diagnostic.

If both extras resolve to zero fuel, integrate safely reconstructed post-movement fuel into candidate inputs, rerun candidate-set v2 and initial-target gate, and require the broad residuals to disappear before promoting a canonical selector. Otherwise investigate the remaining blocker(s).