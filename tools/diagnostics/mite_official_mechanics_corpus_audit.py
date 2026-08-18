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
SCAN_RANGE = 150.0
DOC_PURSUIT_TURNS = {9: 1, 7: 10, 6: 10, 3: None}

archive = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip").read_bytes()
prepared, hit = load_or_build_prepared_game_cache(
    archive,
    game_id=GAME_ID,
    cache_path=Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle"),
)
print("prepared_cache_hit:", hit)


def axis_delta(a, b):
    return ((b - a + PERIOD / 2) % PERIOD) - PERIOD / 2


def distance(a, b):
    if a is None or b is None:
        return None
    return hypot(axis_delta(a[0], b[0]), axis_delta(a[1], b[1]))


def exact(a, b):
    d = distance(a, b)
    return d is not None and d <= EPS


def build_owner_records(kind):
    groups = group_perspective_records(tuple(prepared.snapshots), kind)
    out = {}
    for (turn, rid), group in groups.items():
        owner, rec = _owner_record(group)
        if rec is None:
            continue
        out[(turn, rid)] = (owner, rec.raw)
    return out


ship_raw = build_owner_records("ship")
planet_raw = build_owner_records("planet")

ships = {}
for (turn, sid), (owner, raw) in ship_raw.items():
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
        "m2": _intish(raw.get("mission2target")),
        "enemy": _intish(raw.get("enemy")),
        "cloak": raw.get("iscloaked"),
        "damage": _intish(raw.get("damage")),
        "podcargo": _intish(raw.get("podcargo")),
        "mass": _intish(raw.get("mass")),
        "neutronium": _intish(raw.get("neutronium")),
    }

