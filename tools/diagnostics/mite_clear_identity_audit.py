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
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
    }


def ship(turn, sid):
    return ships.get((turn, sid))


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


def state(turn, target_id, mite):
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


def outcome(after, target_id):
    if after["mission"] == 7 and after["m1"] == target_id:
        return "retained"
    if after["mission"] == 0 and after["m1"] in (None, 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and after["m1"] in (None, 0):
        return "target_clear_pending"
    return "other"


def ident(s):
    if s is None:
        return None
    return (s["owner"], s["hull"], s["name"], s["raw_turn"])


def relation(now, later):
    if later is None:
        return "absent"
    return "same_identity" if ident(now) == ident(later) else "id_reused_or_changed"


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
        target = ship(turn, target_id)
        if target is None:
            continue
        target_next = ship(turn + 1, target_id)
        target_next2 = ship(turn + 2, target_id)
        s, matches = state(turn, target_id, before)
        rows.append({
            "turn": turn,
            "mite": mite_id,
            "target": target_id,
            "state": s,
            "matches": matches,
            "outcome": outcome(after, target_id),
            "cloak": target["cloak"],
            "exact": exact(xy(before), xy(target)),
            "distance": distance(xy(before), xy(target)),
            "next_relation": relation(target, target_next),
            "next2_relation": relation(target, target_next2),
            "target": target_id,
            "target_hull": target["hull"],
            "target_name": target["name"],
            "target_damage": target["damage"],
            "target_podcargo": target["podcargo"],
            "next_damage": None if target_next is None else target_next["damage"],
            "next_podcargo": None if target_next is None else target_next["podcargo"],
        })

clears = [r for r in rows if r["outcome"] == "immediate_full_clear"]
print("\n===== CLEAR ROWS BY STATE / IDENTITY =====")
print("row_count=", len(clears))
print(Counter((r["state"], r["next_relation"], r["cloak"], r["exact"]) for r in clears))

current = [r for r in clears if r["state"] == "current"]
print("\n===== CURRENT -> CLEAR =====")
print("row_count=", len(current))
print("next_relation=", Counter(r["next_relation"] for r in current))
print("next2_relation=", Counter((r["next_relation"], r["next2_relation"]) for r in current))
for r in sorted(current, key=lambda x: (x["turn"], x["target"], x["mite"])):
    print(r)

events = defaultdict(list)
for r in clears:
    events[(r["turn"], r["target"])].append(r)

print("\n===== UNIQUE TARGET-TURN CLEAR EVENTS =====")
print("event_count=", len(events))
summary = Counter()
for rs in events.values():
    summary[(
        rs[0]["next_relation"],
        rs[0]["cloak"],
        tuple(sorted(set(r["state"] for r in rs))),
        any(r["exact"] for r in rs),
    )] += 1
for key, n in sorted(summary.items(), key=lambda x: str(x[0])):
    print({"next_relation": key[0], "cloak": key[1], "states": key[2], "any_exact": key[3], "events": n})

same = [(key, rs) for key, rs in events.items() if rs[0]["next_relation"] == "same_identity"]
print("\n===== SAME-IDENTITY CLEAR EVENTS =====")
print("event_count=", len(same))
print("row_count=", sum(len(rs) for _, rs in same))
print("cloak=", Counter(rs[0]["cloak"] for _, rs in same))
print("states=", Counter(tuple(sorted(set(r["state"] for r in rs))) for _, rs in same))
print("any_exact=", Counter(any(r["exact"] for r in rs) for _, rs in same))

print("\n===== SAME-IDENTITY UNCLOAKED CLEAR EVENTS =====")
clean = [(key, rs) for key, rs in same if rs[0]["cloak"] is False]
print("event_count=", len(clean))
for (turn, target_id), rs in sorted(clean):
    print({
        "turn": (turn - 1, turn, turn + 1),
        "target": target_id,
        "target_hull": rs[0]["target_hull"],
        "target_name": rs[0]["target_name"],
        "mites": sorted(r["mite"] for r in rs),
        "states": sorted(set(r["state"] for r in rs)),
        "distances": {r["mite"]: r["distance"] for r in rs},
        "exact_mites": sorted(r["mite"] for r in rs if r["exact"]),
        "damage_now_next": (rs[0]["target_damage"], rs[0]["next_damage"]),
        "podcargo_now_next": (rs[0]["target_podcargo"], rs[0]["next_podcargo"]),
    })

print("\n===== NON-CONTINUOUS TARGET CLEAR EVENTS =====")
life = [(key, rs) for key, rs in events.items() if rs[0]["next_relation"] != "same_identity"]
print("event_count=", len(life))
print(Counter((rs[0]["next_relation"], rs[0]["next2_relation"]) for _, rs in life))
for (turn, target_id), rs in sorted(life):
    print({
        "turn": turn,
        "target": target_id,
        "mite_count": len(rs),
        "states": sorted(set(r["state"] for r in rs)),
        "next_relation": rs[0]["next_relation"],
        "next2_relation": rs[0]["next2_relation"],
        "cloak": rs[0]["cloak"],
    })

print("\nNOTE: identity continuity requires matching owner, hull, name, and raw ship turn.")
print("Numeric IDs may be reused. Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
