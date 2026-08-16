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
        "m2": _intish(raw.get("mission2target")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
        "fuel": _intish(raw.get("neutronium")),
        "mass": _intish(raw.get("mass")),
        "warp": _intish(raw.get("warp")),
        "heading": _intish(raw.get("heading")),
        "enemy": _intish(raw.get("enemy")),
        "raw_turn": _intish(raw.get("turn")),
        "infoturn": _intish(raw.get("infoturn")),
        "readystatus": _intish(raw.get("readystatus")),
        "friendlycode": raw.get("friendlycode"),
    }


def ship(turn: int, ship_id: int):
    return ships.get((turn, ship_id))


def xy(s):
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def topology_distance(a, b):
    if a is None or b is None:
        return None
    dx, dy = _vector(a, b, topology)
    return hypot(dx, dy)


def raw_distance(a, b):
    if a is None or b is None:
        return None
    return hypot(b[0] - a[0], b[1] - a[1])


def target_point(turn: int, target: int):
    return xy(ship(turn, target))


def waypoint_state(turn: int, target: int, mite_state):
    if mite_state is None:
        return None, []
    wp = (mite_state["targetx"], mite_state["targety"])
    if None in wp:
        return "missing_waypoint", []
    matches = []
    distances = {}
    for lag in range(MAX_LAG + 1):
        p = target_point(turn - lag, target)
        if p is None:
            continue
        d = topology_distance(wp, p)
        distances[lag] = d
        if d is not None and d < 1e-9:
            matches.append(lag)
    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", matches


