"""M2: read-only, fail-closed public-corpus planetary evidence COVERAGE audit.

This is NOT a mass proof of NuHost phases or construction orders.
First census ALL perspective/member metadata (bounded: 224014 for public100),
then metadata-freeze evenly spread adjacent same-perspective T-1/T pairs,
THEN reconstruct a bounded sample to measure owner-current availability.

Crucially, .trn archive states are not pre-Host submitted orders. In
particular, an arbitrary two-turn resource difference is not a client
BuildHull or Transfer event. The output is aggregate coverage only:
no player names, game IDs, raw private orders, or raw state records.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

SCHEMA = "planets-lab.m2-public-corpus-economy-coverage.v1"
FIELDS = {
    "credits_and_supplies": ("megacredits", "supplies"),
    "minerals_surface": ("neutronium", "duranium", "tritanium", "molybdenum"),
    "minerals_ground": ("groundneutronium", "groundduranium",
                        "groundtritanium", "groundmolybdenum"),
    "colonists_and_natives": ("clans", "nativeclans"),
    "structures": ("mines", "factories", "defense"),
    "tax_inputs": ("colonisttaxrate", "nativehappypoints", "nativetaxrate"),
}
MAX_META_ROWS = 1_000_000
MAX_GAMES = 1000
MAX_PAIRS_PER_GAME = 16
MAX_SELECTED_PAIRS = 1600


@dataclass(frozen=True, slots=True)
class Member:
    member_id: int
    game: int
    player: int
    archive_turn: int
    embedded_turn: int


@dataclass(frozen=True, slots=True)
class Pair:
    game: int
    player: int
    after_turn: int
    before_id: int
    after_id: int


def _positive_integer(value: Any) -> int | None:
    return value if type(value) is int and value > 0 else None


def census_members(
    members: list[Member], *, max_games: int, pairs_per_game: int,
) -> tuple[dict[str, Any], list[Pair]]:
    """Make the complete metadata census BEFORE reading any entity contents."""
    if not 1 <= max_games <= MAX_GAMES:
        raise ValueError("max_games out of bounds")
    if not 1 <= pairs_per_game <= MAX_PAIRS_PER_GAME:
        raise ValueError("pairs_per_game out of bounds")
    if len(members) > MAX_META_ROWS:
        raise ValueError("metadata source exceeds safety cap")
    game_ids = {m.game for m in members}
    if any(_positive_integer(g) is None for g in game_ids):
        raise ValueError("game ID must be a positive integer")
    good: dict[tuple[int, int, int], Member] = {}
    duplicates = set()
    bad_metadata = 0
    for m in members:
        if (any(_positive_integer(x) is None
                for x in (m.member_id, m.game, m.player)) or
                type(m.archive_turn) is not int or m.archive_turn < 1 or
                type(m.embedded_turn) is not int or m.embedded_turn < 1 or
                m.archive_turn != m.embedded_turn):
            bad_metadata += 1
            continue
        key = m.game, m.player, m.archive_turn
        if key in good:
            duplicates.add(key)
        else:
            good[key] = m
    for key in duplicates:
        del good[key]

    pairs_by_game: dict[int, list[Pair]] = defaultdict(list)
    for (game, player, turn), current in good.items():
        prev = good.get((game, player, turn - 1))
        if prev is not None and turn >= 2:
            pairs_by_game[game].append(Pair(
                game, player, turn, prev.member_id, current.member_id
            ))

    # Select game coverage first; avoid "first 20 games" bias by
    # spreading deterministically across ALL corpus game identifiers.
    ordered_games = sorted(pairs_by_game)
    game_n = min(len(ordered_games), max_games)
    game_positions = _spread(len(ordered_games), game_n)
    selected: list[Pair] = []
    for game_index in game_positions:
        game = ordered_games[game_index]
        candidates = sorted(pairs_by_game[game], key=lambda p: (
            p.after_turn, p.player,
        ))
        # Select different turns where possible, not every player on
        # just one heavily observed turn.
        by_turn: dict[int, list[Pair]] = defaultdict(list)
        for pair in candidates:
            by_turn[pair.after_turn].append(pair)
        turns = sorted(by_turn)
        take = min(len(turns), pairs_per_game)
        for number, position in enumerate(_spread(len(turns), take)):
            chosen = sorted(by_turn[turns[position]], key=lambda p: p.player)
            selected.append(chosen[number % len(chosen)])

    if len(selected) > MAX_SELECTED_PAIRS:
        raise ValueError("selected corpus sample exceeds read budget")
    serial = [[p.game, p.player, p.after_turn, p.before_id, p.after_id]
              for p in selected]
    fingerprint = sha256(json.dumps(serial, separators=(",", ":")).encode()).hexdigest()
    result = {
        "all_games_in_source_metadata": len(game_ids),
        "all_source_perspective_members": len(members),
        "identity_valid_members": len(good),
        "metadata_invalid_or_embedded_turn_mismatch": bad_metadata,
        "ambiguous_duplicate_perspective_turn_keys": len(duplicates),
        "potential_adjacent_same_perspective_pairs": sum(
            map(len, pairs_by_game.values())
        ),
        "games_with_adjacent_perspective_pairs": len(pairs_by_game),
        "metadata_selected_game_count": len(set(p.game for p in selected)),
        "metadata_frozen_sample_pairs": len(selected),
        "metadata_frozen_selection_sha256": fingerprint,
        "selection_frozen_before_entity_reconstruction": True,
    }
    return result, selected


def _spread(length: int, take: int) -> list[int]:
    if take == 0:
        return []
    if take == 1:
        return [length // 2]
    return [(i * (length - 1)) // (take - 1) for i in range(take)]


def _owned_current_planets(
    payload: Mapping[str, Any], *, player: int, turn: int,
) -> tuple[dict[int, Mapping[str, Any]], Counter[str]]:
    result: dict[int, Mapping[str, Any]] = {}
    status: Counter[str] = Counter()
    raw_planets = payload.get("planets")
    if not isinstance(raw_planets, list):
        status["ABSTAIN_PLANET_ARRAY_MISSING"] += 1
        return result, status
    duplicated: set[int] = set()
    for planet in raw_planets:
        if not isinstance(planet, Mapping):
            status["ABSTAIN_NON_OBJECT_PLANET"] += 1
            continue
        pid = _positive_integer(planet.get("id"))
        owner = _positive_integer(planet.get("ownerid"))
        if pid is None:
            status["ABSTAIN_NO_PLANET_ID"] += 1
            continue
        if owner != player:
            continue
        info_turn = planet.get("infoturn")
        if type(info_turn) is not int or info_turn != turn:
            status["ABSTAIN_OWNER_PLANET_STALE_OR_NO_INFOTURN"] += 1
            continue
        if pid in result:
            duplicated.add(pid)
        else:
            result[pid] = planet
    for pid in duplicated:
        del result[pid]
    status["ABSTAIN_DUPLICATED_OWNER_PLANET_ID"] += len(duplicated)
    status["OWNER_CURRENT_PLANET_RECORDS"] += len(result)
    return result, status


def _valid_payload_identity(payload: Any, member: Member) -> bool:
    if not isinstance(payload, Mapping):
        return False
    game = payload.get("game")
    player = payload.get("player")
    return (
        isinstance(game, Mapping)
        and game.get("id") == member.game
        and game.get("turn") == member.archive_turn
        and isinstance(player, Mapping)
        and player.get("id") == member.player
    )


def profile_pair(
    before: Mapping[str, Any], after: Mapping[str, Any], pair: Pair,
) -> dict[str, Any]:
    """Only observational coverage; no inferred moves/build executions."""
    owned_before, b_status = _owned_current_planets(
        before, player=pair.player, turn=pair.after_turn - 1,
    )
    owned_after, a_status = _owned_current_planets(
        after, player=pair.player, turn=pair.after_turn,
    )
    joint = sorted(set(owned_before) & set(owned_after))
    comparable = Counter()
    differences = Counter()
    for planet_id in joint:
        b, a = owned_before[planet_id], owned_after[planet_id]
        for family, fields in FIELDS.items():
            pairs = [(b.get(field), a.get(field)) for field in fields]
            if not all(type(x) is int and x >= 0 for ab in pairs for x in ab):
                continue
            comparable[family] += 1
            if any(x != y for x, y in pairs):
                differences[family] += 1

    sections = ("ships", "planets", "starbases")
    section_rows = {}
    for section in sections:
        one = before.get(section)
        two = after.get(section)
        section_rows[section] = {
            "before": len(one) if isinstance(one, list) else None,
            "after": len(two) if isinstance(two, list) else None,
        }
    return {
        "owner_current_planets_before": len(owned_before),
        "owner_current_planets_after": len(owned_after),
        "same_owner_planet_id_pairs": len(joint),
        "qualified_field_families": comparable,
        "changed_net_stock_family_rows_not_phase_attribution": differences,
        "source_statuses": b_status + a_status,
        "section_counts": section_rows,
    }


def read_metadata(connection: Any) -> list[Member]:
    """Stream 5 small columns, not the 541M typed entity rows."""
    cursor = connection.execute("""
        SELECT member_id, game_id, perspective_player_id,
               archive_turn, embedded_turn
        FROM source_members
        ORDER BY game_id, archive_turn, perspective_player_id, member_id
    """)
    members: list[Member] = []
    while chunk := cursor.fetchmany(10000):
        for row in chunk:
            if len(members) >= MAX_META_ROWS:
                raise ValueError("metadata source exceeds safety cap")
            members.append(Member(*[int(x) for x in row]))
    return members


def analyze_corpus_coverage(
    connection: Any,
    *,
    max_games: int = 100,
    pairs_per_game: int = 2,
    reconstruct: Callable[[int], Mapping[str, Any]],
) -> dict[str, Any]:
    members = read_metadata(connection)
    metadata, selected = census_members(
        members, max_games=max_games, pairs_per_game=pairs_per_game,
    )
    by_id = {m.member_id: m for m in members}
    counters: Counter[str] = Counter()
    status: Counter[str] = Counter()
    fields: Counter[str] = Counter()
    changed: Counter[str] = Counter()
    section_counts: Counter[str] = Counter()
    for pair in selected:
        before_member, after_member = by_id[pair.before_id], by_id[pair.after_id]
        b, a = reconstruct(pair.before_id), reconstruct(pair.after_id)
        if not (_valid_payload_identity(b, before_member) and
                _valid_payload_identity(a, after_member)):
            status["ABSTAIN_PAYLOAD_IDENTITY_INVALID"] += 1
            continue
        status["SAMPLED_PAIR_PAYLOAD_IDENTITY_VALID"] += 1
        item = profile_pair(b, a, pair)
        for key in (
            "owner_current_planets_before", "owner_current_planets_after",
            "same_owner_planet_id_pairs",
        ):
            counters[key] += item[key]
        status.update(item["source_statuses"])
        fields.update(item["qualified_field_families"])
        changed.update(item["changed_net_stock_family_rows_not_phase_attribution"])
        for name, obj in item["section_counts"].items():
            for point, value in obj.items():
                if value is not None:
                    section_counts[f"{name}_{point}_rows"] += value
                else:
                    status[f"ABSTAIN_SECTION_MISSING_{name}_{point}"] += 1

    return {
        "schema": SCHEMA,
        "status": "CORPUS_METADATA_CENSUS_AND_BOUNDED_OWNER_CURRENT_SAMPLE_NOT_HOST_CAUSAL",
        "metadata": metadata,
        "sample": {
            "sample_status_counts": dict(sorted(status.items())),
            "owner_current_counts": dict(sorted(counters.items())),
            "qualified_planet_field_family_pairs": dict(sorted(fields.items())),
            "net_state_differences_not_mechanics": dict(sorted(changed.items())),
            "section_rows_across_sampled_perspectives":
                dict(sorted(section_counts.items())),
        },
        "evidence_limits": {
            "raw_trn_is_submitted_turn_orders": False,
            "T_minus_1_to_T_stock_change_identifies_action": False,
            "NuHost_economic_formula_verified": False,
            "NuHost_ship_build_cost_verified": False,
            "is_independent_game_disjoint_host_validation": False,
            "may_be_used_to_plan_fresh_independent_subcohorts": True,
        },
    }
