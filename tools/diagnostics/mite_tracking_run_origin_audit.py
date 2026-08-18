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


# Build continuous mission=7/m1=target runs for Red Mites.
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
        start = rr[0]
        end = rr[-1]
        start_mite = ship(start, mite_id)
        pre_mite = ship(start - 1, mite_id)
        target_start = ship(start, target_id)
        anchor = ship(start - 1, target_id)
        after_mite = ship(end + 1, mite_id)
        target_end = ship(end, target_id)
        target_after = ship(end + 1, target_id)

        # Find prior use of this numeric Mite id, if any. Numeric ids may be reused.
        earlier_turns = sorted(t for (t, sid) in ships if sid == mite_id and t < start)
        prior = ship(earlier_turns[-1], mite_id) if earlier_turns else None
        prior_turn = earlier_turns[-1] if earlier_turns else None
        prior_gap = None if prior_turn is None else start - prior_turn
        prior_same_identity = same_identity(prior, start_mite) if prior is not None else None

        anchor_rows = []
        informative_rows = []
        prev_eq_anchor = None
        for t in rr:
            m = ship(t, mite_id)
            target = ship(t, target_id)
            eq_anchor = exact(wp(m), xy(anchor))
            if eq_anchor:
                anchor_rows.append(t)
                if prev_eq_anchor is False:
                    informative_rows.append(t)
            prev_eq_anchor = eq_anchor

        first_anchor_turn = anchor_rows[0] if anchor_rows else None
        first_anchor_target = ship(first_anchor_turn, target_id) if first_anchor_turn is not None else None
        first_anchor_mite = ship(first_anchor_turn, mite_id) if first_anchor_turn is not None else None

        if after_mite is None:
            end_outcome = "missing_after"
        elif tracking(after_mite, target_id):
            end_outcome = "retained_continues"
        elif after_mite["mission"] == 0 and after_mite["m1"] in (None, 0):
            end_outcome = "immediate_full_clear"
        elif after_mite["mission"] == 7 and after_mite["m1"] in (None, 0):
            end_outcome = "target_clear_pending"
        else:
            end_outcome = "other"

        same_target_identity_after = same_identity(target_end, target_after)
        same_identity_immediate_clear = (
            end_outcome == "immediate_full_clear" and same_target_identity_after
        )

        runs.append({
            "mite": mite_id,
            "target": target_id,
            "start": start,
            "end": end,
            "length": end - start + 1,
            "pre_mite_exists": pre_mite is not None,
            "pre_mite_same_identity": same_identity(pre_mite, start_mite) if pre_mite is not None else None,
            "numeric_id_seen_earlier": prior is not None,
            "prior_turn": prior_turn,
            "prior_gap": prior_gap,
            "prior_identity": ident(prior),
            "start_identity": ident(start_mite),
            "prior_same_identity": prior_same_identity,
            "pre_mission": None if pre_mite is None else pre_mite["mission"],
            "pre_m1": None if pre_mite is None else pre_mite["m1"],
            "anchor_exists": anchor is not None,
            "anchor_same_identity_start": same_identity(anchor, target_start),
            "anchor_xy": xy(anchor),
            "target_start_xy": xy(target_start),
            "target_moved_anchor_start": not exact(xy(anchor), xy(target_start)),
            "anchor_to_start_distance": distance(xy(anchor), xy(target_start)),
            "mite_start_xy": xy(start_mite),
            "mite_start_wp": wp(start_mite),
            "start_wp_eq_target": exact(wp(start_mite), xy(target_start)),
            "start_wp_eq_anchor": exact(wp(start_mite), xy(anchor)),
            "first_anchor_turn": first_anchor_turn,
            "first_anchor_age": None if first_anchor_turn is None else first_anchor_turn - start,
            "first_anchor_cloak": None if first_anchor_target is None else first_anchor_target["cloak"],
            "first_anchor_target_eq_anchor": None if first_anchor_target is None else exact(xy(first_anchor_target), xy(anchor)),
            "first_anchor_wp_eq_mite": None if first_anchor_mite is None else exact(wp(first_anchor_mite), xy(first_anchor_mite)),
            "informative_anchor_turn": informative_rows[0] if informative_rows else None,
            "end_outcome": end_outcome,
            "same_target_identity_after": same_target_identity_after,
            "same_identity_immediate_clear": same_identity_immediate_clear,
            "target_end_cloak": None if target_end is None else target_end["cloak"],
        })

