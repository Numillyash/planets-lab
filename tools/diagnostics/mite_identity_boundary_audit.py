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


rows_by_key = defaultdict(list)
for (turn, sid), rec in sorted(ships.items()):
    if rec["hull"] != MITE_HULL_ID:
        continue
    target_id = rec["m1"]
    if rec["mission"] != 7 or target_id is None or target_id <= 0:
        continue
    rows_by_key[(sid, target_id)].append(turn)

runs = []
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
        start, end = rr[0], rr[-1]
        mite = ship(start, mite_id)
        target = ship(start, target_id)
        anchor = ship(start - 1, target_id)
        pre = ship(start - 1, mite_id)
        after_mite = ship(end + 1, mite_id)
        target_end = ship(end, target_id)
        target_after = ship(end + 1, target_id)

        earlier_turns = sorted(t for (t, sid) in ships if sid == mite_id and t < start)
        prior_turn = earlier_turns[-1] if earlier_turns else None
        prior = ship(prior_turn, mite_id) if prior_turn is not None else None

        same_ident_turns = sorted(
            t for (t, sid), r in ships.items()
            if sid == mite_id and ident(r) == ident(mite)
        )
        first_same_ident_turn = same_ident_turns[0] if same_ident_turns else None

        if after_mite is None:
            outcome = "missing_after"
        elif tracking(after_mite, target_id):
            outcome = "retained_continues"
        elif after_mite["mission"] == 0 and after_mite["m1"] in (None, 0):
            outcome = "immediate_full_clear"
        elif after_mite["mission"] == 7 and after_mite["m1"] in (None, 0):
            outcome = "target_clear_pending"
        else:
            outcome = "other"

        same_target_after = same_identity(target_end, target_after)
        same_identity_clear = outcome == "immediate_full_clear" and same_target_after

        runs.append({
            "mite": mite_id,
            "target": target_id,
            "start": start,
            "end": end,
            "length": end - start + 1,
            "start_owner": None if mite is None else mite["owner"],
            "start_hull": None if mite is None else mite["hull"],
            "start_name": None if mite is None else mite["name"],
            "start_raw_turn": None if mite is None else mite["raw_turn"],
            "raw_turn_eq_start": mite is not None and mite["raw_turn"] == start,
            "first_same_ident_turn": first_same_ident_turn,
            "identity_first_seen_at_start": first_same_ident_turn == start,
            "pre_exists": pre is not None,
            "pre_identity": ident(pre),
            "pre_xy": xy(pre),
            "prior_turn": prior_turn,
            "prior_gap": None if prior_turn is None else start - prior_turn,
            "prior_owner": None if prior is None else prior["owner"],
            "prior_hull": None if prior is None else prior["hull"],
            "prior_name": None if prior is None else prior["name"],
            "prior_raw_turn": None if prior is None else prior["raw_turn"],
            "prior_xy": xy(prior),
            "prior_same_identity": same_identity(prior, mite) if prior is not None else None,
            "prior_to_start_distance": distance(xy(prior), xy(mite)),
            "target_start_exists": target is not None,
            "anchor_exists": anchor is not None,
            "anchor_same_identity_start": same_identity(anchor, target),
            "anchor_xy": xy(anchor),
            "target_start_xy": xy(target),
            "start_wp": wp(mite),
            "start_wp_eq_target": exact(wp(mite), xy(target)),
            "start_wp_eq_anchor": exact(wp(mite), xy(anchor)),
            "outcome": outcome,
            "same_target_after": same_target_after,
            "same_identity_clear": same_identity_clear,
        })

print("\n===== RED MITE TRACKING IDENTITY BOUNDARY =====")
print("run_count=", len(runs))
print("raw_turn_eq_start=", Counter(r["raw_turn_eq_start"] for r in runs))
print("identity_first_seen_at_start=", Counter(r["identity_first_seen_at_start"] for r in runs))
print("target_start_exists=", Counter(r["target_start_exists"] for r in runs))
print("anchor_exists=", Counter(r["anchor_exists"] for r in runs))
print("anchor_same_identity_start=", Counter(r["anchor_same_identity_start"] for r in runs))
print("start_wp_eq_target=", Counter(r["start_wp_eq_target"] for r in runs))

print("\n===== START WAYPOINT != CURRENT TARGET =====")
bad_start = [r for r in runs if not r["start_wp_eq_target"]]
print("count=", len(bad_start))
for r in bad_start:
    print(r)

print("\n===== PRIOR NUMERIC-ID IDENTITY DISTRIBUTION =====")
with_prior = [r for r in runs if r["prior_turn"] is not None]
print("with_prior=", len(with_prior))
print("prior_gap=", Counter(r["prior_gap"] for r in with_prior))
print("prior_hull_name=", Counter((r["prior_hull"], r["prior_name"]) for r in with_prior).most_common())
print("prior_owner=", Counter(r["prior_owner"] for r in with_prior))
print("prior_same_identity=", Counter(r["prior_same_identity"] for r in with_prior))

print("\n===== IMMEDIATELY PRECEDING NUMERIC-ID REPLACEMENTS =====")
pre = [r for r in runs if r["pre_exists"]]
print("count=", len(pre))
print("pre_hull_name=", Counter((r["prior_hull"], r["prior_name"]) for r in pre))
print("prior_to_start_distance=", Counter(round(r["prior_to_start_distance"], 6) if r["prior_to_start_distance"] is not None else None for r in pre))
for r in pre:
    print(r)

print("\n===== SAME-IDENTITY IMMEDIATE-CLEAR IDENTITY BOUNDARY =====")
clear_runs = [r for r in runs if r["same_identity_clear"]]
print("run_count=", len(clear_runs))
print("raw_turn_eq_start=", Counter(r["raw_turn_eq_start"] for r in clear_runs))
print("identity_first_seen_at_start=", Counter(r["identity_first_seen_at_start"] for r in clear_runs))
print("prior_gap=", Counter(r["prior_gap"] for r in clear_runs))
print("prior_hull_name=", Counter((r["prior_hull"], r["prior_name"]) for r in clear_runs).most_common())
print("start_wp_eq_target=", Counter(r["start_wp_eq_target"] for r in clear_runs))
print("start_wp_eq_anchor=", Counter(r["start_wp_eq_anchor"] for r in clear_runs))

print("\n===== FOCUS 206 / 329 / 380 =====")
for r in runs:
    if r["target"] in {206, 329, 380}:
        print(r)

print("\nNOTE: identity uses owner, hull, name, and raw ship turn.")
print("raw_turn==start is reported as an observation, not assigned creation semantics by itself.")
print("Numeric ids may be reused. period=2170 is scoped to game 591478.")
