from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_ship_chain_audit.py"
spec = importlib.util.spec_from_file_location("combat_ship_chain_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def _previous(*, race_id: int, terminal: dict[str, object]) -> dict[str, object]:
    return {
        "race_id": race_id,
        "terminal": terminal,
    }


def _current(start: dict[str, object]) -> dict[str, object]:
    return {"start": start}


def test_non_race1_exact_carry_matches() -> None:
    result = audit._transition_comparison(
        _previous(
            race_id=3,
            terminal={
                "shield": 61,
                "damage": 12,
                "crew": 100,
                "torpedoes": 4,
                "fighters": 8,
                "destroyed": False,
                "captured": False,
            },
        ),
        _current(
            {
                "shield": 61,
                "damage": 12,
                "crew": 100,
                "torpedos": 4,
                "fighters": 8,
            }
        ),
    )
    assert result["status"] == "match"
    assert result["carry_mismatches"] == []
    assert result["shield"]["model"] == "exact_carry"


def test_race1_federation_candidate_is_reported_without_forcing_advantage() -> None:
    result = audit._transition_comparison(
        _previous(
            race_id=1,
            terminal={
                "shield": 60,
                "damage": 10,
                "crew": 100,
                "torpedoes": 4,
                "fighters": 8,
                "destroyed": False,
                "captured": False,
            },
        ),
        _current(
            {
                "shield": 70,
                "damage": 10,
                "crew": 100,
                "torpedos": 4,
                "fighters": 8,
            }
        ),
    )
    assert result["status"] == "match"
    assert result["shield"]["model"] == "federation_candidate"
    assert result["shield"]["race1_candidate"] is True


def test_carry_mismatch_is_not_hidden_by_matching_shield() -> None:
    result = audit._transition_comparison(
        _previous(
            race_id=4,
            terminal={
                "shield": 42,
                "damage": 20,
                "crew": 200,
                "torpedoes": 3,
                "fighters": 0,
                "destroyed": False,
                "captured": False,
            },
        ),
        _current(
            {
                "shield": 42,
                "damage": 20,
                "crew": 190,
                "torpedos": 3,
                "fighters": 0,
            }
        ),
    )
    assert result["status"] == "mismatch"
    assert result["carry_mismatches"] == ["crew"]


def test_reappearance_after_replay_defeat_is_separate_status() -> None:
    result = audit._transition_comparison(
        _previous(
            race_id=7,
            terminal={"destroyed": True, "captured": False},
        ),
        _current({"shield": 100}),
    )
    assert result["status"] == "reappearance_after_defeat"


def test_federation_candidate_formula_uses_production_sequence_rule() -> None:
    assert audit._federation_candidate_shield(
        terminal_shield=60,
        terminal_damage=10,
    ) == 70
    assert audit._federation_candidate_shield(
        terminal_shield=95,
        terminal_damage=20,
    ) == 80



def test_loadall_member_is_top_level_rst(tmp_path) -> None:
    import argparse
    import json
    import zipfile

    archive = tmp_path / "game-123.zip"

    # Real loadall shape: the .trn JSON itself is the RST payload.
    # There is no additional {"rst": ...} wrapper.
    rst = {
        "game": {"id": 123, "turn": 8},
        "settings": {"combatrng": 0},
        "beams": [],
        "torpedos": [],
        "vcrs": [
            {
                "id": 77,
                "turn": 8,
            }
        ],
    }

    with zipfile.ZipFile(
        archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zf:
        zf.writestr(
            "player1-turn8.trn",
            json.dumps(rst).encode("utf-8"),
        )

    args = argparse.Namespace(
        archive_dir=tmp_path,
        archive=[],
        output=None,
        detail_limit=10,
        sample_limit=2,
    )

    report = audit.run(args)

    assert report["summary"]["raw_vcr_observations"] == 1
    assert report["summary"]["unique_vcrs"] == 1

    # Extraction succeeds; deliberately incomplete VCR then fails closed
    # during replay rather than disappearing at archive-ingestion time.
    assert report["summary"]["replay_unsupported"] == 1

    assert report["archives"][0]["game_ids"] == [123]
    assert report["archives"][0]["vcr_observations"] == 1
