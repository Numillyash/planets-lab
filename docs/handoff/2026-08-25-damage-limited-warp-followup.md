# Damage-limited warp follow-up

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **route-equivalent Tow v3 is closed and the post-v3 final residual has been rebaselined. The next focused movement differential is documented damage-limited maximum warp, with production unchanged pending runtime evidence.**

This handoff supersedes `2026-08-24-route-equivalent-tow-verified.md` for active triage. Tow v3, mine/web v5, Chunnel v4, classic ion storms, scoped sphere topology and Red Mite remain closed absent fresh contradictory evidence.

## Current verified movement accounting

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

Current schemas remain L1 `planets-lab.compiled-movement.v3` + L2 `planets-lab.compiled-movement-context-labels.v5`.

## Verified post-v3 generic rebaseline

Diagnostic:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

Runtime result:

```text
final_residual_rows       2236
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               779
generic_games               12
generic_hulls               78
```

Compared with the historical post-v5 / pre-Tow-v3 baseline:

```text
final residual  2240 -> 2236  (-4)
generic rows      783 ->  779  (-4)
generic hulls      79 ->   78  (-1)
```

The four removed rows belonged entirely to the Warp-0 target-at-origin family. The main coarse signatures changed as follows:

```text
121 -> 121  warp7-9 <0.5x     observed=other same_line_forward
 97 ->  93  warp0   nominal<=0 target=origin
 64 ->  64  warp7-9 <0.5x     observed=origin stationary
 52 ->  52  warp7-9 >3.0x     target=origin
 48 ->  48  warp7-9 0.5-1.0x observed=other same_line_forward
 46 ->  46  warp7-9 >3.0x     observed=other oblique
```

Thus route-equivalent Tow did not affect the dominant short-forward family.

## Target-origin Tow control after v3

Focused control rerun:

```text
candidate_rows                              222
post_warp0                                  112
has_same_origin_destination_comover          31
has_hidden_or_unresolved_comover              0
has_visible_non_tow_comover                  31
has_visible_tow_targeter                     88
visible_tow_targeter_other_destination       88
any_visible_matching_tower                    0
single_visible_matching_tower                 0
route_equivalent_multiple_visible_towers      0
post_warp0_with_visible_matching_tower        0
post_warp0_with_multiple_visible_towers       0
```

Tow route-equivalence is therefore closed. Visible non-Tow co-movers remain evidence-only and are not a Tow classifier.

## Next focused hypothesis: damage-limited warp

The largest current cross-hull/cross-game family is still:

```text
121  warp7-9 <0.5x observed=other same_line_forward
     26 hulls / 7 games
```

Official Planets.nu documentation states that sufficiently damaged ships have reduced maximum warp. For standard races the maximum speed falls as damage passes successive 10% bands after the first; Lizards use their separate higher-damage survival/speed table. Host Order also places `Mass check, repair, & MKT` before towing/Most Ships Move, so supply/starbase repair can alter the effective damage immediately before movement.

New diagnostic:

```text
tools/diagnostics/damage_limited_warp_residual_audit.py
```

It reads the current `movement_post_mine_strong_residual` endpoint and checks all generic non-Horwasp Warp 1-9 rows, while reporting the 121-row family separately.

The audit compares:

- requested warp;
- owner race (`raceid=2` for Lizard handling);
- raw before-turn damage;
- documented damage-limited maximum warp;
- Gravitonic distance doubling where applicable;
- evidence-scoped effective sphere topology;
- exact Host-major/minor predicted destination;
- a conservative repair bracket from currently onboard supplies (`5 KT -> 1%`);
- same-identity continuity.

### Strong evidence

The strongest pre-production subset is:

```text
requested_warp > damage_limited_max_warp
AND exact Host-major/minor destination match
```

`raw_exact_low_supply` is an especially clean subset because `<5 KT` onboard supplies cannot repair even 1% from the visible current cargo alone.

### Evidence-only repair bracket

`current_supply_bracket_endpoint_exact` is not production-ready by itself. Transfers, starbase repair and other pre-movement Host-order effects can change damage/supplies before Most Ships Move, so current supplies only provide a conservative local bracket.

### Negative controls

Before any production change, inspect:

```text
raw_not_damage_limited_endpoint_exact_control
undamaged_endpoint_exact_control
```

These should be zero or otherwise fully understood. An exact match without an actual damage speed limit would indicate that the classifier is not causally specific enough.

## Existing fuel audit

`tools/diagnostics/generic_fuel_limited_residual_audit.py` still reads the historical `movement_post_horwasp_strong_residual` endpoint. Its old finding (`7` strong fuel-limit signatures) remains useful evidence that fuel proration is real but sparse, but its population counts are not the current post-v3 baseline. Do not use it for new accounting without first parameterizing it to the current final view.

## Immediate work

1. pull current `main` and confirm a clean tree;
2. syntax-check `damage_limited_warp_residual_audit.py`;
3. run it against the current local compiled corpus;
4. confirm `target_short_forward_rows = 121` as a population guard;
5. inspect exact raw-damage matches, low-supply subset, hull/game/race spread and effective-warp distribution;
6. inspect both negative controls before considering production;
7. if exact damage-limited signatures are material and causal, build a narrow regression-backed external-context classifier with an independent pre-build differential;
8. otherwise leave damage-limit unpromoted and return to fuel/other short-forward causes.

## Guardrails

- Do not reopen route-equivalent Tow; both global and target-origin post-fix controls are zero.
- Do not infer hidden Tow from visible non-Tow co-movement.
- Do not broaden mine/web labels to repair-bracket-only rows.
- Do not treat current-supplies repair brackets as exact Host reconstruction.
- Do not generalize game `591478`'s 2170 effective sphere period.
- Do not promote hull-specific rules from hull counts alone.
- Preserve raw facts separately from inferred/effective mechanics context.
