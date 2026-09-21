from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.feature_index import (
    load_feature_rows,
    profile_selection_summary,
)


CHAIN_TOOL = Path(__file__).with_name("combat_ship_chain_audit.py")
spec = importlib.util.spec_from_file_location("combat_ship_chain_audit", CHAIN_TOOL)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {CHAIN_TOOL}")
chain_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain_audit)

DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_FEATURE_INDEX = Path("validation/corpus/compiled/v1/metadata/game_features.parquet")
DEFAULT_SCOPE_PROFILE = "combat-planar-no-horwasp"
CARRY_FIELDS = ("damage", "crew", "torpedoes", "fighters")


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _counter(values: Counter[Any]) -> dict[str, int]:
    return {
        str(key): count
        for key, count in sorted(values.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _battle_shape(vcr: Mapping[str, Any]) -> str:
    left = vcr.get("left")
    right = vcr.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return "unknown"
    left_hull = chain_audit._int(left, "hullid")
    right_hull = chain_audit._int(right, "hullid")
    if left_hull is None or right_hull is None:
        return "unknown"
    left_planet = left_hull <= 0
    right_planet = right_hull <= 0
    if left_planet and right_planet:
        return "planet_vs_planet"
    if left_planet or right_planet:
        return "ship_vs_planet"
    return "ship_vs_ship"


def _side_owner(vcr: Mapping[str, Any], side: str) -> int | None:
    key = "leftownerid" if side == "left" else "rightownerid"
    return chain_audit._int(vcr, key)


def _archive_paths(args: argparse.Namespace) -> list[Path]:
    if args.archive:
        return [Path(value) for value in args.archive]
    return sorted(args.archive_dir.glob("game-*.zip"))


def _scope_selection(args: argparse.Namespace) -> dict[str, Any] | None:
    feature_index = getattr(args, "feature_index", None)
    if feature_index is None:
        return None
    rows = load_feature_rows(Path(feature_index))
    return profile_selection_summary(
        rows,
        profile=getattr(args, "scope_profile", DEFAULT_SCOPE_PROFILE),
    )


def _vcr_metadata(args: argparse.Namespace) -> tuple[dict[tuple[int, int, int], dict[str, Any]], int]:
    metadata: dict[tuple[int, int, int], dict[str, Any]] = {}
    conflicts = 0
    for archive_path in _archive_paths(args):
        data = archive_path.read_bytes()
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        for member in members:
            try:
                rst = chain_audit._decode_turn(raw_members[member.name], member.name)
            except ValueError:
                continue
            game = rst.get("game")
            if not isinstance(game, Mapping):
                continue
            game_id = chain_audit._int(game, "id")
            game_turn = chain_audit._int(game, "turn")
            if game_id is None or game_turn is None:
                continue
            for vcr in chain_audit._objects(rst, "vcrs"):
                vcr_id = chain_audit._int(vcr, "id")
                battle_turn = chain_audit._int(vcr, "turn") or game_turn
                if vcr_id is None:
                    continue
                key = (game_id, battle_turn, vcr_id)
                item = {
                    "shape": _battle_shape(vcr),
                    "left_owner": _side_owner(vcr, "left"),
                    "right_owner": _side_owner(vcr, "right"),
                }
                previous = metadata.get(key)
                if previous is None:
                    metadata[key] = item
                elif previous != item:
                    conflicts += 1
    return metadata, conflicts


def _capture_all_transitions(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    captured: list[dict[str, Any]] = []
    original = chain_audit._transition_comparison

    def wrapped(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
        comparison = original(previous, current)
        captured.append(
            {
                "previous": dict(previous),
                "current": dict(current),
                "comparison": comparison,
            }
        )
        return comparison

    chain_audit._transition_comparison = wrapped
    try:
        base_args = argparse.Namespace(
            archive_dir=args.archive_dir,
            archive=list(args.archive),
            output=None,
            detail_limit=1_000_000,
            sample_limit=1_000_000,
            feature_index=None,
            feature_profile="all-indexed",
        )
        base = chain_audit.run(base_args)
    finally:
        chain_audit._transition_comparison = original
    return base, captured


def _terminal_kind(previous: Mapping[str, Any]) -> str:
    terminal = previous.get("terminal")
    if not isinstance(terminal, Mapping):
        return "unknown"
    if bool(terminal.get("captured")):
        return "captured"
    if bool(terminal.get("destroyed")):
        return "destroyed"
    return "survived"


def _problem_signature(comparison: Mapping[str, Any], terminal_kind: str) -> str:
    if terminal_kind == "captured":
        return "reappearance_after_capture"
    if terminal_kind == "destroyed":
        return "reappearance_after_destroyed"
    fields = comparison.get("carry_mismatches")
    parts = [str(item) for item in fields] if isinstance(fields, list) else []
    shield = comparison.get("shield")
    if isinstance(shield, Mapping) and shield.get("model") == "mismatch":
        parts.append("shield")
    return "+".join(parts) if parts else str(comparison.get("status", "unknown"))


def _carry_delta(comparison: Mapping[str, Any], field: str) -> int | None:
    carry = comparison.get("carry")
    if not isinstance(carry, Mapping):
        return None
    row = carry.get(field)
    if not isinstance(row, Mapping):
        return None
    terminal = _int(row.get("terminal"))
    next_start = _int(row.get("next_start"))
    if terminal is None or next_start is None:
        return None
    return next_start - terminal


def _scope_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status: Counter[str] = Counter()
    signatures: Counter[str] = Counter()
    races: Counter[int] = Counter()
    hulls: Counter[int] = Counter()
    gaps: Counter[int] = Counter()
    side_transitions: Counter[str] = Counter()
    shield_models: Counter[str] = Counter()
    field_deltas: dict[str, Counter[int]] = {field: Counter() for field in CARRY_FIELDS}

    for row in rows:
        comparison = row["comparison"]
        terminal_kind = row["terminal_kind"]
        raw_status = str(comparison.get("status", "unknown"))
        if terminal_kind == "captured":
            row_status = "reappearance_after_capture"
        elif terminal_kind == "destroyed":
            row_status = "reappearance_after_destroyed"
        else:
            row_status = raw_status
        status[row_status] += 1
        if row_status != "match":
            signatures[_problem_signature(comparison, terminal_kind)] += 1
        race_id = _int(row.get("race_id"))
        hull_id = _int(row.get("hull_id"))
        if race_id is not None:
            races[race_id] += 1
        if hull_id is not None:
            hulls[hull_id] += 1
        gaps[int(row["gap"])] += 1
        side_transitions[f"{row['from_side']}->{row['to_side']}"] += 1
        shield = comparison.get("shield")
        if isinstance(shield, Mapping):
            shield_models[str(shield.get("model", "unknown"))] += 1
        for field in CARRY_FIELDS:
            delta = _carry_delta(comparison, field)
            if delta is not None:
                field_deltas[field][delta] += 1

    return {
        "transitions": len(rows),
        "status": _counter(status),
        "problem_signatures": _counter(signatures),
        "races": _counter(races),
        "hulls": _counter(hulls),
        "vcr_gaps": _counter(gaps),
        "side_transitions": _counter(side_transitions),
        "shield_models": _counter(shield_models),
        "field_deltas_next_minus_terminal": {
            field: _counter(counter) for field, counter in field_deltas.items()
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    base, captured = _capture_all_transitions(args)
    metadata, metadata_conflicts = _vcr_metadata(args)

    rows: list[dict[str, Any]] = []
    phase_counts: Counter[str] = Counter()
    terminal_kinds: Counter[str] = Counter()
    capture_owner_changes: Counter[str] = Counter()

    for item in captured:
        previous = item["previous"]
        current = item["current"]
        comparison = item["comparison"]
        game_id = int(previous["game_id"])
        turn = int(previous["turn"])
        from_vcr = int(previous["vcr_id"])
        to_vcr = int(current["vcr_id"])
        from_side = str(previous["side"])
        to_side = str(current["side"])
        from_meta = metadata.get((game_id, turn, from_vcr), {})
        to_meta = metadata.get((game_id, turn, to_vcr), {})
        from_shape = str(from_meta.get("shape", "unknown"))
        to_shape = str(to_meta.get("shape", "unknown"))
        phase = f"{from_shape}->{to_shape}"
        terminal_kind = _terminal_kind(previous)
        from_owner = from_meta.get(f"{from_side}_owner")
        to_owner = to_meta.get(f"{to_side}_owner")
        if terminal_kind == "captured":
            if isinstance(from_owner, int) and isinstance(to_owner, int):
                capture_owner_changes["changed" if from_owner != to_owner else "same"] += 1
            else:
                capture_owner_changes["unknown"] += 1
        phase_counts[phase] += 1
        terminal_kinds[terminal_kind] += 1
        rows.append(
            {
                "game_id": game_id,
                "turn": turn,
                "ship_id": previous.get("ship_id"),
                "race_id": previous.get("race_id"),
                "hull_id": previous.get("hull_id"),
                "from_vcr": from_vcr,
                "to_vcr": to_vcr,
                "gap": to_vcr - from_vcr,
                "from_side": from_side,
                "to_side": to_side,
                "from_shape": from_shape,
                "to_shape": to_shape,
                "terminal_kind": terminal_kind,
                "from_owner": from_owner,
                "to_owner": to_owner,
                "comparison": comparison,
            }
        )

    selection = _scope_selection(args)
    if selection is None:
        selected_ids = {int(row["game_id"]) for row in rows}
        excluded_ids: set[int] = set()
        unknown_ids: set[int] = set()
    else:
        selected_ids = set(selection["included_game_ids"])
        excluded_ids = set(selection["excluded_game_ids"])
        unknown_ids = set(selection["unknown_game_ids"])

    selected = [row for row in rows if int(row["game_id"]) in selected_ids]
    excluded = [row for row in rows if int(row["game_id"]) in excluded_ids]
    unknown_scope = [row for row in rows if int(row["game_id"]) in unknown_ids]

    ordinary_ship_ship_survivors = [
        row
        for row in selected
        if row["from_shape"] == "ship_vs_ship"
        and row["to_shape"] == "ship_vs_ship"
        and row["terminal_kind"] == "survived"
    ]
    ordinary_ship_ship_gap1 = [
        row for row in ordinary_ship_ship_survivors if row["gap"] == 1
    ]
    ordinary_phase_boundary = [
        row
        for row in selected
        if row["from_shape"] == "ship_vs_ship"
        and row["to_shape"] == "ship_vs_planet"
    ]
    captured_reappearances = [row for row in rows if row["terminal_kind"] == "captured"]
    destroyed_reappearances = [row for row in rows if row["terminal_kind"] == "destroyed"]

    return {
        "schema": "planets-lab.combat-ship-chain-phase-audit.v2",
        "read_only": True,
        "source_summary": base.get("summary"),
        "metadata_conflicts": metadata_conflicts,
        "all_phase_transitions": _counter(phase_counts),
        "terminal_kinds": _counter(terminal_kinds),
        "capture_owner_changes": _counter(capture_owner_changes),
        "scope_selection": selection,
        "scopes": {
            "profile_selected_all": _scope_summary(selected),
            "profile_selected_ship_vs_ship_survivors": _scope_summary(ordinary_ship_ship_survivors),
            "profile_selected_ship_vs_ship_survivors_gap1": _scope_summary(ordinary_ship_ship_gap1),
            "profile_selected_ship_to_planet_boundary": _scope_summary(ordinary_phase_boundary),
            "profile_excluded_all": _scope_summary(excluded),
            "profile_unknown_all": _scope_summary(unknown_scope),
            "captured_reappearances_all_games": _scope_summary(captured_reappearances),
            "destroyed_reappearances_all_games": _scope_summary(destroyed_reappearances),
        },
        "notes": [
            "The strongest C3 exact-carry oracle is an ordinary-game surviving ship moving from ship-vs-ship combat to another ship-vs-ship combat.",
            "The gap=1 subset is reported separately as the strongest globally-adjacent VCR subset.",
            "Ship-vs-ship to ship-vs-planet is a Host phase boundary where between-phase repair may intervene and is not treated as a strict exact-carry oracle.",
            "Captured and destroyed terminals are reported separately; a captured ship can legitimately reappear under a new owner.",
            "Clean strict scopes are selected by the feature-index profile; no game id is special-cased in this diagnostic.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase-aware C3 differential audit over factual loadall VCR chains."
    )
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--archive", action="append", default=[])
    parser.add_argument(
        "--feature-index",
        type=Path,
        default=DEFAULT_FEATURE_INDEX,
        help="Compiled game feature index used only to classify report scopes.",
    )
    parser.add_argument(
        "--scope-profile",
        default=DEFAULT_SCOPE_PROFILE,
        help="Feature-index profile defining the clean combat scope.",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")

    print("===== C3 PHASE-AWARE SHIP CHAIN AUDIT =====")
    print(f"source_summary: {report['source_summary']}")
    print(f"metadata_conflicts: {report['metadata_conflicts']}")
    print(f"all_phase_transitions: {report['all_phase_transitions']}")
    print(f"terminal_kinds: {report['terminal_kinds']}")
    print(f"capture_owner_changes: {report['capture_owner_changes']}")
    for name, scope in report["scopes"].items():
        print(f"\n===== {name} =====")
        for key in (
            "transitions",
            "status",
            "problem_signatures",
            "vcr_gaps",
            "shield_models",
            "field_deltas_next_minus_terminal",
        ):
            print(f"{key}: {scope[key]}")
    if args.output is not None:
        print(f"output: {args.output}")
    print("NOTE: phase classification only; no additional combat mechanic is changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
