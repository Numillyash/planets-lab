"""Privacy-minimal, bounded archive window field-sufficiency check for PQ.

Only two predeclared members in ONE pre-approved game archive are read.
This is shape/coverage triage, NOT an attempt to replay Host, infer
queued bases, authenticate orders, or inspect any heldout entity records.
"""
from __future__ import annotations

import gzip
import io
import json
import zipfile
from pathlib import Path
from typing import Any
from collections.abc import Mapping

from planets_lab.corpus.pq_historical_readiness import report_from_paths

SCHEMA = "planets-lab.pq-two-member-field-sufficiency.v1"
MAX_MEMBER_BYTES = 24 * 1024 * 1024


def _int(raw: object, *, positive: bool = False) -> int:
    if type(raw) is not int or (positive and raw <= 0):
        raise ValueError("positive typed integer required")
    return raw


def _decode(raw: bytes) -> dict[str, Any]:
    if raw[:2] == b"\x1f\x8b":
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(MAX_MEMBER_BYTES + 1)
    if len(raw) > MAX_MEMBER_BYTES:
        raise ValueError("selected member exceeds bounded decoded size")
    parsed = json.loads(raw.decode("utf-8-sig"))
    if type(parsed) is not dict:
        raise ValueError("archive turn member is not an object")
    return parsed


def _owner_stats(parsed: Mapping[str, Any], perspective: int, turn: int) -> dict[str, Any]:
    groups = {}
    missing = []
    for kind in ("planets", "starbases", "ships"):
        rows = parsed.get(kind)
        if type(rows) is not list:
            missing.append(f"ABSTAIN_{kind.upper()}_ARRAY_MISSING")
            groups[kind] = {
                "visible_rows": None,
                "explicit_owner_fresh_rows": 0,
                "explicit_owner_without_infoturn_rows": 0,
                "unknown_or_stale_owner_rows": 0,
            }
            continue
        explicit = 0
        unverified_freshness = 0
        unknown = 0
        for row in rows:
            if type(row) is not dict:
                unknown += 1
                continue
            owner = row.get("ownerid")
            if owner is None:
                owner = row.get("owner_id")
            info_turn = row.get("infoturn")
            if type(owner) is int and owner == perspective:
                if info_turn is None:
                    unverified_freshness += 1
                elif type(info_turn) is int and info_turn == turn:
                    explicit += 1
                else:
                    unknown += 1
            elif type(owner) is not int or (
                info_turn is not None and (
                    type(info_turn) is not int or info_turn != turn
                )
            ):
                unknown += 1
        groups[kind] = {
            "visible_rows": len(rows),
            "explicit_owner_fresh_rows": explicit,
            "explicit_owner_without_infoturn_rows": unverified_freshness,
            "unknown_or_stale_owner_rows": unknown,
        }
    if not isinstance(parsed.get("player"), dict):
        missing.append("ABSTAIN_PLAYER_RECORD_MISSING")
    return {"groups": groups, "missing": missing}


def _load_selected_members(
    path: Path, *, game_id: int, player_id: int, t_before: int,
    strict_consecutive: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    if not path.is_file():
        raise ValueError("approved public archive missing")
    names = (
        f"player{player_id}-turn{t_before}.trn",
        f"player{player_id}-turn{t_before+1}.trn",
    )
    with zipfile.ZipFile(path) as archive:
        seen = set(archive.namelist())
        if any(n not in seen for n in names):
            raise ValueError("requested consecutive members not available")
        if any(archive.namelist().count(n) != 1 for n in names):
            raise ValueError("duplicate target member names are not attributable")
        decoded = []
        for name in names:
            info = archive.getinfo(name)
            if info.is_dir() or info.file_size > MAX_MEMBER_BYTES:
                raise ValueError("unbounded archive member")
            decoded.append(_decode(archive.read(info)))
    before, after = decoded
    embedded_turns: list[int] = []
    for item in (before, after):
        game = item.get("game")
        player = item.get("player")
        if (
            type(game) is not dict or type(player) is not dict
            or type(game.get("id")) is not int or game["id"] != game_id
        ):
            raise ValueError("embedded game identity mismatch")
        if type(player.get("id")) is not int or player["id"] != player_id:
            raise ValueError("embedded player identity mismatch")
        embedded_turn = game.get("turn")
        if type(embedded_turn) is not int or embedded_turn < 0:
            raise ValueError("embedded turn is not a nonnegative typed integer")
        embedded_turns.append(embedded_turn)

    # Corpus normalizer already distinguishes filename/archive turn from
    # embedded game.turn. Require a consistent offset AND a consecutive
    # embedded turn transition; neither turn naming convention is guessed.
    if strict_consecutive and embedded_turns[1] != embedded_turns[0] + 1:
        raise ValueError("embedded turns are not consecutive")
    return before, after, embedded_turns[0], embedded_turns[1]

def scan_single_pq_window(
    *, feature_index: Path, frozen_cohort: Path, archive_dir: Path,
    game_id: int, player_id: int, t_before: int,
) -> dict[str, Any]:
    game_id = _int(game_id, positive=True)
    player_id = _int(player_id, positive=True)
    t_before = _int(t_before, positive=True)
    if player_id > 50:
        raise ValueError("invalid bounded player slot")
    # Validate cohort AND index BEFORE attempting to touch a ZIP.
    selection = report_from_paths(feature_index, frozen_cohort)
    records = {g["game_id"]: g for g in selection["games"]}
    case = records.get(game_id)
    if case is None or not case["observational_candidate"]:
        raise ValueError("game not an approved archival PQ/PPQ observational candidate")
    file = archive_dir / f"game-{game_id}.zip"
    before, after, embedded_before, embedded_after = _load_selected_members(
        file, game_id=game_id, player_id=player_id, t_before=t_before,
    )
    # infoturn belongs to the embedded Game turn, not the archive
    # ordinal. A filename off-by-one is not evidence of a stale record.
    a = _owner_stats(before, player_id, embedded_before)
    b = _owner_stats(after, player_id, embedded_after)
    missing = sorted(set((*a["missing"], *b["missing"])))
    # Public perspective fields can show structure/ship changes, but no
    # independent server-accepted orders, causal phase placement, or
    # global completeness; never promote this shape inspection to parity.
    return {
        "schema": SCHEMA,
        "game_id": game_id,
        "player_slot": player_id,
        "before_archive_turn": t_before,
        "after_archive_turn": t_before + 1,
        "before_embedded_turn": embedded_before,
        "after_embedded_turn": embedded_after,
        "archive_to_embedded_turn_offset": embedded_before - t_before,
        "turn_identity_relation": (
            "EXACT" if embedded_before == t_before else "CONSISTENT_OFFSET"
        ),
        "queue_mode": case["mode"],
        "cohort_sha256": selection["cohort_sha256"],
        "index_sha256": selection["index_sha256"],
        "before": a["groups"],
        "after": b["groups"],
        "missing_or_invalid_arrays": missing,
        "observational_shape_available": not missing,
        "causal_queue_replay_admitted": False,
        "host_accepted_orders_verified": False,
        "owner_pp_ledger_independently_complete": False,
        "starbase_component_warehouses_independently_complete": False,
        "complete_global_fleet_and_base_roster_verified": False,
        "host_phase_boundary_independent": False,
        "evidence": "PUBLIC_ARCHIVE_TWO_MEMBER_SHAPE_ONLY_NOT_DIFF_VERIFIED",
        "archive_members_read": 2,
        "private_fields_emitted": False,
    }
