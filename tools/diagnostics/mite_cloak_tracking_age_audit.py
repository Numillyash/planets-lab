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

archive = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip").read_bytes()
prepared, hit = load_or_build_prepared_game_cache(
    archive,
    game_id=GAME_ID,
    cache_path=Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle"),
)
print("prepared_cache_hit:", hit)

groups = group_perspective_records(tuple(prepared.snapshots), "ship")
ships = {}
for (turn, sid), group in groups.items():
    owner, rec = _owner_record(group)
    if rec is None:
        continue
    raw = rec.raw
    ships[(turn, sid)] = {
        "turn": turn,
        "id": sid,
        "owner": owner,
        "hull": _intish(raw.get("hullid")),
        "name": raw.get("name"),
        "raw_turn": _intish(raw.get("turn")),
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
        "tx": _intish(raw.get("targetx")),
        "ty": _intish(raw.get("targety")),
        "mission": _intish(raw.get("mission")),
        "m1": _intish(raw.get("mission1target")),
        "cloak": raw.get("iscloaked"),
    }


def ship(turn, sid):
    return ships.get((turn, sid))


def xy(s):
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def wp(s):
    if s is None or s["tx"] is None or s["ty"] is None:
        return None
    return (s["tx"], s["ty"])


def axis_delta(a, b):
    return ((b - a + PERIOD / 2) % PERIOD) - PERIOD / 2


def distance(a, b):
    if a is None or b is None:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def exact(a, b):
    d = distance(a, b)
    return d is not None and d <= 1e-9


def ident(s):
    if s is None:
        return None
    return (s["owner"], s["hull"], s["name"], s["raw_turn"])


def same_identity(a, b):
    return a is not None and b is not None and ident(a) == ident(b)


def classify_state(turn, target_id, mite):
    matches = []
    for lag in range(MAX_LAG + 1):
        target = ship(turn - lag, target_id)
        if exact(wp(mite), xy(target)):
            matches.append(lag)
    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", matches


