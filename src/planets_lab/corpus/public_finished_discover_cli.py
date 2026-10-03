from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .api import CorpusApiError, PlanetsNuPublicApi
from .indexer import CorpusIndexError, load_manifest_jsonl
from .manifest import build_game_manifest


DEFAULT_BASELINE = Path("validation/corpus/manifests/accounts-recent-finished.jsonl")
DEFAULT_CANDIDATES = Path(
    "validation/corpus/manifests/public-validation-candidates.jsonl"
)
DEFAULT_SELECTED = Path(
    "validation/corpus/manifests/public-validation-selected.jsonl"
)
DEFAULT_COMBINED = Path(
    "validation/corpus/manifests/public-validation-combined.jsonl"
)
DEFAULT_REPORT = Path("artifacts/public-validation-corpus/selection-report.json")

HIGH_VALUE_SETTINGS = (
    "campaignmode",
    "sphere",
    "chainedintercept",
    "cloakandintercept",
    "racehullsonlycloakandintercept",
    "galacticpower",
    "fascistdoublebeams",
    "racehullsonlyfascistdoublebeams",
    "racehullsonlyhiss",
    "moscowinterceptinterference",
    "sscruiserinterceptinterference",
    "hrossfightertransfer",
    "supertransportfuelmod",
    "quantumtorpedos",
    "quantumtorpedomissrateforgravitonics",
    "scoutsplanetimmunity",
    "starbasefightertransfer",
    "transferoverloadprioritizeammo",
    "torpedoset",
    "directtransfermc",
    "directtransferammo",
    "nowebfriendlycodes",
    "nowebsinotherids",
    "chunnelstabilizationeverywhere",
    "combatrng",
    "unlimitedfuel",
    "nominefields",
    "nowarpwells",
    "maxadvantage",
)


