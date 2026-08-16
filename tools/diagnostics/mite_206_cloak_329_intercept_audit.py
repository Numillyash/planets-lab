from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path

from planets_lab.corpus.archive import read_archive_member, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


GAME_ID = 591478
MITE_HULL_ID = 213
MAX_LAG = 4

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
ship_groups = group_perspective_records(records, "ship")
topology = extract_map_topology(archive_data)

members = turn_members(archive_data)
if not members:
    raise RuntimeError("archive contains no .trn members")
payload = read_archive_member(archive_data, members[0].name)
if payload[:2] == b"\x1f\x8b":
    payload = gzip.decompress(payload)
raw_first = json.loads(payload.decode("utf-8-sig"))

hull_meta = {
    _intish(row.get("id")): {
        "name": row.get("name"),
        "cancloak": row.get("cancloak"),
        "special": row.get("special"),
    }
    for row in raw_first.get("hulls", [])
    if isinstance(row, dict) and _intish(row.get("id")) is not None
}

ships: dict[tuple[int, int], dict] = {}
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
        "warp": _intish(raw.get("warp")),
        "heading": _intish(raw.get("heading")),
        "mission": _intish(raw.get("mission")),
        "m1": _intish(raw.get("mission1target")),
        "m2": _intish(raw.get("mission2target")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
        "fuel": _intish(raw.get("neutronium")),
        "mass": _intish(raw.get("mass")),
        "fc": raw.get("friendlycode"),
        "raw_turn": _intish(raw.get("turn")),
        "infoturn": _intish(raw.get("infoturn")),
        "readystatus": _intish(raw.get("readystatus")),
        "raw": raw,
    }


def ship(turn: int, ship_id: int):
    return ships.get((turn, ship_id))


def xy(s):
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def distance(a, b):
    dx, dy = _vector(a, b, topology)
    return hypot(dx, dy)


def target_point(turn: int, target: int):
    return xy(ship(turn, target))


def strict_state(turn: int, target: int, mite: dict):
    waypoint = (mite["targetx"], mite["targety"])
    if None in waypoint:
        return "missing", []
    matches = []
    for lag in range(MAX_LAG + 1):
        p = target_point(turn - lag, target)
        if p is None:
            continue
        if distance(waypoint, p) == 0:
            matches.append(lag)
    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", []


