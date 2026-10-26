"""Strict count-only same-battle-turn VCR perspective consensus on frozen members.

Keys (game, turn, vcr ID), observer IDs and input signatures are ephemeral.
Never export any key, member ID, signature, seed, weapon stat or raw VCR.
Agreement measures archive replay-input consistency, not Host fidelity.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .combat_vcr_runtime import _minimal_records, _minimal_settings, _signature


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


@dataclass(frozen=True)
class _Observation:
    observer: int
    vcr_signature: str
    weapons_signature: str
    settings_signature: str
    full_signature: str
    catalog_ready: bool
    rng_ready: bool
    owners_ready: bool


class FrozenSameTurnVcrConsensus:
    """Count unique selected archive members, not duplicate pair appearances.

    Caller must pin the exact game/turn cohort BEFORE its first reconstruction
    and independently verify embedded identity of each source member.
    """
    def __init__(self) -> None:
        self._seen_members: set[int] = set()
        self._groups: dict[tuple[int, int, int], list[_Observation]] = defaultdict(list)
        self._counts: Counter[str] = Counter()

    def observe(self, *, member_id: int, game: int, turn: int,
                observer: int, payload: Mapping[str, Any]) -> None:
        if (not all(_positive(x) for x in (member_id, game, turn, observer))
                or not isinstance(payload, Mapping)):
            raise ValueError("ABSTAIN_INVALID_FROZEN_MEMBER_IDENTITY")
        if member_id in self._seen_members:
            return
        self._seen_members.add(member_id)
        self._counts["unique_frozen_archive_members_examined"] += 1
        raw = payload.get("vcrs")
        if type(raw) is not list:
            self._counts["ABSTAIN_MEMBER_VCR_LIST_MISSING_OR_UNTYPED"] += 1
            return
        self._counts["vcr_rows_in_unique_member_archives"] += len(raw)
        valid_ids = all(isinstance(row, Mapping) and _positive(row.get("id"))
                        for row in raw)
        if not valid_ids or len({row["id"] for row in raw}) != len(raw):
            self._counts["ABSTAIN_MEMBER_VCR_IDS_INVALID_OR_DUPLICATE"] += 1
            self._counts["vcr_rows_unqualified_atomic_member_abstain"] += len(raw)
            return
        self._counts["qualified_member_vcr_lists"] += 1
        beams_raw, torps_raw = payload.get("beams"), payload.get("torpedos")
        catalog_ready = (
            type(beams_raw) is list and type(torps_raw) is list
            and all(isinstance(v, Mapping) for v in beams_raw)
            and all(isinstance(v, Mapping) for v in torps_raw)
        )
        settings_raw = payload.get("settings")
        settings = _minimal_settings(settings_raw)
        rng_ready = isinstance(settings_raw, Mapping) and "combatrng" in settings
        # Do not rewrite the replay adapter's canonicalization: compare
        # EXACTLY its retained payload/weapon/settings representation.
        for row in raw:
            if (row.get("turn") != turn or type(row.get("turn")) is not int
                    or not isinstance(row.get("left"), Mapping)
                    or not isinstance(row.get("right"), Mapping)
                    or not _positive(row["left"].get("objectid"))
                    or not _positive(row["right"].get("objectid"))):
                self._counts["vcr_rows_unqualified_turn_or_participant"] += 1
                continue
            try:
                beams = _minimal_records(beams_raw if catalog_ready else [], ("id", "damage", "crewkill"))
                torpedoes = _minimal_records(
                    torps_raw if catalog_ready else [],
                    ("id", "damage", "crewkill", "combatrange"),
                )
                raw_sig = _signature(payload=row, beams=[], torpedoes=[], settings={})
                weapon_sig = _signature(payload={}, beams=beams, torpedoes=torpedoes, settings={})
                rng_sig = _signature(payload={}, beams=[], torpedoes=[], settings=settings)
                full_sig = _signature(payload=row, beams=beams, torpedoes=torpedoes, settings=settings)
            except (TypeError, ValueError, OverflowError):
                self._counts["vcr_rows_unqualified_unserializable_input"] += 1
                continue
            owners_ready = _positive(row.get("leftownerid")) and _positive(row.get("rightownerid"))
            self._counts["vcr_rows_qualified_same_turn_typed_participants"] += 1
            if not catalog_ready:
                self._counts["vcr_rows_missing_typed_weapon_catalog"] += 1
            if not rng_ready:
                self._counts["vcr_rows_missing_explicit_combat_rng"] += 1
            if not owners_ready:
                self._counts["vcr_rows_missing_typed_owner_pair"] += 1
            self._groups[(game, turn, row["id"])].append(
                _Observation(observer, raw_sig, weapon_sig, rng_sig,
                             full_sig, catalog_ready, rng_ready, owners_ready)
            )

    def result(self, *, qualified_archive_pairs: int) -> dict[str, int]:
        if type(qualified_archive_pairs) is not int or qualified_archive_pairs < 0:
            raise ValueError("ABSTAIN_FROZEN_PAIR_COUNT")
        c = self._counts.copy()
        c["qualified_original_frozen_adjacent_pairs"] = qualified_archive_pairs
        c["same_turn_observation_groups"] = len(self._groups)
        for records in self._groups.values():
            if len({r.observer for r in records}) != len(records):
                raise ValueError("ABSTAIN_DUPLICATE_SAME_PERSPECTIVE_BATTLE_KEY")
            c["source_observation_rows_in_qualified_groups"] += len(records)
            if len(records) == 1:
                c["single_perspective_groups"] += 1
                continue
            c["multi_perspective_groups"] += 1
            c["multi_perspective_observer_occurrences"] += len(records)
            if len(records) == 2:
                c["multi_perspective_groups_two_observers"] += 1
            else:
                c["multi_perspective_groups_three_or_more_observers"] += 1
            for attribute, label in (
                ("vcr_signature", "vcr_payload"),
                ("weapons_signature", "weapon_catalog"),
                ("settings_signature", "combat_rng_settings"),
                ("full_signature", "complete_adapter_signature"),
            ):
                agrees = len({getattr(r, attribute) for r in records}) == 1
                c["multi_perspective_" + label + ("_equal" if agrees else "_different")] += 1
            complete = all(r.catalog_ready and r.rng_ready and r.owners_ready for r in records)
            if not complete:
                c["multi_perspective_strict_inputs_incomplete"] += 1
            elif len({r.full_signature for r in records}) == 1:
                c["multi_perspective_strict_complete_inputs_equal"] += 1
            else:
                c["multi_perspective_strict_complete_inputs_different"] += 1
        seen = c["vcr_rows_in_unique_member_archives"]
        qual = c["vcr_rows_qualified_same_turn_typed_participants"]
        unqual = sum(c[k] for k in (
            "vcr_rows_unqualified_atomic_member_abstain",
            "vcr_rows_unqualified_turn_or_participant",
            "vcr_rows_unqualified_unserializable_input",
        ))
        members = c["unique_frozen_archive_members_examined"]
        member_categories = sum(c[k] for k in (
            "ABSTAIN_MEMBER_VCR_LIST_MISSING_OR_UNTYPED",
            "ABSTAIN_MEMBER_VCR_IDS_INVALID_OR_DUPLICATE",
            "qualified_member_vcr_lists",
        ))
        g = c["same_turn_observation_groups"]
        multi = c["multi_perspective_groups"]
        if not (
            seen == qual + unqual
            and members == member_categories
            and g == c["single_perspective_groups"] + multi
            and c["source_observation_rows_in_qualified_groups"] == qual
            and multi == (c["multi_perspective_groups_two_observers"]
                          + c["multi_perspective_groups_three_or_more_observers"])
            and multi == sum(c[k] for k in (
                "multi_perspective_strict_inputs_incomplete",
                "multi_perspective_strict_complete_inputs_equal",
                "multi_perspective_strict_complete_inputs_different",
            ))
            and all(multi == c[f"multi_perspective_{k}_equal"] +
                    c[f"multi_perspective_{k}_different"]
                    for k in ("vcr_payload", "weapon_catalog",
                              "combat_rng_settings", "complete_adapter_signature"))
        ):
            raise ValueError("ABSTAIN_VCR_CONSENSUS_COUNT_CONSERVATION")
        return {k: int(c[k]) for k in _FIELDS}


_FIELDS = (
    "qualified_original_frozen_adjacent_pairs",
    "unique_frozen_archive_members_examined",
    "qualified_member_vcr_lists",
    "ABSTAIN_MEMBER_VCR_LIST_MISSING_OR_UNTYPED",
    "ABSTAIN_MEMBER_VCR_IDS_INVALID_OR_DUPLICATE",
    "vcr_rows_in_unique_member_archives",
    "vcr_rows_unqualified_atomic_member_abstain",
    "vcr_rows_unqualified_turn_or_participant",
    "vcr_rows_unqualified_unserializable_input",
    "vcr_rows_qualified_same_turn_typed_participants",
    "vcr_rows_missing_typed_weapon_catalog",
    "vcr_rows_missing_explicit_combat_rng",
    "vcr_rows_missing_typed_owner_pair",
    "source_observation_rows_in_qualified_groups",
    "same_turn_observation_groups",
    "single_perspective_groups",
    "multi_perspective_groups",
    "multi_perspective_observer_occurrences",
    "multi_perspective_groups_two_observers",
    "multi_perspective_groups_three_or_more_observers",
    "multi_perspective_vcr_payload_equal",
    "multi_perspective_vcr_payload_different",
    "multi_perspective_weapon_catalog_equal",
    "multi_perspective_weapon_catalog_different",
    "multi_perspective_combat_rng_settings_equal",
    "multi_perspective_combat_rng_settings_different",
    "multi_perspective_complete_adapter_signature_equal",
    "multi_perspective_complete_adapter_signature_different",
    "multi_perspective_strict_inputs_incomplete",
    "multi_perspective_strict_complete_inputs_equal",
    "multi_perspective_strict_complete_inputs_different",
)
