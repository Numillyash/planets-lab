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
EPS = 1e-9

archive = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip").read_bytes()
prepared, hit = load_or_build_prepared_game_cache(
    archive,
    game_id=GAME_ID,
    cache_path=Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle"),
)
print("prepared_cache_hit:", hit)


def axis_delta(a, b):
    return ((b - a + PERIOD / 2) % PERIOD) - PERIOD / 2


def distance(a, b):
    if a is None or b is None:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def exact(a, b):
    d = distance(a, b)
    return d is not None and d <= EPS


def build_records(kind):
    groups = group_perspective_records(tuple(prepared.snapshots), kind)
    out = {}
    for (turn, rid), group in groups.items():
        owner, rec = _owner_record(group)
        if rec is None:
            continue
        raw = rec.raw
        out[(turn, rid)] = (owner, raw)
    return out

ship_raw = build_records("ship")
planet_raw = build_records("planet")

ships = {}
for (turn, sid), (owner, raw) in ship_raw.items():
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
        "warp": _intish(raw.get("warp")),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
        "mass": _intish(raw.get("mass")),
        "fuel": _intish(raw.get("fuel")),
        "cloak": raw.get("iscloaked"),
    }

planets = {}
for (turn, pid), (owner, raw) in planet_raw.items():
    planets[(turn, pid)] = {
        "turn": turn,
        "id": pid,
        "owner": owner,
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
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


def ident(s):
    if s is None:
        return None
    return (s["owner"], s["hull"], s["name"], s["raw_turn"])


def same_identity(a, b):
    return a is not None and b is not None and ident(a) == ident(b)


def tracking(mite, target_id):
    return mite is not None and mite["hull"] == MITE_HULL_ID and mite["mission"] == 7 and mite["m1"] == target_id


def tracking_start(turn, mite_id, target_id):
    t = turn
    while tracking(ship(t - 1, mite_id), target_id):
        t -= 1
    return t


def outcome(turn, mite_id, target_id):
    after = ship(turn + 1, mite_id)
    if after is None:
        return "missing_after"
    if tracking(after, target_id):
        return "retained"
    if after["mission"] == 0 and after["m1"] in (None, 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and after["m1"] in (None, 0):
        return "target_clear_pending"
    return "other"


def planets_at(turn, point):
    out = []
    for (t, pid), p in planets.items():
        if t == turn and exact(point, xy(p)):
            out.append((pid, p["owner"]))
    return sorted(out)

rows = []
for (turn, mite_id), mite in sorted(ships.items()):
    target_id = mite["m1"]
    if not tracking(mite, target_id) or target_id is None or target_id <= 0:
        continue
    prev_mite = ship(turn - 1, mite_id)
    if not tracking(prev_mite, target_id):
        continue

    target = ship(turn, target_id)
    target_prev = ship(turn - 1, target_id)
    target_next = ship(turn + 1, target_id)
    if target is None or target_prev is None:
        continue
    if not same_identity(target_prev, target):
        continue

    # Restrict to snapshots with no visible cloak on either side of the transition.
    if target_prev["cloak"] is not False or target["cloak"] is not False:
        continue

    # Previous snapshot must be an unambiguous current-target waypoint.
    prev_current = exact(wp(prev_mite), xy(target_prev))
    if not prev_current:
        continue

    start = tracking_start(turn, mite_id, target_id)
    anchor = ship(start - 1, target_id)
    anchor_xy = xy(anchor)
    target_xy = xy(target)
    wp_now = wp(mite)
    anchor_hit = exact(wp_now, anchor_xy)
    target_eq_anchor = exact(target_xy, anchor_xy)
    loss_like_anchor = anchor_hit and not target_eq_anchor

    damage_delta = None
    if target_prev["damage"] is not None and target["damage"] is not None:
        damage_delta = target["damage"] - target_prev["damage"]
    podcargo_delta = None
    if target_prev["podcargo"] is not None and target["podcargo"] is not None:
        podcargo_delta = target["podcargo"] - target_prev["podcargo"]

    rows.append({
        "turn": turn,
        "mite": mite_id,
        "target": target_id,
        "target_hull": target["hull"],
        "target_name": target["name"],
        "tracking_start": start,
        "age": turn - start,
        "outcome": outcome(turn, mite_id, target_id),
        "same_target_next": same_identity(target, target_next),
        "anchor_hit": anchor_hit,
        "target_eq_anchor": target_eq_anchor,
        "loss_like_anchor": loss_like_anchor,
        "exact_contact": exact(xy(mite), target_xy),
        "mite_target_distance": distance(xy(mite), target_xy),
        "target_planets": planets_at(turn, target_xy),
        "anchor_planets": planets_at(turn, anchor_xy),
        "mission": (target_prev["mission"], target["mission"], None if target_next is None else target_next["mission"]),
        "m1": (target_prev["m1"], target["m1"], None if target_next is None else target_next["m1"]),
        "enemy": (target_prev["enemy"], target["enemy"], None if target_next is None else target_next["enemy"]),
        "warp": (target_prev["warp"], target["warp"], None if target_next is None else target_next["warp"]),
        "damage": (target_prev["damage"], target["damage"], None if target_next is None else target_next["damage"]),
        "podcargo": (target_prev["podcargo"], target["podcargo"], None if target_next is None else target_next["podcargo"]),
        "mass": (target_prev["mass"], target["mass"], None if target_next is None else target_next["mass"]),
        "fuel": (target_prev["fuel"], target["fuel"], None if target_next is None else target_next["fuel"]),
        "damage_delta": damage_delta,
        "podcargo_delta": podcargo_delta,
        "anchor_xy": anchor_xy,
        "target_prev_xy": xy(target_prev),
        "target_xy": target_xy,
        "mite_xy": xy(mite),
        "prev_wp": wp(prev_mite),
        "wp": wp_now,
    })

print("\n===== UNCLOAKED CURRENT->NEXT CONTROL POPULATION =====")
print("row_count=", len(rows))
print("outcome=", Counter(r["outcome"] for r in rows))
print("loss_like_anchor_x_outcome=", Counter((r["loss_like_anchor"], r["outcome"]) for r in rows))
print("exact_contact_x_outcome=", Counter((r["exact_contact"], r["outcome"]) for r in rows))
print("damage_delta_x_outcome=", Counter((r["damage_delta"], r["outcome"]) for r in rows))
print("podcargo_delta_x_outcome=", Counter((r["podcargo_delta"], r["outcome"]) for r in rows))

loss_rows = [r for r in rows if r["loss_like_anchor"]]
print("\n===== LOSS-LIKE ANCHOR RESET ROWS =====")
print("count=", len(loss_rows))
for r in loss_rows:
    print(r)

contact_rows = [r for r in rows if r["exact_contact"]]
print("\n===== EXACT MITE-TARGET CONTACT CONTROLS =====")
print("count=", len(contact_rows))
for r in contact_rows:
    print(r)

change_rows = [
    r for r in rows
    if (r["damage_delta"] not in (None, 0)) or (r["podcargo_delta"] not in (None, 0))
]
print("\n===== VISIBLE-UNCLOAKED DAMAGE / PODCARGO CHANGE CONTROLS =====")
print("count=", len(change_rows))
print("outcome=", Counter(r["outcome"] for r in change_rows))
print("loss_like_anchor=", Counter(r["loss_like_anchor"] for r in change_rows))
for r in change_rows:
    print(r)

planet_rows = [r for r in rows if r["target_planets"]]
print("\n===== VISIBLE-UNCLOAKED ON-PLANET CONTROLS =====")
print("count=", len(planet_rows))
print("outcome=", Counter(r["outcome"] for r in planet_rows))
print("loss_like_anchor=", Counter(r["loss_like_anchor"] for r in planet_rows))
for r in planet_rows:
    print(r)

print("\n===== FOCUS TARGET 206 LIFECYCLE =====")
for t in range(63, 69):
    target = ship(t, 206)
    if target is None:
        print({"turn": t, "target": None})
        continue
    tracking_mites = []
    for (tt, sid), rec in sorted(ships.items()):
        if tt == t and tracking(rec, 206):
            tracking_mites.append({
                "mite": sid,
                "xy": xy(rec),
                "wp": wp(rec),
                "outcome": outcome(t, sid, 206),
            })
    print({
        "turn": t,
        "target_xy": xy(target),
        "cloak": target["cloak"],
        "mission": target["mission"],
        "m1": target["m1"],
        "enemy": target["enemy"],
        "warp": target["warp"],
        "damage": target["damage"],
        "podcargo": target["podcargo"],
        "mass": target["mass"],
        "fuel": target["fuel"],
        "planets": planets_at(t, xy(target)),
        "tracking_mites": tracking_mites,
    })

print("\nNOTE: loss_like_anchor means wp(t)==target(start-1) while current target(t)!=that anchor.")
print("Rows require target cloak=False at t-1 and t and Mite waypoint=current target at t-1.")
print("Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
