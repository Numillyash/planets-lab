"""Synthetic M2 client economic witnesses: NO real private HAR data."""
from __future__ import annotations

from copy import deepcopy

import pytest

from planets_lab.data.nu_save_client_economic_witnesses import (
    analyze_client_economic_evidence, EVIDENCE,
)
from planets_lab.data.nu_save_payload import NuSavePayloadError


def record(identity: int, **fields: object) -> str:
    return "|||".join(
        [f"Id:::{identity}"] + [f"{key}:::{value}" for key, value in fields.items()]
    )


def request(
    *,
    turn: int = 7, stamp: str | None = None, game: int = 424242,
    **entities: str,
) -> dict:
    form = {
        "gameid": str(game), "playerid": "1",
        "turn": str(turn), "version": "4", "saveindex": "2",
        "apikey": "<REDACTED_CREDENTIAL>",
        "savekey": "<REDACTED_CREDENTIAL>",
        **entities,
    }
    form["keycount"] = str(len(form) + 1)
    return {
        "method": "POST", "transport": "har",
        "request": {"encoding": "form", "body": form},
        "response": {"encoding": "json", "body": {
            "success": True, "saveIndex": 2,
        }},
        "http_status": 200,
        "timing": {"start_iso": stamp, "network_duration_ms": 12},
    }


def session(*observations: dict) -> dict:
    return {
        "schema": "planets-lab.save-payload-capture.v1",
        "observations": list(observations),
        "route_counters": {"save": len(observations)},
    }


def bundle(*sessions: dict) -> dict:
    return {
        "schema": "planets-lab.har-save-capture-bundle.v1",
        "sessions": list(sessions),
    }


def pick(window: dict, kind: str) -> list[dict]:
    return [ev for ev in window["events"] if ev["kind"] == kind]


def test_pending_reserved_transfer_cancel_exact_balance():
    before = request(Ship5=record(
        5, Clans=30, MegaCredits=1269,
        TransferClans=20, TransferMegaCredits=200,
        TransferTargetId=12, TransferTargetType=1,
    ))
    after = request(Ship5=record(
        5, Clans=50, MegaCredits=1469,
        TransferClans=0, TransferMegaCredits=0,
        TransferTargetId=0, TransferTargetType=0,
    ))
    result = analyze_client_economic_evidence(bundle(session(before, after)))
    events = pick(result["windows"][0], "PENDING_TRANSFER_STATE_CHANGE")
    assert len(events) == 1
    ev = events[0]
    assert ev["status"] == "CLIENT_RESERVATION_BALANCED"
    assert ev["resource_deltas"] == {
        "MegaCredits": {"available_delta": 200, "reserved_delta": -200, "total_delta": 0},
        "Clans": {"available_delta": 20, "reserved_delta": -20, "total_delta": 0},
    } or ev["resource_deltas"] == {
        "Clans": {"available_delta": 20, "reserved_delta": -20, "total_delta": 0},
        "MegaCredits": {"available_delta": 200, "reserved_delta": -200, "total_delta": 0},
    }
    assert ev["transfer_target_before"]["TransferTargetId"] == "12"
    assert ev["transfer_target_after"]["TransferTargetId"] == "0"
    assert ev["evidence"] == EVIDENCE
    assert result["summary"]["NuHost_order_execution_verified"] is False


def test_unbalanced_pending_not_misrepresented_as_transfer_cancellation():
    events = pick(analyze_client_economic_evidence(bundle(session(
        request(Ship9=record(9, Clans=100, TransferClans=10,
                             TransferTargetId=3, TransferTargetType=1)),
        request(Ship9=record(9, Clans=100, TransferClans=0,
                             TransferTargetId=0, TransferTargetType=0)),
    )))["windows"][0], "PENDING_TRANSFER_STATE_CHANGE")
    assert len(events) == 1
    assert events[0]["status"] == "CLIENT_TRANSFER_STATE_CHANGED_UNATTRIBUTED"
    assert events[0]["resource_deltas"]["Clans"]["total_delta"] == -10


