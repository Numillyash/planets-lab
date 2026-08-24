from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from planets_lab.validation.movement_geometry import MovementSample, host_major_minor_destination

from .movement_differential import _intish
from .movement_residual_context import _owner_record
from .movement_sphere_context import (
    _compiled_topology_context,
    effective_sphere_topology,
)
from .movement_topology_diagnostics import sphere_adjusted_sample
from .normalizer import ArchiveTurnSnapshot
from .prepared_cache import PreparedGameCache
from .reconstruction import PerspectiveRecord, group_perspective_records


DAMAGE_LIMITED_WARP_CATEGORY = "damage_limited_warp_match"
HORWASP_HULL_IDS = frozenset(range(201, 214))
LIZARD_RACE_ID = 2


def max_warp_from_damage(damage: int | None, race_id: int | None) -> int | None:
    """Return the documented maximum movement warp for current ship damage.

    The Lizard damage table differs from the standard race table. Destroyed
    states return ``None`` so historical reconstruction fails closed rather than
    inventing movement for a ship state that should no longer be viable.
    """

    if damage is None or damage < 0 or race_id is None or race_id <= 0:
        return None

    if race_id == LIZARD_RACE_ID:
        if damage >= 151:
            return None
        if damage <= 69:
            return 9
        return max(0, min(9, 15 - damage // 10))

    if damage >= 100:
        return None
    if damage <= 19:
        return 9
    return max(1, min(9, 10 - damage // 10))


def damage_limited_warp_match(
    sample: MovementSample,
    *,
    race_id: int | None,
    damage: int | None,
    supplies: int | None,
) -> int | None:
    """Return the effective warp only for the strict corpus-verified signature.

    This deliberately excludes any repair reconstruction. Fewer than 5 KT of
    currently visible supplies cannot repair even 1% using the ship's own cargo,
    which gives a conservative raw-damage subset. Other pre-movement repair or
    transfer effects are not inferred here.
    """

    if supplies is None or supplies < 0 or supplies >= 5:
        return None
    if not 1 <= sample.warp <= 9:
        return None

    effective_warp = max_warp_from_damage(damage, race_id)
    if effective_warp is None or effective_warp >= sample.warp:
        return None

    effective_sample = MovementSample(
        turn=sample.turn,
        ship_id=sample.ship_id,
        x=sample.x,
        y=sample.y,
        target_x=sample.target_x,
        target_y=sample.target_y,
        warp=effective_warp,
        next_x=sample.next_x,
        next_y=sample.next_y,
        gravitonic=sample.gravitonic,
        game_id=sample.game_id,
        player_slot_id=sample.player_slot_id,
        hull_id=sample.hull_id,
        mission=sample.mission,
        damage=sample.damage,
        friendly_code=sample.friendly_code,
    )
    if host_major_minor_destination(effective_sample) != effective_sample.observed_destination:
        return None
    return effective_warp


def _race_map(snapshots: Sequence[ArchiveTurnSnapshot]) -> dict[int, int]:
    observed: dict[int, set[int]] = defaultdict(set)
    for snapshot in snapshots:
        payload = snapshot.mechanics_payload
        candidates: list[Any] = []
        player = payload.get("player") if isinstance(payload, Mapping) else None
        players = payload.get("players", []) if isinstance(payload, Mapping) else []
        if isinstance(player, Mapping):
            candidates.append(player)
        if isinstance(players, list):
            candidates.extend(item for item in players if isinstance(item, Mapping))
        for raw in candidates:
            player_id = _intish(raw.get("id"))
            race_id = _intish(raw.get("raceid"))
            if player_id is not None and player_id > 0 and race_id is not None and race_id > 0:
                observed[player_id].add(race_id)
    return {
        player_id: next(iter(races))
        for player_id, races in observed.items()
        if len(races) == 1
    }


def _same_owner_identity_after(
    *,
    ship_groups: Mapping[tuple[int, int], tuple[PerspectiveRecord, ...]],
    before_turn: int,
    after_turn: int,
    ship_id: int,
    owner_id: int,
    before_raw: Mapping[str, Any],
) -> bool:
    after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))
    if after_owner_id != owner_id or after_owner is None:
        return False

    after_raw = after_owner.raw
    before_hull = _intish(before_raw.get("hullid", before_raw.get("hull_id")))
    after_hull = _intish(after_raw.get("hullid", after_raw.get("hull_id")))
    if before_hull is None or after_hull is None or before_hull != after_hull:
        return False

    before_identity_turn = _intish(before_raw.get("turn"))
    after_identity_turn = _intish(after_raw.get("turn"))
    if (
        before_identity_turn is not None
        and after_identity_turn is not None
        and before_identity_turn != after_identity_turn
    ):
        return False
    return True


def _row_sample(row: Mapping[str, Any]) -> MovementSample | None:
    required = (
        "ship_id",
        "before_embedded_turn",
        "x_before",
        "y_before",
        "target_x",
        "target_y",
        "warp",
        "x_after",
        "y_after",
    )
    if any(row.get(key) is None for key in required):
        return None
    return MovementSample(
        turn=int(row["before_embedded_turn"]),
        ship_id=int(row["ship_id"]),
        x=int(row["x_before"]),
        y=int(row["y_before"]),
        target_x=int(row["target_x"]),
        target_y=int(row["target_y"]),
        warp=int(row["warp"]),
        next_x=int(row["x_after"]),
        next_y=int(row["y_after"]),
        gravitonic=row.get("is_gravitonic_hull") is True,
        game_id=int(row["game_id"]) if row.get("game_id") is not None else None,
        hull_id=int(row["hull_id"]) if row.get("hull_id") is not None else None,
    )


def apply_damage_limited_warp_context_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    prepared: PreparedGameCache,
) -> list[dict[str, Any]]:
    """Close only strict raw-damage exact matches still unresolved in L1.

    The pass is monotonic and intentionally runs after authoritative storm mode
    and scoped effective-sphere geometry. Existing categories are never stolen.
    """

    context = _compiled_topology_context(rows)
    if context is None:
        return [dict(row) for row in rows]
    game_id, topology = context
    effective_topology = effective_sphere_topology(game_id=game_id, topology=topology)

    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    races = _race_map(prepared.snapshots)

    result: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        if row.get("post_external_residual") is not True:
            result.append(row)
            continue

        hull_id = row.get("hull_id")
        if isinstance(hull_id, bool) or not isinstance(hull_id, int) or hull_id in HORWASP_HULL_IDS:
            result.append(row)
            continue

        sample = _row_sample(row)
        if sample is None:
            result.append(row)
            continue

        before_turn = int(row["before_archive_turn"])
        after_turn = int(row["after_archive_turn"])
        owner_id, before_owner = _owner_record(ship_groups.get((before_turn, sample.ship_id), ()))
        if owner_id is None or owner_id <= 0 or before_owner is None:
            result.append(row)
            continue
        before_raw = before_owner.raw
        if not _same_owner_identity_after(
            ship_groups=ship_groups,
            before_turn=before_turn,
            after_turn=after_turn,
            ship_id=sample.ship_id,
            owner_id=owner_id,
            before_raw=before_raw,
        ):
            result.append(row)
            continue

        race_id = races.get(owner_id)
        damage = _intish(before_raw.get("damage"))
        supplies = _intish(before_raw.get("supplies"))

        effective_sample = sample
        if (
            effective_topology.sphere is True
            and effective_topology.mapwidth is not None
            and effective_topology.mapheight is not None
        ):
            effective_sample = sphere_adjusted_sample(
                sample,
                width=int(effective_topology.mapwidth),
                height=int(effective_topology.mapheight),
            )

        if damage_limited_warp_match(
            effective_sample,
            race_id=race_id,
            damage=damage,
            supplies=supplies,
        ) is None:
            result.append(row)
            continue

        row["external_context_category"] = DAMAGE_LIMITED_WARP_CATEGORY
        row["external_context_explained"] = True
        row["post_external_residual"] = False
        result.append(row)

    return result
