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
LOOKAHEAD = 12
ROUND_TOL = 1.5

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
        "warp": _intish(raw.get("warp")),
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


def ident(s):
    if s is None:
        return None
    return (s["owner"], s["hull"], s["name"], s["raw_turn"])


def same_identity(a, b):
    return a is not None and b is not None and ident(a) == ident(b)


def axis_delta(a, b):
    return ((b - a + PERIOD / 2) % PERIOD) - PERIOD / 2


def distance(a, b):
    if a is None or b is None:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def exact(a, b):
    d = distance(a, b)
    return d is not None and d <= EPS


def tracking(s, target_id):
    return (
        s is not None
        and s["hull"] == MITE_HULL_ID
        and s["mission"] == 7
        and s["m1"] == target_id
    )


turns_by_pair = defaultdict(list)
for (turn, sid), s in sorted(ships.items()):
    if s["hull"] != MITE_HULL_ID or s["mission"] != 7:
        continue
    target_id = s["m1"]
    if target_id is None or target_id <= 0:
        continue
    turns_by_pair[(sid, target_id)].append(turn)

runs = []
for (mite_id, target_id), turns in sorted(turns_by_pair.items()):
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
        mite_end = ship(end, mite_id)
        mite_clear = ship(end + 1, mite_id)
        target_end = ship(end, target_id)
        target_after = ship(end + 1, target_id)
        target_anchor = ship(start - 1, target_id)
        if mite_clear is None or target_anchor is None:
            continue
        if mite_clear["mission"] != 0 or mite_clear["m1"] not in (None, 0):
            continue
        if not same_identity(mite_end, mite_clear):
            continue
        if not same_identity(target_end, target_after):
            continue

        visible_cloak = False
        exact_contact = False
        for t in rr:
            m = ship(t, mite_id)
            target = ship(t, target_id)
            if target is None:
                continue
            visible_cloak = visible_cloak or target["cloak"] is True
            exact_contact = exact_contact or exact(xy(m), xy(target))

        if exact_contact:
            branch = "exact_contact"
        elif visible_cloak:
            branch = "visible_cloak"
        else:
            branch = "unexplained"

        base_ident = ident(mite_end)
        anchor = xy(target_anchor)
        rows = []
        first_absent = None
        first_identity_change = None
        first_reach_anchor = None
        first_warp0 = None
        first_wp_self = None

        for offset in range(0, LOOKAHEAD + 1):
            t = end + offset
            m = ship(t, mite_id)
            same = m is not None and ident(m) == base_ident
            if m is None and first_absent is None:
                first_absent = offset
            if m is not None and not same and first_identity_change is None:
                first_identity_change = offset

            point = xy(m) if same else None
            target_wp = wp(m) if same else None
            dist_anchor = distance(point, anchor)
            reach = dist_anchor is not None and dist_anchor <= EPS
            if reach and first_reach_anchor is None:
                first_reach_anchor = offset
            warp = m["warp"] if same else None
            if warp == 0 and first_warp0 is None:
                first_warp0 = offset
            wp_self = same and exact(target_wp, point)
            if wp_self and first_wp_self is None:
                first_wp_self = offset

            prev = ship(t - 1, mite_id)
            prev_same = prev is not None and ident(prev) == base_ident
            prev_point = xy(prev) if prev_same else None
            prev_warp = prev["warp"] if prev_same else None
            step = distance(prev_point, point) if same and prev_same else None
            prev_dist_anchor = distance(prev_point, anchor) if prev_same else None
            progress = None
            if prev_dist_anchor is not None and dist_anchor is not None:
                progress = prev_dist_anchor - dist_anchor
            toward_residual = None
            if step is not None and progress is not None:
                toward_residual = abs(step - progress)
            warp2_residual = None
            if step is not None and prev_warp is not None:
                warp2_residual = abs(step - min(float(prev_warp * prev_warp), prev_dist_anchor if prev_dist_anchor is not None else float(prev_warp * prev_warp)))

            rows.append({
                "offset": offset,
                "turn": t,
                "same_identity": same,
                "xy": point,
                "wp": target_wp,
                "warp": warp,
                "mission": m["mission"] if same else None,
                "m1": m["m1"] if same else None,
                "distance_to_anchor": None if dist_anchor is None else round(dist_anchor, 6),
                "wp_eq_anchor": same and exact(target_wp, anchor),
                "wp_eq_self": wp_self,
                "step": None if step is None else round(step, 6),
                "progress_to_anchor": None if progress is None else round(progress, 6),
                "toward_residual": None if toward_residual is None else round(toward_residual, 6),
                "warp2_residual": None if warp2_residual is None else round(warp2_residual, 6),
            })

        moving_post = [
            r for r in rows[1:]
            if r["same_identity"] and r["warp"] not in (None, 0) and r["step"] is not None
        ]
        fallback_moving = [r for r in moving_post if r["wp_eq_anchor"]]
        straight_toward = [
            r for r in fallback_moving
            if r["progress_to_anchor"] is not None
            and r["progress_to_anchor"] >= -ROUND_TOL
            and r["toward_residual"] is not None
            and r["toward_residual"] <= ROUND_TOL
        ]
        warp2_like = [
            r for r in fallback_moving
            if r["warp2_residual"] is not None and r["warp2_residual"] <= ROUND_TOL
        ]

        runs.append({
            "mite": mite_id,
            "target": target_id,
            "start": start,
            "end": end,
            "length": len(rr),
            "branch": branch,
            "anchor": anchor,
            "end_xy": xy(mite_end),
            "end_wp": wp(mite_end),
            "end_wp_eq_anchor": exact(wp(mite_end), anchor),
            "clear_xy": xy(mite_clear),
            "clear_wp": wp(mite_clear),
            "clear_wp_eq_anchor": exact(wp(mite_clear), anchor),
            "clear_warp": mite_clear["warp"],
            "moving_post_count": len(moving_post),
            "fallback_moving_count": len(fallback_moving),
            "straight_toward_count": len(straight_toward),
            "warp2_like_count": len(warp2_like),
            "all_moving_wp_anchor": bool(moving_post) and len(fallback_moving) == len(moving_post),
            "all_fallback_straight_toward": bool(fallback_moving) and len(straight_toward) == len(fallback_moving),
            "all_fallback_warp2_like": bool(fallback_moving) and len(warp2_like) == len(fallback_moving),
            "first_reach_anchor": first_reach_anchor,
            "first_warp0": first_warp0,
            "first_wp_self": first_wp_self,
            "first_absent": first_absent,
            "first_identity_change": first_identity_change,
            "rows": rows,
        })

