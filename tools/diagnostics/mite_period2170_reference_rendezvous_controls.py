from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


GAME_ID = 591478
MITE_HULL_ID = 213
PERIOD = 2170
MAX_LAG = 4
EPS = 1e-9

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

ships: dict[tuple[int, int], dict] = {}
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
    }


def ship(turn: int, ship_id: int):
    return ships.get((turn, ship_id))


def xy(s):
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def waypoint(s):
    if s is None or s["targetx"] is None or s["targety"] is None:
        return None
    return (s["targetx"], s["targety"])


def axis_delta(a: int, b: int, period: int = PERIOD) -> float:
    raw = b - a
    return ((raw + period / 2) % period) - period / 2


def distance(a, b):
    if a is None or b is None:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def exact(a, b) -> bool:
    d = distance(a, b)
    return d is not None and d <= EPS


def target_matches(turn: int, target_id: int, point):
    matches = []
    if point is None:
        return matches
    for lag in range(MAX_LAG + 1):
        target = ship(turn - lag, target_id)
        if exact(point, xy(target)):
            matches.append(lag)
    return matches


def classify_state(turn: int, target_id: int, mite_state):
    point = waypoint(mite_state)
    if point is None:
        return "missing_waypoint", []
    matches = target_matches(turn, target_id, point)
    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", matches


