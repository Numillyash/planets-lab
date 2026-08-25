# Fuel proration exact differential verified; global-stage audit pending

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **documented Planets.nu waypoint-distance fuel proration is now CORPUS_OBSERVED at the exact Host-endpoint level and clearly beats the affordable-frontier and VGAP3 controls on the current final residual. No production accounting change has been made yet. The immediate next step is a full-L1 residual overlap audit before deciding whether fuel belongs in early L1 context or a later evidence layer.**

This handoff supersedes `2026-08-25-fuel-proration-host-differential-pending.md` for active work.

## Current verified production endpoint

Unchanged:

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
label_issues                           0
```

Generic endpoint:

```text
final_residual_rows       2226
generic_rows               769
generic_games               12
generic_hulls               76
```

Dominant coarse family:

```text
119  warp7-9 <0.5x observed=other same_line_forward
```

## Current-endpoint exact Nu fuel-proration differential

Diagnostic:

```text
tools/diagnostics/fuel_proration_host_differential_audit.py
```

Population guard:

```text
residual_view= movement_post_mine_strong_residual
generic_non_horwasp_warp1_9_rows= 671
target_short_forward_rows= 119
```

Conservative first-pass population:

```text
gravitonic_excluded= 52
partial_waypoint_excluded= 106
reachable_waypoint= 513
same_identity_after= 301
identity_break_after= 212
formula_ready= 301
zero_required_fuel= 52
zero_fuel_separate_mechanic= 9
raw_mass_sufficient_for_waypoint= 221
raw_mass_insufficient_for_waypoint= 19
```

Exact rule differential:

```text
nu_proration_endpoint_exact= 6
frontier_endpoint_exact= 3
vgap3_endpoint_exact= 0
```

Rule signatures:

```text
('-', '-', '-')        13
('nu', '-', '-')        3
('nu', 'frontier', '-') 3
```

Therefore:

```text
Nu exact total = 6
Nu-only exact  = 3
Nu+frontier    = 3
VGAP3 exact    = 0
```

This is direct rule discrimination in favor of documented Nu waypoint proration rather than merely a generic correlation with low fuel.

Exact Nu coverage:

```text
hulls:
  96 -> 2
  17 -> 2
  31 -> 1
  78 -> 1

games:
  620694 -> 4
  360690 -> 1
  620636 -> 1
