from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path

from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _resolved_value,
)
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


GAME_ID = 591478
HORWASP_OWNER = 6
PLANET_WELL_RADIUS = 3.0
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

records = tuple(prepared.snapshots)
groups = group_perspective_records(records, "ship")
entities = _entity_map(records)
topology = extract_map_topology(archive_data)


def rv(entity, field):
    if entity is None:
        return None
    try:
        return _resolved_value(entity, field)
    except Exception:
        return None


def iv(entity, field):
    return _intish(rv(entity, field))


def exy(entity):
    if entity is None:
        return None
    x = iv(entity, "x")
    y = iv(entity, "y")
    if x is None or y is None:
        return None
    return (x, y)


def distance(a, b):
    dx, dy = _vector(a, b, topology)
    return hypot(dx, dy)


ships = {}
for (turn, ship_id), group in groups.items():
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
        "raw_turn": _intish(raw.get("turn")),
        "warp": _intish(raw.get("warp")),
        "heading": _intish(raw.get("heading")),
        "infoturn": _intish(raw.get("infoturn")),
        "readystatus": _intish(raw.get("readystatus")),
    }


def ship(turn, ship_id):
    return ships.get((turn, ship_id))


planets = defaultdict(list)
for (kind, turn, planet_id), entity in entities.items():
    if kind != "planet":
        continue
    point = exy(entity)
    if point is None:
        continue
    planets[turn].append({
        "id": planet_id,
        "owner": iv(entity, "ownerid"),
        "clans": iv(entity, "clans"),
        "xy": point,
    })


def nearest_planet(point, turn, owner=None):
    best = None
    for p in planets.get(turn, ()):
        if owner is not None and p["owner"] != owner:
            continue
        d = distance(point, p["xy"])
        if best is None or d < best["distance"]:
            best = {**p, "distance": d}
    return best


def target_xy(turn, target_id):
    s = ship(turn, target_id)
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def waypoint_matches(turn, target_id, waypoint):
    matches = []
    if waypoint is None:
        return matches
    for lag in range(MAX_LAG + 1):
        p = target_xy(turn - lag, target_id)
        if p is not None and p == waypoint:
            matches.append(lag)
    return matches


def strict_waypoint_state(turn, target_id, mite_state):
    waypoint = (mite_state["targetx"], mite_state["targety"])
    if waypoint[0] is None or waypoint[1] is None:
        return "missing_waypoint", []
    matches = waypoint_matches(turn, target_id, waypoint)
    if 0 in matches:
        return "current", matches
    if matches:
        return f"strict_stale_{min(matches)}", matches
    return "no_match_0_4", matches


def outcome(before, after, target):
    if after is None:
        return "missing_after"
    if after["mission"] == 7 and after["m1"] == target:
        return "retained"
    if after["mission"] == 0 and (after["m1"] is None or after["m1"] == 0):
        return "immediate_full_clear"
    if after["mission"] == 7 and (after["m1"] is None or after["m1"] == 0):
        return "target_clear_pending"
    return f"other_{after['mission']}_{after['m1']}"


mite_sequences = defaultdict(list)
for (turn, ship_id), s in ships.items():
    if s["hull"] == 213:
        mite_sequences[ship_id].append(s)
for seq in mite_sequences.values():
    seq.sort(key=lambda s: s["turn"])

member_rows = []
for mite_id, seq in mite_sequences.items():
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
        state, matches = strict_waypoint_state(before["turn"], target, before)
        member_rows.append({
            "mite": mite_id,
            "before_turn": before["turn"],
            "after_turn": after["turn"],
            "target": target,
            "state": state,
            "matches": matches,
            "shape": outcome(before, after, target),
            "mite_before": before,
            "mite_after": after,
            "target_before": tb,
            "target_after": ta,
        })

print()
print("===== STRICT WAYPOINT STATE × OUTCOME (MEMBER LEVEL) =====")
member_table = defaultdict(Counter)
for row in member_rows:
    member_table[row["state"]][row["shape"]] += 1
for state, c in sorted(member_table.items()):
    print(
        f"{state:18s} total={sum(c.values()):4d} "
        f"retained={c['retained']:4d} "
        f"immediate={c['immediate_full_clear']:3d} "
        f"pending={c['target_clear_pending']:3d}"
    )

clusters = defaultdict(list)
for row in member_rows:
    clusters[(row["before_turn"], row["after_turn"], row["target"])].append(row)

