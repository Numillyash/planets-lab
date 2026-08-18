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


def ident(s):
    if s is None:
        return None
    return (s["owner"], s["hull"], s["name"], s["raw_turn"])


def same_identity(a, b):
    return a is not None and b is not None and ident(a) == ident(b)


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


def outcome(after, target_id):
    if after is None:
        return "missing_after"
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
            "mite": mite_id,
            "target": target_id,
            "state": state,
            "matches": matches,
            "outcome": outcome(after, target_id),
            "mite": before,
            "mite_after": after,
            "target_prev": target_prev,
            "target_now": target_now,
            "target_next": target_next,
        })

row_index = {(r["turn"], r["mite"]["id"], r["target"]): r for r in rows}
events = defaultdict(list)
for r in rows:
    events[(r["turn"], r["target"])].append(r)

onsets = []
for (turn, target_id), rs in events.items():
    now = rs[0]["target_now"]
    prev = rs[0]["target_prev"]
    nxt = rs[0]["target_next"]
    if not same_identity(prev, now):
        continue
    if prev["cloak"] is not False or now["cloak"] is not True:
        continue
    event_kind = "mixed"
    outs = {r["outcome"] for r in rs}
    if outs == {"retained"}:
        event_kind = "all_retained"
    elif outs == {"immediate_full_clear"}:
        event_kind = "all_immediate_clear"
    elif outs == {"target_clear_pending"}:
        event_kind = "all_pending"
    onsets.append({
        "turn": turn,
        "target": target_id,
        "target_hull": now["hull"],
        "target_name": now["name"],
        "event_kind": event_kind,
        "states": tuple(sorted(set(r["state"] for r in rs))),
        "target_prev_xy": xy(prev),
        "target_now_xy": xy(now),
        "target_next_xy": xy(nxt),
        "move_prev_now": distance(xy(prev), xy(now)),
        "move_now_next": distance(xy(now), xy(nxt)),
        "cloak": (prev["cloak"], now["cloak"], nxt["cloak"]),
        "mission": (prev["mission"], now["mission"], nxt["mission"]),
        "m1": (prev["m1"], now["m1"], nxt["m1"]),
        "rows": rs,
    })

print("\n===== CLOAK FALSE->TRUE ONSET EVENTS =====")
print("event_count=", len(onsets))
print("event_kind=", Counter(e["event_kind"] for e in onsets))
print("states=", Counter(e["states"] for e in onsets))
print("target_moved_prev_now=", Counter((e["move_prev_now"] or 0) > EPS for e in onsets))
print("target_moved_now_next=", Counter((e["move_now_next"] or 0) > EPS for e in onsets))
print("event_kind_x_move_prev_now=", Counter((e["event_kind"], (e["move_prev_now"] or 0) > EPS) for e in onsets))

print("\n===== ONSET EVENT DETAILS =====")
for e in sorted(onsets, key=lambda x: (x["turn"], x["target"])):
    mite_rows = []
    for r in sorted(e["rows"], key=lambda x: x["mite"]["id"]):
        mid = r["mite"]["id"]
        nxt_row = row_index.get((e["turn"] + 1, mid, e["target"]))
        mite_rows.append({
            "mite": mid,
            "state": r["state"],
            "matches": r["matches"],
            "outcome": r["outcome"],
            "mite_xy": xy(r["mite"]),
            "waypoint": wp(r["mite"]),
            "wp_eq_target_prev": exact(wp(r["mite"]), e["target_prev_xy"]),
            "wp_eq_target_now": exact(wp(r["mite"]), e["target_now_xy"]),
            "next_event_state": None if nxt_row is None else nxt_row["state"],
            "next_event_outcome": None if nxt_row is None else nxt_row["outcome"],
            "next_waypoint": None if nxt_row is None else wp(nxt_row["mite"]),
        })
    print({
        "turn": (e["turn"] - 1, e["turn"], e["turn"] + 1),
        "target": e["target"],
        "target_hull": e["target_hull"],
        "target_name": e["target_name"],
        "event_kind": e["event_kind"],
        "states": e["states"],
        "target_xy": (e["target_prev_xy"], e["target_now_xy"], e["target_next_xy"]),
        "move_prev_now": e["move_prev_now"],
        "move_now_next": e["move_now_next"],
        "cloak": e["cloak"],
        "mission": e["mission"],
        "m1": e["m1"],
        "mites": mite_rows,
    })

print("\n===== FOCUS TARGET 380 LIFECYCLE =====")
for turn in range(91, 98):
    s = ship(turn, 380)
    if s is None:
        print({"turn": turn, "target": None})
        continue
    tracking = []
    for r in rows:
        if r["turn"] == turn and r["target"] == 380:
            tracking.append({
                "mite": r["mite"]["id"],
                "state": r["state"],
                "matches": r["matches"],
                "outcome": r["outcome"],
                "mite_xy": xy(r["mite"]),
                "waypoint": wp(r["mite"]),
            })
    print({
        "turn": turn,
        "target_xy": xy(s),
        "target_waypoint": wp(s),
        "cloak": s["cloak"],
        "mission": s["mission"],
        "m1": s["m1"],
        "damage": s["damage"],
        "podcargo": s["podcargo"],
        "tracking_mites": tracking,
    })

print("\nNOTE: this diagnostic tests cloak-onset timing and motion only.")
print("Mission numbers are intentionally unnamed. period=2170 is scoped to game 591478.")
