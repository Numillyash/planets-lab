"""HAR -> redacted Nu-save analysis, entirely offline and synthetic."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlencode

import pytest

from planets_lab.data.nu_save_payload import analyze_har_save_bundle, NuSavePayloadError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "diagnostics"))
from nu_har_save_extract_v1 import (  # noqa: E402
    BUNDLE_SCHEMA, REDACTED, extract_har, route_kind, form_fields,
)


API = "DO_NOT_LEAK_TEST_APIKEY_19472"
SAVE = "DO_NOT_LEAK_TEST_SAVEKEY_59812"
COOKIE = "DO_NOT_LEAK_TEST_COOKIE_69127"
PASSWORD = "DO_NOT_LEAK_TEST_PASSWORD_79123"
INLINE = "DO_NOT_LEAK_INLINE_CREDENTIAL_28521"


def post_body(*, x: int = 1965, clans: int = 357) -> dict[str, str]:
    data = {
        "gameid": "424242", "playerid": "1", "turn": "33",
        "version": "4", "apikey": API, "savekey": SAVE, "saveindex": "2",
        "Ship4": f"Id:::4|||Name:::LARGE DEEP SPACE FREIGHTER|||"
                 f"TargetX:::{x}|||TargetY:::1956|||Waypoints:::|||ReadyStatus:::0",
        "Planet3": f"Id:::3|||Clans:::{clans}|||Supplies:::0|||FriendlyCode:::abc",
    }
    data["keycount"] = str(len(data) + 1)
    return data


def entry(
    form: dict[str, str] | None = None,
    *,
    status: int = 200,
    target_url: str = "https://api.planets.nu/game/save",
    response: dict | None = None,
    encoded: bool = False,
) -> dict:
    form = post_body() if form is None else form
    payload = json.dumps(
        response if response is not None else
        {"success": None, "saveIndex": 2, "auth": {"savekey": SAVE}},
    )
    return {
        "startedDateTime": "2026-10-17T18:30:00.000Z",
        "time": 17,
        "request": {
            "url": target_url + "?apikey=" + API,
            "method": "POST",
            "headers": [
                {"name": "Cookie", "value": COOKIE},
                {"name": "Authorization", "value": "Bearer " + PASSWORD},
            ],
            "cookies": [{"name": "session", "value": COOKIE}],
            "postData": {"mimeType": "application/x-www-form-urlencoded",
                         "text": urlencode(form)},
        },
        "response": {
            "status": status,
            "headers": [{"name": "Set-Cookie", "value": COOKIE}],
            "content": {
                "mimeType": "application/json",
                "text": (
                    base64.b64encode(payload.encode()).decode()
                    if encoded else payload
                ),
                **({"encoding": "base64"} if encoded else {}),
            },
        },
    }


def sample_har() -> dict:
    first = entry(encoded=True)
    second = entry(post_body(x=2004, clans=357))
    third = entry({**post_body(x=1988), "turn": "34"})
    ready = entry(target_url="https://api.planets.nu/game/turnready")
    unrelated = entry(target_url="https://evilplanets.nu/game/save")
    similar = entry(target_url="https://api.planets.nu/game/save-not-really")
    extra = entry(target_url="https://api.planets.nu/account/login")
    return {"log": {"version": "1.2", "entries": [
        first, second, ready, unrelated, similar, extra, third,
    ]}}


def test_devtools_har_groups_games_and_redacts_secrets_without_losing_field_changes():
    bundle = extract_har(sample_har())
    assert bundle["schema"] == BUNDLE_SCHEMA
    assert bundle["counts"] == {
        "har_entries": 7, "save_posts_seen": 3,
        "save_posts_extract_failed": 0, "save_posts_extracted": 3,
        "turnready_posts_seen": 1, "grouped_sessions": 2,
    }
    assert len(bundle["sessions"]) == 2
    session = bundle["sessions"][0]
    assert session["observed_save_calls_retained"] == 2
    assert session["route_counters"]["save"] == 2
    assert session["observations"][0]["timing"]["start_iso"] == "2026-10-17T18:30:00.000Z"
    body = session["observations"][0]["request"]["body"]
    assert body["turn"] == "33"
    assert body["gameid"] == "424242"
    assert body["Ship4"].startswith("Id:::4|||Name:::LARGE DEEP SPACE FREIGHTER")
    assert body["Planet3"].endswith("FriendlyCode:::abc")
    assert body["keycount"] == "10"
    assert body["apikey"] == REDACTED
    assert body["savekey"] == REDACTED
    assert session["observations"][0]["response"]["body"]["success"] is None
    assert session["observations"][0]["response"]["body"]["auth"] == REDACTED
    assert session["observations"][0]["response"]["body"]["saveIndex"] == 2

    analysis = analyze_har_save_bundle(bundle)
    assert analysis["schema"] == "planets-lab.har-save-bundle-analysis.v1"
    assert analysis["summary"]["sessions"] == 2
    assert analysis["summary"]["save_requests"] == 3
    assert analysis["summary"]["changed_fields"] == 1
    changes = analysis["sessions"][0]["analysis"]["events"][1]["field_changes_since_previous_entity_observation"]
    assert changes == [{
        "entity": "Ship4",
        "previous_observed_request_index": 0,
        "fields": [{"field": "TargetX", "before": "1965", "after": "2004"}],
    }]
    text = json.dumps(bundle) + json.dumps(analysis)
    for secret in (API, SAVE, COOKIE, PASSWORD):
        assert secret not in text
    for forbidden in ("Authorization", "Set-Cookie", "https://api.planets.nu"):
        assert forbidden not in text
    assert analysis["summary"]["NuHost_order_mapping_verified"] is False


def test_har_exact_route_classification_and_param_fallback():
    assert route_kind("https://planets.nu/game/save?savekey=abc") == "save"
    assert route_kind("https://api.planets.nu/game/save/") == "save"
    assert route_kind("https://api.planets.nu/game/turnready?secret=yes") == "turnready"
    assert route_kind("https://evilplanets.nu/game/save") is None
    assert route_kind("https://untrusted.example.com/game/save") is None
    assert route_kind("https://api.planets.nu/game/save-not-really") is None
    assert route_kind("javascript:game/save") is None
    out = form_fields({"params": [
        {"name": "gameid", "value": "42"},
        {"name": "savekey", "value": SAVE},
        {"name": "Ship6", "value": "Id:::6|||Warp:::7"},
    ]})
    assert out == ("form", {
        "gameid": "42", "savekey": REDACTED, "Ship6": "Id:::6|||Warp:::7",
    })


def test_nested_credential_redaction_and_unexpected_inline_auth_name():
    payload = post_body()
    payload["unknown_game_data"] = json.dumps({
        "Ship5": {"id": 5, "neutronium": 500},
        "token": COOKIE,
        "jwt": PASSWORD,
        "nested": {"refresh_token": SAVE, "description": "normal owned-game value"},
    })
    payload["third_party_note"] = "Authorization=" + INLINE
    payload["password"] = PASSWORD
    payload["keycount"] = str(len(payload))
    bundle = extract_har({"log": {"entries": [entry(payload)]}})
    safe = bundle["sessions"][0]["observations"][0]["request"]["body"]
    assert safe["unknown_game_data"]["Ship5"]["neutronium"] == 500
    assert safe["unknown_game_data"]["token"] == REDACTED
    assert safe["unknown_game_data"]["nested"]["refresh_token"] == REDACTED
    assert safe["unknown_game_data"]["nested"]["description"] == "normal owned-game value"
    assert safe["third_party_note"] == REDACTED
    assert safe["password"] == REDACTED
    for secret in (COOKIE, PASSWORD, SAVE, INLINE):
        assert secret not in json.dumps(bundle)


def test_ambiguous_and_missing_request_bodies_fail_closed():
    bad = entry()
    bad["request"]["postData"]["text"] = "gameid=42&gameid=43&turn=4"
    missing = entry()
    missing["request"]["postData"] = {}
    bundle = extract_har({"log": {"entries": [bad, missing]}})
    assert bundle["counts"]["save_posts_seen"] == 2
    assert bundle["counts"]["save_posts_extract_failed"] == 2
    assert bundle["sessions"] == []


def test_cli_one_command_writes_only_sanitized_bundle_and_existing_analyzer(tmp_path):
    raw = tmp_path / "PRIVATE-RAW-HAR-DONT-SHARE.har"
    clean = tmp_path / "SAFE_REVIEW_SAVE_BUNDLE.json"
    analysis = tmp_path / "PRIVATE-save-analysis.json"
    raw.write_text(json.dumps(sample_har()), encoding="utf-8")
    script = ROOT / "tools" / "diagnostics" / "nu_har_save_extract_v1.py"
    result = subprocess.run(
        [sys.executable, str(script), "--input", str(raw), "--output", str(clean)],
        cwd=ROOT, text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "save_posts_extracted: 3" in result.stdout
    assert "grouped_sessions: 2" in result.stdout
    assert clean.is_file()
    assert API not in clean.read_text(encoding="utf-8")
    again = subprocess.run(
        [sys.executable, str(script), "--input", str(raw), "--output", str(clean)],
        cwd=ROOT, text=True, capture_output=True, timeout=20,
    )
    assert again.returncode != 0, "must not silently overwrite a previous capture"
    converter = ROOT / "tools" / "diagnostics" / "nu_save_payload_diff_v1.py"
    diff = subprocess.run(
        [sys.executable, str(converter), "--input", str(clean), "--output", str(analysis)],
        cwd=ROOT, text=True, capture_output=True, timeout=20,
    )
    assert diff.returncode == 0, diff.stderr
    assert "save_requests: 3" in diff.stdout
    assert "field_changes_between_reobserved_entities: 1" in diff.stdout
    assert analysis.is_file()


def test_not_actual_host_evidence_and_raw_har_never_used_as_analysis_input():
    with pytest.raises(NuSavePayloadError):
        analyze_har_save_bundle(sample_har())
