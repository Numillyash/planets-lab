# Route-equivalent visible Tow — verified closure

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **TESTED + DIFF_VERIFIED**.

This handoff supersedes `2026-08-24-route-equivalent-tow-runtime-verification.md` for the active movement/corpus state. Mine/web v5, Chunnel v4, classic ion storms, scoped sphere topology and Red Mite remain closed absent fresh evidence.

## Verified source state

The L1 Tow detector now treats every non-empty route-equivalent set of owner-visible Tow towers as movement-route evidence when all counted towers:

- target the same ship with Tow;
- are colocated with that target before movement;
- end at the same non-stationary observed destination as the target.

Multiple matching towers preserve tower-identity ambiguity. Production does not choose or export an arbitrary Tow winner.

Current schemas:

```text
movement residual context:
  planets-lab.movement-residual-context-game.v2
  planets-lab.movement-residual-context-stats.v2

compiled L1 movement:
  planets-lab.compiled-movement.v3

compiled L2 labels:
  planets-lab.compiled-movement-context-labels.v5
```

The L1 v2 -> v3 bump is a semantic cache marker; physical columns did not change. L2 remains v5 because label predicates did not change, but its cache correctly invalidates through `source_movement_schema` and exact source movement Parquet SHA-256.

## Global pre-build differential

Diagnostic:

```text
tools/diagnostics/tow_route_equivalent_global_differential_audit.py
```

The audit scanned all old `3938` L1 external residual rows and found exactly:

```text
any_visible_matching_tower                    4
single_visible_matching_tower                 0
route_equivalent_multiple_visible_towers      4

match count distribution:
0 3934
2    4
```

All four multiple-match rows were already at the old final stage:

```text
post_mine_strong_residual 4
```

They span four games and four hulls. All four have baseline category:

```text
warp_zero_external_move
```

Therefore the global predicted delta was exactly:

```text
external_context_explained       +4
post_external_residual           -4
chunnel_explained                 0
horwasp_strong_explained          0
mine_strong_explained             0
post_mine_strong_residual        -4
```

Critical negative control passed:

```text
single_visible_matching_tower = 0
```

So the defect was strictly route-equivalent multiplicity, not ordinary single-Tow detection.

## Test verification

Targeted Tow/compiled/cache/label/mine/Chunnel regressions passed:

```text
26 passed
```

The full repository pytest suite also passed completely.

The source fix is therefore `TESTED`.

## L1 v3 cache migration

Normal L1 build was run without `--rebuild`.

Observed cache behavior:

```text
compiled_cache_hits                0
compiled_cache_misses             12
prepared_cache_hits_on_compile    12
prepared_cache_misses_on_compile   0
```

This is exactly the intended semantic invalidation: all stale L1 v2 partitions were rebuilt while prepared state was reused.

Verified L1 accounting:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13960
post_external_residual         3934
```

Catalog accounting matched the build summary exactly.

## L2 v5 source invalidation

Normal L2 build was then run without `--rebuild`.

Observed cache behavior:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
```

Thus the unchanged v5 label layer correctly invalidated every stale partition from the changed L1 source schema/hash.

Verified L2 accounting:

```text
external_residual_rows             3934
label_issues                          0
chunnel_explained                  1421
post_chunnel_residual              2513
horwasp_ballistic_candidates        911
horwasp_mite_residual               786
horwasp_strong_explained            240
horwasp_observed_context_explained    0
post_horwasp_strong_residual       2273
mine_strong_explained                37
post_mine_strong_residual          2236
```

The build summary and catalog summary matched.

## Exact differential closure

The runtime comparison against the independently calculated pre-build expectation produced zero delta for every layer:

```text
metric                             expected actual delta
external_context_explained            13960  13960   +0
post_external_residual                 3934   3934   +0
chunnel_explained                      1421   1421   +0
post_chunnel_residual                  2513   2513   +0
horwasp_strong_explained                240    240   +0
post_horwasp_strong_residual           2273   2273   +0
mine_strong_explained                    37     37   +0
post_mine_strong_residual              2236   2236   +0
label_issues                              0      0   +0
```

Runtime emitted:

```text
ACCOUNTING DIFFERENTIAL: EXACT MATCH
```

The fix is therefore `DIFF_VERIFIED`.

## Post-fix global negative control

The same global Tow diagnostic was rerun after the rebuild.

It found:

```text
external_residual_rows= 3934
any_visible_matching_tower= 0
single_visible_matching_tower= 0
route_equivalent_multiple_visible_towers= 0
```

Match-count distribution became:

```text
0 3934
```

No downstream overlap remained and the predicted additional delta was zero.

This closes the route-equivalent visible Tow investigation.

## Current authoritative movement endpoint

The new runtime-verified 12-game endpoint is:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13960
post_external_residual              3934
chunnel_explained                   1421
post_chunnel_residual               2513
horwasp_strong_explained             240
post_horwasp_strong_residual        2273
mine_strong_explained                 37
post_mine_strong_residual           2236
label_issues                           0
```

Compared with the previous verified endpoint, only the four route-equivalent Tow rows moved from the final residual into L1 external context.

## Next action

Rebaseline generic residual clustering against the rebuilt final view:

```text
movement_post_mine_strong_residual
```

Use the existing diagnostic:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

The previous generic baseline (`2240` final / `783` generic / `79` generic hulls) is now historical and must not be used to choose the next investigation until the diagnostic is rerun on the v3 endpoint.

After the rebaseline, choose the next broad mechanic family by cross-hull/cross-game evidence rather than hull-specific counts.

## Guardrails

- Do not reopen route-equivalent Tow absent fresh contradictory evidence.
- Do not infer a winning Tow tower from route-equivalent observations.
- Do not broaden Tow classification to visible non-Tow co-movers.
- Do not reopen Chunnel route-equivalent handling, strict mine v5 or Red Mite without new evidence.
- Preserve the distinction between raw facts/topology and evidence-scoped effective interpretations.
