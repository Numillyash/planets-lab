from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from planets_lab.data.nu_static import NuStaticCatalog, NuStaticDataError


def _int(raw: Mapping[str, Any], key: str, *, default: int = 0) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool):
        raise NuStaticDataError(f"{key} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NuStaticDataError(f"{key} must be an integer") from exc


def _optional_int(raw: Mapping[str, Any], key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise NuStaticDataError(f"{key} must be an integer or null")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NuStaticDataError(f"{key} must be an integer or null") from exc


def _name(raw: Mapping[str, Any]) -> str:
    value = raw.get("name", "")
    if not isinstance(value, str):
        raise NuStaticDataError("name must be a string")
    return value


def _bool(raw: Mapping[str, Any], key: str, *, default: bool = False) -> bool:
    value = raw.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise NuStaticDataError(f"{key} must be a boolean")


@dataclass(frozen=True, slots=True)
class ResourceCost:
    megacredits: int = 0
    duranium: int = 0
    tritanium: int = 0
    molybdenum: int = 0


@dataclass(frozen=True, slots=True)
class HullSpec:
    id: int
    name: str
    tech_level: int
    mass: int
    cargo_capacity: int
    fuel_tank: int
    crew: int
    engine_count: int
    beam_count: int
    torpedo_launcher_count: int
    fighter_bay_count: int
    can_cloak: bool
    cost: ResourceCost
    parent_id: int | None = None
    special: str = ""

    @property
    def munition_kind(self) -> str | None:
        """Return the unambiguous munition family accepted by this hull.

        Planets.nu uses a shared ship `ammo` field in turn payloads. A hull with
        only fighter bays can therefore interpret it as fighters, while a hull
        with only torpedo launchers can interpret it as torpedoes. Hulls with
        neither or both remain intentionally unresolved here.
        """

        if self.fighter_bay_count > 0 and self.torpedo_launcher_count == 0:
            return "fighters"
        if self.torpedo_launcher_count > 0 and self.fighter_bay_count == 0:
            return "torpedoes"
        return None


@dataclass(frozen=True, slots=True)
class EngineSpec:
    id: int
    name: str
    tech_level: int
    cost: ResourceCost
    warp_fuel_factors: tuple[int, ...]

    def fuel_factor(self, warp: int) -> int:
        if not 0 <= warp <= 9:
            raise ValueError("warp must be in range 0..9")
        return self.warp_fuel_factors[warp]


@dataclass(frozen=True, slots=True)
class BeamSpec:
    id: int
    name: str
    tech_level: int
    mass: int
    damage: int
    crew_kill: int
    cost: ResourceCost


@dataclass(frozen=True, slots=True)
class TorpedoSpec:
    id: int
    name: str
    tech_level: int
    mass: int
    damage: int
    crew_kill: int
    combat_range: int
    launcher_cost: int
    torpedo_cost: int
    cost: ResourceCost
    full_id: int | None = None


@dataclass(slots=True)
class NuStaticSpecs:
    hulls: dict[int, HullSpec] = field(default_factory=dict)
    beams: dict[int, BeamSpec] = field(default_factory=dict)
    engines: dict[int, EngineSpec] = field(default_factory=dict)
    torpedoes: dict[int, TorpedoSpec] = field(default_factory=dict)

    @classmethod
    def from_catalog(cls, catalog: NuStaticCatalog) -> "NuStaticSpecs":
        return cls(
            hulls={key: hull_spec(raw) for key, raw in catalog.hulls.items()},
            beams={key: beam_spec(raw) for key, raw in catalog.beams.items()},
            engines={key: engine_spec(raw) for key, raw in catalog.engines.items()},
            torpedoes={
                key: torpedo_spec(raw)
                for key, raw in catalog.torpedoes.items()
            },
        )


def _resource_cost(raw: Mapping[str, Any], *, mc_key: str = "cost") -> ResourceCost:
    return ResourceCost(
        megacredits=_int(raw, mc_key),
        duranium=_int(raw, "duranium", default=_int(raw, "dur")),
        tritanium=_int(raw, "tritanium", default=_int(raw, "tri")),
        molybdenum=_int(raw, "molybdenum", default=_int(raw, "mol")),
    )


def hull_spec(raw: Mapping[str, Any]) -> HullSpec:
    special = raw.get("special", "")
    if special is None:
        special = ""
    if not isinstance(special, str):
        special = str(special)

    return HullSpec(
        id=_int(raw, "id"),
        name=_name(raw),
        tech_level=_int(raw, "techlevel"),
        mass=_int(raw, "mass"),
        cargo_capacity=_int(raw, "cargo"),
        fuel_tank=_int(raw, "fueltank"),
        crew=_int(raw, "crew"),
        engine_count=_int(raw, "engines"),
        beam_count=_int(raw, "beams"),
        torpedo_launcher_count=_int(raw, "launchers"),
        fighter_bay_count=_int(raw, "fighterbays"),
        can_cloak=_bool(raw, "cancloak"),
        cost=_resource_cost(raw),
        parent_id=_optional_int(raw, "parentid"),
        special=special,
    )


def engine_spec(raw: Mapping[str, Any]) -> EngineSpec:
    warp_factors = (0,) + tuple(
        _int(raw, f"warp{warp}")
        for warp in range(1, 10)
    )
    return EngineSpec(
        id=_int(raw, "id"),
        name=_name(raw),
        tech_level=_int(raw, "techlevel"),
        cost=_resource_cost(raw),
        warp_fuel_factors=warp_factors,
    )


def beam_spec(raw: Mapping[str, Any]) -> BeamSpec:
    return BeamSpec(
        id=_int(raw, "id"),
        name=_name(raw),
        tech_level=_int(raw, "techlevel"),
        mass=_int(raw, "mass"),
        damage=_int(raw, "damage"),
        crew_kill=_int(raw, "crewkill"),
        cost=_resource_cost(raw),
    )


def torpedo_spec(raw: Mapping[str, Any]) -> TorpedoSpec:
    return TorpedoSpec(
        id=_int(raw, "id"),
        name=_name(raw),
        tech_level=_int(raw, "techlevel"),
        mass=_int(raw, "mass"),
        damage=_int(raw, "damage"),
        crew_kill=_int(raw, "crewkill"),
        combat_range=_int(raw, "combatrange"),
        launcher_cost=_int(raw, "launchercost"),
        torpedo_cost=_int(raw, "torpedocost"),
        cost=_resource_cost(raw, mc_key="launchercost"),
        full_id=_optional_int(raw, "fullid"),
    )
