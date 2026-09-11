# C5 Host combat — combined initial STANDARD blocker projection runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Runtime

Source HEAD:

```text
96ce64a1cc3d7da7874f0e9f37dea1333531330c
```

Targeted tests:

```text
25 passed
```

Diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_combined_blocker_projection_audit.py
```

Artifact:

```text
artifacts/combat-initial-standard-combined-blocker-projection.json
```

## Baseline

The unchanged initial plain-STANDARD baseline still reports exactly four broad mismatch rows: strict + conditional profiles for each of the two known residual sites.

```text
strict broad sites=225
strict first_pair_exact=223
strict first_pair_mismatch=2
strict exact_set first_pair_exact=162/162

conditional broad sites=234
conditional first_pair_exact=232
conditional first_pair_mismatch=2
conditional exact_set first_pair_exact=169/169

unrelated baseline mismatches=0
```

The two mismatch sites remain:

```text
360690/T83: active264, predicted target98, factual target rank2
511506/T94: active496, predicted target202, factual target rank2
```

Each appears once in strict and once in conditional profile.

## Privateer overlay remains clean

The previously tested Privateer Rob ordinary-cloak overlay remains unchanged:

```text
overlay_rows=16
overlay_blocked=7
overlay_eligible=9
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
privateer_residual_profiles=2
privateer_residual_profiles_projected_fixed=2
bird_residual_profiles_overlay_affected=0
```

No prior Privateer acceptance condition regressed.

## Bird focused context remains clean

The focused Bird Super Spy context is reproduced inside the combined gate:

```text
focus_row_found=True
archive_found=True
race_conflicts=0
extra_ship_documented_effective_cloak_supported=True
factual_ship_documented_effective_cloak_supported=False
raw_prior_cloak_control_separates=True
```

Thus ship202 remains supported as the documented Super Spy ordinary-cloak blocker, while factual ship332 remains outside Super Spy scope despite also having archived prior `iscloaked=true`.

## Combined projection

All four original broad mismatch profiles project fixed:

```text
360690/T83 strict      -> Privateer projected fixed
360690/T83 conditional -> Privateer projected fixed
511506/T94 strict      -> Bird projected fixed
511506/T94 conditional -> Bird projected fixed
```

Counters:

```text
baseline_mismatch_examples=4
privateer_residual_profiles=2
privateer_residual_profiles_projected_fixed=2
bird_residual_profiles=2
bird_residual_profiles_projected_fixed=2
unrelated_baseline_mismatches=0
```

Acceptance:

```text
privateer_gate_still_clean=True
bird_context_gate_clean=True
privateer_residual_all_profiles_projected_fixed=True
bird_residual_all_profiles_projected_fixed=True
no_unrelated_baseline_mismatches=True
all_original_broad_mismatches_projected_fixed=True
```

## Evidence boundary

This runtime closes the **structural composition** of the two independently established directional initial-STANDARD targetability blockers. It does not yet promote a generic canonical cloak/targetability rule and does not alter `selection.py` or `queue.py`.

Durable conclusion:

```text
all known broad initial-STANDARD first-target mismatches
  = independently explained by scoped directional targetability state
  = 4/4 projected fixed
  = 0 unrelated broad mismatches
```

The next gate is population-wide Bird Super Spy opportunity testing, followed by a combined directional STANDARD targetability differential over the historical corpus. Only after those gates remain regression-free should targetability be wired into the canonical first STANDARD selector.
