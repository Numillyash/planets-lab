# Refined Stellar Cartography active-feature inventory follow-up

Date: 2026-08-26

Repository: `Numillyash/planets-lab`

Status: **production movement endpoint remains unchanged at 2220. The first Stellar Cartography raw-path inventory is invalid for target-family attribution because it measured 126 rows instead of the authoritative 116 and counted empty/zero JSON paths as feature presence. The diagnostic has been corrected; the active task is to rerun the refined active/non-zero inventory before deciding whether any terrain-speed mechanic deserves a geometry model.**

This handoff supersedes `2026-08-26-stellar-cartography-feature-inventory-pending.md` for active work.

## Verified production baseline

```text
post_fuel_proration_residual = 2220
generic_rows                 = 763
generic_hulls                = 76
dominant short-forward       = 116
```

No L1/L2 schema or accounting change is part of this follow-up.

## Recently rejected leads

The following cannot explain the dominant 116-row family:

```text
outbound fuel transfer: target_short_outbound_fuel_transfer = 0
standard Cloak fuel:     target_short_cloak_mission = 0
Privateer Rob Ship:      target_short_rob_exposure_candidate = 0
```

Crystal Web Drain remains one fully attributable evidence-only row and is not production-promoted.

## First Stellar Cartography inventory — invalid target attribution

The first runtime pass printed:

```text
residual_view = movement_post_fuel_proration_residual
generic_non_horwasp_warp1_9_rows = 665
target_short_forward_rows = 126
```

The authoritative post-v6 generic clustering baseline is 116, so the terrain target-turn counts from that pass must not be used as mechanics evidence.

Root cause: the inventory used a simplified ratio bucket that classified every ratio below 0.5 as `<0.5x`. The authoritative clustering reserves `~0.5x` for ratios within ±0.08 of 0.5. Ten rows were therefore incorrectly added to the target population.

The same pass also counted raw JSON-path existence rather than actual feature activation. For example, entries such as:

```text
blackholes: []
settings.blackholes = 0
```

were counted as Black Hole path occurrences. Likewise `nebulas: []`, `wormholes: []`, zero debris flags and zero/false settings were schema presence, not active feature evidence.

## Corrected diagnostic

`tools/diagnostics/stellar_cartography_raw_feature_inventory.py` now:

1. uses the same `~0.5x/~1.0x/...` ratio-bucket semantics as `post_sphere_generic_residual_clustering_audit.py`;
2. must reproduce `target_short_forward_rows = 116`;
3. counts feature paths once per turn instead of counting every repeated entity value as a turn occurrence;
4. separates:
   - `present_turns` — JSON/schema path exists;
   - `active_turns` — at least one non-empty/non-zero value exists on that turn;
   - `active_values` — number of active values/instances;
   - corresponding `target_*` counters;
5. treats empty lists, zero numbers and false booleans as inactive;
6. prints safe excerpts for non-empty lists without emitting identity/secrets/arbitrary text.

Important outputs:

```text
target_short_forward_rows

GLOBAL FEATURE PATHS:
  present_turns
  active_turns
  active_values
  target_present_turns
  target_active_turns
  target_active_values
```

## Decision rule

- If `target_short_forward_rows != 116`, stop and fix the diagnostic again.
- Path presence alone is never evidence.
- If `blackholes` and `settings.blackholes` have `active_turns = 0`, reject Black Hole terrain for this corpus regardless of path presence.
- If an active movement-relevant terrain feature exists globally but `target_active_turns = 0`, reject it for the dominant family.
- Only active/non-zero terrain on target turns can justify a narrow geometry/timing audit.
- Do not infer a movement effect from nebula/debris/wormhole schema presence alone; use documented mechanics and actual object geometry.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check the corrected inventory;
3. rerun it with `--max-examples-per-path 3`;
4. require exactly `target_short_forward_rows = 116`;
5. inspect `blackholes` and `settings.blackholes` active counts first;
6. then inspect active `wormholes`, `nebulas`, and non-zero `planets.[].debrisdisk` only as population evidence;
7. build no terrain classifier until an active movement-relevant feature overlaps the target turns;
8. keep production accounting at 2220 throughout.

## Invariants

- GitHub `main` is source of truth.
- L1 schema remains `planets-lab.compiled-movement.v3`.
- L1 context marker remains `planets-lab.compiled-movement-storm-context.v3`.
- L2 schema remains `planets-lab.compiled-movement-context-labels.v6`.
- Current authoritative final movement residual remains 2220.
- Closed mechanics and rejected leads stay closed absent contradictory evidence.
