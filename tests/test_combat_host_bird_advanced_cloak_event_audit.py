from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_bird_advanced_cloak_event_audit import (  # noqa: E402
    _active_advantage_projection,
    _mechanical_keywords,
    _message_matches_focus,
    _sanitize_event_mapping,
)


def test_mechanical_keywords_classify_mine_and_cloak_text() -> None:
    labels = _mechanical_keywords("Ship #68 hit a mine and was decloaked before combat.")
    assert "mine" in labels
    assert "cloak" in labels
    assert "combat" in labels


def test_message_matches_exact_target_without_text_heuristic() -> None:
    assert _message_matches_focus(
        {"target": 68, "headline": "Unrelated wording"},
        focus_ids={26, 68},
        focus_ship_ids={26, 68},
        focus_names=set(),
        site=(1984, 2266),
    ) is True


def test_message_matches_site_only_when_mechanical() -> None:
    assert _message_matches_focus(
        {"x": 1984, "y": 2266, "body": "Mine hit report"},
        focus_ids={26, 68},
        focus_ship_ids={26, 68},
        focus_names=set(),
        site=(1984, 2266),
    ) is True
    assert _message_matches_focus(
        {"x": 1984, "y": 2266, "body": "hello there"},
        focus_ids={26, 68},
        focus_ship_ids={26, 68},
        focus_names=set(),
        site=(1984, 2266),
    ) is False


def test_message_matches_focus_ship_name_with_mechanical_keyword() -> None:
    assert _message_matches_focus(
        {"body": "Resolute Alpha suffered damage while cloaked."},
        focus_ids={68},
        focus_ship_ids={68},
        focus_names={"Resolute Alpha"},
        site=(1984, 2266),
    ) is True


def test_active_advantage_projection_resolves_catalog_names() -> None:
    payload = {
        "advantages": [
            {"id": 10, "name": "Hidden Minefields"},
            {"id": 11, "name": "Loki Immunity"},
        ],
        "player": {"activeadvantages": [10, {"id": 11}]},
    }
    assert _active_advantage_projection(payload) == [
        {"id": 10, "name": "Hidden Minefields"},
        {"id": 11, "name": "Loki Immunity"},
    ]


def test_sanitize_event_mapping_suppresses_free_text() -> None:
    projected = _sanitize_event_mapping(
        {
            "shipid": 68,
            "eventtype": "minehit",
            "damage": 12,
            "body": "free form corpus text",
        }
    )
    assert projected["shipid"] == 68
    assert projected["eventtype"] == "minehit"
    assert projected["damage"] == 12
    assert "body" not in projected
    assert projected["suppressed_text_fields"] == ["body"]
