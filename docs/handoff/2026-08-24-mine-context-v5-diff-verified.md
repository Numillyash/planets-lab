# Mine/web movement context v5 — differential verified

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **strict mine/web L2 context v5 is CORPUS_OBSERVED + TESTED + DIFF_VERIFIED; one repository-wide pytest rerun remains after fixing a stale v4 schema sentinel in an older Chunnel regression.**

This handoff supersedes `2026-08-24-mine-context-v5-pending.md` for the active movement/corpus investigation.

## Verified layer accounting

The normal v5 L2 build was run at clean HEAD `fd6c6d3` without `--rebuild`.

Cache behavior:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
games_failed                        0
```

This confirms schema v5 invalidated only the compiled label layer while reusing all prepared caches.

Accounting:

```text
external_residual_rows             3938
chunnel_explained                  1421
post_chunnel_residual              2517
horwasp_strong_explained            240
post_horwasp_strong_residual       2277
mine_strong_explained                37
post_mine_strong_residual          2240
label_issues                           0
```

The pre-mine Chunnel/Horwasp endpoint remained bit-for-accounting unchanged. The independent mine rounding audit predicted exactly 37 strict rows and the production classifier closed exactly 37.

## Strict mine categories

```text
normal_mine_hit_nearest_damage  19
web_mine_hit_nearest_damage     18
```

By hit counts:

```text
normal: damage_hits=1, slowdown_hits=1  -> 17 rows
normal: damage_hits=2, slowdown_hits=1  ->  1 row
normal: damage_hits=2, slowdown_hits=2  ->  1 row
web:    damage_hits=1                   -> 18 rows
```

The `2 damage hits / 1 slowdown` row is intentional evidence that damage-hit multiplicity and 10-ly slowdown count must not be forced equal.

## Overlap guards

All production overlap controls were zero:

```text
mine_and_chunnel              0
mine_and_horwasp_strong       0
mine_horwasp_hulls            0
mine_not_post_horwasp_source  0
```

Thus v5 is an additive post-Horwasp context layer and did not steal rows from previously verified mechanics.

## NuHost rounding compatibility finding

The preceding diagnostic measured:

```text
web_ceil_delta_match_after_field       3
web_floor_delta_match_after_field     15
web_nearest_delta_match_after_field   18
web_nearest_control_no_after_field     0

normal_ceil_delta_multiple_after_field       7
normal_floor_delta_multiple_after_field     13
normal_nearest_delta_multiple_after_field   19
normal_nearest_repair_bracket_from_zero     22
normal_nearest_control_no_after_field        0
```

Planets.nu documentation says mine damage is rounded up, but historical NuHost corpus behavior strongly selects positive nearest-integer rounding for both web and normal mine damage. This is a compatibility finding, not a rewrite of the documentation claim.

Production v5 deliberately uses only the strict field-backed nearest-damage subset. Repair-bracket-only rows remain residual until repair reconstruction is independently validated.

## Production implementation

Module:

```text
src/planets_lab/corpus/movement_mine_context.py
```

Compiled label schema:

```text
planets-lab.compiled-movement-context-labels.v5
```

Derived fields:

```text
mine_category
mine_damage_hits
mine_slowdown_hits
mine_strong_explained
post_mine_strong_residual
```

The exported label data does not include minefield IDs, owners, coordinates, friendly codes or other private source fields.

Layer order remains:

```text
post_external_residual
  -> Chunnel
  -> post_chunnel_residual
  -> Horwasp strong
  -> post_horwasp_strong_residual
  -> strict mine/web strong
  -> post_mine_strong_residual
```

`movement_post_horwasp_strong_residual` remains the pre-mine control view; `movement_post_mine_strong_residual` is the new final movement residual view.

## Tests and stale schema sentinel

The targeted and full pytest runs at HEAD `fd6c6d3` each had exactly one failure:

```text
tests/test_movement_chunnel_route_equivalent.py::test_route_equivalent_semantics_bump_cache_schemas
```

The failing assertion hard-coded compiled label schema v4 even though v5 was intentionally introduced by the mine layer. This was a stale regression sentinel, not a v5 mechanic failure. All new mine-context tests passed in that run.

The assertion was updated on `main` in commit:

```text
3661f038178bf7fae37496ad23be90e08480ea72
```

The standalone Chunnel cache schema remains v2; only the shared compiled context-label schema expectation advances to v5.

A final targeted/full pytest rerun is still required to record a fully green repository state after this test-only fix. The compiled corpus does **not** need rebuilding for that rerun because production code and label data are unchanged by the test fix.

## Immediate next step

1. Pull current `main`.
2. Run the corrected targeted tests and full pytest suite only; no corpus rebuild is required.
3. If green, update durable state to record the final green suite.
4. Re-run generic residual clustering against `movement_post_mine_strong_residual` and establish the new post-v5 generic landscape.
5. Continue with generic cross-game mechanics; do not broaden mine labels to repair-bracket-only rows yet.

Current verified movement endpoint for future triage:

```text
post_mine_strong_residual  2240
```