def outcome(before: dict, after: dict, target: int):
    if after["mission"] == 7 and after["m1"] == target:
        return "retained"
    if after["mission"] == 0 and (after["m1"] is None or after["m1"] == 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and (after["m1"] is None or after["m1"] == 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


# ---------------------------------------------------------------------------
# Active Mite rows.
# ---------------------------------------------------------------------------

mite_seq = defaultdict(list)
for (turn, ship_id), s in ships.items():
    if s["hull"] == MITE_HULL_ID:
        mite_seq[ship_id].append(s)
for seq in mite_seq.values():
    seq.sort(key=lambda s: s["turn"])

member_rows = []
for mite_id, seq in mite_seq.items():
    for before, after in zip(seq, seq[1:]):
        if after["turn"] != before["turn"] + 1:
            continue
        if not (before["mission"] == 7 and before["m1"] is not None and before["m1"] > 0):
            continue
        target = before["m1"]
        tb = ship(before["turn"], target)
        ta = ship(after["turn"], target)
        if tb is None or ta is None or tb["hull"] != ta["hull"]:
            continue
        state, matches = strict_state(before["turn"], target, before)
        member_rows.append({
            "mite": mite_id,
            "turn": before["turn"],
            "after_turn": after["turn"],
            "target": target,
            "state": state,
            "matches": matches,
            "shape": outcome(before, after, target),
            "mite_before": before,
            "target_before": tb,
            "target_after": ta,
        })


# ---------------------------------------------------------------------------
# 1. Decompose strict-stale rows by recent *observed* cloak history.
# This separates ordinary post-cloak stale state from genuinely unexplained
# non-cloak stale state.
# ---------------------------------------------------------------------------

print()
print("===== STRICT-STALE × RECENT OBSERVED CLOAK HISTORY =====")
recent_table = defaultdict(Counter)
no_recent_examples = []

for row in member_rows:
    if not row["state"].startswith("strict_stale_"):
        continue

    cloak_lags = []
    for lag in range(MAX_LAG + 1):
        s = ship(row["turn"] - lag, row["target"])
        if s is not None and s["cloak"] is True:
            cloak_lags.append(lag)

    if not cloak_lags:
        recent = "no_observed_cloak_0_4"
        no_recent_examples.append(row)
    elif 0 in cloak_lags:
        recent = "cloak_now"
    else:
        recent = f"recent_cloak_lag{min(cloak_lags)}"

    recent_table[recent][row["shape"]] += 1

for recent, c in sorted(recent_table.items()):
    print(
        f"{recent:24s} total={sum(c.values()):3d} "
        f"retained={c['retained']:3d} "
        f"immediate={c['immediate_full_clear']:3d} "
        f"pending={c['target_clear_pending']:3d}"
    )

print()
print("===== STRICT-STALE WITH NO OBSERVED CLOAK IN T..T-4 =====")
for row in sorted(no_recent_examples, key=lambda r: (r["turn"], r["target"], r["mite"])):
    history = []
    for turn in range(row["turn"] - 4, row["turn"] + 1):
        s = ship(turn, row["target"])
        if s is None:
            continue
        history.append({
            "turn": turn,
            "xy": xy(s),
            "mission": s["mission"],
            "m1": s["m1"],
            "cloak": s["cloak"],
            "damage": s["damage"],
            "podcargo": s["podcargo"],
        })
    print({
        "turn": row["turn"],
        "target": row["target"],
        "name": row["target_before"]["name"],
        "hull": row["target_before"]["hull"],
        "mite": row["mite"],
        "state": row["state"],
        "matches": row["matches"],
        "outcome": row["shape"],
        "history": history,
    })


# ---------------------------------------------------------------------------
# 2. Empirically test whether raw owner mission=9 predicts next-turn cloak.
# We do not assign a semantic name to mission code 9 here; this is a pure
# transition table over cloak-capable hulls.
# ---------------------------------------------------------------------------

print()
print("===== CLOAK-CAPABLE: CURRENT MISSION -> NEXT OBSERVED CLOAK =====")
mission_table = defaultdict(Counter)
mission9_examples = []

by_ship = defaultdict(list)
for (turn, ship_id), s in ships.items():
    by_ship[ship_id].append(s)
for seq in by_ship.values():
    seq.sort(key=lambda s: s["turn"])

for ship_id, seq in by_ship.items():
    for a, b in zip(seq, seq[1:]):
        if b["turn"] != a["turn"] + 1:
            continue
        if a["hull"] != b["hull"]:
            continue
        meta = hull_meta.get(a["hull"], {})
        if meta.get("cancloak") is not True:
            continue
        if a["cloak"] is not False:
            continue

        damage_delta = None
        if a["damage"] is not None and b["damage"] is not None:
            damage_delta = b["damage"] - a["damage"]

        bucket = (
            "next_cloak_true" if b["cloak"] is True
            else "next_cloak_false"
        )
        if damage_delta is not None and damage_delta > 0:
            bucket += "_damage_up"

        mission_table[a["mission"]][bucket] += 1

        if a["mission"] == 9:
            mission9_examples.append({
                "turn": (a["turn"], b["turn"]),
                "ship": ship_id,
                "name": a["name"],
                "hull": a["hull"],
                "hull_name": meta.get("name"),
                "mission": (a["mission"], b["mission"]),
                "cloak": (a["cloak"], b["cloak"]),
                "damage": (a["damage"], b["damage"]),
                "podcargo": (a["podcargo"], b["podcargo"]),
            })

for mission, c in sorted(mission_table.items(), key=lambda item: (-sum(item[1].values()), item[0] if item[0] is not None else -999)):
    print(
        f"mission={mission!r:>4} total={sum(c.values()):4d} "
        f"next_cloak_true={c['next_cloak_true']:4d} "
        f"next_cloak_true_damage_up={c['next_cloak_true_damage_up']:3d} "
        f"next_cloak_false={c['next_cloak_false']:4d} "
        f"next_cloak_false_damage_up={c['next_cloak_false_damage_up']:3d}"
    )

print()
print("===== MISSION 9 WHILE CURRENTLY UNCLOAKED: EXCEPTIONS / CONTROLS =====")
for row in mission9_examples:
    if row["cloak"][1] is False or row["damage"][1] != row["damage"][0] or row["hull"] == 1033:
        print(row)

print()
print("===== HULL 1033 COMPLETE OWNER TIMELINE =====")
for (turn, ship_id), s in sorted(ships.items()):
    if s["hull"] != 1033:
        continue
    print({
        "turn": turn,
        "ship": ship_id,
        "xy": xy(s),
        "mission": s["mission"],
        "m1": s["m1"],
        "cloak": s["cloak"],
        "damage": s["damage"],
        "podcargo": s["podcargo"],
        "warp": s["warp"],
        "targetxy": (s["targetx"], s["targety"]),
    })


# ---------------------------------------------------------------------------
# 3. Target 329: inspect the anomalous movement/mission turn directly.
# ---------------------------------------------------------------------------

print()
print("===== TARGET 329 FULL RELEVANT RAW TIMELINE =====")
focus_keys = {
    "id", "ownerid", "hullid", "name", "x", "y", "warp", "heading",
    "targetx", "targety", "mission", "mission1target", "mission2target",
    "iscloaked", "damage", "mass", "neutronium", "friendlycode",
    "towtargetid", "towcaptured", "towingid", "interceptid", "enemy",
    "turn", "infoturn", "readystatus",
}
for turn in range(52, 58):
    s = ship(turn, 329)
    if s is None:
        continue
    raw = s["raw"]
    selected = {
        key: raw.get(key)
        for key in sorted(focus_keys)
        if key in raw
    }
    # Also surface any schema fields whose names directly suggest movement,
    # tow/intercept, command-group, or waypoint state.
    for key, value in sorted(raw.items()):
        lk = key.lower()
        if any(token in lk for token in (
            "tow", "intercept", "waypoint", "command", "flotilla", "group",
            "stargate", "chunnel",
        )):
            selected.setdefault(key, value)
    print("turn", turn, selected)

print()
print("===== TARGET 329 TOPOLOGY MOVEMENT DISTANCES =====")
for turn in range(52, 57):
    a = ship(turn, 329)
    b = ship(turn + 1, 329)
    if a is None or b is None:
        continue
    print({
        "turn": (turn, turn + 1),
        "from": xy(a),
        "to": xy(b),
        "distance": distance(xy(a), xy(b)),
        "mission": (a["mission"], b["mission"]),
        "m1": (a["m1"], b["m1"]),
        "warp": (a["warp"], b["warp"]),
    })

print()
print("===== TARGET 329 NEARBY SHIPS AROUND ANOMALY =====")
for turn in (54, 55, 56):
    target = ship(turn, 329)
    if target is None:
        continue
    p = xy(target)
    nearby = []
    for (t, sid), s in ships.items():
        if t != turn or sid == 329:
            continue
        sp = xy(s)
        if sp is None:
            continue
        d = distance(p, sp)
        if d <= 160:
            nearby.append({
                "distance": d,
                "id": sid,
                "owner": s["owner"],
                "hull": s["hull"],
                "name": s["name"],
                "mission": s["mission"],
                "m1": s["m1"],
                "warp": s["warp"],
                "xy": sp,
            })
    nearby.sort(key=lambda r: r["distance"])
    print("turn", turn)
    for row in nearby[:30]:
        print(" ", row)

print()
print("===== MITE 1185 / TARGET 329 WAYPOINT ERROR =====")
for turn in range(53, 57):
    target = ship(turn, 329)
    mite = ship(turn, 1185)
    if target is None or mite is None:
        continue
    wp = (mite["targetx"], mite["targety"])
    print({
        "turn": turn,
        "target": xy(target),
        "mite_xy": xy(mite),
        "mite_targetxy": wp,
        "waypoint_error_to_current": distance(wp, xy(target)),
        "state": strict_state(turn, 329, mite),
        "target_mission": target["mission"],
        "target_m1": target["m1"],
        "target_warp": target["warp"],
        "mite_heading": mite["heading"],
    })
