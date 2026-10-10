"""Pre-registered, read-only early/late held-out combat-mass stress evaluation.

Entire games from both the temporal-static calibration controls and the
earlier 12-game test are excluded. Sample new games/turns using only
pre-existing archive-turn/VCR-existence metadata, NEVER factual VCR mass,
VCR raceid, residual size, or prediction success.

Predicted quantities:
  - static hull component from exact archived T-1 hull catalog;
  - CONDITIONAL Federation +50 KT component from T-1 player roster.
No model predicts complete host combat mass or rule activation.
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
for directory in (ROOT / "src", Path(__file__).resolve().parent):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import combat_mass_time_indexed_static_v1 as static
import combat_mass_tminus1_race_bonus_audit_v1 as race

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, member_refs_for_turns,
    reconstruct_members,
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns

SCHEMA = "planets-lab.combat-mass-independent-late-turn-stress.v1"
STATUS = "INDEPENDENT_LATE_TURN_STRESS_OBSERVATIONAL_NOT_PROMOTED"
GENERATION = static.GENERATION
EXPECTED_DB_SHA256 = static.GENERATION_SHA256
FROZEN_STATIC_GIT_BLOB = "24088d11dc9e946baffa5522c77b692017b52342"
FROZEN_RACE_GIT_BLOB = "63ea59ed250dd967eed67d9a9c66c152fde8840b"


def number(x: Any) -> int | None:
    return x if type(x) is int else None


def log(msg: str) -> None:
    print(f"[late-stress] {msg}", flush=True)


def git_blob_sha1(raw: bytes) -> str:
    """Ensure local evidence JSON bytes equal GitHub-published runtime artifacts."""
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def source_boundaries(static_src: Mapping[str, Any],
                      race_src: Mapping[str, Any]) -> set[int]:
    groups = race.validate_source(static_src)
    if (
        race_src.get("schema") != race.SCHEMA
        or race_src.get("status") !=
            "TMINUS1_RACE_BONUS_CONDITIONAL_EVIDENCE_NOT_PROMOTED"
        or race_src.get("source_db_sha256") != EXPECTED_DB_SHA256
        or race_src.get("summary", {}).get("held_out_games") != 12
        or race_src.get("summary", {}).get("held_out_ship_VCR_sides") != 30
        or race_src.get("summary", {}).get("conditional_candidates_evaluable") != 30
        or race_src.get("summary", {}).get(
            "conditional_candidates_matching_full_VCR_mass") != 30
        or race_src.get("summary", {}).get("full_combat_mass_predictions_made") != 0
    ):
        raise ValueError("prior race experiment is not the completed frozen V1")
    baseline_games = {g["game_id"] for g in groups}
    excluded = static_src.get("selection", {}).get("excluded_control_games")
    if (
        not isinstance(excluded, list)
        or len(baseline_games) != 12
        or len(set(excluded)) < 10
        or any(number(g) is None or g <= 0 for g in excluded)
        or len(set(excluded) & baseline_games) != 0
    ):
        raise ValueError("frozen game-level control exclusions unavailable")
    race_rows = race_src.get("all_30_held_out_sides")
    static_keys = {
        (row["game_id"], row["turn"], row["vcr_id"], row["side"])
        for group in groups for row in group["predictions"]
    }
    if not isinstance(race_rows, list) or {
        (row.get("game_id"), row.get("turn"), row.get("vcr_id"), row.get("side"))
        for row in race_rows
    } != static_keys:
        raise ValueError("race audit identities do not match frozen static V1")
    return set(excluded) | baseline_games


def evenly_spaced(items: Sequence[int], k: int) -> list[int]:
    """Deterministic game-ID quantile selection with no combat outcome features."""
    if k <= 0:
        raise ValueError("max_games must be positive")
    if len(items) <= k:
        return list(items)
    return [items[min(len(items)-1, (2*i+1)*len(items)//(2*k))]
            for i in range(k)]


def select_early_late_windows(
    pairs: Sequence[tuple[int, int]], *, excluded_games: set[int],
    max_games: int, min_turn_span: int = 20, min_candidates_per_game: int = 6,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Freeze selection BEFORE decoding any VCR payload.

    Eligible games need ≥6 VCR-bearing archive turns and a ≥20-turn span.
    Evaluate chronologically earlier 20% and later 85% percentile turns per
    sampled game; selecting an unusually good residual is impossible here.
    """
    if max_games < 1 or min_turn_span < 1 or min_candidates_per_game < 2:
        raise ValueError("invalid stress selection bounds")
    by_game: dict[int, set[int]] = defaultdict(set)
    for game, turn in pairs:
        if (
            number(game) is None or game <= 0
            or number(turn) is None or turn < 1
        ):
            raise ValueError("invalid archive turn candidate metadata")
        if game not in excluded_games:
            by_game[game].add(turn)
    viable: dict[int, list[int]] = {}
    for game, turns in by_game.items():
        ordered = sorted(turns)
        if (len(ordered) >= min_candidates_per_game
                and ordered[-1] - ordered[0] >= min_turn_span):
            viable[game] = ordered
    selected_games = evenly_spaced(sorted(viable), max_games)
    windows: list[dict[str, Any]] = []
    for game in selected_games:
        turns = viable[game]
        early_idx = (len(turns)-1)//5
        late_idx = (len(turns)-1)*85//100
        if late_idx <= early_idx:
            raise ValueError("early/late selection collided")
        for cohort, idx in (("EARLY_QUINTILE", early_idx),
                            ("LATE_85TH_PERCENTILE", late_idx)):
            windows.append({
                "game_id": game, "turn": turns[idx],
                "cohort": cohort, "candidate_count_in_game": len(turns),
                "first_available_turn": turns[0],
                "last_available_turn": turns[-1],
            })
    return windows, {
        "eligible_game_count_before_sampling": len(viable),
        "selected_game_count": len(selected_games),
        "selected_games": selected_games,
        "excluded_control_and_original_heldout_games": sorted(excluded_games),
        "selection_rule": (
            "games with >=6 metadata VCR-bearing consecutive T-1/T archives "
            "spanning >=20 turns; game-ID even quantiles (up to max_games); "
            "archive turn positions 20th and 85th percentiles fixed before "
            "reading current VCR identity, mass or race"
        ),
    }