print()
print("===== STRICT WAYPOINT STATE × OUTCOME (TARGET-TURN CLUSTER LEVEL) =====")
cluster_table = defaultdict(Counter)
for key, rows in clusters.items():
    shapes = {r["shape"] for r in rows}
    if len(shapes) != 1:
        continue
    shape = next(iter(shapes))
    states = {r["state"] for r in rows}
    if all(s == "current" for s in states):
        cluster_state = "all_current"
    elif all(s.startswith("strict_stale_") for s in states):
        cluster_state = "all_strict_stale"
    elif any(s.startswith("strict_stale_") for s in states):
        cluster_state = "mixed_with_stale"
    elif states == {"no_match_0_4"}:
        cluster_state = "all_no_match"
    else:
        cluster_state = "+".join(sorted(states))
    cluster_table[cluster_state][shape] += 1
for state, c in sorted(cluster_table.items()):
    print(
        f"{state:22s} total={sum(c.values()):4d} "
        f"retained={c['retained']:4d} "
        f"immediate={c['immediate_full_clear']:3d} "
        f"pending={c['target_clear_pending']:3d}"
    )

rows_by_mite_turn = {(r["mite"], r["before_turn"]): r for r in member_rows}

onsets = []
for row in member_rows:
    if not row["state"].startswith("strict_stale_"):
        continue
    prev = rows_by_mite_turn.get((row["mite"], row["before_turn"] - 1))
    if prev is None:
        onset_kind = "first_observed_stale"
    elif prev["target"] != row["target"]:
        onset_kind = "target_changed"
    elif prev["state"] == "current":
        onset_kind = "current_to_stale"
    elif prev["state"].startswith("strict_stale_"):
        onset_kind = "already_stale"
    else:
        onset_kind = f"from_{prev['state']}"
    onsets.append({**row, "onset_kind": onset_kind, "prev_row": prev})

print()
print("===== STALE ONSET SUMMARY =====")
summary = defaultdict(Counter)
for row in onsets:
    summary[row["onset_kind"]][row["shape"]] += 1
for kind, c in sorted(summary.items()):
    print(
        f"{kind:22s} total={sum(c.values()):4d} "
        f"retained={c['retained']:4d} "
        f"immediate={c['immediate_full_clear']:3d} "
        f"pending={c['target_clear_pending']:3d}"
    )


def context_for_onset(row):
    turn = row["before_turn"]
    target = row["target"]
    tb = ship(turn, target)
    tp = ship(turn - 1, target)
    if tb is None:
        return None
    now_xy = (tb["x"], tb["y"])
    prev_xy = None if tp is None else (tp["x"], tp["y"])
    p_now = nearest_planet(now_xy, turn)
    hp_now = nearest_planet(now_xy, turn, HORWASP_OWNER)
    p_prev = None if prev_xy is None else nearest_planet(prev_xy, turn - 1)
    hp_prev = None if prev_xy is None else nearest_planet(prev_xy, turn - 1, HORWASP_OWNER)
    moved = None if prev_xy is None else distance(prev_xy, now_xy)
    return {
        "target_transition": None if tp is None else {
            "xy": (prev_xy, now_xy),
            "distance": moved,
            "mission": (tp["mission"], tb["mission"]),
            "cloak": (tp["cloak"], tb["cloak"]),
            "damage": (tp["damage"], tb["damage"]),
            "podcargo": (tp["podcargo"], tb["podcargo"]),
        },
        "planet_prev": p_prev,
        "planet_now": p_now,
        "hw_planet_prev": hp_prev,
        "hw_planet_now": hp_now,
        "entered_any_well": (
            p_prev is not None
            and p_now is not None
            and p_prev["distance"] > PLANET_WELL_RADIUS
            and p_now["distance"] <= PLANET_WELL_RADIUS
        ),
        "entered_hw_well": (
            hp_prev is not None
            and hp_now is not None
            and hp_prev["distance"] > PLANET_WELL_RADIUS
            and hp_now["distance"] <= PLANET_WELL_RADIUS
        ),
    }

