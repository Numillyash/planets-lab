from tools.diagnostics.combat_host_privateer_rob_cloak_fuel_state_audit import (
    _classify_fuel_debit,
    _focus_projection,
    _fuel_threshold,
    _same_position,
)


def test_classify_fuel_debit_exact_reference_cost() -> None:
    assert _classify_fuel_debit(before_fuel=45, after_fuel=40, reference_cost=5) == (
        5,
        "exact_reference_debit",
    )


def test_classify_fuel_debit_zero_and_other() -> None:
    assert _classify_fuel_debit(before_fuel=45, after_fuel=45, reference_cost=5) == (
        0,
        "zero_debit",
    )
    assert _classify_fuel_debit(before_fuel=45, after_fuel=38, reference_cost=5) == (
        7,
        "other_debit",
    )


def test_classify_fuel_debit_unresolved() -> None:
    assert _classify_fuel_debit(before_fuel=None, after_fuel=40, reference_cost=5) == (
        None,
        "fuel_unresolved",
    )
    assert _classify_fuel_debit(before_fuel=45, after_fuel=40, reference_cost=None) == (
        5,
        "reference_cost_unresolved",
    )


def test_fuel_threshold() -> None:
    assert _fuel_threshold(4, 5) == "below_reference_cost"
    assert _fuel_threshold(5, 5) == "equals_reference_cost"
    assert _fuel_threshold(6, 5) == "above_reference_cost"
    assert _fuel_threshold(None, 5) == "unresolved"


def test_same_position() -> None:
    before = {"x": 10, "y": 20}
    assert _same_position(before, {"x": 10, "y": 20}) is True
    assert _same_position(before, {"x": 11, "y": 20}) is False
    assert _same_position(before, {"x": None, "y": 20}) is None


def test_focus_projection_observed_exact_debit() -> None:
    row = {
        "game_id": 360690,
        "battle_turn": 83,
        "classification": "initial_skip_target_outranks_factual",
        "target_ship_id": 98,
        "attacker_ship_id": 264,
        "target": {
            "fuel": 45,
            "basic_cloak_fuel_cost": 5,
            "damage": 0,
            "iscloaked": True,
        },
        "target_t_identity_stable": True,
        "target_t_state_attribution_only": {"fuel": 40, "iscloaked": True},
        "loki_context": {"any_active_start_within_10": False},
        "rob_origin": {"foreign_colocated_count": 0},
    }
    result = _focus_projection(row)
    assert result["observed_fuel_debit"] == 5
    assert result["observed_debit_relation"] == "exact_reference_debit"
    assert result["hypothetical_after_reference_debit"] == 40
    assert result["reference_debit_exhausts_fuel"] is False


def test_focus_projection_ship118_hypothetical_exhaustion_only() -> None:
    row = {
        "game_id": 620694,
        "battle_turn": 64,
        "classification": "initial_pair_vcr",
        "target_ship_id": 118,
        "attacker_ship_id": 134,
        "target": {
            "fuel": 5,
            "basic_cloak_fuel_cost": 5,
            "damage": 0,
            "iscloaked": True,
        },
        "target_t_identity_stable": False,
        "target_t_state_attribution_only": None,
        "loki_context": {"any_active_start_within_10": False},
        "rob_origin": {"foreign_colocated_count": 0},
    }
    result = _focus_projection(row)
    assert result["observed_fuel_debit"] is None
    assert result["observed_debit_relation"] == "fuel_unresolved"
    assert result["hypothetical_after_reference_debit"] == 0
    assert result["reference_debit_exhausts_fuel"] is True
    assert result["fuel_threshold"] == "equals_reference_cost"
