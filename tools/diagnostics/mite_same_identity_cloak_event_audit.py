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
        "enemy": _intish(raw.get("enemy")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
    }


def ship(turn, sid):
    return ships.get((turn, sid))


def ident(s):
    if s is None:
        return None
    return (s["owner"], s["hull"], s["name"], s["raw_turn"])


def same_identity(a, b):
    return a is not None and b is not None and ident(a) == ident(b)


def xy(s):
    return None if s is None else (s["x"], s["y"])


def wp(s):
    return None if s is None else (s["tx"], s["ty"])


def axis_delta(a, b):
    return ((b - a + PERIOD / 2) % PERIOD) - PERIOD / 2


def distance(a, b):
    if a is None or b is None:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def exact(a, b):
    d = distance(a, b)
    return d is not None and d <= EPS


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


def classify_outcome(after, target_id):
    if after["mission"] == 7 and after["m1"] == target_id:
        return "retained"
    if after["mission"] == 0 and after["m1"] in (None, 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and after["m1"] in (None, 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


seqs = defaultdict(list)
for s in ships.values():
    if s["hull"] == MITE_HULL_ID:
        seqs[s["id"]].append(s)
for seq in seqs.values():
    seq.sort(key=lambda s: s["turn"])

rows = []
for mite_id, seq in seqs.items():
    for before, after in zip(seq, seq[1:]):
        if after["turn"] != before["turn"] + 1:
            continue
        if before["mission"] != 7 or before["m1"] is None or before["m1"] <= 0:
            continue

        turn = before["turn"]
        target_id = before["m1"]
        target_prev = ship(turn - 1, target_id)
        target_now = ship(turn, target_id)
        target_next = ship(turn + 1, target_id)
        if target_now is None or not same_identity(target_now, target_next):
            continue

        state, matches = classify_state(turn, target_id, before)
        rows.append({
            "turn": turn,
            "target": target_id,
            "mite": mite_id,
            "state": state,
            "matches": matches,
            "outcome": classify_outcome(after, target_id),
            "distance": distance(xy(before), xy(target_now)),
            "exact": exact(xy(before), xy(target_now)),
            "target_hull": target_now["hull"],
            "target_name": target_now["name"],
            "cloak_prev": None if target_prev is None or not same_identity(target_prev, target_now) else target_prev["cloak"],
            "cloak_now": target_now["cloak"],
            "cloak_next": target_next["cloak"],
            "mission_prev": None if target_prev is None or not same_identity(target_prev, target_now) else target_prev["mission"],
            "m1_prev": None if target_prev is None or not same_identity(target_prev, target_now) else target_prev["m1"],
            "mission_now": target_now["mission"],
            "m1_now": target_now["m1"],
            "damage_prev": None if target_prev is None or not same_identity(target_prev, target_now) else target_prev["damage"],
            "damage_now": target_now["damage"],
            "damage_next": target_next["damage"],
            "podcargo_prev": None if target_prev is None or not same_identity(target_prev, target_now) else target_prev["podcargo"],
            "podcargo_now": target_now["podcargo"],
            "podcargo_next": target_next["podcargo"],
        })


events = defaultdict(list)
for row in rows:
    events[(row["turn"], row["target"])].append(row)


def event_kind(rs):
    outcomes = {r["outcome"] for r in rs}
    if outcomes == {"retained"}:
        return "all_retained"
    if "immediate_full_clear" in outcomes and outcomes <= {"immediate_full_clear"}:
        return "all_immediate_clear"
    if "target_clear_pending" in outcomes and outcomes <= {"target_clear_pending"}:
        return "all_pending"
    return "mixed:" + ",".join(sorted(outcomes))


print("\n===== SAME-IDENTITY ACTIVE TARGET-TURN EVENTS =====")
print("event_count=", len(events))
summary = Counter()
for rs in events.values():
    summary[(
        rs[0]["cloak_now"],
        event_kind(rs),
        tuple(sorted(set(r["state"] for r in rs))),
        any(r["exact"] for r in rs),
    )] += 1
for key, n in sorted(summary.items(), key=lambda x: str(x[0])):
    print({"cloak_now": key[0], "event_kind": key[1], "states": key[2], "any_exact": key[3], "events": n})

print("\n===== CLOAK=TRUE SAME-IDENTITY EVENTS =====")
cloak_events = [(key, rs) for key, rs in events.items() if rs[0]["cloak_now"] is True]
print("event_count=", len(cloak_events))
print("event_kind=", Counter(event_kind(rs) for _, rs in cloak_events))
print("cloak_prev_now_next=", Counter((rs[0]["cloak_prev"], rs[0]["cloak_now"], rs[0]["cloak_next"]) for _, rs in cloak_events))
print("states=", Counter(tuple(sorted(set(r["state"] for r in rs))) for _, rs in cloak_events))

print("\n===== CLOAK=TRUE RETAINED CONTROLS =====")
controls = [(key, rs) for key, rs in cloak_events if event_kind(rs) == "all_retained"]
print("event_count=", len(controls))
for (turn, target_id), rs in sorted(controls):
    print({
        "turn": (turn - 1, turn, turn + 1),
        "target": target_id,
        "target_hull": rs[0]["target_hull"],
        "target_name": rs[0]["target_name"],
        "mites": sorted(r["mite"] for r in rs),
        "states": sorted(set(r["state"] for r in rs)),
        "distances": {r["mite"]: r["distance"] for r in rs},
        "cloak": (rs[0]["cloak_prev"], rs[0]["cloak_now"], rs[0]["cloak_next"]),
        "mission_prev_now": (rs[0]["mission_prev"], rs[0]["mission_now"]),
        "m1_prev_now": (rs[0]["m1_prev"], rs[0]["m1_now"]),
        "damage": (rs[0]["damage_prev"], rs[0]["damage_now"], rs[0]["damage_next"]),
        "podcargo": (rs[0]["podcargo_prev"], rs[0]["podcargo_now"], rs[0]["podcargo_next"]),
    })

print("\n===== CLOAK=TRUE CLEAR EVENTS =====")
clear_cloak = [(key, rs) for key, rs in cloak_events if "immediate_full_clear" in {r["outcome"] for r in rs}]
print("event_count=", len(clear_cloak))
print("cloak_prev_now_next=", Counter((rs[0]["cloak_prev"], rs[0]["cloak_now"], rs[0]["cloak_next"]) for _, rs in clear_cloak))
print("mission_prev_now=", Counter((rs[0]["mission_prev"], rs[0]["mission_now"]) for _, rs in clear_cloak))

print("\n===== UNCLOAKED SAME-IDENTITY CLEAR EVENTS =====")
uncloaked_clear = [
    (key, rs) for key, rs in events.items()
    if rs[0]["cloak_now"] is False and "immediate_full_clear" in {r["outcome"] for r in rs}
]
print("event_count=", len(uncloaked_clear))
for (turn, target_id), rs in sorted(uncloaked_clear):
    print({
        "turn": (turn - 1, turn, turn + 1),
        "target": target_id,
        "target_hull": rs[0]["target_hull"],
        "target_name": rs[0]["target_name"],
        "mites": sorted(r["mite"] for r in rs),
        "states": sorted(set(r["state"] for r in rs)),
        "distances": {r["mite"]: r["distance"] for r in rs},
        "exact_mites": sorted(r["mite"] for r in rs if r["exact"]),
        "cloak": (rs[0]["cloak_prev"], rs[0]["cloak_now"], rs[0]["cloak_next"]),
        "mission_prev_now": (rs[0]["mission_prev"], rs[0]["mission_now"]),
        "m1_prev_now": (rs[0]["m1_prev"], rs[0]["m1_now"]),
        "damage": (rs[0]["damage_prev"], rs[0]["damage_now"], rs[0]["damage_next"]),
        "podcargo": (rs[0]["podcargo_prev"], rs[0]["podcargo_now"], rs[0]["podcargo_next"]),
    })

print("\n===== CURRENT SAME-IDENTITY EVENTS =====")
current_events = [(key, rs) for key, rs in events.items() if "current" in {r["state"] for r in rs}]
print("event_count=", len(current_events))
print("event_kind=", Counter(event_kind(rs) for _, rs in current_events))
print("cloak_now=", Counter(rs[0]["cloak_now"] for _, rs in current_events))

print("\nNOTE: target-turn events are deduplicated across multiple Mites.")
print("Identity continuity requires matching owner, hull, name, and raw ship turn.")
print("Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
