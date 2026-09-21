from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from planets_lab.corpus.feature_index import (
    FEATURE_INDEX_SCHEMA,
    FeaturePredicate,
    archive_feature_rows,
    build_feature_rows,
    feature_row,
    feature_value,
    manifest_feature_rows,
    select_games,
    write_feature_index,
)
from planets_lab.corpus.manifest import MANIFEST_SCHEMA


def _manifest(
    game_id: int = 42,
    *,
    sphere: bool = False,
    campaign: bool = False,
    custom: bool = False,
    game_type: int = 2,
    races: tuple[int, ...] = (1, 2),
) -> dict:
    return {
        "schema": MANIFEST_SCHEMA,
        "game_id": game_id,
        "tier": "B",
        "settings_hash": f"{game_id:064x}"[-64:],
        "game": {
            "id": game_id,
            "status": 3,
            "statusname": "Finished",
            "gametype": game_type,
            "iscustom": custom,
            "isprivate": False,
            "scenarioid": 0,
            "maptype": 2,
            "wincondition": 1,
            "turn": 20,
            "datecreated": "2026-01-01",
            "dateended": "2026-02-01",
        },
        "settings": {
            "sphere": sphere,
            "campaignmode": campaign,
            "productionqueue": False,
            "planetaryproductionqueue": False,
            "shiplimit": 500,
            "shiplimittype": 0,
            "plsminships": 0,
            "plsshipsperplanet": 1,
            "plsextraships": 0,
            "combatrng": 0,
            "cloakandintercept": False,
            "chainedintercept": False,
            "teamsize": 1,
            "maxallies": 1,
            "maxsafepassage": 35,
            "maxshareintel": 35,
            "alliessharefullinfo": False,
            "allshareintel": False,
            "galacticpower": False,
            "superspyadvanced": False,
            "groundattackadjustments": "",
            "cloningenabled": True,
            "nuionstorms": False,
            "unlimitedfuel": False,
            "nominefields": False,
            "nowarpwells": False,
            "hardenedmines": False,
            "stealthmode": False,
            "fascistdoublebeams": False,
            "crystalwebimmunity": 0,
            "birdshaveenlighten": False,
            "burrowsimprovemining": False,
            "empirehasaggregator": False,
            "hivesdetectlife": False,
            "nochunnelhives": False,
            "hrossfightertransfer": False,
            "moscowinterceptinterference": False,
            "quantumtorpedos": False,
            "sapphirenowebimmunity": False,
            "sensorsweepcombatpodscanrange": 0,
            "sensorsweepnoncombatpodscanrange": 0,
            "webdiplomacylevel": 0,
            "webdraindiplomacylevel": 0,
        },
        "player_slots": [
            {"id": index + 1, "raceid": race_id}
            for index, race_id in enumerate(races)
        ],
    }


def _turn_payload(
    game_id: int,
    player: int,
    turn: int,
    *,
    vcrs: list[dict] | None = None,
    relations: list[dict] | None = None,
) -> dict:
    return {
        "game": {"id": game_id, "turn": turn},
        "player": {"id": player, "raceid": player},
        "players": [{"id": 1, "raceid": 1}, {"id": 2, "raceid": 2}],
        "settings": {"combatrng": 0},
        "planets": [],
        "ships": [],
        "starbases": [],
        "ionstorms": [],
        "minefields": [],
        "vcrs": vcrs or [],
        "relations": relations if relations is not None else [],
    }


def _archive(game_id: int = 42) -> bytes:
    ship_v_ship = {
        "id": 1,
        "turn": 1,
        "left": {"hullid": 1, "objectid": 10},
        "right": {"hullid": 2, "objectid": 20},
    }
    ship_v_planet = {
        "id": 2,
        "turn": 1,
        "left": {"hullid": 1, "objectid": 10},
        "right": {"hullid": 0, "objectid": 99},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "player1-turn0.trn",
            json.dumps(_turn_payload(game_id, 1, 0, relations=[{"id": 1}])),
        )
        archive.writestr(
            "player1-turn1.trn",
            json.dumps(
                _turn_payload(
                    game_id,
                    1,
                    1,
                    vcrs=[ship_v_ship, ship_v_planet],
                    relations=[{"id": 1}],
                )
            ),
        )
        archive.writestr(
            "player2-turn0.trn",
            json.dumps(_turn_payload(game_id, 2, 0, relations=[{"id": 2}])),
        )
        archive.writestr(
            "player2-turn1.trn",
            json.dumps(
                _turn_payload(
                    game_id,
                    2,
                    1,
                    vcrs=[ship_v_ship, ship_v_planet],
                    relations=[{"id": 2}],
                )
            ),
        )
    return buffer.getvalue()


