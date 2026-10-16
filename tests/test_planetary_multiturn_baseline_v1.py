from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/planetary_multiturn_baseline_v1.py"
SPEC=importlib.util.spec_from_file_location("planetary_multiturn_baseline_v1",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def test_m2_existing_canonical_pipeline_composes_three_full_turns_deterministically():
    a=M.build_report()
    b=M.build_report()
    assert a==b
    assert a["schema"]==M.SCHEMA
    assert a["summary"]["initial_turn"]==7
    assert a["summary"]["last_turn"]==10
    assert a["turns_compared"]==3
    assert len(a["trace"]["steps"])==3
    assert a["summary"]["multi_turn_deterministic"] is True
    assert a["summary"]["original_state_unchanged"] is True
    assert a["phase_names"]==M.PHASES
    assert all(step["to_turn"]==step["from_turn"]+1 for step in a["trace"]["steps"])


def test_new_scope_cannot_be_misreported_as_NuHost_differential_or_full_M2():
    r=M.build_report()
    assert r["status"]=="M2_INTERNAL_MULTITURN_BASELINE_TESTED_NOT_NUHOST_DIFFERENTIAL"
    assert r["summary"]["factual_NuHost_archives_compared"]==0
    assert r["summary"]["NuHost_phase_differential_verified"] is False
    assert r["summary"]["complete_planetary_host_implemented"] is False
    assert r["summary"]["canonical_combat_C5_changes"]==0
    assert "starbase_ship_construction" in r["unimplemented_surfaces"]
    assert "real_game_multi_turn_differential" in r["unimplemented_surfaces"]


def test_m2_resources_are_consistent_with_source_cloning_and_unowned_boundaries():
    run=M.trajectory()
    initial={p["id"]:p for p in run["initial"]["planets"]}
    final={p["id"]:p for p in run["final"]["planets"]}
    assert len(initial)==len(final)==3
    assert initial[1]["colonist_clans"]==100
    assert final[1]["colonist_clans"]>=initial[1]["colonist_clans"]
    assert final[1]["supplies"]>initial[1]["supplies"]
    assert final[1]["minerals"]["duranium"]["surface"]>0
    assert final[3]["owner_id"] is None
    assert final[3]["supplies"]==initial[3]["supplies"]
    assert final[3]["megacredits"]==initial[3]["megacredits"]
    for planet in final.values():
        for mineral in planet["minerals"].values():
            assert mineral["surface"]>=0 and mineral["ground"]>=0


def test_freeze_failure_on_phase_order_change(monkeypatch):
    monkeypatch.setattr(M,"PHASES",("invented_phase",))
    with pytest.raises(ValueError,match="relative-phase order drift"):
        M.trajectory()


def test_m2_report_is_valid_and_exactly_same_trace_on_replay(tmp_path,monkeypatch):
    dest=tmp_path/"research"/"report.json"
    monkeypatch.setattr(sys,"argv",["m2-baseline","--output",str(dest)])
    assert M.main()==0
    data=json.loads(dest.read_text())
    assert data["status"]==M.build_report()["status"]
    assert data["internal_trace_sha256"]==M.build_report()["internal_trace_sha256"]
    assert not list(dest.parent.glob("*.tmp"))


def test_one_server_command_and_explicit_no_c5_or_current_modifications():
    runner=ROOT/"tools/run-planetary-multiturn-baseline-v1.sh"
    wrapper=ROOT/"tools/run-planetary-multiturn-baseline-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    assert "planetary_multiturn_baseline_v1.py" in runner.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/planetary/multiturn-baseline-v1/published" in wrapper.read_text()
    assert "run-combat" not in runner.read_text()
    assert "--activate-current" not in runner.read_text()