def test_direct_cargo_cochange_requires_two_observed_baselines():
    before = request(
        Ship3=record(3, Clans=0, TransferClans=0,
                     TransferTargetId=0, TransferTargetType=0),
        Planet1=record(1, Clans=914),
    )
    after = request(
        Ship3=record(3, Clans=100, TransferClans=0,
                     TransferTargetId=0, TransferTargetType=0),
        Planet1=record(1, Clans=814),
    )
    out = analyze_client_economic_evidence(bundle(session(before, after)))
    events = pick(out["windows"][0], "CO_SAVED_SHIP_PLANET_STOCK_BALANCE")
    assert len(events) == 1
    assert events[0]["resource"] == "Clans"
    assert events[0]["ship_delta"] == 100
    assert events[0]["planet_delta"] == -100
    assert events[0]["status"] == "CLIENT_BALANCED_CHANGE_CANDIDATE"

    missing_ship_baseline = analyze_client_economic_evidence(bundle(session(
        request(Planet1=record(1, Clans=914)),
        after,
    )))
    assert pick(missing_ship_baseline["windows"][0],
                "CO_SAVED_SHIP_PLANET_STOCK_BALANCE") == []


def test_partial_saves_compare_last_seen_entity_not_immediately_previous_post():
    a = request(Ship3=record(3, Clans=0, TransferClans=0,
                              TransferTargetId=0, TransferTargetType=0),
                Planet1=record(1, Clans=914))
    unrelated = request(Ship9=record(9, Clans=7))
    c = request(Ship3=record(3, Clans=100, TransferClans=0,
                             TransferTargetId=0, TransferTargetType=0),
                Planet1=record(1, Clans=814))
    out = analyze_client_economic_evidence(bundle(session(a, unrelated, c)))
    event = pick(out["windows"][0], "CO_SAVED_SHIP_PLANET_STOCK_BALANCE")[0]
    assert event["previous_entity_save_index"] == 0
    assert event["save_index_in_window"] == 2


def test_new_transfer_snapshot_is_not_supposed_event():
    out = analyze_client_economic_evidence(bundle(session(
        request(Ship3=record(3, Clans=30, TransferClans=40,
                              TransferTargetId=12, TransferTargetType=1))
    )))
    assert pick(out["windows"][0], "PENDING_TRANSFER_STATE_CHANGE") == []


def test_client_starbase_build_cost_wrong_numeric_ids_and_tech_upgrade():
    first = request(
        Starbase1=record(
            1, IsBuilding="false", BuildHullId=0, EngineTechLevel=7,
            EngineTechUp=0,
        ),
        Planet8=record(
            8, MegaCredits=4000, Duranium=300, Tritanium=200,
            Molybdenum=400,
        ),
    )
    second = request(
        Starbase1=record(
            1, IsBuilding="true", BuildHullId=4,
            BuildEngineId=9, BuildBeamId=6, BuildTorpedoId=6,
            BuildBeamCount=4, BuildTorpCount=4,
            EngineTechLevel=10, EngineTechUp=3,
        ),
        Planet8=record(
            8, MegaCredits=698, Duranium=192, Tritanium=163,
            Molybdenum=265,
        ),
    )
    out = analyze_client_economic_evidence(bundle(session(first, second)))
    event = pick(out["windows"][0], "STARBASE_BUILD_SPENDING_COHANGE")[0]
    assert event["planet_entity"] == "Planet8"
    assert event["observed_planet_spending"] == {
        "MegaCredits": 3302, "Duranium": 108,
        "Tritanium": 37, "Molybdenum": 135,
    }
    assert event["status"] == "CLIENT_BUILD_SPENDING_WITH_TECH_CHANGE"
    assert event["tech_field_changes"]["EngineTechUp"] == {
        "before": "0", "after": "3",
    }
    assert out["summary"]["NuHost_phase_order_verified"] is False


def test_ambiguous_spend_explicitly_abstains():
    a = request(
        Starbase1=record(1, IsBuilding="false"),
        Planet1=record(1, MegaCredits=500, Duranium=100, Tritanium=100, Molybdenum=100),
        Planet8=record(8, MegaCredits=500, Duranium=100, Tritanium=100, Molybdenum=100),
    )
    b = request(
        Starbase1=record(1, IsBuilding="true"),
        Planet1=record(1, MegaCredits=400, Duranium=90, Tritanium=90, Molybdenum=90),
        Planet8=record(8, MegaCredits=400, Duranium=90, Tritanium=90, Molybdenum=90),
    )
    out = analyze_client_economic_evidence(bundle(session(a, b)))
    assert not pick(out["windows"][0], "STARBASE_BUILD_SPENDING_COHANGE")
    ev = pick(out["windows"][0], "STARBASE_BUILD_COST_ABSTENTION")[0]
    assert ev["status"] == "ABSTAIN_AMBIGUOUS_SPENDING_PLANETS"
    assert ev["candidate_planet_count"] == 2


