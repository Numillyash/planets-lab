# Normal-mine slowdown exposure follow-up

Date: 2026-08-26

Repository: `Numillyash/planets-lab`

Status: **production movement endpoint remains unchanged at 2220. Refined Stellar Cartography inventory reproduced the authoritative 116-row short-forward family and rejected Black Hole / wormhole speed effects for this corpus. The active generic follow-up is repair-hidden normal-mine slowdown exposure.**

This handoff supersedes `2026-08-26-stellar-cartography-active-inventory-pending.md` for active work.

## Verified production baseline

```text
post_fuel_proration_residual = 2220
generic_rows                 = 763
generic_hulls                = 76
dominant short-forward       = 116
```

No L1/L2 schema or accounting change is part of this follow-up.

## Closed lead — Stellar Cartography speed terrain

The first raw inventory was invalid because it used a simplified ratio bucket and counted empty/zero feature paths as active. The refined inventory fixed both issues and reproduced:

```text
target_short_forward_rows = 116
```

Refined active counts:

```text
blackholes:
  active_turns = 0
  target_active_turns = 0

settings.blackholes:
  active_turns = 0
  target_active_turns = 0

wormholes:
  active_turns = 0
  target_active_turns = 0

settings.maxwormholes:
  active_turns = 0
  target_active_turns = 0
```

Active nebula/debris state exists only on seven target-family turns total (six in game `591478`, one in game `621253`). Current Planets.nu documentation describes nebulae primarily as visibility/ability modifiers and debris disks as destruction/tow-disruption terrain, not a generic normal-movement speed limiter. Therefore Stellar Cartography does not explain the dominant family broadly.

## Active follow-up — repair-hidden normal-mine slowdown exposure

Planets.nu documents that a normal mine hit can reduce movement by 10 light-years per hit for hull tech below 7 when more than 10 light-years remain. Hull tech 7+ is not slowed by normal mine hits.

Strict mine/web v5 already explains transitions where mine-hit damage remains attributable in the historical snapshots. The complementary unresolved possibility is:

```text
normal mine hit during movement
  -> low-tech hull loses 10 ly per hit
  -> ship ends short on the submitted route
  -> later repair / historical snapshot semantics hide some or all damage evidence
```

First-pass diagnostic:

```text
tools/diagnostics/normal_mine_slowdown_exposure_audit.py
```

This first pass intentionally does **not** reconstruct hull tech, historical diplomacy, mine-hit RNG or repair. It measures an upper-bound population:

```text
owner-different normal minefield exists
planned no-hit route intersects field
planned_distance - observed_distance > 0
deficit approximately 10 * N ly
```

The route uses the current effective sphere geometry and the same post-decay minefield timing already used by the verified mine/web and Web Drain diagnostics.

Required guards:

```text
residual_view = movement_post_fuel_proration_residual
target_short_forward_rows = 116
documented_slowdown_per_hit_ly = 10
documented_not_slowed_hull_tech_threshold = 7
```

Important counters:

```text
normal_mine_route_exposure
normal_mine_multi_field_route_exposure
positive_planned_distance_deficit
deficit_near_10n

target_short_normal_mine_route_exposure
target_short_normal_mine_multi_field_route_exposure
target_short_positive_planned_distance_deficit
target_short_deficit_near_10n
```

Decision rule:

- sparse/zero target route exposure rejects this as a broad explanation;
- material exposure but sparse `10*N` geometry also rejects the slowdown hypothesis;
- material exposure plus material `10*N` geometry justifies a second pass reconstructing hull tech <7, diplomacy-safe/enemy mine ownership and damage/repair evidence;
- no production label is allowed from the exposure pass alone.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `normal_mine_slowdown_exposure_audit.py`;
3. run it without rebuilding L1/L2;
4. require the exact 116-row population guard;
5. inspect route exposure and 10*N deficit counts by game/hull;
6. only if the population is material, build the stricter tech/diplomacy/repair differential;
7. keep production accounting at `2220` throughout.

## Invariants

- GitHub `main` is source of truth.
- L1 schema remains `planets-lab.compiled-movement.v3`.
- L1 context marker remains `planets-lab.compiled-movement-storm-context.v3`.
- L2 schema remains `planets-lab.compiled-movement-context-labels.v6`.
- Web Drain remains a one-row fully attributable evidence-only case.
- outbound transfer, standard Cloak, Privateer Rob Ship and Stellar Cartography speed terrain are rejected for the current dominant family absent new evidence.