```

Inside the dominant 119-row family:

```text
target_short_reachable_waypoint= 95
target_short_formula_ready= 95
target_short_raw_mass_insufficient_for_waypoint= 4
target_short_nu_proration_endpoint_exact= 3
target_short_frontier_endpoint_exact= 2
target_short_vgap3_endpoint_exact= 0
```

So fuel proration explains a real but sparse subset of the dominant family; it is not the main cause of the remaining short-forward residual.

## Critical snapshot-provenance correction

The exact audit also reported:

```text
post_out_of_fuel_reset= 0
nu_proration_strong= 0
```

Do **not** interpret this as evidence against Planets.nu's documented out-of-fuel reset.

Planets.nu Time Machine documentation states that historical turns reproduce the saved end-of-turn state, including orders successfully filed before the end of that historical turn. `/game/loadall` supplies those historical turn payloads.

Therefore an `after` owner record is the next historical end-turn snapshot, not an immediate post-Host movement frame for editable fields. By that time the player may have:

- selected a new warp;
- selected a new waypoint;
- performed own cargo/fuel transfers;
- otherwise changed client-side orders for the next Host run.

Consequences for corpus evidence:

```text
x/y after       -> valid Host movement outcome
owner/hull/identity continuity -> useful continuity guard
warp after      -> NOT a mandatory immediate post-move assertion
target after    -> NOT a mandatory immediate post-move assertion
fuel after      -> NOT a mandatory immediate post-move assertion
```

The official normal-operation out-of-fuel rule still documents Warp 0 + waypoint=current when movement consumes the remaining fuel. The historical corpus simply does not preserve that immediate moment cleanly enough to require it as a promotion gate.

This provenance caveat also applies to earlier diagnostics whenever next-turn editable order/cargo fields were used as supportive evidence. It does not invalidate fail-closed classifiers that merely required such a state when present; it does mean absence of the state is not negative evidence.

## Documented rule and existing implementation

Planets.nu `Fuel Consumption Details` documents:

```text
Fuel Use = TRUNC(
    Fuel Factor
    * TRUNC(Total Mass / 10)
    * TRUNC(Distance Traveled)
    / Max Distance Per Turn
    / 10000
)
```

and explicitly states that if waypoint fuel required exceeds available fuel, actual travel distance is prorated against the waypoint trip. Its example is a 60-ly trip requiring 12 KT traveling 55 ly when only 11 KT is available, even though 11 KT could otherwise afford 59 ly.

Repository primitives already implement this:

```text
src/planets_lab/rules/fuel.py
src/planets_lab/rules/proration.py
src/planets_lab/sim/normal_movement.py
```

No simulator-rule change is required for this corpus investigation.

## Why production is not promoted yet

The six exact rows were discovered after all current downstream L2 closures:

```text
movement_post_mine_strong_residual
```

That proves they survive current Chunnel/Horwasp/mine labels, but it does **not** prove that identical exact fuel signatures do not also occur in earlier L1 residual rows later explained by those mechanics.

Adding fuel directly to the early L1 external-context stack without checking global overlap could therefore steal rows from already verified downstream mechanics or hide compound events.

Also, raw snapshot `mass` is a useful candidate movement mass but Host documentation notes several operations before movement that can alter the actual movement mass. Exact endpoint matching is strong positive evidence for rows where raw mass happens to be compatible; non-matches are not evidence against fuel proration.

## New global-stage audit

Diagnostic:

```text
tools/diagnostics/fuel_proration_global_stage_audit.py
```

It scans the full current L1 residual:

```text
movement_residual
```

and uses the same conservative first-pass mechanics:

```text
non-Horwasp
non-Gravitonic
warp 1..9
reachable waypoint
same owner/hull identity across the transition
resolved race/damage guard
raw damage does not limit requested warp
positive fuel
raw mass/engine formula ready
raw mass predicts insufficient waypoint fuel
exact documented Nu Host-major/minor endpoint
```

It then partitions every exact Nu match by current downstream stage:

```text
chunnel_explained
horwasp_strong_explained
mine_strong_explained
post_mine_strong_residual
other
```

and separately counts `Nu-only` matches that do not also match the old frontier or VGAP3 controls.

## Decision rule after global audit

If all exact Nu matches are in `post_mine_strong_residual` and `other=0`, a narrow production fuel context can be considered without stealing verified downstream rows.

If exact Nu matches overlap Chunnel/Horwasp/mine:

- do not add an unconditional early L1 fuel classifier;
- inspect whether the overlaps are compound mechanics or endpoint coincidence;
- prefer a later evidence-layer label if separation cannot be made causal and fail-closed.

Do not require next-turn reset fields as the deciding guard.

## Immediate work

1. pull current `main` and confirm clean status;
2. syntax-check `tools/diagnostics/fuel_proration_global_stage_audit.py`;
3. run it against the current compiled corpus;
4. inspect `nu_proration_endpoint_exact` and `nu_only_endpoint_exact`;
5. require complete downstream-stage accounting for all exact rows;
6. inspect whether any exact or Nu-only rows overlap Chunnel/Horwasp/mine;
7. only then choose L1 vs late evidence-layer placement;
8. do not change production counts before this overlap result is known.

## Guardrails

- Current production endpoint remains `2226`.
- Damage-limited warp remains closed.
- The old seven affordable-frontier `strong_fuel_limit_signature` rows remain historical correlation only.
- `nu_proration_strong=0` from the prior diagnostic is a snapshot-provenance artifact, not a failed mechanics test.
- Do not use absence of next-turn Warp0/waypoint reset as negative evidence.
- Keep partial-waypoint, Gravitonic and zero-fuel fuel semantics outside this first production subset.
- Do not reopen Tow/Chunnel/mine/Red Mite without fresh contradictory evidence.
- Do not generalize game `591478`'s 2170 period.
- Preserve private raw state locally; emit only derived mechanical evidence.
