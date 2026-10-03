from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_o_layer_merge import merge_parts
from combat_public_capture_o_layer_probe import SCHEMA


def _part(game_id: int, *, left: int, right: int) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "scanned_game_ids": [1, 2],
        "probe_game_ids": [game_id],
        "summary": {
            "counts": {
                "discovery_ship_rows": left + right,
                "o_pair_reachable": left + right,
                "o_pair_reachable:left": left,
                "o_pair_reachable:right": right,
            }
        },
        "observations": [
            {
                "game_id": game_id,
                "turn": 10,
                "capture_vcr_id": game_id,
                "captured_ship_id": 100 + game_id,
            }
        ],
    }


def test_merge_parts_sums_counts_and_preserves_game_isolation() -> None:
    report = merge_parts([
        _part(1, left=2, right=1),
        _part(2, left=3, right=4),
    ])
    counts = report["summary"]["counts"]
    assert report["summary"]["game_passes"] == 2
    assert counts["discovery_ship_rows"] == 10
    assert counts["o_pair_reachable"] == 10
    assert counts["o_pair_reachable:left"] == 5
    assert counts["o_pair_reachable:right"] == 5
    assert report["scanned_game_ids"] == [1, 2]
    assert [row["probe_game_ids"] for row in report["summary"]["per_game"]] == [[1], [2]]



def test_merge_preserves_single_corpus_db_generation() -> None:
    first = _part(1, left=1, right=0)
    second = _part(2, left=0, right=1)
    for part in (first, second):
        part["backend"] = "corpus-db"
        part["database_schema"] = "planets-lab.corpus-db.v2.compact1"
        part["database_path"] = "/corpus-db/generations/current.duckdb"

    report = merge_parts([first, second])

    assert report["backend"] == "corpus-db"
    assert report["database_schema"] == "planets-lab.corpus-db.v2.compact1"
    assert report["database_path"] == "/corpus-db/generations/current.duckdb"
    assert {
        row["backend"] for row in report["summary"]["per_game"]
    } == {"corpus-db"}


def test_merge_rejects_mixed_corpus_db_generations() -> None:
    first = _part(1, left=1, right=0)
    second = _part(2, left=0, right=1)
    for part in (first, second):
        part["backend"] = "corpus-db"
        part["database_schema"] = "planets-lab.corpus-db.v2.compact1"
    first["database_path"] = "/corpus-db/generations/a.duckdb"
    second["database_path"] = "/corpus-db/generations/b.duckdb"

    with pytest.raises(ValueError, match="mixed Corpus DB generations"):
        merge_parts([first, second])
