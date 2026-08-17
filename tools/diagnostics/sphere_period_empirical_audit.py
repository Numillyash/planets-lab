from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
import re
from statistics import median

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
CANDIDATE_PERIODS = (2150, 2170)


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


def axis_period_residual(a: int, b: int, period: int) -> int:
    d = abs(b - a)
    return min(d, abs(d - period))


def point_period_residual(a, b, px: int, py: int):
    if a is None or b is None:
        return None
    rx = axis_period_residual(a[0], b[0], px)
    ry = axis_period_residual(a[1], b[1], py)
    return hypot(rx, ry)


def build_game(path: Path):
    game_id = game_id_from_path(path)
    archive_data = path.read_bytes()
    prepared, hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=game_id,
        cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
    )
    topology = extract_map_topology(archive_data)
    groups = group_perspective_records(tuple(prepared.snapshots), "ship")

    ships = {}
    for (turn, sid), group in groups.items():
        owner_id, rec = _owner_record(group)
        if rec is None:
            continue
        raw = rec.raw
        ships[(turn, sid)] = {
            "turn": turn,
            "id": sid,
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
        }
    return game_id, hit, topology, ships


settings_rows = []
comove_axis_diffs = Counter()
comove_rows = []
negative_axis_diffs = Counter()
negative_rows = []
score_samples = defaultdict(list)

for archive_path in sorted(RAW_DIR.glob("game-*.zip")):
    game_id, hit, topology, ships = build_game(archive_path)
    print(f"game={game_id} prepared_cache_hit={hit}")

    settings_rows.append({
        "game": game_id,
        "sphere": topology.sphere,
        "mapwidth": topology.mapwidth,
        "mapheight": topology.mapheight,
        "mapshape": topology.mapshape,
        "stable": topology.stable,
        "first_candidates": dict(topology.first_candidates),
        "last_candidates": dict(topology.last_candidates),
    })

    by_turn = defaultdict(list)
    for (turn, _sid), s in ships.items():
        by_turn[turn].append(s)

    # Strong mission-6 co-movement is used only as an observed equality source:
    # mover and target share the same before and after position. We make no
    # semantic claim about the mission code here.
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
            if xy(mover) != xy(target) or xy(mover_next) != xy(target_next):
                continue
            wp = waypoint(mover)
            end = xy(target_next)
            if wp is None or end is None:
                continue

            dx = abs(wp[0] - end[0])
            dy = abs(wp[1] - end[1])
            crosses_raw_seam = dx > 1000 or dy > 1000
            if not crosses_raw_seam:
                continue

            if dx > 1000:
                comove_axis_diffs[("x", dx)] += 1
            if dy > 1000:
                comove_axis_diffs[("y", dy)] += 1

            residuals = {}
            for period in CANDIDATE_PERIODS:
                residuals[period] = point_period_residual(wp, end, period, period)
                score_samples[("comove", period)].append(residuals[period])

            comove_rows.append({
                "game": game_id,
                "turn": (turn, turn + 1),
                "target": target_id,
                "target_name": target["name"],
                "mover": mover["id"],
                "mover_waypoint_before": wp,
                "shared_endpoint_after": end,
                "raw_axis_difference": (dx, dy),
                "candidate_residuals": residuals,
            })

    # Negative mission1target rows provide an independent observed reference:
    # compare the ship's own targetxy with the raw coordinates of abs(m1).
    for (turn, sid), s in sorted(ships.items()):
        m1 = s["m1"]
        if m1 is None or m1 >= 0:
            continue
        ref = ships.get((turn, abs(m1)))
        if ref is None:
            continue
        wp = waypoint(s)
        ref_xy = xy(ref)
        if wp is None or ref_xy is None:
            continue

        dx = abs(wp[0] - ref_xy[0])
        dy = abs(wp[1] - ref_xy[1])
        if dx > 1000:
            negative_axis_diffs[("x", dx)] += 1
        if dy > 1000:
            negative_axis_diffs[("y", dy)] += 1

        residuals = {}
        for period in CANDIDATE_PERIODS:
            residuals[period] = point_period_residual(wp, ref_xy, period, period)
            score_samples[("negative_m1", period)].append(residuals[period])

        negative_rows.append({
            "game": game_id,
            "turn": turn,
            "ship": sid,
            "ship_name": s["name"],
            "mission": s["mission"],
            "m1": m1,
            "ship_xy": xy(s),
            "ship_targetxy": wp,
            "referenced_ship": abs(m1),
            "referenced_name": ref["name"],
            "referenced_raw_xy": ref_xy,
            "raw_axis_difference": (dx, dy),
            "candidate_residuals": residuals,
        })

print()
print("===== RAW TOPOLOGY SETTINGS =====")
for row in settings_rows:
    print(row)

print()
print("===== STRONG CO-MOVEMENT: RAW WAYPOINT/ENDPOINT SEAM DIFFERENCES =====")
for (axis, diff), n in comove_axis_diffs.most_common():
    print({"axis": axis, "difference": diff, "n": n})
print("rows=", len(comove_rows))

print()
print("===== NEGATIVE M1: RAW TARGETXY/REFERENCED-XY SEAM DIFFERENCES =====")
for (axis, diff), n in negative_axis_diffs.most_common():
    print({"axis": axis, "difference": diff, "n": n})
print("rows=", len(negative_rows))

print()
print("===== CANDIDATE PERIOD SCORES =====")
for source in ("comove", "negative_m1"):
    for period in CANDIDATE_PERIODS:
        values = score_samples.get((source, period), [])
        if not values:
            print({"source": source, "period": period, "n": 0})
            continue
        print({
            "source": source,
            "period": period,
            "n": len(values),
            "exact": sum(v < 1e-9 for v in values),
            "le_1": sum(v <= 1.0 for v in values),
            "le_3": sum(v <= 3.0 for v in values),
            "le_5": sum(v <= 5.0 for v in values),
            "median_residual": median(values),
            "max_residual": max(values),
        })

print()
print("===== CO-MOVEMENT ROWS WHERE 2170 MATERIALly BEATS 2150 =====")
for row in comove_rows:
    r2150 = row["candidate_residuals"][2150]
    r2170 = row["candidate_residuals"][2170]
    if r2170 + 5 < r2150:
        print(row)

print()
print("===== NEGATIVE M1 ROWS =====")
for row in negative_rows:
    print(row)

print()
print("===== FOCUS 329 / 311 / 1185 UNDER BOTH PERIODS =====")
# This section deliberately bypasses current _vector() so the two candidate
# periods can be compared without circularity.
for turn in (54, 55, 56):
    target = None
    mite = None
    mover = None
    for archive_path in RAW_DIR.glob("game-591478.zip"):
        _gid, _hit, _topology, focus_ships = build_game(archive_path)
        target = focus_ships.get((turn, 329))
        mite = focus_ships.get((turn, 1185))
        mover = focus_ships.get((turn, 311))
        break
    if target is None or mite is None:
        continue
    item = {
        "turn": turn,
        "target_xy": xy(target),
        "mite_waypoint": waypoint(mite),
        "mover_waypoint": waypoint(mover),
    }
    for period in CANDIDATE_PERIODS:
        item[f"mite_target_residual_p{period}"] = point_period_residual(
            waypoint(mite), xy(target), period, period
        )
    print(item)