def _by_feature(rows: list[dict] | tuple[dict, ...]) -> dict[str, dict]:
    return {str(row["feature"]): dict(row) for row in rows}


def test_unknown_is_distinct_from_false() -> None:
    false_row = feature_row(
        game_id=1,
        feature="settings.flag",
        value=False,
        known=True,
        source_kind="manifest",
        source_location="fixture",
    )
    unknown_row = feature_row(
        game_id=1,
        feature="engine.version",
        known=False,
        source_kind="unavailable",
        source_location="fixture",
    )

    assert false_row["known"] is True
    assert false_row["bool_value"] is False
    assert feature_value(false_row) is False

    assert unknown_row["known"] is False
    assert unknown_row["bool_value"] is None
    assert feature_value(unknown_row) is None


def test_manifest_feature_rows_keep_false_and_explicit_engine_unknown() -> None:
    rows = _by_feature(
        manifest_feature_rows(_manifest(), manifest_location="manifest.jsonl")
    )

    assert rows["settings.sphere"]["known"] is True
    assert rows["settings.sphere"]["bool_value"] is False
    assert rows["settings.combatrng"]["int_value"] == 0
    assert rows["population.horwasp_present"]["bool_value"] is False
    assert rows["engine.host_version"]["known"] is False
    assert rows["engine.engine_version"]["known"] is False


def test_archive_features_deduplicate_vcrs_and_count_shapes() -> None:
    rows = _by_feature(
        archive_feature_rows(
            game_id=42,
            archive_path=Path("game-42.zip"),
            data=_archive(),
        )
    )

    assert rows["coverage.archive_present"]["bool_value"] is True
    assert rows["coverage.turn_member_count"]["int_value"] == 4
    assert rows["coverage.rectangular_grid_complete"]["bool_value"] is True
    assert rows["evidence.archive_transition_count"]["int_value"] == 2
    assert rows["evidence.vcr.raw_observation_count"]["int_value"] == 4
    assert rows["evidence.vcr.unique_count"]["int_value"] == 2
    assert rows["evidence.vcr.ship_vs_ship_count"]["int_value"] == 1
    assert rows["evidence.vcr.ship_vs_planet_count"]["int_value"] == 1
    assert rows["evidence.vcr.payload_conflict_count"]["int_value"] == 0
    assert rows["evidence.relations.members_available"]["int_value"] == 4
    assert rows["evidence.relations.complete_across_members"]["bool_value"] is True
    assert rows["evidence.relations.record_count"]["known"] is True
    assert rows["evidence.relations.record_count"]["int_value"] == 4


def test_missing_archive_is_known_absence_but_metrics_are_unknown() -> None:
    rows = _by_feature(
        archive_feature_rows(
            game_id=42,
            archive_path=Path("missing.zip"),
            data=None,
        )
    )

    assert rows["coverage.archive_present"]["known"] is True
    assert rows["coverage.archive_present"]["bool_value"] is False
    assert rows["evidence.vcr.unique_count"]["known"] is False
    assert rows["evidence.vcr.unique_count"]["int_value"] is None


def test_selector_fails_closed_on_unknown_and_reports_reason() -> None:
    rows = [
        feature_row(
            game_id=1,
            feature="settings.sphere",
            known=False,
            source_kind="archive_missing",
            source_location="fixture",
        ),
        feature_row(
            game_id=2,
            feature="settings.sphere",
            value=False,
            known=True,
            source_kind="manifest",
            source_location="fixture",
        ),
    ]
    decisions = select_games(
        rows,
        [FeaturePredicate("settings.sphere", "eq", False)],
    )

    first, second = decisions
    assert first.included is False
    assert first.predicates[0]["status"] == "unknown"
    assert first.predicates[0]["source_kind"] == "archive_missing"
    assert second.included is True
    assert second.predicates[0]["status"] == "match"


