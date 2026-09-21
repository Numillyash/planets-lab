from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.columnar_io import write_rows_parquet_arrow


FEATURE_INDEX_SCHEMA = "planets-lab.game-feature-index.v1"
FEATURE_INDEX_BUILD_SCHEMA = "planets-lab.game-feature-index-build.v1"

FEATURE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("schema_version", "VARCHAR"),
    ("game_id", "BIGINT"),
    ("feature", "VARCHAR"),
    ("value_type", "VARCHAR"),
    ("known", "BOOLEAN"),
    ("bool_value", "BOOLEAN"),
    ("int_value", "BIGINT"),
    ("double_value", "DOUBLE"),
    ("text_value", "VARCHAR"),
    ("source_kind", "VARCHAR"),
    ("source_location", "VARCHAR"),
)

# Settings are explicitly allowlisted. Manifest settings can contain descriptive
# or secret-like fields (for example gamepassword); the feature index is an
# evidence-selection artifact, not a wholesale copy of /game/loadinfo.
SETTING_FEATURES: tuple[str, ...] = (
    "sphere",
    "mapshape",
    "mapwidth",
    "mapheight",
    "productionqueue",
    "planetaryproductionqueue",
    "shiplimit",
    "shiplimittype",
    "plsminships",
    "plsshipsperplanet",
    "plsextraships",
    "combatrng",
    "cloakandintercept",
    "chainedintercept",
    "campaignmode",
    "teamsize",
    "maxallies",
    "maxsafepassage",
    "maxshareintel",
    "alliessharefullinfo",
    "allshareintel",
    "galacticpower",
    "superspyadvanced",
    "groundattackadjustments",
    "cloningenabled",
    "nuionstorms",
    "unlimitedfuel",
    "nominefields",
    "nowarpwells",
    "hardenedmines",
    "stealthmode",
    "fascistdoublebeams",
    "crystalwebimmunity",
    "birdshaveenlighten",
    "burrowsimprovemining",
    "empirehasaggregator",
    "hivesdetectlife",
    "nochunnelhives",
    "hrossfightertransfer",
    "moscowinterceptinterference",
    "quantumtorpedos",
    "sapphirenowebimmunity",
    "sensorsweepcombatpodscanrange",
    "sensorsweepnoncombatpodscanrange",
    "webdiplomacylevel",
    "webdraindiplomacylevel",
)

GAME_FEATURES: tuple[tuple[str, str], ...] = (
    ("game.status", "status"),
    ("game.status_name", "statusname"),
    ("game.game_type", "gametype"),
    ("game.is_custom", "iscustom"),
    ("game.is_private", "isprivate"),
    ("game.scenario_id", "scenarioid"),
    ("game.map_type", "maptype"),
    ("game.win_condition", "wincondition"),
    ("game.final_turn", "turn"),
    ("game.date_created", "datecreated"),
    ("game.date_ended", "dateended"),
)

HORWASP_RACE_ID = 12


@dataclass(frozen=True, slots=True)
class FeaturePredicate:
    feature: str
    op: str
    expected: Any = None


@dataclass(frozen=True, slots=True)
class FeatureDecision:
    game_id: int
    included: bool
    predicates: tuple[dict[str, Any], ...]


