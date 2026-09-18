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

from planets_lab.rules.combat import federation_recover_shields

import combat_ship_chain_audit as chain_module
from combat_host_priority_intercept_audit import RAW_DIR, SPECIAL_GAME_ID


SCHEMA = "planets-lab.combat-host-capture-continuation-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80
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


def _shield_projection(
    *,
    terminal: Mapping[str, Any],
    current_start: Mapping[str, Any],
    captor_race_id: int | None,
) -> dict[str, Any]:
    terminal_shield = _int(terminal, "shield")
    terminal_damage = _int(terminal, "damage")
    current_shield = _int(current_start, "shield")
    exact = (
        terminal_shield == current_shield
        if terminal_shield is not None and current_shield is not None
        else None
    )

    fed_candidate = None
    fed_exact = None
    if (
        captor_race_id == 1
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
            fed_candidate = value
            fed_exact = (
                value == current_shield if current_shield is not None else None
            )

    if exact is True and fed_exact is True:
        model = "both"
    elif exact is True:
        model = "exact_carry"
    elif fed_exact is True:
        model = "captor_federation_recovery"
    elif exact is False or fed_exact is False:
        model = "mismatch"
    else:
        model = "unknown"

    return {
        "terminal": terminal_shield,
        "current_start": current_shield,
        "exact_carry": exact,
        "captor_federation_candidate": fed_candidate,
        "captor_federation_exact": fed_exact,
        "model": model,
    }


def _capture_transition(
    *,
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    previous_opponent: Mapping[str, Any] | None,
    current_opponent: Mapping[str, Any] | None,
) -> dict[str, Any]:
    terminal = previous.get("terminal")
    current_start = current.get("start")
    if not isinstance(terminal, Mapping) or not isinstance(current_start, Mapping):
        return {"status": "unresolved", "reason": "terminal_or_start_missing"}
    if terminal.get("captured") is not True:
        return {"status": "not_capture"}

    previous_race = previous.get("race_id")
    current_race = current.get("race_id")
    captor_race = (
        previous_opponent.get("race_id")
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
        captor_race_id=(
            int(captor_race)
            if isinstance(captor_race, int) and not isinstance(captor_race, bool)
            else None
        ),
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
            and result.get("game_id") != SPECIAL_GAME_ID
        ):
            appearances.append(result)
        return result

    ordinary_archives: list[str] = []
    for path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            game_id = int(path.stem.split("-")[-1])
        except ValueError:
            continue
        if game_id != SPECIAL_GAME_ID:
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
    examples: list[dict[str, Any]] = []

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
            row = _capture_transition(
                previous=previous,
                current=current,
                previous_opponent=previous_opponent,
                current_opponent=current_opponent,
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

            if row.get("next_opponent_is_captor") is True:
                counts["next_opponent_captor"] += 1
            elif row.get("next_opponent_is_captor") is False:
                counts["next_opponent_third_ship"] += 1
            else:
                counts["next_opponent_unknown"] += 1

            side = row.get("current_side")
            if side in {"left", "right"}:
                counts[f"post_capture_side:{side}"] += 1

            if row.get("carry_all_exact") is True:
                counts["dynamic_carry_all_exact"] += 1
            else:
                counts["dynamic_carry_not_all_exact"] += 1

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

            if len(examples) < args.example_limit:
                examples.append(row)

    population = int(counts["capture_reappearance_transitions"])
    acceptance = {
        "capture_reappearance_population_present": population > 0,
        "no_capture_transition_adapter_errors": int(
            counts["capture_transition_unresolved"]
        ) == 0,
        "hull_preserved": int(counts["hull_preserved"]) == population,
        "race_changes_to_captor": (
            int(counts["race_changes_to_captor_exact"]) == population
            and int(counts["race_changes_to_captor_mismatch"]) == 0
            and int(counts["race_changes_to_captor_unknown"]) == 0
        ),
    }

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "special_game_591478_excluded": True,
            "counts": dict(sorted(counts.items())),
            "carry_fields": {
                key: dict(sorted(value.items()))
                for key, value in carry_field_counts.items()
            },
            "shield_models": dict(sorted(shield_models.items())),
            "chain_audit_summary": chain_summary,
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "Read-only capture-continuation population audit over deterministic "
            "Classic replay and the next factual same-turn same-location VCR of "
            "the same ship id. Game 591478 is excluded. The previous opponent's "
            "factual VCR race id is used only to test whether the captured ship's "
            "next VCR race id changes to the captor race; no post-Host T state is "
            "used. Dynamic terminal-to-next-start fields are descriptive in this "
            "first pass and are not promoted until the runtime distribution is "
            "reviewed. This tool does not yet modify production capture mutation "
            "or infer post-capture mission, PE, diplomacy or target selection."
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
        "NOTE: descriptive capture continuation only; production capture "
        "mutation remains fail-closed until this population is reviewed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
