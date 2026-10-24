"""Adversarial synthetic source qualification, no private snapshots or NuHost orders."""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess

import pytest

from planets_lab.corpus.m2_economy_coverage import (
    Member, analyze_corpus_coverage, census_members,
)
from planets_lab.corpus.nonplanet_archive_pair_readiness import (
    SECTIONS, profile_source_identity_pairs,
)
from tools.diagnostics.m2_validate_corpus_aggregate_evidence_v1 import (
    _aggregate_only,
)


def record(id, owner=1, infoturn=10, *, x=4, y=7, units=100):
    return dict(id=id, ownerid=owner, infoturn=infoturn,
                x=x, y=y, units=units)


def payload(*, game=99, player=1, turn=10):
    return dict(
        game=dict(id=game, turn=turn),
        player=dict(id=player),
        minefields=[record(5, infoturn=turn)],
        ships=[record(6, infoturn=turn)],
        starbases=[], vcrs=[], ionstorms=[],
        planets=[], relations=[],
    )


def profile(before, after):
    return profile_source_identity_pairs(
        before, after, observer=1, before_turn=10, after_turn=11,
    )


def test_exact_id_and_fresh_self_owner_are_separate_from_host_causality():
    before, after = payload(), payload(turn=11)
    before["minefields"] = [record(4, owner=2, infoturn=9, units=400),
                            record(5, units=100)]
    after["minefields"] = [record(4, owner=2, infoturn=9, units=350),
                           record(5, infoturn=11, units=95),
                           record(8, infoturn=11)]
    r = profile(before, after)["minefields"]
    assert r["qualified_identity_list_pair"] == 1
    assert r["before_id_rows"] == 2
    assert r["after_id_rows"] == 3
    assert r["same_id_seen_in_both_archives"] == 2
    assert r["id_only_after_archive_not_host_construction"] == 1
    assert r["id_only_before_archive_not_host_destruction"] == 0
    assert r["same_id_owner_unchanged"] == 2
    assert r["same_id_current_own_verified_both_archives"] == 1
    assert r["same_id_nonnegative_integer_units_both"] == 2
    assert r["same_id_integer_units_changed_not_host_attribution"] == 2
    assert r["same_id_owner_center_stable_units_changed_not_causal"] == 2
    assert set(profile(before, after)) == set(SECTIONS)


def test_duplicate_ids_invalidate_entire_section_atomically():
    before, after = payload(), payload(turn=11)
    after["minefields"].append(record(5, infoturn=11))
    r = profile(before, after)
    assert r["minefields"] == {"ABSTAIN_MALFORMED_OR_DUPLICATE_ENTITY_ID": 1}
    assert r["ships"]["qualified_identity_list_pair"] == 1
    assert r["ships"]["same_id_current_own_verified_both_archives"] == 1


def test_bad_id_formats_and_nonlist_abstain_without_partial_counts():
    for bad in (True, None, -1, 0, 1.5, "5"):
        before, after = payload(), payload(turn=11)
        before["minefields"] = [dict(id=bad, units=10)]
        assert profile(before, after)["minefields"] == {
            "ABSTAIN_MALFORMED_OR_DUPLICATE_ENTITY_ID": 1
        }
    before, after = payload(), payload(turn=11)
    before["ships"] = {"not": "list"}
    assert profile(before, after)["ships"] == {
        "ABSTAIN_MISSING_SECTION_LIST": 1
    }


def test_missing_or_stale_infoturn_refuses_current_own_even_same_id_and_owner():
    before, after = payload(), payload(turn=11)
    before["ships"][0].pop("infoturn")
    after["minefields"][0]["infoturn"] = 10
    r = profile(before, after)
    assert r["ships"]["same_id_seen_in_both_archives"] == 1
    assert r["ships"]["same_id_current_own_verified_both_archives"] == 0
    assert r["ships"]["same_id_owner_own_but_infoturn_missing_or_stale"] == 1
    assert r["minefields"]["same_id_current_own_verified_both_archives"] == 0
    assert r["minefields"]["same_id_owner_own_but_infoturn_missing_or_stale"] == 1


def test_mine_source_unknown_units_or_position_cannot_promote_inferences():
    before, after = payload(), payload(turn=11)
    before["minefields"][0]["units"] = True
    r = profile(before, after)["minefields"]
    assert r["same_id_nonnegative_integer_units_both"] == 0
    assert r["same_id_integer_units_changed_not_host_attribution"] == 0
    before["minefields"][0]["units"] = 100
    after["minefields"][0]["x"] = 6
    after["minefields"][0]["units"] = 99
    r = profile(before, after)["minefields"]
    assert r["same_id_integer_units_changed_not_host_attribution"] == 1
    assert r["same_id_owner_center_stable_units_changed_not_causal"] == 0


