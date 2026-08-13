# Insufficient-fuel movement proration

Planets.nu documents a movement rule that differs from classic VGA Planets when a ship has some fuel but not enough to reach the current waypoint.

For Planets.nu, the distance limit is proportional to the distance to the current waypoint:

```text
actual_distance = waypoint_distance * fuel_available / fuel_required
```

The documentation gives the concrete example that a 60 light-year trip requiring 12 KT, with only 11 KT aboard, results in 55 light-years traveled.

Primary sources:

- https://help.planets.nu/fuel-details
- https://help.planets.nu/VGAP-3-differences
- https://help.planets.nu/FuelEstimateErrors

## Implementation boundary

`prorate_waypoint_distance()` implements only the continuous distance ratio. It deliberately does not convert that distance into an integer `(x, y)` destination.

Planets.nu separately documents that all positions are stored as integer coordinate pairs and that intermediate positions on diagonal multi-turn trips can be up to about one light-year farther than the nominal speed because of coordinate rounding:

- https://help.planets.nu/navigation-precision

The exact server-side projection/rounding rule is not specified there. It must therefore be established with differential observations before HostEngine mutates coordinates for partial movement.

Evidence status:

- proration ratio: `DOCUMENTED`
- integer coordinate projection after proration: pending `DIFF_VERIFIED`
