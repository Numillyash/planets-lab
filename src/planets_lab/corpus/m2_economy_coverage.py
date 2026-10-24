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

from planets_lab.corpus.m2_mineral_balance import profile_archive_mineral_mass_balance
from planets_lab.corpus.m2_surface_residual_context import (
    CATEGORIES as RESIDUAL_CLASSES, profile_surface_residual_context,
)

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
MAX_PAIRS_PER_GAME = 128
MAX_SELECTED_PAIRS = 16384
NUMERIC_FIELDS = tuple(dict.fromkeys(
    field for family in FIELDS.values() for field in family
))
MINERAL_NAMES = ("neutronium", "duranium", "tritanium", "molybdenum")
STABILITY_CONTROL_FIELDS = (
    "mines", "factories", "defense", "colonisttaxrate", "nativetaxrate",
)


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
    allowed_games: set[int] | None = None,
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
    ordered_games = sorted(
        game for game in pairs_by_game
        if allowed_games is None or game in allowed_games
    )
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
        "games_allowed_for_entity_sampling": len(ordered_games),
        "games_excluded_from_entity_sampling": (
            len(pairs_by_game) - len(ordered_games)
        ),
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


def _numeric_field_directions(
    owned_before: Mapping[int, Mapping[str, Any]],
    owned_after: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    """Descriptive stock-flow directions, never attributed Host mechanics.

    Count each numeric source field on an independently qualified
    same-owner owner-current planet pair. A family's availability does
    not imply that any particular single field changed. Net mining
    patterns may reflect shipments and spending as well as extraction.
    """
    per_field: dict[str, Counter[str]] = defaultdict(Counter)
    mineral_patterns: dict[str, Counter[str]] = defaultdict(Counter)
    controls: Counter[str] = Counter()
    for planet_id in sorted(set(owned_before) & set(owned_after)):
        b, a = owned_before[planet_id], owned_after[planet_id]
        for name in NUMERIC_FIELDS:
            before, after = b.get(name), a.get(name)
            if not (type(before) is int and before >= 0 and
                    type(after) is int and after >= 0):
                continue
            per_field[name]["qualified"] += 1
            if after > before:
                per_field[name]["increased"] += 1
            elif after < before:
                per_field[name]["decreased"] += 1
            else:
                per_field[name]["unchanged"] += 1

        control_pairs = [(b.get(field), a.get(field))
                         for field in STABILITY_CONTROL_FIELDS]
        if all(type(x) is int and x >= 0
               for pair in control_pairs for x in pair):
            controls["qualified"] += 1
            if all(x == y for x, y in control_pairs):
                controls["all_unchanged"] += 1
            else:
                controls["some_changed"] += 1

        for mineral in MINERAL_NAMES:
            surface_b, surface_a = b.get(mineral), a.get(mineral)
            ground_b, ground_a = b.get("ground" + mineral), a.get("ground" + mineral)
            if not all(type(x) is int and x >= 0
                       for x in (surface_b, surface_a, ground_b, ground_a)):
                continue
            bucket = mineral_patterns[mineral]
            bucket["qualified"] += 1
            ground_sign = (
                "ground_decreased" if ground_a < ground_b else
                "ground_increased" if ground_a > ground_b else "ground_unchanged"
            )
            surface_sign = (
                "surface_increased" if surface_a > surface_b else
                "surface_decreased" if surface_a < surface_b else "surface_unchanged"
            )
            bucket[f"{ground_sign}__{surface_sign}"] += 1
            # This subset can help shortlist mining hypotheses but
            # it is NOT evidence that mining caused the surface gain.
            if (ground_a < ground_b and surface_a > surface_b
                    and b.get("mines") == a.get("mines")
                    and type(b.get("mines")) is int and b["mines"] >= 0):
                bucket["ground_down_surface_up_mines_unchanged"] += 1

    return {
        "per_field": {
            name: dict(sorted(items.items()))
            for name, items in sorted(per_field.items())
        },
        "surface_ground_joint_signs_not_mining_attribution": {
            name: dict(sorted(items.items()))
            for name, items in sorted(mineral_patterns.items())
        },
        "observable_structure_and_tax_controls": dict(sorted(controls.items())),
    }


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
        "numeric_directional_coverage": _numeric_field_directions(
            owned_before, owned_after,
        ),
        "conditional_mineral_mass_balance": profile_archive_mineral_mass_balance(
            before, after, owned_before, owned_after,
        ),
        "surface_residual_context": profile_surface_residual_context(
            before, after, owned_before, owned_after, player=pair.player,
        ),
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
    allowed_games: set[int] | None = None,
) -> dict[str, Any]:
    members = read_metadata(connection)
    metadata, selected = census_members(
        members, max_games=max_games, pairs_per_game=pairs_per_game,
        allowed_games=allowed_games,
    )
    by_id = {m.member_id: m for m in members}
    counters: Counter[str] = Counter()
    status: Counter[str] = Counter()
    fields: Counter[str] = Counter()
    changed: Counter[str] = Counter()
    section_counts: Counter[str] = Counter()
    per_field: dict[str, Counter[str]] = defaultdict(Counter)
    mineral_joint: dict[str, Counter[str]] = defaultdict(Counter)
    controls: Counter[str] = Counter()
    mineral_model: dict[str, Counter[str]] = defaultdict(Counter)
    mineral_surface_increase: dict[str, Counter[str]] = defaultdict(Counter)
    mineral_abs_residual: dict[str, Counter[str]] = defaultdict(Counter)
    residual_categories: dict[str, Counter[str]] = defaultdict(Counter)
    residual_covariates: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    residual_bins: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    supporting: dict[str, Counter[str]] = defaultdict(Counter)
    residual_quality: Counter[str] = Counter()
    per_game_residual: dict[int, Counter[str]] = defaultdict(Counter)
    per_game_surface_context: dict[int, Counter[str]] = defaultdict(Counter)
    joint_surface_cargo_base: dict[str, Counter[str]] = defaultdict(Counter)
    planet_residual_events: Counter[str] = Counter()
    per_game_planet_events: dict[int, Counter[str]] = defaultdict(Counter)
    for pair in selected:
        before_member, after_member = by_id[pair.before_id], by_id[pair.after_id]
        b, a = reconstruct(pair.before_id), reconstruct(pair.after_id)
        if not (_valid_payload_identity(b, before_member) and
                _valid_payload_identity(a, after_member)):
            status["ABSTAIN_PAYLOAD_IDENTITY_INVALID"] += 1
            continue
        status["SAMPLED_PAIR_PAYLOAD_IDENTITY_VALID"] += 1
        # Archive-time section availability only. Content may be stale,
        # incomplete or perspective-dependent; never a Host phase proof.
        for section in ("minefields", "ships", "starbases", "vcrs", "ionstorms"):
            before_rows = b.get(section)
            after_rows = a.get(section)
            bucket = supporting[section]
            if type(before_rows) is not list or type(after_rows) is not list:
                bucket["ABSTAIN_SECTION_MISSING_OR_UNTYPED"] += 1
                continue
            bucket["pair_has_both_lists"] += 1
            bucket["before_rows_observed"] += len(before_rows)
            bucket["after_rows_observed"] += len(after_rows)
            if before_rows and after_rows:
                bucket["pair_has_nonempty_both"] += 1
            if len(before_rows) != len(after_rows):
                bucket["pair_row_count_differs_not_host_attribution"] += 1

        # Retain a game even if none of its qualified owner-current
        # planets supports the conditional mineral model.
        # It must contribute a ZERO to every game-cluster histogram,
        # not disappear and bias the residual clustering upward.
        per_game_residual[pair.game]
        per_game_surface_context[pair.game]
        per_game_planet_events[pair.game]
        item = profile_pair(b, a, pair)
        for key in (
            "owner_current_planets_before", "owner_current_planets_after",
            "same_owner_planet_id_pairs",
        ):
            counters[key] += item[key]
        status.update(item["source_statuses"])
        fields.update(item["qualified_field_families"])
        changed.update(item["changed_net_stock_family_rows_not_phase_attribution"])
        directional = item["numeric_directional_coverage"]
        for name, indicators in directional["per_field"].items():
            per_field[name].update(indicators)
        for name, indicators in directional[
            "surface_ground_joint_signs_not_mining_attribution"
        ].items():
            mineral_joint[name].update(indicators)
        controls.update(directional["observable_structure_and_tax_controls"])
        model = item["conditional_mineral_mass_balance"]
        for name, indicators in model["per_mineral"].items():
            mineral_model[name].update(indicators)
        for name, indicators in model[
            "surface_up_ground_equal_surface_increase_buckets"
        ].items():
            mineral_surface_increase[name].update(indicators)
        for name, indicators in model[
            "net_total_minus_default_mutation_abs_residual_buckets"
        ].items():
            mineral_abs_residual[name].update(indicators)
        context = item["surface_residual_context"]
        residual_quality.update(context["source_quality"])
        for mineral, counts in context[
            "per_mineral_surface_residual_joint_cargo_base"
        ].items():
            joint_surface_cargo_base[mineral].update(counts)
        planet_residual_events.update(
            context["planet_transition_residual_events_not_independent_actions"]
        )
        per_game_planet_events[pair.game].update(
            context["planet_transition_residual_events_not_independent_actions"]
        )
        for mineral, class_counts in context["per_mineral_categories"].items():
            residual_categories[mineral].update(class_counts)
            for residual_class, count in class_counts.items():
                per_game_residual[pair.game][residual_class] += count
        for mineral, groups in context["per_mineral_category_covariates"].items():
            for residual_class, values in groups.items():
                residual_covariates[mineral][residual_class].update(values)
                if residual_class == "ground_exact_surface_residual":
                    for metric in (
                        "owner_ship_observed_at_site_both",
                        "one_ship_opposite_cargo_delta_candidate",
                        "multiple_ship_cargo_sum_opposite_candidate_not_order",
                        "ownerless_base_planetlinked_both_not_owner_proof",
                        "owner_starbase_explicit_at_planet_both",
                    ):
                        per_game_surface_context[pair.game][metric] += values.get(
                            metric, 0
                        )
        for mineral, groups in context[
            "per_mineral_category_surface_residual_magnitude_buckets"
        ].items():
            for residual_class, values in groups.items():
                residual_bins[mineral][residual_class].update(values)
        for name, obj in item["section_counts"].items():
            for point, value in obj.items():
                if value is not None:
                    section_counts[f"{name}_{point}_rows"] += value
                else:
                    status[f"ABSTAIN_SECTION_MISSING_{name}_{point}"] += 1

    # Independently calculated cross-tab must agree with the existing
    # conditional mining profiler, including all cohort denominators.
    for mineral, model_counts in mineral_model.items():
        classes = residual_categories[mineral]
        qualified = model_counts.get("candidate_default_mining_qualified", 0)
        both = model_counts.get("both_stock_deltas_match_default_model", 0)
        g = model_counts.get("ground_delta_matches_default_model", 0)
        surface = model_counts.get("surface_delta_matches_default_mining", 0)
        expected = {
            "both_exact": both,
            "ground_exact_surface_residual": g - both,
            "surface_exact_ground_residual": surface - both,
            "neither_exact": qualified - g - surface + both,
        }
        if any(value < 0 for value in expected.values()) or any(
            classes.get(k, 0) != v for k, v in expected.items()
        ) or sum(classes.values()) != qualified:
            raise ValueError("M2_SURFACE_RESIDUAL_CONTEXT_MODEL_COUNT_DIVERGENCE")
    clustering: dict[str, Counter[str]] = defaultdict(Counter)
    for game_counts in per_game_residual.values():
        for residual_class in RESIDUAL_CLASSES:
            count = game_counts[residual_class]
            bucket = (
                "0" if count == 0 else
                "1" if count == 1 else
                "2_to_5" if count <= 5 else
                "6_to_20" if count <= 20 else
                "21_to_100" if count <= 100 else "over_100"
            )
            clustering[residual_class][bucket] += 1

    context_game_histograms: dict[str, Counter[str]] = defaultdict(Counter)
    planet_event_game_histograms: dict[str, Counter[str]] = defaultdict(Counter)
    event_keys = (
        "planet_windows_any_surface_residual",
        "planet_windows_any_single_cargo",
        "planet_windows_any_multiship_cargo",
        "planet_windows_any_cargo_candidate",
        "planet_windows_any_planetlinked_base",
        "planet_windows_any_base_tech_change",
        "planet_windows_base_tech_and_cargo_candidate",
    )
    for game_event_counts in per_game_planet_events.values():
        for metric in event_keys:
            n = game_event_counts[metric]
            label = (
                "0" if n == 0 else "1" if n == 1 else
                "2_to_5" if n <= 5 else "6_to_20" if n <= 20 else
                "21_to_100" if n <= 100 else "over_100"
            )
            planet_event_game_histograms[metric][label] += 1

    for mineral, j in joint_surface_cargo_base.items():
        cov = residual_covariates[mineral].get("ground_exact_surface_residual", {})
        size = residual_categories[mineral].get("ground_exact_surface_residual", 0)
        if (j["qualified_surface_residual"] != size or sum(
            j.get(k, 0) for k in (
                "both_single_and_multiship_candidate",
                "single_only_cargo_candidate",
                "multiship_only_cargo_candidate",
                "no_exact_cargo_candidate",
            )
        ) != size or
            j["single_only_cargo_candidate"] +
            j["both_single_and_multiship_candidate"] !=
            cov.get("one_ship_opposite_cargo_delta_candidate", 0) or
            j["multiship_only_cargo_candidate"] +
            j["both_single_and_multiship_candidate"] !=
            cov.get("multiple_ship_cargo_sum_opposite_candidate_not_order", 0) or
            j["any_exact_opposite_cargo_candidate"] != (
                j["single_only_cargo_candidate"] +
                j["multiship_only_cargo_candidate"] +
                j["both_single_and_multiship_candidate"]
            ) or
            j["ownerless_planetlinked_tech_changed"] !=
            cov.get("ownerless_planetlinked_tech_changed_observed", 0)):
            raise ValueError("M2_SURFACE_JOINT_CARGO_BASE_INVARIANT_FAILURE")

    context_game_histograms: dict[str, Counter[str]] = defaultdict(Counter)
    for game_context_counts in per_game_surface_context.values():
        for metric in (
            "owner_ship_observed_at_site_both",
            "one_ship_opposite_cargo_delta_candidate",
            "multiple_ship_cargo_sum_opposite_candidate_not_order",
            "ownerless_base_planetlinked_both_not_owner_proof",
            "owner_starbase_explicit_at_planet_both",
        ):
            n = game_context_counts[metric]
            key = (
                "0" if n == 0 else
                "1" if n == 1 else
                "2_to_5" if n <= 5 else
                "6_to_20" if n <= 20 else
                "21_to_100" if n <= 100 else "over_100"
            )
            context_game_histograms[metric][key] += 1

    return {
        "schema": SCHEMA,
        "status": "CORPUS_METADATA_CENSUS_AND_BOUNDED_OWNER_CURRENT_SAMPLE_NOT_HOST_CAUSAL",
        "metadata": metadata,
        "sample": {
            "sample_status_counts": dict(sorted(status.items())),
            "nonplanet_section_observability_not_host_phase": {
                name: dict(sorted(values.items()))
                for name, values in sorted(supporting.items())
            },
            "owner_current_counts": dict(sorted(counters.items())),
            "qualified_planet_field_family_pairs": dict(sorted(fields.items())),
            "net_state_differences_not_mechanics": dict(sorted(changed.items())),
            "individual_numeric_field_directions": {
                name: dict(sorted(values.items()))
                for name, values in sorted(per_field.items())
            },
            "surface_ground_joint_signs_not_mining_attribution": {
                name: dict(sorted(values.items()))
                for name, values in sorted(mineral_joint.items())
            },
            "observable_structure_and_tax_controls":
                dict(sorted(controls.items())),
            "conditional_mineral_mass_balance_not_host_verified": {
                "model": "INFERRED_DEFAULT_MINING_PLUS_PUBLISHED_TRANSURANIUM_NOT_HOST_CAUSAL",
                "per_mineral": {
                    name: dict(sorted(values.items()))
                    for name, values in sorted(mineral_model.items())
                },
                "surface_up_ground_equal_surface_increase_buckets": {
                    name: dict(sorted(values.items()))
                    for name, values in sorted(mineral_surface_increase.items())
                },
                "net_total_minus_default_mutation_abs_residual_buckets": {
                    name: dict(sorted(values.items()))
                    for name, values in sorted(mineral_abs_residual.items())
                },
            },
            "surface_residual_context_not_host_verified": {
                "per_mineral_residual_classes": {
                    mineral: dict(sorted(groups.items()))
                    for mineral, groups in sorted(residual_categories.items())
                },
                "per_mineral_class_covariates": {
                    mineral: {
                        label: dict(sorted(counts.items()))
                        for label, counts in sorted(groups.items())
                    }
                    for mineral, groups in sorted(residual_covariates.items())
                },
                "per_mineral_class_residual_magnitude_buckets": {
                    mineral: {
                        label: dict(sorted(counts.items()))
                        for label, counts in sorted(groups.items())
                    }
                    for mineral, groups in sorted(residual_bins.items())
                },
                "source_quality_abstentions_and_limitations":
                    dict(sorted(residual_quality.items())),
                "game_cluster_residual_count_buckets": {
                    status: dict(sorted(bins.items()))
                    for status, bins in sorted(clustering.items())
                },
                "game_cluster_surface_context_count_buckets": {
                    metric: dict(sorted(bins.items()))
                    for metric, bins in sorted(context_game_histograms.items())
                },
                "per_mineral_surface_residual_joint_cargo_base": {
                    mineral: dict(sorted(counts.items()))
                    for mineral, counts in sorted(joint_surface_cargo_base.items())
                },
                "planet_transition_residual_events_not_independent_actions":
                    dict(sorted(planet_residual_events.items())),
                "game_cluster_planet_residual_events_count_buckets": {
                    metric: dict(sorted(counts.items()))
                    for metric, counts in sorted(planet_event_game_histograms.items())
                },
            },
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
            "per_field_change_is_host_phase_evidence": False,
            "nonplanet_section_counts_prove_sweeping_or_combat": False,
            "ground_down_surface_up_proves_mining": False,
            "structure_tax_stability_excludes_hidden_orders": False,
            "default_mining_and_mutation_forecast_is_host_causal": False,
            "both_mineral_deltas_matching_default_model_proves_no_other_actions": False,
            "same_site_owner_ship_observation_proves_cargo_transfer": False,
            "no_owner_ship_observed_excludes_ship_actions": False,
            "starbase_at_planet_means_ship_construction_executed": False,
        },
    }
