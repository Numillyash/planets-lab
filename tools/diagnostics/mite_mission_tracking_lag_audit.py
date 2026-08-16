from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

from planets_lab.corpus.archive import read_archive_member, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


GAME_ID = 591478
MITE_HULL_ID = 213
HORWASP_OWNER = 6

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
ship_groups = group_perspective_records(records, "ship")


# ---------------------------------------------------------------------------
# Static hull metadata from one original .trn member.
# This is only used to annotate whether a target hull can cloak.
# ---------------------------------------------------------------------------

members = turn_members(archive_data)
if not members:
    raise RuntimeError("archive contains no .trn members")

payload = read_archive_member(archive_data, members[0].name)
if payload[:2] == b"\x1f\x8b":
    payload = gzip.decompress(payload)
raw_first = json.loads(payload.decode("utf-8-sig"))

hull_meta = {
    _intish(row.get("id")): {
        "name": row.get("name"),
        "cancloak": row.get("cancloak"),
    }
    for row in raw_first.get("hulls", [])
    if isinstance(row, dict) and _intish(row.get("id")) is not None
}


# ---------------------------------------------------------------------------
# Owner-authoritative ship timeline.
# ---------------------------------------------------------------------------

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
        "readystatus": _intish(raw.get("readystatus")),
        "infoturn": _intish(raw.get("infoturn")),
        "raw_turn": _intish(raw.get("turn")),
        "warp": _intish(raw.get("warp")),
        "heading": _intish(raw.get("heading")),
    }


def ship(turn: int, ship_id: int):
    return ships.get((turn, ship_id))


def perspective_ship(turn: int, ship_id: int, player_id: int):
    group = ship_groups.get((turn, ship_id), ())
    for rec in group:
        if rec.player_id != player_id:
            continue
        raw = rec.raw
        return {
            "player": player_id,
            "x": _intish(raw.get("x")),
            "y": _intish(raw.get("y")),
            "mission": _intish(raw.get("mission")),
            "m1": _intish(raw.get("mission1target")),
            "cloak": raw.get("iscloaked"),
            "damage": _intish(raw.get("damage")),
            "infoturn": _intish(raw.get("infoturn")),
            "readystatus": _intish(raw.get("readystatus")),
        }
    return None


# ---------------------------------------------------------------------------
# Mite member events and target-turn clusters.
# ---------------------------------------------------------------------------

mite_seq = defaultdict(list)
for (turn, ship_id), state in ships.items():
    if state["hull"] == MITE_HULL_ID:
        mite_seq[ship_id].append(state)

for seq in mite_seq.values():
    seq.sort(key=lambda item: item["turn"])

member_events = []
cluster_members = defaultdict(list)

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

        if after["mission"] == 7 and after["m1"] == target:
            shape = "retained"
        elif after["mission"] == 0 and (after["m1"] is None or after["m1"] == 0):
            shape = "immediate_full_clear"
        elif after["mission"] == 7 and (after["m1"] is None or after["m1"] == 0):
            shape = "target_clear_pending"
        else:
            shape = f"other_{after['mission']}_{after['m1']}"

        event = {
            "mite": mite_id,
            "before_turn": before["turn"],
            "after_turn": after["turn"],
            "target": target,
            "shape": shape,
            "mite_before": before,
            "mite_after": after,
        }
        member_events.append(event)
        cluster_members[(before["turn"], after["turn"], target)].append(event)


# ---------------------------------------------------------------------------
# Helpers for target-history / Mite target-point lag.
# ---------------------------------------------------------------------------


def target_point(turn: int, target: int):
    s = ship(turn, target)
    if s is None or s["x"] is None or s["y"] is None:
        return None
    return (s["x"], s["y"])


def classify_target_point_lag(turn: int, target: int, point):
    if point is None or None in point:
        return "missing_point"

    matches = []
    for lag in range(0, 5):
        p = target_point(turn - lag, target)
        if p == point:
            matches.append(lag)

    if not matches:
        return "no_match_0_4"

    return "lag" + "/".join(str(lag) for lag in matches)


# ---------------------------------------------------------------------------
# Cluster-level clean population: same target incarnation and target visible
# before/after. We intentionally do NOT remove cloaking here because the point
# of this diagnostic is to inspect raw mission/cloak timing.
# ---------------------------------------------------------------------------

cluster_rows = []

for (before_turn, after_turn, target), members in cluster_members.items():
    shapes = {m["shape"] for m in members}
    if len(shapes) != 1:
        continue

    tb = ship(before_turn, target)
    ta = ship(after_turn, target)
    if tb is None or ta is None:
        continue
    if tb["hull"] != ta["hull"]:
        continue

    prev = ship(before_turn - 1, target)
    prev2 = ship(before_turn - 2, target)
    meta = hull_meta.get(tb["hull"], {})

    cluster_rows.append({
        "before_turn": before_turn,
        "after_turn": after_turn,
        "target": target,
        "shape": next(iter(shapes)),
        "members": members,
        "before": tb,
        "after": ta,
        "prev": prev,
        "prev2": prev2,
        "cancloak": meta.get("cancloak"),
        "hull_name": meta.get("name"),
    })


print()
print("===== TARGET RAW MISSION HISTORY OUTCOME TABLE =====")

mission_table = defaultdict(Counter)
for row in cluster_rows:
    prev_mission = None if row["prev"] is None else row["prev"]["mission"]
    key = (
        prev_mission,
        row["before"]["mission"],
        row["after"]["mission"],
        row["cancloak"],
        row["before"]["cloak"],
        row["after"]["cloak"],
    )
    mission_table[key][row["shape"]] += 1