PROFILE_PREDICATES: dict[str, tuple[FeaturePredicate, ...]] = {
    "all-indexed": (),
    "ordinary-classic": (
        FeaturePredicate("game.status", "eq", 3),
        FeaturePredicate("game.game_type", "eq", 2),
        FeaturePredicate("game.is_custom", "eq", False),
        FeaturePredicate("game.scenario_id", "eq", 0),
        FeaturePredicate("settings.campaignmode", "eq", False),
        FeaturePredicate("settings.sphere", "eq", False),
        FeaturePredicate("population.horwasp_present", "eq", False),
    ),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _typed_values(value: Any) -> tuple[str, bool | None, int | None, float | None, str | None]:
    if isinstance(value, bool):
        return "boolean", value, None, None, None
    if isinstance(value, int):
        return "integer", None, value, None, None
    if isinstance(value, float):
        return "double", None, None, value, None
    if isinstance(value, str):
        return "string", None, None, None, value
    if isinstance(value, (list, dict)):
        return "json", None, None, None, _canonical_json(value)
    raise TypeError(f"unsupported feature value type: {type(value).__name__}")


def feature_row(
    *,
    game_id: int,
    feature: str,
    value: Any = None,
    known: bool,
    source_kind: str,
    source_location: str,
) -> dict[str, Any]:
    if known:
        if value is None:
            raise ValueError(f"known feature {feature!r} cannot have null value")
        value_type, bool_value, int_value, double_value, text_value = _typed_values(value)
    else:
        value_type = "unknown"
        bool_value = int_value = double_value = text_value = None
    return {
        "schema_version": FEATURE_INDEX_SCHEMA,
        "game_id": game_id,
        "feature": feature,
        "value_type": value_type,
        "known": known,
        "bool_value": bool_value,
        "int_value": int_value,
        "double_value": double_value,
        "text_value": text_value,
        "source_kind": source_kind,
        "source_location": source_location,
    }


def feature_value(row: Mapping[str, Any]) -> Any:
    if row.get("known") is not True:
        return None
    value_type = row.get("value_type")
    if value_type == "boolean":
        return row.get("bool_value")
    if value_type == "integer":
        return row.get("int_value")
    if value_type == "double":
        return row.get("double_value")
    if value_type == "string":
        return row.get("text_value")
    if value_type == "json":
        raw = row.get("text_value")
        return json.loads(raw) if isinstance(raw, str) else None
    raise ValueError(f"unsupported feature value_type {value_type!r}")


def _manifest_row(
    *,
    game_id: int,
    feature: str,
    container: Mapping[str, Any],
    key: str,
    source_location: str,
) -> dict[str, Any]:
    if key not in container or container.get(key) is None:
        return feature_row(
            game_id=game_id,
            feature=feature,
            known=False,
            source_kind="manifest_missing",
            source_location=source_location,
        )
    return feature_row(
        game_id=game_id,
        feature=feature,
        value=container[key],
        known=True,
        source_kind="manifest",
        source_location=source_location,
    )


def manifest_feature_rows(
    manifest: Mapping[str, Any],
    *,
    manifest_location: str,
) -> list[dict[str, Any]]:
    game_id = manifest.get("game_id")
    if isinstance(game_id, bool) or not isinstance(game_id, int) or game_id <= 0:
        raise ValueError("manifest game_id must be a positive integer")
    game = manifest.get("game")
    settings = manifest.get("settings")
    slots = manifest.get("player_slots")
    if not isinstance(game, Mapping):
        raise ValueError(f"game {game_id}: manifest.game must be an object")
    if not isinstance(settings, Mapping):
        raise ValueError(f"game {game_id}: manifest.settings must be an object")
    if not isinstance(slots, list):
        raise ValueError(f"game {game_id}: manifest.player_slots must be a list")

    rows: list[dict[str, Any]] = []
    base = f"{manifest_location}:game_id={game_id}"
    for feature, key in GAME_FEATURES:
        rows.append(
            _manifest_row(
                game_id=game_id,
                feature=feature,
                container=game,
                key=key,
                source_location=f"{base}:game.{key}",
            )
        )
    for key in SETTING_FEATURES:
        rows.append(
            _manifest_row(
                game_id=game_id,
                feature=f"settings.{key}",
                container=settings,
                key=key,
                source_location=f"{base}:settings.{key}",
            )
        )

    race_ids = {
        int(slot["raceid"])
        for slot in slots
        if isinstance(slot, Mapping)
        and isinstance(slot.get("raceid"), int)
        and not isinstance(slot.get("raceid"), bool)
    }
    rows.append(
        feature_row(
            game_id=game_id,
            feature="population.player_slot_count",
            value=len(slots),
            known=True,
            source_kind="manifest",
            source_location=f"{base}:player_slots",
        )
    )
    rows.append(
        feature_row(
            game_id=game_id,
            feature="population.races_present",
            value=sorted(race_ids),
            known=True,
            source_kind="manifest",
            source_location=f"{base}:player_slots[*].raceid",
        )
    )
    for race_id in range(1, HORWASP_RACE_ID + 1):
        rows.append(
            feature_row(
                game_id=game_id,
                feature=f"population.race.{race_id}.present",
                value=race_id in race_ids,
                known=True,
                source_kind="manifest",
                source_location=f"{base}:player_slots[*].raceid",
            )
        )
    rows.append(
        feature_row(
            game_id=game_id,
            feature="population.horwasp_present",
            value=HORWASP_RACE_ID in race_ids,
            known=True,
            source_kind="manifest",
            source_location=f"{base}:player_slots[*].raceid",
        )
    )
    settings_hash = manifest.get("settings_hash")
    rows.append(
        feature_row(
            game_id=game_id,
            feature="coverage.settings_hash",
            value=settings_hash if isinstance(settings_hash, str) else None,
            known=isinstance(settings_hash, str),
            source_kind="manifest" if isinstance(settings_hash, str) else "manifest_missing",
            source_location=f"{base}:settings_hash",
        )
    )

    # Current loadinfo/loadall evidence has no attributable Host/engine version
    # field. Keep these explicit UNKNOWN rows rather than deriving a version from
    # dates, sector names or third-party analyzer labels.
    for feature in ("engine.host_version", "engine.engine_version"):
        rows.append(
            feature_row(
                game_id=game_id,
                feature=feature,
                known=False,
                source_kind="unavailable",
                source_location="/game/loadinfo + /game/loadall:no attributable version field",
            )
        )
    return rows


def _decode_json_member(raw: bytes, *, name: str) -> Mapping[str, Any]:
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, Mapping):
        raise ValueError(f"{name}: turn payload must be an object")
    return parsed


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _vcr_shape(vcr: Mapping[str, Any]) -> str:
    def kind(side: Any) -> str:
        if not isinstance(side, Mapping):
            return "missing"
        hull_id = _intish(side.get("hullid"))
        if hull_id is None:
            return "unknown"
        return "planet" if hull_id <= 0 else "ship"

    return f"{kind(vcr.get('left'))}_vs_{kind(vcr.get('right'))}"


