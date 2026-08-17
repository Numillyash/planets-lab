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
        "raw_turn": _intish(raw.get("turn")),
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
    out = []
    if point is None:
        return out
    for lag in range(MAX_LAG + 1):
        target = ship(turn - lag, target_id)
        if exact(point, xy(target)):
            out.append(lag)
    return out


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


def distance_bucket(value):
    if value is None:
        return "missing"
    if value <= EPS:
        return "exact_0"
    if value <= 3:
        return "le_3"
    if value <= 10:
        return "le_10"
    if value <= 20:
        return "le_20"
    if value <= 50:
        return "le_50"
    return "gt_50"


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
        target_id = before["m1"]
        target = ship(before["turn"], target_id)
        target_after = ship(after["turn"], target_id)
        if target is None or target_after is None or target["hull"] != target_after["hull"]:
            continue
        state, matches = classify_state(before["turn"], target_id, before)
        rows.append({
            "mite": mite_id,
            "turn": before["turn"],
            "target": target_id,
            "state": state,
            "matches": matches,
            "outcome": outcome(after, target_id),
            "mite_state": before,
            "mite_after": after,
            "target_state": target,
            "target_after": target_after,
            "distance": distance(xy(before), xy(target)),
        })

rows_by_mite_turn = {(row["mite"], row["turn"]): row for row in rows}

print()
print("===== MITE-TARGET SEPARATION x STATE x OUTCOME =====")
sep_table = Counter()
for row in rows:
    sep_table[(distance_bucket(row["distance"]), row["state"], row["outcome"])] += 1
for (bucket, state, shape), n in sorted(sep_table.items()):
    print({"distance": bucket, "state": state, "outcome": shape, "n": n})

print()
print("===== EXACT-CONTACT ACTIVE MITE ROWS =====")
exact_rows = [row for row in rows if row["distance"] is not None and row["distance"] <= EPS]
exact_summary = Counter((row["state"], row["outcome"]) for row in exact_rows)
for (state, shape), n in sorted(exact_summary.items()):
    print({"state": state, "outcome": shape, "n": n})
