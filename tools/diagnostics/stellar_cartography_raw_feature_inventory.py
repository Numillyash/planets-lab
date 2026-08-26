from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping, Sequence

import duckdb

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.normalizer import _decode_member_json


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"

FEATURE_TERMS = (
    "blackhole",
    "black_hole",
    "wormhole",
    "nebula",
    "debris",
    "starcluster",
    "star_cluster",
    "stellar",
)

SAFE_SCALAR_KEYS = frozenset(
    {
        "id",
        "type",
        "x",
        "y",
        "radius",
        "size",
        "strength",
        "stability",
        "mass",
        "radiation",
        "radiationlevel",
        "temperature",
        "turn",
        "infoturn",
        "isactive",
        "active",
        "warp",
        "warplimit",
        "maxwarp",
    }
)


def _ratio_bucket(distance: float, nominal: float) -> str:
    """Match the authoritative post-v6 generic clustering bucket semantics."""

    if nominal <= 0:
        return "nominal<=0"
    ratio = distance / nominal
    for label, target in (
        ("~0.5x", 0.5),
        ("~1.0x", 1.0),
        ("~1.5x", 1.5),
        ("~2.0x", 2.0),
        ("~3.0x", 3.0),
    ):
        if abs(ratio - target) <= 0.08:
            return label
    if ratio < 0.5:
        return "<0.5x"
    if ratio < 1.0:
        return "0.5-1.0x"
    if ratio < 1.5:
        return "1.0-1.5x"
    if ratio < 2.0:
        return "1.5-2.0x"
    if ratio < 3.0:
        return "2.0-3.0x"
    return ">3.0x"


def _target_relation(row: Mapping[str, Any]) -> str:
    origin = (int(row["x_before"]), int(row["y_before"]))
    observed = (int(row["x_after"]), int(row["y_after"]))
    target = (int(row["target_x"]), int(row["target_y"]))
    if observed == origin and target == origin:
        return "observed=origin,target=origin"
    if observed == origin:
        return "observed=origin"
    if target == origin:
        return "target=origin"
    if observed == target:
        return "observed=target"
    return "observed=other"


def _direction_bucket(row: Mapping[str, Any]) -> str:
    odx = int(row["x_after"]) - int(row["x_before"])
    ody = int(row["y_after"]) - int(row["y_before"])
    tdx = int(row["target_x"]) - int(row["x_before"])
    tdy = int(row["target_y"]) - int(row["y_before"])
    observed_norm = hypot(odx, ody)
    target_norm = hypot(tdx, tdy)
    if observed_norm <= 1e-9:
        return "observed_stationary"
    if target_norm <= 1e-9:
        return "target_is_origin"
    cosine = (odx * tdx + ody * tdy) / (observed_norm * target_norm)
    if cosine >= 0.98:
        return "same_line_forward"
    if cosine >= 0.75:
        return "mostly_forward"
    if cosine <= -0.98:
        return "same_line_reverse"
    if cosine <= -0.75:
        return "mostly_reverse"
    if -0.25 <= cosine <= 0.25:
        return "roughly_perpendicular"
    return "oblique"


def _is_target_short_forward(row: Mapping[str, Any]) -> bool:
    warp = int(row["warp"])
    return (
        7 <= warp <= 9
        and _ratio_bucket(
            float(row["observed_distance"] or 0.0),
            float(row["nominal_max_distance"] or 0.0),
        )
        == "<0.5x"
        and _target_relation(row) == "observed=other"
        and _direction_bucket(row) == "same_line_forward"
    )


def _load_rows(database: Path) -> list[dict[str, Any]]:
    con = duckdb.connect(str(database), read_only=True)
    try:
        names = [
            "game_id",
            "before_archive_turn",
            "ship_id",
            "hull_id",
            "warp",
            "x_before",
            "y_before",
            "x_after",
            "y_after",
            "target_x",
            "target_y",
            "observed_distance",
            "nominal_max_distance",
        ]
        raw_rows = con.execute(
            f"""
            SELECT {', '.join(names)}
            FROM {RESIDUAL_VIEW}
            WHERE warp BETWEEN 1 AND 9
              AND (hull_id IS NULL OR hull_id NOT BETWEEN 201 AND 213)
            ORDER BY game_id, before_archive_turn, ship_id
            """,
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(names, row)) for row in raw_rows]