def archive_feature_rows(
    *,
    game_id: int,
    archive_path: Path,
    data: bytes | None,
) -> list[dict[str, Any]]:
    location = str(archive_path)
    rows = [
        feature_row(
            game_id=game_id,
            feature="coverage.archive_present",
            value=data is not None,
            known=True,
            source_kind="local_cache",
            source_location=location,
        )
    ]
    archive_features = (
        "coverage.archive_sha256",
        "coverage.archive_bytes",
        "coverage.turn_member_count",
        "coverage.player_stream_count",
        "coverage.first_archive_turn",
        "coverage.last_archive_turn",
        "coverage.archive_turn_count",
        "coverage.missing_grid_cells",
        "coverage.rectangular_grid_complete",
        "evidence.archive_transition_count",
        "evidence.vcr.raw_observation_count",
        "evidence.vcr.unique_count",
        "evidence.vcr.ship_vs_ship_count",
        "evidence.vcr.ship_vs_planet_count",
        "evidence.vcr.payload_conflict_count",
        "evidence.relations.members_available",
        "evidence.relations.complete_across_members",
        "evidence.relations.record_count",
    )
    if data is None:
        rows.extend(
            feature_row(
                game_id=game_id,
                feature=feature,
                known=False,
                source_kind="archive_missing",
                source_location=location,
            )
            for feature in archive_features
        )
        return rows

    members = turn_members(data)
    raw_members = read_archive_members(data, [member.name for member in members])
    players = sorted({member.player for member in members})
    turns = sorted({member.turn for member in members})
    actual_cells = {(member.player, member.turn) for member in members}
    expected_cells = {(player, turn) for player in players for turn in turns}
    missing_grid_cells = len(expected_cells - actual_cells)
    transitions = 0
    by_player: dict[int, list[int]] = defaultdict(list)
    for member in members:
        by_player[member.player].append(member.turn)
    for player_turns in by_player.values():
        ordered = sorted(set(player_turns))
        transitions += sum(
            after == before + 1 for before, after in zip(ordered, ordered[1:])
        )

    observations: dict[tuple[int, int, int], list[str]] = defaultdict(list)
    representative: dict[tuple[int, int, int], Mapping[str, Any]] = {}
    raw_vcr_observations = 0
    relations_members_available = 0
    relation_record_count = 0

    for member in members:
        parsed = _decode_json_member(raw_members[member.name], name=member.name)
        game = parsed.get("game")
        embedded_turn = _intish(game.get("turn")) if isinstance(game, Mapping) else None
        observed_game = _intish(game.get("id")) if isinstance(game, Mapping) else None
        if observed_game != game_id:
            raise ValueError(
                f"{member.name}: game id {observed_game!r} does not match manifest {game_id}"
            )
        relations = parsed.get("relations")
        if isinstance(relations, list):
            relations_members_available += 1
            relation_record_count += sum(isinstance(item, Mapping) for item in relations)
        vcrs = parsed.get("vcrs")
        if not isinstance(vcrs, list):
            continue
        for raw_vcr in vcrs:
            if not isinstance(raw_vcr, Mapping):
                continue
            vcr_id = _intish(raw_vcr.get("id"))
            if vcr_id is None:
                continue
            battle_turn = _intish(raw_vcr.get("turn"))
            if battle_turn is None:
                battle_turn = embedded_turn
            if battle_turn is None:
                continue
            key = (game_id, battle_turn, vcr_id)
            payload_hash = hashlib.sha256(
                _canonical_json(raw_vcr).encode("utf-8")
            ).hexdigest()
            observations[key].append(payload_hash)
            representative.setdefault(key, raw_vcr)
            raw_vcr_observations += 1

    shapes: Counter[str] = Counter()
    payload_conflicts = 0
    for key, hashes in observations.items():
        if len(set(hashes)) != 1:
            payload_conflicts += 1
        shapes[_vcr_shape(representative[key])] += 1

    facts: dict[str, Any] = {
        "coverage.archive_sha256": hashlib.sha256(data).hexdigest(),
        "coverage.archive_bytes": len(data),
        "coverage.turn_member_count": len(members),
        "coverage.player_stream_count": len(players),
        "coverage.first_archive_turn": turns[0] if turns else 0,
        "coverage.last_archive_turn": turns[-1] if turns else 0,
        "coverage.archive_turn_count": len(turns),
        "coverage.missing_grid_cells": missing_grid_cells,
        "coverage.rectangular_grid_complete": missing_grid_cells == 0,
        "evidence.archive_transition_count": transitions,
        "evidence.vcr.raw_observation_count": raw_vcr_observations,
        "evidence.vcr.unique_count": len(observations),
        "evidence.vcr.ship_vs_ship_count": shapes.get("ship_vs_ship", 0),
        "evidence.vcr.ship_vs_planet_count": shapes.get("ship_vs_planet", 0),
        "evidence.vcr.payload_conflict_count": payload_conflicts,
        "evidence.relations.members_available": relations_members_available,
        "evidence.relations.complete_across_members": (
            relations_members_available == len(members)
        ),
    }
    for feature, value in facts.items():
        rows.append(
            feature_row(
                game_id=game_id,
                feature=feature,
                value=value,
                known=True,
                source_kind="loadall_archive",
                source_location=location,
            )
        )

    relations_complete = relations_members_available == len(members)
    rows.append(
        feature_row(
            game_id=game_id,
            feature="evidence.relations.record_count",
            value=relation_record_count if relations_complete else None,
            known=relations_complete,
            source_kind=(
                "loadall_archive"
                if relations_complete
                else "archive_partial_field_coverage"
            ),
            source_location=location,
        )
    )
    return rows


