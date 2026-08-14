from planets_lab.corpus.movement_horwasp_diagnostics import _interesting_fields, _is_pod_like


def test_interesting_fields_keep_only_mechanical_state() -> None:
    raw = {
        "id": 10,
        "targetshipid": 99,
        "podspeed": 54,
        "warp": 0,
        "mission": 0,
        "friendlycode": "123",
        "name": "private-ish label",
        "message": "do not dump",
        "destinationx": 100,
        "destinationy": 200,
    }
    result = _interesting_fields(raw)
    assert result == {
        "destinationx": 100,
        "destinationy": 200,
        "mission": 0,
        "podspeed": 54,
        "targetshipid": 99,
        "warp": 0,
    }


def test_pod_like_detection_uses_historical_catalog_text() -> None:
    assert _is_pod_like({"name": "Red Mite", "special": ""}) is True
    assert _is_pod_like({"name": "Duranium Rock", "special": "Pod"}) is True
    assert _is_pod_like({"name": "Firecloud", "special": "Chunnel Initiator"}) is False


def test_horwasp_diagnostics_cli_imports() -> None:
    from planets_lab.corpus.movement_horwasp_diagnostics_cli import main

    assert callable(main)
