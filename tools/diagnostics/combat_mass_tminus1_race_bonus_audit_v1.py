"""Experimental held-out +50 KT race audit, using only archived T-1 roster as feature.

The Federation +50 combat-mass rule is documented. Its ACTUAL activation
and same-turn owner continuity remain UNPROVEN; this emits candidates, not
generative full NuHost mass predictions. VCR raceid/mass enter only evaluation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, member_refs_for_turns, reconstruct_members,
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns

SCHEMA = "planets-lab.combat-mass-tminus1-race-bonus-audit.v1"
SOURCE_SCHEMA = "planets-lab.combat-mass-time-indexed-static.v1"
GENERATION = "generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA256 = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"


def _int(x: Any) -> int | None:
    return x if type(x) is int else None


def progress(s: str) -> None:
    print(f"[race-v1] {s}", flush=True)


def resolve_owner_race(
    historical: Sequence[tuple[Any, Mapping[str, Any]]], *,
    game_id: int, turn: int, owner: int,
) -> dict[str, Any]:
    """Require exact T-1 provenance and agreement from all archived perspectives.

    Neither VCR mass/race nor inferred player-slot-as-race is accepted.
    """
    def abstain(why: str) -> dict[str, Any]:
        return {
            "status": why, "owner_raceid_Tminus1": None,
            "source_archive_turn": turn - 1, "source_member_ids": [],
        }
    if any(_int(v) is None or v <= 0 for v in (game_id, turn, owner)):
        return abstain("ABSTAIN_INVALID_OWNER_ID")
    if not historical:
        return abstain("ABSTAIN_NO_TMINUS1_PERSPECTIVES")
    for ref, member in historical:
        game = member.get("game")
        if (
            ref.game_id != game_id or ref.archive_turn != turn - 1
            or ref.embedded_turn != turn - 1 or not isinstance(game, Mapping)
            or _int(game.get("id")) != game_id
            or _int(game.get("turn")) != turn - 1
        ):
            return abstain("ABSTAIN_UNTRUSTED_TMINUS1_PROVENANCE")
    if not any(ref.perspective_player_id == owner for ref, _ in historical):
        return abstain("ABSTAIN_OWNER_PERSPECTIVE_MISSING")
    races = []
    ids = []
    for ref, member in historical:
        players = member.get("players")
        if not isinstance(players, list):
            return abstain("ABSTAIN_TMINUS1_PLAYER_ROSTER_MISSING")
        matches = [
            p for p in players if isinstance(p, Mapping)
            and _int(p.get("id")) == owner
        ]
        if not matches:
            return abstain("ABSTAIN_OWNER_NOT_IN_PLAYER_ROSTER")
        if len(matches) != 1:
            return abstain("ABSTAIN_DUPLICATE_OWNER_PLAYER_ROW")
        raceid = _int(matches[0].get("raceid"))
        if raceid is None or not 1 <= raceid <= 12:
            return abstain("ABSTAIN_UNSUPPORTED_OR_MISSING_RACE")
        races.append(raceid)
        ids.append(ref.member_id)
    if len(set(races)) != 1:
        return abstain("ABSTAIN_CONFLICTING_TMINUS1_OWNER_RACE")
    return {
        "status": "RESOLVED_TMINUS1_OWNER_RACE",
        "owner_raceid_Tminus1": races[0],
        "source_archive_turn": turn - 1,
        "source_member_ids": sorted(set(ids)),
        "perspectives_checked": len(historical),
    }


def conditional_candidate(
    race: Mapping[str, Any], hull_mass: int,
) -> dict[str, Any]:
    """Pure T-1 input. Returns conditional component, not full combat mass."""
    if _int(hull_mass) is None or hull_mass <= 0:
        raise ValueError("invalid frozen T-1 hull component")
    if race.get("status") != "RESOLVED_TMINUS1_OWNER_RACE":
        return {
            "status": "ABSTAIN_RACE_UNKNOWN",
            "assumed_federation_bonus_KT": None,
            "conditional_hull_plus_race_mass_KT": None,
            "full_combat_mass_prediction_KT": None,
        }
    raceid = _int(race.get("owner_raceid_Tminus1"))
    if raceid is None or not 1 <= raceid <= 12:
        raise ValueError("inconsistent historical owner race")
    bonus = 50 if raceid == 1 else 0
    return {
        "status": "CONDITIONAL_DOCUMENTED_RACE_COMPONENT",
        "assumed_federation_bonus_KT": bonus,
        "conditional_hull_plus_race_mass_KT": hull_mass + bonus,
        "full_combat_mass_prediction_KT": None,
        "federation_advantage_active_in_host_proven": False,
        "same_turn_current_owner_continuity_proven": False,
    }


def evaluate(
    candidate: Mapping[str, Any], race: Mapping[str, Any], *,
    factual_mass: int, factual_raceid: Any,
) -> dict[str, Any]:
    """Comparison begins here, after a completely independent candidate."""
    if _int(factual_mass) is None or factual_mass <= 0:
        raise ValueError("invalid factual mass comparator")
    mass = candidate["conditional_hull_plus_race_mass_KT"]
    vrace = _int(factual_raceid)
    oldrace = race.get("owner_raceid_Tminus1")
    return {
        "observed_vcr_mass_KT": factual_mass,
        "observed_vcr_raceid_ONLY_FOR_EVALUATION": factual_raceid,
        "VCR_race_matches_Tminus1_roster": (
            vrace == oldrace if vrace is not None and oldrace is not None else None
        ),
        "conditional_candidate_equals_full_observed_mass": (
            mass == factual_mass if mass is not None else None
        ),
        "factual_minus_conditional_candidate_KT": (
            factual_mass - mass if mass is not None else None
        ),
    }


def validate_source(source: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    s = source.get("summary")
    groups = source.get("held_out_results")
    if (
        source.get("schema") != SOURCE_SCHEMA
        or source.get("status") !=
        "EXPERIMENTAL_TMINUS1_STATIC_COMPONENT_PREDICTION_NOT_PROMOTED"
        or source.get("corpus_sha256") != EXPECTED_SHA256
        or not isinstance(s, Mapping)
        or s.get("held_out_games_with_VCRs") != 12
        or s.get("held_out_vcr_sides") != 30
        or s.get("static_resolution_statuses") != {"RESOLVED": 30}
        or s.get("component_equals_full_factual_mass_count") != 26
        or not isinstance(groups, list) or len(groups) != 12
    ):
        raise ValueError("successful frozen static V1 prerequisite absent/drifted")
    seen_games = set()
    seen_sides = set()
    n = 0
    for group in groups:
        g, t = _int(group.get("game_id")), _int(group.get("turn"))
        rows = group.get("predictions")
        if g is None or g <= 0 or t is None or t < 1 or g in seen_games:
            raise ValueError("duplicate/invalid source game-turn")
        if not isinstance(rows, list) or len(rows) != group.get("vcr_side_count"):
            raise ValueError("missing source prediction rows")
        seen_games.add(g)
        for row in rows:
            key = (row.get("game_id"), row.get("turn"),
                   row.get("vcr_id"), row.get("side"))
            if (
                key[:2] != (g, t) or key in seen_sides or _int(key[2]) is None
                or key[3] not in ("left", "right")
            ):
                raise ValueError("duplicate/invalid frozen VCR identity")
            seen_sides.add(key)
            forecast = row.get("forecast", {})
            evaluation = row.get("evaluation", {})
            if (
                forecast.get("status") != "RESOLVED"
                or _int(forecast.get("predicted_hull_mass_KT")) is None
                or evaluation.get("status") != "COMPARATOR_AVAILABLE"
                or _int(evaluation.get("factual_vcr_mass_KT")) is None
            ):
                raise ValueError("source T-1 mass or factual comparator unavailable")
            n += 1
    if n != 30:
        raise ValueError("source side population shifted")
    return groups


def build_report(
    source: Mapping[str, Any], *, conn: Any, dbpath: str, source_sha256: str,
) -> dict[str, Any]:
    groups = validate_source(source)
    out = []
    statuses = Counter()
    for i, group in enumerate(groups, 1):
        game, turn = group["game_id"], group["turn"]
        progress(f"[{i}/12] game={game} T{turn}: reconstructing T-1 owner race rosters")
        refs = member_refs_for_turns(
            conn, game_id=game, turns={turn - 1}, include_embedded_turn=False
        )
        historical = list(reconstruct_members(conn, refs))
        cases = combat_vcr_cases_for_turns(
            conn, game_id=game, battle_turns={turn}
        )
        unique_owners = {
            row["target_owner_id"] for row in group["predictions"]
            if _int(row["target_owner_id"]) is not None
        }
        resolved = {
            owner: resolve_owner_race(
                historical, game_id=game, turn=turn, owner=owner
            )
            for owner in unique_owners
        }
        for row in group["predictions"]:
            vid, side = row["vcr_id"], row["side"]
            case = cases.get((turn, vid))
            if case is None:
                raise ValueError(f"G{game} T{turn} V{vid}: VCR comparator missing")
            payload = case.payload
            party = payload.get(side)
            if (
                not isinstance(party, Mapping)
                or _int(payload.get(side+"ownerid")) != row["target_owner_id"]
                or _int(party.get("hullid")) != row["target_hull_id"]
                or _int(party.get("mass")) != row["evaluation"]["factual_vcr_mass_KT"]
            ):
                raise ValueError(f"G{game} T{turn} V{vid} {side}: VCR identity mismatch")
            race = resolved.get(row["target_owner_id"], {
                "status": "ABSTAIN_INVALID_OWNER_ID",
                "owner_raceid_Tminus1": None,
                "source_archive_turn": turn-1, "source_member_ids": [],
            })
            candidate = conditional_candidate(
                race, row["forecast"]["predicted_hull_mass_KT"]
            )
            assessment = evaluate(
                candidate, race,
                factual_mass=row["evaluation"]["factual_vcr_mass_KT"],
                factual_raceid=party.get("raceid"),
            )
            out.append({
                "game_id": game, "turn": turn, "vcr_id": vid, "side": side,
                "owner_id_from_VCR_identity_only": row["target_owner_id"],
                "hull_id": row["target_hull_id"],
                "independent_Tminus1_hull_mass_KT":
                    row["forecast"]["predicted_hull_mass_KT"],
                "original_factual_minus_hull_KT":
                    row["evaluation"]["difference_factual_minus_component_KT"],
                "historical_race_evidence": race,
                "conditional_precombat_race_component": candidate,
                "postforecast_comparison": assessment,
            })
            statuses[race["status"]] += 1
        progress(f"[{i}/12] complete; sides={len(group['predictions'])}")
    if len(out) != 30:
        raise ValueError("all 30 original held-out sides required")
    discrepancies = [
        r for r in out if r["original_factual_minus_hull_KT"] != 0
    ]
    if len(discrepancies) != 4 or any(
        r["original_factual_minus_hull_KT"] != 50 for r in discrepancies
    ):
        raise ValueError("original four +50KT side identities shifted")
    evaluable = [
        r for r in out if r["conditional_precombat_race_component"][
            "conditional_hull_plus_race_mass_KT"
        ] is not None
    ]
    matches = sum(
        r["postforecast_comparison"]["conditional_candidate_equals_full_observed_mass"]
        is True for r in evaluable
    )
    return {
        "schema": SCHEMA,
        "status": "TMINUS1_RACE_BONUS_CONDITIONAL_EVIDENCE_NOT_PROMOTED",
        "source_static_V1_file_sha256": source_sha256,
        "source_db": dbpath,
        "source_db_sha256": EXPECTED_SHA256,
        "summary": {
            "held_out_games": len(groups),
            "held_out_ship_VCR_sides": len(out),
            "hull_only_numeric_matches": 26,
            "original_plus50KT_sides": len(discrepancies),
            "Tminus1_race_resolver_statuses": dict(sorted(statuses.items())),
            "conditional_candidates_evaluable": len(evaluable),
            "conditional_candidates_matching_full_VCR_mass": matches,
            "conditional_candidates_not_matching_full_VCR_mass": len(evaluable)-matches,
            "race_disagreements_vs_current_VCR": sum(
                r["postforecast_comparison"]["VCR_race_matches_Tminus1_roster"]
                is False for r in evaluable
            ),
            "full_combat_mass_predictions_made": 0,
        },
        "original_four_plus50KT_cases": discrepancies,
        "all_30_held_out_sides": out,
        "boundary": (
            "Federation +50KT is documented, but campaign advantage activation "
            "and combat-phase owner continuity are not predicted. The candidate "
            "uses T-1 player race from ALL perspectives and T-1 static hull mass. "
            "Current VCR raceid/mass are only postforecast comparators. "
            "Numerical agreement does NOT prove full combat mass, SG, carrier RNG, "
            "capture ordering or Host implementation. Missing/conflicting roster "
            "abstains. No canonical DB or production change."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-db-root", type=Path, required=True)
    p.add_argument("--source-static-v1", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        raw = a.source_static_v1.read_bytes()
        source = json.loads(raw)
        validate_source(source)
        dbfile = a.corpus_db_root / GENERATION
        if not dbfile.is_file():
            raise ValueError("explicit pinned public100 database missing")
        progress(f"SHA256 verifying once: {dbfile.name}")
        started = time.monotonic()
        with dbfile.open("rb") as f:
            actual = hashlib.file_digest(f, "sha256").hexdigest()
        if actual != EXPECTED_SHA256:
            raise ValueError("pinned DuckDB SHA256 mismatch")
        progress(f"verified SHA256 in {time.monotonic()-started:.1f}s")
        conn, dbpath = connect_compact_generation_read_only(GENERATION, a.corpus_db_root)
        try:
            report = build_report(
                source, conn=conn, dbpath=str(dbpath),
                source_sha256=hashlib.sha256(raw).hexdigest(),
            )
        finally:
            conn.close()
        a.output.parent.mkdir(parents=True, exist_ok=True)
        temp = a.output.with_suffix(a.output.suffix+".tmp")
        temp.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        temp.replace(a.output)
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    print("===== PRE-VCR T-1 RACE BONUS AUDIT =====")
    print("status:", report["status"])
    print("summary:", report["summary"])
    for r in report["original_four_plus50KT_cases"]:
        print("plus50:", r["game_id"], r["turn"], r["vcr_id"], r["side"],
              "T-1 race status:", r["historical_race_evidence"]["status"],
              "raceid:", r["historical_race_evidence"]["owner_raceid_Tminus1"],
              "candidate:", r["conditional_precombat_race_component"]["conditional_hull_plus_race_mass_KT"],
              "match:", r["postforecast_comparison"]["conditional_candidate_equals_full_observed_mass"])
    print("output:", a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