def test_ordinary_classic_profile_excludes_campaign_horwasp_game() -> None:
    from planets_lab.corpus.feature_index import profile_predicates

    normal = manifest_feature_rows(
        _manifest(10),
        manifest_location="manifest.jsonl",
    )
    special = manifest_feature_rows(
        _manifest(
            20,
            sphere=True,
            campaign=True,
            game_type=4,
            races=(1, 12),
        ),
        manifest_location="manifest.jsonl",
    )
    standard_manifest = _manifest(30)
    standard_manifest["settings"].update(
        {
            "productionqueue": True,
            "planetaryproductionqueue": True,
            "shiplimittype": 1,
            "plsminships": 20,
            "cloakandintercept": True,
            "galacticpower": True,
            "superspyadvanced": True,
            "fascistdoublebeams": True,
            "unlimitedfuel": True,
        }
    )
    standard = manifest_feature_rows(
        standard_manifest,
        manifest_location="manifest.jsonl",
    )
    decisions = select_games(
        [*normal, *special, *standard],
        profile_predicates("ordinary-classic"),
    )

    assert [(row.game_id, row.included) for row in decisions] == [
        (10, True),
        (20, False),
        (30, False),
    ]
    failed = [
        predicate["feature"]
        for predicate in decisions[1].predicates
        if predicate["status"] != "match"
    ]
    assert "game.game_type" in failed
    assert "settings.campaignmode" in failed
    assert "settings.sphere" in failed
    assert "population.horwasp_present" in failed

    standard_failed = [
        predicate["feature"]
        for predicate in decisions[2].predicates
        if predicate["status"] != "match"
    ]
    assert "settings.productionqueue" in standard_failed
    assert "settings.cloakandintercept" in standard_failed


def test_build_is_deterministic_and_reads_compiled_movement_count(tmp_path) -> None:
    archive_dir = tmp_path / "loadall"
    archive_dir.mkdir()
    (archive_dir / "game-42.zip").write_bytes(_archive())

    compiled_dir = tmp_path / "compiled"
    movement = (
        compiled_dir
        / "mechanics"
        / "movement_transitions"
        / "game_id=42"
    )
    movement.mkdir(parents=True)
    (movement / "_meta.json").write_text(
        json.dumps({"transition_rows": 123}),
        encoding="utf-8",
    )

    rows1 = build_feature_rows(
        [_manifest()],
        archive_dir=archive_dir,
        compiled_dir=compiled_dir,
        manifest_location="manifest.jsonl",
    )
    rows2 = build_feature_rows(
        [_manifest()],
        archive_dir=archive_dir,
        compiled_dir=compiled_dir,
        manifest_location="manifest.jsonl",
    )
    assert rows1 == rows2
    indexed = _by_feature(rows1)
    assert indexed["evidence.movement_transition_count"]["int_value"] == 123

    first_parquet = tmp_path / "one.parquet"
    second_parquet = tmp_path / "two.parquet"
    first_db = tmp_path / "one.duckdb"
    second_db = tmp_path / "two.duckdb"
    first = write_feature_index(
        rows=rows1,
        parquet_path=first_parquet,
        database_path=first_db,
    )
    second = write_feature_index(
        rows=rows2,
        parquet_path=second_parquet,
        database_path=second_db,
    )

    assert first["feature_index_schema"] == FEATURE_INDEX_SCHEMA
    assert first["parquet_sha256"] == second["parquet_sha256"]
    assert first_parquet.read_bytes() == second_parquet.read_bytes()