def compiled_movement_feature_row(
    *,
    game_id: int,
    compiled_dir: Path,
) -> dict[str, Any]:
    meta = (
        compiled_dir
        / "mechanics"
        / "movement_transitions"
        / f"game_id={game_id}"
        / "_meta.json"
    )
    feature = "evidence.movement_transition_count"
    if not meta.is_file():
        return feature_row(
            game_id=game_id,
            feature=feature,
            known=False,
            source_kind="compiled_missing",
            source_location=str(meta),
        )
    payload = json.loads(meta.read_text(encoding="utf-8"))
    value = payload.get("transition_rows")
    if isinstance(value, bool) or not isinstance(value, int):
        return feature_row(
            game_id=game_id,
            feature=feature,
            known=False,
            source_kind="compiled_malformed",
            source_location=f"{meta}:transition_rows",
        )
    return feature_row(
        game_id=game_id,
        feature=feature,
        value=value,
        known=True,
        source_kind="compiled_movement",
        source_location=f"{meta}:transition_rows",
    )


def build_feature_rows(
    manifests: Sequence[Mapping[str, Any]],
    *,
    archive_dir: Path,
    compiled_dir: Path,
    manifest_location: str,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for manifest in sorted(manifests, key=lambda item: int(item["game_id"])):
        game_id = int(manifest["game_id"])
        if game_id in seen:
            raise ValueError(f"duplicate game_id {game_id}")
        seen.add(game_id)
        rows.extend(
            manifest_feature_rows(manifest, manifest_location=manifest_location)
        )
        archive_path = archive_dir / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes() if archive_path.is_file() else None
        rows.extend(
            archive_feature_rows(
                game_id=game_id,
                archive_path=archive_path,
                data=archive_data,
            )
        )
        rows.append(
            compiled_movement_feature_row(
                game_id=game_id,
                compiled_dir=compiled_dir,
            )
        )

    rows.sort(key=lambda row: (int(row["game_id"]), str(row["feature"])))
    keys = [(row["game_id"], row["feature"]) for row in rows]
    if len(keys) != len(set(keys)):
        duplicates = [key for key, count in Counter(keys).items() if count > 1]
        raise ValueError(f"duplicate feature rows: {duplicates[:10]}")
    return tuple(rows)


def feature_coverage(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        counts[str(row["feature"])]["rows"] += 1
        counts[str(row["feature"])][
            "known" if row.get("known") is True else "unknown"
        ] += 1
    return {
        feature: {
            "rows": counter["rows"],
            "known": counter["known"],
            "unknown": counter["unknown"],
        }
        for feature, counter in sorted(counts.items())
    }


def write_feature_index(
    *,
    rows: Sequence[Mapping[str, Any]],
    parquet_path: Path,
    database_path: Path,
) -> dict[str, Any]:
    write_rows_parquet_arrow(rows=rows, columns=FEATURE_COLUMNS, path=parquet_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    try:
        sql_path = str(parquet_path.resolve()).replace("'", "''")
        connection.execute("DROP VIEW IF EXISTS game_features")
        connection.execute(
            f"CREATE VIEW game_features AS SELECT * FROM read_parquet('{sql_path}')"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS feature_index_metadata "
            "(key VARCHAR PRIMARY KEY, value VARCHAR)"
        )
        connection.execute("DELETE FROM feature_index_metadata")
        connection.executemany(
            "INSERT INTO feature_index_metadata VALUES (?, ?)",
            [
                ("feature_index_schema", FEATURE_INDEX_SCHEMA),
                ("feature_index_build_schema", FEATURE_INDEX_BUILD_SCHEMA),
            ],
        )
    finally:
        connection.close()
    return {
        "schema": FEATURE_INDEX_BUILD_SCHEMA,
        "feature_index_schema": FEATURE_INDEX_SCHEMA,
        "games": len({int(row["game_id"]) for row in rows}),
        "rows": len(rows),
        "known_rows": sum(row.get("known") is True for row in rows),
        "unknown_rows": sum(row.get("known") is not True for row in rows),
        "coverage": feature_coverage(rows),
        "parquet_sha256": hashlib.sha256(parquet_path.read_bytes()).hexdigest(),
    }


def load_feature_rows(path: Path) -> tuple[dict[str, Any], ...]:
    table = pq.read_table(path)
    rows = table.to_pylist()
    rows.sort(key=lambda row: (int(row["game_id"]), str(row["feature"])))
    return tuple(rows)


def _compare(actual: Any, op: str, expected: Any) -> bool:
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "gt":
        return actual > expected
    if op == "ge":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "le":
        return actual <= expected
    if op == "in":
        return actual in expected
    raise ValueError(f"unsupported predicate op {op!r}")


def select_games(
    rows: Sequence[Mapping[str, Any]],
    predicates: Sequence[FeaturePredicate],
) -> tuple[FeatureDecision, ...]:
    by_game: dict[int, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_game[int(row["game_id"])][str(row["feature"])] = row

    decisions: list[FeatureDecision] = []
    for game_id in sorted(by_game):
        game_rows = by_game[game_id]
        results: list[dict[str, Any]] = []
        included = True
        for predicate in predicates:
            row = game_rows.get(predicate.feature)
            if row is None or row.get("known") is not True:
                included = False
                results.append(
                    {
                        "feature": predicate.feature,
                        "op": predicate.op,
                        "expected": predicate.expected,
                        "status": "unknown",
                        "actual": None,
                        "source_kind": row.get("source_kind")
                        if row
                        else "feature_missing",
                        "source_location": row.get("source_location") if row else None,
                    }
                )
                continue
            actual = feature_value(row)
            if predicate.op == "known":
                matched = True
            else:
                matched = _compare(actual, predicate.op, predicate.expected)
            if not matched:
                included = False
            results.append(
                {
                    "feature": predicate.feature,
                    "op": predicate.op,
                    "expected": predicate.expected,
                    "status": "match" if matched else "mismatch",
                    "actual": actual,
                    "source_kind": row.get("source_kind"),
                    "source_location": row.get("source_location"),
                }
            )
        decisions.append(
            FeatureDecision(
                game_id=game_id,
                included=included,
                predicates=tuple(results),
            )
        )
    return tuple(decisions)


def profile_predicates(name: str) -> tuple[FeaturePredicate, ...]:
    try:
        return PROFILE_PREDICATES[name]
    except KeyError as exc:
        raise ValueError(
            f"unknown feature profile {name!r}; expected one of "
            f"{sorted(PROFILE_PREDICATES)}"
        ) from exc


def selected_game_ids(
    rows: Sequence[Mapping[str, Any]],
    *,
    profile: str,
    extra_predicates: Sequence[FeaturePredicate] = (),
) -> tuple[int, ...]:
    predicates = (*profile_predicates(profile), *extra_predicates)
    return tuple(
        decision.game_id
        for decision in select_games(rows, predicates)
        if decision.included
    )


def game_id_from_archive_path(path: Path) -> int | None:
    match = re.fullmatch(r"game-(\d+)\.zip", path.name)
    return int(match.group(1)) if match else None
