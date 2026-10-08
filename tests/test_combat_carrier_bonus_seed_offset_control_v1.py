from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/"tools"/"diagnostics"/"combat_carrier_bonus_seed_offset_control_v1.py"
SPEC=importlib.util.spec_from_file_location("carrier_bonus_seed_offset_control_v1",MODULE)
assert SPEC is not None and SPEC.loader is not None
PROBE=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=PROBE
SPEC.loader.exec_module(PROBE)
FIXTURE=ROOT/"validation"/"combat"/"carrier-bonus-seed-offset-game400330-t141.json"


def test_t141_carrier_bonus_fixed_offset_control_rejects_both_orientations() -> None:
    observations=json.loads(FIXTURE.read_text(encoding="utf-8"))
    report=PROBE.audit_fixed_offsets(observations)
    assert report["status"]=="OBSERVATIONAL_NOT_PROMOTED"
    assert report["observations"]==8
    assert report["positive_360"]==5
    assert report["no_bonus"]==3
    for result in report["hypotheses"].values():
        assert result["candidate_offsets_119"]==119
        assert result["exact_offsets"]==[]
        assert result["best_matched_rows"]==7


def test_control_fails_closed_for_inconsistent_factual_labels() -> None:
    observations=json.loads(FIXTURE.read_text(encoding="utf-8"))
    observations["rows"][0]["observed_mass"]=645
    import pytest
    with pytest.raises(ValueError,match="fixture source observation invalid"):
        PROBE.audit_fixed_offsets(observations)