def test_partial_relation_field_coverage_does_not_become_zero(tmp_path) -> None:
    buffer = io.BytesIO()
    first = _turn_payload(42, 1, 0, relations=[{"id": 1}])
    second = _turn_payload(42, 1, 1)
    second.pop("relations")
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("player1-turn0.trn", json.dumps(first))
        archive.writestr("player1-turn1.trn", json.dumps(second))

    rows = _by_feature(
        archive_feature_rows(
            game_id=42,
            archive_path=tmp_path / "game-42.zip",
            data=buffer.getvalue(),
        )
    )

    assert rows["evidence.relations.members_available"]["int_value"] == 1
    assert (
        rows["evidence.relations.complete_across_members"]["bool_value"]
        is False
    )
    assert rows["evidence.relations.record_count"]["known"] is False
    assert rows["evidence.relations.record_count"]["int_value"] is None



def test_combat_planar_no_horwasp_profile_preserves_legacy_ordinary_scope() -> None:
    from planets_lab.corpus.feature_index import (
        profile_predicates,
        profile_selection_summary,
    )

    classic = manifest_feature_rows(
        _manifest(10),
        manifest_location="manifest.jsonl",
    )
    custom_campaign = manifest_feature_rows(
        _manifest(20, campaign=True, custom=True),
        manifest_location="manifest.jsonl",
    )
    horwasp_sphere = manifest_feature_rows(
        _manifest(
            30,
            sphere=True,
            campaign=True,
            game_type=4,
            races=(1, 12),
        ),
        manifest_location="manifest.jsonl",
    )

    rows = [*classic, *custom_campaign, *horwasp_sphere]
    decisions = select_games(
        rows,
        profile_predicates("combat-planar-no-horwasp"),
    )
    assert [(row.game_id, row.included) for row in decisions] == [
        (10, True),
        (20, True),
        (30, False),
    ]

    summary = profile_selection_summary(
        rows,
        profile="combat-planar-no-horwasp",
    )
    assert summary == {
        "profile": "combat-planar-no-horwasp",
        "predicate_count": 3,
        "included_game_ids": [10, 20],
        "excluded_game_ids": [30],
        "unknown_game_ids": [],
    }



def test_feature_scope_classifies_selected_excluded_unknown_and_unindexed(
    tmp_path,
) -> None:
    from planets_lab.corpus.feature_scope import load_feature_scope

    rows = [
        feature_row(
            game_id=1,
            feature="game.status",
            value=3,
            known=True,
            source_kind="fixture",
            source_location="fixture",
        ),
        feature_row(
            game_id=1,
            feature="settings.sphere",
            value=False,
            known=True,
            source_kind="fixture",
            source_location="fixture",
        ),
        feature_row(
            game_id=1,
            feature="population.horwasp_present",
            value=False,
            known=True,
            source_kind="fixture",
            source_location="fixture",
        ),
        feature_row(
            game_id=2,
            feature="game.status",
            value=3,
            known=True,
            source_kind="fixture",
            source_location="fixture",
        ),
        feature_row(
            game_id=2,
            feature="settings.sphere",
            value=True,
            known=True,
            source_kind="fixture",
            source_location="fixture",
        ),
        feature_row(
            game_id=2,
            feature="population.horwasp_present",
            value=False,
            known=True,
            source_kind="fixture",
            source_location="fixture",
        ),
        feature_row(
            game_id=3,
            feature="game.status",
            value=3,
            known=True,
            source_kind="fixture",
            source_location="fixture",
        ),
        feature_row(
            game_id=3,
            feature="settings.sphere",
            known=False,
            source_kind="fixture",
            source_location="fixture",
        ),
        feature_row(
            game_id=3,
            feature="population.horwasp_present",
            value=False,
            known=True,
            source_kind="fixture",
            source_location="fixture",
        ),
    ]
    index = tmp_path / "game_features.parquet"
    write_feature_index(
        rows=rows,
        parquet_path=index,
        database_path=tmp_path / "corpus.duckdb",
    )

    scope = load_feature_scope(
        index,
        profile="combat-planar-no-horwasp",
    )

    assert scope.included_game_ids == (1,)
    assert scope.excluded_game_ids == (2, 3)
    assert scope.unknown_game_ids == (3,)
    assert scope.classify(1) == "selected"
    assert scope.classify(2) == "excluded"
    assert scope.classify(3) == "unknown"
    assert scope.classify(4) == "unindexed"
    assert scope.to_dict()["profile"] == "combat-planar-no-horwasp"
