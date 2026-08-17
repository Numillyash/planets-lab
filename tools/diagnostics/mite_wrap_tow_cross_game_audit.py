from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
import re

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


MITE_HULL_ID = 213
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")


def game_id_from_path(path: Path) -> int:
    m = re.fullmatch(r"game-(\d+)\.zip", path.name)
    if not m:
        raise ValueError(path)
    return int(m.group(1))


def xy(s):
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def waypoint(s):
    if s is None or s["targetx"] is None or s["targety"] is None:
        return None
    return (s["targetx"], s["targety"])


def raw_distance(a, b):
    if a is None or b is None:
        return None
    return hypot(b[0] - a[0], b[1] - a[1])


def build_game(path: Path):
    game_id = game_id_from_path(path)
    archive_data = path.read_bytes()
    prepared, hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=game_id,
        cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
    )
    topology = extract_map_topology(archive_data)
    ship_groups = group_perspective_records(tuple(prepared.snapshots), "ship")

    ships = {}
    for (turn, ship_id), group in ship_groups.items():
        owner_id, rec = _owner_record(group)
        if rec is None:
            continue
        raw = rec.raw
        ships[(turn, ship_id)] = {
            "turn": turn,
            "id": ship_id,
            "owner": owner_id,
            "hull": _intish(raw.get("hullid")),
            "name": raw.get("name"),
            "x": _intish(raw.get("x")),
            "y": _intish(raw.get("y")),
            "targetx": _intish(raw.get("targetx")),
            "targety": _intish(raw.get("targety")),
            "mission": _intish(raw.get("mission")),
            "m1": _intish(raw.get("mission1target")),
            "cloak": raw.get("iscloaked"),
            "warp": _intish(raw.get("warp")),
        }

    return game_id, hit, topology, ships


def topology_distance(a, b, topology):
    if a is None or b is None:
        return None
    dx, dy = _vector(a, b, topology)
    return hypot(dx, dy)


def wrap_like(a, b, topology):
    rd = raw_distance(a, b)
    td = topology_distance(a, b, topology)
    return (
        rd is not None
        and td is not None
        and rd - td > 500.0
    )


summary = Counter()
wrap_tow_rows = []
mite_observer_rows = []

for archive_path in sorted(RAW_DIR.glob("game-*.zip")):
    game_id, cache_hit, topology, ships = build_game(archive_path)
    print(f"game={game_id} prepared_cache_hit={cache_hit}")

    by_turn = defaultdict(list)
    for (turn, sid), s in ships.items():
        by_turn[turn].append(s)

    for turn, states in sorted(by_turn.items()):
        for mover in states:
            target_id = mover["m1"]
            if mover["mission"] != 6 or target_id is None or target_id <= 0:
                continue

            target = ships.get((turn, target_id))
            mover_next = ships.get((turn + 1, mover["id"]))
            target_next = ships.get((turn + 1, target_id))
            if target is None or mover_next is None or target_next is None:
                continue
            if xy(mover) != xy(target):
                continue
            if xy(mover_next) != xy(target_next):
                continue

            summary[("strong_comovement", game_id)] += 1
            is_wrap = wrap_like(xy(target), xy(target_next), topology)
            if not is_wrap:
                continue

            summary[("wrap_comovement", game_id)] += 1

            observers = []
            for mite in states:
                if (
                    mite["hull"] == MITE_HULL_ID
                    and mite["mission"] == 7
                    and mite["m1"] == target_id
                ):
                    mite_next = ships.get((turn + 1, mite["id"]))
                    if mite_next is None:
                        continue
                    wp_next = waypoint(mite_next)
                    prov = (
                        "exact_target_after"
                        if wp_next == xy(target_next)
                        else "exact_mover_previous_waypoint"
                        if wp_next == waypoint(mover)
                        else "other"
                    )
                    observer = {
                        "mite": mite["id"],
                        "mite_before_xy": xy(mite),
                        "mite_before_waypoint": waypoint(mite),
                        "mite_after_xy": xy(mite_next),
                        "mite_after_waypoint": wp_next,
                        "mite_after_mission": mite_next["mission"],
                        "mite_after_m1": mite_next["m1"],
                        "provenance": prov,
                        "error_to_target_after": topology_distance(
                            wp_next,
                            xy(target_next),
                            topology,
                        ),
                        "error_to_mover_previous_waypoint": topology_distance(
                            wp_next,
                            waypoint(mover),
                            topology,
                        ),
                    }
                    observers.append(observer)
                    mite_observer_rows.append({
                        "game": game_id,
                        "turn": (turn, turn + 1),
                        "target": target_id,
                        "target_name": target["name"],
                        "mover": mover["id"],
                        **observer,
                    })
                    summary[("wrap_comovement_mite_observer", game_id, prov)] += 1

            wrap_tow_rows.append({
                "game": game_id,
                "turn": (turn, turn + 1),
                "target": target_id,
                "target_owner": target["owner"],
                "target_hull": target["hull"],
                "target_name": target["name"],
                "target_before_xy": xy(target),
                "target_after_xy": xy(target_next),
                "target_after_mission": target_next["mission"],
                "target_after_m1": target_next["m1"],
                "mover": mover["id"],
                "mover_owner": mover["owner"],
                "mover_hull": mover["hull"],
                "mover_name": mover["name"],
                "mover_before_waypoint": waypoint(mover),
                "mover_after_waypoint": waypoint(mover_next),
                "raw_distance": raw_distance(xy(target), xy(target_next)),
                "topology_distance": topology_distance(
                    xy(target),
                    xy(target_next),
                    topology,
                ),
                "mite_observers": observers,
            })

print()
print("===== CROSS-GAME SUMMARY =====")
for key, n in sorted(summary.items(), key=lambda kv: str(kv[0])):
    print(key, n)

print()
print("===== ALL WRAP + STRONG MISSION6 CO-MOVEMENT EVENTS =====")
for row in wrap_tow_rows:
    print(row)
print("count=", len(wrap_tow_rows))

print()
print("===== ACTIVE RED MITE OBSERVERS OF WRAP + CO-MOVEMENT =====")
for row in mite_observer_rows:
    print(row)
print("count=", len(mite_observer_rows))
