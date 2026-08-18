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
        "enemy": _intish(raw.get("enemy")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "crew": _intish(raw.get("crew")),
        "mass": _intish(raw.get("mass")),
        "fuel": _intish(raw.get("neutronium")),
        "podcargo": _intish(raw.get("podcargo")),
        "warp": _intish(raw.get("warp")),
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


def delta(new, old):
    if new is None or old is None:
        return None
    return new - old


def compact(s):
    if s is None:
        return None
    return {
        "id": s["id"],
        "owner": s["owner"],
        "hull": s["hull"],
        "name": s["name"],
        "xy": xy(s),
        "targetxy": waypoint(s),
        "warp": s["warp"],
        "mission": s["mission"],
        "m1": s["m1"],
        "enemy": s["enemy"],
        "cloak": s["cloak"],
        "damage": s["damage"],
        "crew": s["crew"],
        "mass": s["mass"],
        "fuel": s["fuel"],
        "podcargo": s["podcargo"],
        "raw_turn": s["raw_turn"],
    }


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
        target_prev = ship(turn - 1, target_id)
        target_now = ship(turn, target_id)
        target_next = ship(turn + 1, target_id)
        mite_prev = ship(turn - 1, mite_id)
        mite_next = after

        if target_now is None:
            continue

        state, matches = classify_state(turn, target_id, before)
        row_outcome = outcome(after, target_id)

        row = {
            "turn": turn,
            "mite": mite_id,
            "target": target_id,
            "target_hull": target_now["hull"],
            "target_name": target_now["name"],
            "state": state,
            "matches": matches,
            "outcome": row_outcome,
            "mite_prev": mite_prev,
            "mite_now": before,
            "mite_next": mite_next,
            "target_prev": target_prev,
            "target_now": target_now,
            "target_next": target_next,
            "distance_prev": distance(xy(mite_prev), xy(target_prev)),
            "distance_now": distance(xy(before), xy(target_now)),
            "distance_next": distance(xy(mite_next), xy(target_next)),
            "exact_prev": exact(xy(mite_prev), xy(target_prev)),
            "exact_now": exact(xy(before), xy(target_now)),
            "exact_next": exact(xy(mite_next), xy(target_next)),
            "mite_now_eq_target_prev": exact(xy(before), xy(target_prev)),
            "mite_next_eq_target_now": exact(xy(mite_next), xy(target_now)),
            "target_damage_delta_prev_now": delta(
                target_now["damage"], None if target_prev is None else target_prev["damage"]
            ),
            "target_damage_delta_now_next": delta(
                None if target_next is None else target_next["damage"], target_now["damage"]
            ),
            "target_crew_delta_prev_now": delta(
                target_now["crew"], None if target_prev is None else target_prev["crew"]
            ),
            "target_crew_delta_now_next": delta(
                None if target_next is None else target_next["crew"], target_now["crew"]
            ),
            "target_mass_delta_prev_now": delta(
                target_now["mass"], None if target_prev is None else target_prev["mass"]
            ),
            "target_mass_delta_now_next": delta(
                None if target_next is None else target_next["mass"], target_now["mass"]
            ),
            "target_cloak_prev": None if target_prev is None else target_prev["cloak"],
            "target_cloak_now": target_now["cloak"],
            "target_cloak_next": None if target_next is None else target_next["cloak"],
            "target_present_next": target_next is not None,
        }
        rows.append(row)


print()
print("===== ACTIVE MITE ROWS BY STATE / OUTCOME / EXACT CONTACT =====")
summary = Counter(
    (row["state"], row["outcome"], row["exact_now"], row["target_cloak_now"])
    for row in rows
)
for key, n in sorted(summary.items(), key=lambda item: str(item[0])):
    print({
        "state": key[0],
        "outcome": key[1],
        "exact_contact_now": key[2],
        "target_cloak_now": key[3],
        "n": n,
    })

print()
print("===== ALL EXACT MITE-TARGET CONTACT ROWS =====")
exact_rows = [row for row in rows if row["exact_now"]]
print("count=", len(exact_rows))
for row in sorted(exact_rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    print({
        "turn": (row["turn"] - 1, row["turn"], row["turn"] + 1),
        "mite": row["mite"],
        "target": row["target"],
        "target_hull": row["target_hull"],
        "target_name": row["target_name"],
        "state": row["state"],
        "outcome": row["outcome"],
        "distance_prev": row["distance_prev"],
        "distance_now": row["distance_now"],
        "distance_next": row["distance_next"],
        "target_damage_delta_prev_now": row["target_damage_delta_prev_now"],
        "target_damage_delta_now_next": row["target_damage_delta_now_next"],
        "target_cloak_prev": row["target_cloak_prev"],
        "target_cloak_now": row["target_cloak_now"],
        "target_cloak_next": row["target_cloak_next"],
        "mite_prev": compact(row["mite_prev"]),
        "mite_now": compact(row["mite_now"]),
        "mite_next": compact(row["mite_next"]),
        "target_prev": compact(row["target_prev"]),
        "target_now": compact(row["target_now"]),
        "target_next": compact(row["target_next"]),
    })

print()
print("===== IMMEDIATE FULL CLEAR AGGREGATES =====")
clear_rows = [row for row in rows if row["outcome"] == "immediate_full_clear"]
print("count=", len(clear_rows))
print("state:", Counter(row["state"] for row in clear_rows))
print("target_cloak_now:", Counter(row["target_cloak_now"] for row in clear_rows))
print("exact_contact_now:", Counter(row["exact_now"] for row in clear_rows))
print("damage_delta_prev_now:", Counter(row["target_damage_delta_prev_now"] for row in clear_rows))
print("damage_delta_now_next:", Counter(row["target_damage_delta_now_next"] for row in clear_rows))

print()
print("===== UNCLOAKED IMMEDIATE FULL CLEAR DETAILS =====")
uncloaked_clears = [
    row for row in clear_rows
    if row["target_cloak_now"] is False
]
print("count=", len(uncloaked_clears))
for row in sorted(uncloaked_clears, key=lambda r: (r["turn"], r["target"], r["mite"])):
    print("-" * 110)
    print({
        "turn": (row["turn"] - 1, row["turn"], row["turn"] + 1),
        "mite": row["mite"],
        "target": row["target"],
        "target_hull": row["target_hull"],
        "target_name": row["target_name"],
        "state": row["state"],
        "matches": row["matches"],
        "distance_prev": row["distance_prev"],
        "distance_now": row["distance_now"],
        "distance_next": row["distance_next"],
        "exact_prev": row["exact_prev"],
        "exact_now": row["exact_now"],
        "exact_next": row["exact_next"],
        "mite_now_eq_target_prev": row["mite_now_eq_target_prev"],
        "mite_next_eq_target_now": row["mite_next_eq_target_now"],
        "target_damage_delta_prev_now": row["target_damage_delta_prev_now"],
        "target_damage_delta_now_next": row["target_damage_delta_now_next"],
        "target_crew_delta_prev_now": row["target_crew_delta_prev_now"],
        "target_crew_delta_now_next": row["target_crew_delta_now_next"],
        "target_mass_delta_prev_now": row["target_mass_delta_prev_now"],
        "target_mass_delta_now_next": row["target_mass_delta_now_next"],
        "target_cloak_prev": row["target_cloak_prev"],
        "target_cloak_now": row["target_cloak_now"],
        "target_cloak_next": row["target_cloak_next"],
    })
    print("  mite_prev  :", compact(row["mite_prev"]))
    print("  mite_now   :", compact(row["mite_now"]))
    print("  mite_next  :", compact(row["mite_next"]))
    print("  target_prev:", compact(row["target_prev"]))
    print("  target_now :", compact(row["target_now"]))
    print("  target_next:", compact(row["target_next"]))

print()
print("===== CURRENT+RETAINED DAMAGE / CONTACT CONTROLS =====")
controls = [
    row for row in rows
    if row["state"] == "current" and row["outcome"] == "retained"
]
print("count=", len(controls))
print("exact_contact_now:", Counter(row["exact_now"] for row in controls))
print("target_cloak_now:", Counter(row["target_cloak_now"] for row in controls))
print("damage_delta_prev_now:", Counter(row["target_damage_delta_prev_now"] for row in controls))
print("damage_delta_now_next:", Counter(row["target_damage_delta_now_next"] for row in controls))

print()
print("===== CLOSEST CURRENT+RETAINED CONTROLS =====")
for row in sorted(
    (r for r in controls if r["distance_now"] is not None),
    key=lambda r: (r["distance_now"], r["turn"], r["mite"]),
)[:25]:
    print({
        "turn": row["turn"],
        "mite": row["mite"],
        "target": row["target"],
        "target_hull": row["target_hull"],
        "target_name": row["target_name"],
        "distance_now": row["distance_now"],
        "target_cloak_now": row["target_cloak_now"],
        "damage_delta_prev_now": row["target_damage_delta_prev_now"],
        "damage_delta_now_next": row["target_damage_delta_now_next"],
        "target_mission": row["target_now"]["mission"],
        "target_m1": row["target_now"]["m1"],
        "target_enemy": row["target_now"]["enemy"],
    })

print()
print("NOTE: mission numeric values are intentionally left unnamed.")
print("period=2170 is an empirical coordinate-period candidate for game 591478 only.")
print("This diagnostic distinguishes observed contact/clear timing from causal interpretation.")
