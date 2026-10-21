"""Classic PBP standard-only pointer; no priority, cloning or ship creation."""
from __future__ import annotations

from dataclasses import replace

import pytest

from planets_lab.sim.classic_standard_queue_pointer import (
    STATUS, ClassicBaseQueueEntry, ClassicStandardSubphase,
    select_classic_standard_subphase,
)


def base(pid, owner, queued, **changes):
    return ClassicBaseQueueEntry(pid, owner, queued, **changes)


def scenario(**kwargs):
    args = dict(
        ship_limit=500,
        current_ship_count=498,
        last_standard_build_planet_id=40,
        bases=(
            base(10, 1, True),
            base(30, 1, False),
            base(50, 2, True),
            base(80, 1, True),
            base(500, 2, True),
        ),
        player_pbps=((1, 20), (2, 0)),
        standard_phase_after_priorities_asserted=True,
        complete_starbase_roster_asserted=True,
        complete_player_pbp_balances_asserted=True,
        no_cloning_or_other_build_effects_asserted=True,
    )
    args.update(kwargs)
    return ClassicStandardSubphase(**args)


def test_two_available_slots_walk_past_idle_and_stop_with_persisted_pointer():
    state = scenario()
    selected = select_classic_standard_subphase(state)
    assert selected.status == STATUS and selected.supported
    assert selected.selected_planet_ids == (50, 80)
    assert selected.last_standard_build_planet_id_after == 80
    assert selected.unfilled_ship_slots == 0
    assert not selected.queue_pointer_independently_verified
    assert not selected.pbp_balances_independently_verified
    assert not selected.nuhost_standard_subphase_verified
    assert not selected.nuhost_ship_ids_allocated


def test_wrap_after_planet_500_and_skip_all_empty_bases():
    s = scenario(current_ship_count=497, last_standard_build_planet_id=499)
    result = select_classic_standard_subphase(s)
    assert result.selected_planet_ids == (500, 10, 50)
    assert result.last_standard_build_planet_id_after == 50


def test_pointer_between_existing_planet_ids_is_valid():
    s = scenario(current_ship_count=498, last_standard_build_planet_id=57)
    result = select_classic_standard_subphase(s)
    assert result.selected_planet_ids == (80, 500)


def test_full_limit_yields_empty_supported_selection_without_pointer_advance():
    s = scenario(current_ship_count=500)
    result = select_classic_standard_subphase(s)
    assert result.supported
    assert result.selected_planet_ids == ()
    assert result.unfilled_ship_slots == 0
    assert result.last_standard_build_planet_id_after == 40


def test_fewer_orders_than_free_slots_leaves_slots_unused():
    s = scenario(current_ship_count=495)
    r = select_classic_standard_subphase(s)
    assert r.supported
    assert r.selected_planet_ids == (50, 80, 500, 10)
    assert r.unfilled_ship_slots == 1
    assert r.last_standard_build_planet_id_after == 10


def test_pointer_chains_across_explicit_subphases_without_guessing_next_host():
    original = scenario(current_ship_count=499)
    first = select_classic_standard_subphase(original)
    assert first.selected_planet_ids == (50,)
    assert first.last_standard_build_planet_id_after == 50
    # A later caller supplied a *new*, independently asserted fleet count;
    # this test does not infer whether battles or new Host phases happened.
    next_context = replace(
        original,
        current_ship_count=498,
        last_standard_build_planet_id=first.last_standard_build_planet_id_after,
        bases=tuple(
            replace(row, ordinary_ship_queued=False)
            if row.planet_id == 50 else row for row in original.bases
        ),
    )
    second = select_classic_standard_subphase(next_context)
    assert second.selected_planet_ids == (80, 500)
    assert second.last_standard_build_planet_id_after == 500


