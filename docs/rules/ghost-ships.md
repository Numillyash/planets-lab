# Ghost ships

Status: `DOCUMENTED` for the canonical state represented here. Tow-capture execution is not yet implemented by this document.

## Canonical state

Planets.nu explicitly defines a ghost ship as a starship whose crew has been completely killed by radiation. Such a ship becomes unowned and belongs to no race until captured.

For `planets-lab`, this maps to:

- `Ship.owner_id = None`;
- `Ship.crew = 0` when the source exposes crew;
- `Ship.warp = 0`;
- the ship remains present in `GameState.ships` and still counts as a ship rather than being discarded as an invalid observation.

`owner_id = None` is therefore different from an unknown owner. In Planets.nu `/game/loadall` data, the corresponding observed wire representation is `ownerid = 0`.

## Behavior boundary

Documented Planets.nu behavior says ghost ships cannot fight or function and can be captured by towing; a friendly starbase can also capture/restore them according to the Stellar Cartography documentation. The current simulator only establishes the legal canonical state and prevents ordinary player orders from controlling an unowned ship. Full ghost tow-capture / crew replacement belongs to the warfare/race-mechanics implementation and remains unsupported until separately implemented and tested.

## Evidence

Primary Planets.nu documentation:

- `Starship Crew`: a ship whose crew all dies from radiation becomes unowned, a ghost ship, and can be claimed by towing;
- `Stellar Cartography`: ghost ships belong to no particular race and cannot fight or function;
- `Star Clusters`: ghost-ship warp is set to zero and tow capture supplies a minimum capture crew;
- `Scoreboard`: ghost ships are not counted as ships owned by a player but still count toward the ship limit;
- `Annotated Host Order`: ghost tow capture is a special case resolved around towing/radiation host-order steps.

Real corpus observation (`game 680910`, `Flatland Sector`) independently exposed two ship records with `ownerid = 0`, `warp = 0`, which motivated adding the documented state to the canonical model.
