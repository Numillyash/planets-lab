from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


GAME_ID = 591478
MITE_HULL_ID = 213
MAX_LAG = 4

ARCHIVE_PATH = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")
PREPARED_PATH = Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle")

archive_data = ARCHIVE_PATH.read_bytes()
prepared, hit = load_or_build_prepared_game_cache(
    archive_data,
    game_id=GAME_ID,
    cache_path=PREPARED_PATH,
)
print("prepared_cache_hit:", hit)

topology = extract_map_topology(archive_data)
records = tuple(prepared.snapshots)
ship_groups = group_perspective_records(records, "ship")

ships: dict[tuple[int, int], dict] = {}
for (turn, ship_id), group in ship_groups.items():
    owner_id, rec = _owner_record(group)
    if rec is None:
        continue
    raw = rec.raw
    ships[(turn, ship_id)] = {
        "turn": turn,
        "id": ship_id,
        "owner": owner_id,
        "hull": _intish(raw.get("hullid")),
        "name": raw.get("name"),
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
        "targetx": _intish(raw.get("targetx")),
        "targety": _intish(raw.get("targety")),
        "mission": _intish(raw.get("mission")),
        "m1": _intish(raw.get("mission1target")),
        "cloak": raw.get("iscloaked"),
        "warp": _intish(raw.get("warp")),
        "enemy": _intish(raw.get("enemy")),
    }


def ship(turn: int, ship_id: int):
    return ships.get((turn, ship_id))


def xy(s):
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def waypoint(s):
    if s is None or s["targetx"] is None or s["targety"] is None:
        return None
    return (s["targetx"], s["targety"])


def raw_distance(a, b):
    if a is None or b is None:
        return None
    return hypot(b[0] - a[0], b[1] - a[1])


def topology_vector(a, b):
    if a is None or b is None:
        return None
    return _vector(a, b, topology)


def topology_distance(a, b):
    v = topology_vector(a, b)
    if v is None:
        return None
    return hypot(v[0], v[1])


def nearest_topology_image(origin, target):
    v = topology_vector(origin, target)
    if v is None:
        return None
    return (origin[0] + v[0], origin[1] + v[1])


def wrap_required(a, b):
    rd = raw_distance(a, b)
    td = topology_distance(a, b)
    return (
        rd is not None
        and td is not None
        and rd - td > 500.0
    )


def target_point(turn: int, target: int):
    return xy(ship(turn, target))


def waypoint_state(turn: int, target: int, mite_state):
    wp = waypoint(mite_state)
    if wp is None:
        return "missing_waypoint", []
    matches = []
    for lag in range(MAX_LAG + 1):
        p = target_point(turn - lag, target)
        if p is None:
            continue
        d = topology_distance(wp, p)
        if d is not None and d < 1e-9:
            matches.append(lag)
    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", matches


