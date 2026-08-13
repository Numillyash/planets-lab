from __future__ import annotations

from planets_lab.core import Ship
from planets_lab.data import NuStaticSpecs


class MovementMassError(ValueError):
    pass


def ship_movement_mass(ship: Ship, specs: NuStaticSpecs) -> int:
    """Return the KT mass used by normal movement fuel calculations.

    Planets.nu documents movement mass as hull mass (which already includes
    engine mass), fitted beam mass, fitted torpedo-tube mass, torpedoes,
    fighters, fuel, supplies, clans and minerals. MegaCredits and crew are not
    part of this movement-mass sum.

    The function uses actual fitted counts from the turn state rather than the
    maximum weapon slots in the hull specification.
    """

    hull = specs.hulls.get(ship.hull_id)
    if hull is None:
        raise MovementMassError(f"missing hull spec {ship.hull_id} for ship {ship.id}")

    if ship.unresolved_ammo:
        raise MovementMassError(
            f"ship {ship.id} has {ship.unresolved_ammo} unresolved ammo units"
        )

    mass = hull.mass

    if ship.beam_count:
        if ship.beam_id is None:
            raise MovementMassError(
                f"ship {ship.id} has beams fitted but no beam component id"
            )
        beam = specs.beams.get(ship.beam_id)
        if beam is None:
            raise MovementMassError(
                f"missing beam spec {ship.beam_id} for ship {ship.id}"
            )
        mass += beam.mass * ship.beam_count

    if ship.torpedo_launcher_count:
        if ship.torpedo_id is None:
            raise MovementMassError(
                f"ship {ship.id} has torpedo launchers fitted but no torpedo component id"
            )
        torpedo = specs.torpedoes.get(ship.torpedo_id)
        if torpedo is None:
            raise MovementMassError(
                f"missing torpedo spec {ship.torpedo_id} for ship {ship.id}"
            )
        # The static torpedo component `mass` is the launcher/tube mass. Each
        # carried torpedo itself contributes another 1 KT below.
        mass += torpedo.mass * ship.torpedo_launcher_count

    mass += ship.torpedoes
    mass += ship.fighters

    # Neutronium is fuel and is stored separately from normal cargo capacity,
    # but its current amount contributes to the mass that has to be moved.
    mass += ship.cargo.neutronium
    mass += ship.cargo.supplies
    mass += ship.cargo.clans
    mass += ship.cargo.duranium
    mass += ship.cargo.tritanium
    mass += ship.cargo.molybdenum

    return mass
