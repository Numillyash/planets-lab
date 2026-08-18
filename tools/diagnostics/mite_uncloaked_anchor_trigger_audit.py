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

ship_groups = group_perspective_records(tuple(prepared.snapshots), "ship")
ships = {}
for (turn, sid), group in ship_groups.items():
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
        "warp": _intish(raw.get("warp")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
        "mass": _intish(raw.get("mass")),
        "fuel": _intish(raw.get("neutronium")),
    }

planet_groups = group_perspective_records(tuple(prepared.snapshots), "planet")
planets = {}
for (turn, pid), group in planet_groups.items():
    owner, rec = _owner_record(group)
    if rec is None:
        continue
    raw = rec.raw
    planets[(turn, pid)] = {
        "turn": turn,
        "id": pid,
        "owner": owner,
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
    }


def ship(turn, sid):
    return ships.get((turn, sid))


def xy(rec):
    if rec is None or rec["x"] is None or rec["y"] is None:
        return None
    return (rec["x"], rec["y"])


def wp(rec):
    if rec is None or rec["tx"] is None or rec["ty"] is None:
        return None
    return (rec["tx"], rec["ty"])


def axis_delta(a, b):
    return ((b - a + PERIOD / 2) % PERIOD) - PERIOD / 2


def distance(a, b):
    if a is None or b is None:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def exact(a, b):
    d = distance(a, b)
    return d is not None and d <= EPS


def ident(rec):
    if rec is None:
        return None
    return (rec["owner"], rec["hull"], rec["name"], rec["raw_turn"])


def same_identity(a, b):
    return a is not None and b is not None and ident(a) == ident(b)


def tracking(rec, target_id):
    return rec is not None and rec["mission"] == 7 and rec["m1"] == target_id


def exact_planets(turn, point):
    if point is None:
        return []
    out = []
    for (t, pid), p in planets.items():
        if t == turn and exact(point, xy(p)):
            out.append((pid, p["owner"]))
    return sorted(out)


def ships_at(turn, point, exclude=None):
    if point is None:
        return []
    out = []
    for (t, sid), s in ships.items():
        if t != turn or sid == exclude:
            continue
        if exact(point, xy(s)):
            out.append((sid, s["owner"], s["hull"], s["name"]))
    return sorted(out)

# Build continuous mission=7/m1=target runs.
rows_by_key = defaultdict(list)
for (turn, sid), rec in sorted(ships.items()):
    if rec["hull"] != MITE_HULL_ID:
        continue
    target_id = rec["m1"]
    if rec["mission"] != 7 or target_id is None or target_id <= 0:
        continue
    rows_by_key[(sid, target_id)].append(turn)

