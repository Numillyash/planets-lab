# Damage-limited warp verified; current fuel follow-up

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **strict damage-limited maximum warp is now DOCUMENTED (legacy Nu help page) + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED. The current final movement endpoint is 2226 rows / 769 generic rows, and the next focused task is a current-endpoint fuel-proration differential over the surviving 119-row short-forward family.**

This handoff supersedes `2026-08-25-damage-limited-warp-runtime-verification.md` for active work. Route-equivalent Tow, Chunnel multiplicity, strict mine/web context, classic/cloudy ion storms, scoped sphere topology and Red Mite remain closed absent fresh contradictory evidence.

## Runtime-verified movement accounting

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13970
post_external_residual              3924
chunnel_explained                   1421
post_chunnel_residual               2503
horwasp_strong_explained             240
post_horwasp_strong_residual        2263
mine_strong_explained                 37
post_mine_strong_residual           2226
label_issues                           0
```

Strict L1 category:

```text
damage_limited_warp_match  10
```

The production build reproduced the independent pre-build prediction exactly:

```text
ACCOUNTING DIFFERENTIAL: EXACT MATCH
```

## Damage-limited differential closure

Independent pre-build audit on the old 2236 endpoint found:

```text
raw_damage_limited                  11
raw_damage_limited_endpoint_exact   10
raw_exact_low_supply                10
raw_not_damage_limited_endpoint_exact_control  0
undamaged_endpoint_exact_control               0
```

The 10 exact rows spanned 9 games, 8 hulls, 6 races and effective maximum warps 1, 3, 4, 5, 6, 7 and 8. Only 2 belonged to the then-121-row dominant short-forward family.

Production requires all of:

```text
still unresolved after previous L1 contexts
non-Horwasp hull
resolved owner/race
same ship identity after transition
requested warp 1..9
visible supplies < 5 KT
raw-damage maximum warp < requested warp
exact Host-major/minor endpoint at that effective warp
```

Repair-bracket-only rows remain evidence-only.

Post-build audit confirmed complete removal of the strict subset:

```text
raw_damage_limited_endpoint_exact   0
raw_exact_low_supply                0
raw_not_damage_limited_endpoint_exact_control  0
undamaged_endpoint_exact_control               0
```

One damaged/limited residual remains, but it is not an exact endpoint match and therefore correctly stays unresolved.

## Tests

Runtime verification:

```text
targeted regression set: 27 passed
full pytest suite:        green
```

## Cache behavior

L1 semantic marker migration to:

```text
planets-lab.compiled-movement-storm-context.v3
```

correctly invalidated every L1 partition:

```text
compiled_cache_hits                0
compiled_cache_misses             12
prepared_cache_hits_on_compile    12
prepared_cache_misses_on_compile   0
```

L2 result was:

```text
compiled_label_cache_hits           3
compiled_label_cache_misses         9
prepared_cache_hits_on_compile      9
prepared_cache_misses_on_compile    0
```

This is correct. L2 cache validity is bound to `label_schema`, `source_movement_schema`, archive/settings identity and the exact source movement Parquet SHA-256. Physical L1 schema remained `planets-lab.compiled-movement.v3`. Three rebuilt games produced byte-identical source Parquet because the new damage pass changed no row in those partitions, so their existing L2 labels remained valid and were reused. The other nine source hashes changed and correctly missed.

Do not change the cache contract to force misses when source bytes and source schema are unchanged.

## Post-build generic rebaseline

```text
final_residual_rows       2226
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               769
generic_games               12
generic_hulls               76
```

Main coarse signatures:

```text
119  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 45  warp7-9 0.5-1.0x observed=other same_line_forward
```

The damage pass changed the dominant family only `121 -> 119`, exactly as predicted.

## Next focused task: current-endpoint fuel proration

Diagnostic:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

Previously it was hard-wired to `movement_post_horwasp_strong_residual`, so its old pre-damage population counts are no longer directly reproducible from the current L1 corpus and must be treated as historical recorded evidence only.

It is now parameterized. Default current final stage:

```text
--residual-view movement_post_mine_strong_residual
```

Optional earlier L2 stage on the **same current L1 corpus**:

```text
--residual-view movement_post_horwasp_strong_residual
```

This option is not a frozen historical snapshot and must not be described as reproducing the old pre-damage audit exactly.

The audit also now reports the exact current coarse family independently:

```text
target_short_forward_rows = 119   # expected population guard
```

and breaks fuel evidence down inside that family:

```text
target_short_gravitonic_excluded
target_short_non_gravitonic
target_short_fuel_geometry_candidate
target_short_same_identity_after
target_short_formula_ready
target_short_insufficient_for_regular
target_short_formula_brackets_observed
target_short_affordable_frontier_match
target_short_depleted_after
target_short_strong_fuel_limit_signature
```

Strong fuel evidence still requires:

```text
same identity after transition
AND insufficient fuel for regular movement
AND observed movement affordable
AND observed distance near maximum affordable whole-light-year frontier
AND fuel after movement = 0
```

Raw snapshot mass remains a correlation input rather than a fully reconstructed pre-movement mass.

## Immediate work

1. pull current `main` and confirm clean status;
2. syntax-check `generic_fuel_limited_residual_audit.py`;
3. run it on the default current final view;
4. require `target_short_forward_rows = 119` as the population guard;
5. compare current strong fuel count against the historical recorded `7` signatures without assuming the old population can be reconstructed from current L1;
6. inspect how many current strong signatures are actually inside the 119-row family;
7. inspect hull/game spread and formula controls before any production change;
8. do not broaden fuel classification merely to maximize coverage.

## Guardrails

- Damage-limited warp is closed; do not broaden it to repair-bracket-only rows.
- Do not reinterpret damage-limit as the main cause of the remaining 119 short-forward rows.
- Keep Gravitonic fuel cases separate from the standard fuel formula audit.
- Do not reopen Tow/Chunnel/mine/Red Mite without new evidence.
- Do not generalize game `591478`'s 2170 effective sphere period.
- Preserve raw/private state locally and export only derived mechanical evidence.
