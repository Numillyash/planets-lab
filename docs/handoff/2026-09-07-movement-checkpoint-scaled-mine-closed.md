# Movement checkpoint — scaled normal-mine closure

Date: 2026-09-07

GitHub `main` is the only source of truth. This handoff records the runtime-verified state of the normal-mine short-waypoint production integration on branch `agent/normal-mine-scaled-floor-production` before merge.

## Runtime-verified L2 accounting

The full 12-game context-label corpus rebuilt cleanly with prepared-cache hits for all games and zero failures:

```text
external_residual_rows             3924
chunnel_explained                  1421
post_chunnel_residual              2503
horwasp_strong_explained            240
post_horwasp_strong_residual       2263
mine_strong_explained                60
post_mine_strong_residual          2203
fuel_proration_explained              6
post_fuel_proration_residual       2197
label_issues                          0
```

Delta versus the previous production baseline:

```text
mine_strong_explained        37 -> 60   (+23)
post_mine_strong_residual  2226 -> 2203 (-23)
fuel_proration_explained      6 -> 6    (unchanged)
post_fuel_proration_residual 2220 -> 2197 (-23)
```

Chunnel and Horwasp accounting were unchanged.

## New production category

```text
normal_mine_hit_scaled_floor_exact
```

The new path is deliberately narrow and fail-closed:

- planar topology only;
- hull tech `< 7`;
- hostile normal-mine route crossing;
- real short waypoint (`regular_distance < nominal_distance`);
- same-line shortened movement;
- direct mine-damage multiple or exact canonical automatic supply-repair reconstruction;
- unique `(damage_hits, slowdown_hits)` model;
- exact Host major-axis click endpoint under the empirical scaled-floor penalty;
- sphere/unknown topology and ambiguous models remain unresolved.

The empirical penalty is:

```text
floor(10 * slowdown_hits * nominal_max_distance / regular_distance)
```

This is a corpus-observed classifier relation, not a claim that NuHost literally evaluates this expression internally.

## Independent evidence chain

Before production integration:

```text
production planar controls:       15/15 within +/-1 click
strict residual planar resolved:  31/31 within +/-1 click
strict residual exact:            27/31
production-visible equivalence:   23/23 report-backed references
misses:                            0
extras:                            0
```

The production integration intentionally accepts only the independently equivalent exact short-waypoint subset: 23 rows.

Runtime population:

```text
scaled_floor_exact rows = 23
games                   = 6
hulls                    = 9
Horwasp rows             = 0
```

By game:

```text
360690  10
511506   4
620694   5
620917   1
621103   2
680910   1
```

All 23 have `damage_hits = 1` and `slowdown_hits = 1` in the current corpus.

## Original target is closed

`511506 / before turn 23 / ship 160 / hull 17` now classifies as:

```text
mine_category       = normal_mine_hit_scaled_floor_exact
mine_damage_hits    = 1
mine_slowdown_hits  = 1
mine_strong_explained = true
post_mine_strong_residual = false
post_fuel_proration_residual = false
```

Its damage trace is reconstructed from production-visible state as one normal-mine hit plus exact automatic supply repair:

```text
0 damage + 76 mine damage
53 supplies -> repair 10 damage using 50 supplies
final = 66 damage / 3 supplies
```

No raw message dependency is required by the production classifier.

## Current generic final endpoint

Runtime-verified after the production rebuild and final generic clustering:

```text
final_residual_rows       2197
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               740
generic_games               12
generic_hulls               75
```

Largest coarse generic family:

```text
113  warp7-9 <0.5x observed=other same_line_forward
```

Largest detailed member of that family:

```text
89  warp7-9 reachable_other <0.5x observed=other same_line_forward non-gravitonic
```

These residual clusters remain leads, not mechanics by themselves.

## Evidence status

The short-waypoint scaled-floor normal-mine classifier is:

- underlying low-tech mine slowdown: `DOCUMENTED`;
- exact scaled-floor relation: `CORPUS_OBSERVED`;
- deterministic classifier/tests: `TESTED`;
- independent production-visible equivalence plus clean 12-game production rebuild/accounting: `DIFF_VERIFIED`.

Do not relabel the empirical scaled-floor expression itself as documented NuHost source semantics.

## Test and performance status

```text
movement-mine targeted tests = 10 passed
12-game L2 rebuild           = 12 compiled / 0 failed
prepared cache hits          = 12/12
label issues                 = 0
L2 rebuild wall time         = ~101.6 s with --jobs 2
```

GitHub Actions was green on the mechanics/test commits; final docs-only commits must also be green before merge.

The optimized production-evidence equivalence diagnostic reduced the earlier hour-scale run to roughly five minutes by removing a duplicated corpus pass and skipping sphere rows before heavy reconstruction.

## Next project step

Do not reopen normal-mine short-waypoint research absent contradictory evidence.

After merge and `main` verification:

1. treat movement as a subsystem checkpoint rather than continue unbounded residual hunting;
2. inventory reusable mechanics across `planets-lab` and `Numillyash/planets-intel`;
3. next major integration target is the already-developed Classic combat/VCR core from `planets-intel`, preserving evidence and regression coverage;
4. then proceed through full Host combat ordering, economy/starbases/production, minefield lifecycle, missions/ship abilities, diplomacy/alliances, race mechanics, visibility/observer, and end-to-end Host-order integration in roadmap order.

The goal remains a high-fidelity NuHost-compatible simulator suitable for later player-safe training/self-play, not a shortcut model that bypasses unresolved Host mechanics.
