# C5 Host combat — mission-7 matched controls and Galactic Power gate — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains excluded from ordinary-mechanics tuning.

This handoff records the matched-control gate that rejected a universal non-cloakable Intercept side rule and identified Galactic Power as the specific documented mechanic to investigate for the remaining Gorbie/T-Rex row.

For the subsequent user-operated Gorbie corpus runtime and its important mixed enabled/disabled-context result, continue with:

```text
docs/handoff/2026-09-09-combat-c5-galactic-power-runtime.md
```

## Matched-control runtime

Source:

```text
b1335ea6032a356c12be13be2c4fdb8cbc46b011
```

Result:

```text
targeted tests: 4 passed
archives_considered: 11
payload_conflicts: 0
candidate_rows: 41
target_case_rows: 1
control_rows: 40
standard_relation:
  right_higher_priority: 40
  left_higher_priority:   1
interceptor_side:
  right: 22
  left:  19
exact_case2_shape_relation:
  right_higher_priority: 2
  left_higher_priority:  1
numeric_vs_symbolic_nonkill_relation:
  right_higher_priority: 6
  left_higher_priority:  1
no_t_extra_survivor_relation:
  right_higher_priority: 30
  left_higher_priority:   1
tests rc=0; audit rc=0
artifact dir: artifacts/combat-c5-mission7-controls-20260909-003724
```

## Conclusion

The sole contradiction is exactly:

```text
game 621896 / battle T28 / VCR67
LEFT  ship62 owner5 race8 hull70 Gorbie
      mission7 target38 PE2 FC001
RIGHT ship38 owner2 race2 hull23 T-Rex
      mission1 PE5 FCeqe damage24
```

The target remains unique under exact `001`-vs-symbolic-nonKill and no-extra-T-survivor controls. Therefore:

- `mission=7` itself is not a forced-left/right rule;
- non-cloakable targeted Intercept with matching PE is not a general pre-standard side phase in this population;
- FC `001` versus symbolic non-Kill does not explain the row;
- standard priority must not be weakened.

Primary Planets.nu documentation identifies **Galactic Power** as a forced-left rule for an Evil-Empire-owned Gorbie when the advantage is active, matching the target's race/hull/factual side signature.

At this checkpoint Galactic Power was therefore the leading specific explanation, but effective game advantage state remained unresolved. The subsequent Gorbie corpus runtime proved that this distinction is essential: many Evil-Empire-owned Gorbies in the corpus fight from the right, so race8+hull70 alone cannot establish enablement.

## Canonical primitive

`src/planets_lab/rules/combat/order.py` contains a tri-state, fail-closed `galactic_power_forces_left(...)` helper that requires explicit effective `galactic_power_enabled` state.

Do not widen it based on race/hull alone. See the subsequent runtime handoff for the current evidence boundary.
