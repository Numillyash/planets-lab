"""Frozen precombat Horwasp clan mass hypothesis on independent late stress.

Inputs: only original T-1 hull + owner-perspective T-1 clan/cargo/capacity
from the 424-side phase-audit evidence; VCR game/turn/ship identity selects
a target but DOES NOT supply prediction state. Observed combat mass enters
only postforecast comparison. An explicit unverified floor interpolation
is a falsifiable pre-registered HYPOTHESIS, not NuHost code reconstruction.

VCR ID ordering is NOT independently verified Host combat order: the
first-by-ID vs repeated labels are descriptive, not proven phase steps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "planets-lab.combat-mass-horwasp-tminus1-first-vcr.v1"
STATUS = "HORWASP_TMINUS1_LINEAR_FLOOR_HYPOTHESIS_NOT_PROMOTED"
SOURCE_SCHEMA = "planets-lab.combat-mass-late-residual-prestate-audit.v1"
SOURCE_STATUS = "OBSERVATIONAL_TMINUS1_LATE_MASS_RESIDUALS_NOT_PROMOTED"
SOURCE_GIT_BLOB_SHA1 = "f4650a6cdb612f750970385d762af0d486894c6e"
DB_SHA256 = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"


def integer(x: Any) -> int | None:
    return x if type(x) is int else None


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def freeze_census(source: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if (source.get("schema") != SOURCE_SCHEMA
        or source.get("status") != SOURCE_STATUS
        or source.get("source_db_sha256") != DB_SHA256
        or source.get("source_stress_git_blob_sha1") !=
           "b6a373e4ea9f6274f9169c8e8aad4db7cc5e2f2e"):
        raise ValueError("wrong frozen observational prereq schema/status")
    summary = source.get("summary")
    census = source.get("all_424_side_controls")
    residuals = source.get("original_71_observed_residuals")
    if not isinstance(summary, Mapping) or not isinstance(census, list) or not isinstance(residuals, list):
        raise ValueError("frozen observed arrays are missing")
    if (summary.get("total_sides") != 424
        or summary.get("observed_residual_sides") != 71
        or summary.get("equal_to_frozen_conditional_component") != 353
        or summary.get("historical_horwasp_Tminus1_clans_seen") != 26
        or len(census) != 424 or len(residuals) != 71):
        raise ValueError("upstream frozen population size/status drift")
    seen = set()
    out = []
    for r in census:
        key = (r.get("game_id"), r.get("turn"), r.get("vcr_id"), r.get("side"))
        if (any(integer(x) is None or x <= 0 for x in key[:3])
            or key[3] not in ("left", "right") or key in seen):
            raise ValueError("invalid/duplicate VCR key")
        seen.add(key)
        if (integer(r.get("Tminus1_owner_race")) is None
            or integer(r.get("factual_current_VCR_mass_KT")) is None
            or integer(r.get("original_conditional_candidate_KT")) is None
            or r.get("observational_residual", {}).get("delta_KT") !=
               r["factual_current_VCR_mass_KT"] - r["original_conditional_candidate_KT"]):
            raise ValueError("frozen identity/mass consistency changed")
        if r["Tminus1_owner_race"] == 12:
            out.append(r)
    if len(out) != 26:
        raise ValueError("exactly 26 original Horwasp sides required")
    baseline_keys = {(
        r["game_id"], r["turn"], r["vcr_id"], r["side"]
    ) for r in residuals}
    if baseline_keys != {
        (r["game_id"], r["turn"], r["vcr_id"], r["side"])
        for r in census if r["observational_residual"]["delta_KT"] != 0
    }:
        raise ValueError("observational residual identities changed")
    if any(r["observational_residual"]["delta_KT"] == 0 for r in out):
        raise ValueError("original Horwasp residual control membership changed")
    return out


def hypothetical_clan_component(*, hull_mass: Any, clans: Any,
                                 cargo_capacity: Any,
                                 catalog_mass: Any) -> dict[str, Any]:
    """Pure T-1 hypothesis: mass = hull + FLOOR(hull*clans/cargo).

    All values provided independent of current VCR mass and left bay count.
    The floor rule has not been confirmed from host source/binary.
    """
    def abstain(reason: str) -> dict[str, Any]:
        return {
            "status": reason, "hypothetical_clan_component_KT": None,
            "hypothetical_no_carrier_mass_KT": None,
            "is_full_load_Tminus1": None,
            "full_mass_prediction_KT": None,
        }
    if (any(integer(x) is None for x in
            (hull_mass, clans, cargo_capacity, catalog_mass))):
        return abstain("ABSTAIN_INCOMPLETE_TMINUS1_CLAN_OR_CATALOG")
    if hull_mass <= 0 or cargo_capacity <= 0 or clans < 0 or clans > cargo_capacity:
        return abstain("ABSTAIN_INVALID_TMINUS1_CLAN_RANGE")
    if catalog_mass != hull_mass:
        return abstain("ABSTAIN_TMINUS1_HULL_CATALOG_MISMATCH")
    hypothetical_component = hull_mass * clans // cargo_capacity
    return {
        "status": "HYPOTHETICAL_TMINUS1_LINEAR_FLOOR_COMPONENT",
        "hypothetical_clan_component_KT": hypothetical_component,
        "hypothetical_no_carrier_mass_KT": hull_mass + hypothetical_component,
        "is_full_load_Tminus1": clans == cargo_capacity,
        "full_mass_prediction_KT": None,
        "linear_floor_rule_independently_proven": False,
        "same_turn_clans_unchanged_proven": False,
        "carrier_plus360_RNG_predicted": False,
    }


def no_mass_oracle_forecast(row: Mapping[str, Any]) -> dict[str, Any]:
    """Constrain function signature to archived T-1 inputs only."""
    historical = row.get("historical_Tminus1_owner_ship", {})
    prestate = row.get("independent_Tminus1_clan_and_capacity", {})
    hull = historical.get("tminus1_hull") if isinstance(historical, Mapping) else None
    if (not isinstance(historical, Mapping)
        or historical.get("status") != "RESOLVED_TMINUS1_OWNER_SHIP"
        or prestate.get("independently_precombat_seen") is not True):
        return {
            "status": "ABSTAIN_TMINUS1_OWNER_SHIP_UNRESOLVED",
            "hypothetical_clan_component_KT": None,
            "hypothetical_no_carrier_mass_KT": None,
            "full_mass_prediction_KT": None,
        }
    return hypothetical_clan_component(
        hull_mass=row.get("Tminus1_static_hull_mass"),
        clans=prestate.get("clans"),
        cargo_capacity=prestate.get("hull_cargo_capacity"),
        catalog_mass=hull.get("mass") if isinstance(hull, Mapping) else None,
    )


def evaluate_after_forecast(
    forecast: Mapping[str, Any], *,
    factual_vcr_mass: Any, side: str,
    left_vcr_bays_ANNOTATION_ONLY: Any,
) -> dict[str, Any]:
    """VCR factual fields are *never* inputs to no_mass_oracle_forecast."""
    observed = integer(factual_vcr_mass)
    hypothesis = forecast.get("hypothetical_no_carrier_mass_KT")
    if observed is None or observed <= 0:
        raise ValueError("invalid source factual mass")
    if hypothesis is None:
        return {
            "comparison_status": "ABSTAIN_PRESTATE_HYPOTHESIS_UNKNOWN",
            "observed_vcr_mass_KT": observed,
            "observed_minus_hypothetical_no_carrier_KT": None,
            "hypothetical_no_carrier_equals_factual_mass": None,
            "retrospective_carrier_branch_eligible": None,
            "hypothetical_plus360_equals_factual_mass": None,
        }
    left_bays = integer(left_vcr_bays_ANNOTATION_ONLY)
    condition = (side == "right" and left_bays is not None and left_bays > 0)
    return {
        "comparison_status": "POSTFORECAST_VCR_COMPARISON",
        "observed_vcr_mass_KT": observed,
        "observed_minus_hypothetical_no_carrier_KT": observed - hypothesis,
        "hypothetical_no_carrier_equals_factual_mass": hypothesis == observed,
        "retrospective_carrier_branch_eligible": condition,
        "hypothetical_plus360_equals_factual_mass": (
            hypothesis + 360 == observed if condition else None
        ),
        "plus360_is_a_counterfactual_not_a_predicted_RNG_outcome": True,
    }


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [
        r for r in rows if r["forecast"]["hypothetical_no_carrier_mass_KT"] is not None
    ]
    no_carrier = sum(
        r["evaluation"]["hypothetical_no_carrier_equals_factual_mass"] is True
        for r in eligible
    )
    alternative360 = sum(
        r["evaluation"]["hypothetical_plus360_equals_factual_mass"] is True
        for r in eligible
    )
    return {
        "sides": len(rows),
        "Tminus1_hypothesis_evaluable": len(eligible),
        "Tminus1_hypothesis_abstentions": len(rows) - len(eligible),
        "no_carrier_numeric_matches": no_carrier,
        "retrospective_plus360_numeric_matches": alternative360,
        "neither_numeric_branch_matches": len(eligible) - no_carrier - alternative360,
        "Tminus1_full_load_count": sum(r["forecast"].get("is_full_load_Tminus1") is True for r in rows),
        "Tminus1_partial_load_count": sum(r["forecast"].get("is_full_load_Tminus1") is False for r in rows),
        "observed_minus_Tminus1_no_carrier_by_KT": dict(sorted(Counter(
            str(r["evaluation"]["observed_minus_hypothetical_no_carrier_KT"])
            for r in eligible
        ).items())),
        "no_full_combat_mass_predictions": True,
    }


def build_report(source: Mapping[str, Any], raw_sha: str) -> dict[str, Any]:
    population = freeze_census(source)
    by_ship: dict[tuple[int, int, int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for r in population:
        if (integer(r.get("owner_id")) is None
            or integer(r.get("ship_id")) is None
            or r["ship_id"] <= 0):
            raise ValueError("frozen Horwasp ship identity missing")
        by_ship[(r["game_id"], r["turn"], r["owner_id"], r["ship_id"])].append(r)
    annotations = []
    chains = []
    for key, group in sorted(by_ship.items()):
        ordered = sorted(group, key=lambda x:(x["vcr_id"], x["side"]))
        entries = []
        for i, row in enumerate(ordered):
            # Pre-VCR calculation uses ONLY frozen T-1 facts.
            prediction = no_mass_oracle_forecast(row)
            observed = row["factual_current_VCR_mass_KT"]
            # Future/CURRENT VCR left bays enter only AFTER prediction.
            evaluation = evaluate_after_forecast(
                prediction, factual_vcr_mass=observed, side=row["side"],
                left_vcr_bays_ANNOTATION_ONLY=row["observational_residual"].get(
                    "VCR_left_baycount_observed"
                ),
            )
            preceding = ordered[i-1] if i else None
            record = {
                "game_id": row["game_id"], "turn": row["turn"],
                "vcr_id": row["vcr_id"], "side": row["side"],
                "ship_id": row["ship_id"], "owner_id": row["owner_id"],
                "hull_id": row["hull_id"], "cohort": row["cohort"],
                "Tminus1_static_hull_mass_KT": row["Tminus1_static_hull_mass"],
                "independent_Tminus1_clans": row["independent_Tminus1_clan_and_capacity"]["clans"],
                "independent_Tminus1_cargo_capacity": row["independent_Tminus1_clan_and_capacity"]["hull_cargo_capacity"],
                "Tminus1_owner_ship_status": row["historical_Tminus1_owner_ship"]["status"],
                "VCR_ID_order_label": (
                    "FIRST_BY_VCR_ID_IN_SELECTED_WINDOW" if i == 0
                    else "REPEATED_SHIP_BY_VCR_ID_IN_SELECTED_WINDOW"
                ),
                "VCR_ID_order_is_proven_host_execution_order": False,
                "forecast": prediction,
                "evaluation": evaluation,
                "observed_minus_preceding_VCR_mass_KT": (
                    observed - preceding["factual_current_VCR_mass_KT"]
                    if preceding else None
                ),
            }
            annotations.append(record)
            entries.append({
                "vcr_id": row["vcr_id"],
                "side": row["side"],
                "observed_VCR_mass_KT": observed,
                "factual_minus_preceding_VCR_mass_KT":
                    record["observed_minus_preceding_VCR_mass_KT"],
                "hypothetical_Tminus1_no_carrier_mass_KT":
                    prediction["hypothetical_no_carrier_mass_KT"],
            })
        if len(entries)>1:
            chains.append({
                "game_id": key[0], "turn": key[1],
                "owner_id": key[2], "ship_id": key[3],
                "VCR_ID_order_is_proven_host_execution_order": False,
                "VCRs_by_id_NOT_proven_execution_sequence": entries,
            })
    first = [r for r in annotations if r["VCR_ID_order_label"].startswith("FIRST")]
    repeats = [r for r in annotations if r["VCR_ID_order_label"].startswith("REPEATED")]
    if len(annotations) != 26:
        raise ValueError("incomplete Horwasp cohort")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_observational_report_git_blob_sha1": raw_sha,
        "source_db_sha256": DB_SHA256,
        "population": {
            "frozen_total_ship_vcr_sides": 424,
            "frozen_observed_residual_sides": 71,
            "original_horwasp_sides": 26,
            "distinct_horwasp_ships_by_game_turn_owner": len(by_ship),
        },
        "summary_all_26": summarize(annotations),
        "summary_first_by_VCR_ID": summarize(first),
        "summary_repeated_by_VCR_ID": summarize(repeats),
        "frozen_horwasp_side_evaluations": sorted(
            annotations, key=lambda x:(x["game_id"],x["turn"],x["vcr_id"],x["side"])
        ),
        "repeated_ship_VCR_ID_chains": chains,
        "scientific_boundary": (
            "T-1 player ship clan/cargo and time-indexed hull mass were fixed "
            "BEFORE factual VCR mass comparison. Floor linear interpolation "
            "is a falsifiable HYPOTHESIS, NOT an established host formula. "
            "VCR numeric ordering does not establish host execution chronology. "
            "Current VCR fighter bays only describe retrospective carrier "
            "eligibility; +360 is not a predicted RNG decision. Other mass "
            "effects and phase transitions remain unmodeled. No mass solver "
            "or production executor promotion."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--frozen-prestate-audit", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        raw = a.frozen_prestate_audit.read_bytes()
        digest = git_blob_sha1(raw)
        if digest != SOURCE_GIT_BLOB_SHA1:
            raise ValueError("frozen published prestate audit Git blob SHA mismatch")
        print("[horwasp-v1] source immutable Git blob verified", flush=True)
        data = json.loads(raw)
        report = build_report(data, digest)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = a.output.with_suffix(a.output.suffix+".tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    print("===== INDEPENDENT T-1 HORWASP CLAN HYPOTHESIS V1 =====")
    print("status:", report["status"])
    print("all sides:", report["summary_all_26"])
    print("first VCR-ID:", report["summary_first_by_VCR_ID"])
    print("repeated VCR-ID:", report["summary_repeated_by_VCR_ID"])
    print("output:", a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
