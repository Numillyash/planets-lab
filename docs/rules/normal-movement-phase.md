# Normal movement host phase

`NormalMovementPhase` executes the ordinary `Move Most` subset for explicitly
classified ships.

## Ordering

Planets.nu separates movement into tow, Move Most, and intercept groups. The
phase therefore accepts explicit `eligible_ship_ids` and processes them in
ascending Ship ID order.

Primary references:

- https://help.planets.nu/host-order
- https://help.planets.nu/host-order-commentary
- https://help.planets.nu/mis-intercept
- https://help.planets.nu/mis-tow

## Baseline mode

The default remains the earlier fail-closed full-waypoint behavior. This keeps
existing callers from silently adopting inferred geometry.

## Expanded movement mode

`enable_expanded_movement=True` additionally enables:

- partial movement toward a waypoint beyond the current-turn `warp^2` range;
- nearest-integer coordinate projection after moving the documented nominal
  distance toward the waypoint;
- the documented insufficient-fuel distance proration when the waypoint itself
  is reachable within the current turn;
- the documented navigation reset when normal movement consumes the remaining
  fuel.

The nearest-coordinate projection is an evidence-backed working rule rather
than a fully universal NuHost rule. Historical differential testing found it
matched the large majority of candidate ordinary-movement observations, while
remaining mismatches include samples contaminated by special movement and
other Host interactions. It must therefore be used only after Move Most
eligibility classification.

## Still fail-closed

The combination of both:

- a waypoint beyond the nominal current-turn range, and
- insufficient fuel for that nominal partial move

remains unsupported until the ordering of those two limits is separately
verified. The phase raises `UnsupportedNormalMovement` unless diagnostic
`allow_deferred=True` is selected.

## Outside this phase

Still separate:

- tow and tow capture;
- intercept / chained intercept;
- mine and web mine impacts;
- warp-well capture;
- Hyperjump and Chunnel;
- debris disks and star-cluster effects;
- race/advantage movement modifiers beyond explicitly supplied Gravitonic
  classification;
- Cobol Ramscoop and other post-movement effects.
