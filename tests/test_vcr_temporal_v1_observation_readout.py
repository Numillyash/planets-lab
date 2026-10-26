"""Real published VCR source replay and hostile provenance validation.

Count-only fixtures. No Host, Docker, database or sealed32 access.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.vcr_temporal_v1_observation_readout import (
    EvidenceReviewAbstain, FIELDS, readout_vcr_temporal,
)

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"
V6 = ROOT / "tests/fixtures/public100_baseline68_v6_mine_joint_safe_projection.json"
VCR = ROOT / "tests/fixtures/public100_baseline68_vcr_temporal_v1_safe_projection.json"
SCORE = ROOT / "validation/research/public100-baseline68-vcr-temporal-v1-source-scorecard.json"
CLI = ROOT / "tools/diagnostics/review_vcr_temporal_v1_observations.py"


def payloads():
    return [json.loads(f.read_text(encoding="utf-8")) for f in (V5, V6, VCR)]


def counts(vcr):
    return vcr["source"]["sample"]["vcr_archive_temporal_input_readiness_not_host_phase"]


def test_exact_real_2026_10_26_vcr_runtime_replay_and_status():
    result = readout_vcr_temporal(*payloads())
    assert result == json.loads(SCORE.read_text(encoding="utf-8"))
    q = result["vcr_observer_archive_rows_not_unique_battles"]
    assert q["rows_total"] == 44332
    assert q["rows_before"] == 21918
    assert q["rows_after"] == 22414
    assert q["raw_turn_equals_archive_turn"] == 44332
    assert q["both_participant_objectids_typed"] == 44332
    assert q["both_ownerids_typed"] == 44331
    assert q["exact_turn_and_both_participants"] == 44332
    assert q["exact_turn_and_participants_and_owners"] == 44331
    assert q["qualified_exact_turn_participants_but_owners_incomplete"] == 1
    assert q["archive_pair_lists_both_empty"] == 3748
    assert q["same_generic_id_across_adjacent_archives_not_battle_link"] == 0
    assert all(value is False for key,value in result["inference_gates"].items()
               if key != "typed_same_turn_vcr_inputs_observed")


@pytest.mark.parametrize("mutate", [
    lambda x:x["runtime"].update(source_commit="0"*40),
    lambda x:x["runtime"].update(run_id="unverified"),
    lambda x:x["runtime"].update(exit_code=125),
    lambda x:x["runtime"].update(economy_status="ABSTAIN_BUILD_FAILED"),
    lambda x:x["runtime"].update(heldout32_entities_read=True),
    lambda x:x["runtime"].update(host_diff_verified=True),
    lambda x:x["runtime"].update(pytest_cases=0),
    lambda x:x["runtime"].update(generation_read_only=False),
    lambda x:x["source"]["generation"].update(read_only=False),
    lambda x:x["source"]["metadata"].update(metadata_frozen_selection_sha256="0"*64),
    lambda x:x["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["vcrs"].update(before_id_rows=21919),
    lambda x:x["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["ships"].update(same_id_owner_changed_not_host_capture=6892),
    lambda x:x["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(same_id_fresh_own_center_stable_units_changed_joint_not_causal=138440),
    lambda x:counts(x).update(before_turn_exact=21917),
    lambda x:counts(x).update(after_exact_turn_and_typed_participants=22415),
    lambda x:counts(x).update(after_exact_turn_and_full_typed_participants_owners=22414),
    lambda x:counts(x).update(after_two_ownerids_typed=True),
    lambda x:counts(x).update(qualified_archive_pairs=8551),
    lambda x:counts(x).update(raw_private_battle_id=987654321),
    lambda x:counts(x).pop(FIELDS[0]),
    lambda x:x.update(private_raw_orders="secret"),
])
def test_all_old_marginals_runtime_flags_joint_conservation_and_raw_injection_abstain(mutate):
    v5,v6,vcr = payloads()
    mutate(vcr)
    with pytest.raises(EvidenceReviewAbstain):
        readout_vcr_temporal(v5,v6,vcr)


def test_poisoned_reference_does_not_bypass_old_frozen_gates():
    v5,v6,vcr = payloads()
    v6["runtime"]["exit_code"] = 2
    with pytest.raises(EvidenceReviewAbstain):
        readout_vcr_temporal(v5,v6,vcr)


def test_cli_runs_under_isolated_system_python_and_refuses_overwrite(tmp_path):
    output = tmp_path / "safe-scorecard.json"
    cmd = [sys.executable, "-I", "-S", str(CLI),
           "--v5", str(V5), "--v6", str(V6), "--vcr", str(VCR),
           "--output", str(output)]
    result = subprocess.run(cmd,cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(output.read_text()) == json.loads(SCORE.read_text())
    assert "host_diff_verified=false" in result.stdout
    second = subprocess.run(cmd,cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert second.returncode == 2
    assert second.stdout.strip() == "ABSTAIN_OUTPUT_EXISTS_OR_INPUT_OVERWRITE"


def test_cli_rejects_untrusted_private_input_and_prints_no_raw_identifier(tmp_path):
    v5,v6,vcr = payloads()
    counts(vcr)["secret_member_987654321"] = 7
    source = tmp_path / "malicious.json"
    source.write_text(json.dumps(vcr))
    dest = tmp_path / "should-not-exist.json"
    result = subprocess.run(
        [sys.executable,"-I","-S",str(CLI),
         "--v5",str(V5),"--v6",str(V6),"--vcr",str(source),"--output",str(dest)],
        cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert result.returncode == 2
    assert result.stdout.strip() == "ABSTAIN_VCR_TEMPORAL_READOUT"
    assert "987654321" not in result.stdout + result.stderr
    assert not dest.exists()