planets = {}
for (turn, pid), (owner, raw) in planet_raw.items():
    planets[(turn, pid)] = {
        "turn": turn,
        "id": pid,
        "owner": owner,
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
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


def tracking(mite, target_id):
    return (
        mite is not None
        and mite["hull"] == MITE_HULL_ID
        and mite["mission"] == 7
        and mite["m1"] == target_id
    )


def planets_near(turn, point, radius=0.0):
    out = []
    for (t, pid), p in planets.items():
        if t != turn:
            continue
        d = distance(point, xy(p))
        if d is not None and d <= radius + EPS:
            out.append((pid, p["owner"], round(d, 6)))
    return sorted(out)


def scan_support(turn, point, horwasp_owner, mite_id):
    same_owner_ship_distances = []
    other_ship_distances = []
    for (t, sid), s in ships.items():
        if t != turn or s["owner"] != horwasp_owner:
            continue
        d = distance(point, xy(s))
        if d is None:
            continue
        same_owner_ship_distances.append((d, sid, s["hull"], s["name"]))
        if sid != mite_id:
            other_ship_distances.append((d, sid, s["hull"], s["name"]))

    same_owner_planet_distances = []
    for (t, pid), p in planets.items():
        if t != turn or p["owner"] != horwasp_owner:
            continue
        d = distance(point, xy(p))
        if d is not None:
            same_owner_planet_distances.append((d, pid))

    same_owner_ship_distances.sort()
    other_ship_distances.sort()
    same_owner_planet_distances.sort()

    min_any_ship = same_owner_ship_distances[0] if same_owner_ship_distances else None
    min_other_ship = other_ship_distances[0] if other_ship_distances else None
    min_planet = same_owner_planet_distances[0] if same_owner_planet_distances else None

    candidates_including_self = []
    if min_any_ship is not None:
        candidates_including_self.append(min_any_ship[0])
    if min_planet is not None:
        candidates_including_self.append(min_planet[0])

    candidates_excluding_self = []
    if min_other_ship is not None:
        candidates_excluding_self.append(min_other_ship[0])
    if min_planet is not None:
        candidates_excluding_self.append(min_planet[0])

    return {
        "min_any_ship": min_any_ship,
        "min_other_ship": min_other_ship,
        "min_planet": min_planet,
        "within150_including_mite": bool(candidates_including_self) and min(candidates_including_self) <= SCAN_RANGE + EPS,
        "within150_excluding_mite": bool(candidates_excluding_self) and min(candidates_excluding_self) <= SCAN_RANGE + EPS,
    }


def outcome_after(turn, mite_id, target_id):
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


# Build continuous mission=7/m1=target runs for Red Mites.
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
        mite_start = ship(start, mite_id)
        mite_end = ship(end, mite_id)
        mite_after = ship(end + 1, mite_id)
        target_start = ship(start, target_id)
        target_anchor = ship(start - 1, target_id)
        target_end = ship(end, target_id)
        target_after = ship(end + 1, target_id)
        horwasp_owner = mite_start["owner"]

        row_details = []
        first_loss_like_anchor = None
        first_exact_contact = None
        first_visible_cloak = None
        first_scan_loss_excluding_mite = None
        for t in rr:
            m = ship(t, mite_id)
            target = ship(t, target_id)
            if target is None:
                continue
            anchor_hit = exact(wp(m), xy(target_anchor))
            target_eq_anchor = exact(xy(target), xy(target_anchor))
            loss_like_anchor = anchor_hit and not target_eq_anchor
            contact = exact(xy(m), xy(target))
            scan = scan_support(t, xy(target), horwasp_owner, mite_id)
            if loss_like_anchor and first_loss_like_anchor is None:
                first_loss_like_anchor = t
            if contact and first_exact_contact is None:
                first_exact_contact = t
            if target["cloak"] is True and first_visible_cloak is None:
                first_visible_cloak = t
            if not scan["within150_excluding_mite"] and first_scan_loss_excluding_mite is None:
                first_scan_loss_excluding_mite = t
            row_details.append({
                "turn": t,
                "mite_xy": xy(m),
                "mite_wp": wp(m),
                "mite_warp": m["warp"],
                "target_xy": xy(target),
                "target_cloak": target["cloak"],
                "target_planet": planets_near(t, xy(target), 0.0),
                "target_warpwell": planets_near(t, xy(target), 3.0),
                "exact_contact": contact,
                "loss_like_anchor": loss_like_anchor,
                "scan": scan,
            })

        end_scan = None if target_end is None else scan_support(end, xy(target_end), horwasp_owner, mite_id)
        anchor_planet = None if target_anchor is None else planets_near(start - 1, xy(target_anchor), 0.0)
        anchor_warpwell = None if target_anchor is None else planets_near(start - 1, xy(target_anchor), 3.0)
        start_planet = None if target_start is None else planets_near(start, xy(target_start), 0.0)
        start_warpwell = None if target_start is None else planets_near(start, xy(target_start), 3.0)

        start_warp = mite_start["warp"]
        doc_turns = DOC_PURSUIT_TURNS.get(start_warp, "unknown")
        length = len(rr)
        age_end = end - start

        target_damage_delta = None
        if target_end is not None and target_after is not None and target_end["damage"] is not None and target_after["damage"] is not None:
            target_damage_delta = target_after["damage"] - target_end["damage"]

        runs.append({
            "mite": mite_id,
            "target": target_id,
            "start": start,
            "end": end,
            "length": length,
            "age_end": age_end,
            "mite_owner": horwasp_owner,
            "mite_start_identity": ident(mite_start),
            "mite_start_raw_turn_eq_start": mite_start["raw_turn"] == start,
            "mite_start_warp": start_warp,
            "mite_warp_sequence": tuple(ship(t, mite_id)["warp"] for t in rr),
            "doc_pursuit_turns": doc_turns,
            "length_eq_doc": isinstance(doc_turns, int) and length == doc_turns,
            "age_eq_doc": isinstance(doc_turns, int) and age_end == doc_turns,
            "outcome": outcome_after(end, mite_id, target_id),
            "mite_after_exists": mite_after is not None,
            "mite_after_identity": ident(mite_after),
            "mite_same_identity_after": same_identity(mite_end, mite_after),
            "mite_after_hull": None if mite_after is None else mite_after["hull"],
            "mite_after_name": None if mite_after is None else mite_after["name"],
            "mite_after_raw_turn": None if mite_after is None else mite_after["raw_turn"],
            "mite_after_mission": None if mite_after is None else mite_after["mission"],
            "mite_after_m1": None if mite_after is None else mite_after["m1"],
            "anchor_exists": target_anchor is not None,
            "anchor_xy": xy(target_anchor),
            "target_start_xy": xy(target_start),
            "start_wp_eq_target": target_start is not None and exact(wp(mite_start), xy(target_start)),
            "target_anchor_same_identity_start": same_identity(target_anchor, target_start),
            "target_anchor_planet": anchor_planet,
            "target_anchor_warpwell": anchor_warpwell,
            "target_start_planet": start_planet,
            "target_start_warpwell": start_warpwell,
            "target_same_identity_after": same_identity(target_end, target_after),
            "target_end_cloak": None if target_end is None else target_end["cloak"],
            "target_after_cloak": None if target_after is None else target_after["cloak"],
            "target_damage_delta_end_after": target_damage_delta,
            "first_loss_like_anchor": first_loss_like_anchor,
            "first_exact_contact": first_exact_contact,
            "first_visible_cloak": first_visible_cloak,
            "first_scan_loss_excluding_mite": first_scan_loss_excluding_mite,
            "end_scan": end_scan,
            "rows": row_details,
        })

print("\n===== OFFICIAL-MECHANICS RUN SUMMARY =====")
print("run_count=", len(runs))
print("start_warp=", Counter(r["mite_start_warp"] for r in runs))
print("start_warp_x_length=", Counter((r["mite_start_warp"], r["length"]) for r in runs))
print("start_warp_x_outcome=", Counter((r["mite_start_warp"], r["outcome"]) for r in runs))
print("doc_length_alignment=", Counter((r["mite_start_warp"], r["length_eq_doc"], r["age_eq_doc"]) for r in runs))
print("outcome=", Counter(r["outcome"] for r in runs))
print("first_visible_cloak_present=", Counter(r["first_visible_cloak"] is not None for r in runs))
print("first_exact_contact_present=", Counter(r["first_exact_contact"] is not None for r in runs))
print("first_scan_loss_excluding_mite_present=", Counter(r["first_scan_loss_excluding_mite"] is not None for r in runs))
print("first_loss_like_anchor_present=", Counter(r["first_loss_like_anchor"] is not None for r in runs))

print("\n===== LAUNCH-BOUNDARY PLANET / WARPWELL =====")
print("anchor_at_planet=", Counter(bool(r["target_anchor_planet"]) for r in runs))
print("anchor_in_warpwell=", Counter(bool(r["target_anchor_warpwell"]) for r in runs))
print("start_target_at_planet=", Counter(bool(r["target_start_planet"]) for r in runs))
print("start_target_in_warpwell=", Counter(bool(r["target_start_warpwell"]) for r in runs))
print("anchor_not_planet_to_start_planet=", Counter(
    (not bool(r["target_anchor_planet"])) and bool(r["target_start_planet"])
    for r in runs
))

print("\n===== SAME-IDENTITY IMMEDIATE CLEAR =====")
clear = [r for r in runs if r["outcome"] == "immediate_full_clear" and r["target_same_identity_after"]]
print("run_count=", len(clear))
print("start_warp=", Counter(r["mite_start_warp"] for r in clear))
print("length=", Counter(r["length"] for r in clear))
print("visible_cloak=", Counter(r["first_visible_cloak"] is not None for r in clear))
print("exact_contact=", Counter(r["first_exact_contact"] is not None for r in clear))
print("scan_loss_excluding_mite=", Counter(r["first_scan_loss_excluding_mite"] is not None for r in clear))
print("loss_like_anchor=", Counter(r["first_loss_like_anchor"] is not None for r in clear))
print("branch_signature=", Counter((
    r["first_visible_cloak"] is not None,
    r["first_exact_contact"] is not None,
    r["first_scan_loss_excluding_mite"] is not None,
    r["first_loss_like_anchor"] is not None,
) for r in clear))

print("\n===== MITE AFTER RUN / SELF-DESTRUCT OBSERVABILITY =====")
print("after_exists=", Counter(r["mite_after_exists"] for r in runs))
print("same_identity_after=", Counter(r["mite_same_identity_after"] for r in runs))
print("clear_same_identity_after=", Counter(r["mite_same_identity_after"] for r in clear))
print("contact_clear_same_identity_after=", Counter(r["mite_same_identity_after"] for r in clear if r["first_exact_contact"] is not None))

print("\n===== DOCUMENTED-BRANCH OUTLIERS: SAME-IDENTITY CLEAR =====")
outliers = [
    r for r in clear
    if r["first_visible_cloak"] is None
    and r["first_exact_contact"] is None
    and r["first_scan_loss_excluding_mite"] is None
]
print("count=", len(outliers))
for r in outliers:
    print({k: v for k, v in r.items() if k != "rows"})

print("\n===== FOCUS 206 / 329 / 380 =====")
for r in runs:
    if r["target"] in {206, 329, 380}:
        print({k: v for k, v in r.items() if k != "rows"})
        for row in r["rows"]:
            print("  ", row)

print("\nNOTE: official reference says Red Mite delivers one minehit on successful interception,")
print("cannot target/track cloaked ships, loses lock outside 150ly scan of any Horwasp ship/planet,")
print("and pursuit lifetime depends on launch speed (warp9=1, warp7/6=10, warp3=unlimited).")
print("This diagnostic tests observable correspondence only; it does not assume field/phase semantics.")
print("Scan is reported both including and excluding the tracked Mite itself.")
print("period=2170 remains scoped to game 591478.")
