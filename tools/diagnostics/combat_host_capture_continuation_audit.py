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

from planets_lab.corpus.feature_scope import (
    DEFAULT_FEATURE_INDEX_PATH,
    load_feature_scope,
)
from planets_lab.rules.combat import (
    ShipCaptureTransfer,
    apply_ship_terminal_batch,
    federation_recover_shields,
)

import combat_ship_chain_audit as chain_module
from combat_host_priority_intercept_audit import RAW_DIR


SCHEMA = "planets-lab.combat-host-capture-continuation-audit.v2"
DEFAULT_EXAMPLE_LIMIT = 80
KNOWN_DAMAGE_REPLAY_RESIDUALS = {
    (621253, 17, 84, 39, 45, 11, 7),
}
CARRY_FIELDS = (
    ("damage", "damage"),
    ("crew", "crew"),
    ("torpedoes", "torpedos"),
    ("fighters", "fighters"),
)


def _int(raw: Mapping[str, Any] | None, key: str) -> int | None:
    if not isinstance(raw, Mapping):
        return None
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _same_location(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
) -> bool:
    return bool(
        previous.get("position") is not None
        and previous.get("position") == current.get("position")
    )


def _other_appearance(
    by_vcr: Mapping[tuple[int, int, int], Sequence[Mapping[str, Any]]],
    appearance: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    key = (
        int(appearance["game_id"]),
        int(appearance["turn"]),
        int(appearance["vcr_id"]),
    )
    for other in by_vcr.get(key, ()):
        if int(other["ship_id"]) != int(appearance["ship_id"]):
            return other
    return None


def _other_is_planet(
    by_vcr: Mapping[tuple[int, int, int], Sequence[Mapping[str, Any]]],
    appearance: Mapping[str, Any],
) -> bool:
    key = (
        int(appearance["game_id"]),
        int(appearance["turn"]),
        int(appearance["vcr_id"]),
    )
    # The underlying replay is supported and every ship side becomes one
    # appearance. Exactly one ship appearance therefore means the other VCR
    # side is the planet/base combatant.
    return len(by_vcr.get(key, ())) == 1


def _shield_projection(
    *,
    terminal: Mapping[str, Any],
    current_start: Mapping[str, Any],
    previous_race_id: int | None,
) -> dict[str, Any]:
    terminal_shield = _int(terminal, "shield")
    terminal_damage = _int(terminal, "damage")
    current_shield = _int(current_start, "shield")
    exact = (
        terminal_shield == current_shield
        if terminal_shield is not None and current_shield is not None
        else None
    )

    pre_capture_fed_candidate = None
    pre_capture_fed_exact = None
    if (
        previous_race_id == 1
        and terminal_shield is not None
        and terminal_damage is not None
    ):
        recovered, _amount = federation_recover_shields(
            {
                "shield": terminal_shield,
                "damage": terminal_damage,
                "federation_crew_bonus": True,
            }
        )
        value = recovered.get("shield")
        if isinstance(value, int) and not isinstance(value, bool):
            pre_capture_fed_candidate = value
            pre_capture_fed_exact = (
                value == current_shield if current_shield is not None else None
            )

    if exact is True and pre_capture_fed_exact is True:
        model = "both"
    elif exact is True:
        model = "exact_carry"
    elif pre_capture_fed_exact is True:
        model = "pre_capture_federation_recovery"
    elif exact is False or pre_capture_fed_exact is False:
        model = "mismatch"
    else:
        model = "unknown"

    return {
        "terminal": terminal_shield,
        "current_start": current_shield,
        "exact_carry": exact,
        "pre_capture_federation_candidate": pre_capture_fed_candidate,
        "pre_capture_federation_exact": pre_capture_fed_exact,
        "model": model,
    }


def _active_ship_from_appearance(
    appearance: Mapping[str, Any],
) -> dict[str, Any]:
    start = appearance.get("start")
    start = start if isinstance(start, Mapping) else {}
    ship_id = int(appearance["ship_id"])
    hull_id = appearance.get("hull_id")
    owner_id = appearance.get("owner_id")
    race_id = appearance.get("race_id")
    if isinstance(hull_id, bool) or not isinstance(hull_id, int) or hull_id <= 0:
        raise ValueError("capture appearance hull unresolved")
    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id <= 0:
        raise ValueError("capture appearance owner unresolved")
    if isinstance(race_id, bool) or not isinstance(race_id, int) or race_id <= 0:
        raise ValueError("capture appearance race unresolved")

    def integer(primary: str, fallback: str | None = None, default: int = 0) -> int:
        value = start.get(primary)
        if (
            (isinstance(value, bool) or not isinstance(value, int))
            and fallback is not None
        ):
            value = start.get(fallback)
        return (
            int(value)
            if isinstance(value, int) and not isinstance(value, bool)
            else default
        )

    return {
        "id": ship_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "hull_id": hull_id,
        "shield": integer("shield", default=100),
        "damage": integer("damage"),
        "crew": integer("crew", default=1),
        "physical_beam_count": integer("beamcount", "beam_count"),
        "physical_launcher_count": integer("launchercount", "launcher_count"),
        "physical_bay_count": integer("baycount", "bay_count"),
        "beam_count": integer("beamcount", "beam_count"),
        "launcher_count": integer("launchercount", "launcher_count"),
        "bay_count": integer("baycount", "bay_count"),
        "torpedoes": integer("torpedos", "torpedoes"),
        "fighters": integer("fighters"),
        "federation_crew_bonus": race_id == 1,
        "lizard_crew_bonus": race_id == 2,
    }


def _production_capture_projection(
    *,
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    previous_opponent: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(previous_opponent, Mapping):
        return {"resolved": None, "reason": "captor_ship_appearance_missing"}
    terminal = previous.get("terminal")
    current_start = current.get("start")
    if not isinstance(terminal, Mapping) or not isinstance(current_start, Mapping):
        return {"resolved": None, "reason": "terminal_or_current_start_missing"}

    ship_id = int(previous["ship_id"])
    captor_owner_id = previous_opponent.get("owner_id")
    captor_race_id = previous_opponent.get("race_id")
    if (
        isinstance(captor_owner_id, bool)
        or not isinstance(captor_owner_id, int)
        or captor_owner_id <= 0
        or isinstance(captor_race_id, bool)
        or not isinstance(captor_race_id, int)
        or captor_race_id <= 0
    ):
        return {"resolved": None, "reason": "captor_owner_or_race_unresolved"}

    try:
        mutation = apply_ship_terminal_batch(
            active_ships={ship_id: _active_ship_from_appearance(previous)},
            terminals_by_ship_id={ship_id: terminal},
            capture_transfers_by_ship_id={
                ship_id: ShipCaptureTransfer(
                    new_owner_id=captor_owner_id,
                    new_race_id=captor_race_id,
                    new_federation_crew_bonus=captor_race_id == 1,
                    new_lizard_crew_bonus=captor_race_id == 2,
                )
            },
        )
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "resolved": None,
            "reason": f"production_capture_exception:{type(exc).__name__}:{exc}",
        }

    if mutation.resolved is not True or ship_id not in mutation.active_ships:
        return {
            "resolved": mutation.resolved,
            "reason": "production_capture_mutation_unresolved",
            "unresolved_reasons": list(mutation.unresolved_reasons),
        }

    predicted = mutation.active_ships[ship_id]
    current_owner_id = current.get("owner_id")
    current_race_id = current.get("race_id")
    current_hull_id = current.get("hull_id")

    comparisons = {
        "owner_id": (
            predicted.get("owner_id"),
            current_owner_id,
        ),
        "race_id": (
            predicted.get("race_id"),
            current_race_id,
        ),
        "hull_id": (
            predicted.get("hull_id"),
            current_hull_id,
        ),
        "shield": (
            predicted.get("shield"),
            _int(current_start, "shield"),
        ),
        "damage": (
            predicted.get("damage"),
            _int(current_start, "damage"),
        ),
        "crew": (
            predicted.get("crew"),
            _int(current_start, "crew"),
        ),
        "torpedoes": (
            predicted.get("torpedoes"),
            _int(current_start, "torpedos"),
        ),
        "fighters": (
            predicted.get("fighters"),
            _int(current_start, "fighters"),
        ),
    }
    fields: dict[str, dict[str, Any]] = {}
    for name, (expected, actual) in comparisons.items():
        fields[name] = {
            "predicted": expected,
            "current_start": actual,
            "matches": (
                expected == actual
                if expected is not None and actual is not None
                else None
            ),
        }

    exact_without_damage = all(
        fields[name]["matches"] is True
        for name in (
            "owner_id",
            "race_id",
            "hull_id",
            "shield",
            "crew",
            "torpedoes",
            "fighters",
        )
    )
    all_exact = exact_without_damage and fields["damage"]["matches"] is True
    return {
        "resolved": True,
        "captured_ship_ids": list(mutation.captured_ship_ids),
        "fields": fields,
        "exact_without_damage": exact_without_damage,
        "all_exact": all_exact,
    }


def _capture_transition(
    *,
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    previous_opponent: Mapping[str, Any] | None,
    current_opponent: Mapping[str, Any] | None,
    current_opponent_is_planet: bool = False,
) -> dict[str, Any]:
    terminal = previous.get("terminal")
    current_start = current.get("start")
    if not isinstance(terminal, Mapping) or not isinstance(current_start, Mapping):
        return {"status": "unresolved", "reason": "terminal_or_start_missing"}
    if terminal.get("captured") is not True:
        return {"status": "not_capture"}

    previous_race = previous.get("race_id")
    previous_owner = previous.get("owner_id")
    current_race = current.get("race_id")
    current_owner = current.get("owner_id")
    captor_race = (
        previous_opponent.get("race_id")
        if isinstance(previous_opponent, Mapping)
        else None
    )
    captor_owner = (
        previous_opponent.get("owner_id")
        if isinstance(previous_opponent, Mapping)
        else None
    )
    previous_opponent_id = (
        int(previous_opponent["ship_id"])
        if isinstance(previous_opponent, Mapping)
        else None
    )
    current_opponent_id = (
        int(current_opponent["ship_id"])
        if isinstance(current_opponent, Mapping)
        else None
    )

    carry: dict[str, Any] = {}
    comparable = 0
    exact_fields = 0
    for terminal_key, start_key in CARRY_FIELDS:
        expected = _int(terminal, terminal_key)
        actual = _int(current_start, start_key)
        matches = (
            expected == actual
            if expected is not None and actual is not None
            else None
        )
        if matches is not None:
            comparable += 1
            if matches:
                exact_fields += 1
        carry[terminal_key] = {
            "terminal": expected,
            "current_start": actual,
            "matches": matches,
        }

    shield = _shield_projection(
        terminal=terminal,
        current_start=current_start,
        previous_race_id=(
            int(previous_race)
            if isinstance(previous_race, int) and not isinstance(previous_race, bool)
            else None
        ),
    )
    production = _production_capture_projection(
        previous=previous,
        current=current,
        previous_opponent=previous_opponent,
    )

    return {
        "status": "capture_continuation",
        "game_id": int(previous["game_id"]),
        "turn": int(previous["turn"]),
        "ship_id": int(previous["ship_id"]),
        "from_vcr_id": int(previous["vcr_id"]),
        "to_vcr_id": int(current["vcr_id"]),
        "position": previous.get("position"),
        "hull_id_before": previous.get("hull_id"),
        "hull_id_after": current.get("hull_id"),
        "hull_preserved": previous.get("hull_id") == current.get("hull_id"),
        "owner_id_before": previous_owner,
        "captor_owner_id": captor_owner,
        "owner_id_after": current_owner,
        "owner_changes_to_captor": (
            current_owner == captor_owner
            if current_owner is not None and captor_owner is not None
            else None
        ),
        "race_id_before": previous_race,
        "captor_ship_id": previous_opponent_id,
        "captor_race_id": captor_race,
        "race_id_after": current_race,
        "race_changes_to_captor": (
            current_race == captor_race
            if current_race is not None and captor_race is not None
            else None
        ),
        "race_changed": (
            current_race != previous_race
            if current_race is not None and previous_race is not None
            else None
        ),
        "current_opponent_ship_id": current_opponent_id,
        "current_opponent_race_id": (
            current_opponent.get("race_id")
            if isinstance(current_opponent, Mapping)
            else None
        ),
        "current_opponent_is_planet": current_opponent_is_planet,
        "next_opponent_is_captor": (
            current_opponent_id == previous_opponent_id
            if current_opponent_id is not None and previous_opponent_id is not None
            else None
        ),
        "current_side": current.get("side"),
        "terminal_destroyed": terminal.get("destroyed"),
        "terminal_captured": terminal.get("captured"),
        "carry": carry,
        "carry_comparable_fields": comparable,
        "carry_exact_fields": exact_fields,
        "carry_all_exact": comparable > 0 and exact_fields == comparable,
        "shield": shield,
        "production": production,
    }


def _collect_appearances(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
    appearances: list[dict[str, Any]] = []
    original_appearance = chain_module._appearance

    def wrapped_appearance(*wrapped_args: Any, **wrapped_kwargs: Any):
        result = original_appearance(*wrapped_args, **wrapped_kwargs)
        if (
            isinstance(result, dict)
            and result.get("game_id") in selected_ids
        ):
            appearances.append(result)
        return result

    ordinary_archives: list[str] = []
    for path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            game_id = int(path.stem.split("-")[-1])
        except ValueError:
            continue
        if game_id in selected_ids:
            ordinary_archives.append(str(path))

    chain_module._appearance = wrapped_appearance
    try:
        report = chain_module.run(
            argparse.Namespace(
                archive=ordinary_archives,
                archive_dir=args.archive_dir,
                detail_limit=args.example_limit,
                sample_limit=min(args.example_limit, 20),
            )
        )
    finally:
        chain_module._appearance = original_appearance

    return appearances, report.get("summary", {})


def run(args: argparse.Namespace) -> dict[str, Any]:
    feature_scope = load_feature_scope(
        args.feature_index,
        profile=args.scope_profile,
    )
    appearances, chain_summary = _collect_appearances(args)

    by_vcr: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    by_ship_turn: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in appearances:
        by_vcr[
            (int(row["game_id"]), int(row["turn"]), int(row["vcr_id"]))
        ].append(row)
        by_ship_turn[
            (int(row["game_id"]), int(row["turn"]), int(row["ship_id"]))
        ].append(row)

    counts: Counter[str] = Counter()
    shield_models: Counter[str] = Counter()
    carry_field_counts: dict[str, Counter[str]] = {
        key: Counter() for key, _ in CARRY_FIELDS
    }
    production_field_counts: dict[str, Counter[str]] = {
        key: Counter()
        for key in (
            "owner_id",
            "race_id",
            "hull_id",
            "shield",
            "damage",
            "crew",
            "torpedoes",
            "fighters",
        )
    }
    examples: list[dict[str, Any]] = []
    damage_residuals: set[tuple[int, int, int, int, int, int, int]] = set()

    for chain in by_ship_turn.values():
        chain.sort(key=lambda item: int(item["vcr_id"]))
        for previous, current in zip(chain, chain[1:]):
            if not _same_location(previous, current):
                continue
            terminal = previous.get("terminal")
            if not isinstance(terminal, Mapping) or terminal.get("captured") is not True:
                continue

            counts["capture_reappearance_transitions"] += 1
            previous_opponent = _other_appearance(by_vcr, previous)
            current_opponent = _other_appearance(by_vcr, current)
            current_opponent_is_planet = _other_is_planet(by_vcr, current)
            row = _capture_transition(
                previous=previous,
                current=current,
                previous_opponent=previous_opponent,
                current_opponent=current_opponent,
                current_opponent_is_planet=current_opponent_is_planet,
            )
            if row.get("status") != "capture_continuation":
                counts["capture_transition_unresolved"] += 1
                if len(examples) < args.example_limit:
                    examples.append(row)
                continue

            if row.get("hull_preserved") is True:
                counts["hull_preserved"] += 1
            else:
                counts["hull_changed_or_unknown"] += 1

            owner_to_captor = row.get("owner_changes_to_captor")
            if owner_to_captor is True:
                counts["owner_changes_to_captor_exact"] += 1
            elif owner_to_captor is False:
                counts["owner_changes_to_captor_mismatch"] += 1
            else:
                counts["owner_changes_to_captor_unknown"] += 1

            race_to_captor = row.get("race_changes_to_captor")
            if race_to_captor is True:
                counts["race_changes_to_captor_exact"] += 1
            elif race_to_captor is False:
                counts["race_changes_to_captor_mismatch"] += 1
            else:
                counts["race_changes_to_captor_unknown"] += 1

            if row.get("race_changed") is True:
                counts["race_changed"] += 1
            elif row.get("race_changed") is False:
                counts["race_unchanged"] += 1
            else:
                counts["race_change_unknown"] += 1

            if current_opponent_is_planet:
                counts["next_opponent_planet"] += 1
            elif row.get("next_opponent_is_captor") is True:
                counts["next_opponent_captor"] += 1
            elif row.get("next_opponent_is_captor") is False:
                counts["next_opponent_third_ship"] += 1
            else:
                counts["next_opponent_unknown"] += 1

            side = row.get("current_side")
            if side in {"left", "right"}:
                counts[f"post_capture_side:{side}"] += 1

            if row.get("carry_all_exact") is True:
                counts["raw_terminal_carry_all_exact"] += 1
            else:
                counts["raw_terminal_carry_not_all_exact"] += 1

            carry = row.get("carry")
            if isinstance(carry, Mapping):
                for field, detail in carry.items():
                    if field not in carry_field_counts or not isinstance(detail, Mapping):
                        continue
                    matches = detail.get("matches")
                    carry_field_counts[field][
                        "exact" if matches is True else (
                            "mismatch" if matches is False else "unknown"
                        )
                    ] += 1

            shield = row.get("shield")
            if isinstance(shield, Mapping):
                shield_models[str(shield.get("model", "unknown"))] += 1

            production = row.get("production")
            if not isinstance(production, Mapping) or production.get("resolved") is not True:
                counts["production_capture_unresolved"] += 1
            else:
                if production.get("exact_without_damage") is True:
                    counts["production_capture_exact_without_damage"] += 1
                else:
                    counts["production_capture_mismatch_without_damage"] += 1
                if production.get("all_exact") is True:
                    counts["production_capture_all_exact"] += 1
                else:
                    counts["production_capture_not_all_exact"] += 1
                fields = production.get("fields")
                if isinstance(fields, Mapping):
                    damage_detail = fields.get("damage")
                    if (
                        isinstance(damage_detail, Mapping)
                        and damage_detail.get("matches") is False
                        and isinstance(damage_detail.get("predicted"), int)
                        and not isinstance(damage_detail.get("predicted"), bool)
                        and isinstance(damage_detail.get("current_start"), int)
                        and not isinstance(damage_detail.get("current_start"), bool)
                    ):
                        damage_residuals.add(
                            (
                                int(row["game_id"]),
                                int(row["turn"]),
                                int(row["ship_id"]),
                                int(row["from_vcr_id"]),
                                int(row["to_vcr_id"]),
                                int(damage_detail["predicted"]),
                                int(damage_detail["current_start"]),
                            )
                        )
                    for field, detail in fields.items():
                        if (
                            field not in production_field_counts
                            or not isinstance(detail, Mapping)
                        ):
                            continue
                        matches = detail.get("matches")
                        production_field_counts[field][
                            "exact" if matches is True else (
                                "mismatch" if matches is False else "unknown"
                            )
                        ] += 1

            if len(examples) < args.example_limit:
                examples.append(row)

    population = int(counts["capture_reappearance_transitions"])
    acceptance = {
        "capture_reappearance_population_present": population > 0,
        "no_capture_transition_adapter_errors": int(
            counts["capture_transition_unresolved"]
        ) == 0,
        "hull_preserved": int(counts["hull_preserved"]) == population,
        "owner_changes_to_captor": (
            int(counts["owner_changes_to_captor_exact"]) == population
            and int(counts["owner_changes_to_captor_mismatch"]) == 0
            and int(counts["owner_changes_to_captor_unknown"]) == 0
        ),
        "race_changes_to_captor": (
            int(counts["race_changes_to_captor_exact"]) == population
            and int(counts["race_changes_to_captor_mismatch"]) == 0
            and int(counts["race_changes_to_captor_unknown"]) == 0
        ),
        "production_capture_state_exact_excluding_damage": (
            int(counts["production_capture_exact_without_damage"]) == population
            and int(counts["production_capture_mismatch_without_damage"]) == 0
            and int(counts["production_capture_unresolved"]) == 0
        ),
        "no_new_damage_replay_residuals": (
            damage_residuals <= KNOWN_DAMAGE_REPLAY_RESIDUALS
            and int(production_field_counts["damage"]["unknown"]) == 0
        ),
    }
    acceptance["capture_transition_gate_passed"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "feature_scope": feature_scope.to_dict(),
            "counts": dict(sorted(counts.items())),
            "raw_terminal_carry_fields": {
                key: dict(sorted(value.items()))
                for key, value in carry_field_counts.items()
            },
            "shield_models": dict(sorted(shield_models.items())),
            "damage_replay_residuals": [list(row) for row in sorted(damage_residuals)],
            "known_damage_replay_residuals": [
                list(row) for row in sorted(KNOWN_DAMAGE_REPLAY_RESIDUALS)
            ],
            "production_fields": {
                key: dict(sorted(value.items()))
                for key, value in production_field_counts.items()
            },
            "chain_audit_summary": chain_summary,
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "Capture-continuation differential over deterministic Classic replay "
            "and the next factual same-turn same-location VCR of the same ship id. "
            "The population is selected through shared FeatureScope. Explicit captor owner/race attribution comes "
            "from the opposing factual VCR side of the capture engagement; no "
            "post-Host T state is used. Production capture mutation applies the "
            "terminal vector, pre-capture Federation end-of-battle shield recovery, "
            "documented 10-person prize crew, explicit owner/race transfer and "
            "new-owner combat bonus flags before preparing the next engagement. "
            "A single damage-only residual is tolerated as an upstream replay "
            "residual only if every ownership/race/hull/shield/crew/ammunition "
            "field remains exact. Post-capture mission, PE, diplomacy and full "
            "next-pair ordering are still separate."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit same-turn same-location captured-ship continuation into a "
            "later factual VCR."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument(
        "--feature-index",
        type=Path,
        default=DEFAULT_FEATURE_INDEX_PATH,
    )
    parser.add_argument(
        "--scope-profile",
        default="combat-planar-no-horwasp",
    )
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT CAPTURE CONTINUATION AUDIT =====")
    print("summary:", report["summary"])
    if report["examples"]:
        print()
        print("EXAMPLES:")
        for row in report["examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: bounded production capture-state gate; post-capture order/"
        "diplomacy remains separate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