print("\n===== CLEAR FALLBACK NAVIGATION SUMMARY =====")
print("run_count=", len(runs))
print("branch=", Counter(r["branch"] for r in runs))
print("end_wp_eq_anchor=", Counter((r["branch"], r["end_wp_eq_anchor"]) for r in runs))
print("clear_wp_eq_anchor=", Counter((r["branch"], r["clear_wp_eq_anchor"]) for r in runs))
print("all_moving_wp_anchor=", Counter((r["branch"], r["all_moving_wp_anchor"]) for r in runs))
print("all_fallback_straight_toward=", Counter((r["branch"], r["all_fallback_straight_toward"]) for r in runs))
print("all_fallback_warp2_like=", Counter((r["branch"], r["all_fallback_warp2_like"]) for r in runs))
print("first_reach_anchor=", Counter((r["branch"], r["first_reach_anchor"]) for r in runs))
print("first_warp0=", Counter((r["branch"], r["first_warp0"]) for r in runs))
print("first_wp_self=", Counter((r["branch"], r["first_wp_self"]) for r in runs))
print("first_absent=", Counter((r["branch"], r["first_absent"]) for r in runs))

print("\n===== REACHED ANCHOR BEFORE STOP / LOSS =====")
reached = [r for r in runs if r["first_reach_anchor"] is not None]
print("count=", len(reached))
print("branch=", Counter(r["branch"] for r in reached))
print("reach_then_warp0_offset_delta=", Counter(
    None if r["first_warp0"] is None else r["first_warp0"] - r["first_reach_anchor"]
    for r in reached
))
print("reach_then_wp_self_offset_delta=", Counter(
    None if r["first_wp_self"] is None else r["first_wp_self"] - r["first_reach_anchor"]
    for r in reached
))

print("\n===== DISAPPEAR / CHANGE BEFORE ANCHOR =====")
preanchor_loss = []
for r in runs:
    terminal = r["first_absent"]
    if terminal is None:
        terminal = r["first_identity_change"]
    if terminal is not None and (r["first_reach_anchor"] is None or terminal < r["first_reach_anchor"]):
        preanchor_loss.append(r)
print("count=", len(preanchor_loss))
print("branch=", Counter(r["branch"] for r in preanchor_loss))
for r in preanchor_loss[:20]:
    print({k: v for k, v in r.items() if k != "rows"})

print("\n===== NAVIGATION MISMATCHES =====")
mismatches = [
    r for r in runs
    if r["moving_post_count"] > 0
    and (not r["all_moving_wp_anchor"] or not r["all_fallback_straight_toward"])
]
print("count=", len(mismatches))
for r in mismatches[:20]:
    print({k: v for k, v in r.items() if k != "rows"})
    for row in r["rows"]:
        print("  ", row)

print("\n===== FOCUS 206 / 329 / 380 =====")
for r in runs:
    if r["target"] in {206, 329, 380}:
        print({k: v for k, v in r.items() if k != "rows"})
        for row in r["rows"]:
            print("  ", row)

print("\nNOTE: anchor means owner-authoritative target position at tracking_start-1.")
print("This audit tests observed post-clear navigation toward that coordinate; it does not assert an internal Host field.")
print("warp2_like compares observed step to min(previous_warp^2, remaining anchor distance), with 1.5ly rounding tolerance.")
print("period=2170 remains scoped to game 591478.")
