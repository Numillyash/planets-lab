"""Synthetic proofs of actual legacy Nu save format, partial record semantics."""
from __future__ import annotations

from copy import deepcopy

import pytest

from planets_lab.data.nu_save_payload import (
    NuSavePayloadError,
    analyze_save_capture,
    parse_capture,
    parse_legacy_entity,
    parse_save_body,
)


def entity(kind: str, number: int, **fields: object) -> str:
    return "|||".join(
        [f"Id:::{number}"] + [f"{key}:::{value}" for key, value in fields.items()]
    )


def event(**entries: str) -> dict:
    body = {
        "gameid": "424242",
        "playerid": "1",
        "turn": "33",
        "version": "4",
        "savekey": "<REDACTED_CREDENTIAL>",
        "apikey": "<REDACTED_CREDENTIAL>",
        "saveindex": "2",
        **entries,
    }
    body["keycount"] = str(len(body) + 1)
    return {
        "transport": "xhr", "method": "POST",
        "request": {"encoding": "form", "body": body},
        "http_status": 200,
        "response": {"encoding": "json", "body": {"success": None, "saveIndex": 2}},
    }


def capture(*events: dict) -> dict:
    return {
        "schema": "planets-lab.save-payload-capture.v1",
        "observed_save_calls_retained": len(events),
        "observations": list(events),
        "route_counters": {"save": len(events) + 2, "turnready": 0},
    }


def sample_capture() -> dict:
    planet_914 = entity("Planet", 1, Clans=914, ColonistTaxRate=0, SuppliesSold=112)
    planet_814 = entity("Planet", 1, Clans=814, ColonistTaxRate=0, SuppliesSold=112)
    base = entity("Starbase", 1, Fighters=0, Mission=4, IsBuilding="false")
    ship6 = entity("Ship", 6, Name="LARGE DEEP SPACE FREIGHTER",
                   Neutronium=600, Waypoints="", TargetX=1960)
    ship3 = entity("Ship", 3, Name="NEBULA CLASS CRUISER", Clans=100)
    ship4_p3 = entity("Ship", 4, TargetX=1965, TargetY=1956, Warp=7)
    ship4_p1 = entity("Ship", 4, TargetX=2004, TargetY=2035, Warp=7)
    p3 = entity("Planet", 3, Clans=357)
    return capture(
        event(Planet1=planet_914, Starbase1=base),
        event(Ship6=ship6, Planet1=planet_914, Starbase1=base),
        event(Ship3=ship3, Planet1=planet_814, Starbase1=base),
        event(Planet1=planet_814, Starbase1=base),
        event(Ship4=ship4_p3, Planet3=p3),
        event(Ship4=ship4_p1, Planet3=p3),
    )


def test_legacy_entity_grammar_preserves_exact_strings_and_empty_waypoints():
    item = parse_legacy_entity(
        "Id:::6|||Name:::LARGE DEEP SPACE FREIGHTER"
        "|||Neutronium:::600|||Waypoints:::|||ReadyStatus:::0",
        kind="Ship", entity_id=6,
    )
    assert item.kind == "Ship"
    assert item.identity == "Ship6"
    assert item.fields == {
        "Id": "6", "Name": "LARGE DEEP SPACE FREIGHTER",
        "Neutronium": "600", "Waypoints": "", "ReadyStatus": "0",
    }


def test_parse_observed_form_entity_fields_and_keycount():
    sample = sample_capture()
    parsed = parse_capture(sample)
    assert len(parsed) == 6
    assert parsed[1].entities["Ship6"].fields["Neutronium"] == "600"
    assert parsed[0].entities["Planet1"].fields["Clans"] == "914"
    assert parsed[0].entities["Starbase1"].fields["IsBuilding"] == "false"
    assert parsed[1].source_form_field_count == 11
    assert parsed[0].response_success is None
    assert parsed[0].response_save_index == 2
    assert parsed[0].game_id == 424242
    assert parsed[0].turn == 33


