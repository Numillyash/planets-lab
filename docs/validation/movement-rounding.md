# Movement coordinate differential validation

Planets.nu documents that starship positions are stored as integer X/Y coordinate pairs. For multi-turn diagonal travel, the resulting intermediate integer position can be up to about one light-year farther than the nominal speed because of rounding.

Primary source:

- https://help.planets.nu/navigation-precision

The documentation does not state the exact server-side rounding/projection algorithm. `planets-lab` therefore does not yet use any inferred rounding mode in HostEngine.

## Differential harness

`planets_lab.validation.movement_geometry` projects the documented continuous `warp^2` endpoint and compares four candidate integer conversions:

- truncation toward zero;
- floor;
- ceil;
- nearest integer using JavaScript-style `Math.round` semantics.

These are candidates only. A candidate becomes a simulator rule only after it is supported by observed consecutive NuHost turns.

The command-line helper reads CSV from stdin:

```bash
python -m planets_lab.validation.movement_rounding_cli < samples.csv
```

Required columns:

```text
turn,ship_id,x,y,target_x,target_y,warp,next_x,next_y
```

Optional column:

```text
gravitonic
```

Samples must be restricted to ordinary `Move Most` transitions that are not towing, being towed, intercepting, hyperjumping, mine-stopped, warp-well-captured or fuel-limited. Those filters belong to the extraction/validation process rather than being guessed inside the geometry helper.

Evidence status: pending `DIFF_VERIFIED`.
