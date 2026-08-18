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
MAX_LAG = 8
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


def ident(s):
    if s is None:
        return None
    return (s["owner"], s["hull"], s["name"], s["raw_turn"])


def same_identity(a, b):
    return a is not None and b is not None and ident(a) == ident(b)


def tracking(mite, target_id):
    return mite is not None and mite["mission"] == 7 and mite["m1"] == target_id


def tracking_start(turn, mite_id, target_id):
    t = turn
    while tracking(ship(t - 1, mite_id), target_id):
        t -= 1
    return t


def matches(turn, target_id, point):
    out = []
    for lag in range(MAX_LAG + 1):
        target = ship(turn - lag, target_id)
        if exact(point, xy(target)):
            out.append(lag)
    return out


def state(turn, target_id, mite):
    mm = matches(turn, target_id, wp(mite))
    if 0 in mm:
        return "current", mm
    if mm:
        return f"strict_stale_{min(mm)}", mm
    return f"no_match_0_{MAX_LAG}", mm


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

rows = []
for (turn, mite_id), mite in sorted(ships.items()):
    if mite["hull"] != MITE_HULL_ID:
        continue
    target_id = mite["m1"]
    if target_id is None or target_id <= 0 or not tracking(mite, target_id):
        continue
    target = ship(turn, target_id)
    if target is None:
        continue
    start = tracking_start(turn, mite_id, target_id)
    anchor = ship(start - 1, target_id)
    target_prev = ship(turn - 1, target_id)
    target_next = ship(turn + 1, target_id)
    st, mm = state(turn, target_id, mite)
    rows.append({
        "turn": turn,
        "mite": mite_id,
        "target": target_id,
        "tracking_start": start,
        "age": turn - start,
        "state": st,
        "matches": mm,
        "outcome": outcome(turn, mite_id, target_id),
        "waypoint": wp(mite),
        "mite_xy": xy(mite),
        "target_xy": xy(target),
        "anchor_turn": start - 1,
        "anchor_xy": xy(anchor),
        "anchor_same_identity": same_identity(target, anchor),
        "wp_eq_anchor": exact(wp(mite), xy(anchor)),
        "target_eq_anchor": exact(xy(target), xy(anchor)),
        "wp_eq_target": exact(wp(mite), xy(target)),
        "wp_eq_mite": exact(wp(mite), xy(mite)),
        "mite_eq_target": exact(xy(mite), xy(target)),
        "cloak_prev": None if target_prev is None else target_prev["cloak"],
        "cloak_now": target["cloak"],
        "cloak_next": None if target_next is None else target_next["cloak"],
        "same_identity_next": same_identity(target, target_next),
        "damage_now": target["damage"],
        "damage_next": None if target_next is None else target_next["damage"],
        "podcargo_now": target["podcargo"],
        "podcargo_next": None if target_next is None else target_next["podcargo"],
    })

runs = defaultdict(list)
for r in rows:
    runs[(r["mite"], r["target"], r["tracking_start"])].append(r)
for rr in runs.values():
    rr.sort(key=lambda r: r["turn"])

# An informative anchor exposure is a transition from a previous tracking row whose
# waypoint was not the pre-run anchor to a row whose waypoint is exactly that anchor.
anchor_exposures = []
for key, rr in runs.items():
    for prev, cur in zip(rr, rr[1:]):
        if cur["turn"] != prev["turn"] + 1:
            continue
        if cur["wp_eq_anchor"] and not prev["wp_eq_anchor"]:
            anchor_exposures.append((key, prev, cur))

print("\n===== INFORMATIVE NON-ANCHOR -> ANCHOR TRANSITIONS =====")
print("count=", len(anchor_exposures))
print("cloak_x_state_x_outcome=", Counter(
    (cur["cloak_now"], cur["state"], cur["outcome"])
    for _, _, cur in anchor_exposures
))
print("target_eq_anchor_x_outcome=", Counter(
    (cur["target_eq_anchor"], cur["outcome"])
    for _, _, cur in anchor_exposures
))
print("exact_contact_x_outcome=", Counter(
    (cur["mite_eq_target"], cur["outcome"])
    for _, _, cur in anchor_exposures
))

