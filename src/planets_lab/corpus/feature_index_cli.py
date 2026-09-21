from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .feature_index import (
    FEATURE_INDEX_BUILD_SCHEMA,
    FEATURE_INDEX_SCHEMA,
    FeaturePredicate,
    build_feature_rows,
    load_feature_rows,
    profile_predicates,
    select_games,
    write_feature_index,
)
from .indexer import CorpusIndexError, load_manifest_jsonl


DEFAULT_MANIFEST = Path("validation/corpus/manifests/accounts-recent-finished.jsonl")
DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_COMPILED_DIR = Path("validation/corpus/compiled/v1")
DEFAULT_PARQUET = DEFAULT_COMPILED_DIR / "metadata" / "game_features.parquet"
DEFAULT_DATABASE = DEFAULT_COMPILED_DIR / "corpus.duckdb"
DEFAULT_BUILD_META = DEFAULT_COMPILED_DIR / "metadata" / "game_feature_build.json"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_manifests(path: Path) -> tuple[dict[str, Any], ...]:
    return load_manifest_jsonl(path.read_text(encoding="utf-8"))


def _typed_cli_value(raw: str) -> Any:
    value = raw.strip()
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _parse_feature_value(raw: str, *, op: str) -> FeaturePredicate:
    if "=" not in raw:
        raise ValueError(f"{op} requires FEATURE=VALUE")
    feature, value = raw.split("=", 1)
    feature = feature.strip()
    if not feature:
        raise ValueError(f"{op} requires a non-empty feature name")
    return FeaturePredicate(feature, op, _typed_cli_value(value))


def _extra_predicates(args: argparse.Namespace) -> tuple[FeaturePredicate, ...]:
    predicates: list[FeaturePredicate] = []
    for flag, op in (
        ("eq", "eq"),
        ("ne", "ne"),
        ("gt", "gt"),
        ("ge", "ge"),
        ("lt", "lt"),
        ("le", "le"),
    ):
        for raw in getattr(args, flag):
            predicates.append(_parse_feature_value(raw, op=op))
    for feature in args.known:
        predicates.append(FeaturePredicate(feature.strip(), "known"))
    return tuple(predicates)


def _decision_json(decision: Any) -> dict[str, Any]:
    unknown = [
        predicate
        for predicate in decision.predicates
        if predicate["status"] == "unknown"
    ]
    mismatches = [
        predicate
        for predicate in decision.predicates
        if predicate["status"] == "mismatch"
    ]
    return {
        "game_id": decision.game_id,
        "included": decision.included,
        "predicates": list(decision.predicates),
        "unknown_predicates": unknown,
        "exclusion_reasons": [
            {
                "feature": item["feature"],
                "status": item["status"],
                "actual": item["actual"],
                "expected": item["expected"],
            }
            for item in (*mismatches, *unknown)
        ],
    }


def build_command(args: argparse.Namespace) -> int:
    manifests = _read_manifests(args.manifest)
    rows = build_feature_rows(
        manifests,
        archive_dir=args.archive_dir,
        compiled_dir=args.compiled_dir,
        manifest_location=str(args.manifest),
    )
    summary = write_feature_index(
        rows=rows,
        parquet_path=args.output,
        database_path=args.database,
    )
    missing_archives = sorted(
        int(row["game_id"])
        for row in rows
        if row["feature"] == "coverage.archive_present"
        and row["known"] is True
        and row["bool_value"] is False
    )
    summary.update(
        {
            "manifest": str(args.manifest),
            "archive_dir": str(args.archive_dir),
            "compiled_dir": str(args.compiled_dir),
            "parquet": str(args.output),
            "database": str(args.database),
            "missing_archives": missing_archives,
            "manifest_sha256": hashlib.sha256(
                args.manifest.read_bytes()
            ).hexdigest(),
        }
    )
    _write_json(args.build_meta, summary)

    print("===== GAME FEATURE INDEX BUILD =====")
    print(f"feature_index_schema: {FEATURE_INDEX_SCHEMA}")
    print(f"build_schema:         {FEATURE_INDEX_BUILD_SCHEMA}")
    print(f"games:                {summary['games']}")
    print(f"rows:                 {summary['rows']}")
    print(f"known_rows:           {summary['known_rows']}")
    print(f"unknown_rows:         {summary['unknown_rows']}")
    print(f"missing_archives:     {missing_archives}")
    print(f"parquet_sha256:       {summary['parquet_sha256']}")
    print(f"parquet:              {args.output}")
    print(f"database:             {args.database}")
    print(f"build_meta:           {args.build_meta}")

    if args.require_archives and missing_archives:
        print(
            "ERROR: required immutable loadall archives are missing: "
            + ", ".join(str(game_id) for game_id in missing_archives),
            file=sys.stderr,
        )
        return 1
    return 0


def select_command(args: argparse.Namespace) -> int:
    rows = load_feature_rows(args.index)
    predicates = (*profile_predicates(args.profile), *_extra_predicates(args))
    decisions = select_games(rows, predicates)
    payload = {
        "schema": "planets-lab.game-feature-selection.v1",
        "feature_index_schema": FEATURE_INDEX_SCHEMA,
        "index": str(args.index),
        "profile": args.profile,
        "predicate_count": len(predicates),
        "included_game_ids": [
            decision.game_id for decision in decisions if decision.included
        ],
        "excluded_game_ids": [
            decision.game_id for decision in decisions if not decision.included
        ],
        "games": [_decision_json(decision) for decision in decisions],
    }

    if args.output is not None:
        _write_json(args.output, payload)

    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build and query the deterministic Planets.nu historical game / Host "
            "feature index."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build",
        help="Compile manifests, immutable loadall archives and compiled counters.",
    )
    build.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    build.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    build.add_argument("--compiled-dir", type=Path, default=DEFAULT_COMPILED_DIR)
    build.add_argument("--output", type=Path, default=DEFAULT_PARQUET)
    build.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    build.add_argument("--build-meta", type=Path, default=DEFAULT_BUILD_META)
    build.add_argument(
        "--require-archives",
        action="store_true",
        help="Fail after build when any manifest game lacks its immutable loadall ZIP.",
    )
    build.set_defaults(handler=build_command)

    select = subparsers.add_parser(
        "select",
        help="Evaluate a named corpus profile plus optional explicit predicates.",
    )
    select.add_argument("--index", type=Path, default=DEFAULT_PARQUET)
    select.add_argument(
        "--profile",
        default="all-indexed",
        choices=("all-indexed", "ordinary-classic"),
    )
    for flag in ("eq", "ne", "gt", "ge", "lt", "le"):
        select.add_argument(
            f"--{flag}",
            action="append",
            default=[],
            metavar="FEATURE=VALUE",
        )
    select.add_argument(
        "--known",
        action="append",
        default=[],
        metavar="FEATURE",
        help="Require the feature to be known, regardless of value.",
    )
    select.add_argument("--output", type=Path, default=None)
    select.set_defaults(handler=select_command)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return int(args.handler(args))
    except (OSError, ValueError, CorpusIndexError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
