from __future__ import annotations

from collections import defaultdict
from math import hypot
from pathlib import Path

import duckdb

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

ARCHIVE_PATH = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")
PREPARED_PATH = Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle")
DB_PATH = Path("validation/corpus/compiled/v1/corpus.duckdb")


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
        "warp": _intish(raw.get("warp")),
        "heading": _intish(raw.get("heading")),
        "mission": _intish(raw.get("mission")),
        "m1": _intish(raw.get("mission1target")),
        "m2": _intish(raw.get("mission2target")),
        "raw_turn": _intish(raw.get("turn")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
        "fuel": _intish(raw.get("neutronium")),
        "transfer_id": _intish(raw.get("transfertargetid")),
        "transfer_type": _intish(raw.get("transfertargettype")),
        "fc": raw.get("friendlycode"),
        "raw": raw,
    }


def ship(turn, ship_id):
    return ships.get((turn, ship_id))


planets = {}

for (kind, turn, planet_id), entity in entities.items():
    if kind != "planet":
        continue

    point = exy(entity)
    if point is None:
        continue

    planets[(turn, planet_id)] = {
        "turn": turn,
        "id": planet_id,
        "owner": iv(entity, "ownerid"),
        "clans": iv(entity, "clans"),
        "nativeclans": iv(entity, "nativeclans"),
        "xy": point,
    }


def planet(turn, planet_id):
    return planets.get((turn, planet_id))


def nearest_planet(point, turn, owner=None):
    best = None

    for (t, _pid), p in planets.items():
        if t != turn:
            continue
        if owner is not None and p["owner"] != owner:
            continue

        d = distance(point, p["xy"])
        if best is None or d < best["distance"]:
            best = {**p, "distance": d}

    return best


# Schema-tolerant read: the compiled corpus schema evolves during reverse engineering.
con = duckdb.connect(str(DB_PATH), read_only=True)


def table_columns(name: str) -> set[str]:
    return {
        row[1]
        for row in con.execute(
            f"PRAGMA table_info('{name}')"
        ).fetchall()
    }


def optional_col(alias: str, columns: set[str], name: str) -> str:
    if name in columns:
        return f"{alias}.{name}"
    return "NULL"


t_cols = table_columns("movement_transitions")
l_cols = table_columns("movement_context_labels")

print()
print("movement_transitions columns:")
print(sorted(t_cols))
print()
print("movement_context_labels columns:")
print(sorted(l_cols))

movement_context = {}

query = f"""
    SELECT
        t.before_archive_turn,
        t.after_archive_turn,
        t.ship_id,
        {optional_col('t', t_cols, 'intent_class')} AS intent_class,
        {optional_col('t', t_cols, 'baseline_category')} AS baseline_category,
        {optional_col('t', t_cols, 'external_category')} AS external_category,
        {optional_col('l', l_cols, 'chunnel_category')} AS chunnel_category,
        {optional_col('l', l_cols, 'chunnel_explained')} AS chunnel_explained,
        {optional_col('l', l_cols, 'horwasp_category')} AS horwasp_category,
        {optional_col('l', l_cols, 'horwasp_explained')} AS horwasp_explained
    FROM movement_transitions t
    LEFT JOIN movement_context_labels l
      ON l.game_id = t.game_id
     AND l.before_archive_turn = t.before_archive_turn
     AND l.after_archive_turn = t.after_archive_turn
     AND l.ship_id = t.ship_id
    WHERE t.game_id = ?
"""

for row in con.execute(query, [GAME_ID]).fetchall():
    movement_context[(row[0], row[1], row[2])] = {
        "intent": row[3],
        "baseline": row[4],
        "external": row[5],
        "chunnel_category": row[6],
        "chunnel_explained": row[7],
        "horwasp_category": row[8],
        "horwasp_explained": row[9],
    }

con.close()


mite_seq = defaultdict(list)

for (turn, ship_id), s in ships.items():
    if s["hull"] != 213:
        continue
    mite_seq[ship_id].append(s)

