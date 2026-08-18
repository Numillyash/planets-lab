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
LOOKAHEAD = 6

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
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
        "mass": _intish(raw.get("mass")),
        "neutronium": _intish(raw.get("neutronium")),
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
        if mite_clear is None:
            continue
        if mite_clear["mission"] != 0 or mite_clear["m1"] not in (None, 0):
            continue
        if not same_identity(mite_end, mite_clear):
            continue
        if not same_identity(target_end, target_after):
            continue

        visible_cloak_turns = []
        contact_turns = []
        for t in rr:
            m = ship(t, mite_id)
            target = ship(t, target_id)
            if target is None:
                continue
            if target["cloak"] is True:
                visible_cloak_turns.append(t)
            if exact(xy(m), xy(target)):
                contact_turns.append(t)

        if contact_turns:
            branch = "exact_contact"
        elif visible_cloak_turns:
            branch = "visible_cloak"
        else:
            branch = "unexplained"

        base_ident = ident(mite_end)
        lifecycle = []
        first_absent_offset = None
        first_changed_identity_offset = None
        for offset in range(0, LOOKAHEAD + 1):
            t = end + offset
            m = ship(t, mite_id)
            target = ship(t, target_id)
            same = m is not None and ident(m) == base_ident
            if m is None and first_absent_offset is None:
                first_absent_offset = offset
            if m is not None and not same and first_changed_identity_offset is None:
                first_changed_identity_offset = offset
            lifecycle.append({
                "offset_from_end": offset,
                "turn": t,
                "mite_exists": m is not None,
                "mite_same_identity": same,
                "mite_identity": ident(m),
                "mite_xy": xy(m),
                "mite_wp": wp(m),
                "mite_warp": None if m is None else m["warp"],
                "mite_mission": None if m is None else m["mission"],
                "mite_m1": None if m is None else m["m1"],
                "target_exists": target is not None,
                "target_identity": ident(target),
                "target_xy": xy(target),
                "target_cloak": None if target is None else target["cloak"],
                "target_damage": None if target is None else target["damage"],
                "target_podcargo": None if target is None else target["podcargo"],
                "target_mass": None if target is None else target["mass"],
                "target_neutronium": None if target is None else target["neutronium"],
                "exact_contact": exact(xy(m), xy(target)),
            })

        same_identity_offsets = [
            row["offset_from_end"] for row in lifecycle if row["mite_same_identity"]
        ]
        last_same_identity_offset = max(same_identity_offsets) if same_identity_offsets else None

        runs.append({
            "mite": mite_id,
            "target": target_id,
            "start": start,
            "end": end,
            "length": len(rr),
            "branch": branch,
            "visible_cloak_turns": tuple(visible_cloak_turns),
            "contact_turns": tuple(contact_turns),
            "base_identity": base_ident,
            "clear_turn": end + 1,
            "clear_xy": xy(mite_clear),
            "clear_wp": wp(mite_clear),
            "clear_warp": mite_clear["warp"],
            "first_absent_offset": first_absent_offset,
            "first_changed_identity_offset": first_changed_identity_offset,
            "last_same_identity_offset": last_same_identity_offset,
            "lifecycle": lifecycle,
        })

print("\n===== SAME-IDENTITY IMMEDIATE-CLEAR POSTSTATE SUMMARY =====")
print("run_count=", len(runs))
print("branch=", Counter(r["branch"] for r in runs))
print("first_absent_offset=", Counter((r["branch"], r["first_absent_offset"]) for r in runs))
print("first_changed_identity_offset=", Counter((r["branch"], r["first_changed_identity_offset"]) for r in runs))
print("last_same_identity_offset=", Counter((r["branch"], r["last_same_identity_offset"]) for r in runs))

print("\n===== BRANCH REPRESENTATIVES =====")
for branch in ("exact_contact", "unexplained", "visible_cloak"):
    subset = [r for r in runs if r["branch"] == branch]
    print(f"-- {branch}: count={len(subset)} --")
    for r in subset[:6]:
        print({k: v for k, v in r.items() if k != "lifecycle"})
        for row in r["lifecycle"]:
            print("  ", row)

print("\n===== FOCUS 206 / 329 / 380 =====")
for r in runs:
    if r["target"] in {206, 329, 380}:
        print({k: v for k, v in r.items() if k != "lifecycle"})
        for row in r["lifecycle"]:
            print("  ", row)

print("\nNOTE: offsets are relative to the last active tracking snapshot end.")
print("offset=1 is the observed mission=0/m1=0 clear snapshot.")
print("Identity uses owner, hull, name, and raw ship turn; numeric IDs may be reused.")
print("period=2170 remains scoped to game 591478.")