def test_missing_owner_and_stable_own_id_not_mislabelled_host_capture():
    before, after = payload(), payload(turn=11)
    before["ships"][0]["ownerid"] = None
    r = profile(before, after)["ships"]
    assert r["same_id_owner_untyped_abstain"] == 1
    assert r["same_id_owner_changed_not_host_capture"] == 0
    before["ships"][0]["ownerid"] = 2
    r = profile(before, after)["ships"]
    assert r["same_id_owner_changed_not_host_capture"] == 1
    assert r["same_id_current_own_verified_both_archives"] == 0


def test_pair_profiles_export_only_numeric_allowlisted_aggregate_no_raw_entity():
    before, after = payload(), payload(turn=11)
    before["minefields"].append(dict(id=90318,ownerid=8,units=100))
    after["minefields"].append(dict(id=90318,ownerid=8,units=99))
    result = profile(before, after)
    _aggregate_only(result, section="nonplanet_source_identity")
    assert "90318" not in str(result)
    assert "ownerid" not in str(result)
    assert all(type(v) is int and v >= 0 for d in result.values() for v in d.values())
    with pytest.raises(ValueError, match="non-count value"):
        _aggregate_only({"minefields": {"unsafe_game_id": "90318"}}, section="source")


class SourceConn:
    def __init__(self):
        self.reads = 0
    def execute(self, sql):
        assert "FROM source_members" in sql
        return self
    def fetchmany(self, n):
        self.reads += 1
        return [(1, 99, 1, 10, 10), (2, 99, 1, 11, 11)] if self.reads == 1 else []


def test_analyzer_accepts_exact_population_digest_and_preserves_abstain_boundaries():
    observed=[]
    before, after = payload(), payload(turn=11)
    after["minefields"][0]["units"] = 95
    source={1: before, 2: after}
    def restore(member):
        observed.append(member)
        return copy.deepcopy(source[member])
    _, frozen=census_members([Member(1,99,1,10,10),Member(2,99,1,11,11)],
                             max_games=1, pairs_per_game=1, allowed_games={99})
    assert len(frozen)==1
    meta,_=census_members([Member(1,99,1,10,10),Member(2,99,1,11,11)],
                          max_games=1,pairs_per_game=1,allowed_games={99})
    r=analyze_corpus_coverage(
        SourceConn(), max_games=1, pairs_per_game=1,
        reconstruct=restore, allowed_games={99},
        expected_frozen_selection_sha256=meta["metadata_frozen_selection_sha256"])
    assert observed == [1,2]
    x=r["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]
    assert x["minefields"]["same_id_owner_center_stable_units_changed_not_causal"]==1
    assert x["ships"]["same_id_current_own_verified_both_archives"]==1
    assert x["vcrs"]["empty_lists_both"]==1
    assert r["evidence_limits"]["archive_identity_or_mine_unit_changes_prove_host_phase"] is False


def test_selection_mismatch_refuses_before_any_member_reconstruction():
    retrieved=[]
    with pytest.raises(ValueError, match="FROZEN_OBSERVATIONAL_SOURCE_SELECTION_CHANGED"):
        analyze_corpus_coverage(
            SourceConn(), max_games=1,pairs_per_game=1,allowed_games={99},
            reconstruct=lambda member: retrieved.append(member),
            expected_frozen_selection_sha256="0"*64)
    assert retrieved==[]


def test_script_and_publisher_scope():
    root=Path(__file__).resolve().parents[1]
    for name in (
        "tools/run-public100-baseline68-identity-v5.sh",
        "tools/run-public100-baseline68-identity-v5-with-evidence.sh",
    ):
        r=subprocess.run(["bash","-n",str(root/name)],capture_output=True,
                         check=False)
        assert r.returncode==0,name
    launch=(root/"tools/run-public100-baseline68-identity-v5-with-evidence.sh").read_text()
    runner=(root/"tools/run-public100-baseline68-identity-v5.sh").read_text()
    assert "tools/run-with-runtime-evidence.sh" in launch
    assert "private-local" not in launch
    assert "--expected-selection-sha256 4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659" in runner
    assert "--pairs-per-game 128" in runner
    assert "public100_baseline68_cohort_guard_v3.py" in runner
    assert "public100-baseline68-identity-v5" in launch
    assert "m2_validate_corpus_aggregate_evidence_v1.py" in runner
