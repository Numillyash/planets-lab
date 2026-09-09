# Finite-fuel Tow transient storm-state runtime checkpoint — 2026-09-09

## Scope

This checkpoint records the completed historical runtime for the bounded transient ion-storm membership audit that followed the finite-fuel Tow storm-vector residual analysis.

The run is evidence mining only. It does **not** promote a Host rule, does not modify simulator mechanics, and does not transfer anything into `planets-intel`.

## Exact runtime

GitHub / server candidate:

```text
ddf1d40cdc06e47e57d02712265b09aa63192ae2
```

Source external-context gate:

```text
logs/finite-fuel-tow-external-20260909T171801Z-2c5d841f-20098
```

Collected transient gate:

```text
logs/finite-fuel-tow-transient-storm-20260909T192603Z-ddf1d40c-15232
```

All stages completed with command/tee status `0/0`:

```text
inputs
 tooling
transient-storm-state
summary
```

The inputs stage confirmed:

```text
56 classified residuals
53 clean residuals
12 archives
12 prepared caches
```

## Tow residual result

The previous storm-vector gate was reproduced exactly:

```text
clean_residual_input=53
tow_clean_cases=53
tow_after_root_vector_rows=44
tow_no_after_root_vector_match=9
tow_after_root_vector_matches=49
tow_after_root_vector_ambiguous_rows=5
```

All 44 vector-matched rows had a stable before/after root identity and stable cluster ID set:

```text
tow_rows_with_stable_root_pair=44
tow_rows_with_stable_cluster_id_set=44
```

The bounded transient cloud-state hypotheses did **not** explain the Tow membership condition:

```text
tow_any_transient_origin_qualifies=0
tow_any_transient_geometry_qualifies=0
tow_any_transient_causal_point_qualifies=0
```

Only three rows qualified under the raw before-turn cloud state at origin:

```text
tow_any_origin_qualifies=3
tow_before_raw_origin_qualifies=3
```

Those three isolated hits do not explain the 44-row family.

## Ordinary movement controls

The control population consisted of ordinary non-Tow Move Most transitions already reproduced by the current direct `ion_storm_drag` classifier and narrowed to one active after-turn root whose integer drag vector exactly equals the factual displacement.

```text
ordinary_direct_classifier_rows=236
ordinary_single_root_direct_controls=236
ordinary_control_not_single_active_root=0
ordinary_control_single_root_vector_mismatch=0
```

The current baseline reproduced all controls:

```text
control_after_raw_origin_qualifies=236
```

The bounded transient candidates remained compatible with at least one causal point for every control row:

```text
control_any_transient_origin_qualifies=236
control_any_transient_geometry_qualifies=225
control_any_transient_causal_point_qualifies=236
```

This validates the control harness and shows that the negative Tow result is not caused by a broken generic storm-state reconstruction path.

## Evidence interpretation

The 44-row Tow family still has strong vector attribution evidence: the factual `observed - direct_tow_geometry` vector exactly equals an after-turn historical root-storm integer drag vector.

However, none of the tested persisted/transient **Nu cloud local-voltage** states establishes class-4 membership at the causal Tow points (`origin` or direct Tow geometry) for those rows.

Therefore:

- the 44 rows should no longer be treated as likely fuel-proration residuals;
- the exact storm vector remains a strong external-mechanics lead;
- the tested hidden/transient cloud-state variants are rejected as an explanation of the membership condition;
- finite-fuel Tow cost-basis inference remains blocked.

## Next bounded hypothesis

The repository already carries a separate documented/research implementation for **classic ion storms** (`nuionstorms=false`) in `tools/diagnostics/classic_ion_storm_final_residual_audit.py`.

That model does not use Nu cloud local voltage. It treats the root storm as a constant-voltage circle and checks membership against the root circle radius/voltage.

This is now the highest-value next check because the observed combination is exactly what a mode mismatch could produce:

1. after-turn root heading/warp gives the correct drag vector;
2. Nu cloud local-voltage membership is absent;
3. classic constant-voltage root-circle membership has not yet been tested on this Tow residual population.

The next diagnostic must:

- reuse the same 53 clean residuals;
- preserve the exact 44 after-root-vector population;
- derive `nuionstorms` only from archived mechanics payload in the historical corpus (no new corpus search/acquisition);
- test classic root-circle membership at origin/direct Tow geometry for bounded before/after/transient root states;
- report classic/Nu/unknown mode separately;
- treat classic membership as explanatory evidence only when the game mode supports it;
- keep the 9 no-root-vector rows separate.

## Decision

Finite-fuel Tow remains:

```text
OPEN
nominal-vs-projected discriminator: NONE FOUND
```

No `planets-intel` production change is justified by this checkpoint.
