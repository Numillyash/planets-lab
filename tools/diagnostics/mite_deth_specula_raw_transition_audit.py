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
DETH_SPECULA_HULL_ID = 1033
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
        out[(turn, rid)] = (owner, rec.raw)
    return out


ship_raw = build_records("ship")
planet_raw = build_records("planet")


def normalize_ship(turn, sid):
    item = ship_raw.get((turn, sid))
    if item is None:
        return None
    owner, raw = item
    return {
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
        "warp": _intish(raw.get("warp")),
        "mission": _intish(raw.get("mission")),
        "m1": _intish(raw.get("mission1target")),
        "m2": _intish(raw.get("mission2target")),
        "enemy": _intish(raw.get("enemy")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "crew": _intish(raw.get("crew")),
        "mass": _intish(raw.get("mass")),
        "neutronium": _intish(raw.get("neutronium")),
        "podcargo": _intish(raw.get("podcargo")),
        "ammo": _intish(raw.get("ammo")),
        "clans": _intish(raw.get("clans")),
        "supplies": _intish(raw.get("supplies")),
        "megacredits": _intish(raw.get("megacredits")),
        "friendlycode": raw.get("friendlycode"),
        "turnkilled": _intish(raw.get("turnkilled")),
        "readystatus": _intish(raw.get("readystatus")),
        "infoturn": _intish(raw.get("infoturn")),
        "transfertargetid": _intish(raw.get("transfertargetid")),
        "transfertargettype": _intish(raw.get("transfertargettype")),
    }


ships = {key: normalize_ship(*key) for key in ship_raw}
planets = {}
for (turn, pid), (owner, raw) in planet_raw.items():
    planets[(turn, pid)] = {
        "id": pid,
        "owner": owner,
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
    }


def ship(turn, sid):
    return ships.get((turn, sid))


def raw_ship(turn, sid):
    item = ship_raw.get((turn, sid))
    return None if item is None else item[1]


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
    return (
        mite is not None
        and mite["hull"] == MITE_HULL_ID
        and mite["mission"] == 7
        and mite["m1"] == target_id
    )


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
    if point is None:
        return []
    out = []
    for (t, pid), p in planets.items():
        if t != turn:
            continue
        pxy = (p["x"], p["y"]) if p["x"] is not None and p["y"] is not None else None
        if exact(point, pxy):
            out.append((pid, p["owner"]))
    return sorted(out)


def diff_raw(a, b):
    if a is None or b is None:
        return None
    keys = sorted(set(a) | set(b))
    return {k: (a.get(k), b.get(k)) for k in keys if a.get(k) != b.get(k)}


def compact(s):
    if s is None:
        return None
    return {
        "id": s["id"], "owner": s["owner"], "hull": s["hull"], "name": s["name"],
        "raw_turn": s["raw_turn"], "xy": xy(s), "wp": wp(s), "warp": s["warp"],
        "mission": s["mission"], "m1": s["m1"], "m2": s["m2"], "enemy": s["enemy"],
        "cloak": s["cloak"], "damage": s["damage"], "crew": s["crew"], "mass": s["mass"],
        "neutronium": s["neutronium"], "podcargo": s["podcargo"], "ammo": s["ammo"],
        "clans": s["clans"], "supplies": s["supplies"], "megacredits": s["megacredits"],
        "friendlycode": s["friendlycode"], "turnkilled": s["turnkilled"],
        "readystatus": s["readystatus"], "infoturn": s["infoturn"],
        "transfertargetid": s["transfertargetid"], "transfertargettype": s["transfertargettype"],
    }


print("\n===== DETH SPECULA IDENTITIES =====")
idents = defaultdict(list)
for (turn, sid), s in sorted(ships.items()):
    if s["hull"] == DETH_SPECULA_HULL_ID:
        idents[(sid, s["owner"], s["raw_turn"], s["name"])].append(turn)
print("identity_count=", len(idents))
for key, turns in sorted(idents.items()):
    print({"identity": key, "first": min(turns), "last": max(turns), "turns": turns})

print("\n===== DETH SPECULA TARGETED BY RED MITES =====")
rows = []
for (turn, mite_id), mite in sorted(ships.items()):
    target_id = mite["m1"]
    if target_id is None or target_id <= 0 or not tracking(mite, target_id):
        continue
    target = ship(turn, target_id)
    if target is None or target["hull"] != DETH_SPECULA_HULL_ID:
        continue
    start = tracking_start(turn, mite_id, target_id)
    anchor = ship(start - 1, target_id)
    loss_like_anchor = exact(wp(mite), xy(anchor)) and not exact(xy(target), xy(anchor))
    rows.append({
        "turn": turn,
        "mite": mite_id,
        "target": target_id,
        "tracking_start": start,
        "age": turn - start,
        "target_identity": ident(target),
        "target_xy": xy(target),
        "target_wp": wp(target),
        "target_planets": planets_at(turn, xy(target)),
        "mite_xy": xy(mite),
        "mite_wp": wp(mite),
        "distance": distance(xy(mite), xy(target)),
        "loss_like_anchor": loss_like_anchor,
        "outcome": outcome(turn, mite_id, target_id),
        "cloak": target["cloak"],
        "mission": target["mission"],
        "m1": target["m1"],
        "m2": target["m2"],
        "enemy": target["enemy"],
        "warp": target["warp"],
        "damage": target["damage"],
        "podcargo": target["podcargo"],
        "mass": target["mass"],
        "neutronium": target["neutronium"],
    })
print("row_count=", len(rows))
print("target_ids=", Counter(r["target"] for r in rows))
print("outcome=", Counter(r["outcome"] for r in rows))
print("loss_like_anchor=", Counter(r["loss_like_anchor"] for r in rows))
for r in rows:
    print(r)

print("\n===== FOCUS RAW TARGET 206 =====")
for t in range(63, 69):
    s = ship(t, 206)
    print({"turn": t, "ship": compact(s), "planets": planets_at(t, xy(s)) if s else []})
print("-- RAW DIFF 64->65 --")
print(diff_raw(raw_ship(64, 206), raw_ship(65, 206)))
print("-- RAW DIFF 65->66 --")
print(diff_raw(raw_ship(65, 206), raw_ship(66, 206)))
print("-- RAW DIFF 66->67 --")
print(diff_raw(raw_ship(66, 206), raw_ship(67, 206)))

print("\n===== FOCUS RAW TARGET 469 CONTROL =====")
for t in range(58, 64):
    s = ship(t, 469)
    print({"turn": t, "ship": compact(s), "planets": planets_at(t, xy(s)) if s else []})
for a, b in [(59, 60), (60, 61), (61, 62), (62, 63)]:
    print(f"-- RAW DIFF {a}->{b} --")
    print(diff_raw(raw_ship(a, 469), raw_ship(b, 469)))

# Build a strict visible-uncloaked current-tracking transition population.
control = []
for (turn, mite_id), mite in sorted(ships.items()):
    target_id = mite["m1"]
    if target_id is None or target_id <= 0 or not tracking(mite, target_id):
        continue
    prev_mite = ship(turn - 1, mite_id)
    if not tracking(prev_mite, target_id):
        continue
    target = ship(turn, target_id)
    target_prev = ship(turn - 1, target_id)
    if target is None or target_prev is None or not same_identity(target_prev, target):
        continue
    if target_prev["cloak"] is not False or target["cloak"] is not False:
        continue
    if not exact(wp(prev_mite), xy(target_prev)):
        continue

    start = tracking_start(turn, mite_id, target_id)
    anchor = ship(start - 1, target_id)
    loss_like_anchor = exact(wp(mite), xy(anchor)) and not exact(xy(target), xy(anchor))
    damage_delta = None
    if target_prev["damage"] is not None and target["damage"] is not None:
        damage_delta = target["damage"] - target_prev["damage"]
    pod_delta = None
    if target_prev["podcargo"] is not None and target["podcargo"] is not None:
        pod_delta = target["podcargo"] - target_prev["podcargo"]

    control.append({
        "turn": turn, "mite": mite_id, "target": target_id,
        "target_hull": target["hull"], "target_name": target["name"],
        "outcome": outcome(turn, mite_id, target_id),
        "loss_like_anchor": loss_like_anchor,
        "target_planets": planets_at(turn, xy(target)),
        "mission_transition": (target_prev["mission"], target["mission"]),
        "m1_transition": (target_prev["m1"], target["m1"]),
        "damage_transition": (target_prev["damage"], target["damage"]),
        "podcargo_transition": (target_prev["podcargo"], target["podcargo"]),
        "damage_delta": damage_delta,
        "podcargo_delta": pod_delta,
        "mass_transition": (target_prev["mass"], target["mass"]),
        "neutronium_transition": (target_prev["neutronium"], target["neutronium"]),
        "distance": distance(xy(mite), xy(target)),
    })

positive_pod = [r for r in control if r["podcargo_delta"] is not None and r["podcargo_delta"] > 0]
print("\n===== POSITIVE PODCARGO INFLOW CONTROLS =====")
print("count=", len(positive_pod))
print("delta_x_outcome=", Counter((r["podcargo_delta"], r["outcome"]) for r in positive_pod))
print("hull_x_delta_x_outcome=", Counter((r["target_hull"], r["podcargo_delta"], r["outcome"]) for r in positive_pod))
print("loss_like_anchor=", Counter(r["loss_like_anchor"] for r in positive_pod))
for r in positive_pod:
    print(r)

mission_9_to_1 = [r for r in control if r["mission_transition"] == (9, 1)]
print("\n===== MISSION 9->1 VISIBLE-UNCLOAKED CONTROLS =====")
print("count=", len(mission_9_to_1))
print("outcome=", Counter(r["outcome"] for r in mission_9_to_1))
print("loss_like_anchor=", Counter(r["loss_like_anchor"] for r in mission_9_to_1))
for r in mission_9_to_1:
    print(r)

same_combo = [
    r for r in control
    if r["damage_delta"] == 1 and r["podcargo_delta"] is not None and r["podcargo_delta"] > 0
]
print("\n===== DAMAGE +1 WITH POSITIVE PODCARGO INFLOW =====")
print("count=", len(same_combo))
for r in same_combo:
    print(r)

print("\nNOTE: neutronium is the ship fuel field in raw records; this audit does not use raw.get('fuel').")
print("Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
