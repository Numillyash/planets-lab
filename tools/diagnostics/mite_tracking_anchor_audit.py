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
MAX_LAG = 6
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
    if mite["hull"] != MITE_HULL_ID or not tracking(mite, mite["m1"]):
        continue
    target_id = mite["m1"]
    if target_id is None or target_id <= 0:
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
        "tracking_age": turn - start,
        "state": st,
        "matches": mm,
        "outcome": outcome(turn, mite_id, target_id),
        "cloak_prev": None if target_prev is None else target_prev["cloak"],
        "cloak_now": target["cloak"],
        "cloak_next": None if target_next is None else target_next["cloak"],
        "same_identity_next": same_identity(target, target_next),
        "waypoint": wp(mite),
        "target_xy": xy(target),
        "anchor_turn": start - 1,
        "anchor_xy": xy(anchor),
        "anchor_same_identity": same_identity(target, anchor),
        "wp_eq_anchor": exact(wp(mite), xy(anchor)),
        "wp_anchor_distance": distance(wp(mite), xy(anchor)),
    })

onset_rows = [
    r for r in rows
    if r["cloak_prev"] is False and r["cloak_now"] is True
]
print("\n===== FALSE->TRUE CLOAK ONSET ROWS: TRACKING-RUN ANCHOR =====")
print("row_count=", len(onset_rows))
print("outcome_x_anchor=", Counter((r["outcome"], r["wp_eq_anchor"]) for r in onset_rows))
print("state_x_anchor=", Counter((r["state"], r["wp_eq_anchor"]) for r in onset_rows))
print("anchor_identity=", Counter(r["anchor_same_identity"] for r in onset_rows))
print("anchor_distance=", Counter(round(r["wp_anchor_distance"], 6) if r["wp_anchor_distance"] is not None else None for r in onset_rows))

bad_onset = [r for r in onset_rows if not r["wp_eq_anchor"]]
print("\n===== ONSET ANCHOR MISMATCHES =====")
print("count=", len(bad_onset))
for r in bad_onset:
    print(r)

print("\n===== ONSET ANCHOR MATCH EXAMPLES =====")
for r in onset_rows[:20]:
    if r["wp_eq_anchor"]:
        print(r)

# First non-current row in each continuous tracking run. This tests whether the same
# pre-run anchor explains the general transition, not only visible cloak onset rows.
runs = defaultdict(list)
for r in rows:
    runs[(r["mite"], r["target"], r["tracking_start"])].append(r)
for rr in runs.values():
    rr.sort(key=lambda r: r["turn"])

first_noncurrent = []
for key, rr in runs.items():
    for r in rr:
        if r["state"] != "current":
            first_noncurrent.append(r)
            break

print("\n===== FIRST NON-CURRENT ROW PER TRACKING RUN =====")
print("run_count=", len(first_noncurrent))
print("cloak_x_outcome_x_anchor=", Counter(
    (r["cloak_now"], r["outcome"], r["wp_eq_anchor"])
    for r in first_noncurrent
))
print("state_x_anchor=", Counter((r["state"], r["wp_eq_anchor"]) for r in first_noncurrent))

print("\n===== FIRST NON-CURRENT ANCHOR MISMATCHES =====")
bad_first = [r for r in first_noncurrent if not r["wp_eq_anchor"]]
print("count=", len(bad_first))
for r in bad_first:
    print(r)

print("\n===== FOCUS TARGETS 380 / 329 / 206 =====")
for r in rows:
    if r["target"] in {380, 329, 206}:
        print(r)

print("\nNOTE: anchor = owner-authoritative target position at tracking_start - 1.")
print("Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