for seq in mite_seq.values():
    seq.sort(key=lambda s: s["turn"])


clusters = defaultdict(list)

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

        clusters[(before["turn"], after["turn"], before["owner"], target)].append(
            {
                "mite": mite_id,
                "shape": shape,
                "mite_before": before,
                "mite_after": after,
            }
        )


cluster_rows = []

for (before_turn, after_turn, mite_owner, target), members in clusters.items():
    shapes = {m["shape"] for m in members}
    if len(shapes) != 1:
        continue

    shape = next(iter(shapes))
    tb = ship(before_turn, target)
    ta = ship(after_turn, target)

    if tb is None or ta is None:
        continue

    same_hull = tb["hull"] == ta["hull"]
    before_xy = (tb["x"], tb["y"])
    after_xy = (ta["x"], ta["y"])

    pb = nearest_planet(before_xy, before_turn)
    phb = nearest_planet(before_xy, before_turn, HORWASP_OWNER)

    exact_any = pb is not None and pb["distance"] == 0
    exact_hw = phb is not None and phb["distance"] == 0

    left_same = False
    same_planet_after = None

    if exact_any:
        same_planet_after = planet(after_turn, pb["id"])
        if same_planet_after is not None:
            d = distance(after_xy, same_planet_after["xy"])
            left_same = d > 3

    cluster_rows.append(
        {
            "before_turn": before_turn,
            "after_turn": after_turn,
            "owner": mite_owner,
            "target": target,
            "members": members,
            "shape": shape,
            "before": tb,
            "after": ta,
            "same_hull": same_hull,
            "planet_before": pb,
            "hw_planet_before": phb,
            "exact_any": exact_any,
            "exact_hw": exact_hw,
            "left_same": left_same,
            "same_planet_after": same_planet_after,
            "movement": movement_context.get((before_turn, after_turn, target)),
        }
    )


print()
print("===== ALL EXACT HORWASP PLANET CASES =====")

exact_hw_rows = [
    row
    for row in cluster_rows
    if row["same_hull"] and row["exact_hw"]
]

for row in sorted(exact_hw_rows, key=lambda r: (r["before_turn"], r["target"])):
    b = row["before"]
    a = row["after"]
    p = row["hw_planet_before"]
    p_after = planet(row["after_turn"], p["id"])

    print()
    print("=" * 90)
    print(
        f"turn={row['before_turn']}->{row['after_turn']} "
        f"target={row['target']} {b['name']} shape={row['shape']}"
    )
    print("  mites:", [m["mite"] for m in row["members"]])
    print(
        "  target_before:",
        {
            "owner": b["owner"],
            "hull": b["hull"],
            "xy": (b["x"], b["y"]),
            "warp": b["warp"],
            "mission": b["mission"],
            "m1": b["m1"],
            "cloak": b["cloak"],
            "damage": b["damage"],
            "podcargo": b["podcargo"],
            "fuel": b["fuel"],
            "transfer_id": b["transfer_id"],
            "transfer_type": b["transfer_type"],
            "fc": b["fc"],
        },
    )
    print(
        "  target_after:",
        {
            "xy": (a["x"], a["y"]),
            "warp": a["warp"],
            "mission": a["mission"],
            "m1": a["m1"],
            "cloak": a["cloak"],
            "damage": a["damage"],
            "podcargo": a["podcargo"],
            "fuel": a["fuel"],
            "transfer_id": a["transfer_id"],
            "transfer_type": a["transfer_type"],
            "fc": a["fc"],
        },
    )
    print("  planet_before:", p)
    print("  planet_after:", p_after)
    print(
        "  planet_owner_transition:",
        (p["owner"], None if p_after is None else p_after["owner"]),
    )
    print(
        "  planet_clans_transition:",
        (p["clans"], None if p_after is None else p_after["clans"]),
    )
    print("  left_same_planet:", row["left_same"])
    print("  movement:", row["movement"])


print()
print("===== EXACT HW + LEAVES SAME PLANET MATCHED PAIR =====")

