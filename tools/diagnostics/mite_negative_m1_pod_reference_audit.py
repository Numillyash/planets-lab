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
        "enemy": _intish(raw.get("enemy")),
        "mass": _intish(raw.get("mass")),
        "fuel": _intish(raw.get("neutronium")),
        "clans": _intish(raw.get("clans")),
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


def classify_mite_state(turn: int, target_id: int, mite_state):
    point = waypoint(mite_state)
    if point is None:
        return "missing_waypoint", []
    matches = target_matches(turn, target_id, point)
    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", matches


def mite_outcome(after, target_id: int):
    if after is None:
        return "missing_after"
    if after["mission"] == 7 and after["m1"] == target_id:
        return "retained"
    if after["mission"] == 0 and (after["m1"] is None or after["m1"] == 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and (after["m1"] is None or after["m1"] == 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


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
        "podcargo": s["podcargo"],
        "mass": s["mass"],
        "fuel": s["fuel"],
        "clans": s["clans"],
        "raw_turn": s["raw_turn"],
    }


mites_by_turn_target: dict[tuple[int, int], list[dict]] = defaultdict(list)
for (turn, _ship_id), state in ships.items():
    if (
        state["hull"] == MITE_HULL_ID
        and state["mission"] == 7
        and state["m1"] is not None
        and state["m1"] > 0
    ):
        mites_by_turn_target[(turn, state["m1"])].append(state)


rows = []
for (turn, actor_id), actor in sorted(ships.items()):
    if not (
        actor["mission"] == 7
        and actor["m1"] is not None
        and actor["m1"] < 0
    ):
        continue

    ref_id = abs(actor["m1"])
    ref_now = ship(turn, ref_id)
    actor_next = ship(turn + 1, actor_id)
    ref_next = ship(turn + 1, ref_id)
    ref_next2 = ship(turn + 2, ref_id)

    if ref_now is None:
        continue

    actor_wp = waypoint(actor)
    actor_next_xy = xy(actor_next)
    ref_now_xy = xy(ref_now)
    ref_next_xy = xy(ref_next)

    mite_rows = []
    for mite_now in sorted(
        mites_by_turn_target.get((turn, actor_id), []),
        key=lambda s: s["id"],
    ):
        mite_after = ship(turn + 1, mite_now["id"])
        state, matches = classify_mite_state(turn, actor_id, mite_now)
        mite_rows.append({
            "mite": mite_now["id"],
            "state": state,
            "matches": matches,
            "outcome": mite_outcome(mite_after, actor_id),
            "mite_xy": xy(mite_now),
            "mite_waypoint": waypoint(mite_now),
            "mite_actor_distance": distance(xy(mite_now), xy(actor)),
            "mite_eq_actor": exact(xy(mite_now), xy(actor)),
            "mite_eq_ref_now": exact(xy(mite_now), ref_now_xy),
            "mite_after": compact(mite_after),
        })

    row = {
        "turn": turn,
        "actor": actor_id,
        "actor_hull": actor["hull"],
        "actor_name": actor["name"],
        "ref": ref_id,
        "ref_hull": ref_now["hull"],
        "ref_name": ref_now["name"],
        "actor": compact(actor),
        "actor_next": compact(actor_next),
        "ref_now": compact(ref_now),
        "ref_next": compact(ref_next),
        "ref_next2": compact(ref_next2),
        "actor_wp_eq_ref_now": exact(actor_wp, ref_now_xy),
        "actor_next_eq_ref_now": exact(actor_next_xy, ref_now_xy),
        "actor_next_eq_ref_next": exact(actor_next_xy, ref_next_xy),
        "actor_ref_distance_now": distance(xy(actor), ref_now_xy),
        "actor_next_ref_next_distance": distance(actor_next_xy, ref_next_xy),
        "ref_move_distance": distance(ref_now_xy, ref_next_xy),
        "ref_present_next": ref_next is not None,
        "ref_present_next2": ref_next2 is not None,
        "ref_same_identity_next": (
            ref_next is not None
            and ref_next["owner"] == ref_now["owner"]
            and ref_next["hull"] == ref_now["hull"]
            and ref_next["raw_turn"] == ref_now["raw_turn"]
        ),
        "ref_same_identity_next2": (
            ref_next2 is not None
            and ref_next2["owner"] == ref_now["owner"]
            and ref_next2["hull"] == ref_now["hull"]
            and ref_next2["raw_turn"] == ref_now["raw_turn"]
        ),
        "mites_tracking_actor": mite_rows,
    }
    rows.append(row)


print()
print("===== ALL MISSION=7 NEGATIVE-M1 REFERENCE ROWS =====")
print("count=", len(rows))
print(Counter((r["actor_hull"], r["ref_hull"]) for r in rows))
for row in rows:
    print()
    print("-" * 110)
    print({
        "turn": row["turn"],
        "actor_id": row["actor"]["id"],
        "actor_hull": row["actor_hull"],
        "actor_name": row["actor_name"],
        "ref_id": row["ref"],
        "ref_hull": row["ref_hull"],
        "ref_name": row["ref_name"],
        "actor_wp_eq_ref_now": row["actor_wp_eq_ref_now"],
        "actor_next_eq_ref_now": row["actor_next_eq_ref_now"],
        "actor_next_eq_ref_next": row["actor_next_eq_ref_next"],
        "actor_ref_distance_now": row["actor_ref_distance_now"],
        "actor_next_ref_next_distance": row["actor_next_ref_next_distance"],
        "ref_move_distance": row["ref_move_distance"],
        "ref_present_next": row["ref_present_next"],
        "ref_present_next2": row["ref_present_next2"],
        "ref_same_identity_next": row["ref_same_identity_next"],
        "ref_same_identity_next2": row["ref_same_identity_next2"],
        "active_mites_tracking_actor": len(row["mites_tracking_actor"]),
    })
    print("  actor_now :", row["actor"])
    print("  actor_next:", row["actor_next"])
    print("  ref_now   :", row["ref_now"])
    print("  ref_next  :", row["ref_next"])
    print("  ref_next2 :", row["ref_next2"])
    if row["mites_tracking_actor"]:
        print("  mites tracking actor:")
        for mite in row["mites_tracking_actor"]:
            print("   ", mite)


print()
print("===== NEGATIVE-M1 ROWS WITH ACTIVE RED MITE TRACKING THE ACTOR =====")
with_mites = [r for r in rows if r["mites_tracking_actor"]]
print("count=", len(with_mites))
summary = Counter()
for row in with_mites:
    for mite in row["mites_tracking_actor"]:
        summary[(
            row["actor_hull"],
            row["ref_hull"],
            mite["state"],
            mite["outcome"],
            mite["mite_eq_actor"],
            mite["mite_eq_ref_now"],
        )] += 1
for key, n in sorted(summary.items(), key=lambda item: str(item[0])):
    print({
        "actor_hull": key[0],
        "ref_hull": key[1],
        "mite_state": key[2],
        "mite_outcome": key[3],
        "mite_eq_actor": key[4],
        "mite_eq_ref_now": key[5],
        "n": n,
    })


print()
print("===== FOCUS ACTORS 329 AND 446 =====")
for row in rows:
    if row["actor"]["id"] not in {329, 446}:
        continue
    print({
        "turn": row["turn"],
        "actor": row["actor"],
        "actor_next": row["actor_next"],
        "ref_now": row["ref_now"],
        "ref_next": row["ref_next"],
        "ref_next2": row["ref_next2"],
        "actor_wp_eq_ref_now": row["actor_wp_eq_ref_now"],
        "actor_next_eq_ref_now": row["actor_next_eq_ref_now"],
        "actor_next_eq_ref_next": row["actor_next_eq_ref_next"],
        "actor_ref_distance_now": row["actor_ref_distance_now"],
        "actor_next_ref_next_distance": row["actor_next_ref_next_distance"],
        "ref_move_distance": row["ref_move_distance"],
        "mites_tracking_actor": row["mites_tracking_actor"],
    })


print()
print("NOTE: mission numeric values are left unnamed. period=2170 is an empirical candidate for game 591478 only.")
print("This diagnostic tests observed reference/movement/lifecycle relations; it does not infer mission semantics or causality.")