def _normalize_key(key: Any) -> str:
    return str(key).strip().lower().replace("-", "_")


def _matches_feature_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    return any(term in normalized for term in FEATURE_TERMS)


def _path(path: Sequence[str]) -> str:
    return ".".join(path)


def _safe_excerpt(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in SAFE_SCALAR_KEYS and isinstance(
                item,
                (int, float, bool, str, type(None)),
            ):
                result[str(key)] = item
        return result
    if isinstance(value, list):
        excerpt: dict[str, Any] = {"list_len": len(value)}
        if value:
            excerpt["safe_items"] = [_safe_excerpt(item) for item in value[:3]]
        return excerpt
    if isinstance(value, (int, float, bool, str, type(None))):
        return value
    return {"type": type(value).__name__}


def _is_active_feature_value(value: Any) -> bool:
    """Distinguish schema presence from a non-empty/non-zero feature instance."""

    if isinstance(value, list):
        return bool(value)
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "none", "null"}
    return value is not None


def _discover(value: Any, *, path: tuple[str, ...] = ()) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_s = str(key)
            child_path = path + (key_s,)
            if _matches_feature_key(key):
                found.append((_path(child_path), item))
            found.extend(_discover(item, path=child_path))
    elif isinstance(value, list):
        for item in value:
            found.extend(_discover(item, path=path + ("[]",)))
    return found


