# Damage-limited warp L1 context — runtime verification pending

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **the independent post-v3 corpus differential strongly confirms a narrow damage-limited maximum-warp signature. A strict fail-closed L1 context pass and regressions are implemented on `main`; runtime tests and normal L1/L2 cache-invalidating builds are still required before promotion to TESTED + DIFF_VERIFIED.**

This handoff supersedes `2026-08-25-damage-limited-warp-followup.md` for active work. Route-equivalent Tow v3, mine/web v5, Chunnel v4, classic ion storms, scoped sphere topology and Red Mite remain closed absent fresh contradictory evidence.

## Last runtime-verified corpus baseline

The currently generated 12-game corpus remains:

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

Verified generic endpoint before the pending damage pass:

```text
final_residual_rows       2236
generic_rows               779
generic_games               12
generic_hulls               78
```

Largest coarse family:

```text
121  warp7-9 <0.5x observed=other same_line_forward
```

## Independent damage-limited warp differential

Diagnostic:

```text
tools/diagnostics/damage_limited_warp_residual_audit.py
```

Runtime population:

```text
generic_non_horwasp_warp1_9_rows  681
target_short_forward_rows          121
same_identity_after                444
identity_break_after               237
formula_ready                      444
damaged_before                      61
undamaged_before                   383
raw_damage_limited                  11
raw_not_damage_limited             433
```

Exact differential:

```text
raw_endpoint_exact                               10
raw_damage_limited_endpoint_exact                10
current_supply_bracket_endpoint_exact            10
damage_limit_any_exact                           10
raw_exact_low_supply                             10
raw_not_damage_limited_endpoint_exact_control      0
undamaged_endpoint_exact_control                   0
```

The exact subset spans:

```text
9 games
8 hulls
6 races
```

and effective maximum warp values:

```text
Warp 1  -> 3 rows
Warp 3  -> 1
Warp 4  -> 1
Warp 5  -> 1
Warp 6  -> 1
Warp 7  -> 1
Warp 8  -> 2
```

The broad cross-game/cross-hull spread plus zero negative controls makes accidental geometry matching unlikely.

### Relation to the dominant 121-row family

Only two of the 121 dominant short-forward rows are exact raw-damage matches:

```text
target_short_raw_damage_limited         2
target_short_raw_endpoint_exact         2
target_short_current_supply_bracket_exact 2
target_short_damage_limit_any_exact     2
target_short_raw_exact_low_supply       2
```

Therefore damage-limited warp is a real generic mechanic but **not** the main explanation of the 121-row family. Production must close only its strict subset and leave the other 119 rows for later triage.

## Documentation / Host-order caveat

Planets.nu `Damage - Details` documents reduced maximum warp by damage band, including the separate Lizard table, but marks that page as outdated/superseded. The production context therefore does not rely on the page alone.

Host Order independently places `Mass check, repair & MKT` before Tow and Most Ships Move. Pre-movement repair/transfers can therefore alter damage before movement.

For that reason the production predicate deliberately excludes repair reconstruction and accepts only the strict raw-damage subset with fewer than 5 KT of currently visible onboard supplies plus an exact Host-major/minor endpoint.

## Implemented production context

New module:

```text
src/planets_lab/corpus/movement_damage_context.py
```

Production category:

```text
damage_limited_warp_match
```

Strict predicate:

```text
row still unresolved after existing L1 external context
AND non-Horwasp hull
AND owner/race resolved
AND same owner/hull/ship identity after transition
AND requested warp in 1..9
AND visible supplies before movement < 5 KT
AND documented raw-damage max warp < requested warp
AND exact Host-major/minor endpoint at that effective warp
```

Gravitonic distance and the evidence-scoped effective sphere topology are preserved.

No damage, supplies, race ID or inferred effective warp is added to exported Parquet columns. Only the derived external-context category/flags change.

## Ordered L1 context stack

The existing historical semantic marker name remains `MOVEMENT_STORM_CONTEXT_SCHEMA`, but its meaning is now the complete ordered post-compile L1 stack:

```text
authoritative storm mode
  -> scoped effective sphere geometry
  -> strict damage-limited warp context
```

The marker is bumped:

```text
planets-lab.compiled-movement-storm-context.v2
  -> planets-lab.compiled-movement-storm-context.v3
```

Physical L1 columns and schema remain:

```text
planets-lab.compiled-movement.v3
```

L2 remains:

```text
planets-lab.compiled-movement-context-labels.v5
```

The semantic marker bump must invalidate all 12 L1 partitions on a normal build. Changed L1 Parquet hashes must then invalidate all 12 unchanged-v5 label partitions.

## Regression coverage

New tests:

```text
tests/test_movement_damage_context.py
```

They cover:

- standard damage-band maximum warp;
- Lizard damage-band maximum warp;
- exact endpoint requirement;
- `<5 KT` supplies guard;
- undamaged/not-limited negative control;
- Gravitonic doubled movement distance;
- stable production category name.

## Independent expected production delta

All 10 strict rows were selected from the current `movement_post_mine_strong_residual`, so they currently survive Chunnel, Horwasp strong and mine/web strong.

If production reproduces the independent diagnostic exactly, expected accounting is:

```text
external_context_explained        13960 -> 13970  (+10)
post_external_residual             3934 ->  3924  (-10)
chunnel_explained                  1421 ->  1421
post_chunnel_residual              2513 ->  2503  (-10)
horwasp_strong_explained            240 ->   240
post_horwasp_strong_residual       2273 ->  2263  (-10)
mine_strong_explained                37 ->    37
post_mine_strong_residual          2236 ->  2226  (-10)
label_issues                          0 ->     0
```

Expected current generic population after the strict pass:

```text
generic_rows  779 -> 769
```

The dominant short-forward family should change only:

```text
121 -> 119
```

Do not assert a new generic-hull count until the post-build rebaseline runs.

## Cache expectations

Normal L1 build without `--rebuild`:

```text
compiled_cache_hits                0
compiled_cache_misses             12
prepared_cache_hits_on_compile    12
prepared_cache_misses_on_compile   0
```

Following normal L2 build without `--rebuild`:

```text
compiled_label_cache_hits           0
compiled_label_cache_misses        12
prepared_cache_hits_on_compile     12
prepared_cache_misses_on_compile    0
```

## Required runtime verification

1. pull current `main` and confirm clean status;
2. syntax-check the new module, changed L1 context stack and test file;
3. run the targeted damage/storm/compiled/cache regression set;
4. run full pytest;
5. run normal L1 build without `--rebuild`;
6. confirm semantic-marker invalidation gives 0/12 L1 compiled hits and 12/12 prepared hits;
7. run normal L2 v5 build without `--rebuild`;
8. confirm changed source Parquet/hash gives 0/12 label hits and 12/12 prepared hits;
9. compare all layer counts against the exact pre-build prediction above;
10. rerun the damage differential and broad generic clustering on the rebuilt endpoint.

## Guardrails

- Do not promote current-supplies repair-bracket-only cases.
- Do not infer exact pre-movement repair from visible before-turn supplies.
- Do not reinterpret the 10-row mechanic as explaining the remaining 119 short-forward rows.
- Do not reopen Tow/Chunnel/mine/Red Mite without fresh evidence.
- Preserve raw damage/race/supplies as private local facts; export only derived category/flags.
- Keep game `591478`'s 2170 effective sphere period scoped to that game.