matched = [row for row in exact_hw_rows if row["left_same"]]

for row in sorted(matched, key=lambda r: r["before_turn"]):
    b = row["before"]
    a = row["after"]
    p = row["hw_planet_before"]
    pa = planet(row["after_turn"], p["id"])

    print()
    print(
        f"{row['before_turn']}->{row['after_turn']} "
        f"target={row['target']} {b['name']} shape={row['shape']}"
    )
    print(
        "  transition:",
        {
            "xy": ((b["x"], b["y"]), (a["x"], a["y"])),
            "mission": (b["mission"], a["mission"]),
            "damage": (b["damage"], a["damage"]),
            "podcargo": (b["podcargo"], a["podcargo"]),
            "fuel": (b["fuel"], a["fuel"]),
            "transfer": (
                (b["transfer_type"], b["transfer_id"]),
                (a["transfer_type"], a["transfer_id"]),
            ),
        },
    )
    print(
        "  planet:",
        {
            "id": p["id"],
            "owner": (p["owner"], None if pa is None else pa["owner"]),
            "clans": (p["clans"], None if pa is None else pa["clans"]),
        },
    )


print()
print("===== ALL NEW-INFECTION TARGET CLUSTERS =====")

for row in sorted(cluster_rows, key=lambda r: (r["before_turn"], r["target"])):
    if not row["same_hull"]:
        continue

    b = row["before"]
    a = row["after"]

    before_pod = b["podcargo"] or 0
    after_pod = a["podcargo"] or 0

    if not (before_pod == 0 and after_pod > 0):
        continue

    movement = row["movement"] or {}

    if b["cloak"] is True:
        known_reason = "cloak_before"
    elif b["cloak"] is False and a["cloak"] is True:
        known_reason = "cloak_false_to_true"
    elif movement.get("chunnel_explained") is True:
        known_reason = "target_chunnel"
    else:
        known_reason = "none_of_current_strong"

    print()
    print(
        f"turn={row['before_turn']}->{row['after_turn']} "
        f"target={row['target']} {b['name']} "
        f"shape={row['shape']} reason={known_reason}"
    )
    print(
        "  target:",
        {
            "owner": b["owner"],
            "hull": b["hull"],
            "xy": ((b["x"], b["y"]), (a["x"], a["y"])),
            "mission": (b["mission"], a["mission"]),
            "cloak": (b["cloak"], a["cloak"]),
            "damage": (b["damage"], a["damage"]),
            "podcargo": (before_pod, after_pod),
            "transfer": (
                (b["transfer_type"], b["transfer_id"]),
                (a["transfer_type"], a["transfer_id"]),
            ),
        },
    )
    print("  nearest_planet_before:", row["planet_before"])
    print("  nearest_hw_before:", row["hw_planet_before"])
    print("  movement:", row["movement"])
    print(
        "  mites:",
        [
            (m["mite"], m["mite_before"]["raw_turn"])
            for m in row["members"]
        ],
    )


print()
print("===== MATCHED PAIR TIMELINES =====")

focus_targets = {row["target"] for row in matched}

for target_id in sorted(focus_targets):
    relevant = [row for row in matched if row["target"] == target_id]
    center = relevant[0]["before_turn"]

    print()
    print("=" * 100)
    print("TARGET", target_id, relevant[0]["before"]["name"])
    print("=" * 100)

    for turn in range(center - 2, center + 3):
        s = ship(turn, target_id)
        if s is None:
            continue

        p = nearest_planet((s["x"], s["y"]), turn)
        hp = nearest_planet((s["x"], s["y"]), turn, HORWASP_OWNER)

        print(
            f"turn={turn} "
            f"xy=({s['x']},{s['y']}) "
            f"mission={s['mission']} "
            f"cloak={s['cloak']} "
            f"damage={s['damage']} "
            f"podcargo={s['podcargo']} "
            f"fuel={s['fuel']} "
            f"transfer=({s['transfer_type']},{s['transfer_id']}) "
            f"nearest={p} nearest_hw={hp}"
        )
