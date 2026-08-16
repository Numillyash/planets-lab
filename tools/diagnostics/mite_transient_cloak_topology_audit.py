from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path

from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _resolved_value,
)
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


GAME_ID = 591478
MAX_LAG = 4
EXACT_EPS = 1e-9
NEAR_EPS = 3.0

ARCHIVE_PATH = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")
PREPARED_PATH = Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle")

archive_data = ARCHIVE_PATH.read_bytes()
prepared, hit = load_or_build_prepared_game_cache(
    archive_data,
    game_id=GAME_ID,
    cache_path=PREPARED_PATH,
)

print("prepared_cache_hit:", hit)

records = tuple(prepared.snapshots)
groups = group_perspective_records(records, "ship")
entities = _entity_map(records)
topology = extract_map_topology(archive_data)


def rv(entity, field):
    if entity is None:
        return None
    try:
        return _resolved_value(entity, field)
    except Exception:
        return None


def iv(entity, field):
    return _intish(rv(entity, field))


def topology_distance(a, b):
    if a is None or b is None:
        return None
    dx, dy = _vector(a, b, topology)
    return hypot(dx, dy)


ships = {}
for (turn, ship_id), group in groups.items():
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
        "m2": _intish(raw.get("mission2target")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
        "warp": _intish(raw.get("warp")),
        "heading": _intish(raw.get("heading")),
        "raw_turn": _intish(raw.get("turn")),
        "infoturn": _intish(raw.get("infoturn")),
        "readystatus": _intish(raw.get("readystatus")),
    }


def ship(turn, ship_id):
    return ships.get((turn, ship_id))


def xy(s):
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def waypoint(s):
    if s is None or s["targetx"] is None or s["targety"] is None:
        return None
    return (s["targetx"], s["targety"])