def test_tax_is_client_forecast_and_has_both_values():
    a = request(Planet1=record(
        1, NativeTaxRate=0, NativeHappyChange=6, ColonistTaxRate=0,
        ColHappyChange=8,
    ))
    b = request(Planet1=record(
        1, NativeTaxRate=5, NativeHappyChange=2, ColonistTaxRate=0,
        ColHappyChange=8,
    ))
    ev = pick(analyze_client_economic_evidence(bundle(session(a, b)))["windows"][0],
              "PLANET_TAX_PREVIEW_CHANGE")[0]
    assert ev["tax_before"] == 0 and ev["tax_after"] == 5
    assert ev["preview_before"] == "6" and ev["preview_after"] == "2"
    assert ev["status"] == "CLIENT_FORECAST_ONLY"


def test_overlap_sessions_sorted_by_timestamp_without_cross_turn_diff():
    t0 = "2026-10-17T18:00:00Z"
    t1 = "2026-10-17T18:00:01Z"
    earlier = session(request(stamp=t0, Planet1=record(1, Clans=100)))
    later = session(request(stamp=t1, Planet1=record(1, Clans=90)))
    different_turn = session(request(
        turn=8, stamp=t1, Planet1=record(1, Clans=70),
    ))
    out = analyze_client_economic_evidence(bundle(later, different_turn, earlier))
    assert out["summary"]["input_saves"] == 3
    assert out["summary"]["unique_game_player_turn_windows"] == 2
    assert out["summary"]["overlap_windows"] == 1
    w7 = next(w for w in out["windows"] if w["turn"] == 7)
    assert w7["source_segments"] == 2
    assert w7["save_count"] == 2
    assert w7["status"] == "CLIENT_OBSERVATIONS_ORDERED_NOT_HOST_VERIFIED"
    assert out["summary"]["NuHost_order_execution_verified"] is False
    # A planet-only stock change is not automatically a Host production or a transfer.
    assert w7["events"] == []


def test_overlap_without_complete_timestamps_abstains_and_does_not_splice():
    out = analyze_client_economic_evidence(bundle(
        session(request(Planet1=record(1, Clans=100))),
        session(request(stamp="2026-10-17T18:00:02Z",
                        Planet1=record(1, Clans=70))),
    ))
    assert out["summary"]["windows_abstained"] == 1
    assert out["summary"]["saves_with_witnessed_order"] == 0
    assert out["windows"][0]["status"] == "ABSTAIN_CROSS_HAR_ORDER_UNWITNESSED"
    assert out["windows"][0]["events"] == []


def test_notes_and_secret_fields_never_enter_research_event_output():
    src = bundle(session(
        request(
            Note120="Id:::0|||OwnerId:::1|||Body:::PRIVATE_NOTE_DO_NOT_EXPORT"
                    "|||TargetId:::12|||TargetType:::0|||Color:::",
            Ship5=record(5, Clans=30, TransferClans=20,
                         TransferTargetId=12, TransferTargetType=1),
        ),
        request(
            Note120="Id:::0|||OwnerId:::1|||Body:::SECOND_PRIVATE_NOTE"
                    "|||TargetId:::12|||TargetType:::0|||Color:::",
            Ship5=record(5, Clans=50, TransferClans=0,
                         TransferTargetId=0, TransferTargetType=0),
        ),
    ))
    import json
    output = json.dumps(analyze_client_economic_evidence(src))
    for forbidden in (
        "PRIVATE_NOTE_DO_NOT_EXPORT", "SECOND_PRIVATE_NOTE",
        "REDACTED_CREDENTIAL", "apikey", "savekey",
    ):
        assert forbidden not in output


def test_rejects_mixed_identity_inside_one_session():
    src = bundle(session(request(), request(turn=8)))
    with pytest.raises(NuSavePayloadError):
        analyze_client_economic_evidence(src)