def test_partial_save_absence_not_deletion_and_last_seen_diff():
    outcome = analyze_save_capture(sample_capture())
    assert outcome["schema"] == "planets-lab.nu-save-observation-analysis.v1"
    summary = outcome["summary"]
    assert summary["retained_saves"] == 6
    assert summary["earlier_saves_not_retained"] == 2
    assert summary["unique_entities_observed"] == 6
    assert summary["field_changes_between_reobserved_entities"] == 3
    assert summary["http_200_explicit_success_true"] == 0
    assert summary["http_200_success_unknown_or_null"] == 6
    assert summary["NuHost_orders_accepted_verified"] is False
    assert summary["snapshot_absence_means_deletion"] is False
    assert outcome["events"][1]["first_observed_in_window_not_creation"] == ["Ship6"]
    third = outcome["events"][2]
    assert third["first_observed_in_window_not_creation"] == ["Ship3"]
    assert third["field_changes_since_previous_entity_observation"] == [
        {
            "entity": "Planet1",
            "previous_observed_request_index": 1,
            "fields": [{"field": "Clans", "before": "914", "after": "814"}],
        }
    ]
    assert "Ship6" not in third["field_changes_since_previous_entity_observation"]
    sixth = outcome["events"][5]["field_changes_since_previous_entity_observation"]
    assert sixth == [{
        "entity": "Ship4", "previous_observed_request_index": 4,
        "fields": [
            {"field": "TargetX", "before": "1965", "after": "2004"},
            {"field": "TargetY", "before": "1956", "after": "2035"},
        ],
    }]


@pytest.mark.parametrize("kind,entity_id,source", [
    ("Ship", 2, "Id:::6|||Warp:::7"),
    ("Planet", 1, "Id:::1|||Mines:::10|||Mines:::11"),
    ("Ship", 6, "Id:::6|||Waypoints:::|||broken_field"),
    ("Ship", 6, "Id:::6|||Warp:::7|||"),
    ("Ship", 6, "Id:::6|||:::value"),
    ("Other", 6, "Id:::6|||Warp:::7"),
])
def test_malformed_and_wrong_identity_abstain(kind, entity_id, source):
    with pytest.raises(NuSavePayloadError):
        parse_legacy_entity(source, kind=kind, entity_id=entity_id)


@pytest.mark.parametrize("mutation", [
    lambda b: b.update(keycount="19"),
    lambda b: b.update(turn="foo"),
    lambda b: b.update(Ship9=entity("Ship", 7, Warp=7)),
    lambda b: b.update(ShipBad="Id:::9|||Warp:::7"),
    lambda b: b.update(Planet6="not a serialized record"),
])
def test_bad_body_never_silently_claims_a_valid_record(mutation):
    body = deepcopy(sample_capture()["observations"][0]["request"]["body"])
    mutation(body)
    with pytest.raises(NuSavePayloadError):
        parse_save_body(body)


def test_different_turns_in_capture_refused():
    payload = sample_capture()
    payload["observations"][1]["request"]["body"]["turn"] = "34"
    with pytest.raises(NuSavePayloadError, match="different games"):
        parse_capture(payload)


def test_success_true_is_distinct_from_null():
    request = event(Ship6=entity("Ship", 6, Warp=7))
    request["response"]["body"]["success"] = True
    outcome = analyze_save_capture(capture(request))
    assert outcome["summary"]["http_200_explicit_success_true"] == 1
    assert outcome["summary"]["http_200_success_unknown_or_null"] == 0


def test_non_form_and_host_inference_never_promoted():
    payload = sample_capture()
    payload["observations"][0]["request"]["encoding"] = "json"
    with pytest.raises(NuSavePayloadError, match="decoded form"):
        parse_capture(payload)

def test_success_false_rejected_as_not_verified():
    request = event(Ship6=entity("Ship", 6, Warp=7))
    request["response"]["body"]["success"] = False
    outcome = analyze_save_capture(capture(request))
    assert outcome["summary"]["http_200_explicit_success_true"] == 0
    assert outcome["summary"]["http_200_explicit_success_false"] == 1
    assert outcome["summary"]["http_200_success_unknown_or_null"] == 0