print()
print("===== CURRENT -> STRICT-STALE ONSETS =====")
for row in sorted(
    (r for r in onsets if r["onset_kind"] == "current_to_stale"),
    key=lambda r: (r["before_turn"], r["target"], r["mite"]),
):
    ctx = context_for_onset(row)
    mb = row["mite_before"]
    print()
    print(
        f"turn={row['before_turn']} target={row['target']} "
        f"{row['target_before']['name']} mite={row['mite']} "
        f"state={row['state']} matches={row['matches']} "
        f"next_outcome={row['shape']}"
    )
    print(
        "  mite:",
        {
            "xy": (mb["x"], mb["y"]),
            "targetxy": (mb["targetx"], mb["targety"]),
            "mission": mb["mission"],
            "m1": mb["m1"],
            "raw_turn": mb["raw_turn"],
            "heading": mb["heading"],
        },
    )
    print("  context:", ctx)

print()
print("===== ONSET FEATURE COUNTS =====")
feature_counts = defaultdict(Counter)
for row in onsets:
    if row["onset_kind"] != "current_to_stale":
        continue
    ctx = context_for_onset(row)
    if ctx is None or ctx["target_transition"] is None:
        continue
    tr = ctx["target_transition"]
    features = {
        "cloak_before": tr["cloak"][0] is True,
        "cloak_after": tr["cloak"][1] is True,
        "mission9_before": tr["mission"][0] == 9,
        "mission9_after": tr["mission"][1] == 9,
        "damage_increased": (
            tr["damage"][0] is not None
            and tr["damage"][1] is not None
            and tr["damage"][1] > tr["damage"][0]
        ),
        "new_podcargo": (
            (tr["podcargo"][0] or 0) == 0
            and (tr["podcargo"][1] or 0) > 0
        ),
        "entered_any_well": ctx["entered_any_well"],
        "entered_hw_well": ctx["entered_hw_well"],
    }
    for name, value in features.items():
        if value:
            feature_counts[name][row["shape"]] += 1
for name, c in sorted(feature_counts.items()):
    print(
        f"{name:20s} total={sum(c.values()):3d} "
        f"retained={c['retained']:3d} "
        f"immediate={c['immediate_full_clear']:3d} "
        f"pending={c['target_clear_pending']:3d}"
    )

print()
print("===== FOCUS 206 / 329 STALE ONSET TIMELINES =====")
for target_id in (206, 329):
    print()
    print("=" * 100)
    print("TARGET", target_id)
    print("=" * 100)
    target_member_rows = sorted(
        (r for r in member_rows if r["target"] == target_id),
        key=lambda r: (r["before_turn"], r["mite"]),
    )
    for r in target_member_rows:
        if target_id == 206 and not (64 <= r["before_turn"] <= 67):
            continue
        if target_id == 329 and not (53 <= r["before_turn"] <= 57):
            continue
        mb = r["mite_before"]
        tb = r["target_before"]
        print(
            f"turn={r['before_turn']} mite={r['mite']} "
            f"target_xy=({tb['x']},{tb['y']}) "
            f"target_mission={tb['mission']} cloak={tb['cloak']} "
            f"damage={tb['damage']} podcargo={tb['podcargo']} "
            f"mite_targetxy=({mb['targetx']},{mb['targety']}) "
            f"state={r['state']} matches={r['matches']} "
            f"outcome={r['shape']}"
        )

print()
print("===== CONTROL: ENTERING PLANET WELL WHILE MITE ACTIVE =====")
control = Counter()
examples = defaultdict(list)
for row in member_rows:
    turn = row["before_turn"]
    target = row["target"]
    tb = ship(turn, target)
    tp = ship(turn - 1, target)
    if tb is None or tp is None:
        continue
    p_now = nearest_planet((tb["x"], tb["y"]), turn)
    p_prev = nearest_planet((tp["x"], tp["y"]), turn - 1)
    if p_now is None or p_prev is None:
        continue
    entered = p_prev["distance"] > PLANET_WELL_RADIUS and p_now["distance"] <= PLANET_WELL_RADIUS
    if not entered:
        continue
    key = (row["state"], row["shape"])
    control[key] += 1
    if len(examples[key]) < 20:
        examples[key].append({
            "turn": turn,
            "target": target,
            "name": tb["name"],
            "mite": row["mite"],
            "state": row["state"],
            "shape": row["shape"],
            "planet_now": p_now,
            "mission": (tp["mission"], tb["mission"]),
            "cloak": (tp["cloak"], tb["cloak"]),
            "damage": (tp["damage"], tb["damage"]),
            "podcargo": (tp["podcargo"], tb["podcargo"]),
        })
for key, n in sorted(control.items(), key=lambda item: (item[0][0], item[0][1])):
    print(f"state={key[0]:18s} outcome={key[1]:22s} n={n}")
    for e in examples[key]:
        print("  ", e)
