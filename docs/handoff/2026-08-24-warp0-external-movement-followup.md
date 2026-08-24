# Generic movement residual — warp-zero external movement follow-up

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **generic fuel-limited movement is confirmed as a small contributor; warp-zero external displacement is the next active investigation.**

This handoff supersedes `2026-08-24-generic-fuel-followup.md` for current priorities.

## Runtime baseline

The compiled 12-game movement baseline is unchanged:

```text
move_most_candidates              227468
post_external_residual              3938
post_chunnel_residual               2551
post_horwasp_strong_residual        2311
```

## Generic fuel-limited audit result

Focused diagnostic:

```text
tools/diagnostics/generic_fuel_limited_residual_audit.py
```

Runtime population:

```text
generic_non_horwasp_warp1_9_rows   730
gravitionic_excluded                 53
same_line_forward                   239
short_same_line_forward             216
candidate_same_identity_after       215
candidate_formula_ready             216
```

Fuel formula evidence:

```text
observed_affordable                 212
sufficient_for_regular              200
insufficient_for_regular             16
formula_brackets_observed            12
affordable_frontier_match             8
depleted_after                       42
strong_fuel_limit_signature           7
```

Strong signatures occur across six hull IDs and four games:

```text
hulls:
  17  -> 2
  105 -> 1
  61  -> 1
  94  -> 1
  31  -> 1
  78  -> 1

games:
  620694 -> 3
  620636 -> 2
  360690 -> 1
  511506 -> 1
```

The seven strong rows satisfy all focused guardrails: same ship identity, insufficient fuel for the regular move, observed move affordable by the documented formula, observed distance near the affordable whole-light-year frontier, and zero fuel after the move.

Interpretation:

- fuel-limited/prorated movement is a real generic contributor in the current residual;
- coverage is only `7 / 216` short same-line candidates under the strict signature, so it does not explain the main generic residual family;
- `200 / 216` short same-line candidates have enough raw-snapshot fuel for the regular move under the correlation formula, so a broad production fuel-context pass would overfit badly;
- raw snapshot mass remains correlation evidence rather than exact post-host-order movement mass, so these seven rows are not yet sufficient to alter L1 accounting.

Fuel proration therefore returns to **verified minor contributor / low current priority**. Preserve the seven examples as evidence, but do not promote a broad residual classifier from them.

## Next active target — warp-zero external displacement

The broad clustering audit found:

```text
warp0 + target=origin + external move
119 rows / 35 hulls / 8 games
```

This is now the highest-value generic context family because ordinary self-waypoint geometry predicts no movement while the stored ship position changes externally.

New focused diagnostic:

```text
tools/diagnostics/warp0_external_move_context_audit.py
```

The audit is designed to distinguish several causal families without promoting any rule:

1. **visible explicit tow** — another ship is co-located before, shares the exact observed destination after, has an owner-visible `TOW_ATTEMPT`, and explicitly targets the candidate ship;
2. **hidden/unresolved co-mover** — another ship is co-located before and shares the destination after, but its owner-private tow mission cannot be resolved; this is a strong lead for enemy/private tow context;
3. **visible non-tow co-mover** — shared external motion exists but the visible mover is not an explicit tower of the candidate;
4. **effective-topology storm vector match** — the observed displacement vector equals the authoritative classic/cloudy ion-storm offset when measured under the effective topology, catching potential sphere-coordinate misses in the storm layer;
5. **other unexplained** — no co-moving ship or storm-vector evidence.

The audit uses effective `2170x2170` topology only for game `591478`, preserving raw topology facts.

Implementation commit:

```text
0a74225  Add warp-zero external movement context audit
```

## Immediate next step

Run:

```bash
docker compose run --rm -T lab \
  python -m py_compile tools/diagnostics/warp0_external_move_context_audit.py

docker compose run --rm -T lab \
  python -u tools/diagnostics/warp0_external_move_context_audit.py \
  | tee /tmp/warp0_external_move_context_audit.log
```

Interpret these first:

```text
candidate_rows
has_colocated_same_destination_comover
single_colocated_same_destination_comover
visible_explicit_tow_target_match
has_hidden_or_unresolved_comover
has_visible_non_tow_comover
effective_topology_storm_vector_match
```

A high co-mover rate across multiple hulls/games would support tow/shared transport as the generic cause. A high storm-vector rate concentrated in sphere game `591478` would instead indicate a topology bug in storm displacement. If neither is broad, inspect the `other unexplained` examples before adding another hypothesis.

## Guardrails

- Do not classify all co-moving pairs as tow; shared storm/transport displacement can produce the same geometry.
- Do not infer enemy tow missions from unavailable private fields; report them only as hidden/unresolved co-mover evidence.
- Do not generalize game `591478`'s effective period beyond its audited scope.
- Do not reopen Red Mite or known Horwasp clusters during this generic pass.
- Production promotion requires cross-sample causal evidence and fail-closed tests.