@pytest.mark.parametrize("invalid", (
    "missing_priority_assert", "missing_base_assert", "missing_pbp_assert",
    "missing_no_clone_assert", "ship_limit_over_999", "ship_limit_zero",
    "ship_count_over_limit", "ship_count_bool", "unknown_pointer",
    "negative_pointer", "pointer_bool", "duplicate_base", "bool_base_id", "missing_owner_points",
    "duplicate_owner_points", "negative_pbp", "threshold_21_pbp",
    "bool_pbp", "priority_fcode", "clone", "invalid_order_flag",
    "missing_player_scope", "unsupported_base_501",
    "no_bases", "no_pp_rows",
))
def test_unattributable_input_abstains_without_partial_selection(invalid):
    s = scenario()
    if invalid == "missing_priority_assert":
        s = replace(s, standard_phase_after_priorities_asserted=False)
    elif invalid == "missing_base_assert":
        s = replace(s, complete_starbase_roster_asserted=False)
    elif invalid == "missing_pbp_assert":
        s = replace(s, complete_player_pbp_balances_asserted=False)
    elif invalid == "missing_no_clone_assert":
        s = replace(s, no_cloning_or_other_build_effects_asserted=False)
    elif invalid == "ship_limit_over_999": s = replace(s, ship_limit=1000)
    elif invalid == "ship_limit_zero": s = replace(s, ship_limit=0)
    elif invalid == "ship_count_over_limit":
        s = replace(s, current_ship_count=501)
    elif invalid == "ship_count_bool":
        s = replace(s, current_ship_count=True)
    elif invalid == "unknown_pointer":
        s = replace(s, last_standard_build_planet_id=None)
    elif invalid == "negative_pointer":
        s = replace(s, last_standard_build_planet_id=-1)
    elif invalid == "pointer_bool":
        s = replace(s, last_standard_build_planet_id=True)
    elif invalid == "duplicate_base":
        s = replace(s, bases=s.bases+(s.bases[0],))
    elif invalid == "bool_base_id":
        s = replace(s, bases=(base(True, 1, True),)+s.bases[1:])
    elif invalid == "missing_owner_points":
        s = replace(s, player_pbps=((1, 20),))
    elif invalid == "duplicate_owner_points":
        s = replace(s, player_pbps=((1, 20), (1, 0), (2, 0)))
    elif invalid == "negative_pbp":
        s = replace(s, player_pbps=((1, -1), (2, 0)))
    elif invalid == "threshold_21_pbp":
        s = replace(s, player_pbps=((1, 21), (2, 0)))
    elif invalid == "bool_pbp":
        s = replace(s, player_pbps=((1, True), (2, 0)))
    elif invalid == "priority_fcode":
        s = replace(s, bases=(base(10, 1, True, priority_build_code=1),)+s.bases[1:])
    elif invalid == "clone":
        s = replace(s, bases=(base(10, 1, True, clone_ordered=True),)+s.bases[1:])
    elif invalid == "invalid_order_flag":
        s = replace(s, bases=(base(10, 1, "on"),)+s.bases[1:])
    elif invalid == "missing_player_scope":
        s = replace(s, player_pbps=((1, 0), (2, 0), (3, 0)))
    elif invalid == "unsupported_base_501":
        s = replace(s, bases=(base(501, 1, True),)+s.bases[1:])
    elif invalid == "no_bases": s = replace(s, bases=())
    elif invalid == "no_pp_rows": s = replace(s, player_pbps=())
    result = select_classic_standard_subphase(s)
    assert result.status == "ABSTAIN_CLASSIC_STANDARD_SUBPHASE"
    assert result.selected_planet_ids == ()
    assert result.last_standard_build_planet_id_after is None
    assert not result.supported


def test_omitted_real_base_cannot_be_inferred_without_external_roster():
    """Complete-starbase-roster is a *caller assertion*, not independent proof."""
    full = scenario()
    omission = replace(full, bases=full.bases[:3])
    assert select_classic_standard_subphase(omission).supported
    assert not select_classic_standard_subphase(replace(
        omission, complete_starbase_roster_asserted=False,
    )).supported
