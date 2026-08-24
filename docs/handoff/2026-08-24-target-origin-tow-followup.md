# Target-origin tow residual follow-up

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **post-v5 generic residual rebaseline complete; next focused lead is target-at-origin external movement and route-equivalent tow multiplicity.**

This handoff supersedes `2026-08-24-post-v5-generic-rebaseline-pending.md` for the active movement investigation. Mine/web v5, Chunnel v4, classic ion storms, scoped sphere topology and Red Mite closure remain closed unless fresh evidence appears.

## Verified current accounting

```text
move_most_candidates              227468
post_external_residual              3938
chunnel_explained                   1421
post_chunnel_residual               2517
horwasp_strong_explained             240
post_horwasp_strong_residual        2277
mine_strong_explained                 37
post_mine_strong_residual           2240
label_issues                           0
```

Mine/web v5 is fully `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`. Targeted v5 regressions and the full repository pytest suite are green on clean `main`.

## Post-v5 generic rebaseline

The broad clustering now reads the final v5 layer by default:

```text
movement_post_mine_strong_residual
```

Runtime result:

```text
final_residual_rows       2240
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               783
generic_games               12
generic_hulls               79
```

The arithmetic `820 - 37 = 783` was therefore confirmed exactly; every strict mine/web closure was non-Horwasp and disappeared from the generic triage population.

Largest current coarse cross-game signatures:

```text
warp7-9  <0.5x   observed=other  same_line_forward   121
warp0    nominal<=0 target=origin target_is_origin    97
warp7-9  <0.5x   observed=origin stationary          64
warp7-9  >3.0x   target=origin   target_is_origin     52
warp7-9  0.5-1.0x observed=other same_line_forward    48
warp7-9  >3.0x   observed=other  oblique              46
```

Other useful totals:

```text
baseline above_nominal          265
baseline reachable_other        255
baseline warp_zero_external     102
baseline partial_other           84
baseline reachable_stayed        52
baseline partial_stayed          25

target_relation target=origin   226
direction same_line_forward     245
direction stationary             77
```

Short-forward movement remains the largest family after strict mine removal, but it is still heterogeneous. The target-at-origin family is now a stronger causal lead because it directly indicates movement not explained by the ship's own waypoint.

## Why tow is the next focused lead

Official Planets.nu tow behavior says that a successful tow:

1. moves the target to the towing ship's destination;
2. leaves the towed ship at speed / warp 0;
3. resolves in the tow movement phase before Move Most.

The compiled corpus already has an owner-visible observed-tow context layer. Its helper `_observed_tow_targets()` collects matching towers that:

- start colocated with the target;
- have an owner-visible Tow mission targeting that ship;
- finish at the same observed destination as the target;
- actually move.

However, the current helper explains the target only when exactly one such tower exists. If two or more matching towers exist it records `observed_tow_target_ambiguous` and leaves the target residual.

That creates a possible route-equivalent semantic defect analogous to Chunnel v4: tower identity may be ambiguous, but if every matching tower starts with the target and ends at the same observed endpoint, the target movement route is already explained.

## New diagnostic

```text
tools/diagnostics/target_origin_tow_residual_audit.py
```

Population:

- final `movement_post_mine_strong_residual`;
- non-Horwasp rows;
- `target_x = x_before` and `target_y = y_before`;
- ship actually moved.

The broad clustering predicts:

```text
candidate_rows = 226
```

The diagnostic measures:

```text
post_warp0
has_same_origin_destination_comover
has_hidden_or_unresolved_comover
has_visible_non_tow_comover
has_visible_tow_targeter
visible_tow_targeter_other_destination
any_visible_matching_tower
single_visible_matching_tower
route_equivalent_multiple_visible_towers
post_warp0_with_visible_matching_tower
post_warp0_with_multiple_visible_towers
post_warp0_with_comover
post_warp0_hidden_comover_without_visible_tow
post_warp0_visible_non_tow_comover_without_visible_tow
post_warp0_without_comover
```

It also prints visible matching-tower multiplicity and sanitized mechanical examples. No account IDs are emitted.

## Interpretation rules

Strongest possible result:

- `route_equivalent_multiple_visible_towers > 0`;
- `single_visible_matching_tower = 0` or near zero;
- matching rows also preferentially have post-state `warp=0`.

That would isolate a narrow current-detector semantic gap. As with Chunnel, production can then explain movement without pretending to know which tower identity won the lock.

A weaker but still useful lead is:

- post-state `warp=0`;
- same-origin/same-destination co-mover;
- no owner-visible tow mission.

Treat those as hidden/unresolved tow candidates only, not production labels. The current corpus does not justify inferring an unseen mission from co-movement alone.

## Immediate next step

Run:

```bash
cd ~/projects/planets-lab
set -o pipefail

git pull --ff-only origin main

echo "===== HEAD ====="
git rev-parse --short HEAD

echo
echo "===== STATUS ====="
git status --short

echo
echo "===== SYNTAX CHECK ====="
docker compose run --rm -T lab \
  python -m py_compile \
  tools/diagnostics/target_origin_tow_residual_audit.py

echo
echo "===== TARGET-ORIGIN TOW AUDIT ====="
docker compose run --rm -T lab \
  python -u tools/diagnostics/target_origin_tow_residual_audit.py \
  | tee /tmp/target_origin_tow_residual_audit.log

echo
echo "===== STATUS AFTER ====="
git status --short
```

## Evidence guardrails

- Do not promote hidden/unresolved co-movement to tow without stronger evidence.
- Do not broaden mine labels to repair-bracket rows yet.
- Do not reopen Chunnel route-equivalent ambiguity; it is fixed and verified.
- Do not reopen Red Mite without fresh evidence.
- Keep current external-context counts stable until a separate tow differential predicts an exact production delta.
- Prefer route-equivalent movement semantics over event-identity overfitting when all candidate events already imply the same observed route.