transitions = []
for (mite_id, target_id), turns in rows_by_key.items():
    turns = sorted(turns)
    chunks = []
    cur = [turns[0]]
    for t in turns[1:]:
        if t == cur[-1] + 1:
            cur.append(t)
        else:
            chunks.append(cur)
            cur = [t]
    chunks.append(cur)

    for rr in chunks:
        start = rr[0]
        anchor_target = ship(start - 1, target_id)
        anchor_xy = xy(anchor_target)
        prev_eq_anchor = None
        for t in rr:
            mite = ship(t, mite_id)
            target = ship(t, target_id)
            if mite is None or target is None:
                prev_eq_anchor = None
                continue
            eq_anchor = exact(wp(mite), anchor_xy)
            if prev_eq_anchor is False and eq_anchor:
                after_mite = ship(t + 1, mite_id)
                target_next = ship(t + 1, target_id)
                if after_mite is None:
                    outcome = "missing_after"
                elif tracking(after_mite, target_id):
                    outcome = "retained"
                elif after_mite["mission"] == 0 and after_mite["m1"] in (None, 0):
                    outcome = "immediate_full_clear"
                elif after_mite["mission"] == 7 and after_mite["m1"] in (None, 0):
                    outcome = "target_clear_pending"
                else:
                    outcome = "other"

                prev_target = ship(t - 1, target_id)
                next_target = ship(t + 1, target_id)
                prev_mite = ship(t - 1, mite_id)
                transitions.append({
                    "turn": t,
                    "mite": mite_id,
                    "target": target_id,
                    "target_hull": target["hull"],
                    "target_name": target["name"],
                    "tracking_start": start,
                    "age": t - start,
                    "outcome": outcome,
                    "same_target_identity_next": same_identity(target, target_next),
                    "anchor_xy": anchor_xy,
                    "target_xy": xy(target),
                    "target_eq_anchor": exact(xy(target), anchor_xy),
                    "mite_xy": xy(mite),
                    "mite_eq_target": exact(xy(mite), xy(target)),
                    "wp_eq_mite": exact(wp(mite), xy(mite)),
                    "mite_target_distance": distance(xy(mite), xy(target)),
                    "cloak": (
                        None if prev_target is None else prev_target["cloak"],
                        target["cloak"],
                        None if next_target is None else next_target["cloak"],
                    ),
                    "mission": (
                        None if prev_target is None else prev_target["mission"],
                        target["mission"],
                        None if next_target is None else next_target["mission"],
                    ),
                    "m1": (
                        None if prev_target is None else prev_target["m1"],
                        target["m1"],
                        None if next_target is None else next_target["m1"],
                    ),
                    "enemy": (
                        None if prev_target is None else prev_target["enemy"],
                        target["enemy"],
                        None if next_target is None else next_target["enemy"],
                    ),
                    "warp": (
                        None if prev_target is None else prev_target["warp"],
                        target["warp"],
                        None if next_target is None else next_target["warp"],
                    ),
                    "damage": (
                        None if prev_target is None else prev_target["damage"],
                        target["damage"],
                        None if next_target is None else next_target["damage"],
                    ),
                    "podcargo": (
                        None if prev_target is None else prev_target["podcargo"],
                        target["podcargo"],
                        None if next_target is None else next_target["podcargo"],
                    ),
                    "mass": (
                        None if prev_target is None else prev_target["mass"],
                        target["mass"],
                        None if next_target is None else next_target["mass"],
                    ),
                    "fuel": (
                        None if prev_target is None else prev_target["fuel"],
                        target["fuel"],
                        None if next_target is None else next_target["fuel"],
                    ),
                    "target_xy_history": (
                        xy(ship(t - 2, target_id)),
                        xy(prev_target),
                        xy(target),
                        xy(next_target),
                    ),
                    "mite_wp_history": (
                        wp(ship(t - 2, mite_id)),
                        wp(prev_mite),
                        wp(mite),
                        wp(ship(t + 1, mite_id)),
                    ),
                    "target_planets": exact_planets(t, xy(target)),
                    "anchor_planets": exact_planets(t, anchor_xy),
                    "coincident_ships": ships_at(t, xy(target), exclude=target_id),
                })
            prev_eq_anchor = eq_anchor

uncloaked = [r for r in transitions if r["cloak"][1] is False]
print("\n===== UNCLOAKED INFORMATIVE ANCHOR TRANSITIONS =====")
print("count=", len(uncloaked))
print("outcome=", Counter(r["outcome"] for r in uncloaked))
print("target_eq_anchor_x_outcome=", Counter((r["target_eq_anchor"], r["outcome"]) for r in uncloaked))
print("exact_contact_x_outcome=", Counter((r["mite_eq_target"], r["outcome"]) for r in uncloaked))
print("target_hull_name=", Counter((r["target_hull"], r["target_name"]) for r in uncloaked))

print("\n===== UNCLOAKED TRANSITION DETAILS =====")
for r in uncloaked:
    print(r)

print("\n===== FOCUS 206 / 329 / 202 / 216 =====")
for r in transitions:
    if r["target"] in {206, 329, 202, 216}:
        print(r)

print("\nNOTE: this diagnostic compares only informative non-anchor -> anchor transitions.")
print("Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
