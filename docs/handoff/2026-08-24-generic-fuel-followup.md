# Generic movement residual — focused fuel follow-up

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **broad post-sphere clustering complete; focused fuel-limited diagnostic implemented and awaiting runtime output.**

## Runtime baseline

The current compiled 12-game movement baseline remains:

```text
move_most_candidates              227468
post_external_residual              3938
post_chunnel_residual               2551
post_horwasp_strong_residual        2311
```

Sphere-aware ordinary movement for game `591478` remains `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` and is not reopened by this investigation.

## Broad generic clustering result

Runtime diagnostic:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

Population:

```text
final_residual_rows          2311
known_horwasp_hull_rows      1457
generic_rows                  854
generic_games                  12
generic_hulls                  82
```

Two generic signatures dominate prioritization:

### 1. Short movement in the waypoint direction

The strongest causal-looking family is ordinary non-Horwasp movement that remains on the target line but travels materially less than normal geometry predicts.

Large coarse groups include:

```text
warp7-9, <0.5x, same_line_forward       133 rows / 26 hulls / 7 games
warp7-9, 0.5-1.0x, same_line_forward     70 rows / 26 hulls / 8 games
warp7-9, ~0.5x, same_line_forward         29 rows / 15 hulls / 7 games
```

These groups cross many hull IDs and games, so they are a better generic-mechanic target than any single hull count. Their geometry is consistent with a distance-limiting mechanic. Insufficient-fuel proration is the first focused hypothesis because the repository already contains the documented fuel-use formula and a previous narrow hull-16/17 correlation audit.

### 2. Warp-zero external movement with self waypoint

Another large family is:

```text
warp0, target=origin, external move      119 rows / 35 hulls / 8 games
```

This strongly suggests an external displacement/transport mechanic, but the broad geometry alone cannot distinguish hidden tow, remaining storm-context gaps, or another pre-movement transport effect. It remains the next fallback target if the fuel hypothesis does not explain enough of the short-forward cluster.

## Focused fuel diagnostic

New diagnostic:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

It differs from the older `freighter_fuel_movement_residual_audit.py` in several important ways:

- runs across the full non-Horwasp final residual instead of only hulls 16/17;
- excludes gravitonic rows from the ordinary-fuel candidate set so doubled movement geometry is not mixed into the test;
- uses the evidence-scoped effective `2170x2170` topology for game `591478`, while preserving raw topology facts;
- reconstructs only the rows that are actually short and aligned with the waypoint;
- reads fuel before/after, raw snapshot mass, engine ID and authoritative static engine fuel factor;
- evaluates documented fuel use for both the observed and normal expected distances;
- enumerates the maximum whole-light-year distance affordable by the observed fuel amount;
- reports same-identity continuity and post-move fuel depletion.

A row is counted as a **strong fuel-limit signature** only when all of these hold:

1. ship identity is continuous across the transition;
2. observed movement is short and aligned with the waypoint;
3. fuel is insufficient for the normal movement distance;
4. the observed movement is affordable by the same formula;
5. observed distance is within 1.5 ly of the maximum whole-ly affordable frontier;
6. the same ship is observed with zero fuel after the transition.

This is deliberately stricter than the old bracket-only audit. Raw snapshot `mass` remains correlation evidence rather than proof of exact post-host-order movement mass, so even a high hit rate must be reviewed before production promotion.

Implementation commit:

```text
5d3bedf  Add generic fuel-limited residual audit
```

## Immediate next step

Run the focused diagnostic and preserve the full output:

```bash
docker compose run --rm -T lab \
  python -u tools/diagnostics/generic_fuel_limited_residual_audit.py \
  | tee /tmp/generic_fuel_limited_residual_audit.log
```

Interpretation priorities:

- total `short_same_line_forward` population;
- `formula_brackets_observed` coverage;
- `strong_fuel_limit_signature` coverage;
- number of distinct hulls and games in strong signatures;
- false negatives where fuel is clearly sufficient;
- whether the result is broad enough to justify a production fuel-proration context layer.

If strong fuel signatures are sparse, do not overfit them. Return to the `warp0 + target=origin + external move` cluster as the next generic context investigation.