def out_of_scope_record(vid: int, payload: Any, reason: str) -> dict[str, Any]:
    raw = payload if isinstance(payload, Mapping) else {}
    return {
        "vcr_id": vid,
        "status": reason,
        "left_hullid": raw.get("left", {}).get("hullid")
            if isinstance(raw.get("left"), Mapping) else None,
        "right_hullid": raw.get("right", {}).get("hullid")
            if isinstance(raw.get("right"), Mapping) else None,
    }


def _abstain(status: str) -> dict[str, Any]:
    return {
        "status": status,
        "predicted_hull_mass_KT": None,
        "source_member_ids": [],
        "full_combat_mass_prediction_KT": None,
    }


def forecast_pre_vcr_side(
    snapshots: Sequence[static.Snapshot] | None,
    historical: Sequence[tuple[Any, Mapping[str, Any]]], *,
    game: int, turn: int, owner: Any, hull: Any, malformed_tminus1: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """ONLY archive T-1, plus target owner/hull identity, enter prediction."""
    owner_id, hull_id = number(owner), number(hull)
    if owner_id is None or owner_id <= 0 or hull_id is None or hull_id <= 0:
        hull_prediction = _abstain("ABSTAIN_INVALID_CURRENT_TARGET_IDENTITY")
        historical_race = {
            "status": "ABSTAIN_INVALID_OWNER_ID", "owner_raceid_Tminus1": None,
            "source_member_ids": [],
        }
    else:
        historical_race = race.resolve_owner_race(
            historical, game_id=game, turn=turn, owner=owner_id
        )
        if malformed_tminus1:
            hull_prediction = _abstain("ABSTAIN_MALFORMED_TMINUS1_STATIC")
        else:
            assert snapshots is not None
            hull_prediction = static.forecast_component(
                snapshots, game_id=game, battle_turn=turn,
                owner_id=owner_id, hull_id=hull_id,
            )
    predicted_hull = hull_prediction.get("predicted_hull_mass_KT")
    if number(predicted_hull) is None:
        conditional = {
            "status": "ABSTAIN_HULL_COMPONENT_UNKNOWN",
            "assumed_federation_bonus_KT": None,
            "conditional_hull_plus_race_mass_KT": None,
            "full_combat_mass_prediction_KT": None,
        }
    else:
        conditional = race.conditional_candidate(historical_race, predicted_hull)
    return hull_prediction, historical_race, conditional


def validate_after_prediction(
    *, conditional: Mapping[str, Any], historical_race: Mapping[str, Any],
    factual_mass: Any, factual_raceid: Any,
) -> dict[str, Any]:
    """Current VCR mass/race ONLY read by post-forecast evaluation."""
    factual = number(factual_mass)
    if factual is None or factual <= 0:
        return {
            "status": "ABSTAIN_INVALID_VCR_MASS_COMPARATOR",
            "observed_vcr_mass_KT": None,
            "observed_vcr_raceid_ONLY_FOR_EVALUATION": factual_raceid,
            "conditional_candidate_equals_full_observed_mass": None,
            "factual_minus_conditional_candidate_KT": None,
        }
    return {
        "status": "COMPARATOR_AVAILABLE",
        **race.evaluate(
            conditional, historical_race,
            factual_mass=factual, factual_raceid=factual_raceid,
        ),
    }


def evaluate_window(conn: Any, item: Mapping[str, Any]) -> dict[str, Any]:
    game, turn = item["game_id"], item["turn"]
    vcrs = combat_vcr_cases_for_turns(
        conn, game_id=game, battle_turns={turn}
    )
    ship_cases: list[tuple[int, Any]] = []
    excluded_vcrs: list[dict[str, Any]] = []
    for (_case_turn, vid), case in sorted(vcrs.items()):
        reason = static.vcr_ship_scope(case.payload)
        if reason is None:
            ship_cases.append((vid, case))
        else:
            excluded_vcrs.append(
                out_of_scope_record(vid, case.payload, reason)
            )
    data = {
        **item,
        "all_vcr_count": len(vcrs),
        "ship_vcr_count": len(ship_cases),
        "excluded_nonship_vcrs": excluded_vcrs,
        "Tminus1_member_count": 0,
        "Tminus1_static_input_failures": [],
        "predictions": [],
    }
    if not ship_cases:
        data["status"] = "NO_IN_SCOPE_SHIP_VCR_FOR_PRESELECTED_WINDOW"
        return data
    refs = member_refs_for_turns(
        conn, game_id=game, turns={turn - 1},
        include_embedded_turn=False,
    )
    historical = list(reconstruct_members(conn, refs))
    snapshots = []
    malformed = False
    issues: list[str] = []
    for ref, member in historical:
        try:
            snapshots.append(static.snapshot_from_member(ref, member))
        except (ValueError, TypeError, KeyError) as exc:
            malformed = True
            issues.append(
                f"member_id={ref.member_id} {type(exc).__name__}: {exc}"
            )
    data["Tminus1_member_count"] = len(historical)
    data["Tminus1_static_input_failures"] = issues
    for vid, case in ship_cases:
        for side in ("left", "right"):
            payload = case.payload
            party = payload[side]
            owner = payload.get(side+"ownerid")
            hull = party.get("hullid")
            # Forecast before the comparator is accessed.
            h, r, c = forecast_pre_vcr_side(
                snapshots if not malformed else None, historical,
                game=game, turn=turn, owner=owner, hull=hull,
                malformed_tminus1=malformed,
            )
            evaluation = validate_after_prediction(
                conditional=c, historical_race=r,
                factual_mass=party.get("mass"),
                factual_raceid=party.get("raceid"),
            )
            data["predictions"].append({
                "game_id": game, "turn": turn, "cohort": item["cohort"],
                "vcr_id": vid, "side": side,
                "identity_from_current_VCR_not_predicted": {
                    "owner_id": owner, "hull_id": hull,
                    "ship_id": party.get("objectid"),
                },
                "Tminus1_static_component": h,
                "Tminus1_owner_race": r,
                "conditional_race_component": c,
                "postforecast_evaluation": evaluation,
            })
    data["status"] = (
        "PREDICTIONS_EVALUATED_WITH_EXPLICIT_ABSTENTIONS"
        if not malformed else "TMINUS1_STATIC_MALFORMED_ABSTAINED"
    )
    return data


def build_report(conn: Any, static_src: Mapping[str, Any],
                 race_src: Mapping[str, Any], *, max_games: int,
                 db_path: str, source_hashes: Mapping[str, str]) -> dict[str, Any]:
    excluded = source_boundaries(static_src, race_src)
    log("discovering VCR-bearing T-1/T metadata, pre-registering independent game/turn split")
    all_pairs = static._candidate_pairs(conn)
    windows, selection = select_early_late_windows(
        all_pairs, excluded_games=excluded, max_games=max_games
    )
    if len(selection["selected_games"]) < 8:
        raise ValueError(
            f"only {len(selection['selected_games'])} independent eligible games"
        )
    log(
        f"preselected {len(windows)} windows from "
        f"{selection['selected_game_count']} independent games; "
        f"{selection['eligible_game_count_before_sampling']} eligible"
    )
    results = []
    for idx, item in enumerate(windows, start=1):
        log(
            f"[{idx}/{len(windows)}] game={item['game_id']} T{item['turn']} "
            f"{item['cohort']}: loading VCRs and T-1 facts"
        )
        result = evaluate_window(conn, item)
        results.append(result)
        statuses = Counter(
            x["conditional_race_component"]["status"]
            for x in result["predictions"]
        )
        log(
            f"[{idx}/{len(windows)}] ship_vcrs={result['ship_vcr_count']} "
            f"sides={len(result['predictions'])} "
            f"static_failures={len(result['Tminus1_static_input_failures'])} "
            f"candidate_statuses={dict(sorted(statuses.items()))}"
        )
    sides = [r for item in results for r in item["predictions"]]
    eval_sides = [
        r for r in sides if (
            r["conditional_race_component"]["conditional_hull_plus_race_mass_KT"]
            is not None
            and r["postforecast_evaluation"]["status"] == "COMPARATOR_AVAILABLE"
        )
    ]
    exact = sum(
        r["postforecast_evaluation"]["conditional_candidate_equals_full_observed_mass"]
        is True for r in eval_sides
    )
    races = Counter(
        r["Tminus1_owner_race"]["owner_raceid_Tminus1"]
        for r in eval_sides
    )
    residuals = [
        r for r in eval_sides
        if r["postforecast_evaluation"]["conditional_candidate_equals_full_observed_mass"]
        is False
    ]
    summary = {
        "selected_distinct_independent_games": len(selection["selected_games"]),
        "preselected_early_and_late_windows": len(windows),
        "windows_with_in_scope_ship_VCRs": sum(x["ship_vcr_count"] > 0 for x in results),
        "ship_VCRs": sum(x["ship_vcr_count"] for x in results),
        "ship_VCR_sides": len(sides),
        "out_of_scope_VCRs": sum(len(x["excluded_nonship_vcrs"]) for x in results),
        "static_resolution_statuses": dict(sorted(Counter(
            r["Tminus1_static_component"]["status"] for r in sides
        ).items())),
        "race_resolution_statuses": dict(sorted(Counter(
            r["Tminus1_owner_race"]["status"] for r in sides
        ).items())),
        "race_conditional_statuses": dict(sorted(Counter(
            r["conditional_race_component"]["status"] for r in sides
        ).items())),
        "conditional_candidate_evaluable": len(eval_sides),
        "conditional_candidate_equal_to_full_VCR": exact,
        "conditional_candidate_different_from_full_VCR": len(residuals),
        "evaluable_Tminus1_race_distribution": dict(sorted(
            (str(k), v) for k, v in races.items()
        )),
        "evaluable_after_forecast_VCR_race_disagreement": sum(
            r["postforecast_evaluation"].get("VCR_race_matches_Tminus1_roster")
            is False for r in eval_sides
        ),
        "full_combat_mass_predictions_made": 0,
    }
    if not sides:
        raise ValueError("no eligible ship/VCR sides in new independent population")
    return {
        "schema": SCHEMA, "status": STATUS,
        "source_db_generation": GENERATION, "source_db_sha256": EXPECTED_DB_SHA256,
        "db_path": db_path, "frozen_source_file_blob_sha1": dict(source_hashes),
        "selection": selection,
        "summary": summary,
        "residuals_after_conditional_race_component": residuals,
        "per_window_results": results,
        "boundary": (
            "Game and early/late turn selection uses only archival metadata, "
            "excluding all earlier 14 calibration controls and initial 12-game "
            "held-out population. Exact T-1 historical static/roster data "
            "are resolved before current VCR race and mass comparisons. "
            "Target ship identity is obtained from current VCR and NOT predicted. "
            "Fed +50KT is a conditional documented component, NOT verified "
            "battle-phase activation. Unknown T-1 specs/rosters ABSTAIN; numeric "
            "nonmatches are not automatically errors or new rules. Cargo, "
            "Shield Generator, Horwasp, carrier RNG, captures and movement "
            "are not reconstructed. No production/executor/DB mutation."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-db-root", type=Path, required=True)
    p.add_argument("--frozen-static", type=Path, required=True)
    p.add_argument("--frozen-race", type=Path, required=True)
    p.add_argument("--max-games", type=int, default=24)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        raw = {
            "static": a.frozen_static.read_bytes(),
            "race": a.frozen_race.read_bytes(),
        }
        blobs = {k: git_blob_sha1(v) for k, v in raw.items()}
        if blobs != {
            "static": FROZEN_STATIC_GIT_BLOB,
            "race": FROZEN_RACE_GIT_BLOB,
        }:
            raise ValueError(f"frozen published report blob SHA mismatch: {blobs}")
        static_src = json.loads(raw["static"])
        race_src = json.loads(raw["race"])
        source_boundaries(static_src, race_src)
        dbfile = a.corpus_db_root / GENERATION
        if not dbfile.is_file():
            raise ValueError("explicit immutable public100 database missing")
        log(f"verifying pinned corpus SHA256 once: {dbfile.name}")
        started = time.monotonic()
        with dbfile.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if sha != EXPECTED_DB_SHA256:
            raise ValueError("immutable corpus SHA256 mismatch")
        log(f"SHA256 verified in {time.monotonic()-started:.1f}s; opening read-only")
        conn, dbpath = connect_compact_generation_read_only(
            GENERATION, a.corpus_db_root
        )
        try:
            report = build_report(
                conn, static_src, race_src, max_games=a.max_games,
                db_path=str(dbpath), source_hashes=blobs,
            )
        finally:
            conn.close()
        a.output.parent.mkdir(parents=True, exist_ok=True)
        temp = a.output.with_suffix(a.output.suffix+".tmp")
        temp.write_text(
            json.dumps(report, sort_keys=True, indent=2)+"\n",
            encoding="utf-8",
        )
        temp.replace(a.output)
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as e:
        print("ERROR:", e, file=sys.stderr)
        return 2
    print("===== INDEPENDENT EARLY/LATE COMBAT-MASS STRESS V1 =====")
    print("status:", report["status"])
    print("summary:", report["summary"])
    print("report:", a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