def outcome(after, target_id: int):
    if after is None:
        return "missing_after"
    if after["mission"] == 7 and after["m1"] == target_id:
        return "retained"
    if after["mission"] == 0 and (after["m1"] is None or after["m1"] == 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and (after["m1"] is None or after["m1"] == 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


mite_sequences = defaultdict(list)
for (turn, ship_id), state in ships.items():
    if state["hull"] == MITE_HULL_ID:
        mite_sequences[ship_id].append(state)
for seq in mite_sequences.values():
    seq.sort(key=lambda item: item["turn"])

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

        turn = before["turn"]
        target_id = before["m1"]
        target_now = ship(turn, target_id)
        target_after = ship(turn + 1, target_id)
        target_prev = ship(turn - 1, target_id)
        mite_prev = ship(turn - 1, mite_id)

        if target_now is None or target_after is None:
            continue
        if target_now["hull"] != target_after["hull"]:
            continue

        state, matches = classify_state(turn, target_id, before)

        previous_ref_id = None
        ref_prev = None
        ref_now = None
        if target_prev is not None and target_prev["m1"] not in (None, 0):
            previous_ref_id = abs(target_prev["m1"])
            ref_prev = ship(turn - 1, previous_ref_id)
            ref_now = ship(turn, previous_ref_id)

        target_prev_wp = waypoint(target_prev)
        target_now_xy = xy(target_now)
        mite_now_xy = xy(before)
        ref_prev_xy = xy(ref_prev)
        ref_now_xy = xy(ref_now)

        row = {
            "turn": turn,
            "target": target_id,
            "target_name": target_now["name"],
            "mite": mite_id,
            "state": state,
            "matches": matches,
            "outcome": outcome(after, target_id),
            "target_prev": target_prev,
            "target_now": target_now,
            "target_after": target_after,
            "mite_prev": mite_prev,
            "mite_now": before,
            "mite_after": after,
            "previous_ref_id": previous_ref_id,
            "ref_prev": ref_prev,
            "ref_now": ref_now,
            "distance_now": distance(mite_now_xy, target_now_xy),
            "distance_prev": distance(xy(mite_prev), xy(target_prev)),
            "target_arrived_prev_waypoint": exact(target_now_xy, target_prev_wp),
            "target_prev_waypoint_matches_ref_prev": exact(target_prev_wp, ref_prev_xy),
            "target_prev_waypoint_matches_ref_now": exact(target_prev_wp, ref_now_xy),
            "target_now_matches_ref_prev": exact(target_now_xy, ref_prev_xy),
            "target_now_matches_ref_now": exact(target_now_xy, ref_now_xy),
            "mite_now_matches_ref_prev": exact(mite_now_xy, ref_prev_xy),
            "mite_now_matches_ref_now": exact(mite_now_xy, ref_now_xy),
            "mite_target_exact_now": exact(mite_now_xy, target_now_xy),
        }
        row["triple_ref_rendezvous"] = (
            row["target_prev_waypoint_matches_ref_prev"]
            and row["target_now_matches_ref_prev"]
            and row["mite_now_matches_ref_prev"]
        )
        rows.append(row)


print()
print("===== PREVIOUS NONZERO-M1 ACTIVE MITE ROWS =====")
summary = Counter()
for row in rows:
    if row["previous_ref_id"] is None:
        continue
    tp = row["target_prev"]
    key = (
        "negative" if tp is not None and tp["m1"] is not None and tp["m1"] < 0 else "positive",
        row["state"],
        row["outcome"],
        row["target_prev_waypoint_matches_ref_prev"],
        row["target_now_matches_ref_prev"],
        row["mite_now_matches_ref_prev"],
        row["mite_target_exact_now"],
    )
    summary[key] += 1
for key, n in sorted(summary.items(), key=lambda item: str(item[0])):
    print({
        "m1_sign": key[0],
        "state": key[1],
        "outcome": key[2],
        "target_prev_wp_eq_ref_prev": key[3],
        "target_now_eq_ref_prev": key[4],
        "mite_now_eq_ref_prev": key[5],
        "mite_eq_target_now": key[6],
        "n": n,
    })


print()
print("===== TRIPLE REFERENCE RENDEZVOUS =====")
triple_rows = [row for row in rows if row["triple_ref_rendezvous"]]
print("count=", len(triple_rows))
print(Counter((row["state"], row["outcome"]) for row in triple_rows))
for row in sorted(triple_rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    tp = row["target_prev"]
    print({
        "turn": (row["turn"] - 1, row["turn"], row["turn"] + 1),
        "target": row["target"],
        "target_name": row["target_name"],
        "mite": row["mite"],
        "state": row["state"],
        "outcome": row["outcome"],
        "target_prev_mission": None if tp is None else tp["mission"],
        "target_prev_m1": None if tp is None else tp["m1"],
        "previous_ref_id": row["previous_ref_id"],
        "target_prev_xy": xy(tp),
        "target_prev_waypoint": waypoint(tp),
        "target_now_xy": xy(row["target_now"]),
        "ref_prev_xy": xy(row["ref_prev"]),
        "ref_now_xy": xy(row["ref_now"]),
        "mite_prev_xy": xy(row["mite_prev"]),
        "mite_now_xy": xy(row["mite_now"]),
        "mite_prev_waypoint": waypoint(row["mite_prev"]),
        "mite_now_waypoint": waypoint(row["mite_now"]),
        "distance_prev": row["distance_prev"],
        "distance_now": row["distance_now"],
    })


print()
print("===== NEGATIVE PREVIOUS-M1 CONTROLS =====")
negative_rows = [
    row for row in rows
    if row["target_prev"] is not None
    and row["target_prev"]["m1"] is not None
    and row["target_prev"]["m1"] < 0
]
print("count=", len(negative_rows))
print(Counter((row["state"], row["outcome"]) for row in negative_rows))
for row in sorted(negative_rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    tp = row["target_prev"]
    print({
        "turn": (row["turn"] - 1, row["turn"], row["turn"] + 1),
        "target": row["target"],
        "target_name": row["target_name"],
        "mite": row["mite"],
        "state": row["state"],
        "outcome": row["outcome"],
        "target_prev_mission": tp["mission"],
        "target_prev_m1": tp["m1"],
        "previous_ref_id": row["previous_ref_id"],
        "target_prev_wp_eq_ref_prev": row["target_prev_waypoint_matches_ref_prev"],
        "target_now_eq_ref_prev": row["target_now_matches_ref_prev"],
        "mite_now_eq_ref_prev": row["mite_now_matches_ref_prev"],
        "mite_eq_target_now": row["mite_target_exact_now"],
        "distance_now": row["distance_now"],
        "target_prev_xy": xy(tp),
        "target_prev_waypoint": waypoint(tp),
        "target_now_xy": xy(row["target_now"]),
        "ref_prev_xy": xy(row["ref_prev"]),
        "ref_now_xy": xy(row["ref_now"]),
        "mite_now_xy": xy(row["mite_now"]),
    })


print()
print("===== CLOSEST CURRENT+RETAINED CONTACT CONTROLS =====")
controls = [
    row for row in rows
    if row["state"] == "current" and row["outcome"] == "retained" and row["distance_now"] is not None
]
for row in sorted(controls, key=lambda r: (r["distance_now"], r["turn"], r["mite"]))[:40]:
    tp = row["target_prev"]
    print({
        "distance_now": row["distance_now"],
        "turn": row["turn"],
        "target": row["target"],
        "target_name": row["target_name"],
        "mite": row["mite"],
        "target_prev_mission": None if tp is None else tp["mission"],
        "target_prev_m1": None if tp is None else tp["m1"],
        "previous_ref_id": row["previous_ref_id"],
        "target_arrived_prev_waypoint": row["target_arrived_prev_waypoint"],
        "target_prev_wp_eq_ref_prev": row["target_prev_waypoint_matches_ref_prev"],
        "target_now_eq_ref_prev": row["target_now_matches_ref_prev"],
        "mite_now_eq_ref_prev": row["mite_now_matches_ref_prev"],
        "target_xy": xy(row["target_now"]),
        "mite_xy": xy(row["mite_now"]),
    })


print()
print("===== REFERENCE-ARRIVAL CONTROLS (TARGET NOW == REF PREV) =====")
ref_arrivals = [
    row for row in rows
    if row["previous_ref_id"] is not None and row["target_now_matches_ref_prev"]
]
print("count=", len(ref_arrivals))
print(Counter((row["state"], row["outcome"]) for row in ref_arrivals))
for row in sorted(ref_arrivals, key=lambda r: (r["turn"], r["target"], r["mite"])):
    tp = row["target_prev"]
    print({
        "turn": (row["turn"] - 1, row["turn"], row["turn"] + 1),
        "target": row["target"],
        "target_name": row["target_name"],
        "mite": row["mite"],
        "state": row["state"],
        "outcome": row["outcome"],
        "target_prev_mission": None if tp is None else tp["mission"],
        "target_prev_m1": None if tp is None else tp["m1"],
        "previous_ref_id": row["previous_ref_id"],
        "target_prev_wp_eq_ref_prev": row["target_prev_waypoint_matches_ref_prev"],
        "mite_now_eq_ref_prev": row["mite_now_matches_ref_prev"],
        "mite_eq_target_now": row["mite_target_exact_now"],
        "distance_now": row["distance_now"],
        "target_now_xy": xy(row["target_now"]),
        "ref_prev_xy": xy(row["ref_prev"]),
        "mite_now_xy": xy(row["mite_now"]),
    })


print()
print("===== FOCUS 329 / 1185 AND 206 / 1167 =====")
for target_id, mite_id, turn in ((329, 1185, 56), (206, 1167, 66)):
    row = next(
        (r for r in rows if r["turn"] == turn and r["target"] == target_id and r["mite"] == mite_id),
        None,
    )
    if row is None:
        print({"target": target_id, "mite": mite_id, "turn": turn, "missing": True})
        continue
    tp = row["target_prev"]
    print({
        "turn": (turn - 1, turn, turn + 1),
        "target": target_id,
        "target_name": row["target_name"],
        "mite": mite_id,
        "state": row["state"],
        "outcome": row["outcome"],
        "target_prev_mission": None if tp is None else tp["mission"],
        "target_prev_m1": None if tp is None else tp["m1"],
        "target_prev_cloak": None if tp is None else tp["cloak"],
        "target_now_cloak": row["target_now"]["cloak"],
        "target_prev_damage": None if tp is None else tp["damage"],
        "target_now_damage": row["target_now"]["damage"],
        "target_prev_podcargo": None if tp is None else tp["podcargo"],
        "target_now_podcargo": row["target_now"]["podcargo"],
        "previous_ref_id": row["previous_ref_id"],
        "target_prev_wp_eq_ref_prev": row["target_prev_waypoint_matches_ref_prev"],
        "target_now_eq_ref_prev": row["target_now_matches_ref_prev"],
        "mite_now_eq_ref_prev": row["mite_now_matches_ref_prev"],
        "mite_eq_target_now": row["mite_target_exact_now"],
        "triple_ref_rendezvous": row["triple_ref_rendezvous"],
        "distance_prev": row["distance_prev"],
        "distance_now": row["distance_now"],
    })

print()
print("NOTE: period=2170 is an empirical candidate for game 591478 only.")
print("This diagnostic searches for retained controls for the 329 reference/contact pattern; it does not assert causality or name numeric missions.")
