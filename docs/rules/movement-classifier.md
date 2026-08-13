# Movement classifier

Planets.nu movement order is Tow, Move Most, then Intercept.

Sources:
- https://help.planets.nu/host-order
- https://help.planets.nu/mis-tow
- https://help.planets.nu/mis-intercept
- https://help.planets.nu/mis-hyperjump

`classify_movement_intents()` partitions ships before tow-lock resolution.

The default Nu mission convention uses mission 6 for Tow and mission 7 for Intercept. The convention is injectable.

Ships with `HYP` friendly code are separated from ordinary Move Most because Hyperjump needs its own movement implementation.

`move_most_candidate_ship_ids` is intentionally only a candidate set. A successfully towed target must later be removed after tow resolution.

The loadturn importer also preserves `mission1target` and `mission2target` as raw canonical target IDs without assigning unverified semantics.
