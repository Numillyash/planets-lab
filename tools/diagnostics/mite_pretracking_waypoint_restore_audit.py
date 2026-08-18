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


# Build continuous tracking runs.
runs = defaultdict(list)
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
    runs[(mite_id, target_id, start)].append(turn)

run_rows = []
for (mite_id, target_id, start), turns in sorted(runs.items()):
    turns = sorted(turns)
    pre_mite = ship(start - 1, mite_id)
    pre_target = ship(start - 1, target_id)
    start_target = ship(start, target_id)
    start_mite = ship(start, mite_id)
    anchor = xy(pre_target)
    pre_wp = wp(pre_mite)

    clear_turn = None
    clear_target_same_next = None
    clear_wp = None
    clear_target_xy = None
    for turn in turns:
        if outcome(turn, mite_id, target_id) == "immediate_full_clear":
            target_now = ship(turn, target_id)
            target_next = ship(turn + 1, target_id)
            clear_turn = turn
            clear_target_same_next = same_identity(target_now, target_next)
            clear_wp = wp(ship(turn, mite_id))
            clear_target_xy = xy(target_now)
            break

    run_rows.append({
        "mite": mite_id,
        "target": target_id,
        "tracking_start": start,
        "tracking_end": max(turns),
        "pre_mite_exists": pre_mite is not None,
        "pre_target_exists": pre_target is not None,
        "anchor_same_identity_start": same_identity(pre_target, start_target),
        "pre_mite_xy": xy(pre_mite),
        "pre_mite_wp": pre_wp,
        "pre_mite_mission": None if pre_mite is None else pre_mite["mission"],
        "pre_mite_m1": None if pre_mite is None else pre_mite["m1"],
        "anchor_xy": anchor,
        "start_target_xy": xy(start_target),
        "start_mite_wp": wp(start_mite),
        "pre_wp_eq_anchor": exact(pre_wp, anchor),
        "pre_wp_eq_pre_mite": exact(pre_wp, xy(pre_mite)),
        "start_wp_eq_target": exact(wp(start_mite), xy(start_target)),
        "clear_turn": clear_turn,
        "clear_target_same_next": clear_target_same_next,
        "clear_wp": clear_wp,
        "clear_target_xy": clear_target_xy,
        "clear_wp_eq_anchor": exact(clear_wp, anchor),
        "clear_wp_eq_pre_wp": exact(clear_wp, pre_wp),
    })

print("\n===== ALL TRACKING RUNS: PRE-TRACKING WAYPOINT =====")
print("run_count=", len(run_rows))
print("pre_mite_exists=", Counter(r["pre_mite_exists"] for r in run_rows))
print("pre_target_exists=", Counter(r["pre_target_exists"] for r in run_rows))
print("anchor_same_identity_start=", Counter(r["anchor_same_identity_start"] for r in run_rows))
print("pre_wp_eq_anchor=", Counter(r["pre_wp_eq_anchor"] for r in run_rows))
print("pre_wp_eq_pre_mite=", Counter(r["pre_wp_eq_pre_mite"] for r in run_rows))
print("start_wp_eq_target=", Counter(r["start_wp_eq_target"] for r in run_rows))
print("pre_mission_m1=", Counter((r["pre_mite_mission"], r["pre_mite_m1"]) for r in run_rows).most_common(20))

valid_pre = [r for r in run_rows if r["pre_mite_exists"] and r["pre_target_exists"]]
print("\n===== VALID PRE-SNAPSHOT RUNS =====")
print("run_count=", len(valid_pre))
print("pre_wp_eq_anchor=", Counter(r["pre_wp_eq_anchor"] for r in valid_pre))
print("pre_wp_eq_pre_mite=", Counter(r["pre_wp_eq_pre_mite"] for r in valid_pre))

same_identity_clears = [
    r for r in run_rows
    if r["clear_turn"] is not None and r["clear_target_same_next"] is True
]
print("\n===== SAME-IDENTITY IMMEDIATE-CLEAR RUNS =====")
print("run_count=", len(same_identity_clears))
print("pre_mite_exists=", Counter(r["pre_mite_exists"] for r in same_identity_clears))
print("pre_wp_eq_anchor=", Counter(r["pre_wp_eq_anchor"] for r in same_identity_clears))
print("clear_wp_eq_anchor=", Counter(r["clear_wp_eq_anchor"] for r in same_identity_clears))
print("clear_wp_eq_pre_wp=", Counter(r["clear_wp_eq_pre_wp"] for r in same_identity_clears))
print("joint=", Counter(
    (r["pre_wp_eq_anchor"], r["clear_wp_eq_anchor"], r["clear_wp_eq_pre_wp"])
    for r in same_identity_clears
))

print("\n===== PRE-WAYPOINT != ANCHOR EXAMPLES =====")
bad = [r for r in valid_pre if not r["pre_wp_eq_anchor"]]
print("count=", len(bad))
for r in bad[:50]:
    print(r)

print("\n===== CLEAR RUNS: RESTORE PRE-WAYPOINT MISMATCHES =====")
restore_bad = [
    r for r in same_identity_clears
    if r["pre_mite_exists"] and not r["clear_wp_eq_pre_wp"]
]
print("count=", len(restore_bad))
for r in restore_bad:
    print(r)

print("\n===== FOCUS 206 / 329 / 380 / 202 / 216 =====")
for r in run_rows:
    if r["target"] in {206, 329, 380, 202, 216}:
        print(r)

print("\nNOTE: anchor = owner-authoritative target position at tracking_start - 1.")
print("This diagnostic tests whether that anchor is simply the Mite waypoint from the pre-tracking snapshot.")
print("Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
