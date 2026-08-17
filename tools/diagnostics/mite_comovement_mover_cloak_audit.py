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
MAX_LAG = 4
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
            "damage": _intish(raw.get("damage")),
            "enemy": _intish(raw.get("enemy")),
        }

    return game_id, hit, topology, ships


def waypoint_state(turn: int, target_id: int, mite, ships, topology):
    wp = waypoint(mite)
    if wp is None:
        return "missing_waypoint", []

    matches = []
    for lag in range(MAX_LAG + 1):
        target = ships.get((turn - lag, target_id))
        p = xy(target)
        if p is None:
            continue
        d = topology_distance(wp, p, topology)
        if d is not None and d < 1e-9:
            matches.append(lag)

    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", matches


def mite_outcome(mite_next, target_id: int):
    if mite_next is None:
        return "missing_after"
    if mite_next["mission"] == 7 and mite_next["m1"] == target_id:
        return "retained"
    if mite_next["mission"] == 0 and (mite_next["m1"] is None or mite_next["m1"] == 0):
        return "immediate_full_clear"
    if mite_next["mission"] == 7 and (mite_next["m1"] is None or mite_next["m1"] == 0):
        return "target_clear_pending"
    return f"other_{mite_next['mission']}_{mite_next['m1']}"


summary = Counter()
rows = []

for archive_path in sorted(RAW_DIR.glob("game-*.zip")):
    game_id, cache_hit, topology, ships = build_game(archive_path)
    print(f"game={game_id} prepared_cache_hit={cache_hit}")

    by_turn = defaultdict(list)
    for (turn, _sid), s in ships.items():
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

            is_wrap = wrap_like(xy(target), xy(target_next), topology)

            for mite in states:
                if not (
                    mite["hull"] == MITE_HULL_ID
                    and mite["mission"] == 7
                    and mite["m1"] == target_id
                ):
                    continue

                mite_next = ships.get((turn + 1, mite["id"]))
                if mite_next is None:
                    continue

                state_before, matches_before = waypoint_state(
                    turn, target_id, mite, ships, topology
                )
                state_after, matches_after = waypoint_state(
                    turn + 1, target_id, mite_next, ships, topology
                )
                outcome = mite_outcome(mite_next, target_id)

                mover_next_cloak = mover_next["cloak"]
                target_next_cloak = target_next["cloak"]
                wp_next = waypoint(mite_next)
                if wp_next == xy(target_next) and wp_next == waypoint(mover):
                    prov = "exact_both"
                elif wp_next == xy(target_next):
                    prov = "exact_target_after"
                elif wp_next == waypoint(mover):
                    prov = "exact_mover_previous_waypoint"
                else:
                    prov = "other"

                next2_state = None
                next_outcome = None
                mite_next2 = ships.get((turn + 2, mite["id"]))
                target_next2 = ships.get((turn + 2, target_id))
                if (
                    mite_next2 is not None
                    and target_next2 is not None
                    and mite_next["mission"] == 7
                    and mite_next["m1"] == target_id
                ):
                    next2_state, _ = waypoint_state(
                        turn + 2, target_id, mite_next2, ships, topology
                    )
                    next_outcome = mite_outcome(mite_next2, target_id)

                key = (
                    is_wrap,
                    mover["cloak"],
                    mover_next_cloak,
                    state_after,
                    outcome,
                    prov,
                )
                summary[key] += 1

                rows.append({
                    "game": game_id,
                    "turn": (turn, turn + 1),
                    "target": target_id,
                    "target_name": target["name"],
                    "target_hull": target["hull"],
                    "target_cloak": (target["cloak"], target_next_cloak),
                    "target_xy": (xy(target), xy(target_next)),
                    "target_mission": (target["mission"], target_next["mission"]),
                    "target_m1": (target["m1"], target_next["m1"]),
                    "mover": mover["id"],
                    "mover_name": mover["name"],
                    "mover_hull": mover["hull"],
                    "mover_cloak": (mover["cloak"], mover_next_cloak),
                    "mover_xy": (xy(mover), xy(mover_next)),
                    "mover_waypoint": (waypoint(mover), waypoint(mover_next)),
                    "mover_mission": (mover["mission"], mover_next["mission"]),
                    "mover_m1": (mover["m1"], mover_next["m1"]),
                    "wrap_like": is_wrap,
                    "mite": mite["id"],
                    "mite_state_before": state_before,
                    "mite_matches_before": matches_before,
                    "mite_state_after": state_after,
                    "mite_matches_after": matches_after,
                    "mite_outcome": outcome,
                    "mite_waypoint": (waypoint(mite), wp_next),
                    "waypoint_provenance": prov,
                    "error_to_target_after": topology_distance(
                        wp_next, xy(target_next), topology
                    ),
                    "error_to_mover_previous_waypoint": topology_distance(
                        wp_next, waypoint(mover), topology
                    ),
                    "mite_state_t2": next2_state,
                    "mite_outcome_t1_to_t2": next_outcome,
                })

print()
print("===== ACTIVE-MITE STRONG CO-MOVEMENT SUMMARY =====")
for key, n in summary.most_common():
    print({
        "wrap_like": key[0],
        "mover_cloak_before": key[1],
        "mover_cloak_after": key[2],
        "mite_state_after": key[3],
        "mite_outcome": key[4],
        "waypoint_provenance": key[5],
        "n": n,
    })

print()
print("===== CLOAKED-MOVER CASES =====")
for row in rows:
    if row["mover_cloak"][0] is True:
        print(row)
print("count=", sum(1 for row in rows if row["mover_cloak"][0] is True))

print()
print("===== NON-CURRENT / LOSS-AJACENT CO-MOVEMENT CASES =====")
for row in rows:
    if (
        row["mite_state_after"] != "current"
        or row["mite_outcome"] != "retained"
        or row["mite_state_t2"] not in {None, "current"}
    ):
        print(row)

print()
print("===== FOCUS 329 / 311 / 1185 =====")
for row in rows:
    if row["game"] == 591478 and row["target"] == 329 and row["mite"] == 1185:
        print(row)