def _turn_from_member_name(name: str) -> int | None:
    marker = "-turn"
    if marker not in name or not name.endswith(".trn"):
        return None
    tail = name.rsplit(marker, 1)[1][:-4]
    try:
        return int(tail)
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory raw Stellar Cartography-related payload paths and distinguish "
            "schema presence from active/non-zero feature instances."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--max-examples-per-path", type=int, default=3)
    args = parser.parse_args()

    if not args.database.is_file():
        raise SystemExit(f"missing compiled corpus database: {args.database}")
    if args.max_examples_per_path < 0:
        raise SystemExit("--max-examples-per-path must be non-negative")

    rows = _load_rows(args.database)
    target_rows = [row for row in rows if _is_target_short_forward(row)]
    print("===== RAW STELLAR-CARTOGRAPHY ACTIVE FEATURE INVENTORY =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("generic_non_horwasp_warp1_9_rows=", len(rows))
    print("target_short_forward_rows=", len(target_rows))
    print("feature_terms=", FEATURE_TERMS)

    target_turns_by_game: dict[int, set[int]] = defaultdict(set)
    target_rows_by_game: Counter[int] = Counter()
    for row in target_rows:
        game_id = int(row["game_id"])
        target_turns_by_game[game_id].add(int(row["before_archive_turn"]))
        target_rows_by_game[game_id] += 1

    global_present_turns: Counter[str] = Counter()
    global_active_turns: Counter[str] = Counter()
    global_active_values: Counter[str] = Counter()
    global_games: dict[str, set[int]] = defaultdict(set)
    global_target_present_turns: Counter[str] = Counter()
    global_target_active_turns: Counter[str] = Counter()
    global_target_active_values: Counter[str] = Counter()
    global_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    game_ids = sorted({int(row["game_id"]) for row in rows})
    for game_id in game_ids:
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.is_file():
            print(f"game={game_id} missing_archive={archive_path}")
            continue
        archive_data = archive_path.read_bytes()
        members = turn_members(archive_data)
        member_by_name = {member.name: member for member in members}

        by_turn: dict[int, list[str]] = defaultdict(list)
        for member in members:
            turn = _turn_from_member_name(member.name)
            if turn is not None:
                by_turn[turn].append(member.name)

        game_present_turns: Counter[str] = Counter()
        game_active_turns: Counter[str] = Counter()
        game_active_values: Counter[str] = Counter()
        game_target_present_turns: Counter[str] = Counter()
        game_target_active_turns: Counter[str] = Counter()
        game_target_active_values: Counter[str] = Counter()

        for turn in sorted(by_turn):
            # One deterministic perspective per turn is sufficient for raw feature/schema
            # inventory. This remains intentionally visibility-incomplete.
            member_name = sorted(by_turn[turn])[0]
            raw = read_archive_members(archive_data, [member_name])[member_name]
            payload, _ = _decode_member_json(raw, member_by_name[member_name])
            discovered = _discover(payload)

            values_by_path: dict[str, list[Any]] = defaultdict(list)
            for path, value in discovered:
                values_by_path[path].append(value)

            for path, values in values_by_path.items():
                active_values = [value for value in values if _is_active_feature_value(value)]
                active = bool(active_values)

                game_present_turns[path] += 1
                global_present_turns[path] += 1
                global_games[path].add(game_id)
                if active:
                    game_active_turns[path] += 1
                    game_active_values[path] += len(active_values)
                    global_active_turns[path] += 1
                    global_active_values[path] += len(active_values)

                if turn in target_turns_by_game.get(game_id, set()):
                    game_target_present_turns[path] += 1
                    global_target_present_turns[path] += 1
                    if active:
                        game_target_active_turns[path] += 1
                        game_target_active_values[path] += len(active_values)
                        global_target_active_turns[path] += 1
                        global_target_active_values[path] += len(active_values)

                if (
                    args.max_examples_per_path > 0
                    and len(global_examples[path]) < args.max_examples_per_path
                ):
                    example_value = active_values[0] if active_values else values[0]
                    global_examples[path].append(
                        {
                            "game": game_id,
                            "turn": turn,
                            "member": member_name,
                            "active": active,
                            "excerpt": _safe_excerpt(example_value),
                        }
                    )

        print(f"\n===== GAME {game_id} =====")
        print("turns_scanned=", len(by_turn))
        print("target_family_rows=", target_rows_by_game.get(game_id, 0))
        print("target_family_turns=", len(target_turns_by_game.get(game_id, set())))
        if not game_present_turns:
            print("matching_paths= 0")
        else:
            print("matching_paths=", len(game_present_turns))
            for path in sorted(game_present_turns):
                print(
                    path,
                    "present_turns=", game_present_turns[path],
                    "active_turns=", game_active_turns.get(path, 0),
                    "active_values=", game_active_values.get(path, 0),
                    "target_present_turns=", game_target_present_turns.get(path, 0),
                    "target_active_turns=", game_target_active_turns.get(path, 0),
                    "target_active_values=", game_target_active_values.get(path, 0),
                )

    print("\n===== GLOBAL FEATURE PATHS =====")
    if not global_present_turns:
        print("matching_paths= 0")
    else:
        for path in sorted(
            global_present_turns,
            key=lambda item: (-global_active_turns.get(item, 0), item),
        ):
            print(
                path,
                "present_turns=", global_present_turns[path],
                "active_turns=", global_active_turns.get(path, 0),
                "active_values=", global_active_values.get(path, 0),
                "games=", len(global_games[path]),
                "target_present_turns=", global_target_present_turns.get(path, 0),
                "target_active_turns=", global_target_active_turns.get(path, 0),
                "target_active_values=", global_target_active_values.get(path, 0),
            )

    print("\n===== SAFE PATH EXAMPLES =====")
    for path in sorted(global_examples):
        print(path)
        for example in global_examples[path]:
            print(example)

    print("\n===== DECISION GUARDRAIL =====")
    print(
        "Schema/path presence is not feature presence. Empty lists and zero/false settings "
        "must have active_turns=0. Only active/non-zero movement-relevant terrain on target "
        "turns can justify a geometry/timing follow-up. The target population must reproduce "
        "the authoritative post-v6 coarse cluster exactly."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