def outcome(before, after, target):
    if after is None:
        return "missing_after"
    if after["mission"] == 7 and after["m1"] == target:
        return "retained"
    if after["mission"] == 0 and (after["m1"] is None or after["m1"] == 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and (after["m1"] is None or after["m1"] == 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


def lag_distances(turn, target_id, point):
    out = {}
    if point is None:
        return out
    for lag in range(MAX_LAG + 1):
        target = ship(turn - lag, target_id)
        target_point = xy(target)
        if target_point is None:
            continue
        out[lag] = topology_distance(point, target_point)
    return out


def raw_exact_matches(turn, target_id, point):
    out = []
    if point is None:
        return out
    for lag in range(MAX_LAG + 1):
        target = ship(turn - lag, target_id)
        if xy(target) == point:
            out.append(lag)
    return out


def topology_exact_matches(turn, target_id, point):
    return [
        lag
        for lag, dist in lag_distances(turn, target_id, point).items()
        if dist is not None and dist <= EXACT_EPS
    ]


def topology_near_matches(turn, target_id, point):
    return [
        lag
        for lag, dist in lag_distances(turn, target_id, point).items()
        if dist is not None and dist <= NEAR_EPS
    ]


def classify_exact(turn, target_id, point, *, topology_aware):
    matches = (
        topology_exact_matches(turn, target_id, point)
        if topology_aware
        else raw_exact_matches(turn, target_id, point)
    )
    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", matches


mite_sequences = defaultdict(list)
for (turn, ship_id), state in ships.items():
    if state["hull"] == 213:
        mite_sequences[ship_id].append(state)
for seq in mite_sequences.values():
    seq.sort(key=lambda s: s["turn"])

rows = []
for mite_id, seq in mite_sequences.items():
    for before, after in zip(seq, seq[1:]):
        if after["turn"] != before["turn"] + 1:
            continue
        if not (
            before["mission"] == 7
            and before["m1"] is not None
            and before["m1"] > 0
        ):
            continue

        target_id = before["m1"]
        target_before = ship(before["turn"], target_id)
        target_after = ship(after["turn"], target_id)
        if target_before is None or target_after is None:
            continue
        if target_before["hull"] != target_after["hull"]:
            continue

        point = waypoint(before)
        raw_state, raw_matches = classify_exact(
            before["turn"], target_id, point, topology_aware=False
        )
        topo_state, topo_matches = classify_exact(
            before["turn"], target_id, point, topology_aware=True
        )
        distances = lag_distances(before["turn"], target_id, point)

        rows.append(
            {
                "mite": mite_id,
                "turn": before["turn"],
                "target": target_id,
                "shape": outcome(before, after, target_id),
                "mite_before": before,
                "mite_after": after,
                "target_before": target_before,
                "target_after": target_after,
                "raw_state": raw_state,
                "raw_matches": raw_matches,
                "topo_state": topo_state,
                "topo_matches": topo_matches,
                "topo_near_matches": topology_near_matches(before["turn"], target_id, point),
                "lag_distances": distances,
            }
        )


print()
print("===== RAW EXACT VS TOPOLOGY-AWARE EXACT =====")
changed = Counter()
for row in rows:
    changed[(row["raw_state"], row["topo_state"], row["shape"])] += 1
for (raw_state, topo_state, shape), n in sorted(changed.items()):
    if raw_state != topo_state:
        print(
            f"raw={raw_state:18s} topo={topo_state:18s} "
            f"outcome={shape:22s} n={n}"
        )

print()
print("===== TOPOLOGY-AWARE WAYPOINT STATE × OUTCOME =====")
table = defaultdict(Counter)
for row in rows:
    table[row["topo_state"]][row["shape"]] += 1
for state, c in sorted(table.items()):
    print(
        f"{state:18s} total={sum(c.values()):4d} "
        f"retained={c['retained']:4d} "
        f"immediate={c['immediate_full_clear']:3d} "
        f"pending={c['target_clear_pending']:3d}"
    )


print()
print("===== MISSION9 + END-UNCLOAKED + NEW DAMAGE CASE/CONTROL =====")
mission9_damage_rows = []
for row in rows:
    tb = row["target_before"]
    ta = row["target_after"]
    db = tb["damage"]
    da = ta["damage"]
    if not (
        tb["mission"] == 9
        and tb["cloak"] is False
        and ta["cloak"] is False
        and db is not None
        and da is not None
        and db == 0
        and da > db
    ):
        continue
    mission9_damage_rows.append(row)
    print(
        {
            "turn": (row["turn"], row["turn"] + 1),
            "target": row["target"],
            "name": tb["name"],
            "mite": row["mite"],
            "mission": (tb["mission"], ta["mission"]),
            "cloak": (tb["cloak"], ta["cloak"]),
            "damage": (db, da),
            "podcargo": (tb["podcargo"], ta["podcargo"]),
            "waypoint_raw": waypoint(row["mite_before"]),
            "raw_state": row["raw_state"],
            "topo_state": row["topo_state"],
            "lag_distances": row["lag_distances"],
            "outcome": row["shape"],
        }
    )
print("count=", len(mission9_damage_rows))


print()
print("===== MISSION9 + END-UNCLOAKED + NO NEW DAMAGE CONTROLS =====")
control_table = defaultdict(Counter)
control_examples = defaultdict(list)
for row in rows:
    tb = row["target_before"]
    ta = row["target_after"]
    db = tb["damage"]
    da = ta["damage"]
    if not (
        tb["mission"] == 9
        and tb["cloak"] is False
        and ta["cloak"] is False
        and db is not None
        and da is not None
        and da <= db
    ):
        continue
    key = row["topo_state"]
    control_table[key][row["shape"]] += 1
    if len(control_examples[key]) < 20:
        control_examples[key].append(
            {
                "turn": (row["turn"], row["turn"] + 1),
                "target": row["target"],
                "name": tb["name"],
                "mite": row["mite"],
                "mission": (tb["mission"], ta["mission"]),
                "cloak": (tb["cloak"], ta["cloak"]),
                "damage": (db, da),
                "podcargo": (tb["podcargo"], ta["podcargo"]),
                "state": row["topo_state"],
                "outcome": row["shape"],
            }
        )
for state, c in sorted(control_table.items()):
    print(
        f"{state:18s} total={sum(c.values()):3d} "
        f"retained={c['retained']:3d} "
        f"immediate={c['immediate_full_clear']:3d} "
        f"pending={c['target_clear_pending']:3d}"
    )
    for example in control_examples[state]:
        print("  ", example)


print()
print("===== VISIBLE CLOAK ONSET WAYPOINT BEHAVIOR =====")
cloak_table = defaultdict(Counter)
for row in rows:
    tb = row["target_before"]
    ta = row["target_after"]
    if tb["cloak"] is False and ta["cloak"] is True:
        cloak_table[row["topo_state"]][row["shape"]] += 1
for state, c in sorted(cloak_table.items()):
    print(
        f"{state:18s} total={sum(c.values()):3d} "
        f"retained={c['retained']:3d} "
        f"immediate={c['immediate_full_clear']:3d} "
        f"pending={c['target_clear_pending']:3d}"
    )


print()
print("===== NON-CLOAK STRICT-STALE CASES =====")
for row in sorted(rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    if not row["topo_state"].startswith("strict_stale_"):
        continue
    tb = row["target_before"]
    ta = row["target_after"]
    if ta["cloak"] is True:
        continue
    print(
        {
            "turn": (row["turn"], row["turn"] + 1),
            "target": row["target"],
            "name": tb["name"],
            "mite": row["mite"],
            "mission": (tb["mission"], ta["mission"]),
            "cloak": (tb["cloak"], ta["cloak"]),
            "damage": (tb["damage"], ta["damage"]),
            "podcargo": (tb["podcargo"], ta["podcargo"]),
            "state": row["topo_state"],
            "matches": row["topo_matches"],
            "lag_distances": row["lag_distances"],
            "outcome": row["shape"],
        }
    )


print()
print("===== FOCUS 206 / 329 TOPOLOGY-AWARE TIMELINES =====")
for target_id, mite_id, turns in (
    (206, 1167, range(64, 68)),
    (329, 1185, range(53, 58)),
):
    print()
    print("=" * 100)
    print("TARGET", target_id, "MITE", mite_id)
    print("=" * 100)
    for turn in turns:
        target = ship(turn, target_id)
        mite = ship(turn, mite_id)
        if target is None:
            continue
        point = waypoint(mite)
        raw_state = None
        raw_matches = []
        topo_state = None
        topo_matches = []
        near_matches = []
        distances = {}
        if mite is not None and mite["mission"] == 7 and mite["m1"] == target_id:
            raw_state, raw_matches = classify_exact(turn, target_id, point, topology_aware=False)
            topo_state, topo_matches = classify_exact(turn, target_id, point, topology_aware=True)
            near_matches = topology_near_matches(turn, target_id, point)
            distances = lag_distances(turn, target_id, point)
        print(
            {
                "turn": turn,
                "target_xy": xy(target),
                "target_mission": target["mission"],
                "target_cloak": target["cloak"],
                "target_damage": target["damage"],
                "target_podcargo": target["podcargo"],
                "mite": None if mite is None else {
                    "xy": xy(mite),
                    "mission": mite["mission"],
                    "m1": mite["m1"],
                    "targetxy": point,
                    "raw_state": raw_state,
                    "raw_matches": raw_matches,
                    "topo_state": topo_state,
                    "topo_matches": topo_matches,
                    "topo_near_matches": near_matches,
                    "lag_distances": distances,
                    "raw_turn": mite["raw_turn"],
                    "heading": mite["heading"],
                },
            }
        )


print()
print("===== SUMMARY HYPOTHESIS COUNTS =====")
summary = Counter()
for row in rows:
    tb = row["target_before"]
    ta = row["target_after"]
    damage_up = (
        tb["damage"] is not None
        and ta["damage"] is not None
        and ta["damage"] > tb["damage"]
    )
    if row["topo_state"].startswith("strict_stale_"):
        if ta["cloak"] is True:
            summary["strict_stale_visible_cloak"] += 1
        elif tb["mission"] == 9 and tb["cloak"] is False and ta["cloak"] is False and damage_up:
            summary["strict_stale_transient_cloak_candidate"] += 1
        else:
            summary["strict_stale_other_noncloak"] += 1
print(dict(summary))