def outcome(turn, mite_id, target_id):
    after = ship(turn + 1, mite_id)
    if after is None:
        return "missing_after"
    if after["mission"] == 7 and after["m1"] == target_id:
        return "retained"
    if after["mission"] == 0 and after["m1"] in (None, 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and after["m1"] in (None, 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


def tracks(mite, target_id):
    return (
        mite is not None
        and mite["hull"] == MITE_HULL_ID
        and mite["mission"] == 7
        and mite["m1"] == target_id
    )


def continuous_tracking_start(turn, mite_id, target_id):
    start = turn
    while tracks(ship(start - 1, mite_id), target_id):
        start -= 1
    return start


def mite_history(turn, mite_id, target_id, radius=4):
    out = []
    for tt in range(turn - radius, turn + 2):
        mite = ship(tt, mite_id)
        if not tracks(mite, target_id):
            out.append({"turn": tt, "tracking": False})
            continue
        state, matches = classify_state(tt, target_id, mite)
        out.append({
            "turn": tt,
            "tracking": True,
            "state": state,
            "matches": matches,
            "mite_xy": xy(mite),
            "waypoint": wp(mite),
            "target_xy": xy(ship(tt, target_id)),
            "outcome": outcome(tt, mite_id, target_id),
        })
    return out


def target_history(turn, target_id, radius=4):
    out = []
    base = ship(turn, target_id)
    for tt in range(turn - radius, turn + 2):
        target = ship(tt, target_id)
        out.append({
            "turn": tt,
            "same_identity": same_identity(base, target),
            "xy": xy(target),
            "cloak": None if target is None else target["cloak"],
            "mission": None if target is None else target["mission"],
            "m1": None if target is None else target["m1"],
        })
    return out

# Build false->true cloak onset events with same target identity across t-1/t.
onsets = defaultdict(list)
for (turn, mite_id), mite in ships.items():
    if mite["hull"] != MITE_HULL_ID or mite["mission"] != 7 or not mite["m1"] or mite["m1"] <= 0:
        continue
    target_id = mite["m1"]
    prev = ship(turn - 1, target_id)
    now = ship(turn, target_id)
    if now is None or prev is None or not same_identity(prev, now):
        continue
    if prev["cloak"] is not False or now["cloak"] is not True:
        continue
    state, matches = classify_state(turn, target_id, mite)
    start = continuous_tracking_start(turn, mite_id, target_id)
    onsets[(turn, target_id)].append({
        "mite": mite_id,
        "state": state,
        "matches": matches,
        "outcome": outcome(turn, mite_id, target_id),
        "tracking_start": start,
        "tracking_age": turn - start,
        "tracked_prev": tracks(ship(turn - 1, mite_id), target_id),
        "state_prev": classify_state(turn - 1, target_id, ship(turn - 1, mite_id))[0]
        if tracks(ship(turn - 1, mite_id), target_id) else None,
        "outcome_prev": outcome(turn - 1, mite_id, target_id)
        if tracks(ship(turn - 1, mite_id), target_id) else None,
    })


def event_kind(rows):
    outs = {r["outcome"] for r in rows}
    if outs == {"retained"}:
        return "all_retained"
    if outs == {"immediate_full_clear"}:
        return "all_immediate_clear"
    return "+".join(sorted(outs))

print("\n===== CLOAK ONSET: TRACKING AGE SUMMARY =====")
print("event_count=", len(onsets))
summary = Counter()
for rows in onsets.values():
    summary[(
        event_kind(rows),
        tuple(sorted(set(r["state"] for r in rows))),
        tuple(sorted(r["tracking_age"] for r in rows)),
        tuple(sorted(set(r["state_prev"] for r in rows))),
    )] += 1
for key, n in sorted(summary.items(), key=lambda kv: str(kv[0])):
    print({
        "event_kind": key[0],
        "states_now": key[1],
        "tracking_ages": key[2],
        "states_prev": key[3],
        "events": n,
    })

print("\n===== CLOAK ONSET: AGE DISTRIBUTION =====")
print("row_count=", sum(len(rows) for rows in onsets.values()))
print("kind_x_age=", Counter((event_kind(rows), r["tracking_age"]) for rows in onsets.values() for r in rows))
print("kind_x_tracked_prev=", Counter((event_kind(rows), r["tracked_prev"]) for rows in onsets.values() for r in rows))
print("kind_x_state_prev=", Counter((event_kind(rows), r["state_prev"]) for rows in onsets.values() for r in rows))

print("\n===== FRESH / SHORT-AGE ONSET DETAILS =====")
for (turn, target_id), rows in sorted(onsets.items()):
    if min(r["tracking_age"] for r in rows) <= 1 or event_kind(rows) != "all_immediate_clear":
        target = ship(turn, target_id)
        print({
            "turn": (turn - 1, turn, turn + 1),
            "target": target_id,
            "target_hull": target["hull"],
            "target_name": target["name"],
            "kind": event_kind(rows),
            "target_history": target_history(turn, target_id),
            "mites": rows,
        })
        for r in rows:
            print("  mite_history", r["mite"], mite_history(turn, r["mite"], target_id))

print("\n===== FOCUS TARGET 380 =====")
for turn in range(91, 98):
    target = ship(turn, 380)
    if target is None:
        continue
    tracking = []
    for (tt, mite_id), mite in ships.items():
        if tt != turn or not tracks(mite, 380):
            continue
        state, matches = classify_state(turn, 380, mite)
        tracking.append({
            "mite": mite_id,
            "state": state,
            "matches": matches,
            "outcome": outcome(turn, mite_id, 380),
            "tracking_start": continuous_tracking_start(turn, mite_id, 380),
            "tracking_age": turn - continuous_tracking_start(turn, mite_id, 380),
            "waypoint": wp(mite),
        })
    print({
        "turn": turn,
        "target_xy": xy(target),
        "cloak": target["cloak"],
        "mission": target["mission"],
        "m1": target["m1"],
        "tracking_mites": sorted(tracking, key=lambda r: r["mite"]),
    })

print("\nNOTE: tracking_age is the number of consecutive prior snapshots in the same mission=7/m1=target run.")
print("This diagnostic does not assign semantics to mission numbers. period=2170 is scoped to game 591478.")