print("\n===== TRACKING RUN ORIGIN SUMMARY =====")
print("run_count=", len(runs))
print("pre_mite_exists=", Counter(r["pre_mite_exists"] for r in runs))
print("numeric_id_seen_earlier=", Counter(r["numeric_id_seen_earlier"] for r in runs))
print("prior_same_identity=", Counter(r["prior_same_identity"] for r in runs))
print("start_wp_eq_target=", Counter(r["start_wp_eq_target"] for r in runs))
print("end_outcome=", Counter(r["end_outcome"] for r in runs))

print("\n===== PREVIOUS-SNAPSHOT ABSENT RUNS =====")
absent = [r for r in runs if not r["pre_mite_exists"]]
print("run_count=", len(absent))
print("numeric_id_seen_earlier=", Counter(r["numeric_id_seen_earlier"] for r in absent))
print("prior_same_identity=", Counter(r["prior_same_identity"] for r in absent))
print("end_outcome=", Counter(r["end_outcome"] for r in absent))
print("has_anchor_exposure=", Counter(r["first_anchor_turn"] is not None for r in absent))
print("has_informative_anchor_transition=", Counter(r["informative_anchor_turn"] is not None for r in absent))
print("target_moved_anchor_start=", Counter(r["target_moved_anchor_start"] for r in absent))

print("\n===== PREVIOUS-SNAPSHOT PRESENT RUNS =====")
present = [r for r in runs if r["pre_mite_exists"]]
print("run_count=", len(present))
for r in present:
    print(r)

print("\n===== SAME-IDENTITY IMMEDIATE-CLEAR RUNS =====")
clear_runs = [r for r in runs if r["same_identity_immediate_clear"]]
print("run_count=", len(clear_runs))
print("pre_mite_exists=", Counter(r["pre_mite_exists"] for r in clear_runs))
print("numeric_id_seen_earlier=", Counter(r["numeric_id_seen_earlier"] for r in clear_runs))
print("prior_same_identity=", Counter(r["prior_same_identity"] for r in clear_runs))
print("has_anchor_exposure=", Counter(r["first_anchor_turn"] is not None for r in clear_runs))
print("has_informative_anchor_transition=", Counter(r["informative_anchor_turn"] is not None for r in clear_runs))
print("first_anchor_age=", Counter(r["first_anchor_age"] for r in clear_runs))
print("first_anchor_cloak=", Counter(r["first_anchor_cloak"] for r in clear_runs))
print("first_anchor_target_eq_anchor=", Counter(r["first_anchor_target_eq_anchor"] for r in clear_runs))

print("\n===== ABSENT-PREV RUNS BY OUTCOME / PRIOR-ID HISTORY =====")
print(Counter(
    (r["end_outcome"], r["numeric_id_seen_earlier"], r["prior_same_identity"])
    for r in absent
))

print("\n===== CLEAR RUN PRIOR-ID REUSE EXAMPLES =====")
reuse_clear = [r for r in clear_runs if r["numeric_id_seen_earlier"]]
print("count=", len(reuse_clear))
for r in reuse_clear[:30]:
    print(r)

print("\n===== FOCUS 206 / 329 / 380 =====")
for r in runs:
    if r["target"] in {206, 329, 380}:
        print(r)

print("\nNOTE: pre_mite_exists means the same numeric ship id is present on start-1.")
print("Numeric ids may be reused; absence on start-1 is not called birth without lifecycle evidence.")
print("anchor = owner-authoritative target position at tracking_start-1.")
print("Mission numbers remain unnamed. period=2170 is scoped to game 591478.")
