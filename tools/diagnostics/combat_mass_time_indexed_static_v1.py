"""Experimental pre-VCR time-indexed static mass resolver (read-only).

All feature inputs come from archive turn T-1. Current VCRs are used only
AFTER forecasting, to identify evaluation targets and compare factual mass.
A predicted *hull component* is NOT a full NuHost combat-mass prediction.
No result from this experiment may enter a production combat executor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "planets-lab.combat-mass-time-indexed-static.v1"
RECONCILIATION_SCHEMA = "planets-lab.combat-mass-temporal-reconciliation.v1"
CONTROL_SCHEMA = "planets-lab.combat-mass-capture-phase-controls.v1"
GENERATION = "generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
GENERATION_SHA256 = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
MIN_HOLDOUT_GAMES = 3


def integer(value: Any) -> int | None:
    return value if type(value) is int else None


@dataclass(frozen=True)
class Snapshot:
    game_id: int
    archive_turn: int
    embedded_turn: int
    owner_perspective: int
    member_id: int
    sha256: str
    masses: dict[int, int]


def snapshot_from_member(ref: Any, member: Mapping[str, Any]) -> Snapshot:
    """Ingest only an archived hull catalog, excluding ships and all VCR fields."""
    required = (ref.game_id, ref.archive_turn, ref.embedded_turn,
                ref.perspective_player_id, ref.member_id)
    if any(integer(x) is None for x in required):
        raise ValueError("invalid static provenance identifiers")
    digest = ref.decoded_payload_sha256
    if not isinstance(digest, str) or len(digest) != 64 or any(
        c not in "0123456789abcdef" for c in digest
    ):
        raise ValueError("invalid static source digest")
    game = member.get("game")
    if not isinstance(game, Mapping) or integer(game.get("id")) != ref.game_id:
        raise ValueError("archived game identity mismatch")
    if integer(game.get("turn")) != ref.embedded_turn:
        raise ValueError("archived embedded turn mismatch")
    rows = member.get("hulls")
    if not isinstance(rows, list) or not rows:
        raise ValueError("archived static catalog missing")
    masses: dict[int, int] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("malformed archived hull")
        hid, mass = integer(row.get("id")), integer(row.get("mass"))
        if hid is None or hid <= 0 or mass is None or mass <= 0:
            raise ValueError("incomplete archived hull id/mass")
        if hid in masses:
            raise ValueError("duplicate archived hull id")
        masses[hid] = mass
    return Snapshot(
        ref.game_id, ref.archive_turn, ref.embedded_turn,
        ref.perspective_player_id, ref.member_id, digest, masses,
    )


def resolve_mass(
    snapshots: Sequence[Snapshot], *, game_id: int,
    battle_turn: int, owner_id: int, hull_id: int,
) -> dict[str, Any]:
    """Fail closed: exact T-1, owner present, every available perspective agrees.

    Older and future archives are NEVER fallback sources. The resolved component
    is obtained without any VCR mass, engine, or postcombat entity attributes.
    """
    if any(integer(x) is None or x <= 0 for x in
           (game_id, battle_turn, owner_id, hull_id)):
        raise ValueError("invalid prediction identity")
    eligible = [
        x for x in snapshots
        if x.game_id == game_id and x.archive_turn == battle_turn - 1
    ]
    def abstain(reason: str) -> dict[str, Any]:
        return {"status": reason, "predicted_hull_mass_KT": None,
                "source_archive_turn": battle_turn - 1,
                "source_member_ids": []}
    if not eligible:
        return abstain("MISSING_EXACT_TMINUS1")
    # Do not use a file named T-1 with an embedded future game state.
    if any(x.embedded_turn != battle_turn - 1 for x in eligible):
        return abstain("UNTRUSTED_EMBEDDED_TURN")
    if not any(x.owner_perspective == owner_id for x in eligible):
        return abstain("MISSING_OWNER_PERSPECTIVE")
    if any(hull_id not in x.masses for x in eligible):
        return abstain("MISSING_HULL_IN_PERSPECTIVE")
    if len({x.masses[hull_id] for x in eligible}) != 1:
        return abstain("CONFLICTING_TMINUS1_STATIC")
    masses = {x.masses[hull_id] for x in eligible}
    return {
        "status": "RESOLVED",
        "predicted_hull_mass_KT": masses.pop(),
        "source_archive_turn": battle_turn - 1,
        "source_member_ids": sorted({x.member_id for x in eligible}),
        "source_sha256": sorted({x.sha256 for x in eligible}),
        "perspectives_checked": len(eligible),
        "owner_perspectives_checked": sum(
            x.owner_perspective == owner_id for x in eligible
        ),
    }


def forecast_component(
    snapshots: Sequence[Snapshot], *, game_id: int, battle_turn: int,
    owner_id: int, hull_id: int,
) -> dict[str, Any]:
    """Pre-VCR forecast: no observed mass or current VCR state argument exists."""
    resolved = resolve_mass(
        snapshots, game_id=game_id, battle_turn=battle_turn,
        owner_id=owner_id, hull_id=hull_id,
    )
    return {
        **resolved,
        "scope": "PREDICTED_STATIC_HULL_COMPONENT_ONLY",
        "full_combat_mass_prediction_KT": None,
        "full_mass_abstention": (
            "SG activation, movement, cargo/clans, carrier RNG, and capture "
            "are not phase-independently resolved from T-1 hull catalogs"
        ),
    }


def evaluate_forecast(forecast: Mapping[str, Any], observed_mass: Any) -> dict[str, Any]:
    """The ONLY point where the factual VCR mass enters the evaluation."""
    factual = integer(observed_mass)
    if factual is None or factual <= 0:
        raise ValueError("VCR mass unavailable or invalid")
    component = forecast["predicted_hull_mass_KT"]
    return {
        "factual_vcr_mass_KT": factual,
        "component_equals_factual_mass": (
            component == factual if component is not None else None
        ),
        "difference_factual_minus_component_KT": (
            factual - component if component is not None else None
        ),
        "interpretation": (
            "Component-vs-total comparison only; mismatches are NOT "
            "proof of an erroneous static resolver"
        ),
    }


def select_holdout_pairs(
    pairs: Sequence[tuple[int, int]], *, excluded_games: set[int],
) -> list[tuple[int, int]]:
    """First chronological archived T-1/T pair per independent game.

    Selection uses ONLY available archive-turn metadata; never VCR masses or
    residual rankings. Excludes all games used by the 14 targeted controls.
    """
    selected: dict[int, int] = {}
    for game, turn in sorted(set(pairs)):
        if (integer(game) is None or integer(turn) is None or turn < 1
                or game in excluded_games):
            continue
        selected.setdefault(game, turn)
    return sorted(selected.items())


def _candidate_pairs(conn: Any) -> list[tuple[int, int]]:
    rows = conn.execute("""
        WITH gt AS (
            SELECT DISTINCT game_id, archive_turn FROM source_members
        )
        SELECT later.game_id, later.archive_turn
        FROM gt AS later
        INNER JOIN gt AS earlier
          ON earlier.game_id = later.game_id
         AND earlier.archive_turn = later.archive_turn - 1
        WHERE later.archive_turn >= 1
        ORDER BY later.game_id, later.archive_turn
    """).fetchall()
    return [(int(g), int(t)) for g, t in rows]


def _read_json(path: Path) -> Mapping[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, Mapping):
        raise ValueError("source JSON must be an object")
    return obj


def live_report(
    *, db_root: Path, controls_path: Path,
    reconciliation_path: Path, max_games: int = 12,
) -> dict[str, Any]:
    from planets_lab.corpus.corpus_db_runtime import (
        connect_compact_generation_read_only, member_refs_for_turns,
        reconstruct_members,
    )
    from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns

    controls = _read_json(controls_path)
    recon = _read_json(reconciliation_path)
    if (controls.get("schema") != CONTROL_SCHEMA
            or controls.get("status") !=
            "INDEPENDENT_CAPTURE_AND_TEMPORAL_STATIC_CONTROLS_OBSERVATIONAL_NOT_PROMOTED"):
        raise ValueError("wrong prerequisite capture control schema/status")
    control_rows = controls.get("static_snapshot_controls")
    if not isinstance(control_rows, list) or len(control_rows) != 14:
        raise ValueError("prerequisite 14 controls missing")
    if (recon.get("schema") != RECONCILIATION_SCHEMA
            or recon.get("status") !=
            "TEMPORAL_STATIC_AND_CAPTURE_RECONCILED_OBSERVATIONAL_NOT_PROMOTED"
            or recon.get("summary", {}).get("residuals_with_direct_Tminus1_changed_hull") != 7
            or recon.get("summary", {}).get("source_aggregate_zero_change_controls_with_truncated_details") != 4):
        raise ValueError("V1 reconciliation not yet successful")
    excluded = {row["game_id"] for row in control_rows}
    if len(excluded) < 2 or max_games < MIN_HOLDOUT_GAMES:
        raise ValueError("invalid held-out selection bounds")
    db_file = db_root / GENERATION
    if not db_file.is_file():
        raise ValueError("pinned public100 generation missing")
    # Hash before DuckDB open; never modify this file or its CURRENT pointer.
    with db_file.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != GENERATION_SHA256:
        raise ValueError("pinned corpus SHA256 mismatch")
    conn, path = connect_compact_generation_read_only(GENERATION, db_root)
    try:
        candidates = select_holdout_pairs(
            _candidate_pairs(conn), excluded_games=excluded
        )
        results: list[dict[str, Any]] = []
        scan_log: list[dict[str, Any]] = []
        for game, turn in candidates:
            if len(results) >= max_games:
                break
            cases = combat_vcr_cases_for_turns(
                conn, game_id=game, battle_turns={turn}
            )
            if not cases:
                scan_log.append({"game_id": game, "turn": turn,
                                 "status": "NO_TARGET_VCR"})
                continue
            refs = member_refs_for_turns(
                conn, game_id=game, turns={turn - 1},
                include_embedded_turn=False,
            )
            snapshots = [
                snapshot_from_member(ref, member)
                for ref, member in reconstruct_members(conn, refs)
            ]
            per_case = []
            for (_turn, vcr_id), case in sorted(cases.items()):
                for side in ("left", "right"):
                    party = case.payload.get(side)
                    owner = integer(case.payload.get(side + "ownerid"))
                    hull = integer(party.get("hullid")) if isinstance(party, Mapping) else None
                    factual = integer(party.get("mass")) if isinstance(party, Mapping) else None
                    if owner is None or hull is None or factual is None:
                        raise ValueError("held-out VCR identity/observed mass incomplete")
                    # Forecast receives ONLY pre-VCR snapshots and target IDs.
                    predicted = forecast_component(
                        snapshots, game_id=game, battle_turn=turn,
                        owner_id=owner, hull_id=hull,
                    )
                    # Comparator is deliberately applied only AFTER forecast.
                    assessed = evaluate_forecast(predicted, factual)
                    per_case.append({
                        "game_id": game, "turn": turn, "vcr_id": vcr_id,
                        "side": side, "target_owner_id": owner,
                        "target_hull_id": hull,
                        "target_identity_from_vcr": True,
                        "forecast": predicted, "evaluation": assessed,
                    })
            results.append({
                "game_id": game, "turn": turn,
                "precombat_archive_member_count": len(refs),
                "vcr_side_count": len(per_case),
                "predictions": per_case,
            })
        if len(results) < MIN_HOLDOUT_GAMES:
            raise ValueError("insufficient independent held-out games with VCRs")
    finally:
        conn.close()
    flattened = [row for group in results for row in group["predictions"]]
    status = Counter(row["forecast"]["status"] for row in flattened)
    equal = sum(row["evaluation"]["component_equals_factual_mass"] is True
                for row in flattened)
    return {
        "schema": SCHEMA,
        "status": "EXPERIMENTAL_TMINUS1_STATIC_COMPONENT_PREDICTION_NOT_PROMOTED",
        "corpus_generation": str(path),
        "corpus_sha256": digest,
        "selection": {
            "method": "earliest consecutive archived T-1/T pair by independent game ID; no VCR or residual mass ranking",
            "excluded_control_games": sorted(excluded),
            "candidate_game_count": len(candidates),
            "max_selected_games": max_games,
        },
        "summary": {
            "held_out_games_with_VCRs": len(results),
            "held_out_vcr_sides": len(flattened),
            "static_resolution_statuses": dict(sorted(status.items())),
            "component_equals_full_factual_mass_count": equal,
            "full_combat_mass_predictions_made": 0,
        },
        "skipped_no_vcr": scan_log,
        "held_out_results": results,
        "boundary": (
            "Independently held-out games and T-1 owner/static agreement predict "
            "only the hull mass component. VCR reveals target identity and site, "
            "never predictor features or calibration of mass. Neither equality "
            "nor residual proves Shield Generator phase, capture, Horwasp loss "
            "or a generative NuHost combat engine. Missing/conflicting specs "
            "fail closed. No executor or canonical DB mutation."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-db-root", type=Path, required=True)
    p.add_argument("--capture-controls", type=Path, required=True)
    p.add_argument("--reconciliation", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-games", type=int, default=12)
    a = p.parse_args()
    try:
        result = live_report(
            db_root=a.corpus_db_root, controls_path=a.capture_controls,
            reconciliation_path=a.reconciliation, max_games=a.max_games,
        )
        a.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = a.output.with_name(a.output.name + ".tmp")
        temporary.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8",
        )
        temporary.replace(a.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    print("===== TIME-INDEXED STATIC COMPONENT PREDICTION V1 =====")
    print("status:", result["status"])
    print("summary:", result["summary"])
    print("output:", a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