def mite_outcome(before, after, target: int):
    if after is None:
        return "missing_after"
    if after["mission"] == 7 and after["m1"] == target:
        return "retained"
    if after["mission"] == 0 and (after["m1"] is None or after["m1"] == 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and (after["m1"] is None or after["m1"] == 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


# Active Mite member events.
mite_seq = defaultdict(list)
for (turn, ship_id), state in ships.items():
    if state["hull"] == MITE_HULL_ID:
        mite_seq[ship_id].append(state)
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
        target = before["m1"]
        tb = ship(before["turn"], target)
        ta = ship(after["turn"], target)
        if tb is None or ta is None or tb["hull"] != ta["hull"]:
            continue
        state, matches = waypoint_state(before["turn"], target, before)
        row = {
            "mite": mite_id,
            "turn": before["turn"],
            "target": target,
            "target_before": tb,
            "target_after": ta,
            "mite_before": before,
            "mite_after": after,
            "state": state,
            "matches": matches,
            "outcome": mite_outcome(before, after, target),
        }
        member_rows.append(row)
        rows_by_mite_turn[(mite_id, before["turn"])] = row


# ---------------------------------------------------------------------------
# Same-ship evidence for target 206: mission 9 -> next cloak vs damage.
# ---------------------------------------------------------------------------

print()
print("===== TARGET 206 SAME-SHIP MISSION-9 REPLICATION =====")
for turn in range(41, 105):
    a = ship(turn, 206)
    b = ship(turn + 1, 206)
    if a is None or b is None or a["hull"] != 1033 or b["hull"] != 1033:
        continue
    if a["mission"] != 9 or a["cloak"] is not False:
        continue
    print({
        "turn": (turn, turn + 1),
        "mission": (a["mission"], b["mission"]),
        "cloak": (a["cloak"], b["cloak"]),
        "damage": (a["damage"], b["damage"]),
        "podcargo": (a["podcargo"], b["podcargo"]),
        "xy": (xy(a), xy(b)),
    })


# ---------------------------------------------------------------------------
# Candidate mission-6 targeters. We deliberately call these candidates rather
# than asserting the raw numeric mission mapping in the diagnostic itself.
# A strong tow-like case is: same location at T, mission=6/m1=target, and the
# candidate and target end T+1 at the same location.
# ---------------------------------------------------------------------------


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
        out.append({
            "id": sid,
            "owner": s["owner"],
            "hull": s["hull"],
            "name": s["name"],
            "warp": s["warp"],
            "before_xy": xy(s),
            "after_xy": xy(sn),
            "target_after_xy": xy(tn),
            "same_after": sn is not None and tn is not None and xy(sn) == xy(tn),
        })
    return out


# ---------------------------------------------------------------------------
# Sphere-wrap-like movement. Large raw displacement but short topology-aware
# displacement means the target crossed/used a duplicated sphere edge.
# ---------------------------------------------------------------------------

wrap_rows = []
tow_rows = []
combo_table = defaultdict(Counter)

for row in member_rows:
    turn = row["turn"]
    target = row["target"]
    tb = row["target_before"]
    ta = row["target_after"]

    rdist = raw_distance(xy(tb), xy(ta))
    tdist = topology_distance(xy(tb), xy(ta))
    wrap_like = (
        rdist is not None
        and tdist is not None
        and rdist - tdist > 500.0
    )

    targeters = mission6_targeters(turn, target)
    strong_tow_like = any(x["same_after"] for x in targeters)

    next_row = rows_by_mite_turn.get((row["mite"], turn + 1))
    if next_row is not None and next_row["target"] != target:
        next_row = None

    next2_row = rows_by_mite_turn.get((row["mite"], turn + 2))
    if next2_row is not None and next2_row["target"] != target:
        next2_row = None

    category = (
        "wrap+tow" if wrap_like and strong_tow_like
        else "wrap_only" if wrap_like
        else "tow_only" if strong_tow_like
        else "neither"
    )

    next_state = None if next_row is None else next_row["state"]
    combo_table[category][
        (row["outcome"], next_state)
    ] += 1

    payload = {
        "turn": (turn, turn + 1),
        "target": target,
        "name": tb["name"],
        "hull": tb["hull"],
        "mite": row["mite"],
        "target_move": {
            "from": xy(tb),
            "to": xy(ta),
            "raw_distance": rdist,
            "topology_distance": tdist,
            "warp": (tb["warp"], ta["warp"]),
            "mission": (tb["mission"], ta["mission"]),
            "m1": (tb["m1"], ta["m1"]),
            "cloak": (tb["cloak"], ta["cloak"]),
        },
        "mite_state_t": row["state"],
        "mite_outcome_t_to_t1": row["outcome"],
        "mite_state_t1": next_state,
        "mite_outcome_t1_to_t2": None if next_row is None else next_row["outcome"],
        "mite_state_t2": None if next2_row is None else next2_row["state"],
        "mission6_targeters": targeters,
    }

    if wrap_like:
        wrap_rows.append(payload)
    if strong_tow_like:
        tow_rows.append(payload)

print()
print("===== WRAP / MISSION6-TARGETER COMBINATION TABLE =====")
for category, counter in sorted(combo_table.items()):
    print(category)
    for key, n in counter.most_common():
        print("  ", key, n)

print()
print("===== ALL SPHERE-WRAP-LIKE ACTIVE-MITE TARGET MOVES =====")
for item in sorted(wrap_rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    print(item)
print("count=", len(wrap_rows))

print()
print("===== ALL STRONG MISSION6/TARGET CO-MOVEMENT CASES =====")
for item in sorted(tow_rows, key=lambda r: (r["turn"], r["target"], r["mite"])):
    print(item)
print("count=", len(tow_rows))


# ---------------------------------------------------------------------------
# Negative mission1target audit. This is useful for understanding the raw
# representation used by target 329 (mission=7, m1=-1096) without assuming a
# mission-name mapping.
# ---------------------------------------------------------------------------

neg_table = Counter()
neg_rows = []
for (turn, sid), s in sorted(ships.items()):
    m1 = s["m1"]
    if m1 is None or m1 >= 0:
        continue
    abs_target = abs(m1)
    target = ship(turn, abs_target)
    target_next = ship(turn + 1, abs_target)
    self_next = ship(turn + 1, sid)
    d = None if target is None else topology_distance(xy(s), xy(target))
    neg_table[(s["mission"], s["hull"], None if target is None else target["hull"])] += 1
    neg_rows.append({
        "turn": turn,
        "ship": sid,
        "owner": s["owner"],
        "hull": s["hull"],
        "name": s["name"],
        "mission": s["mission"],
        "m1": m1,
        "abs_target": abs_target,
        "target_owner": None if target is None else target["owner"],
        "target_hull": None if target is None else target["hull"],
        "target_name": None if target is None else target["name"],
        "distance_now": d,
        "ship_xy": xy(s),
        "ship_next_xy": xy(self_next),
        "target_xy": xy(target),
        "target_next_xy": xy(target_next),
    })

print()
print("===== NEGATIVE MISSION1TARGET SUMMARY =====")
for key, n in neg_table.most_common(50):
    print({"mission": key[0], "ship_hull": key[1], "target_hull": key[2], "n": n})

print()
print("===== NEGATIVE M1: RU30 / TARGET-329-AREA CASES =====")
for item in neg_rows:
    if item["hull"] == 2071 or item["ship"] in {329, 446} or item["abs_target"] in {1096, 1102}:
        print(item)


# ---------------------------------------------------------------------------
# Target mission 8 while an active Mite is tracking, restricted to cases with
# no current cloak. This tests whether 329's mission=8 state itself is unusual.
# ---------------------------------------------------------------------------

mission8_table = Counter()
mission8_rows = []
for row in member_rows:
    tb = row["target_before"]
    if tb["mission"] != 8 or tb["cloak"] is not False:
        continue
    mission8_table[(row["state"], row["outcome"])] += 1
    mission8_rows.append({
        "turn": row["turn"],
        "target": row["target"],
        "name": tb["name"],
        "hull": tb["hull"],
        "mite": row["mite"],
        "state": row["state"],
        "outcome": row["outcome"],
        "m1": tb["m1"],
        "enemy": tb["enemy"],
        "damage": tb["damage"],
        "podcargo": tb["podcargo"],
    })

print()
print("===== TARGET MISSION=8, CURRENTLY UNCLOAKED: MITE OUTCOME =====")
for key, n in mission8_table.most_common():
    print({"state": key[0], "outcome": key[1], "n": n})
print("examples:")
for item in mission8_rows[:100]:
    print(item)


# ---------------------------------------------------------------------------
# Focus 329 and the nearby RU30 control 446 / Meteor 311 / Horwasp objects.
# ---------------------------------------------------------------------------

print()
print("===== FOCUS 329 / 446 / 311 / 1096 / 1102 TIMELINES =====")
for turn in range(52, 58):
    print()
    print("TURN", turn)
    for sid in (329, 446, 311, 1096, 1102, 1185):
        s = ship(turn, sid)
        if s is None:
            continue
        print(sid, {
            "owner": s["owner"],
            "hull": s["hull"],
            "name": s["name"],
            "xy": xy(s),
            "targetxy": (s["targetx"], s["targety"]),
            "mission": s["mission"],
            "m1": s["m1"],
            "cloak": s["cloak"],
            "damage": s["damage"],
            "fuel": s["fuel"],
            "mass": s["mass"],
            "warp": s["warp"],
            "enemy": s["enemy"],
            "raw_turn": s["raw_turn"],
        })

print()
print("===== FOCUS 329: MITE 1185 STATE CHAIN =====")
for turn in range(53, 58):
    target = ship(turn, 329)
    mite = ship(turn, 1185)
    if target is None or mite is None:
        continue
    state, matches = waypoint_state(turn, 329, mite) if mite["mission"] == 7 and mite["m1"] == 329 else (None, [])
    print({
        "turn": turn,
        "target_xy": xy(target),
        "target_mission": target["mission"],
        "target_m1": target["m1"],
        "target_warp": target["warp"],
        "target_cloak": target["cloak"],
        "mite_xy": xy(mite),
        "mite_targetxy": (mite["targetx"], mite["targety"]),
        "mite_mission": mite["mission"],
        "mite_m1": mite["m1"],
        "mite_state": state,
        "matches": matches,
        "mite_age_from_raw_turn": None if mite["raw_turn"] is None else turn - mite["raw_turn"],
    })
