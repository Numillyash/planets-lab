from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Cargo:
    """Cargo/resources carried by a ship or stored on a planet."""

    neutronium: int = 0
    duranium: int = 0
    tritanium: int = 0
    molybdenum: int = 0
    supplies: int = 0
    clans: int = 0
    megacredits: int = 0


@dataclass(slots=True)
class MineralDeposit:
    """Ground mineral reserve and extraction density for a planet."""

    amount: int = 0
    density: int = 0


@dataclass(slots=True)
class NativePopulation:
    race_id: int
    clans: int
    government_id: int
    happiness: int = 100
    tax_rate: int = 0


@dataclass(slots=True)
class Player:
    id: int
    name: str = ""
    race_id: int | None = None
    is_alive: bool = True


@dataclass(slots=True)
class Planet:
    id: int
    x: int
    y: int
    owner_id: int | None = None

    cargo: Cargo = field(default_factory=Cargo)

    ground_neutronium: MineralDeposit = field(default_factory=MineralDeposit)
    ground_duranium: MineralDeposit = field(default_factory=MineralDeposit)
    ground_tritanium: MineralDeposit = field(default_factory=MineralDeposit)
    ground_molybdenum: MineralDeposit = field(default_factory=MineralDeposit)

    factories: int = 0
    mines: int = 0
    defense_posts: int = 0
    happiness: int = 100
    tax_rate: int = 0
    natives: NativePopulation | None = None


@dataclass(slots=True)
class Ship:
    id: int
    owner_id: int
    hull_id: int
    x: int
    y: int

    engine_id: int | None = None
    beam_id: int | None = None
    torpedo_id: int | None = None

    # Installed armament counts. These are the actual fitted values from the
    # turn state, not the maximum slots from the hull specification.
    beam_count: int = 0
    torpedo_launcher_count: int = 0
    fighter_bay_count: int = 0

    waypoint_x: int | None = None
    waypoint_y: int | None = None
    warp: int = 0
    mission: str | None = None
    primary_enemy_id: int | None = None
    friendly_code: str = ""

    cargo: Cargo = field(default_factory=Cargo)
    fighters: int = 0
    torpedoes: int = 0
    unresolved_ammo: int = 0
    damage: int = 0


@dataclass(slots=True)
class Starbase:
    planet_id: int
    owner_id: int
    defense: int = 0
    fighters: int = 0
    tech_hull: int = 1
    tech_engine: int = 1
    tech_beam: int = 1
    tech_torpedo: int = 1


@dataclass(slots=True)
class GameState:
    """Canonical full-information state used by the simulator.

    This is deliberately distinct from a player's observation. AI agents must
    eventually consume PlayerObservation rather than GameState directly.
    """

    game_id: int | str
    turn: int
    players: dict[int, Player] = field(default_factory=dict)
    planets: dict[int, Planet] = field(default_factory=dict)
    ships: dict[int, Ship] = field(default_factory=dict)
    starbases: dict[int, Starbase] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def clone(self) -> GameState:
        return deepcopy(self)

    def validate(self) -> None:
        if self.turn < 0:
            raise ValueError("turn must be non-negative")

        for player_id, player in self.players.items():
            if player.id != player_id:
                raise ValueError(f"player key {player_id} does not match player.id {player.id}")

        for planet_id, planet in self.planets.items():
            if planet.id != planet_id:
                raise ValueError(f"planet key {planet_id} does not match planet.id {planet.id}")
            if planet.owner_id is not None and planet.owner_id not in self.players:
                raise ValueError(f"planet {planet_id} has unknown owner {planet.owner_id}")

        for ship_id, ship in self.ships.items():
            if ship.id != ship_id:
                raise ValueError(f"ship key {ship_id} does not match ship.id {ship.id}")
            if ship.owner_id not in self.players:
                raise ValueError(f"ship {ship_id} has unknown owner {ship.owner_id}")
            for label, value in (
                ("beam_count", ship.beam_count),
                ("torpedo_launcher_count", ship.torpedo_launcher_count),
                ("fighter_bay_count", ship.fighter_bay_count),
                ("fighters", ship.fighters),
                ("torpedoes", ship.torpedoes),
                ("unresolved_ammo", ship.unresolved_ammo),
            ):
                if value < 0:
                    raise ValueError(f"ship {ship_id} has negative {label}")

        for planet_id, starbase in self.starbases.items():
            if starbase.planet_id != planet_id:
                raise ValueError(
                    f"starbase key {planet_id} does not match starbase.planet_id {starbase.planet_id}"
                )
            if planet_id not in self.planets:
                raise ValueError(f"starbase references unknown planet {planet_id}")
            if starbase.owner_id not in self.players:
                raise ValueError(f"starbase on planet {planet_id} has unknown owner {starbase.owner_id}")
