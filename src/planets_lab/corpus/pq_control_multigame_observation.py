"""Frozen-control multi-game PPQ observational identity survey.

Runs ONLY previously permitted completed PPQ games with archived adjacent
coverage. Each game uses the existing bounded strict two-member scanner,
which checks typed embedded identity and game.turn delta=+1. The output
contains only aggregate counts, never entity IDs, private fields, or
unverified ship-build/Host causal claims. No public100/heldout scans.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from planets_lab.corpus.pq_historical_readiness import report_from_paths
from planets_lab.corpus.pq_bounded_window_selection import select_bounded_pq_windows

SCHEMA = "planets-lab.pq-frozen-control-multigame-observation.v1"
KINDS = ("planets", "ships", "starbases")
MAX_GAMES = 8


def _empty_counts() -> dict[str, int]:
    return {
        "observed_in_both": 0,
        "newly_visible_owned_fresh_ids": 0,
        "no_longer_visible_owned_fresh_ids": 0,
        "before_fresh_owned_rows": 0,
        "after_fresh_owned_rows": 0,
        "before_unqualified_rows": 0,
        "after_unqualified_rows": 0,
    }


def _summarize_selection(game_id: int, selected: dict[str, Any]) -> dict[str, Any]:
    totals = {key: _empty_counts() for key in KINDS}
    accepted = 0
    rejected_source = 0
    base_provenance = Counter()
    discovery_windows: list[dict[str, Any]] = []
    templates = Counter()
    prioritypoint_directions = Counter()
    reference_by_stratum: dict[str, dict[str, Any]] = {}
    for window in selected["admissible_window_reports"]:
        observed = window["observed_owner_transition"]
        if observed.get("status") != "OBSERVED_OWNER_CURRENT_IDENTITY_INTERSECTION_ONLY":
            rejected_source += 1
            continue
        if observed.get("host_causal_verified") is not False:
            raise ValueError("noncausal observation guard violated")
        for key in KINDS:
            row = observed["entity_signatures"][key]
            for field in (
                "observed_in_both",
                "newly_visible_owned_fresh_ids",
                "no_longer_visible_owned_fresh_ids",
            ):
                value = row[field]
                if type(value) is not int or value < 0:
                    raise ValueError("invalid observed entity count")
                totals[key][field] += value
            for side in ("before", "after"):
                prefix = side + "_"
                for field, source in (
                    ("fresh_owned_rows", "fresh_owned_typed_rows"),
                    ("unqualified_rows", "unqualified_rows"),
                ):
                    n = row[side][source]
                    if type(n) is not int or n < 0:
                        raise ValueError("invalid observed source shape")
                    totals[key][prefix + field] += n
        fields = window.get("ship_appearance_source_field_audit")
        if type(fields) is not dict or fields.get("source_fields_match_causal_build_event") is not False:
            raise ValueError("ship appearance field-audit contract missing")
        candidates = observed["entity_signatures"]["ships"]["newly_visible_owned_fresh_ids"]
        if fields.get("newly_visible_owned_current_ship_ids_count") != candidates:
            raise ValueError("inconsistent ship candidate count")
        correlation = window.get("ship_appearance_noncausal_correlates")
        if type(correlation) is not dict or correlation.get("host_causal_verified") is not False:
            raise ValueError("noncausal appearance correlate contract missing")
        if correlation.get("newly_visible_owned_current_ship_count") != candidates:
            raise ValueError("inconsistent appearance correlate candidate count")
        baseline = window.get("existing_owned_ship_template_reference")
        if type(baseline) is not dict or baseline.get("host_causal_verified") is not False:
            raise ValueError("existing ship template reference guard missing")
        if baseline.get("newly_visible_owned_ship_identity_count") != candidates:
            raise ValueError("existing ship template reference candidate mismatch")
        stratum = baseline.get("stratum")
        if stratum not in (
            "WINDOW_WITH_NEWLY_VISIBLE_OWN_SHIP",
            "WINDOW_WITHOUT_NEWLY_VISIBLE_OWN_SHIP",
        ) or (stratum == "WINDOW_WITH_NEWLY_VISIBLE_OWN_SHIP") != (candidates > 0):
            raise ValueError("existing ship reference stratum mismatch")
        metric = reference_by_stratum.setdefault(stratum, {
            "windows": 0, "reference_comparisons": 0,
            "matching_preexisting_ship_templates": 0,
            "nonmatching_preexisting_ship_templates": 0,
            "untyped_preexisting_ship_specs": 0,
            "status_counts": {},
        })
        status = baseline.get("status")
        allowable = (
            "REFERENCE_TYPED_PERSISTENT_OWNED_SHIPS",
            "ABSTAIN_SOURCE_ARRAY_OR_SHIP_ID_AMBIGUOUS",
            "ABSTAIN_NO_UNIQUE_CURRENT_BASE",
            "ABSTAIN_NO_PERSISTENT_OWNED_SHIP_REFERENCE",
            "ABSTAIN_BASE_TEMPLATE_UNTYPED",
            "ABSTAIN_NO_TYPED_PERSISTENT_SHIP_SPECS",
        )
        if status not in allowable:
            raise ValueError("unknown existing ship reference status")
        metrics = {
            "reference_comparisons": "typed_stable_ship_base_template_comparisons",
            "matching_preexisting_ship_templates": "matches_before_base_hull_and_engine",
            "nonmatching_preexisting_ship_templates": "does_not_match_before_base_hull_and_engine",
            "untyped_preexisting_ship_specs": "stable_ships_with_untyped_hull_or_engine",
        }
        for key, field in metrics.items():
            number = baseline.get(field)
            if type(number) is not int or number < 0:
                raise ValueError("malformed existing ship reference count")
            metric[key] += number
        if (metric["matching_preexisting_ship_templates"] +
                metric["nonmatching_preexisting_ship_templates"] >
                metric["reference_comparisons"]):
            raise ValueError("reference comparison counters inconsistent")
        metric["windows"] += 1
        metric["status_counts"][status] = metric["status_counts"].get(status, 0) + 1
        if candidates > 0:
            compatibility = correlation["before_current_base_vs_new_ship"]
            pp_direction = correlation["observed_prioritypoints_trend"]
            if type(compatibility) is not str or type(pp_direction) is not str:
                raise ValueError("malformed appearance correlate categories")
            templates[compatibility] += 1
            prioritypoint_directions[pp_direction] += 1
            discovery_windows.append({
                "observed_before_base_template_and_pp": correlation,
                "archive_before_turn": window["before_archive_turn"],
                "archive_after_turn": window["after_archive_turn"],
                "embedded_before_turn": window["before_embedded_turn"],
                "embedded_after_turn": window["after_embedded_turn"],
                "newly_visible_owned_fresh_ship_count": candidates,
                "owned_source_field_audit": fields,
                "selection_type": "EXPLORATORY_POSTHOC_OBSERVED_IDENTITY",
                "verified_ship_build": False,
            })
        for side in ("before", "after"):
            provenance = window["starbase_provenance"][side]
            for name in (
                "fresh_owned_planet_linked_bases",
                "linked_owned_planet_bases_without_base_infoturn",
                "linked_owned_planet_bases_with_stale_base_infoturn",
                "unresolved_or_ambiguous_base_rows",
            ):
                value = provenance.get(name)
                if type(value) is int and value >= 0:
                    base_provenance[name] += value
                else:
                    raise ValueError("unresolved base diagnostic shape")
        accepted += 1
    return {
        "game_id": game_id,
        "queue_mode": "PPQ",
        "archive_adjacent_pairs_checked": selected["actually_checked_pairs"],
        "embedded_consecutive_pairs_admitted": selected["admissible_consecutive_embedded_pairs"],
        "owner_current_source_qualified_pairs": accepted,
        "owner_current_source_abstain_pairs": rejected_source,
        "refusal_counts": selected["refusal_counts"],
        "entity_identity_counts": totals,
        "exploratory_ship_appearance_windows": discovery_windows,
        "exploratory_ship_appearance_window_count": len(discovery_windows),
        "exploratory_before_base_template_status_counts": dict(sorted(templates.items())),
        "exploratory_prioritypoints_direction_counts": dict(sorted(prioritypoint_directions.items())),
        "existing_ship_template_reference_by_stratum": reference_by_stratum,
        "starbase_provenance_observations": dict(sorted(base_provenance.items())),
        "has_newly_visible_owned_fresh_ship_identity": (
            totals["ships"]["newly_visible_owned_fresh_ids"] > 0
        ),
        "does_not_attribute_ship_construction": True,
        "observed_windows_are_bounded_not_exhaustive": True,
    }


def survey_frozen_public_ppq(
    *, feature_index: Path, frozen_cohort: Path, archive_dir: Path,
    player_slot: int = 1, first_archive_turn: int = 1,
    max_pairs_per_game: int = 48, max_accepted_per_game: int = 8,
) -> dict[str, Any]:
    if any(type(n) is not int for n in (
        player_slot, first_archive_turn, max_pairs_per_game, max_accepted_per_game,
    )) or not (
        1 <= player_slot <= 50 and first_archive_turn >= 0
        and 1 <= max_pairs_per_game <= 64
        and 1 <= max_accepted_per_game <= 8
    ):
        raise ValueError("invalid bounded frozen PPQ survey scope")
    # Read the explicit frozen cohort and tiny preexisting feature index
    # BEFORE any individual ZIP gets accessed.
    readiness = report_from_paths(feature_index, frozen_cohort)
    targets = sorted(
        x["game_id"] for x in readiness["games"]
        if x["mode"] == "PPQ" and x["observational_candidate"]
    )
    if not targets or len(targets) > MAX_GAMES:
        raise ValueError("no eligible PPQ targets or survey scope exceeds cap")

    results: list[dict[str, Any]] = []
    aggregate = {name: _empty_counts() for name in KINDS}
    refusal: Counter[str] = Counter()
    total_checked = total_embedded = total_observed = total_abstained = 0
    games_with_ship_appearance = 0
    discovery_count = 0
    all_templates = Counter()
    all_pp_directions = Counter()
    all_reference: dict[str, dict[str, Any]] = {}
    failures = Counter()
    for game_id in targets:
        if not (archive_dir / f"game-{game_id}.zip").is_file():
            failures["APPROVED_GAME_ARCHIVE_MISSING"] += 1
            results.append({
                "game_id": game_id, "status": "ABSTAIN_ARCHIVE_MISSING",
                "owner_current_source_qualified_pairs": 0,
                "causal_queue_parity_verified": False,
            })
            continue
        try:
            selected = select_bounded_pq_windows(
                feature_index=feature_index, frozen_cohort=frozen_cohort,
                archive_dir=archive_dir, game_id=game_id,
                player_slot=player_slot, first_archive_turn=first_archive_turn,
                max_pairs=max_pairs_per_game,
                max_accepted=max_accepted_per_game,
            )
            if selected.get("nuhost_execution_verified") is not False:
                raise ValueError("unexpected causal promotion")
            item = _summarize_selection(game_id, selected)
        except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
            # Never surface any exception text originating in archival payload.
            if str(exc) == "unexpected causal promotion":
                raise
            failures["UNSUPPORTED_GAME_OR_ARCHIVE"] += 1
            results.append({
                "game_id": game_id, "status": "ABSTAIN_UNSUPPORTED_GAME_OR_ARCHIVE",
                "owner_current_source_qualified_pairs": 0,
                "causal_queue_parity_verified": False,
            })
            continue
        item["status"] = (
            "OBSERVED_OWNER_CURRENT_IDENTITY_WINDOWS"
            if item["owner_current_source_qualified_pairs"]
            else "ABSTAIN_NO_SOURCE_QUALIFIED_PAIR"
        )
        results.append(item)
        total_checked += item["archive_adjacent_pairs_checked"]
        total_embedded += item["embedded_consecutive_pairs_admitted"]
        total_observed += item["owner_current_source_qualified_pairs"]
        total_abstained += item["owner_current_source_abstain_pairs"]
        if item["has_newly_visible_owned_fresh_ship_identity"]:
            games_with_ship_appearance += 1
        discovery_count += item["exploratory_ship_appearance_window_count"]
        all_templates.update(item["exploratory_before_base_template_status_counts"])
        all_pp_directions.update(item["exploratory_prioritypoints_direction_counts"])
        for stratum, row in item["existing_ship_template_reference_by_stratum"].items():
            combined = all_reference.setdefault(stratum, {
                "windows": 0, "reference_comparisons": 0,
                "matching_preexisting_ship_templates": 0,
                "nonmatching_preexisting_ship_templates": 0,
                "untyped_preexisting_ship_specs": 0,
                "status_counts": {},
            })
            for name in (
                "windows", "reference_comparisons",
                "matching_preexisting_ship_templates",
                "nonmatching_preexisting_ship_templates",
                "untyped_preexisting_ship_specs",
            ):
                combined[name] += row[name]
            for status, count in row["status_counts"].items():
                combined["status_counts"][status] = (
                    combined["status_counts"].get(status, 0) + count
                )
        for kind in KINDS:
            for key, value in item["entity_identity_counts"][kind].items():
                aggregate[kind][key] += value
        refusal.update(item["refusal_counts"])
    return {
        "schema": SCHEMA,
        "source_feature_index_sha256": readiness["index_sha256"],
        "frozen_cohort_sha256": readiness["cohort_sha256"],
        "scoped_games": len(targets),
        "perspective_slot": player_slot,
        "first_archive_turn": first_archive_turn,
        "max_pairs_per_game": max_pairs_per_game,
        "max_accepted_per_game": max_accepted_per_game,
        "max_total_candidate_member_pairs": len(targets) * max_pairs_per_game,
        "games_with_qualified_observations": sum(
            x["status"] == "OBSERVED_OWNER_CURRENT_IDENTITY_WINDOWS"
            for x in results
        ),
        "games_with_newly_visible_owned_fresh_ship_identity": games_with_ship_appearance,
        "exploratory_ship_appearance_window_count": discovery_count,
        "exploratory_before_base_template_status_counts": dict(sorted(all_templates.items())),
        "exploratory_prioritypoints_direction_counts": dict(sorted(all_pp_directions.items())),
        "existing_ship_template_reference_by_stratum": all_reference,
        "existing_ship_reference_is_independent_negative_control": False,
        "posthoc_window_selection_not_independent_validation": True,
        "game_level_failures": dict(sorted(failures.items())),
        "archive_adjacent_pairs_checked": total_checked,
        "embedded_consecutive_pairs_admitted": total_embedded,
        "owner_current_source_qualified_pairs": total_observed,
        "owner_current_source_abstain_pairs": total_abstained,
        "refusal_counts": dict(sorted(refusal.items())),
        "entity_identity_counts": aggregate,
        "by_game": results,
        "only_predeclared_public_control_games": True,
        "no_sealed_holdout_or_public100_scan": True,
        "no_individual_entity_identifiers_emitted": True,
        "independently_complete_owner_ship_roster": False,
        "ship_appearance_is_construction_verified": False,
        "ship_disappearance_is_loss_verified": False,
        "planet_gained_is_colonization_verified": False,
        "queue_component_warehouse_and_pp_verified": False,
        "server_accepted_orders_verified": False,
        "host_causal_verified": False,
        "evidence": "BOUNDED_PUBLIC_PPQ_MULTIGAME_OWNER_CURRENT_OBSERVATION_NOT_HOST_CAUSAL",
    }
