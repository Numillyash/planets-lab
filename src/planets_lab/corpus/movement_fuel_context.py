from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Mapping

from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.proration import prorate_waypoint_distance
from planets_lab.sim.normal_movement import project_toward_waypoint
from planets_lab.validation.movement_geometry import MovementSample

from .archive import read_archive_members, turn_members
from .movement_damage_context import max_warp_from_damage
from .movement_differential import _intish
from .normalizer import _decode_member_json


FUEL_PRORATION_CATEGORY = "fuel_proration_waypoint_match"
HORWASP_HULL_IDS = frozenset(range(201, 214))


@dataclass(frozen=True, slots=True)
class FuelProrationEvidence:
    category: str


def extract_static_specs(archive_data: bytes) -> NuStaticSpecs:
    """Extract the public/static component catalog embedded in a historical turn."""

    members = turn_members(archive_data)
    if not members:
        raise ValueError("archive contains no .trn members")
    member = members[0]
    raw = read_archive_members(archive_data, [member.name])[member.name]
    payload, _ = _decode_member_json(raw, member)
    return NuStaticSpecs.from_catalog(import_static_all(payload))


def strict_fuel_proration_endpoint(
    sample: MovementSample,
    *,
    fuel_available: int,
    total_mass: int,
    fuel_factor: int,
    race_id: int | None,
    damage: int | None,
) -> tuple[int, int] | None:
    """Return the documented Nu fuel-prorated endpoint for the strict corpus subset.

    This is deliberately fail-closed. The first production-compatible subset is
    restricted to ordinary non-Gravitonic movement toward a waypoint reachable in
    one turn, positive-but-insufficient fuel, a damage state that does not lower
    the requested warp, and an exact Host major/minor endpoint.
    """

    if sample.hull_id in HORWASP_HULL_IDS or sample.gravitonic:
        return None
    if not 1 <= sample.warp <= 9:
        return None
    if fuel_available <= 0 or total_mass < 0 or fuel_factor < 0:
        return None

    allowed_warp = max_warp_from_damage(damage, race_id)
    if allowed_warp is None or allowed_warp < sample.warp:
        return None

    target_distance = hypot(sample.target_x - sample.x, sample.target_y - sample.y)
    if target_distance <= 0.0:
        return None
    max_distance = sample.warp * sample.warp
    if target_distance > max_distance + 1e-9:
        return None

    fuel_required = movement_fuel_use(
        fuel_factor=fuel_factor,
        total_mass=total_mass,
        distance_traveled=target_distance,
        max_distance_per_turn=max_distance,
    )
    if fuel_required <= 0 or fuel_available >= fuel_required:
        return None

    proration = prorate_waypoint_distance(
        requested_distance=target_distance,
        fuel_available=fuel_available,
        fuel_required=fuel_required,
    )
    endpoint = project_toward_waypoint(
        x=sample.x,
        y=sample.y,
        target_x=sample.target_x,
        target_y=sample.target_y,
        distance=proration.distance,
    )
    if endpoint != sample.observed_destination:
        return None
    return endpoint


def classify_strict_fuel_proration_transition(
    sample: MovementSample,
    *,
    before_raw: Mapping[str, Any],
    race_id: int | None,
    specs: NuStaticSpecs,
) -> FuelProrationEvidence | None:
    """Classify only the exact documented waypoint-proration compatibility subset."""

    engine_id = _intish(before_raw.get("engineid"))
    fuel_available = _intish(before_raw.get("neutronium"))
    total_mass = _intish(before_raw.get("mass"))
    damage = _intish(before_raw.get("damage"))
    if (
        engine_id is None
        or engine_id not in specs.engines
        or fuel_available is None
        or total_mass is None
    ):
        return None

    fuel_factor = specs.engines[engine_id].fuel_factor(sample.warp)
    if strict_fuel_proration_endpoint(
        sample,
        fuel_available=fuel_available,
        total_mass=total_mass,
        fuel_factor=fuel_factor,
        race_id=race_id,
        damage=damage,
    ) is None:
        return None
    return FuelProrationEvidence(category=FUEL_PRORATION_CATEGORY)
