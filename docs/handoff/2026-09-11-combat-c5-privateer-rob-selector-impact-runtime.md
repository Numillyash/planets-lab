# C5 Host combat — Privateer Rob selector-impact runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded from ordinary promotion.

Runtime source:

```text
5bfdecfc090357cd7f38fa69f9cb05d2c6aee611
```

Executed:

```text
tests/test_combat_effective_state.py
tests/test_combat_host_privateer_rob_effective_cloak_threshold_audit.py
tests/test_combat_host_privateer_rob_selector_impact_audit.py
tools/diagnostics/combat_host_privateer_rob_selector_impact_audit.py
```

Runtime result:

```text
targeted tests: 15 passed

overlay_rows=16
overlay_eligible=9
overlay_blocked=7
safe_first_selector_block_rows=7

blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0

privateer_residual_profiles=2
privateer_residual_profiles_projected_fixed=2
bird_residual_profiles=2
bird_residual_profiles_overlay_affected=0
```

Acceptance:

```text
no_blocked_factual_pair=True
no_potential_first_selector_regression=True
privateer_residual_all_profiles_projected_fixed=True
bird_residual_present_and_unaffected=True
```

Therefore the Privateer Rob effective-cloak threshold candidate is **TESTED + DIFF_VERIFIED at the scoped initial-STANDARD targetability boundary**.

## Unchanged baseline

The impact audit reran the unchanged full initial-STANDARD baseline before applying the overlay.

```text
strict broad:
  sites=225
  first_pair_exact=223
  first_pair_mismatch=2

strict exact-set:
  sites=162
  first_pair_exact=162
  first_right_exact=162

conditional broad:
  sites=234
  first_pair_exact=232
  first_pair_mismatch=2

conditional exact-set:
  sites=169
  first_pair_exact=169
  first_right_exact=169
```

The two broad mismatches in each profile remain the known Privateer and Bird initial target residuals before overlay.

## Privateer correction

For `360690/T83`:

```text
active ship:          264
baseline extra target: 98
factual target:        190
```

Both strict and conditional baseline profiles predict ship98 as the first target and rank the factual target second. The Rob effective-state overlay marks ship98 blocked and a single rank-1 removal projects the factual target into first place in both profiles.

```text
strict:      projected_fixed_by_single_rank1_removal=True
conditional: projected_fixed_by_single_rank1_removal=True
```

The same scoped model also explains the two earlier clean Privateer skip controls at `360690/T57` (ships 46 and 280).

## Regression controls

Seven overlay rows are blocked by the helper:

```text
blocked_outranking_skip_candidate_fix=3
blocked_lower_target_no_first_effect=3
blocked_noninitial_attacker_no_first_effect=1
```

No blocked row is a factual pair and no blocked lower-priority/noninitial row can change the current first selector under the tested queue shape.

This is the critical regression boundary:

```text
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
```

## Bird isolation

`511506/T94/ship202` remains the only other original broad initial-target blocker. The Privateer helper does not apply to it:

```text
strict Bird residual overlay affected=False
conditional Bird residual overlay affected=False
```

This is intentional. Bird Super Spy/effective-cloak state remains a separate workstream.

## Evidence-scoped Privateer state

The promoted scoped model remains:

```text
Privateer race5 + mission9 Rob + ordinary cloak-capable hull:
  prior iscloaked=false                 -> not effectively cloaked
  prior iscloaked=true and fuel <= cost -> not effectively cloaked
  prior iscloaked=true and fuel > cost  -> effectively cloaked
  advanced cloak                        -> unresolved / fail closed
```

The helper is implemented in:

```text
src/planets_lab/rules/combat/effective_state.py
```

Important architectural boundary: this does **not** establish a symmetric pair-combat blocker. The differential establishes a directional ordinary-STANDARD targetability effect: a supported effectively cloaked Rob ship is skipped as an enemy target. Do not turn `effective_cloak=True` into a blanket pair rejection, because a cloaked ship may have its own combat request and pre-standard phases have separate semantics.

## Next gate

Close the remaining Bird residual `511506/T94/ship202` using documented Super Spy cloak semantics plus archived dynamic context. Official Planets.nu documentation states that a Bird ship on Super Spy which can cloak attempts to cloak normally; inadequate fuel prevents the cloak but the Super Spy mission continues. Official Cloak documentation states that a cloaked ship is protected from enemy attack and that damage prevents cloaking.

Before canonical first-selector promotion, verify ship202's precombat damage/fuel/cloak type and relevant decloak context (ion/Loki/Glory or equivalent) without using T state as an input. Keep ship332 as the matched negative control demonstrating that raw `T-1 iscloaked=true` alone is not a blocker.
