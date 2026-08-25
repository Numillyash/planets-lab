# Fuel-proration L2 v6 — verified; web-drain follow-up

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **documented Planets.nu waypoint-distance fuel proration is CORPUS_OBSERVED + TESTED + DIFF_VERIFIED on a strict six-row L2 subset. The active next investigation is documented pre-movement Crystal web drain as an input to already verified Nu fuel proration.**

This handoff supersedes `2026-08-25-fuel-proration-v6-runtime-verification.md` for active work.

## Runtime verification result

Source/runtime HEAD used for the verification:

```text
327d30d
```

Targeted v6 tests:

```text
16 passed
```

Full pytest suite:

```text
green
```

Normal L2 v6 build, without `--rebuild`:

```text
compiled_label_cache_hits:            0
compiled_label_cache_misses:          12
prepared_cache_hits_on_compile:       12
prepared_cache_misses_on_compile:      0
```

The schema bump from v5 to v6 therefore invalidated every old L2 label partition exactly as intended while reusing all prepared caches.

## Verified movement accounting

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
fuel_proration_explained               6
post_fuel_proration_residual        2220
label_issues                           0
```

Fuel category:

```text
fuel_proration_waypoint_match  6
```

All overlap guards were zero:

```text
fuel_and_chunnel             0
fuel_and_horwasp_strong      0
fuel_and_mine_strong         0
fuel_not_post_mine_source    0
```

Runtime accounting matched the independent pre-build prediction exactly.

Status: **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.

## Post-v6 generic baseline

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest surviving coarse families:

```text
116  warp7-9 <0.5x     observed=other same_line_forward
 93  warp0   nominal<=0 target=origin
 64  warp7-9 <0.5x     observed=origin stationary
 52  warp7-9 >3.0x     target=origin
 46  warp7-9 >3.0x     observed=other oblique
 43  warp7-9 0.5-1.0x observed=other same_line_forward
```

The independently predicted dominant-family change also reproduced exactly:

```text
119 -> 116
```

## Why web drain is the next focused mechanic

The dominant 116-row family contains ships whose waypoint is reachable at the submitted Warp and whose observed movement remains on the waypoint line but stops far short. Strict raw-fuel proration, damage-limited warp, strict mine/web hits, Tow, Chunnel, storm/sphere and Horwasp strong context have already been removed.

Planets.nu documents Web Drain before normal movement. An enemy ship inside, or within 1 ly of, each post-decay Crystal web field loses 25 KT of Neutronium per field. `Fuel Consumption Details` separately lists Web Drain among the events that occur before movement fuel usage is calculated.

This can create the exact residual shape still under investigation:

```text
submitted fuel sufficient
-> web drain removes 25/50/... KT
-> movement mass falls by the drained fuel amount
-> remaining fuel becomes insufficient
-> documented Nu waypoint-distance proration
-> short same-line movement without requiring a web-mine impact
```

Web-hit v5 remains closed. This is a separate pre-movement fuel-state mechanism.

## New diagnostic

```text
tools/diagnostics/web_drain_fuel_proration_audit.py
```

It runs on:

```text
movement_post_fuel_proration_residual
```

Population guard:

```text
target_short_forward_rows = 116
```

The diagnostic compares:

1. raw-fuel proration control — expected to be zero after v6;
2. documented web drain applied to fuel only;
3. documented web drain applied to both fuel and movement mass;
4. a synthetic 25-KT drain on rows with no visible enemy web as a negative control.

Strongest causal signature:

```text
visible enemy web at origin
+ raw fuel sufficient before drain
+ positive fuel after documented drain
+ insufficient fuel after drain
+ exact Nu waypoint-proration endpoint using reduced fuel and reduced mass
```

No production schema/accounting change should be made until this differential is run.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/web_drain_fuel_proration_audit.py`;
3. run it on the current v6 generated corpus;
4. require `target_short_forward_rows = 116`;
5. compare `web_drain_fuel_only_endpoint_exact` vs `web_drain_fuel_mass_endpoint_exact`;
6. inspect `web_drain_causal_exact` and the no-web synthetic control;
7. inspect exact hull/game/web-count spread;
8. promote only a narrow exact subset if causal conversion is cross-game and negative controls remain sparse/zero.

Closed work remains closed absent fresh contradictory evidence: route-equivalent Tow, Chunnel multiplicity, strict mine/web hit v5, damage-limited warp, fuel-proration v6, classic/cloudy storms, scoped sphere topology, Red Mite and verified Horwasp ballistic context.
