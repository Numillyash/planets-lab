from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from planets_lab.core.models import (
    Cargo,
    GameState,
    MineralDeposit,
    NativePopulation,
    Planet,
    Player,
    Ship,
    Starbase,
)


class NuLoadTurnError(ValueError):
    pass


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NuLoadTurnError(f"{label} must be an object")
    return value


def _records(value: Any, label: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise NuLoadTurnError(f"{label} must be a list")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NuLoadTurnError(f"{label}[{index}] must be an object")
        result.append(item)
    return result


def _first(raw: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return default


def _int(raw: Mapping[str, Any], *keys: str, default: int = 0) -> int:
    value = _first(raw, *keys, default=default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NuLoadTurnError(f"expected integer for one of {keys}, got {value!r}") from exc


def _required_int(raw: Mapping[str, Any], *keys: str) -> int:
    value = _first(raw, *keys, default=None)
    if value is None:
        raise NuLoadTurnError(f"missing required field; expected one of {keys}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NuLoadTurnError(f"expected integer for one of {keys}, got {value!r}") from exc


def _owner_id(raw: Mapping[str, Any]) -> int | None:
    owner_id = _int(raw, "ownerid", "owner_id", default=0)
    return owner_id or None


def _cargo(raw: Mapping[str, Any]) -> Cargo:
    return Cargo(
        neutronium=_int(raw, "neutronium"),
        duranium=_int(raw, "duranium"),
        tritanium=_int(raw, "tritanium"),
        molybdenum=_int(raw, "molybdenum"),
        supplies=_int(raw, "supplies"),
        clans=_int(raw, "clans"),
        megacredits=_int(raw, "megacredits", "megacredit"),
    )


def _planet(raw: Mapping[str, Any]) -> Planet:
    native_clans = _int(raw, "nativeclans", "native_clans")
    native_race_id = _int(raw, "nativerace", "nativeraceid", "native_race_id")
    natives = None
    if native_clans > 0 or native_race_id > 0:
        natives = NativePopulation(
            race_id=native_race_id,
            clans=native_clans,
            government_id=_int(raw, "nativegovernment", "nativegovernmentid"),
            happiness=_int(raw, "nativehappypoints", "nativehappiness", default=100),
            tax_rate=_int(raw, "nativetaxrate", default=0),
        )

    return Planet(
        id=_required_int(raw, "id"),
        x=_required_int(raw, "x"),
        y=_required_int(raw, "y"),
        owner_id=_owner_id(raw),
        cargo=_cargo(raw),
        ground_neutronium=MineralDeposit(
            amount=_int(raw, "groundneutronium"),
            density=_int(raw, "densityneutronium"),
        ),
        ground_duranium=MineralDeposit(
            amount=_int(raw, "groundduranium"),
            density=_int(raw, "densityduranium"),
        ),
        ground_tritanium=MineralDeposit(
            amount=_int(raw, "groundtritanium"),
            density=_int(raw, "densitytritanium"),
        ),
        ground_molybdenum=MineralDeposit(
            amount=_int(raw, "groundmolybdenum"),
            density=_int(raw, "densitymolybdenum"),
        ),
        factories=_int(raw, "factories"),
        mines=_int(raw, "mines"),
        defense_posts=_int(raw, "defense", "defenseposts"),
        happiness=_int(raw, "colonisthappypoints", "happiness", default=100),
        tax_rate=_int(raw, "colonisttaxrate", "taxrate", default=0),
        natives=natives,
    )


def _ship(raw: Mapping[str, Any]) -> Ship:
    owner_id = _owner_id(raw)
    if owner_id is None:
        raise NuLoadTurnError(f"ship {_first(raw, 'id', default='?')} has no owner")

    return Ship(
        id=_required_int(raw, "id"),
        owner_id=owner_id,
        hull_id=_required_int(raw, "hullid", "hull_id"),
        x=_required_int(raw, "x"),
        y=_required_int(raw, "y"),
        engine_id=_int(raw, "engineid", "engine_id") or None,
        beam_id=_int(raw, "beamid", "beam_id") or None,
        torpedo_id=_int(raw, "torpedoid", "torpedo_id") or None,
        waypoint_x=_int(raw, "targetx", "waypointx", "waypoint_x", default=_required_int(raw, "x")),
        waypoint_y=_int(raw, "targety", "waypointy", "waypoint_y", default=_required_int(raw, "y")),
        warp=_int(raw, "warp"),
        mission=str(_first(raw, "mission", default="")) or None,
        primary_enemy_id=_int(raw, "enemy", "primaryenemy", "primary_enemy_id") or None,
        friendly_code=str(_first(raw, "friendlycode", "friendly_code", default="")),
        cargo=_cargo(raw),
        damage=_int(raw, "damage"),
    )


def _starbase(raw: Mapping[str, Any]) -> Starbase:
    owner_id = _owner_id(raw)
    if owner_id is None:
        raise NuLoadTurnError(f"starbase on planet {_first(raw, 'planetid', default='?')} has no owner")
    return Starbase(
        planet_id=_required_int(raw, "planetid", "planet_id"),
        owner_id=owner_id,
        defense=_int(raw, "defense"),
        fighters=_int(raw, "fighters"),
        tech_hull=_int(raw, "hulltechlevel", "techhull", default=1),
        tech_engine=_int(raw, "enginetechlevel", "techengine", default=1),
        tech_beam=_int(raw, "beamtechlevel", "techbeam", default=1),
        tech_torpedo=_int(raw, "torptechlevel", "techtorpedo", default=1),
    )


def import_loadturn(
    payload: Mapping[str, Any],
    *,
    game_id: int | str | None = None,
    turn: int | None = None,
) -> GameState:
    """Convert a Planets.nu loadturn-style payload into canonical GameState.

    Only fields with unambiguous canonical meaning are mapped. Unknown fields
    are intentionally ignored until their semantics are specified and tested.
    """

    payload = _mapping(payload, "payload")
    rst = _mapping(payload.get("rst"), "payload.rst")

    game = payload.get("game")
    game_mapping = game if isinstance(game, Mapping) else {}

    resolved_game_id = game_id
    if resolved_game_id is None:
        resolved_game_id = _first(game_mapping, "id", "gameid", default=None)
    if resolved_game_id is None:
        resolved_game_id = _first(rst, "gameid", "game_id", default=None)
    if resolved_game_id is None:
        raise NuLoadTurnError("game_id must be supplied when payload does not identify the game")

    resolved_turn = turn
    if resolved_turn is None:
        candidate = _first(game_mapping, "turn", "turnnumber", default=None)
        if candidate is None:
            candidate = _first(rst, "turn", "turnnumber", default=None)
        if candidate is not None:
            try:
                resolved_turn = int(candidate)
            except (TypeError, ValueError) as exc:
                raise NuLoadTurnError(f"invalid turn value {candidate!r}") from exc
    if resolved_turn is None:
        raise NuLoadTurnError("turn must be supplied when payload does not identify the turn")

    planets = {planet.id: planet for planet in (_planet(raw) for raw in _records(rst.get("planets"), "rst.planets"))}
    ships = {ship.id: ship for ship in (_ship(raw) for raw in _records(rst.get("ships"), "rst.ships"))}
    starbases = {
        starbase.planet_id: starbase
        for starbase in (_starbase(raw) for raw in _records(rst.get("starbases"), "rst.starbases"))
    }

    players: dict[int, Player] = {}
    raw_players = rst.get("players")
    if raw_players is None:
        raw_players = payload.get("players")
    for raw in _records(raw_players, "players"):
        player_id = _required_int(raw, "id", "playerid", "player_id")
        players[player_id] = Player(
            id=player_id,
            name=str(_first(raw, "username", "name", default="")),
            race_id=_int(raw, "raceid", "race_id") or None,
        )

    referenced_owner_ids = {
        owner_id
        for owner_id in [
            *(planet.owner_id for planet in planets.values()),
            *(ship.owner_id for ship in ships.values()),
            *(starbase.owner_id for starbase in starbases.values()),
        ]
        if owner_id is not None
    }
    for owner_id in referenced_owner_ids:
        players.setdefault(owner_id, Player(id=owner_id))

    state = GameState(
        game_id=resolved_game_id,
        turn=resolved_turn,
        players=players,
        planets=planets,
        ships=ships,
        starbases=starbases,
        metadata={"source": "planets.nu/loadturn"},
    )
    state.validate()
    return state
