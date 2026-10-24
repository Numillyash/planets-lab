"""Fail-closed *archive-source* identity coverage of paired nonplanet lists.

A T-1/T archive pair is NOT a NuHost order, movement, mine sweep, battle,
or even one specific Host phase. Each count reflects only the game's
observer-relative source records. Never export entity IDs, source records,
owner IDs, coordinates, ship loadouts or member identifiers.

Require *every* list row to have a unique positive strict-int 'id'
before comparing row identities. Any malformed/duplicate ID invalidates
the whole section pair; never partially match the remaining entries.
Cross-snapshot current-own observations require *both* matching ownerid
and exact infoturn separately; mere ID stability is not freshness.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SECTIONS = ("minefields", "ships", "starbases", "vcrs", "ionstorms")


def _ids(rows: list[Any]) -> dict[int, Mapping[str, Any]] | None:
    found: dict[int, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            return None
        key = row.get("id")
        if type(key) is not int or key <= 0 or key in found:
            return None
        found[key] = row
    return found


def _fresh_own(row: Mapping[str, Any], *, observer: int, turn: int) -> bool:
    return (
        type(observer) is int and observer > 0
        and type(turn) is int and turn > 0
        and type(row.get("ownerid")) is int
        and row["ownerid"] == observer
        and type(row.get("infoturn")) is int
        and row["infoturn"] == turn
    )


def profile_source_identity_pairs(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *, observer: int, before_turn: int, after_turn: int,
) -> dict[str, dict[str, int]]:
    """Only aggregate integer counts, no raw source identities.

    Consistent row IDs from successive observer archives are not evidence
    of actual Host events or even necessarily current information.
    """
    results: dict[str, dict[str, int]] = {}
    for section in SECTIONS:
        lhs = before.get(section)
        rhs = after.get(section)
        count: dict[str, int] = {}
        if type(lhs) is not list or type(rhs) is not list:
            count["ABSTAIN_MISSING_SECTION_LIST"] = 1
            results[section] = count
            continue
        b = _ids(lhs)
        a = _ids(rhs)
        if b is None or a is None:
            count["ABSTAIN_MALFORMED_OR_DUPLICATE_ENTITY_ID"] = 1
            results[section] = count
            continue
        count["qualified_identity_list_pair"] = 1
        count["before_id_rows"] = len(b)
        count["after_id_rows"] = len(a)
        shared = b.keys() & a.keys()
        count["same_id_seen_in_both_archives"] = len(shared)
        count["id_only_before_archive_not_host_destruction"] = len(b) - len(shared)
        count["id_only_after_archive_not_host_construction"] = len(a) - len(shared)
        count["empty_lists_both"] = int(not b and not a)

        same_owner = 0
        changed_owner = 0
        owner_abstain = 0
        current_own = 0
        current_own_missing_freshness = 0
        numeric_mine_units_comparable = 0
        numeric_mine_units_changed = 0
        same_owner_and_center_stable_units_changed = 0
        for identity in shared:
            one, two = b[identity], a[identity]
            owner_b, owner_a = one.get("ownerid"), two.get("ownerid")
            if type(owner_b) is int and owner_b > 0 and type(owner_a) is int and owner_a > 0:
                if owner_b == owner_a:
                    same_owner += 1
                else:
                    changed_owner += 1
            else:
                owner_abstain += 1

            if type(owner_b) is int and owner_b == observer and type(owner_a) is int and owner_a == observer:
                if (_fresh_own(one, observer=observer, turn=before_turn)
                        and _fresh_own(two, observer=observer, turn=after_turn)):
                    current_own += 1
                else:
                    current_own_missing_freshness += 1

            if section == "minefields":
                units_b, units_a = one.get("units"), two.get("units")
                if (type(units_b) is int and units_b >= 0
                        and type(units_a) is int and units_a >= 0):
                    numeric_mine_units_comparable += 1
                    if units_b != units_a:
                        numeric_mine_units_changed += 1
                        # Pure observation: this cannot isolate decay,
                        # beam/fighter sweep, MSC, overlap or hit damage.
                        if (type(owner_b) is int and owner_b > 0
                                and owner_b == owner_a
                                and all(type(one.get(k)) is int and type(two.get(k)) is int
                                        and one[k] == two[k] for k in ("x", "y"))):
                            same_owner_and_center_stable_units_changed += 1
        count["same_id_owner_unchanged"] = same_owner
        count["same_id_owner_changed_not_host_capture"] = changed_owner
        count["same_id_owner_untyped_abstain"] = owner_abstain
        count["same_id_current_own_verified_both_archives"] = current_own
        count["same_id_owner_own_but_infoturn_missing_or_stale"] = current_own_missing_freshness
        if section == "minefields":
            count["same_id_nonnegative_integer_units_both"] = numeric_mine_units_comparable
            count["same_id_integer_units_changed_not_host_attribution"] = numeric_mine_units_changed
            count["same_id_owner_center_stable_units_changed_not_causal"] = (
                same_owner_and_center_stable_units_changed
            )

        if (count["same_id_seen_in_both_archives"]
                + count["id_only_before_archive_not_host_destruction"] != count["before_id_rows"]
                or count["same_id_seen_in_both_archives"]
                + count["id_only_after_archive_not_host_construction"] != count["after_id_rows"]
                or same_owner + changed_owner + owner_abstain != len(shared)
                or numeric_mine_units_changed > numeric_mine_units_comparable):
            raise ValueError("NONPLANET_SOURCE_IDENTITY_INVARIANT_FAILURE")
        results[section] = count
    return results