print("count=", len(exact_rows))
for row in sorted(exact_rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    print({
        "turn": (row["turn"], row["turn"] + 1),
        "target": row["target"],
        "target_name": row["target_state"]["name"],
        "mite": row["mite"],
        "state": row["state"],
        "outcome": row["outcome"],
        "mite_xy": xy(row["mite_state"]),
        "target_xy": xy(row["target_state"]),
        "mite_waypoint": waypoint(row["mite_state"]),
        "target_mission": row["target_state"]["mission"],
        "target_m1": row["target_state"]["m1"],
        "target_cloak": row["target_state"]["cloak"],
    })

onsets = []
for row in rows:
    if row["state"] == "current":
        continue
    prev = rows_by_mite_turn.get((row["mite"], row["turn"] - 1))
    if prev is None or prev["target"] != row["target"] or prev["state"] != "current":
        continue

    turn = row["turn"]
    target_id = row["target"]
    target_prev = ship(turn - 1, target_id)
    target_now = ship(turn, target_id)
    mite_prev = ship(turn - 1, row["mite"])
    mite_now = row["mite_state"]

    previous_ref_id = None
    ref_prev = None
    ref_now = None
    if target_prev is not None and target_prev["m1"] not in (None, 0):
        previous_ref_id = abs(target_prev["m1"])
        ref_prev = ship(turn - 1, previous_ref_id)
        ref_now = ship(turn, previous_ref_id)

    onsets.append({
        **row,
        "prev_row": prev,
        "target_prev": target_prev,
        "target_now": target_now,
        "mite_prev": mite_prev,
        "mite_now": mite_now,
        "previous_ref_id": previous_ref_id,
        "ref_prev": ref_prev,
        "ref_now": ref_now,
        "distance_prev": distance(xy(mite_prev), xy(target_prev)),
        "distance_now": distance(xy(mite_now), xy(target_now)),
        "target_arrived_prev_waypoint": exact(xy(target_now), waypoint(target_prev)),
        "target_prev_waypoint_error": distance(xy(target_now), waypoint(target_prev)),
        "target_prev_waypoint_matches_ref_prev": exact(waypoint(target_prev), xy(ref_prev)),
        "target_prev_waypoint_matches_ref_now": exact(waypoint(target_prev), xy(ref_now)),
        "target_now_matches_ref_prev": exact(xy(target_now), xy(ref_prev)),
        "target_now_matches_ref_now": exact(xy(target_now), xy(ref_now)),
        "mite_now_matches_ref_prev": exact(xy(mite_now), xy(ref_prev)),
        "mite_now_matches_ref_now": exact(xy(mite_now), xy(ref_now)),
    })

print()
print("===== CURRENT -> NONCURRENT ONSET FEATURE COUNTS =====")
features = Counter()
for row in onsets:
    tp = row["target_prev"]
    tn = row["target_now"]
    if row["distance_now"] is not None and row["distance_now"] <= EPS:
        features["mite_target_exact_contact_now"] += 1
    if row["distance_now"] is not None and row["distance_now"] <= 3:
        features["mite_target_le3_now"] += 1
    if row["target_arrived_prev_waypoint"]:
        features["target_arrived_previous_waypoint"] += 1
    if tp is not None and tp["m1"] is not None and tp["m1"] < 0:
        features["target_previous_m1_negative"] += 1
    if row["previous_ref_id"] is not None:
        features["target_previous_m1_nonzero"] += 1
    if row["target_prev_waypoint_matches_ref_prev"]:
        features["target_prev_waypoint_exact_ref_prev"] += 1
    if row["target_now_matches_ref_prev"]:
        features["target_now_exact_ref_prev"] += 1
    if row["mite_now_matches_ref_prev"]:
        features["mite_now_exact_ref_prev"] += 1
    if tp is not None and tn is not None and tp["cloak"] is True:
        features["target_cloak_prev_true"] += 1
    if tp is not None and tn is not None and tn["cloak"] is True:
        features["target_cloak_now_true"] += 1
    if tp is not None and tn is not None and tp["cloak"] is False and tn["cloak"] is False:
        features["target_cloak_false_false"] += 1
print("onset_rows=", len(onsets))
for name, n in sorted(features.items()):
    print({"feature": name, "n": n})

print()
print("===== CURRENT -> NONCURRENT ONSETS: FULL CONTACT/REFERENCE CONTEXT =====")
for row in sorted(onsets, key=lambda r: (r["turn"], r["target"], r["mite"])):
    tp = row["target_prev"]
    tn = row["target_now"]
    print({
        "turn": (row["turn"] - 1, row["turn"], row["turn"] + 1),
        "target": row["target"],
        "target_name": None if tn is None else tn["name"],
        "mite": row["mite"],
        "state_now": row["state"],
        "matches_now": row["matches"],
        "outcome_now_to_next": row["outcome"],
        "mite_target_distance": (row["distance_prev"], row["distance_now"]),
        "mite_xy": (xy(row["mite_prev"]), xy(row["mite_now"])),
        "mite_waypoint": (waypoint(row["prev_row"]["mite_state"]), waypoint(row["mite_now"])),
        "target_xy": (xy(tp), xy(tn)),
        "target_waypoint_prev": waypoint(tp),
        "target_arrived_prev_waypoint": row["target_arrived_prev_waypoint"],
        "target_prev_waypoint_error": row["target_prev_waypoint_error"],
        "target_mission": (None if tp is None else tp["mission"], None if tn is None else tn["mission"]),
        "target_m1": (None if tp is None else tp["m1"], None if tn is None else tn["m1"]),
        "target_cloak": (None if tp is None else tp["cloak"], None if tn is None else tn["cloak"]),
        "target_damage": (None if tp is None else tp["damage"], None if tn is None else tn["damage"]),
        "target_podcargo": (None if tp is None else tp["podcargo"], None if tn is None else tn["podcargo"]),
        "previous_ref_id": row["previous_ref_id"],
        "ref_prev_xy": xy(row["ref_prev"]),
        "ref_now_xy": xy(row["ref_now"]),
        "target_prev_waypoint_matches_ref_prev": row["target_prev_waypoint_matches_ref_prev"],
        "target_now_matches_ref_prev": row["target_now_matches_ref_prev"],
        "target_now_matches_ref_now": row["target_now_matches_ref_now"],
        "mite_now_matches_ref_prev": row["mite_now_matches_ref_prev"],
        "mite_now_matches_ref_now": row["mite_now_matches_ref_now"],
    })

print()
print("===== ARRIVAL-AT-PREVIOUS-WAYPOINT CONTROLS =====")
arrival_table = Counter()
arrival_examples = defaultdict(list)
for row in rows:
    prev = rows_by_mite_turn.get((row["mite"], row["turn"] - 1))
    if prev is None or prev["target"] != row["target"]:
        continue
    target_prev = ship(row["turn"] - 1, row["target"])
    target_now = row["target_state"]
    arrived = exact(xy(target_now), waypoint(target_prev))
    if not arrived:
        continue
    key = (row["state"], row["outcome"])
    arrival_table[key] += 1
    if len(arrival_examples[key]) < 20:
        arrival_examples[key].append({
            "turn": row["turn"],
            "target": row["target"],
            "target_name": target_now["name"],
            "mite": row["mite"],
            "distance_now": row["distance"],
            "target_prev_mission": None if target_prev is None else target_prev["mission"],
            "target_prev_m1": None if target_prev is None else target_prev["m1"],
            "target_now_mission": target_now["mission"],
            "target_now_m1": target_now["m1"],
        })
for (state, shape), n in sorted(arrival_table.items()):
    print({"state": state, "outcome": shape, "n": n})
    for item in arrival_examples[(state, shape)]:
        print("  ", item)

print()
print("===== FOCUS 329 / 1185 =====")
for row in onsets:
    if row["target"] == 329 and row["mite"] == 1185:
        print({
            "turn": (row["turn"] - 1, row["turn"], row["turn"] + 1),
            "distance_prev": row["distance_prev"],
            "distance_now": row["distance_now"],
            "target_prev_xy": xy(row["target_prev"]),
            "target_now_xy": xy(row["target_now"]),
            "target_prev_waypoint": waypoint(row["target_prev"]),
            "target_arrived_prev_waypoint": row["target_arrived_prev_waypoint"],
            "target_prev_mission": None if row["target_prev"] is None else row["target_prev"]["mission"],
            "target_prev_m1": None if row["target_prev"] is None else row["target_prev"]["m1"],
            "previous_ref_id": row["previous_ref_id"],
            "ref_prev_xy": xy(row["ref_prev"]),
            "ref_now_xy": xy(row["ref_now"]),
            "mite_prev_xy": xy(row["mite_prev"]),
            "mite_now_xy": xy(row["mite_now"]),
            "mite_now_matches_target": exact(xy(row["mite_now"]), xy(row["target_now"])),
            "mite_now_matches_ref_prev": row["mite_now_matches_ref_prev"],
            "state_now": row["state"],
            "outcome": row["outcome"],
        })

print()
print("NOTE: period=2170 is an empirical candidate for game 591478 only.")
print("The diagnostic tests contact/arrival correlations; it does not name numeric missions or assert causality.")
