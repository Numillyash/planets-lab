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
MAX_LAG = 4
PERIODS = (2150, 2170)
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


def wrapped_axis_delta(a: int, b: int, period: int) -> int:
    raw = b - a
    candidates = (raw - period, raw, raw + period)
    return min(candidates, key=lambda value: (abs(value), abs(value - raw)))


def period_distance(a, b, period: int):
    if a is None or b is None:
        return None
    dx = wrapped_axis_delta(a[0], b[0], period)
    dy = wrapped_axis_delta(a[1], b[1], period)
    return hypot(dx, dy)


def target_history_distances(turn: int, target_id: int, point, period: int):
    distances = {}
    if point is None:
        return distances
    for lag in range(MAX_LAG + 1):
        target = ship(turn - lag, target_id)
        target_point = xy(target)
        if target_point is None:
            continue
        distances[lag] = period_distance(point, target_point, period)
    return distances


def classify_state(turn: int, target_id: int, point, period: int):
    distances = target_history_distances(turn, target_id, point, period)
    exact = [lag for lag, d in distances.items() if d is not None and d <= EXACT_EPS]
    near = [lag for lag, d in distances.items() if d is not None and d <= NEAR_EPS]
    if 0 in exact:
        state = "current"
    elif exact:
        state = f"strict_stale_{min(exact)}"
    else:
        state = "no_match_0_4"
    return state, exact, near, distances


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
for (_turn, ship_id), state in ships.items():
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
        target_before = ship(before["turn"], target_id)
        target_after = ship(after["turn"], target_id)
        if target_before is None or target_after is None:
            continue
        if target_before["hull"] != target_after["hull"]:
            continue

        point = waypoint(before)
        period_data = {}
        for period in PERIODS:
            state, exact, near, distances = classify_state(
                before["turn"], target_id, point, period
            )
            period_data[period] = {
                "state": state,
                "exact": exact,
                "near": near,
                "distances": distances,
            }

        rows.append({
            "mite": mite_id,
            "turn": before["turn"],
            "target": target_id,
            "target_name": target_before["name"],
            "shape": outcome(after, target_id),
            "mite_before": before,
            "mite_after": after,
            "target_before": target_before,
            "target_after": target_after,
            "period": period_data,
        })


print()
print("===== STATE RECLASSIFICATION 2150 -> 2170 =====")
reclass = Counter()
for row in rows:
    s2150 = row["period"][2150]["state"]
    s2170 = row["period"][2170]["state"]
    reclass[(s2150, s2170, row["shape"])] += 1
for (s2150, s2170, shape), n in sorted(reclass.items()):
    print({
        "state_2150": s2150,
        "state_2170": s2170,
        "outcome": shape,
        "n": n,
    })

for period in PERIODS:
    print()
    print(f"===== PERIOD {period}: WAYPOINT STATE x OUTCOME =====")
    table = defaultdict(Counter)
    for row in rows:
        table[row["period"][period]["state"]][row["shape"]] += 1
    for state, counts in sorted(table.items()):
        print(
            f"{state:18s} total={sum(counts.values()):4d} "
            f"retained={counts['retained']:4d} "
            f"immediate={counts['immediate_full_clear']:3d} "
            f"pending={counts['target_clear_pending']:3d}"
        )

print()
print("===== ROWS WHOSE EXACT STATE CHANGES UNDER 2170 =====")
for row in sorted(rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    p0 = row["period"][2150]
    p1 = row["period"][2170]
    if p0["state"] == p1["state"]:
        continue
    print({
        "turn": row["turn"],
        "target": row["target"],
        "target_name": row["target_name"],
        "mite": row["mite"],
        "waypoint": waypoint(row["mite_before"]),
        "target_xy": xy(row["target_before"]),
        "state_2150": p0["state"],
        "state_2170": p1["state"],
        "exact_2150": p0["exact"],
        "exact_2170": p1["exact"],
        "near_2170": p1["near"],
        "distances_2150": p0["distances"],
        "distances_2170": p1["distances"],
        "outcome": row["shape"],
    })

rows_by_mite_turn = {(row["mite"], row["turn"]): row for row in rows}

for period in PERIODS:
    print()
    print(f"===== PERIOD {period}: STALE/NO-MATCH ONSET SUMMARY =====")
    onset = Counter()
    for row in rows:
        state = row["period"][period]["state"]
        if state == "current":
            continue
        prev = rows_by_mite_turn.get((row["mite"], row["turn"] - 1))
        if prev is None:
            kind = "first_noncurrent"
        elif prev["target"] != row["target"]:
            kind = "target_changed"
        else:
            prev_state = prev["period"][period]["state"]
            kind = f"{prev_state}->{state}"
        onset[(kind, row["shape"])] += 1
    for (kind, shape), n in sorted(onset.items()):
        print({"onset": kind, "outcome": shape, "n": n})

print()
print("===== PERIOD 2170: CURRENT -> STRICT-STALE ONSETS =====")
for row in sorted(rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    state = row["period"][2170]["state"]
    if not state.startswith("strict_stale_"):
        continue
    prev = rows_by_mite_turn.get((row["mite"], row["turn"] - 1))
    if prev is None or prev["target"] != row["target"]:
        continue
    if prev["period"][2170]["state"] != "current":
        continue
    tb = row["target_before"]
    ta = row["target_after"]
    print({
        "turn": (row["turn"], row["turn"] + 1),
        "target": row["target"],
        "target_name": row["target_name"],
        "mite": row["mite"],
        "state": state,
        "matches": row["period"][2170]["exact"],
        "waypoint": waypoint(row["mite_before"]),
        "target_xy": xy(tb),
        "target_mission": (tb["mission"], ta["mission"]),
        "target_m1": (tb["m1"], ta["m1"]),
        "target_cloak": (tb["cloak"], ta["cloak"]),
        "target_damage": (tb["damage"], ta["damage"]),
        "target_podcargo": (tb["podcargo"], ta["podcargo"]),
        "outcome": row["shape"],
    })

print()
print("===== FOCUS 329 / 1185 UNDER BOTH PERIODS =====")
for turn in range(53, 58):
    target = ship(turn, 329)
    mite = ship(turn, 1185)
    if target is None or mite is None:
        continue
    item = {
        "turn": turn,
        "target_xy": xy(target),
        "target_waypoint": waypoint(target),
        "target_mission": target["mission"],
        "target_m1": target["m1"],
        "target_cloak": target["cloak"],
        "mite_xy": xy(mite),
        "mite_waypoint": waypoint(mite),
        "mite_mission": mite["mission"],
        "mite_m1": mite["m1"],
    }
    if mite["mission"] == 7 and mite["m1"] == 329:
        for period in PERIODS:
            state, exact, near, distances = classify_state(
                turn, 329, waypoint(mite), period
            )
            item[f"p{period}"] = {
                "state": state,
                "exact": exact,
                "near": near,
                "distances": distances,
            }
    print(item)

print()
print("NOTE: period=2170 is an empirical candidate for game 591478 only.")
print("This diagnostic does not assert a universal mapwidth+20 Host rule.")
