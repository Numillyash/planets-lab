from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.movement_chunnel_context import (
    _numeric_friendly_code,
    _pre_chunnel_position,
    _sample_from_transition,
    extract_stable_chunnel_abilities,
)
from planets_lab.corpus.movement_context import (
    MOVE_MOST_CANDIDATE,
    MovementMissionConvention,
    _classify_owner_record,
)
from planets_lab.corpus.movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
    _resolved_value,
)
from planets_lab.corpus.movement_mine_context import (
    build_mine_evidence_context,
    classify_strong_mine_hit_transition,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _owner_record,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample

from damage_limited_warp_residual_audit import _max_warp_from_damage, _race_map
from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR
from mine_hit_hostorder_differential_audit import _owner_states


EXAMPLE_LIMIT = 100


def _parse_section(log_path: Path, bucket: str, expected_key: str) -> tuple[int, tuple[dict[str, Any], ...]]:
    text = log_path.read_text(encoding="utf-8")
    matches = re.findall(rf"^{re.escape(expected_key)}=\s*(\d+)\s*$", text, re.M)
    if not matches:
        raise ValueError(f"{expected_key} summary counter missing")
    expected = int(matches[-1])
    marker = f"-- {bucket} --"
    if marker not in text:
        raise ValueError(f"bucket marker missing: {marker}")
    section = text.split(marker, 1)[1]
    next_marker = re.search(r"^-- [a-z0-9_]+ --$|^===== ", section, re.M)
    if next_marker is not None:
        section = section[: next_marker.start()]

    values: list[dict[str, Any]] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        value = ast.literal_eval(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-dict example in {bucket}")
        values.append(value)
    if len(values) != expected:
        raise ValueError(
            f"{bucket} examples truncated: expected {expected}, parsed {len(values)}; "
            "re-run the producer with a larger --examples value"
        )
    return expected, tuple(values)


def _case_key(item: Mapping[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(item["game"]),
        int(item["turn"]),
        int(item["tower_ship"]),
        int(item["target_ship"]),
    )


def _effective_damage_sample(sample: MovementSample, *, effective_warp: int) -> MovementSample:
    return MovementSample(
        turn=sample.turn,
        ship_id=sample.ship_id,
        x=sample.x,
        y=sample.y,
        target_x=sample.target_x,
        target_y=sample.target_y,
        warp=effective_warp,
        next_x=sample.next_x,
        next_y=sample.next_y,
        hull_id=sample.hull_id,
        gravitonic=sample.gravitonic,
        game_id=sample.game_id,
    )


def _nonzero_transfer_fields(raw: Mapping[str, Any]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for key, value in raw.items():
        normalized = str(key).lower().replace("_", "").replace("-", "")
        if not normalized.startswith("transfer"):
            continue
        if normalized in {"transfertargetid", "transfertargettype"}:
            continue
        if value in (None, 0, 0.0, "", "0", False):
            continue
        found[str(key)] = value
    return dict(sorted(found.items()))


def _transfer_target_id(raw: Mapping[str, Any]) -> int | None:
    for key in ("transfertargetid", "transfer_target_id"):
        value = _intish(raw.get(key))
        if value is not None and value > 0:
            return value
    return None


def _transfer_candidates(
    *,
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    turn: int,
    tower_id: int,
    target_id: int,
    tower_owner: int,
    tower_raw: Mapping[str, Any],
    target_raw: Mapping[str, Any],
) -> dict[str, Any]:
    outbound_tower = _nonzero_transfer_fields(tower_raw)
    outbound_target = _nonzero_transfer_fields(target_raw)
    inbound: list[dict[str, Any]] = []

    for (candidate_turn, candidate_ship), records in ship_groups.items():
        if candidate_turn != turn or candidate_ship in {tower_id, target_id}:
            continue
        current = [
            record
            for record in records
            if record.player_id == tower_owner and record.is_current
        ]
        if len(current) != 1:
            continue
        raw = current[0].raw
        transfer_fields = _nonzero_transfer_fields(raw)
        if not transfer_fields:
            continue
        transfer_target = _transfer_target_id(raw)
        if transfer_target not in {tower_id, target_id}:
            continue
        inbound.append(
            {
                "source_ship": candidate_ship,
                "target_ship": transfer_target,
                "fields": transfer_fields,
            }
        )

    return {
        "tower_outbound": outbound_tower,
        "target_outbound": outbound_target,
        "inbound_visible_to_tower_owner": tuple(inbound),
    }


def _targeted_chunnel_matches(
    *,
    before_turn: int,
    after_turn: int,
    ship_id: int,
    owner_id: int,
    observed: tuple[int, int],
    abilities: Any,
    entities: Any,
    ship_groups: Any,
    transition_by_key: Any,
    planets: tuple[tuple[int, int, int], ...],
    storms: tuple[Any, ...],
) -> tuple[dict[str, Any], ...]:
    target_before = entities.get(("ship", before_turn, ship_id))
    if target_before is None:
        return ()
    target_hull = _intish(_resolved_value(target_before, "hullid"))
    if target_hull not in abilities.target_hull_ids:
        return ()

    convention = MovementMissionConvention()
    target_code = ship_id % 1000
    matches: list[dict[str, Any]] = []
    for (kind, turn, initiator_id), entity in entities.items():
        if kind != "ship" or turn != before_turn or initiator_id == ship_id:
            continue
        initiator_hull = _intish(_resolved_value(entity, "hullid"))
        if initiator_hull not in abilities.initiator_hull_ids:
            continue
        candidate_owner_id, owner = _owner_record(ship_groups.get((before_turn, initiator_id), ()))
        if candidate_owner_id != owner_id or owner is None:
            continue
        if _classify_owner_record(owner, convention=convention) != MOVE_MOST_CANDIDATE:
            continue
        if _numeric_friendly_code(owner) != target_code:
            continue
        transition = transition_by_key.get((before_turn, after_turn, initiator_id))
        if transition is None:
            continue
        initiator_sample = _sample_from_transition(transition, entities)
        if initiator_sample is None or initiator_sample.observed_destination != observed:
            continue
        pre_position, status = _pre_chunnel_position(
            initiator_sample,
            planets=planets,
            storms=storms,
        )
        if pre_position is None or pre_position == observed:
            continue
        matches.append(
            {
                "initiator_ship": initiator_id,
                "pre_chunnel_position": pre_position,
                "destination": observed,
                "status": status,
            }
        )
    return tuple(matches)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify the exact finite-fuel Tow residual left after ordinary warp-well handling "
            "against already-modelled storm, mine, damage and Chunnel context, while inventorying "
            "submitted transfer orders as phase-state confounders. Evidence mining only."
        )
    )
    parser.add_argument("--discovery-log", type=Path, required=True)
    parser.add_argument("--warpwell-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    _, discovery_cases = _parse_section(
        args.discovery_log,
        "phase_neither_possible",
        "phase_neither_possible",
    )
    residual_count, residual_cases = _parse_section(
        args.warpwell_log,
        "phase_warpwell_neither_possible",
        "phase_warpwell_neither_possible",
    )
    discovery_by_key = {_case_key(item): item for item in discovery_cases}
    residual_by_game: dict[int, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for residual in residual_cases:
        key = _case_key(residual)
        original = discovery_by_key.get(key)
        if original is None:
            raise ValueError(f"warp-well residual not present in discovery population: {key}")
        residual_by_game[key[0]].append((original, residual))

    totals: Counter[str] = Counter()
    totals["residual_input"] = residual_count
    cases: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW EXTERNAL-CONTEXT FOLLOW-UP =====")
    print("residual_input=", residual_count)

    for game_id in sorted(residual_by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.is_file():
            raise FileNotFoundError(archive_path)
        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        planets_by_turn = _planet_tuples_by_turn(entities)
        transition_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }
        races = _race_map(prepared.snapshots)
        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(prepared.snapshots)
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )
        abilities = extract_stable_chunnel_abilities(archive_data)
        game_counts: Counter[str] = Counter()

        for original, residual in residual_by_game[game_id]:
            before_turn = int(original["turn"])
            after_turn = int(original["after_turn"])
            tower_id = int(original["tower_ship"])
            target_id = int(original["target_ship"])
            tower_owner = int(original["tower_owner"])
            target_owner = int(original["target_owner"])
            hull_id = int(original["tower_hull"])
            warp = int(original["tower_warp"])
            origin = tuple(int(value) for value in original["origin"])
            waypoint = tuple(int(value) for value in original["waypoint"])
            observed = tuple(int(value) for value in original["observed"])

            owner_id, tower_raw, tower_after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=tower_id,
            )
            target_owner_id, target_raw, _, target_same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=target_id,
            )
            if (
                owner_id != tower_owner
                or target_owner_id != target_owner
                or tower_raw is None
                or target_raw is None
                or tower_after_raw is None
                or not same_identity
                or not target_same_identity
            ):
                totals["identity_or_owner_state_mismatch"] += 1
                game_counts["identity_or_owner_state_mismatch"] += 1
                continue

            transition = transition_by_key.get((before_turn, after_turn, tower_id))
            embedded_turn = (
                int(transition.before_embedded_turn)
                if transition is not None
                else before_turn
            )
            sample = MovementSample(
                turn=embedded_turn,
                ship_id=tower_id,
                x=origin[0],
                y=origin[1],
                target_x=waypoint[0],
                target_y=waypoint[1],
                warp=warp,
                next_x=observed[0],
                next_y=observed[1],
                hull_id=hull_id,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS,
                game_id=game_id,
            )
            planets = planets_by_turn.get(before_turn, ())
            baseline_category = _movement_category(sample, planets=planets)

            mine_evidence = classify_strong_mine_hit_transition(
                context=mine_context,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=tower_id,
                owner_id=tower_owner,
                before_raw=tower_raw,
                sample=sample,
            )
            if mine_evidence is not None:
                totals[f"mine:{mine_evidence.category}"] += 1
                game_counts["mine_context"] += 1

            race_id = races.get(tower_owner)
            before_damage = _intish(tower_raw.get("damage"))
            after_damage = _intish(tower_after_raw.get("damage"))
            damage_limit = _max_warp_from_damage(before_damage, race_id)
            damage_effective_warp = min(warp, damage_limit) if damage_limit is not None else None
            damage_category = None
            if damage_effective_warp is not None and damage_effective_warp < warp:
                damage_sample = _effective_damage_sample(sample, effective_warp=damage_effective_warp)
                damage_category = _movement_category(damage_sample, planets=planets)
                if damage_category in GEOMETRY_EXPLAINED_CATEGORIES:
                    totals["damage_limited_exact"] += 1
                    game_counts["damage_limited_exact"] += 1

            storm_category = None
            storm_status = None
            if after_turn in storm_conflicts:
                storm_status = "conflict"
                totals["storm_context_conflict"] += 1
            elif after_turn in storm_invalid:
                storm_status = "invalid"
                totals["storm_context_invalid"] += 1
            else:
                storm_category, storm_status = _storm_expected_category(
                    sample,
                    storms=storms_by_turn.get(after_turn, ()),
                    planets=planets,
                )
                if storm_category is not None:
                    totals[f"storm:{storm_category}"] += 1
                    game_counts["storm_context"] += 1

            chunnel_matches: tuple[dict[str, Any], ...] = ()
            if after_turn not in storm_conflicts and after_turn not in storm_invalid:
                chunnel_matches = _targeted_chunnel_matches(
                    before_turn=before_turn,
                    after_turn=after_turn,
                    ship_id=tower_id,
                    owner_id=tower_owner,
                    observed=observed,
                    abilities=abilities,
                    entities=entities,
                    ship_groups=ship_groups,
                    transition_by_key=transition_by_key,
                    planets=planets,
                    storms=storms_by_turn.get(after_turn, ()),
                )
            if chunnel_matches:
                totals["observed_chunnel_target_route"] += 1
                game_counts["observed_chunnel_target_route"] += 1

            transfers = _transfer_candidates(
                ship_groups=ship_groups,
                turn=before_turn,
                tower_id=tower_id,
                target_id=target_id,
                tower_owner=tower_owner,
                tower_raw=tower_raw,
                target_raw=target_raw,
            )
            transfer_flag = any(
                (
                    transfers["tower_outbound"],
                    transfers["target_outbound"],
                    transfers["inbound_visible_to_tower_owner"],
                )
            )
            if transfer_flag:
                totals["submitted_transfer_confounder"] += 1
                game_counts["submitted_transfer_confounder"] += 1

            external_flags: list[str] = []
            if mine_evidence is not None:
                external_flags.append(f"mine:{mine_evidence.category}")
            if damage_category in GEOMETRY_EXPLAINED_CATEGORIES:
                external_flags.append(f"damage:{damage_category}")
            if storm_category is not None:
                external_flags.append(f"storm:{storm_category}")
            if chunnel_matches:
                external_flags.append("observed_chunnel_target_route")
            if transfer_flag:
                external_flags.append("submitted_transfer_confounder")

            if external_flags:
                totals["with_known_context_or_transfer_confounder"] += 1
                game_counts["with_known_context_or_transfer_confounder"] += 1
            else:
                totals["without_known_context_or_transfer_confounder"] += 1
                game_counts["without_known_context_or_transfer_confounder"] += 1

            totals["classified_cases"] += 1
            game_counts["classified_cases"] += 1
            cases.append(
                {
                    "game": game_id,
                    "turn": before_turn,
                    "after_turn": after_turn,
                    "tower_ship": tower_id,
                    "target_ship": target_id,
                    "tower_owner": tower_owner,
                    "target_owner": target_owner,
                    "hull": hull_id,
                    "race": race_id,
                    "warp": warp,
                    "origin": origin,
                    "waypoint": waypoint,
                    "observed": observed,
                    "geometry_endpoint": tuple(int(v) for v in original["geometry_endpoint"]),
                    "observed_planet_id": residual.get("observed_planet_id"),
                    "observed_distance": round(hypot(observed[0] - origin[0], observed[1] - origin[1]), 3),
                    "baseline_category": baseline_category,
                    "before_damage": before_damage,
                    "after_damage": after_damage,
                    "damage_warp_limit": damage_limit,
                    "damage_effective_warp": damage_effective_warp,
                    "damage_category": damage_category,
                    "mine_evidence": (
                        {
                            "category": mine_evidence.category,
                            "damage_hits": mine_evidence.damage_hits,
                            "slowdown_hits": mine_evidence.slowdown_hits,
                        }
                        if mine_evidence is not None
                        else None
                    ),
                    "storm_status": storm_status,
                    "storm_category": storm_category,
                    "chunnel_matches": chunnel_matches,
                    "submitted_transfers": transfers,
                    "known_context_or_transfer_flags": tuple(external_flags),
                }
            )

        print({"game": game_id, "cache_hit": cache_hit, **dict(sorted(game_counts.items()))}, flush=True)

    if totals["classified_cases"] + totals["identity_or_owner_state_mismatch"] != totals["residual_input"]:
        raise AssertionError(
            "external-context case accounting mismatch: "
            f"input={totals['residual_input']} classified={totals['classified_cases']} "
            f"state_mismatch={totals['identity_or_owner_state_mismatch']}"
        )

    print("\n===== SUMMARY =====")
    for key in (
        "residual_input",
        "classified_cases",
        "identity_or_owner_state_mismatch",
        "with_known_context_or_transfer_confounder",
        "without_known_context_or_transfer_confounder",
        "damage_limited_exact",
        "observed_chunnel_target_route",
        "submitted_transfer_confounder",
        "storm_context_conflict",
        "storm_context_invalid",
    ):
        print(f"{key}= {totals[key]}")
    for key, count in sorted(totals.items()):
        if key.startswith("mine:") or key.startswith("storm:"):
            print(f"{key}= {count}")

    print("\n===== CASES =====")
    for case in cases[: args.examples]:
        print(case)

    print("\n===== INTERPRETATION =====")
    print(
        "The input is exactly the Tow population still unexplained after ordinary warp-well handling. "
        "Mine, storm and damage checks reuse the current movement-context classifiers instead of inventing Tow-only rules."
    )
    print(
        "Chunnel detection here is deliberately narrow: it proves only the candidate tower itself as an observed target-hull route. "
        "A negative result does not exclude passenger Chunnel relocation and must not be used as such."
    )
    print(
        "Submitted transfer fields are confounder inventory only. They do not establish successful transfer execution, receiver capacity, "
        "foreign inbound state, or the exact Tow-phase mass/fuel state."
    )
    print("finite-fuel Tow remains OPEN; this diagnostic never changes rule status or planets-intel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