print("\n===== ANCHOR TRANSITION DETAILS =====")
for _, prev, cur in anchor_exposures:
    if cur["outcome"] != "retained" or cur["target_eq_anchor"] or cur["target"] in {206, 329, 380}:
        print({
            "turn": (prev["turn"], cur["turn"], cur["turn"] + 1),
            "mite": cur["mite"],
            "target": cur["target"],
            "tracking_start": cur["tracking_start"],
            "age": cur["age"],
            "prev_state": prev["state"],
            "state": cur["state"],
            "outcome": cur["outcome"],
            "cloak": (cur["cloak_prev"], cur["cloak_now"], cur["cloak_next"]),
            "anchor": cur["anchor_xy"],
            "target_xy": cur["target_xy"],
            "target_eq_anchor": cur["target_eq_anchor"],
            "mite_eq_target": cur["mite_eq_target"],
            "wp_eq_mite": cur["wp_eq_mite"],
            "damage": (cur["damage_now"], cur["damage_next"]),
            "podcargo": (cur["podcargo_now"], cur["podcargo_next"]),
        })

# For every run that has an immediate full clear while the target identity continues,
# check whether an anchor exposure occurred on the clear row or earlier in that run.
loss_runs = []
for key, rr in runs.items():
    clear = next((r for r in rr if r["outcome"] == "immediate_full_clear" and r["same_identity_next"]), None)
    if clear is None:
        continue
    exposures = [
        cur for exp_key, prev, cur in anchor_exposures
        if exp_key == key and cur["turn"] <= clear["turn"]
    ]
    first_noncurrent = next((r for r in rr if r["state"] != "current"), None)
    loss_runs.append({
        "key": key,
        "clear": clear,
        "exposures": exposures,
        "first_noncurrent": first_noncurrent,
    })

print("\n===== SAME-IDENTITY IMMEDIATE-CLEAR RUN COVERAGE =====")
print("run_count=", len(loss_runs))
print("has_anchor_exposure=", Counter(bool(x["exposures"]) for x in loss_runs))
print("clear_minus_first_exposure=", Counter(
    None if not x["exposures"] else x["clear"]["turn"] - x["exposures"][0]["turn"]
    for x in loss_runs
))
print("clear_cloak=", Counter(x["clear"]["cloak_now"] for x in loss_runs))

print("\n===== LOSS RUNS WITHOUT INFORMATIVE ANCHOR TRANSITION =====")
missing = [x for x in loss_runs if not x["exposures"]]
print("count=", len(missing))
for x in missing:
    clear = x["clear"]
    print({
        "mite": clear["mite"],
        "target": clear["target"],
        "tracking_start": clear["tracking_start"],
        "clear_turn": clear["turn"],
        "state": clear["state"],
        "cloak": clear["cloak_now"],
        "wp_eq_anchor": clear["wp_eq_anchor"],
        "target_eq_anchor": clear["target_eq_anchor"],
        "wp_eq_mite": clear["wp_eq_mite"],
        "anchor": clear["anchor_xy"],
        "target_xy": clear["target_xy"],
    })

print("\n===== FOCUS 206 / 329 / 380 =====")
for r in rows:
    if r["target"] in {206, 329, 380}:
        print({k: r[k] for k in (
            "turn", "mite", "target", "tracking_start", "age", "state", "outcome",
            "wp_eq_anchor", "target_eq_anchor", "wp_eq_target", "wp_eq_mite",
            "mite_eq_target", "cloak_prev", "cloak_now", "cloak_next",
            "waypoint", "anchor_xy", "target_xy"
        )})

print("\nNOTE: anchor exposure is observational: waypoint equals target position at tracking_start-1.")
print("When target_xy also equals anchor_xy, coordinates alone cannot prove which internal source supplied the waypoint.")
print("Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
