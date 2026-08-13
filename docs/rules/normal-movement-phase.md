# Normal movement host phase

`NormalMovementPhase` is the first executable Host phase built on top of the
verified movement planner.

## Evidence-backed ordering

Planets.nu documents three major movement groups:

1. tow movement;
2. most ships / normal movement;
3. intercept movement.

The annotated Host Order additionally states that movement is sequential by
ascending Ship ID for the ordinary movement flow. The current phase therefore
processes its explicitly supplied `eligible_ship_ids` in ascending ID order.

Primary references:

- https://help.planets.nu/host-order
- https://help.planets.nu/host-order-commentary
- https://help.planets.nu/mis-intercept
- https://help.planets.nu/mis-tow

## Why eligibility is explicit

The canonical model does not yet contain a verified movement classifier that
can distinguish every tow, towed, intercept, hyperjump and special-movement
case from normal `Move Most` processing. Moving every ship through the normal
phase would therefore silently violate Host Order.

Until that classifier exists, callers must pass the exact ship IDs already
classified as eligible for normal movement. Unknown eligibility IDs are
rejected.

## Supported behavior

For each eligible ship, the phase:

1. applies submitted waypoint/warp navigation fields, falling back to the
   canonical ship's existing waypoint/warp when a field is not resubmitted;
2. calls `plan_full_normal_move()`;
3. executes complete, reachable, sufficiently fueled waypoints;
4. burns the calculated neutronium;
5. emits a structured `HostEvent` with entity identity and movement details;
6. treats Warp 0 and a waypoint at the current location as valid no-op cases.

The planner uses:

- documented `warp^2` nominal range;
- explicitly supplied Gravitonic hull classification;
- canonical movement mass;
- the selected engine's `warp1..warp9` fuel factor;
- the documented movement fuel formula.

## Fail-closed unsupported behavior

The default phase raises `UnsupportedNormalMovement` for mechanics that are not
yet reproduced exactly, including:

- partial movement toward a waypoint beyond the current-turn range;
- insufficient-fuel distance proration.

This is intentional. Returning a next-turn `GameState` with unchanged
coordinates for either case would silently produce a false simulation result.

Research/replay tooling may opt into `allow_deferred=True`. In that mode the
phase retains the submitted waypoint/warp, leaves position unchanged, and
emits `ship_deferred`. This mode is diagnostic only and is not a NuHost-equivalent
turn result.

## Still outside this phase

The following remain separate Host mechanics:

- tow and tow capture;
- intercept / chained intercept;
- mine and web mine impacts;
- warp-well capture;
- Hyperjump and Chunnel;
- debris disks and star-cluster effects;
- race/advantage movement modifiers beyond explicitly supplied Gravitonic
  classification;
- Cobol Ramscoop and other post-movement effects.

These should be added as evidence-backed phases/subphases rather than folded
into the current full-waypoint implementation.