def _int_value(record: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return int(value)


def _metadata_bucket(game: Mapping[str, Any]) -> str:
    short = str(game.get("shortdescription") or "").strip().lower()
    game_type = _int_value(game, "gametype")
    if "campaign" in short:
        return "campaign"
    if game_type == 6:
        return "championship"
    if game_type == 4:
        return "giant_melee"
    if game_type == 3:
        return "team_or_mvm"
    if game.get("iscustom") is True:
        return "custom"
    if "classic" in short:
        return "classic"
    return "standard_or_other"


def _metadata_priority(game: Mapping[str, Any]) -> tuple[int, int, int, int]:
    bucket = _metadata_bucket(game)
    bucket_bonus = {
        "campaign": 700,
        "championship": 650,
        "giant_melee": 500,
        "team_or_mvm": 450,
        "custom": 350,
        "classic": 300,
        "standard_or_other": 250,
    }[bucket]
    return (
        bucket_bonus,
        min(_int_value(game, "turn"), 250),
        min(_int_value(game, "slots"), 30),
        _int_value(game, "id"),
    )


def _eligible_metadata(
    game: Mapping[str, Any],
    *,
    existing_ids: frozenset[int],
    min_turn: int,
    min_slots: int,
    max_turn: int | None = None,
    max_slots: int | None = None,
) -> bool:
    game_id = _int_value(game, "id")
    return (
        game_id > 0
        and game_id not in existing_ids
        and _int_value(game, "status") == 3
        and game.get("isprivate") is not True
        and _int_value(game, "turn") >= min_turn
        and _int_value(game, "slots") >= min_slots
        and (
            max_turn is None
            or _int_value(game, "turn") <= max_turn
        )
        and (
            max_slots is None
            or _int_value(game, "slots") <= max_slots
        )
    )


def _round_robin_shortlist(
    games: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    buckets: dict[str, list[dict[str, Any]]] = {}
    for raw in games:
        game = dict(raw)
        buckets.setdefault(_metadata_bucket(game), []).append(game)
    for rows in buckets.values():
        rows.sort(key=_metadata_priority, reverse=True)

    order = (
        "campaign",
        "championship",
        "classic",
        "standard_or_other",
        "custom",
        "team_or_mvm",
        "giant_melee",
    )
    result: list[dict[str, Any]] = []
    indices = {name: 0 for name in order}

    while len(result) < limit:
        progressed = False
        for name in order:
            rows = buckets.get(name, [])
            index = indices[name]
            if index >= len(rows):
                continue
            result.append(rows[index])
            indices[name] = index + 1
            progressed = True
            if len(result) >= limit:
                break
        if not progressed:
            break
    return result


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _manifest_bucket(record: Mapping[str, Any]) -> str:
    settings = record.get("settings")
    settings = settings if isinstance(settings, Mapping) else {}
    players = record.get("player_slots")
    players = players if isinstance(players, Sequence) else ()
    active = any(
        isinstance(player, Mapping)
        and (
            _nonempty(player.get("activeadvantages"))
            or _nonempty(player.get("activehulls"))
        )
        for player in players
    )
    if active:
        return "campaign_active"
    if settings.get("campaignmode") is True:
        return "campaign"
    game = record.get("game")
    game = game if isinstance(game, Mapping) else {}
    if _int_value(game, "gametype") == 6:
        return "championship"
    if settings.get("sphere") is True:
        return "sphere"
    if settings.get("unlimitedfuel") is False:
        return "finite_fuel"
    if any(
        settings.get(key) is True
        for key in (
            "chainedintercept",
            "cloakandintercept",
            "galacticpower",
            "quantumtorpedos",
            "moscowinterceptinterference",
            "sscruiserinterceptinterference",
        )
    ):
        return "modern_standard"
    if game.get("iscustom") is True:
        return "custom"
    return "other"


def _tokenize(record: Mapping[str, Any]) -> dict[str, float]:
    tokens: dict[str, float] = {}
    game = record.get("game")
    game = game if isinstance(game, Mapping) else {}
    settings = record.get("settings")
    settings = settings if isinstance(settings, Mapping) else {}
    players = record.get("player_slots")
    players = players if isinstance(players, Sequence) else ()

    def add(token: str, weight: float) -> None:
        tokens[token] = max(weight, tokens.get(token, 0.0))

    add(f"gametype={game.get('gametype')}", 8.0)
    add(f"custom={game.get('iscustom')}", 6.0)
    add(f"maptype={game.get('maptype')}", 4.0)
    add(f"scenarioid={game.get('scenarioid')}", 5.0)
    add(f"bucket={_manifest_bucket(record)}", 25.0)
    settings_hash = record.get("settings_hash")
    if isinstance(settings_hash, str) and settings_hash:
        add(f"settings_hash={settings_hash}", 8.0)

    for key in HIGH_VALUE_SETTINGS:
        if key in settings:
            add(f"setting:{key}={settings[key]!r}", 12.0)

    for key, value in settings.items():
        if key in HIGH_VALUE_SETTINGS:
            continue
        if isinstance(value, (bool, int, float, str)) or value is None:
            rendered = repr(value)
            if len(rendered) <= 80:
                add(f"setting_any:{key}={rendered}", 1.0)

    for player in players:
        if not isinstance(player, Mapping):
            continue
        race_id = player.get("raceid")
        if isinstance(race_id, int) and not isinstance(race_id, bool):
            add(f"race={race_id}", 2.0)
        advantages = player.get("activeadvantages")
        hulls = player.get("activehulls")
        if _nonempty(advantages):
            add("activeadvantages=present", 100.0)
            add(f"activeadvantages:{advantages}", 35.0)
        if _nonempty(hulls):
            add("activehulls=present", 100.0)
            add(f"activehulls:{hulls}", 35.0)
    return tokens


def _baseline_tokens(records: Iterable[Mapping[str, Any]]) -> set[str]:
    result: set[str] = set()
    for record in records:
        result.update(_tokenize(record))
    return result


def _select_records(
    candidates: Sequence[Mapping[str, Any]],
    *,
    baseline: Sequence[Mapping[str, Any]],
    count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    remaining = [dict(record) for record in candidates]
    seen = _baseline_tokens(baseline)
    selected: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    bucket_counts: Counter[str] = Counter()

    bucket_targets = {
        "campaign_active": 6,
        "campaign": 6,
        "championship": 4,
        "sphere": 3,
        "finite_fuel": 6,
        "modern_standard": 8,
        "custom": 4,
        "other": 2,
    }

    while remaining and len(selected) < count:
        best_index = 0
        best_score = -math.inf
        best_reasons: list[str] = []

        for index, record in enumerate(remaining):
            tokens = _tokenize(record)
            novel = [
                (token, weight)
                for token, weight in tokens.items()
                if token not in seen
            ]
            novelty = sum(weight for _token, weight in novel)
            bucket = _manifest_bucket(record)
            quota_gap = max(bucket_targets.get(bucket, 0) - bucket_counts[bucket], 0)
            bucket_bonus = 30.0 if quota_gap > 0 else 0.0
            game = record.get("game")
            game = game if isinstance(game, Mapping) else {}
            size_bonus = min(_int_value(game, "turn"), 200) / 20.0
            slot_bonus = min(_int_value(game, "slots"), 20) / 4.0
            score = novelty + bucket_bonus + size_bonus + slot_bonus

            if score > best_score:
                best_score = score
                best_index = index
                best_reasons = [
                    f"bucket={bucket}",
                    f"bucket_bonus={bucket_bonus:.1f}",
                    f"novelty={novelty:.1f}",
                    f"turn_bonus={size_bonus:.1f}",
                    f"slot_bonus={slot_bonus:.1f}",
                ]
                if any(token == "activeadvantages=present" for token, _ in novel):
                    best_reasons.append("new_activeadvantages")
                if any(token == "activehulls=present" for token, _ in novel):
                    best_reasons.append("new_activehulls")

        record = remaining.pop(best_index)
        tokens = _tokenize(record)
        selected.append(record)
        bucket = _manifest_bucket(record)
        bucket_counts[bucket] += 1
        seen.update(tokens)
        game = record.get("game")
        game = game if isinstance(game, Mapping) else {}
        report_rows.append(
            {
                "game_id": record.get("game_id"),
                "name": game.get("name"),
                "turn": game.get("turn"),
                "slots": game.get("slots"),
                "gametype": game.get("gametype"),
                "bucket": bucket,
                "score": best_score,
                "reasons": best_reasons,
            }
        )

    return selected, report_rows


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _merge_records(
    baseline: Sequence[Mapping[str, Any]],
    selected: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_id: dict[int, dict[str, Any]] = {}
    for record in (*baseline, *selected):
        game_id = record.get("game_id")
        if isinstance(game_id, bool) or not isinstance(game_id, int):
            raise ValueError("manifest game_id must be an integer")
        existing = by_id.get(game_id)
        if existing is not None and existing.get("settings_hash") != record.get(
            "settings_hash"
        ):
            raise ValueError(f"conflicting manifest records for game {game_id}")
        by_id[game_id] = dict(record)
    return [by_id[game_id] for game_id in sorted(by_id)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Discover large independent public finished Planets.nu games, probe "
            "their public loadinfo rulesets, and greedily select a validation "
            "corpus that maximizes settings/campaign coverage."
        )
    )
    parser.add_argument(
        "--baseline-manifest",
        type=Path,
        default=DEFAULT_BASELINE,
    )
    parser.add_argument("--min-turn", type=int, default=55)
    parser.add_argument(
        "--max-turn",
        type=int,
        default=0,
        help="maximum final turn; 0 disables the upper bound",
    )
    parser.add_argument("--min-slots", type=int, default=8)
    parser.add_argument(
        "--max-slots",
        type=int,
        default=0,
        help="maximum game slots; 0 disables the upper bound",
    )
    parser.add_argument("--probe-limit", type=int, default=160)
    parser.add_argument("--select-count", type=int, default=36)
    parser.add_argument("--list-limit", type=int, default=0)
    parser.add_argument("--request-delay", type=float, default=0.20)
    parser.add_argument("--candidates-output", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--selected-output", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--combined-output", type=Path, default=DEFAULT_COMBINED)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.min_turn <= 0 or args.min_slots <= 0:
        print("--min-turn and --min-slots must be positive", file=sys.stderr)
        return 2
    if args.max_turn < 0 or args.max_slots < 0:
        print("--max-turn/--max-slots must be non-negative", file=sys.stderr)
        return 2
    if args.max_turn and args.max_turn < args.min_turn:
        print("--max-turn cannot be smaller than --min-turn", file=sys.stderr)
        return 2
    if args.max_slots and args.max_slots < args.min_slots:
        print("--max-slots cannot be smaller than --min-slots", file=sys.stderr)
        return 2
    if args.probe_limit <= 0 or args.select_count <= 0:
        print("--probe-limit and --select-count must be positive", file=sys.stderr)
        return 2
    if args.select_count > args.probe_limit:
        print("--select-count cannot exceed --probe-limit", file=sys.stderr)
        return 2
    if args.list_limit < 0 or args.request_delay < 0:
        print("--list-limit/request-delay must be non-negative", file=sys.stderr)
        return 2

    try:
        baseline = list(
            load_manifest_jsonl(args.baseline_manifest.read_text(encoding="utf-8"))
        )
        existing_ids = frozenset(int(record["game_id"]) for record in baseline)

        client = PlanetsNuPublicApi()
        listed = client.games_list(
            statuses=(3,),
            game_types=(2, 3, 4, 6),
            scopes=(0,),
            limit=args.list_limit,
        )
        eligible = [
            game
            for game in listed
            if _eligible_metadata(
                game,
                existing_ids=existing_ids,
                min_turn=args.min_turn,
                min_slots=args.min_slots,
                max_turn=(args.max_turn or None),
                max_slots=(args.max_slots or None),
            )
        ]
        shortlist = _round_robin_shortlist(
            eligible,
            limit=args.probe_limit,
        )

        candidates: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for position, game in enumerate(shortlist, start=1):
            game_id = _int_value(game, "id")
            try:
                info = client.load_info(game_id)
                candidates.append(build_game_manifest(dict(game), info, tier="B"))
                print(
                    json.dumps(
                        {
                            "position": position,
                            "total": len(shortlist),
                            "game_id": game_id,
                            "status": "ok",
                            "bucket": _metadata_bucket(game),
                            "turn": game.get("turn"),
                            "slots": game.get("slots"),
                        },
                        sort_keys=True,
                    )
                )
            except (CorpusApiError, ValueError) as exc:
                failures.append(
                    {
                        "game_id": game_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
                print(
                    json.dumps(
                        {
                            "position": position,
                            "total": len(shortlist),
                            "game_id": game_id,
                            "status": "failed",
                            "error": str(exc),
                        },
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
            if args.request_delay > 0 and position < len(shortlist):
                time.sleep(args.request_delay)

        selected, selection_rows = _select_records(
            candidates,
            baseline=baseline,
            count=min(args.select_count, len(candidates)),
        )
        combined = _merge_records(baseline, selected)

        _write_jsonl(args.candidates_output, candidates)
        _write_jsonl(args.selected_output, selected)
        _write_jsonl(args.combined_output, combined)

        report = {
            "schema": "planets-lab.public-validation-selection.v1",
            "baseline_manifest": str(args.baseline_manifest),
            "listed_games": len(listed),
            "eligible_games": len(eligible),
            "bounds": {
                "min_turn": args.min_turn,
                "max_turn": args.max_turn or None,
                "min_slots": args.min_slots,
                "max_slots": args.max_slots or None,
            },
            "probed_games": len(shortlist),
            "successful_loadinfo": len(candidates),
            "failed_loadinfo": failures,
            "selected_games": len(selected),
            "combined_games": len(combined),
            "selected_by_bucket": dict(
                sorted(Counter(_manifest_bucket(row) for row in selected).items())
            ),
            "selected": selection_rows,
            "outputs": {
                "candidates": str(args.candidates_output),
                "selected": str(args.selected_output),
                "combined": str(args.combined_output),
            },
        }
        _write_json(args.report_output, report)

        print("===== PUBLIC VALIDATION CORPUS DISCOVERY =====")
        print(f"listed_games:       {len(listed)}")
        print(f"eligible_games:     {len(eligible)}")
        print(f"probed_games:       {len(shortlist)}")
        print(f"loadinfo_ok:        {len(candidates)}")
        print(f"loadinfo_failed:    {len(failures)}")
        print(f"selected_games:     {len(selected)}")
        print(f"combined_games:     {len(combined)}")
        print(f"selected_by_bucket: {report['selected_by_bucket']}")
        print(f"selected_manifest:  {args.selected_output}")
        print(f"combined_manifest:  {args.combined_output}")
        print(f"report:             {args.report_output}")
        return 0 if selected else 1
    except (OSError, ValueError, CorpusApiError, CorpusIndexError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