def test_cli_offline_without_raw_game_data_in_stdout(tmp_path):
    import json
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    source = tmp_path / "PRIVATE-observation.json"
    output = tmp_path / "PRIVATE-analysis.json"
    source.write_text(json.dumps(sample_capture()), encoding="utf-8")
    cmd = [
        sys.executable, str(root / "tools/diagnostics/nu_save_payload_diff_v1.py"),
        "--input", str(source), "--output", str(output),
    ]
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "retained_saves: 6" in result.stdout
    assert "field_changes_between_reobserved_entities: 3" in result.stdout
    assert "http_200_success_unknown_or_null: 6" in result.stdout
    assert "424242" not in result.stdout
    private_report = json.loads(output.read_text(encoding="utf-8"))
    assert private_report["events"][5]["field_changes_since_previous_entity_observation"][0]["fields"][0]["after"] == "2004"


def test_real_stock_and_note_wire_conventions_not_conflated():
    # Exact *structural* patterns seen in real HAR captures, using only
    # synthetic IDs and text (NEVER commit actual private captures).
    stock = parse_legacy_entity(
        "Id:::14|||Amount:::2|||BuiltAmount:::2",
        kind="Stock", entity_id=14,
    )
    assert stock.fields["BuiltAmount"] == "2"
    note = parse_legacy_entity(
        "Id:::0|||OwnerId:::1|||Body:::test-note|||TargetId:::17"
        "|||TargetType:::0|||Color:::40",
        kind="Note", entity_id=170,
    )
    assert note.identity == "Note170"
    assert note.fields["Id"] == "0"
    # A Note key encodes a selector rather than necessarily the note Id:
    assert parse_legacy_entity(
        "Id:::7|||OwnerId:::1|||Body:::|||TargetId:::12"
        "|||TargetType:::0|||Color:::34",
        kind="Note", entity_id=120,
    ).fields["Id"] == "7"
    with pytest.raises(NuSavePayloadError, match="disagree"):
        parse_legacy_entity(
            "Id:::13|||Amount:::3|||BuiltAmount:::3",
            kind="Stock", entity_id=14,
        )


def test_har_observed_auxiliary_records_and_partial_note_body_edits():
    first = event(
        Stock14="Id:::14|||Amount:::1|||BuiltAmount:::1",
        Note170="Id:::0|||OwnerId:::1|||Body:::|||TargetId:::17"
        "|||TargetType:::0|||Color:::40",
    )
    second = event(
        Note170="Id:::0|||OwnerId:::1|||Body:::synthetic-note"
        "|||TargetId:::17|||TargetType:::0|||Color:::40",
    )
    third = event(
        Stock14="Id:::14|||Amount:::2|||BuiltAmount:::2",
    )
    report = analyze_save_capture(capture(first, second, third))
    summary = report["summary"]
    assert summary["record_observations_by_kind"] == {
        "Note": 2, "Stock": 2,
    }
    assert summary["changed_fields_by_kind"] == {
        "Note": 1, "Stock": 2,
    }
    assert summary["field_changes_between_reobserved_entities"] == 3
    assert report["events"][1]["field_changes_since_previous_entity_observation"] == [{
        "entity": "Note170",
        "previous_observed_request_index": 0,
        "fields": [{"field": "Body", "before": "", "after": "synthetic-note"}],
    }]
    assert report["events"][2]["field_changes_since_previous_entity_observation"] == [{
        "entity": "Stock14",
        "previous_observed_request_index": 0,
        "fields": [
            {"field": "Amount", "before": "1", "after": "2"},
            {"field": "BuiltAmount", "before": "1", "after": "2"},
        ],
    }]
    # Absence of Stock14 from the intervening save is NOT deletion.
    assert summary["snapshot_absence_means_deletion"] is False


def test_malformed_auxiliary_wire_key_rejected():
    body = deepcopy(sample_capture()["observations"][0]["request"]["body"])
    body["StockXYZ"] = "Id:::14|||Amount:::2|||BuiltAmount:::2"
    body["keycount"] = str(len(body))
    with pytest.raises(NuSavePayloadError, match="unrecognized"):
        parse_save_body(body)
