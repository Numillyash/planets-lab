# Hyperjump

Hyperjump is a special Move Most movement selected by Friendly Code `HYP` on a hyperjump-capable hull.

Official Planets.nu rules used by this simulator:

- the ship must be hyperjump-capable;
- warp must be greater than 0;
- the selected waypoint must be more than 20 ly away;
- a successful hyperjump consumes 50 KT Neutronium;
- a waypoint 340-360 ly away is the exact jump destination;
- otherwise NuHost moves approximately 350 ly along the selected course;
- towing a ship cancels its hyperjump;
- hyperjump is processed in Move Most;
- planetary warp wells affect hyperjump only inside the inner two rings / under 3 ly.

Current implementation scope will initially support exact 340-360 ly jumps only. The default 350-ly projected endpoint remains fail-closed until its integer-coordinate projection is differentially verified.

Sources:

- https://help.planets.nu/mis-hyperjump
- https://help.planets.nu/friendly-codes
- https://help.planets.nu/host-order
- https://help.planets.nu/default-config
