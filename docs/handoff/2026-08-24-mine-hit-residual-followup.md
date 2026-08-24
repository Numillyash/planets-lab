# Mine/web-hit movement residual — focused follow-up

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **post-v4 residual landscape rebaselined; focused mine/web-hit diagnostic implemented; runtime audit pending**.

This handoff supersedes `2026-08-24-chunnel-route-equivalent-verified.md` for the active movement investigation. Chunnel v4 remains closed and verified.

## Current runtime-verified corpus baseline

```text
move_most_candidates              227468
post_external_residual              3938
chunnel_explained                   1421
post_chunnel_residual               2517
horwasp_strong_explained             240
post_horwasp_strong_residual        2277
```

Chunnel route-equivalent multi-event handling is **TESTED + DIFF_VERIFIED** and must not be reopened absent new evidence.

## Post-v4 generic residual rebaseline

Diagnostic:

```text
tools/diagnostics/post_sphere_generic_residual_clustering_audit.py
```

Measured after the Chunnel v4 fix:

```text
final_residual_rows       2277
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               820
generic_games               12
generic_hulls               81
```

The old pre-v4 generic population was 854 rows. The exact `854 -> 820` change confirms that the 34 Chunnel route-equivalent false residuals were removed without changing the generic population definition.

Largest current generic signatures include:

```text
warp7-9  <0.5x    observed=other  same_line_forward   133 rows / 26 hulls / 7 games
warp0    nominal<=0 target=origin target_is_origin     97 rows / 33 hulls / 8 games
warp7-9  0.5-1.0x observed=other  same_line_forward    70 rows / 26 hulls / 8 games
warp7-9  <0.5x    observed=origin observed_stationary   64 rows / 30 hulls / 5 games
warp7-9  >3.0x    target=origin   target_is_origin      52 rows / 15 hulls / 4 games
warp7-9  >3.0x    observed=other  oblique               46 rows / 21 hulls / 4 games
```

The current generic residual is therefore not dominated by one hull-specific special ability.

## Post-v4 Warp-0 rebaseline

Diagnostic:

```text
tools/diagnostics/warp0_external_move_context_audit.py
```

Measured population:

```text
candidate_rows                                97
has_colocated_same_destination_comover        11
single_colocated_same_destination_comover      3
visible_explicit_tow_target_match              4
has_hidden_or_unresolved_comover               0
has_visible_non_tow_comover                   11
effective_topology_storm_vector_match          0
```

The old pre-v4 population was 119 rows; exactly 22 Warp-0 Chunnel false residuals were removed by v4, giving the expected `119 -> 97`.

Ordinary visible tow and effective-topology ion-storm displacement remain sparse explanations. Warp-0 is still heterogeneous and is not the next broad production target.

## Intercept hypothesis checked and rejected for this corpus layer

The simulator already has an Intercept phase, and Intercept is a plausible geometric cause of above-nominal movement when ordinary waypoint coordinates are irrelevant.

However the historical corpus movement intent classifier already classifies owner mission `7` as `INTERCEPT` and excludes it from `MOVE_MOST_CANDIDATE` before compiled movement residuals are formed:

```text
src/planets_lab/corpus/movement_context.py
```

Therefore the current generic `MOVE_MOST_CANDIDATE` residual should not be reclassified as ordinary visible Intercept merely from geometry. Any future Intercept revisit requires evidence that owner mission reconstruction itself is wrong or incomplete.

## Active lead: mine/web-mine interruption

The strongest current generic family is short movement along the intended waypoint line. Prior fuel analysis found only seven strict fuel-limit signatures among 216 short same-line candidates, so fuel shortage is real but not the broad cause.

Official Planets.nu minefield rules provide two causally testable signatures:

- normal mine hits can reduce movement by 10 ly per hit for hulls below the configured tech threshold;
- a web-mine hit stops the ship immediately and sets Warp 0; out-of-fuel/web-hit rules also reset the waypoint to the current location.

Primary sources:

- `https://help.planets.nu/minefields`
- `https://help.planets.nu/out-of-fuel`

Minefield records are already retained in normalized `mechanics_payload` even though canonical `GameState` does not yet model them.

Focused diagnostic:

```text
tools/diagnostics/mine_hit_residual_audit.py
```

The diagnostic reads private prepared state locally but prints only derived mechanical evidence.

### Evidence levels

`web_state_signature` requires:

- generic non-Horwasp short same-line movement;
- surviving owner-state damage increase;
- after-state `warp=0`;
- after-state waypoint reset to the observed endpoint.

`web_strong` additionally requires an enemy web minefield containing the observed endpoint in at least one available perspective.

`normal_mine_strong` requires:

- generic short same-line movement;
- surviving owner-state damage increase;
- hull tech below 7;
- lost movement distance near an integer multiple of 10 ly;
- a parseable observed enemy normal-mine field intersecting the expected movement corridor.

The script separately reports owner-perspective vs any-perspective field visibility and raw minefield keysets/radius-source coverage. Absence of a visible minefield must not be interpreted as proof that no minefield existed.

## Important limitations

Do not promote mine/web classification from field overlap alone.

Minefield state can change between the two turn snapshots through laying, decay, destruction, pull/push and other pre-movement effects. Full production classification will need correct Host-order field reconstruction or a narrower fail-closed signature.

Sphere game `591478` continues to use only the independently verified effective `2170x2170` topology for geometric diagnostics; raw topology remains unchanged.

## Immediate next step

1. Pull current `main`.
2. Syntax-check `tools/diagnostics/mine_hit_residual_audit.py`.
3. Run the diagnostic against the current `2277` final residual.
4. Preserve the complete output, especially:
   - `short_same_line_forward`;
   - `damage_increase`;
   - `post_warp0_waypoint_reset`;
   - `web_state_signature`;
   - `owner_visible_web_at_observed`;
   - `any_visible_web_at_observed`;
   - `web_strong`;
   - `normal_mine_10ly_geometry`;
   - `any_visible_normal_field_crossing`;
   - `normal_mine_strong`;
   - minefield raw keysets and radius-source coverage.
5. If web/normal signatures are material across multiple hulls and games, build a narrower Host-order-aware differential before touching production labels.
6. If mine signatures are sparse, return to the remaining short-forward/stationary families rather than overfitting minefields.
7. Keep Horwasp 201-213, Red Mite and closed Chunnel work outside generic prioritization.
