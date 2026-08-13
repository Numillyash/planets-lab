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

Towed mass, race/ability modifiers and special Horwasp/pod mechanics are outside this helper and will be layered into later host phases.
