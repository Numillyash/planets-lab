# Chunnel route-equivalent matches — runtime verification handoff

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **production semantics fixed; deterministic/runtime verification pending**.

This handoff supersedes `2026-08-24-chunnel-route-equivalent-ambiguity.md` for the active task.

## Last runtime-verified baseline

These remain authoritative until the new L2 label build is run:

```text
external_residual_rows             3938
chunnel_explained                  1387
post_chunnel_residual              2551
horwasp_strong_explained            240
post_horwasp_strong_residual       2311
label_issues                          0
```

## Pre-fix all-corpus differential

Diagnostic:

```text
tools/diagnostics/chunnel_route_equivalent_ambiguity_audit.py
```

Measured on the v3 label corpus:

```text
labeled_rows                         3938
multiple_match_rows                    34
multiple_match_unexplained             34
multiple_match_post_chunnel             34
multiple_match_final_residual            34
multiple_match_warp0_self_waypoint       22
```

Every affected row had exactly two current Chunnel matches:

```text
chunnel_match_count=2   34 rows
```

All 34 were currently labeled:

```text
ambiguous_matching_events
```

Coverage:

```text
by game:
  360690  21
  591478  13

by baseline category:
  warp_zero_external_move  22
  above_nominal            12
```

Affected hulls:

```text
56    19
53     5
17     4
52     4
16     1
1054   1
```

This is a generic L2 semantic defect rather than a warp-zero-only rule.

## Root cause

Both standalone Chunnel evaluation and compiled L2 labels first filter candidate events to:

- the same transition turn;
- the same candidate pre-Chunnel position;
- the same observed destination.

Therefore, after this predicate is applied, multiple matching events are already route-equivalent for movement classification. Event identity can be ambiguous, but the movement cause is not.

The previous behavior treated:

```text
len(matches) == 1  -> Chunnel explained
len(matches) > 1   -> ambiguous_matching_events -> residual
```

This produced 34 false residual rows.

## Production fix in main

Shared helper:

```text
src/planets_lab/corpus/movement_chunnel_match.py
```

Function:

```text
route_equivalent_chunnel_category(...)
```

New semantics:

- empty match set -> unexplained;
- any non-empty already route-equivalent match set -> Chunnel movement explained;
- if all matching events assign the same role, retain `initiator`, `passenger_same_owner` or `passenger_other_owner`;
- if matching events assign different roles, use `route_equivalent_multiple_roles`;
- role ambiguity is descriptive only and does not reopen the movement residual.

Both production L2 and the standalone Chunnel evaluator use the same helper.

Schema changes:

```text
compiled context labels:
  planets-lab.compiled-movement-context-labels.v3
  -> planets-lab.compiled-movement-context-labels.v4

standalone Chunnel game summary:
  planets-lab.movement-chunnel-context-game.v1
  -> planets-lab.movement-chunnel-context-game.v2

standalone Chunnel aggregate summary:
  planets-lab.movement-chunnel-context-stats.v1
  -> planets-lab.movement-chunnel-context-stats.v2
```

The L2 schema bump must invalidate all old label partitions during a normal build without `--rebuild`.

Regression coverage:

```text
tests/test_movement_chunnel_route_equivalent.py
```

It covers empty matches, duplicate same-route events for same-owner/other-owner passengers, mixed-role route equivalence, and semantic schema bumps.

## Expected runtime differential

The pre-fix DB audit measured exactly 34 affected rows and all 34 were final residuals. If production rebuild matches the diagnostic exactly, expected counts are:

```text
chunnel_explained             1387 -> 1421  (+34)
post_chunnel_residual         2551 -> 2517  (-34)
horwasp_strong_explained       240 ->  240  (expected unchanged)
post_horwasp_strong_residual  2311 -> 2277  (-34)
```

These are expectations, not yet runtime-verified invariants. Record the measured result even if it differs.

## Immediate next step

1. Pull current main.
2. Run targeted Chunnel/compiled-label tests and full pytest.
3. Run the L2 label compiler normally, without `--rebuild`.
4. Verify schema v4 invalidates old label caches automatically.
5. Verify prepared caches are reused.
6. Query exact Chunnel/final residual counts and route-equivalent categories.
7. Confirm no `ambiguous_matching_events` rows remain with `chunnel_match_count > 1`.
8. Re-run `chunnel_route_equivalent_ambiguity_audit.py`; it should report no multiple-match unexplained/final residual rows.
9. Rebaseline README, ROADMAP and COMPILED_CORPUS only from measured output.

Do not start another movement mechanic before this exact differential is closed.
