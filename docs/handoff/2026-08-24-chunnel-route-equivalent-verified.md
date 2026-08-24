# Chunnel route-equivalent matches — verified runtime state

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **TESTED + DIFF_VERIFIED**.

This handoff supersedes `2026-08-24-chunnel-route-equivalent-runtime-verification.md` for current movement/corpus state.

## Runtime-verified accounting

The L1 movement population is unchanged. L2 now reports:

```text
external_residual_rows             3938
chunnel_explained                  1421
post_chunnel_residual              2517
horwasp_strong_explained            240
post_horwasp_strong_residual       2277
label_issues                          0
```

Relative to the prior v3 runtime baseline:

```text
chunnel_explained             1387 -> 1421  (+34)
post_chunnel_residual         2551 -> 2517  (-34)
horwasp_strong_explained       240 ->  240  (unchanged)
post_horwasp_strong_residual  2311 -> 2277  (-34)
```

The measured production delta exactly matches the independent pre-fix DB differential.

## Pre-fix differential and post-fix closure

Pre-fix v3 audit:

```text
labeled_rows                         3938
multiple_match_rows                    34
multiple_match_unexplained             34
multiple_match_post_chunnel             34
multiple_match_final_residual            34
multiple_match_warp0_self_waypoint       22
```

All 34 had `chunnel_match_count=2`, split across:

```text
by game:
  360690  21
  591478  13

by baseline category:
  warp_zero_external_move  22
  above_nominal            12

by hull:
  56    19
  53     5
  17     4
  52     4
  16     1
  1054   1
```

Post-fix v4 audit:

```text
multiple_match_rows                 34
multiple_match_unexplained           0
multiple_match_post_chunnel           0
multiple_match_final_residual          0
old_ambiguous_category                0
```

Post-fix route-equivalent categories:

```text
route_equivalent_multiple_roles  19
passenger_same_owner             15
```

This proves the old residual was caused by event-identity/role multiplicity, not by an ambiguous movement route.

## Semantics

Production first filters Chunnel candidate events to the same transition turn, candidate pre-Chunnel position, and observed destination. Once that predicate is satisfied, any non-empty match set is sufficient to explain the displacement as Chunnel.

Shared helper:

```text
src/planets_lab/corpus/movement_chunnel_match.py
```

Rules:

- no matches -> unexplained;
- one or more route-equivalent matches -> `chunnel_explained=true`;
- one consistent role -> `initiator`, `passenger_same_owner`, or `passenger_other_owner`;
- mixed roles across equivalent events -> `route_equivalent_multiple_roles`;
- role ambiguity does not reopen the movement residual.

Both compiled L2 labels and the standalone Chunnel evaluator use the same helper.

## Schemas

Verified current schemas:

```text
compiled context labels:
  planets-lab.compiled-movement-context-labels.v4

standalone Chunnel game summary:
  planets-lab.movement-chunnel-context-game.v2

standalone Chunnel aggregate summary:
  planets-lab.movement-chunnel-context-stats.v2
```

## Cache verification

A normal L2 build was run without `--rebuild` after the v3 -> v4 semantic bump:

```text
compiled_label_cache_hits:          0
compiled_label_cache_misses:       12
prepared_cache_hits_on_compile:    12
prepared_cache_misses_on_compile:   0
games_compiled:                    12
games_failed:                       0
```

Therefore semantic cache invalidation and prepared-cache reuse both behaved as intended.

## Tests

The initially suggested targeted command contained a nonexistent path, `tests/test_compiled_movement_labels_corpus_cli.py`, and therefore exited before running. That was a command mistake, not a code failure.

The full pytest suite then passed, including:

```text
tests/test_movement_chunnel_route_equivalent.py
tests/test_movement_chunnel_context.py
tests/test_compiled_movement_labels.py
```

A correct focused command for future use is:

```bash
docker compose run --rm -T lab pytest -q \
  tests/test_movement_chunnel_route_equivalent.py \
  tests/test_movement_chunnel_context.py \
  tests/test_compiled_movement_labels.py
```

## Closed hypotheses from this chain

The prior Warp-0 investigation established:

```text
candidate_rows                               119
visible_explicit_tow_target_match               4
has_hidden_or_unresolved_comover                0
effective_topology_storm_vector_match           0
```

A structural Chunnel audit then found 22 Chunnel-shaped Warp-0 rows, but all 22 were already represented by existing event discovery. Therefore:

- ordinary visible tow is not the broad Warp-0 cause;
- hidden/private-FC event discovery is not the missing Chunnel layer here;
- storm topology is not the broad Warp-0 cause;
- route-equivalent event multiplicity was the actual L2 defect for those 22 rows plus 12 additional `above_nominal` rows.

## Next task

Resume generic post-v4 residual triage on the runtime-verified final residual of `2277`.

Do not select a hull by count alone. First rerun the existing generic clustering audit against the new final-residual view, then rerun the Warp-0 external-context audit to measure the population after removal of the 22 Chunnel false residuals.

Diagnostics:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
tools/diagnostics/warp0_external_move_context_audit.py
```

Keep Horwasp hull IDs `201-213` and closed Red Mite research out of generic prioritization. Fuel proration remains a verified minor contributor rather than the next broad production target.
