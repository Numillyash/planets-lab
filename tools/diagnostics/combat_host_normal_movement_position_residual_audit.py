from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_context import MovementMissionConvention
from planets_lab.corpus.movement_differential import _entity_map, _intish, _planet_tuples_by_turn
from planets_lab.corpus.movement_mine_context import (
    build_mine_evidence_context,
    classify_strong_mine_hit_transition,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
    _storm_consensus_by_turn,
)
from planets_lab.corpus.movement_storm_context import storm_expected_category_for_mode
from planets_lab.corpus.normalizer import _decode_member_json
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample

from combat_host_candidate_set_audit import _owner_rows_for_turn
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_normal_movement_position_audit import _effective_requested_warp
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, SPECIAL_GAME_ID
from combat_host_residual_physical_stack_audit import _xy


POSITION_SCHEMA = "planets-lab.combat-host-normal-movement-position-audit.v2"
SCHEMA = "planets-lab.combat-host-normal-movement-position-residual-audit.v1"


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return None


def _find_named_setting(value: Any, normalized_name: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("_", "").replace("-", "")
            if normalized == normalized_name:
                found.append(child)
            if isinstance(child, (Mapping, list, tuple)):
                found.extend(_find_named_setting(child, normalized_name))
    elif isinstance(value, (list, tuple)):
        for child in value:
            if isinstance(child, (Mapping, list, tuple)):
                found.extend(_find_named_setting(child, normalized_name))
    return found


def _archive_nuionstorms_consensus(archive_data: bytes) -> tuple[bool | None, tuple[str, ...]]:
    """Read only the stable public mechanical setting from first/last turn payloads."""

    members = turn_members(archive_data)
    if not members:
        return None, ()
    selected = [members[0]]
    if members[-1].name != members[0].name:
        selected.append(members[-1])
    raw_by_name = read_archive_members(archive_data, [member.name for member in selected])
    parsed: set[bool] = set()
    raw_values: set[str] = set()
    for member in selected:
        payload, _ = _decode_member_json(raw_by_name[member.name], member)
        values = _find_named_setting(payload, "nuionstorms")
        for value in values:
            raw_values.add(repr(value))
            flag = _boolish(value)
            if flag is not None:
                parsed.add(flag)
    return (next(iter(parsed)) if len(parsed) == 1 else None), tuple(sorted(raw_values))


def _mismatch_rows(position_report: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    if position_report.get("schema") != POSITION_SCHEMA:
        raise ValueError(f"position report schema must be {POSITION_SCHEMA}")
    summary = position_report.get("summary")
    if not isinstance(summary, Mapping):
        raise ValueError("position report has no summary")
    occurrences = summary.get("ship_occurrences")
    if not isinstance(occurrences, Mapping):
        raise ValueError("position report has no ship_occurrences summary")
    expected = _intish(occurrences.get("position_mismatch")) or 0
    examples = position_report.get("examples")
    if not isinstance(examples, list):
        raise ValueError("position report examples must be a list")
    rows = tuple(row for row in examples if isinstance(row, Mapping))
    if len(rows) != expected:
        raise ValueError(
            "position report does not contain every mismatch example; rerun the position audit "
            f"with --example-limit >= {expected}"
        )
    return rows


def _storm_candidates(
    *,
    sample: MovementSample,
    storms: Sequence[Any],
    planets: Sequence[tuple[int, int, int]],
    nuionstorms: bool | None,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    nu_category, nu_status = storm_expected_category_for_mode(
        sample,
        storms=storms,
        planets=planets,
        nuionstorms=True,
    )
    classic_category, classic_status = storm_expected_category_for_mode(
        sample,
        storms=storms,
        planets=planets,
        nuionstorms=False,
    )

    candidates: list[str] = []
    if nuionstorms is True and nu_category is not None:
        candidates.append(f"ion_storm_nu:{nu_category}")
    elif nuionstorms is False and classic_category is not None:
        candidates.append(f"ion_storm_classic:{classic_category}")
    elif nuionstorms is None:
        if nu_category is not None:
            candidates.append(f"ion_storm_nu_candidate:{nu_category}")
        if classic_category is not None:
            candidates.append(f"ion_storm_classic_candidate:{classic_category}")

    return tuple(candidates), {
        "nuionstorms": nuionstorms,
        "nu_category": nu_category,
        "nu_status": nu_status,
        "classic_category": classic_category,
        "classic_status": classic_status,
    }


def _candidate_families(candidates: Sequence[str]) -> tuple[str, ...]:
    families: set[str] = set()
    for candidate in candidates:
        if candidate.startswith("ion_storm_"):
            families.add("ion_storm")
        elif candidate.startswith("mine:"):
            families.add("mine")
        elif candidate.startswith("observed_tow_route"):
            families.add("tow")
        else:
            families.add(candidate.split(":", 1)[0])
    return tuple(sorted(families))


def run(args: argparse.Namespace) -> dict[str, Any]:
    position_report = json.loads(args.position_report.read_text(encoding="utf-8"))
    mismatch_rows = _mismatch_rows(position_report)
    by_game: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in mismatch_rows:
        game_id = _intish(row.get("game_id"))
        if game_id is None or game_id == SPECIAL_GAME_ID:
            raise ValueError(f"invalid ordinary mismatch game_id: {row.get('game_id')!r}")
        by_game[int(game_id)].append(row)

    summary: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    candidate_counts: Counter[str] = Counter()
    rows_out: list[dict[str, Any]] = []

    for game_id, game_rows in sorted(by_game.items()):
        archive_path = args.archive_dir / f"game-{game_id}.zip"
        if not archive_path.exists():
            raise FileNotFoundError(archive_path)
        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        entities = _entity_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities)
        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(prepared.snapshots)
        races, _race_conflicts = _player_races(prepared.snapshots)
        nuionstorms, nuionstorms_raw = _archive_nuionstorms_consensus(archive_data)
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )

        valid_pairs = {
            (int(row["battle_turn"]) - 1, int(row["battle_turn"]))
            for row in game_rows
        }
        observed_tow_targets, _tow_counts = _observed_tow_targets(
            entities=entities,
            ship_groups=ship_groups,
            valid_pairs=valid_pairs,
            convention=MovementMissionConvention(),
        )

        owner_rows_cache: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}
        for source_row in sorted(game_rows, key=lambda item: (int(item["battle_turn"]), int(item["ship_id"]))):
            summary["mismatch_rows"] += 1
            battle_turn = int(source_row["battle_turn"])
            before_turn = battle_turn - 1
            ship_id = int(source_row["ship_id"])
            owner_id = int(source_row["owner_id"])
            owner_rows = owner_rows_cache.setdefault(
                before_turn,
                _owner_rows_for_turn(ship_groups, before_turn),
            )
            owner_entry = owner_rows.get(ship_id)
            if owner_entry is None or owner_entry[0] != owner_id:
                summary["owner_current_missing"] += 1
                rows_out.append({**dict(source_row), "context_status": "owner_current_missing"})
                continue
            _, raw = owner_entry

            origin = _xy(raw)
            target_x = _intish(raw.get("targetx"))
            target_y = _intish(raw.get("targety"))
            hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
            factual_site = source_row.get("factual_site")
            if (
                origin[0] is None
                or origin[1] is None
                or target_x is None
                or target_y is None
                or not isinstance(factual_site, list)
                or len(factual_site) != 2
            ):
                summary["sample_unresolved"] += 1
                rows_out.append({**dict(source_row), "context_status": "sample_unresolved"})
                continue

            effective_warp, warp_issue = _effective_requested_warp(
                raw,
                race_id=races.get(owner_id),
            )
            if effective_warp is None or warp_issue is not None:
                summary["sample_unresolved"] += 1
                rows_out.append(
                    {
                        **dict(source_row),
                        "context_status": "effective_warp_unresolved",
                        "warp_issue": warp_issue,
                    }
                )
                continue

            sample = MovementSample(
                turn=before_turn,
                ship_id=ship_id,
                x=int(origin[0]),
                y=int(origin[1]),
                target_x=int(target_x),
                target_y=int(target_y),
                warp=int(effective_warp),
                next_x=int(factual_site[0]),
                next_y=int(factual_site[1]),
                hull_id=int(hull_id) if hull_id is not None else None,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS if hull_id is not None else False,
            )

            candidates: list[str] = []
            storm_context: dict[str, Any]
            if battle_turn in storm_conflicts:
                storm_context = {"nuionstorms": nuionstorms, "status": "storm_context_conflict"}
            elif battle_turn in storm_invalid:
                storm_context = {"nuionstorms": nuionstorms, "status": "storm_context_invalid"}
            else:
                storm_candidates, storm_context = _storm_candidates(
                    sample=sample,
                    storms=storms_by_turn.get(battle_turn, ()),
                    planets=planets_by_turn.get(before_turn, ()),
                    nuionstorms=nuionstorms,
                )
                candidates.extend(storm_candidates)

            mine_evidence = classify_strong_mine_hit_transition(
                context=mine_context,
                before_turn=before_turn,
                after_turn=battle_turn,
                ship_id=ship_id,
                owner_id=owner_id,
                before_raw=raw,
                sample=sample,
            )
            if mine_evidence is not None:
                candidates.append(f"mine:{mine_evidence.category}")

            tow_towers = observed_tow_targets.get((before_turn, ship_id), ())
            if tow_towers:
                candidates.append("observed_tow_route")

            families = _candidate_families(candidates)
            if not families:
                context_status = "unresolved"
                summary["unresolved"] += 1
            elif len(families) == 1:
                context_status = "single_exact_context_family"
                summary["single_exact_context_family"] += 1
            else:
                context_status = "multiple_exact_context_families"
                summary["multiple_exact_context_families"] += 1

            for candidate in candidates:
                candidate_counts[candidate] += 1
            for family in families:
                family_counts[family] += 1

            after_entry = _owner_rows_for_turn(ship_groups, battle_turn).get(ship_id)
            after_raw = after_entry[1] if after_entry is not None and after_entry[0] == owner_id else None
            predicted = source_row.get("predicted")
            predicted_delta = None
            if isinstance(predicted, list) and len(predicted) == 2:
                predicted_delta = [
                    int(factual_site[0]) - int(predicted[0]),
                    int(factual_site[1]) - int(predicted[1]),
                ]

            rows_out.append(
                {
                    **dict(source_row),
                    "before_turn": before_turn,
                    "origin": [int(origin[0]), int(origin[1])],
                    "hull_id": hull_id,
                    "effective_warp": effective_warp,
                    "prediction_delta": predicted_delta,
                    "nuionstorms_setting": nuionstorms,
                    "nuionstorms_raw_values": list(nuionstorms_raw),
                    "storm_context": storm_context,
                    "mine_context": (
                        {
                            "category": mine_evidence.category,
                            "damage_hits": mine_evidence.damage_hits,
                            "slowdown_hits": mine_evidence.slowdown_hits,
                        }
                        if mine_evidence is not None
                        else None
                    ),
                    "observed_tow_tower_ids": list(tow_towers),
                    "after_state": (
                        {
                            "position": list(_xy(after_raw)) if after_raw is not None else None,
                            "damage": _intish(after_raw.get("damage")) if after_raw is not None else None,
                            "supplies": _intish(after_raw.get("supplies")) if after_raw is not None else None,
                            "fuel": _intish(after_raw.get("neutronium")) if after_raw is not None else None,
                            "warp": _intish(after_raw.get("warp")) if after_raw is not None else None,
                        }
                        if after_raw is not None
                        else None
                    ),
                    "candidate_contexts": list(candidates),
                    "candidate_families": list(families),
                    "context_status": context_status,
                }
            )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "source_position_report": str(args.position_report),
        "summary": {
            **{key: int(value) for key, value in sorted(summary.items())},
            "candidate_family_counts": {
                key: int(value) for key, value in sorted(family_counts.items())
            },
            "candidate_context_counts": {
                key: int(value) for key, value in sorted(candidate_counts.items())
            },
        },
        "rows": rows_out,
        "evidence_boundary": (
            "Residual attribution only. The position report remains the independent T-1 predictor result. "
            "This audit may use post-turn survivor state and route-equivalent observed Tow evidence to explain "
            "already-observed mismatches; those facts must never be fed back into candidate-set prediction. "
            "Ion-storm candidates require exact endpoint equality under the archived nuionstorms setting when that "
            "setting resolves; if the setting is unknown, Nu/classic exact matches remain explicitly mode-conditional. "
            "Mine attribution uses only the existing strong DIFF_VERIFIED mine classifier."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify the bounded residuals from the combat T-1 normal-movement position gate."
    )
    parser.add_argument("--position-report", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT NORMAL-MOVEMENT POSITION RESIDUAL AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("RESIDUAL CONTEXT ROWS:")
    for row in report["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: attribution-only gate; post-turn context is never candidate-set predictor input.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
