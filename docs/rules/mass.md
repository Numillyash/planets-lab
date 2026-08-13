# Ship movement mass

Planets.nu documents the mass used by normal movement fuel calculation as the sum of:

- hull mass (already including engine mass);
- fitted beam weapon mass;
- fitted torpedo tube mass;
- carried torpedoes;
- carried fighters;
- neutronium fuel;
- supplies;
- colonist clans;
- duranium, tritanium and molybdenum;
- plus the same categories for a towed ship when towing applies.

MegaCredits and crew are not listed as movement-mass terms.

Primary source:

- https://help.planets.nu/fuel-details

Supporting component/munition sources:

- https://help.planets.nu/torpedo-tubes
- https://help.planets.nu/combat-mass

Implementation policy for the current M1 helper:

1. use `HullSpec.mass` directly because the documented hull mass includes engine mass;
2. use actual fitted `Ship.beam_count` and `Ship.torpedo_launcher_count`, not hull slot maxima;
3. multiply fitted beam count by the selected `BeamSpec.mass`;
4. multiply fitted tube count by the selected `TorpedoSpec.mass`;
5. count each carried torpedo as 1 KT, consistent with the documented 1 KT cargo size;
6. count each short-range fighter as 1 KT; Planets.nu explicitly gives a short-range fighter a 1 KT mass and movement rules include carried fighters in total mass;
7. add fuel, supplies, clans and the three minerals at their KT quantities;
8. do not include MegaCredits;
9. reject unresolved Nu `ammo` rather than silently producing an incorrect movement mass.

## `loadturn.ship.mass` is not Host movement mass

A live August 2026 private-turn comparison showed that the `mass` field returned on observed ship records cannot be used as a direct ground-truth value for the Host movement-mass calculation. It is present for both own and foreign ships, but it can disagree with the mass reconstructed from the current visible cargo/component fields, including cases where current visible cargo alone is larger than the returned value.

This is consistent with the Planets.nu documentation for client fuel estimation: the client-side `getMass()`/fuel estimate intentionally does not model every Host-order interaction and has documented error cases involving transfers, Rob, beam-up, Super Refit, mine laying, alchemy and other pre-movement changes.

Policy:

- canonical `GameState` does not import `ship.mass` as physical simulation mass;
- the Host Engine recomputes movement mass from canonical state at the movement phase;
- API `ship.mass` may later be retained by the observation/intelligence layer as an observed UI/scanner fact;
- differential validation of Host movement mass must compare against controlled Host outcomes, not this API field alone.

Reference:

- https://help.planets.nu/FuelEstimateErrors

Towed mass, race/ability modifiers and special Horwasp/pod mechanics are outside this helper and will be layered into later host phases.
