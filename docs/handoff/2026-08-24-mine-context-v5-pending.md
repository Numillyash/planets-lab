# Mine/web movement context v5 — runtime verification pending

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **mine/web interruption and NuHost nearest-integer damage are strongly corpus-observed; strict v5 L2 classifier implemented; tests/build differential pending runtime**.

This handoff supersedes `2026-08-24-mine-damage-rounding-followup.md` for the active movement investigation. Existing Chunnel v4, classic ion-storm, scoped sphere and Horwasp evidence remains unchanged.

## Current verified pre-v5 accounting

```text
move_most_candidates              227468
post_external_residual              3938
chunnel_explained                   1421
post_chunnel_residual               2517
horwasp_strong_explained             240
post_horwasp_strong_residual        2277
```

No mine label has yet been runtime-built into the local compiled corpus.

## Damage-rounding differential — runtime result

The user ran:

```text
tools/diagnostics/mine_hit_damage_rounding_audit.py
```

at clean HEAD `732151f`.

Population and field-backed mine candidates:

```text
effective_short_same_line       238
same_identity_after             238
web_state_signature              19
web_after_field_strong           18
normal_mine_10ly_geometry        54
normal_after_field_strong        25
```

### Web damage rounding

```text
web_ceil_delta_match_after_field       3
web_floor_delta_match_after_field     15
web_nearest_delta_match_after_field   18
web_nearest_not_ceil_delta            15
web_nearest_control_no_after_field     0
```

Nearest-integer damage matches every field-backed web state signature. The matches span all three corpus games with observed web records and multiple hull masses.

### Normal mine damage rounding

```text
normal_ceil_delta_multiple_after_field       7
normal_floor_delta_multiple_after_field     13
normal_nearest_delta_multiple_after_field   19
normal_nearest_repair_bracket_from_zero     22
normal_nearest_not_ceil_from_zero           10
normal_nearest_damage_hits_differ_from_slow_hits 1
normal_nearest_control_no_after_field        0
```

Nearest-integer damage again dominates the documented ceil interpretation. Repair-bracket rows are supportive but are deliberately not promoted in the first production classifier.

One corpus row also demonstrates why damage-hit multiplicity must remain separate from 10-ly slowdown count: two nearest-rounded damage quanta can coexist with only one inferred slowdown when a later impact occurs with insufficient distance remaining for another slowdown.

## Compatibility conclusion

Planets.nu documentation describes mine damage as rounded up. Historical NuHost corpus evidence instead strongly selects positive nearest-integer rounding for both normal and web mine damage.

Evidence status before production build:

```text
mine/web movement interruption: DOCUMENTED + CORPUS_OBSERVED
NuHost nearest damage rounding: CORPUS_OBSERVED
production v5 classifier:        TESTED pending / DIFF_VERIFIED pending
```

Do not silently rewrite the documentation claim. The implementation must keep the compatibility distinction explicit.

## Implemented strict production classifier

New module:

```text
src/planets_lab/corpus/movement_mine_context.py
```

The classifier is deliberately fail-closed and uses only the strongest current evidence.

### Strict web category

```text
web_mine_hit_nearest_damage
```

Requires:

- non-Horwasp movement residual;
- Warp 1..9 short movement on the intended line, with Gravitonic effective distance where applicable;
- same owner/hull/raw-turn identity after Host;
- positive damage delta;
- post-state Warp 0 and waypoint reset to the observed stop point;
- enemy web field visible in at least one after-turn corpus perspective and containing the stop point;
- damage delta is a positive multiple of `round_half_up(1000 / (hull_mass + 1))`.

### Strict normal-mine category

```text
normal_mine_hit_nearest_damage
```

Requires:

- non-Horwasp movement residual;
- Warp 1..9 short same-line movement using effective Gravitonic distance when applicable;
- same owner/hull/raw-turn identity after Host;
- hull tech below 7;
- lost movement near a positive integer multiple of 10 ly;
- enemy normal minefield visible in at least one after-turn corpus perspective and intersecting the expected movement corridor;
- positive damage delta is a positive multiple of `round_half_up(10000 / (hull_mass + 1))`.

Damage-hit multiplicity is exported separately from slowdown count. They are not forced equal.

### Deliberate exclusions

The first production classifier does **not** promote:

- repair-bracket-only rows;
- before-turn-only minefield overlap;
- invisible/absent after-turn fields;
- field overlap without the matching damage signature;
- Horwasp hull IDs 201-213;
- broad mine guesses from geometry alone.

## Compiled label schema v5

`src/planets_lab/corpus/compiled_movement_labels.py` now declares:

```text
planets-lab.compiled-movement-context-labels.v5
```

New privacy-safe derived fields:

```text
mine_category
mine_damage_hits
mine_slowdown_hits
mine_strong_explained
post_mine_strong_residual
```

No minefield ID, owner, coordinate, friendly code or other private raw field is exported.

Layer order is intentionally preserved:

```text
post_external_residual
  -> Chunnel
  -> post_chunnel_residual
  -> Horwasp strong
  -> post_horwasp_strong_residual
  -> strict mine/web strong
  -> post_mine_strong_residual
```

The existing `movement_post_horwasp_strong_residual` DuckDB view remains available as the exact pre-mine control layer. New final view:

```text
movement_post_mine_strong_residual
```

Schema v5 automatically invalidates v4 compiled-label cache while preserving prepared cache validity.

## Pre-build differential target

The independent rounding audit measured strict field-backed nearest subsets:

```text
web nearest delta matches after field     18
normal nearest delta multiples after field 19
```

These subsets are disjoint under the strict classifier by mechanic predicates, so the expected production differential is:

```text
post_horwasp_strong_residual  2277  unchanged
mine_strong_explained           37  expected
post_mine_strong_residual     2240  expected
```

These are **expected**, not runtime-verified, until the v5 normal build completes.

## Tests added

```text
tests/test_movement_mine_context.py
```

Regression cases include:

- web mass 120: nearest quantum 8, documented ceil would be 9;
- normal mass 180: nearest quantum 55, documented ceil would be 56;
- two normal damage hits with one slowdown;
- fail-closed behavior without an observed after-turn field.

`tests/test_compiled_movement_labels.py` is extended for layered mine accounting and the new final DuckDB view.

## Immediate runtime verification

Run syntax checks, focused tests, full pytest, then a normal v5 L2 build **without `--rebuild`**. Expected cache behavior:

```text
compiled_label_cache_hits:          0
compiled_label_cache_misses:       12
prepared_cache_hits_on_compile:    12
prepared_cache_misses_on_compile:   0
```

Then verify:

```text
chunnel_explained               1421
post_chunnel_residual           2517
horwasp_strong_explained         240
post_horwasp_strong_residual    2277
mine_strong_explained             37  expected
post_mine_strong_residual       2240  expected
label_issues                        0
```

Also group `mine_category`, `mine_damage_hits` and `mine_slowdown_hits` in DuckDB. Any deviation from 37 must be inspected rather than normalized away.

Do not promote repair-bracket rows until the strict v5 differential is closed and repair reconstruction is separately validated.
