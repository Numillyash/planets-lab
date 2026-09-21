from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "diagnostics" / "combat_capture_reintegration_check.py"
SPEC = spec_from_file_location("combat_capture_reintegration_check", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _capture_report() -> dict:
    return {
        "summary": {
            "feature_scope": {"profile": "combat-planar-no-horwasp"},
            "counts": {"capture_reappearance_transitions": 23},
            "acceptance": {"capture_transition_gate_passed": True},
        }
    }


def _initiator_report() -> dict:
    return {
        "summary": {
            "feature_scope": {"profile": "combat-planar-no-horwasp"},
            "counts": {
                "capture_continuations": 23,
                "opponent_type:ship": 8,
                "opponent_type:planet": 15,
                "independent_opponent_attack_candidate": 23,
            },
            "required_unresolved_total": 0,
            "acceptance": {"post_capture_initiator_gate_passed": True},
        }
    }


def test_accepts_preserved_capture_population(tmp_path: Path) -> None:
    report = MODULE.run(
        _write(tmp_path / "predictive.json", {"exact": True, "failures": []}),
        _write(tmp_path / "capture.json", _capture_report()),
        _write(tmp_path / "initiator.json", _initiator_report()),
    )
    assert report["exact"] is True
    assert report["failures"] == []


def test_rejects_population_shrink(tmp_path: Path) -> None:
    initiator = _initiator_report()
    initiator["summary"]["counts"]["opponent_type:ship"] = 7
    report = MODULE.run(
        _write(tmp_path / "predictive.json", {"exact": True, "failures": []}),
        _write(tmp_path / "capture.json", _capture_report()),
        _write(tmp_path / "initiator.json", initiator),
    )
    assert report["exact"] is False
    assert "ship_continuation_population_preserved" in report["failures"]
