"""Frozen 424-side late-turn mass residual audit, NOT a combat predictor.

Factual VCR fields are used only as observational comparisons. The historical
T-1 owner ship/clan/engine and hull catalog are independently read before
summarizing phase hypotheses. No +360, Horwasp or SG rule is promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, member_refs_for_turns,
    reconstruct_members,
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns

SCHEMA = "planets-lab.combat-mass-late-residual-prestate-audit.v1"
SOURCE_SCHEMA = "planets-lab.combat-mass-independent-late-turn-stress.v1"
SOURCE_STATUS = "INDEPENDENT_LATE_TURN_STRESS_OBSERVATIONAL_NOT_PROMOTED"
DB_GENERATION = "generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
DB_SHA256 = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
FROZEN_STRESS_REPORT_GIT_BLOB = "b6a373e4ea9f6274f9169c8e8aad4db7cc5e2f2e"
SG_BONUS_BY_ENGINE = {1: 1, 2: 1, 3: 2, 4: 2, 5: 13, 6: 27, 7: 85, 8: 100, 9: 150}


def integer(x: Any) -> int | None:
    return x if type(x) is int else None


def progress(s: str) -> None:
    print(f"[late-phase] {s}", flush=True)


def blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def freeze_source(source: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if (
        source.get("schema") != SOURCE_SCHEMA
        or source.get("status") != SOURCE_STATUS
        or source.get("source_db_sha256") != DB_SHA256
    ):
        raise ValueError("wrong pinned public100 stress schema/status")
    s = source.get("summary")
    windows = source.get("per_window_results")
    if not isinstance(s, Mapping) or not isinstance(windows, list) or (
        s.get("selected_distinct_independent_games") != 24
        or s.get("preselected_early_and_late_windows") != 48
        or s.get("ship_VCR_sides") != 424
        or s.get("conditional_candidate_evaluable") != 424
        or s.get("conditional_candidate_equal_to_full_VCR") != 353
        or s.get("conditional_candidate_different_from_full_VCR") != 71
        or len(windows) != 48
    ):
        raise ValueError("frozen completed 424-side population is missing")
    seen_window = set()
    seen_side = set()
    sides = []
    for w in windows:
        g, t, cohort = w.get("game_id"), w.get("turn"), w.get("cohort")
        k = (g, t)
        if (
            integer(g) is None or g <= 0 or integer(t) is None or t <= 0
            or cohort not in ("EARLY_QUINTILE", "LATE_85TH_PERCENTILE")
            or k in seen_window
        ):
            raise ValueError("duplicate/invalid frozen time window")
        seen_window.add(k)
        rows = w.get("predictions")
        if not isinstance(rows, list) or len(rows) != w.get("ship_vcr_count", -1) * 2:
            raise ValueError("frozen window side count mismatch")
        for p in rows:
            identity = p.get("identity_from_current_VCR_not_predicted", {})
            old = p.get("Tminus1_static_component", {})
            race = p.get("Tminus1_owner_race", {})
            pred = p.get("conditional_race_component", {})
            ev = p.get("postforecast_evaluation", {})
            key = (g, t, p.get("vcr_id"), p.get("side"))
            if (
                key in seen_side or integer(key[2]) is None
                or key[3] not in ("left", "right")
                or p.get("game_id") != g or p.get("turn") != t
                or p.get("cohort") != cohort
                or old.get("status") != "RESOLVED"
                or race.get("status") != "RESOLVED_TMINUS1_OWNER_RACE"
                or pred.get("status") != "CONDITIONAL_DOCUMENTED_RACE_COMPONENT"
                or ev.get("status") != "COMPARATOR_AVAILABLE"
                or integer(identity.get("hull_id")) is None
                or integer(identity.get("owner_id")) is None
                or integer(old.get("predicted_hull_mass_KT")) is None
                or integer(pred.get("conditional_hull_plus_race_mass_KT")) is None
                or integer(ev.get("observed_vcr_mass_KT")) is None
            ):
                raise ValueError("frozen VCR-side status/identity drift")
            seen_side.add(key)
            sides.append((w, p))
    if len(sides) != 424 or len(seen_window) != 48:
        raise ValueError("frozen side/window population changed")
    nonmatches = sum(
        p["postforecast_evaluation"]["conditional_candidate_equals_full_observed_mass"]
        is False for _, p in sides
    )
    if nonmatches != 71:
        raise ValueError("frozen residual count is not 71")
    return windows, sides


def _owner_ship_in_archive(
    historical: Sequence[tuple[Any, Mapping[str, Any]]], *,
    game: int, turn: int, owner: int, ship_id: Any,
) -> dict[str, Any]:
    """Exact T-1 OWNER perspective only; conflicts or missing rows abstain.

    Never use a later VCR's ship state, another player's scan, or observed
    combat mass to fill precombat clan/engine/position gaps.
    """
    def abstain(reason: str) -> dict[str, Any]:
        return {
            "status": reason, "tminus1_ship": None,
            "owner_member_ids": [],
            "tminus1_hull": None,
        }
    if integer(owner) is None or owner <= 0 or integer(ship_id) is None or ship_id <= 0:
        return abstain("ABSTAIN_INVALID_OWNER_OR_SHIP_IDENTITY")
    owner_members = [
        (ref, member) for ref, member in historical
        if ref.perspective_player_id == owner
    ]
    if not owner_members:
        return abstain("ABSTAIN_MISSING_OWNER_PERSPECTIVE")
    rows = []
    catalogs = []
    for ref, member in owner_members:
        embedded = member.get("game")
        if (
            ref.game_id != game or ref.archive_turn != turn-1
            or ref.embedded_turn != turn-1
            or not isinstance(embedded, Mapping)
            or integer(embedded.get("id")) != game
            or integer(embedded.get("turn")) != turn-1
        ):
            return abstain("ABSTAIN_INVALID_HISTORICAL_PROVENANCE")
        ships, hulls = member.get("ships"), member.get("hulls")
        if not isinstance(ships, list) or not isinstance(hulls, list):
            return abstain("ABSTAIN_INCOMPLETE_TMINUS1_OWNER_DATA")
        matches = [
            s for s in ships if isinstance(s, Mapping)
            and integer(s.get("id")) == ship_id
            and integer(s.get("ownerid")) == owner
        ]
        if not matches:
            return abstain("ABSTAIN_TMINUS1_OWNER_SHIP_NOT_SEEN")
        if len(matches) != 1:
            return abstain("ABSTAIN_DUPLICATE_TMINUS1_OWNER_SHIP")
        row = matches[0]
        sid = integer(row.get("hullid"))
        hmatch = [
            h for h in hulls
            if isinstance(h, Mapping) and integer(h.get("id")) == sid
        ]
        if sid is None or len(hmatch) != 1:
            return abstain("ABSTAIN_OWNER_SHIP_HULL_CATALOG_UNKNOWN")
        reduced = {k: row.get(k) for k in (
            "id", "ownerid", "hullid", "engineid", "clans", "x", "y",
            "targetx", "targety", "warp", "damage", "mission",
        )}
        hull = {k: hmatch[0].get(k) for k in ("id", "mass", "cargo", "name", "special")}
        rows.append(reduced)
        catalogs.append(hull)
    if any(x != rows[0] for x in rows[1:]):
        return abstain("ABSTAIN_CONFLICTING_TMINUS1_OWNER_SHIP")
    if any(x != catalogs[0] for x in catalogs[1:]):
        return abstain("ABSTAIN_CONFLICTING_TMINUS1_SHIP_HULL_CATALOG")
    return {
        "status": "RESOLVED_TMINUS1_OWNER_SHIP",
        "tminus1_ship": rows[0],
        "tminus1_hull": catalogs[0],
        "owner_member_ids": sorted({r.member_id for r, _ in owner_members}),
    }


def _site_and_sg_context(
    historical: Sequence[tuple[Any, Mapping[str, Any]]], *,
    owner: int, site: tuple[int, int] | None,
) -> dict[str, Any]:
    """Retrospective archival geometry; current VCR site is NOT prestate."""
    answer = {
        "status": "ABSTAIN_VCR_SITE_UNAVAILABLE",
        "Tminus1_exact_site_generator_count": None,
        "Tminus1_generator_ids": [],
    }
    if site is None:
        return answer
    choices = []
    for ref, member in historical:
        if ref.perspective_player_id != owner:
            continue
        ships, hulls = member.get("ships"), member.get("hulls")
        if not isinstance(ships, list) or not isinstance(hulls, list):
            return {**answer, "status": "ABSTAIN_TMINUS1_OWNER_SECTION_MISSING"}
        catalog = {}
        for hull in hulls:
            if not isinstance(hull, Mapping):
                return {**answer, "status": "ABSTAIN_MALFORMED_STATIC_HULL_RECORD"}
            hid = integer(hull.get("id"))
            if hid in catalog:
                return {**answer, "status": "ABSTAIN_DUPLICATE_TMINUS1_HULL"}
            catalog[hid] = hull
        matching = []
        for ship in ships:
            if not isinstance(ship, Mapping) or integer(ship.get("ownerid")) != owner:
                continue
            h = catalog.get(integer(ship.get("hullid")))
            if h is None:
                continue
            label = str(h.get("name") or "")+" "+str(h.get("special") or "")
            if "shield generator" not in label.casefold():
                continue
            if (integer(ship.get("x")), integer(ship.get("y"))) == site:
                matching.append(integer(ship.get("id")))
        if None in matching:
            return {**answer, "status": "ABSTAIN_MALFORMED_GENERATOR_SHIP_ID"}
        choices.append(sorted(matching))
    if not choices:
        return {**answer, "status": "ABSTAIN_OWNER_PERSPECTIVE_MISSING"}
    if any(row != choices[0] for row in choices[1:]):
        return {**answer, "status": "ABSTAIN_CONFLICTING_TMINUS1_GENERATOR_POSITION"}
    return {
        "status": "RETROSPECTIVE_TMINUS1_GEOMETRY_ONLY",
        "Tminus1_exact_site_generator_count": len(choices[0]),
        "Tminus1_generator_ids": choices[0],
        "activation_proven": False,
    }


def classify_observed_residual(
    *, delta: int, side: str, raceid: int,
    left_vcr_bays: Any,
) -> dict[str, Any]:
    """Mutually exclusive research labels; NEVER modify a predicted mass."""
    left_bays = integer(left_vcr_bays)
    carrier_geometry = (
        side == "right" and left_bays is not None and left_bays > 0
    )
    if delta == 0:
        name = "BASELINE_EQUALITY_CONTROL"
    elif raceid == 12:
        name = "HORWASP_MUTABLE_MASS_OPEN"
    elif side == "right" and delta == 360:
        name = "RIGHT_PLUS360_NUMERIC_CANDIDATE"
    else:
        name = "OTHER_POSITIVE_OR_NEGATIVE_RESIDUAL"
    return {
        "class": name,
        "delta_KT": delta,
        "VCR_left_baycount_observed": left_vcr_bays,
        "carrier_side_and_VCR_bays_condition": carrier_geometry,
        "left_bays_are_current_VCR_observation_not_Tminus1": True,
        "host_random_branch_predicted": False,
        "shield_generator_activation_predicted": False,
        "horwasp_clan_attrition_predicted": False,
    }


def annotate_side(
    w: Mapping[str, Any], row: Mapping[str, Any],
    vcr: Mapping[str, Any],
    historical: Sequence[tuple[Any, Mapping[str, Any]]],
) -> dict[str, Any]:
    """Validate same VCR identity then annotate, preserving source forecasts."""
    game, turn, vid, side = w["game_id"], w["turn"], row["vcr_id"], row["side"]
    party = vcr.get(side)
    ident = row["identity_from_current_VCR_not_predicted"]
    ev = row["postforecast_evaluation"]
    if (
        not isinstance(party, Mapping)
        or integer(vcr.get(side+"ownerid")) != ident.get("owner_id")
        or integer(party.get("hullid")) != ident.get("hull_id")
        or integer(party.get("objectid")) != ident.get("ship_id")
        or integer(party.get("mass")) != ev["observed_vcr_mass_KT"]
        or integer(party.get("raceid")) != row["Tminus1_owner_race"]["owner_raceid_Tminus1"]
    ):
        raise ValueError(f"G{game} T{turn} V{vid} {side}: frozen VCR identity drift")
    base = row["conditional_race_component"]["conditional_hull_plus_race_mass_KT"]
    factual = ev["observed_vcr_mass_KT"]
    delta = factual - base
    if delta != ev["factual_minus_conditional_candidate_KT"]:
        raise ValueError("frozen observed-minus-conditional delta drift")
    x, y = integer(vcr.get("x")), integer(vcr.get("y"))
    site = (x, y) if x is not None and y is not None else None
    owner = ident["owner_id"]
    history = _owner_ship_in_archive(
        historical, game=game, turn=turn,
        owner=owner, ship_id=ident.get("ship_id"),
    )
    owner_ship = history.get("tminus1_ship") or {}
    hull = history.get("tminus1_hull") or {}
    sg = _site_and_sg_context(historical, owner=owner, site=site)
    left = vcr.get("left")
    left_bays = left.get("baycount") if isinstance(left, Mapping) else None
    label = classify_observed_residual(
        delta=delta, side=side,
        raceid=row["Tminus1_owner_race"]["owner_raceid_Tminus1"],
        left_vcr_bays=left_bays,
    )
    return {
        "game_id": game, "turn": turn, "cohort": w["cohort"],
        "vcr_id": vid, "side": side, "owner_id": owner,
        "ship_id": ident.get("ship_id"), "hull_id": ident.get("hull_id"),
        "Tminus1_owner_race": row["Tminus1_owner_race"]["owner_raceid_Tminus1"],
        "Tminus1_static_hull_mass": row["Tminus1_static_component"]["predicted_hull_mass_KT"],
        "original_conditional_candidate_KT": base,
        "factual_current_VCR_mass_KT": factual,
        "observational_residual": label,
        "VCR_site_observed_only": list(site) if site else None,
        "historical_Tminus1_owner_ship": history,
        "independent_Tminus1_clan_and_capacity": {
            "clans": integer(owner_ship.get("clans")),
            "hull_cargo_capacity": integer(hull.get("cargo")),
            "independently_precombat_seen": history["status"] == "RESOLVED_TMINUS1_OWNER_SHIP",
        },
        "independent_Tminus1_engine_id": integer(owner_ship.get("engineid")),
        "documented_SG_bonus_if_activated_KT": SG_BONUS_BY_ENGINE.get(
            integer(owner_ship.get("engineid"))
        ),
        "retrospective_VCR_site_Tminus1_SG_geometry": sg,
        "boundary": (
            "Observation: VCR site/left bays and factual mass are current battle "
            "data; T-1 ship, hull, engine, clans and SG geometry are independent "
            "historical context. Neither generator phase activation nor +360 RNG "
            "nor Horwasp clans-at-combat are inferred from residual."
        ),
    }


def make_report(source: Mapping[str, Any], *, conn: Any, dbpath: str) -> dict[str, Any]:
    windows, frozen_sides = freeze_source(source)
    all_annotations = []
    for i, w in enumerate(windows, 1):
        game, turn = w["game_id"], w["turn"]
        progress(f"[{i}/{len(windows)}] game={game} T{turn} {w['cohort']}: "
                 f"VCR={w['ship_vcr_count']} sides={len(w['predictions'])}")
        if not w["predictions"]:
            continue
        cases = combat_vcr_cases_for_turns(conn, game_id=game, battle_turns={turn})
        refs = member_refs_for_turns(
            conn, game_id=game, turns={turn-1},
            include_embedded_turn=False,
        )
        historical = list(reconstruct_members(conn, refs))
        for row in w["predictions"]:
            case = cases.get((turn, row["vcr_id"]))
            if case is None:
                raise ValueError(f"G{game} T{turn} V{row['vcr_id']} missing")
            all_annotations.append(
                annotate_side(w, row, case.payload, historical)
            )
        progress(f"[{i}/{len(windows)}] annotated={len(w['predictions'])}")
    if len(all_annotations) != len(frozen_sides) or len(all_annotations) != 424:
        raise ValueError("incomplete 424-side annotation")
    grouped = defaultdict(list)
    for item in all_annotations:
        grouped[item["cohort"]].append(item)
    def summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        deltas = Counter(
            str(r["observational_residual"]["delta_KT"])
            for r in rows
            if r["observational_residual"]["delta_KT"] != 0
        )
        residuals = [r for r in rows if r["observational_residual"]["delta_KT"] != 0]
        return {
            "total_sides": len(rows),
            "equal_to_frozen_conditional_component": len(rows)-len(residuals),
            "observed_residual_sides": len(residuals),
            "residual_values_KT": dict(sorted(deltas.items())),
            "residual_classes": dict(sorted(Counter(
                r["observational_residual"]["class"] for r in rows
            ).items())),
            "Tminus1_owner_ship_statuses": dict(sorted(Counter(
                r["historical_Tminus1_owner_ship"]["status"] for r in rows
            ).items())),
            "carrier_geometry_cross_tab": {
                "RIGHT_PLUS360_NUMERIC_CANDIDATE": dict(sorted(Counter(
                    str(r["observational_residual"]["carrier_side_and_VCR_bays_condition"])
                    for r in rows
                    if r["observational_residual"]["class"] == "RIGHT_PLUS360_NUMERIC_CANDIDATE"
                ).items())),
                "OTHER_RIGHT_STANDARD_SIDES": dict(sorted(Counter(
                    str(r["observational_residual"]["carrier_side_and_VCR_bays_condition"])
                    for r in rows
                    if r["side"] == "right" and r["Tminus1_owner_race"] != 12
                    and r["observational_residual"]["class"] != "RIGHT_PLUS360_NUMERIC_CANDIDATE"
                ).items())),
            },
            "historical_horwasp_Tminus1_clans_seen": sum(
                r["Tminus1_owner_race"] == 12
                and r["independent_Tminus1_clan_and_capacity"]["clans"] is not None
                for r in rows
            ),
            "historical_SG_exact_site_candidate_count_positive": sum(
                (r["retrospective_VCR_site_Tminus1_SG_geometry"].get(
                    "Tminus1_exact_site_generator_count") or 0) > 0
                for r in rows
            ),
            "full_combat_mass_predictions_made": 0,
        }
    original_71 = [
        r for r in all_annotations
        if r["observational_residual"]["delta_KT"] != 0
    ]
    if len(original_71) != 71:
        raise ValueError("original 71 residuals missing")
    return {
        "schema": SCHEMA,
        "status": "OBSERVATIONAL_TMINUS1_LATE_MASS_RESIDUALS_NOT_PROMOTED",
        "source_stress_git_blob_sha1": FROZEN_STRESS_REPORT_GIT_BLOB,
        "source_db_generation": DB_GENERATION,
        "source_db_sha256": DB_SHA256,
        "dbpath": dbpath,
        "summary": summary(all_annotations),
        "cohort_summaries": {
            k: summary(grouped[k]) for k in (
                "EARLY_QUINTILE", "LATE_85TH_PERCENTILE"
            )
        },
        "all_424_side_controls": all_annotations,
        "original_71_observed_residuals": original_71,
        "scientific_boundary": (
            "All current VCR geometry and numerical mass information is "
            "retrospective. Strict T-1 owner ship/clan and static hull/engine "
            "facts are independent but DO NOT prove same-turn combat state, "
            "Shield Generator activation, random carrier branch, Horwasp clan "
            "attrition, terminal outcomes, or correct order of mutable fights. "
            "No host prediction, production, CURRENT or corpus mutation."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-db-root", type=Path, required=True)
    p.add_argument("--frozen-stress", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        raw = a.frozen_stress.read_bytes()
        if blob_sha1(raw) != FROZEN_STRESS_REPORT_GIT_BLOB:
            raise ValueError("frozen published 424-side report Git blob SHA mismatch")
        source = json.loads(raw)
        freeze_source(source)
        db = a.corpus_db_root / DB_GENERATION
        if not db.is_file():
            raise ValueError("pinned immutable public100 DuckDB missing")
        start = time.monotonic()
        progress(f"verifying single pinned SHA256: {db.name}")
        with db.open("rb") as src:
            sha = hashlib.file_digest(src, "sha256").hexdigest()
        if sha != DB_SHA256:
            raise ValueError("public100 SHA256 mismatch")
        progress(f"SHA256 verified in {time.monotonic()-start:.1f}s; opening read-only DB")
        conn, dbpath = connect_compact_generation_read_only(
            DB_GENERATION, a.corpus_db_root
        )
        try:
            report = make_report(source, conn=conn, dbpath=str(dbpath))
        finally:
            conn.close()
        a.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = a.output.with_suffix(a.output.suffix + ".tmp")
        tmp.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        tmp.replace(a.output)
    except (KeyError, ValueError, TypeError, OSError, json.JSONDecodeError) as e:
        print("ERROR:", e, file=sys.stderr)
        return 2
    print("===== LATE MASS RESIDUAL / PRESTATE PHASE AUDIT V1 =====")
    print("status:", report["status"])
    print("summary:", report["summary"])
    for k, v in report["cohort_summaries"].items():
        print(k, v["total_sides"], "residuals:", v["observed_residual_sides"])
    print("output:", a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
