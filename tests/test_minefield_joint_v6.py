"""V6 tests use synthetic rows and sanitized historical v5 counts only."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest

from planets_lab.corpus.nonplanet_archive_pair_readiness import profile_source_identity_pairs
from tools.diagnostics.validate_minefield_joint_v6 import JOINT, validate_joint
from planets_lab.corpus.nonplanet_v5_evidence_review import EvidenceReviewAbstain

ROOT=Path(__file__).resolve().parents[1]
V5=ROOT/"tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"

def row(i, *, turn, units, owner=1, x=7, y=8):
    return {"id":i,"ownerid":owner,"infoturn":turn,"units":units,"x":x,"y":y}

def profile(b,a):
    return profile_source_identity_pairs(
        {"minefields":b}, {"minefields":a},
        observer=1,before_turn=10,after_turn=11)["minefields"]

def test_joint_partitions_increases_decreases_and_unchanged():
    before=[row(1,turn=10,units=100),row(2,turn=10,units=100),
            row(3,turn=10,units=100),row(4,turn=9,units=100),
            row(5,turn=10,units=100),row(6,turn=10,units=100)]
    after=[row(1,turn=11,units=110),row(2,turn=11,units=90),
           row(3,turn=11,units=100),row(4,turn=11,units=90),
           row(5,turn=11,units=90,x=9),row(6,turn=11,units=90,owner=2)]
    r=profile(before,after)
    assert r[JOINT[0]]==3
    assert r[JOINT[1]]==1
    assert r[JOINT[2]]==1
    assert r[JOINT[3]]==1
    assert r[JOINT[4]]==2
    assert r["same_id_owner_center_stable_units_changed_not_causal"]==4
    assert r["same_id_current_own_verified_both_archives"]==4

@pytest.mark.parametrize("edit",[
    lambda x: x[0].update(infoturn=9),
    lambda x: x[0].update(units=True),
    lambda x: x[0].update(x=9),
    lambda x: x[0].update(ownerid=2),
    lambda x: x[0].update(id=True),
])
def test_invalid_freshness_units_coordinates_owner_id_cannot_count(edit):
    before=[row(1,turn=10,units=100)]
    after=[row(1,turn=11,units=90)]
    edit(before)
    r=profile(before,after)
    assert r.get(JOINT[4],0)==0
    if type(before[0]["id"]) is not int:
        assert r=={"ABSTAIN_MALFORMED_OR_DUPLICATE_ENTITY_ID":1}

def fixture():
    p=json.loads(V5.read_text())
    mine=p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]
    # A mathematically consistent synthetic extension of real v5 margins,
    # deliberately NOT the actual yet-unobserved v6 empirical count.
    mine.update(dict(zip(JOINT,(100,30,40,30,70))))
    return p

def test_synthetic_extension_accepts_only_conserved_partition():
    assert validate_joint(fixture())[JOINT[4]]==70

@pytest.mark.parametrize("key,val",[
    (JOINT[0],99),(JOINT[1],31),(JOINT[4],71),
    (JOINT[2],True),(JOINT[3],-1)
])
def test_synthetic_tampered_joint_abstains(key,val):
    p=fixture()
    p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"][key]=val
    with pytest.raises(EvidenceReviewAbstain):
        validate_joint(p)

def test_wrong_frozen_population_and_v5_marginal_abstain():
    p=fixture()
    p["metadata"]["metadata_frozen_selection_sha256"]="0"*64
    with pytest.raises(EvidenceReviewAbstain):
        validate_joint(p)
    p=fixture()
    p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]["same_id_current_own_verified_both_archives"]+=1
    with pytest.raises(EvidenceReviewAbstain):
        validate_joint(p)

def test_runner_uses_exact_generic_publisher_and_fixed_frozen_cohort():
    run=(ROOT/"tools/run-public100-baseline68-mine-joint-v6.sh").read_text()
    launch=(ROOT/"tools/run-public100-baseline68-mine-joint-v6-with-evidence.sh").read_text()
    assert "tools/run-with-runtime-evidence.sh" in launch
    assert "--include artifacts/corpus/public100-baseline68-mine-joint-v6/m2-deep-coverage.json" in launch
    assert "private-local" not in launch
    assert "--pairs-per-game 128" in run
    assert "--expected-selection-sha256 4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659" in run
    assert "public100_baseline68_cohort_guard_v3.py" in run
    assert "validate_minefield_joint_v6.py" in run
    for name in ("tools/run-public100-baseline68-mine-joint-v6.sh",
                 "tools/run-public100-baseline68-mine-joint-v6-with-evidence.sh"):
        assert subprocess.run(["bash","-n",str(ROOT/name)],capture_output=True).returncode==0
