"""Bounded, source-gated selection of truly consecutive public PPQ archive windows.

Archive filename adjacency is NOT the same as embedded game.turn adjacency.
The scanner reads only selected, approved perspective pairs and never
promotes mismatches to a comparable Host transition. It reports a bounded
failure histogram instead of raw .trn contents or exception messages.
"""
from __future__ import annotations

import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from planets_lab.corpus.pq_historical_readiness import report_from_paths
from planets_lab.corpus.pq_window_field_sufficiency import (
    _load_selected_members, scan_single_pq_window,
)

REPORT_SCHEMA = "planets-lab.pq-bounded-window-selection.v1"
TURN_NAME = re.compile(r"^player([0-9]+)-turn([0-9]+)\.trn$")
MAX_PAIRS = 64
MAX_ACCEPTED = 8


def _category(exc: Exception) -> str:
    # Never propagate an exception's untrusted raw values to uploaded evidence.
    if type(exc) is ValueError:
        message = str(exc)
        if message == "embedded turns are not consecutive":
            return "EMBEDDED_TURNS_NOT_CONSECUTIVE"
        if message == "embedded game identity mismatch":
            return "EMBEDDED_GAME_IDENTITY_MISMATCH"
        if message == "embedded player identity mismatch":
            return "EMBEDDED_PLAYER_IDENTITY_MISMATCH"
        if message == "embedded turn is not a nonnegative typed integer":
            return "MALFORMED_EMBEDDED_TURN"
        if message == "duplicate target member names are not attributable":
            return "DUPLICATE_TARGET_MEMBERS"
        if message == "requested consecutive members not available":
            return "MISSING_TARGET_MEMBER"
        if message == "unbounded archive member" or message == "selected member exceeds bounded decoded size":
            return "MEMBER_SIZE_LIMIT"
    return "UNREADABLE_OR_UNSUPPORTED_MEMBER"


def select_bounded_pq_windows(
    *, feature_index: Path, frozen_cohort: Path, archive_dir: Path,
    game_id: int, player_slot: int, first_archive_turn: int = 1,
    max_pairs: int = 48, max_accepted: int = 5,
) -> dict[str, Any]:
    if any(type(x) is not int for x in (
        game_id, player_slot, first_archive_turn, max_pairs, max_accepted
    )) or not (
        game_id > 0 and 1 <= player_slot <= 50
        and first_archive_turn >= 0 and 1 <= max_pairs <= MAX_PAIRS
        and 1 <= max_accepted <= MAX_ACCEPTED
    ):
        raise ValueError("invalid bounded selector arguments")

    # Enforce the frozen allowlist and index predicates BEFORE opening a ZIP.
    readiness = report_from_paths(feature_index, frozen_cohort)
    permitted = {
        item["game_id"]: item for item in readiness["games"]
        if item["observational_candidate"]
    }
    if game_id not in permitted:
        raise ValueError("game outside frozen approved PQ/PPQ archive candidate scope")

    archive_path = archive_dir / f"game-{game_id}.zip"
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.namelist()  # central directory only; no member data
    occurrences = Counter(members)
    present = set()
    for name in members:
        match = TURN_NAME.fullmatch(name)
        if match and int(match.group(1)) == player_slot:
            ordinal = int(match.group(2))
            if ordinal >= first_archive_turn:
                present.add(ordinal)
    pairs = sorted(
        i for i in present
        if i + 1 in present
    )[:max_pairs]

    failures: Counter[str] = Counter()
    qualified: list[dict[str, Any]] = []
    checked = 0
    for ordinal in pairs:
        checked += 1
        before_name = f"player{player_slot}-turn{ordinal}.trn"
        after_name = f"player{player_slot}-turn{ordinal+1}.trn"
        if occurrences[before_name] != 1 or occurrences[after_name] != 1:
            failures["DUPLICATE_TARGET_MEMBERS"] += 1
            continue
        try:
            report = scan_single_pq_window(
                feature_index=feature_index, frozen_cohort=frozen_cohort,
                archive_dir=archive_dir, game_id=game_id,
                player_id=player_slot, t_before=ordinal,
            )
        except (
            ValueError, TypeError, KeyError, OSError, EOFError, UnicodeError,
            OverflowError, zipfile.BadZipFile,
        ) as exc:
            category = _category(exc)
            if category == "EMBEDDED_TURNS_NOT_CONSECUTIVE":
                # Diagnostic only: game/player IDs must match, and this
                # never admits an invalid transition as mechanically usable.
                try:
                    _, _, before_embedded, after_embedded = _load_selected_members(
                        archive_path, game_id=game_id, player_id=player_slot,
                        t_before=ordinal, strict_consecutive=False,
                    )
                    delta = after_embedded - before_embedded
                    category = (
                        "EMBEDDED_TURN_REPEATED" if delta == 0 else
                        "EMBEDDED_TURN_BACKWARDS" if delta < 0 else
                        "EMBEDDED_TURN_SKIPPED_FORWARD"
                    )
                except (ValueError, OSError, KeyError, TypeError):
                    category = "UNREADABLE_OR_UNSUPPORTED_MEMBER"
            failures[category] += 1
            continue
        # The strict reader has already verified embedded delta == 1.
        if (
            report["after_embedded_turn"] != report["before_embedded_turn"] + 1
            or report["archive_members_read"] != 2
            or report["causal_queue_replay_admitted"] is not False
        ):
            raise ValueError("strict reader produced inconsistent observation")
        qualified.append(report)
        if len(qualified) >= max_accepted:
            break

    return {
        "schema": REPORT_SCHEMA,
        "game_id": game_id,
        "player_slot": player_slot,
        "queue_mode": permitted[game_id]["mode"],
        "cohort_sha256": readiness["cohort_sha256"],
        "index_sha256": readiness["index_sha256"],
        "first_archive_turn": first_archive_turn,
        "max_pairs": max_pairs,
        "max_accepted": max_accepted,
        "archive_name_adjacent_pairs_in_bounded_range": len(pairs),
        "actually_checked_pairs": checked,
        "admissible_consecutive_embedded_pairs": len(qualified),
        "refusal_counts": dict(sorted(failures.items())),
        "first_approved_archive_turn": (
            qualified[0]["before_archive_turn"] if qualified else None
        ),
        "admissible_window_reports": qualified,
        "coverage_is_bounded_not_exhaustive": True,
        "no_eligible_pair_in_checked_scope": not qualified,
        "host_accepted_orders_verified": False,
        "pp_warehouse_queue_parity_verified": False,
        "nuhost_execution_verified": False,
        "evidence": "BOUNDED_PUBLIC_ARCHIVAL_IDENTITY_AND_SHAPE_NOT_DIFF_VERIFIED",
        "raw_turn_payloads_emitted": False,
    }