def mite_outcome(after, target: int):
    if after is None:
        return "missing_after"
    if after["mission"] == 7 and after["m1"] == target:
        return "retained"
    if after["mission"] == 0 and (after["m1"] is None or after["m1"] == 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and (after["m1"] is None or after["m1"] == 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


# ---------------------------------------------------------------------------
# 1. Does the sign of mission1target correlate with selecting a wrapped image
#    of the referenced ship? We do not assign any mission semantics here.
# ---------------------------------------------------------------------------

sign_wrap = Counter()
mission_sign_wrap = Counter()
negative_rows = []

for (turn, sid), s in sorted(ships.items()):
    m1 = s["m1"]
    if m1 is None or m1 == 0:
        continue

    target = ship(turn, abs(m1))
    if target is None:
        continue

    a = xy(s)
    b = xy(target)
    rd = raw_distance(a, b)
    td = topology_distance(a, b)
    needs_wrap = wrap_required(a, b)
    sign = "negative" if m1 < 0 else "positive"
    nearest = nearest_topology_image(a, b)

    sign_wrap[(sign, needs_wrap)] += 1
    mission_sign_wrap[(s["mission"], sign, needs_wrap)] += 1

    if m1 < 0:
        negative_rows.append({
            "turn": turn,
            "ship": sid,
            "ship_owner": s["owner"],
            "ship_hull": s["hull"],
            "ship_name": s["name"],
            "mission": s["mission"],
            "m1": m1,
            "abs_target": abs(m1),
            "target_owner": target["owner"],
            "target_hull": target["hull"],
            "target_name": target["name"],
            "ship_xy": a,
            "target_raw_xy": b,
            "target_nearest_image": nearest,
            "raw_distance": rd,
            "topology_distance": td,
            "wrap_required": needs_wrap,
        })

print()
print("===== MISSION1TARGET SIGN VS TOPOLOGY-WRAP REQUIREMENT =====")
for key, n in sorted(sign_wrap.items()):
    print({"sign": key[0], "wrap_required": key[1], "n": n})

print()
print("===== MISSION/SIGN/WRAP SUMMARY =====")
for key, n in mission_sign_wrap.most_common():
    print({
        "mission": key[0],
        "sign": key[1],
        "wrap_required": key[2],
        "n": n,
    })

print()
print("===== ALL NEGATIVE MISSION1TARGET ROWS WITH NEAREST TOPOLOGY IMAGE =====")
for item in negative_rows:
    print(item)


# ---------------------------------------------------------------------------
# 2. Active Mite transitions and strong mission-6 co-movement candidates.
#    The narrow question is provenance: when the Mite's next waypoint is not
#    the target's next position, does it exactly inherit the candidate mover's
#    previous raw waypoint?
# ---------------------------------------------------------------------------

mite_seq = defaultdict(list)
for (turn, sid), s in ships.items():
    if s["hull"] == MITE_HULL_ID:
        mite_seq[sid].append(s)
for seq in mite_seq.values():
    seq.sort(key=lambda s: s["turn"])

member_rows = []
rows_by_mite_turn = {}
for mite_id, seq in mite_seq.items():
    for before, after in zip(seq, seq[1:]):
        if after["turn"] != before["turn"] + 1:
            continue
        if not (
            before["mission"] == 7
            and before["m1"] is not None
            and before["m1"] > 0
        ):
            continue
        target_id = before["m1"]
        tb = ship(before["turn"], target_id)
        ta = ship(after["turn"], target_id)
        if tb is None or ta is None or tb["hull"] != ta["hull"]:
            continue
        state, matches = waypoint_state(before["turn"], target_id, before)
        next_state, next_matches = waypoint_state(after["turn"], target_id, after)
        row = {
            "mite": mite_id,
            "turn": before["turn"],
            "target": target_id,
            "target_before": tb,
            "target_after": ta,
            "mite_before": before,
            "mite_after": after,
            "state": state,
            "matches": matches,
            "next_state": next_state,
            "next_matches": next_matches,
            "outcome": mite_outcome(after, target_id),
        }
        member_rows.append(row)
        rows_by_mite_turn[(mite_id, before["turn"])] = row


def mission6_targeters(turn: int, target_id: int):
    target = ship(turn, target_id)
    if target is None:
        return []
    p = xy(target)
    out = []
    for (t, sid), s in ships.items():
        if t != turn or sid == target_id:
            continue
        if s["mission"] != 6 or s["m1"] != target_id:
            continue
        if xy(s) != p:
            continue
        sn = ship(turn + 1, sid)
        tn = ship(turn + 1, target_id)
        if sn is None or tn is None or xy(sn) != xy(tn):
            continue
        out.append({
            "id": sid,
            "owner": s["owner"],
            "hull": s["hull"],
            "name": s["name"],
            "before_xy": xy(s),
            "before_waypoint": waypoint(s),
            "after_xy": xy(sn),
            "after_waypoint": waypoint(sn),
            "mission_after": sn["mission"],
            "m1_after": sn["m1"],
        })
    return out


provenance = Counter()
strong_rows = []

for row in member_rows:
    turn = row["turn"]
    target_id = row["target"]
    targeters = mission6_targeters(turn, target_id)
    if not targeters:
        continue

    target_before_xy = xy(row["target_before"])
    target_after_xy = xy(row["target_after"])
    mite_after_wp = waypoint(row["mite_after"])
    wrap_like = wrap_required(target_before_xy, target_after_xy)

    for mover in targeters:
        mover_wp = mover["before_waypoint"]
        exact_target_after = mite_after_wp == target_after_xy
        exact_mover_waypoint = mite_after_wp is not None and mite_after_wp == mover_wp
        topo_error_to_target_after = topology_distance(mite_after_wp, target_after_xy)
        topo_error_to_mover_wp = topology_distance(mite_after_wp, mover_wp)

        if exact_target_after and exact_mover_waypoint:
            prov = "exact_both"
        elif exact_target_after:
            prov = "exact_target_after"
        elif exact_mover_waypoint:
            prov = "exact_mover_previous_waypoint"
        else:
            prov = "other"

        provenance[(wrap_like, row["next_state"], prov)] += 1
        strong_rows.append({
            "turn": (turn, turn + 1),
            "target": target_id,
            "target_name": row["target_before"]["name"],
            "target_hull": row["target_before"]["hull"],
            "mite": row["mite"],
            "mite_state_before": row["state"],
            "mite_state_after": row["next_state"],
            "mite_outcome": row["outcome"],
            "wrap_like": wrap_like,
            "target_before_xy": target_before_xy,
            "target_after_xy": target_after_xy,
            "target_after_nearest_image_from_mite_wp": nearest_topology_image(
                mite_after_wp,
                target_after_xy,
            ),
            "mite_after_waypoint": mite_after_wp,
            "mover": mover,
            "provenance": prov,
            "topology_error_mite_wp_to_target_after": topo_error_to_target_after,
            "topology_error_mite_wp_to_mover_wp": topo_error_to_mover_wp,
        })

print()
print("===== STRONG MISSION6 CO-MOVEMENT: NEXT MITE WAYPOINT PROVENANCE =====")
for key, n in provenance.most_common():
    print({
        "wrap_like": key[0],
        "mite_state_after": key[1],
        "provenance": key[2],
        "n": n,
    })

print()
print("===== STRONG CO-MOVEMENT ROWS RELEVANT TO PROVENANCE =====")
for item in strong_rows:
    if (
        item["wrap_like"]
        or item["mite_state_after"] != "current"
        or item["provenance"] == "exact_mover_previous_waypoint"
        or item["target"] == 329
    ):
        print(item)


# ---------------------------------------------------------------------------
# 3. Focus the 329 chain. This makes it explicit whether the turn-55 no-match
#    waypoint is inherited from ship 311's turn-54 waypoint, and whether the
#    following strict-stale state is a distinct later transition.
# ---------------------------------------------------------------------------

print()
print("===== TARGET 329 / MITE 1185 SPHERE-REFERENCE CHAIN =====")
for turn in range(53, 57):
    target = ship(turn, 329)
    mite = ship(turn, 1185)
    mover = ship(turn, 311)
    if target is None or mite is None:
        continue

    state = None
    matches = []
    if mite["mission"] == 7 and mite["m1"] == 329:
        state, matches = waypoint_state(turn, 329, mite)

    abs_m1_target = None
    nearest_abs_m1_target = None
    if target["m1"] is not None and target["m1"] != 0:
        abs_m1_target = ship(turn, abs(target["m1"]))
        if abs_m1_target is not None:
            nearest_abs_m1_target = nearest_topology_image(
                xy(target),
                xy(abs_m1_target),
            )

    print({
        "turn": turn,
        "target_xy": xy(target),
        "target_waypoint": waypoint(target),
        "target_mission": target["mission"],
        "target_m1": target["m1"],
        "target_abs_m1_raw_xy": xy(abs_m1_target),
        "target_abs_m1_nearest_image": nearest_abs_m1_target,
        "target_abs_m1_topology_distance": (
            None
            if abs_m1_target is None
            else topology_distance(xy(target), xy(abs_m1_target))
        ),
        "mover_311_xy": xy(mover),
        "mover_311_waypoint": waypoint(mover),
        "mover_311_mission": None if mover is None else mover["mission"],
        "mover_311_m1": None if mover is None else mover["m1"],
        "mite_xy": xy(mite),
        "mite_waypoint": waypoint(mite),
        "mite_state": state,
        "mite_matches": matches,
        "mite_wp_equals_311_wp": (
            mover is not None and waypoint(mite) == waypoint(mover)
        ),
    })

print()
print("===== CURRENT -> NO_MATCH -> STRICT_STALE CHAINS =====")
for row in member_rows:
    if row["state"] != "current" or row["next_state"] != "no_match_0_4":
        continue
    next_row = rows_by_mite_turn.get((row["mite"], row["turn"] + 1))
    if next_row is None or next_row["target"] != row["target"]:
        continue
    next2_row = rows_by_mite_turn.get((row["mite"], row["turn"] + 2))
    next2_state = None
    if next2_row is not None and next2_row["target"] == row["target"]:
        next2_state = next2_row["state"]
    print({
        "turn": row["turn"],
        "mite": row["mite"],
        "target": row["target"],
        "target_name": row["target_before"]["name"],
        "target_move_wrap_like": wrap_required(
            xy(row["target_before"]),
            xy(row["target_after"]),
        ),
        "state_t": row["state"],
        "state_t1": row["next_state"],
        "state_t2": next2_state,
        "outcome_t_to_t1": row["outcome"],
        "outcome_t1_to_t2": next_row["outcome"],
        "mission6_targeters_t": mission6_targeters(row["turn"], row["target"]),
        "mite_waypoint_t1": waypoint(row["mite_after"]),
    })