for key, counts in sorted(mission_table.items(), key=lambda item: str(item[0])):
    if counts["immediate_full_clear"] == 0 and counts["target_clear_pending"] == 0:
        continue
    print(
        "prev_mission=%r before=%r after=%r cancloak=%r cloak=%r->%r "
        "retained=%d immediate=%d pending=%d"
        % (
            key[0], key[1], key[2], key[3], key[4], key[5],
            counts["retained"],
            counts["immediate_full_clear"],
            counts["target_clear_pending"],
        )
    )


print()
print("===== RAW MISSION 9 / PREVIOUS MISSION 9 CASES =====")

for row in sorted(cluster_rows, key=lambda r: (r["before_turn"], r["target"])):
    prev_mission = None if row["prev"] is None else row["prev"]["mission"]
    if row["before"]["mission"] != 9 and prev_mission != 9:
        continue

    b = row["before"]
    a = row["after"]
    p = row["prev"]

    print({
        "turn": (row["before_turn"], row["after_turn"]),
        "target": row["target"],
        "name": b["name"],
        "hull": b["hull"],
        "hull_name": row["hull_name"],
        "cancloak": row["cancloak"],
        "shape": row["shape"],
        "prev_mission": None if p is None else p["mission"],
        "mission": (b["mission"], a["mission"]),
        "cloak": (None if p is None else p["cloak"], b["cloak"], a["cloak"]),
        "damage": (None if p is None else p["damage"], b["damage"], a["damage"]),
        "mites": [m["mite"] for m in row["members"]],
    })


print()
print("===== MITE TARGET-POINT LAG × OUTCOME =====")

lag_table = defaultdict(Counter)
lag_examples = defaultdict(list)

for event in member_events:
    before = event["mite_before"]
    point = (before["targetx"], before["targety"])
    lag = classify_target_point_lag(
        event["before_turn"],
        event["target"],
        point,
    )
    lag_table[lag][event["shape"]] += 1

    if event["shape"] != "retained" or lag not in {"lag0", "lag0/1"}:
        lag_examples[(lag, event["shape"])].append(event)

for lag, counts in sorted(lag_table.items()):
    total = sum(counts.values())
    print(
        f"{lag:14s} total={total:4d} "
        f"retained={counts['retained']:4d} "
        f"immediate={counts['immediate_full_clear']:3d} "
        f"pending={counts['target_clear_pending']:3d}"
    )


print()
print("===== NONTRIVIAL LAG LOSS EXAMPLES =====")

for (lag, shape), events in sorted(lag_examples.items(), key=lambda item: str(item[0])):
    if shape == "retained":
        continue
    print()
    print(lag, shape, "count=", len(events))
    for event in events[:50]:
        b = event["mite_before"]
        print({
            "turn": (event["before_turn"], event["after_turn"]),
            "target": event["target"],
            "mite": event["mite"],
            "mite_xy": (b["x"], b["y"]),
            "mite_targetxy": (b["targetx"], b["targety"]),
            "target_t": target_point(event["before_turn"], event["target"]),
            "target_t1": target_point(event["before_turn"] - 1, event["target"]),
            "target_t2": target_point(event["before_turn"] - 2, event["target"]),
        })


print()
print("===== FOCUS 206 VS 522 TARGET / MITE TIMELINES =====")

focus = [
    (206, 1167, range(63, 69)),
    (522, 1082, range(76, 82)),
]

for target_id, mite_id, turns in focus:
    print()
    print("=" * 100)
    print("TARGET", target_id, "MITE", mite_id)
    print("=" * 100)

    for turn in turns:
        target = ship(turn, target_id)
        mite = ship(turn, mite_id)

        owner_view = perspective_ship(turn, target_id, ship(turn, target_id)["owner"] if ship(turn, target_id) else -1)
        hw_view = perspective_ship(turn, target_id, HORWASP_OWNER)

        print()
        print("turn", turn)
        print("  target_owner:", None if target is None else {
            "xy": (target["x"], target["y"]),
            "mission": target["mission"],
            "m1": target["m1"],
            "cloak": target["cloak"],
            "damage": target["damage"],
            "infoturn": target["infoturn"],
            "readystatus": target["readystatus"],
        })
        print("  owner_perspective_record:", owner_view)
        print("  horwasp_perspective_record:", hw_view)
        print("  mite:", None if mite is None else {
            "xy": (mite["x"], mite["y"]),
            "mission": mite["mission"],
            "m1": mite["m1"],
            "targetxy": (mite["targetx"], mite["targety"]),
            "targetxy_lag": classify_target_point_lag(
                turn,
                target_id,
                (mite["targetx"], mite["targety"]),
            ),
            "raw_turn": mite["raw_turn"],
            "warp": mite["warp"],
            "heading": mite["heading"],
        })


print()
print("===== FOUR CONTINUOUS UNEXPLAINED HISTORY =====")

for target_id, center in ((329, 56), (206, 66), (200, 75), (63, 94)):
    print()
    print("TARGET", target_id)
    for turn in range(center - 2, center + 2):
        s = ship(turn, target_id)
        if s is None:
            print(" ", turn, "MISSING")
            continue
        meta = hull_meta.get(s["hull"], {})
        print(
            " ",
            turn,
            {
                "xy": (s["x"], s["y"]),
                "hull": s["hull"],
                "hull_name": meta.get("name"),
                "cancloak": meta.get("cancloak"),
                "mission": s["mission"],
                "m1": s["m1"],
                "cloak": s["cloak"],
                "damage": s["damage"],
                "infoturn": s["infoturn"],
            },
        )
