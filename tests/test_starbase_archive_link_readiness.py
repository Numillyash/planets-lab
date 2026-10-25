"""Synthetic and adversarial starbase link provenance, no private corpus."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.m2_economy_coverage import Member, analyze_corpus_coverage, census_members
from planets_lab.corpus.starbase_archive_link_readiness import (
    profile_starbase_archive_link_pair,
)
from tools.diagnostics.validate_starbase_archive_link_v1 import (
    SCHEMA_KEYS, validate_links,
)

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"

def p(*,turn=10,observer=1,base_owner=None,planet_owner=None,
      base_infoturn=None,anchor=8,planet_infoturn=None):
    base={"id":77,"planetid":anchor}
    if base_owner is not None:
        base["ownerid"]=base_owner
    if base_infoturn is not None:
        base["infoturn"]=base_infoturn
    planet={"id":anchor,"ownerid":observer if planet_owner is None else planet_owner,
            "infoturn":turn if planet_infoturn is None else planet_infoturn}
    return {"game":{"id":99,"turn":turn},"player":{"id":observer},
            "starbases":[base],"planets":[planet],
            "ships":[],"minefields":[],"vcrs":[],"ionstorms":[],"relations":[]}

def profile(b,a):
    return profile_starbase_archive_link_pair(b,a,observer=1,before_turn=10,after_turn=11)

def test_planet_current_owner_does_not_pretend_base_is_fresh():
    b,a=p(),p(turn=11)
    r=profile(b,a)
    assert r["same_id_starbase_observer_occurrences"]==1
    assert r["same_id_planet_linked_current_own_both_archives"]==1
    assert r["same_id_planet_linked_base_infoturn_missing_any"]==1
    assert r["same_id_planet_linked_base_current_both_archives"]==0
    assert not any("planetid" in k or "ownerid" in k for k in r)
    b["starbases"][0]["infoturn"]=10
    a["starbases"][0]["infoturn"]=11
    r=profile(b,a)
    assert r["same_id_planet_linked_base_current_both_archives"]==1
    assert r["same_id_planet_linked_base_infoturn_missing_any"]==0

def test_stale_or_invalid_base_freshness_separate_from_owner_link():
    b,a=p(base_infoturn=9),p(turn=11,base_infoturn=11)
    r=profile(b,a)
    assert r["same_id_planet_linked_current_own_both_archives"]==1
    assert r["same_id_planet_linked_base_infoturn_stale_or_invalid_any"]==1
    assert r["same_id_planet_linked_base_current_both_archives"]==0

@pytest.mark.parametrize("mutate,abstain", [
    (lambda b,a: a["starbases"][0].update(planetid=9), "ABSTAIN_SAME_ID_ANCHOR_MISSING_OR_CHANGED"),
    (lambda b,a: a["planets"][0].update(infoturn=10), "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED"),
    (lambda b,a: a["planets"][0].update(ownerid=2), "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED"),
    (lambda b,a: a["starbases"][0].update(ownerid=2), "ABSTAIN_SAME_ID_BASE_OWNER_CONFLICT"),
    (lambda b,a: a["starbases"][0].update(planet_id=9), "ABSTAIN_SAME_ID_ANCHOR_MISSING_OR_CHANGED"),
    (lambda b,a: a["starbases"].append({"id":78,"planetid":8}), "ABSTAIN_SAME_ID_ANCHOR_AMBIGUOUS"),
    (lambda b,a: a["planets"].append({"id":8,"ownerid":1,"infoturn":11}), "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED"),
])
def test_link_ambiguity_ownership_provenance_abstains(mutate,abstain):
    b,a=p(),p(turn=11)
    mutate(b,a)
    result=profile(b,a)
    assert result[abstain]==1
    assert result["same_id_planet_linked_current_own_both_archives"]==0
    assert sum(result[k] for k in result if k.startswith("ABSTAIN_SAME_ID_"))==1

@pytest.mark.parametrize("bad", [None,True,0,-1,"77",1.5])
def test_malformed_base_id_invalidates_entire_side_atomically(bad):
    b,a=p(),p(turn=11)
    a["starbases"][0]["id"]=bad
    assert profile(b,a)=={"ABSTAIN_STARBASE_SECTION_DUPLICATE_OR_INVALID_ID":1}

def test_duplicate_base_id_invalidates_whole_pair_and_missing_sections_abstain():
    b,a=p(),p(turn=11)
    a["starbases"].append(copy.deepcopy(a["starbases"][0]))
    assert profile(b,a)=={"ABSTAIN_STARBASE_SECTION_DUPLICATE_OR_INVALID_ID":1}
    a=p(turn=11)
    a["planets"]=None
    assert profile(b,a)=={"ABSTAIN_REQUIRED_ARCHIVE_SECTION_NOT_LIST":1}

def test_invalid_turn_or_observer_never_qualifies():
    b,a=p(),p(turn=11)
    for observer,before,after in [(True,10,11),(1,0,11),(1,10,12)]:
        with pytest.raises(ValueError):
            profile_starbase_archive_link_pair(b,a,observer=observer,
                                              before_turn=before,after_turn=after)

class SourceConn:
    def __init__(self): self.calls=0
    def execute(self,sql):
        assert "FROM source_members" in sql
        return self
    def fetchmany(self,n):
        self.calls+=1
        return [(1,99,1,10,10),(2,99,1,11,11)] if self.calls==1 else []

def test_opt_in_integration_with_frozen_sample_preserves_default_source_schema():
    source={1:p(base_infoturn=10),2:p(turn=11,base_infoturn=11)}
    members=[Member(1,99,1,10,10),Member(2,99,1,11,11)]
    meta,pairs=census_members(members,max_games=1,pairs_per_game=1,allowed_games={99})
    assert len(pairs)==1
    opts=dict(max_games=1,pairs_per_game=1,allowed_games={99},
              expected_frozen_selection_sha256=meta["metadata_frozen_selection_sha256"],
              reconstruct=lambda mid:copy.deepcopy(source[mid]))
    original=analyze_corpus_coverage(SourceConn(),**opts)
    assert "starbase_planet_archive_link_not_host_phase" not in original["sample"]
    linked=analyze_corpus_coverage(SourceConn(),starbase_planet_link_readiness=True,**opts)
    counts=linked["sample"]["starbase_planet_archive_link_not_host_phase"]
    assert counts["qualified_source_list_pairs"]==1
    assert counts["same_id_starbase_observer_occurrences"]==1
    assert counts["same_id_planet_linked_base_current_both_archives"]==1
    assert linked["metadata"]==original["metadata"]
    copy_sample=dict(linked["sample"]);copy_sample.pop("starbase_planet_archive_link_not_host_phase")
    assert copy_sample==original["sample"]

def synthetic_full_aggregate():
    report=json.loads(BASE.read_text())
    report["evidence_limits"].update({
        "raw_trn_is_submitted_turn_orders":False,
        "NuHost_ship_build_cost_verified":False,
        "NuHost_economic_formula_verified":False,
    })
    links=dict.fromkeys(SCHEMA_KEYS,0)
    links.update({
        "qualified_source_list_pairs":8550,
        "same_id_starbase_observer_occurrences":346222,
        "same_id_planet_linked_current_own_both_archives":7,
        "same_id_planet_linked_base_current_both_archives":2,
        "same_id_planet_linked_base_infoturn_missing_any":4,
        "same_id_planet_linked_base_infoturn_stale_or_invalid_any":1,
        "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED":346215,
    })
    report["sample"]["starbase_planet_archive_link_not_host_phase"]=links
    return report

def isolated_cli(*args,cwd):
    script=ROOT/"tools/diagnostics/validate_starbase_archive_link_v1.py"
    return subprocess.run([sys.executable,"-I","-S",str(script),*args],
                          cwd=cwd,text=True,capture_output=True,timeout=20)

def test_isolated_host_stdlib_validator_with_synthetic_only_baseline(tmp_path):
    selftest=isolated_cli("--self-test",cwd=tmp_path)
    assert selftest.returncode==0,selftest.stdout+selftest.stderr
    source=tmp_path/"safe.json";source.write_text(json.dumps(synthetic_full_aggregate()))
    outcome=isolated_cli("--input",str(source),cwd=tmp_path)
    assert outcome.returncode==0,outcome.stdout+outcome.stderr
    assert "PASS_STARBASE_PLANET_LINK_OBSERVATIONAL_ONLY" in outcome.stdout
    assert "linked_own_archive_occurrences=7" in outcome.stdout

def test_standalone_source_validator_rejects_tamper_without_raw_leak(tmp_path):
    report=synthetic_full_aggregate()
    report["sample"]["starbase_planet_archive_link_not_host_phase"]["same_id_planet_linked_base_current_both_archives"]=8
    source=tmp_path/"malicious.json"
    report["sample"]["starbase_planet_archive_link_not_host_phase"]["raw_planet_private"]=987654321
    source.write_text(json.dumps(report))
    result=isolated_cli("--input",str(source),cwd=tmp_path)
    assert result.returncode==2
    assert result.stdout.strip()=="ABSTAIN_STARBASE_LINK_SOURCE"
    assert "987654321" not in result.stdout+result.stderr

def test_runner_pins_cohort_and_uses_exact_generic_evidence_wrapper():
    launcher=(ROOT/"tools/run-public100-baseline68-starbase-link-v1-with-evidence.sh").read_text()
    runner=(ROOT/"tools/run-public100-baseline68-starbase-link-v1.sh").read_text()
    assert "tools/run-with-runtime-evidence.sh" in launcher
    assert "private-local" not in launcher
    assert "--starbase-linked-provenance" in runner
    assert "--pairs-per-game 128" in runner
    assert "--expected-selection-sha256 4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659" in runner
    assert "public100_baseline68_cohort_guard_v3.py" in runner
    assert "validate_starbase_archive_link_v1.py" in runner
    assert runner.index("host_starbase_link_validator_self_test") < runner.index("deep_m2_100_metadata_68_baseline")
    for script in ("tools/run-public100-baseline68-starbase-link-v1.sh",
                   "tools/run-public100-baseline68-starbase-link-v1-with-evidence.sh"):
        assert subprocess.run(["bash","-n",str(ROOT/script)],capture_output=True).returncode==0
