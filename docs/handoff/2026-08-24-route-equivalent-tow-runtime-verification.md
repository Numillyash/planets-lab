# Route-equivalent visible Tow migration — runtime verification pending

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **a route-equivalent Tow ambiguity defect has been demonstrated on four target-origin final-residual rows; the L1 external-context fix and schema invalidation are implemented on `main`, but the global pre-build differential and runtime corpus rebuild are still required.**

This handoff supersedes `2026-08-24-target-origin-tow-followup.md` for the active movement investigation. Mine/web v5, Chunnel v4, classic ion storms, scoped sphere topology and Red Mite remain closed unless fresh evidence appears.

## Last runtime-verified corpus baseline

Before the Tow semantic change, the verified 12-game accounting is:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13956
post_external_residual              3938
chunnel_explained                   1421
post_chunnel_residual               2517
horwasp_strong_explained             240
post_horwasp_strong_residual        2277
mine_strong_explained                 37
post_mine_strong_residual           2240
label_issues                           0
```

The fully verified post-v5 generic rebaseline is:

```text
final_residual_rows       2240
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               783
generic_games               12
generic_hulls               79
```

## Target-origin Tow finding

Focused diagnostic:

```text
tools/diagnostics/target_origin_tow_residual_audit.py
```

Runtime population:

```text
candidate_rows                              226
post_warp0                                  116
has_same_origin_destination_comover          35
has_hidden_or_unresolved_comover              0
has_visible_tow_targeter                     92
visible_tow_targeter_other_destination       88
any_visible_matching_tower                    4
single_visible_matching_tower                 0
route_equivalent_multiple_visible_towers      4
```

All four matching rows have exactly two owner-visible Tow targeters. Each counted tower:

- targets the candidate ship with the Tow mission;
- is colocated with the target before movement;
- ends at exactly the same non-stationary observed destination as the target.

All four targets also end at Warp 0. The rows span four games and four hulls.

Therefore tower identity is ambiguous, but the observed target movement route is not. The old `_observed_tow_targets()` incorrectly treated `len(matches) > 1` as unresolved movement evidence.

The four target-origin rows are a guaranteed lower bound on the bug's corpus impact. They are **not yet assumed to be the full global count**, because the focused diagnostic filtered to `target=origin`.

## Implemented source fix

`src/planets_lab/corpus/movement_residual_context.py` now preserves all matching tower IDs:

```text
(before_turn, target_id) -> tuple[tower_id, ...]
```

Any non-empty matching set is movement evidence. The helper never chooses an arbitrary tower as the actual Tow winner.

Derived Tow counters now distinguish:

```text
observed_tow_target_match
observed_tow_target_single
observed_tow_target_route_equivalent_multiple
```

Standalone residual-context schemas were bumped to:

```text
planets-lab.movement-residual-context-game.v2
planets-lab.movement-residual-context-stats.v2
```

The behavioral regression in `tests/test_movement_residual_context.py` covers two owner-visible Tow towers targeting one ship and sharing its observed route.

## L1 cache/schema migration

Because Tow interpretation is part of the compiled L1 external-context semantics, `COMPILED_MOVEMENT_SCHEMA` was bumped from v2 to:

```text
planets-lab.compiled-movement.v3
```

No physical columns changed. The schema bump is semantic and intentionally invalidates all old L1 movement partitions on a normal build without `--rebuild`.

L2 remains:

```text
planets-lab.compiled-movement-context-labels.v5
```

A label-schema bump is not required because the Chunnel/Horwasp/mine label predicates themselves did not change. L2 metadata already binds each label partition to:

- current `source_movement_schema`;
- exact source movement Parquet SHA-256.

Therefore rebuilding L1 v3 automatically invalidates stale v5 label partitions on the following normal L2 build.

## Global pre-build differential

Before rebuilding L1, run:

```text
tools/diagnostics/tow_route_equivalent_global_differential_audit.py
```

It reads the old verified `movement_labeled_residual` population and independently reconstructs owner-visible matching Tow routes across all 3938 external residual rows.

Critical guard:

```text
single_visible_matching_tower = 0
```

If this is non-zero, stop: it would mean the old L1 detector missed ordinary single Tow matches and the semantic change is broader than the demonstrated multiplicity defect.

The diagnostic partitions route-equivalent multiple matches by their current downstream stage:

```text
chunnel_explained
horwasp_strong_explained
mine_strong_explained
post_mine_strong_residual
```

Those counts define the authoritative expected production delta. Do not assume the global total is four merely from the target-origin audit.

If the global output is exactly the four known final-residual rows, the expected accounting would be:

```text
external_context_explained  13956 -> 13960
post_external_residual        3938 ->  3934
chunnel_explained             1421 ->  1421
post_chunnel_residual         2517 ->  2513
horwasp_strong_explained       240 ->   240
post_horwasp_strong_residual  2277 ->  2273
mine_strong_explained           37 ->    37
post_mine_strong_residual      2240 ->  2236
```

That block is conditional until the global audit runs.

## Required runtime verification order

1. pull current `main` and confirm a clean tree;
2. syntax-check the changed source/tests/diagnostic;
3. run the global route-equivalent Tow differential **before rebuilding corpus data**;
4. run targeted tests and full pytest;
5. run normal L1 compilation without `--rebuild`;
6. verify all 12 L1 partitions missed cache and reused prepared caches;
7. run normal L2 v5 compilation without `--rebuild`;
8. verify all 12 label partitions missed cache because L1 schema/hash changed;
9. compare the resulting layer accounting against the global differential;
10. rerun the target-origin audit and broad generic clustering only after the rebuilt final views exist.

## Cache expectations

L1 v2 -> v3 semantic invalidation should produce:

```text
compiled_cache_hits                0
compiled_cache_misses             12
prepared_cache_hits_on_compile    12
prepared_cache_misses_on_compile   0
```

The subsequent L2 v5 build should also produce:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
```

Exact field names in CLI output should be taken from runtime; the invariant is 0/12 compiled-cache reuse and 12/12 prepared-cache reuse for both stages.

## Evidence guardrails

- Multiple matching Tow towers are movement-route evidence, not evidence of which tower won Host's Tow lock contest.
- Do not export or infer a winning tower ID from route-equivalent observations.
- Do not broaden the fix to visible non-Tow co-movers; seven target-origin Warp-0 examples have such co-movers but no matching Tow evidence.
- There is no hidden/unresolved co-mover evidence in the focused 226-row population.
- Do not broaden mine labels to repair-bracket rows.
- Do not reopen Chunnel route-equivalent handling or Red Mite.
- The last verified final residual remains 2240 until the L1/L2 rebuild closes the Tow differential.
