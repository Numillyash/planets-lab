"""M2 surface residual context: no causal cargo/base claims, baseline-only."""
from __future__ import annotations

from copy import deepcopy
import json

from planets_lab.corpus.m2_surface_residual_context import (
    profile_surface_residual_context,
)
from planets_lab.corpus.m2_economy_coverage import (
    Pair, profile_pair, analyze_corpus_coverage,
)


def snapshots():
    def one(turn, d=20, ground=60, cargo=10):
        return {
            "game": {"id": 777001, "turn": turn},
            "player": {"id": 1, "raceid": 3},
            "planets": [{
                "id": 13, "ownerid": 1, "infoturn": turn,
                "x": 100, "y": 200, "mines": 5,
                "duranium": d, "groundduranium": ground,
                "densityduranium": 40,
                "neutronium": 0, "groundneutronium": 50, "densityneutronium": 40,
                "tritanium": 0, "groundtritanium": 50, "densitytritanium": 40,
                "molybdenum": 0, "groundmolybdenum": 50, "densitymolybdenum": 40,
                "factories": 3, "defense": 2,
                "colonisttaxrate": 0, "nativetaxrate": 0,
            }],
            "ships": [{
                "id": 9, "ownerid": 1, "infoturn": turn,
                "x": 100, "y": 200, "duranium": cargo,
            }],
            "starbases": [{
                "planetid": 13, "id": 77, "ownerid": 1, "infoturn": turn,
                "hulltechlevel": 3, "enginetechlevel": 2,
                "beamtechlevel": 2, "torptechlevel": 2,
            }],
        }
    return one(10), one(11, d=29, cargo=3)


def profile(a, b):
    return profile_pair(a, b, Pair(777001, 1, 11, 1, 2))["surface_residual_context"]


def test_surface_residual_ship_cargo_opposite_is_candidate_not_order_proof():
    before, after = snapshots()
    o = profile(before, after)
    row = o["per_mineral_categories"]["duranium"]
    assert row == {"ground_exact_surface_residual": 1}
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    for k in (
        "planet_coordinates_qualified", "owner_ship_observed_at_site_before",
        "owner_ship_observed_at_site_after", "owner_ship_observed_at_site_both",
        "same_owner_ship_id_observed_at_site_both",
        "same_ship_cargo_pair_qualified",
        "one_ship_opposite_cargo_delta_candidate",
        "opposite_cargo_ship_both_freshness_explicit",
        "owner_starbase_explicit_at_planet_before",
        "owner_starbase_explicit_at_planet_after",
        "owner_starbase_explicit_at_planet_both",
        "observed_starbase_tech_unchanged",
        "structure_and_tax_controls_qualified",
        "structure_and_tax_controls_unchanged",
        "surface_residual_positive",
    ):
        assert c[k] == 1, k
    assert o["per_mineral_category_surface_residual_magnitude_buckets"][
        "duranium"
    ]["ground_exact_surface_residual"] == {"6_to_20": 1}
    exported = json.dumps(o)
    for value in ("777001", '"planetid"', '"id"', '"x"', '"y"'):
        assert value not in exported


def test_mismatched_ship_cargo_not_promoted_as_matching_transfer():
    a, b = snapshots()
    b["ships"][0]["duranium"] = 8
    c = profile(a, b)["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert c["same_ship_cargo_pair_qualified"] == 1
    assert "one_ship_opposite_cargo_delta_candidate" not in c


def test_missing_ship_freshness_keeps_separate_low_confidence_counter():
    a, b = snapshots()
    del a["ships"][0]["infoturn"]
    del b["ships"][0]["infoturn"]
    o = profile(a, b)
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert c["one_ship_opposite_cargo_delta_candidate"] == 1
    assert c["opposite_cargo_ship_freshness_unverified"] == 1
    assert "opposite_cargo_ship_both_freshness_explicit" not in c
    assert o["source_quality"]["OWNER_SHIP_INFOTURN_UNAVAILABLE"] == 2


def test_stale_owner_ship_and_ownerless_starbase_not_assumed_valid():
    a, b = snapshots()
    a["ships"][0]["infoturn"] = 8
    b["starbases"][0].pop("ownerid")
    o = profile(a, b)
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "one_ship_opposite_cargo_delta_candidate" not in c
    assert o["source_quality"]["ABSTAIN_OWNER_SHIP_STALE"] == 1
    assert o["source_quality"]["ABSTAIN_STARBASE_OWNER_MISSING"] == 1
    assert "owner_starbase_explicit_at_planet_both" not in c


def test_different_planetid_is_not_same_starbase_even_if_base_id_matches():
    a, b = snapshots()
    a["starbases"][0]["planetid"] = 14
    b["starbases"][0]["planetid"] = 14
    o = profile(a, b)
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "owner_starbase_explicit_at_planet_before" not in c
    assert "owner_starbase_explicit_at_planet_both" not in c


def test_duplicate_ship_id_ambiguous_and_absent_coordinates_abstain():
    a, b = snapshots()
    a["ships"].append(deepcopy(a["ships"][0]))
    o = profile(a, b)
    assert o["source_quality"]["ABSTAIN_DUPLICATE_OWNER_SHIP_ID"] == 1
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "one_ship_opposite_cargo_delta_candidate" not in c
    del a["planets"][0]["x"]
    o = profile(a, b)
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert c["ABSTAIN_PLANET_COORDS_MISSING"] == 1
    assert "one_ship_opposite_cargo_delta_candidate" not in c


def test_no_owner_ship_observed_is_not_proof_of_no_ship_orders():
    a, b = snapshots()
    a["ships"] = []
    b["ships"] = []
    o = profile(a, b)
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert c["NO_OWNER_SHIP_OBSERVED_AT_SITE_NOT_ABSENCE_PROOF"] == 1
    assert "one_ship_opposite_cargo_delta_candidate" not in c


def test_explicit_starbase_tech_change_is_observation_not_build_order():
    a, b = snapshots()
    b["starbases"][0]["enginetechlevel"] = 3
    o = profile(a, b)
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert c["observed_starbase_tech_changed"] == 1
    assert "observed_starbase_tech_unchanged" not in c


def test_both_exact_and_ground_mismatch_are_separate_categories():
    a, b = snapshots()
    b["planets"][0]["duranium"] = 22
    o = profile(a, b)
    assert o["per_mineral_categories"]["duranium"] == {"both_exact": 1}
    b["planets"][0]["groundduranium"] = 55
    o = profile(a, b)
    assert o["per_mineral_categories"]["duranium"] == {
        "surface_exact_ground_residual": 1
    }
    b["planets"][0]["duranium"] = 29
    o = profile(a, b)
    assert o["per_mineral_categories"]["duranium"] == {"neither_exact": 1}


def test_end_to_end_same_sample_context_and_mineral_totals_align():
    class Connection:
        visited = False
        def execute(self, query):
            assert "source_members" in query
            return self
        def fetchmany(self, count):
            if self.visited:
                return []
            self.visited = True
            return [(1, 777001, 1, 10, 10), (2, 777001, 1, 11, 11)]
    a, b = snapshots()
    result = analyze_corpus_coverage(
        Connection(), max_games=1, pairs_per_game=1,
        allowed_games={777001}, reconstruct=lambda n: {1: a, 2: b}[n]
    )
    out = result["sample"]["surface_residual_context_not_host_verified"]
    assert out["per_mineral_residual_classes"]["duranium"] == {
        "ground_exact_surface_residual": 1,
    }
    assert out["game_cluster_residual_count_buckets"][
        "ground_exact_surface_residual"
    ] == {"2_to_5": 1}  # This game also has 3 residuals in other minerals.
    cluster = out["game_cluster_surface_context_count_buckets"]
    assert cluster["owner_ship_observed_at_site_both"] == {"2_to_5": 1}
    assert cluster["one_ship_opposite_cargo_delta_candidate"] == {"1": 1}
    assert cluster["ownerless_base_planetlinked_both_not_owner_proof"] == {"0": 1}
    assert result["sample"]["conditional_mineral_mass_balance_not_host_verified"][
        "per_mineral"
    ]["duranium"]["candidate_default_mining_qualified"] == 1
    assert result["evidence_limits"][
        "same_site_owner_ship_observation_proves_cargo_transfer"
    ] is False
    assert result["evidence_limits"][
        "no_owner_ship_observed_excludes_ship_actions"
    ] is False


def test_nonowner_or_stale_planet_does_not_generate_context():
    a, b = snapshots()
    a["planets"][0]["infoturn"] = 9
    o = profile(a, b)
    assert o["per_mineral_categories"] == {}
    assert o["per_mineral_category_covariates"] == {}



def test_missing_ship_array_abstains_instead_of_claiming_no_ship():
    a, b = snapshots()
    del a["ships"]
    o = profile(a, b)
    c = o["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert c["planet_coordinates_qualified"] == 1
    assert c["ABSTAIN_SHIP_SECTION_MISSING_ONE_OR_BOTH"] == 1
    assert "owner_ship_section_pair_qualified" not in c
    assert "NO_OWNER_SHIP_OBSERVED_AT_SITE_NOT_ABSENCE_PROOF" not in c
    assert o["source_quality"]["ABSTAIN_SHIP_ARRAY_MISSING"] == 1



def test_ownerless_starbase_is_planet_linked_not_owner_verified():
    a, b = snapshots()
    for payload in (a, b):
        del payload["starbases"][0]["ownerid"]
    observed = profile(a, b)
    ctx = observed["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "owner_starbase_explicit_at_planet_both" not in ctx
    assert ctx["ownerless_base_planetlinked_before_not_owner_proof"] == 1
    assert ctx["ownerless_base_planetlinked_after_not_owner_proof"] == 1
    assert ctx["ownerless_base_planetlinked_both_not_owner_proof"] == 1
    assert ctx["planetlinked_base_both_any_owner_provenance"] == 1
    assert ctx["ownerless_planetlinked_tech_unchanged_observed"] == 1
    assert observed["source_quality"]["ABSTAIN_STARBASE_OWNER_MISSING"] == 2
    assert observed["source_quality"][
        "OWNERLESS_BASE_PLANETLINK_CANDIDATE_NOT_OWNER_VERIFIED"
    ] == 2
    b["starbases"][0]["enginetechlevel"] = 5
    observed = profile(a, b)
    ctx = observed["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert ctx["ownerless_planetlinked_tech_changed_observed"] == 1


def test_ownerless_base_unowned_planet_or_conflicting_explicit_owner_abstains():
    a, b = snapshots()
    for payload in (a, b):
        payload["starbases"][0]["planetid"] = 14
        del payload["starbases"][0]["ownerid"]
    observed = profile(a, b)
    ctx = observed["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "ownerless_base_planetlinked_both_not_owner_proof" not in ctx
    assert observed["source_quality"][
        "ABSTAIN_OWNERLESS_BASE_PLANET_NOT_OWNER_CURRENT"
    ] == 2

    a, b = snapshots()
    for payload in (a, b):
        payload["starbases"][0]["ownerid"] = 2
    observed = profile(a, b)
    ctx = observed["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "owner_starbase_explicit_at_planet_both" not in ctx
    assert "planetlinked_base_both_any_owner_provenance" not in ctx
    assert observed["source_quality"][
        "ABSTAIN_CONFLICTING_EXPLICIT_BASE_OWNER"
    ] == 2


def test_mixed_starbase_owner_provenance_and_duplicate_planet_id():
    a, b = snapshots()
    del a["starbases"][0]["ownerid"]
    observed = profile(a, b)
    ctx = observed["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert ctx["planetlinked_base_both_any_owner_provenance"] == 1
    assert ctx["planetlinked_base_owner_provenance_changed"] == 1
    assert "ownerless_base_planetlinked_both_not_owner_proof" not in ctx
    assert "owner_starbase_explicit_at_planet_both" not in ctx
    # Ambiguous duplicate with conflicting ownership excludes BOTH.
    b["starbases"].append({
        "planetid": 13, "ownerid": 2, "infoturn": 11,
    })
    observed = profile(a, b)
    ctx = observed["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "planetlinked_base_both_any_owner_provenance" not in ctx
    assert observed["source_quality"][
        "ABSTAIN_DUPLICATE_STARBASE_PLANETID"
    ] == 1


def test_multi_ship_exact_opposite_sum_not_a_single_transfer_order():
    a, b = snapshots()
    a["ships"] = [
        {**a["ships"][0], "id": 31, "duranium": 9},
        {**a["ships"][0], "id": 32, "duranium": 8},
    ]
    b["ships"] = [
        {**b["ships"][0], "id": 31, "duranium": 6},
        {**b["ships"][0], "id": 32, "duranium": 4},
    ]
    ctx = profile(a, b)["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "one_ship_opposite_cargo_delta_candidate" not in ctx
    assert ctx["multiple_co_site_ship_ids_all_cargo_qualified"] == 1
    assert ctx["multiple_ship_cargo_sum_opposite_candidate_not_order"] == 1
    assert ctx["same_site_identical_ship_set_all_cargo_qualified"] == 1
    del b["ships"][1]["duranium"]
    ctx = profile(a, b)["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "multiple_ship_cargo_sum_opposite_candidate_not_order" not in ctx
    assert ctx["ABSTAIN_WHOLE_SITE_CARGO_MISSING"] == 1
    # A ship arrival prevents "closed observed fleet" aggregation.
    b["ships"][1]["duranium"] = 4
    b["ships"].append({**b["ships"][0], "id": 33})
    ctx = profile(a, b)["per_mineral_category_covariates"]["duranium"][
        "ground_exact_surface_residual"
    ]
    assert "same_site_identical_ship_set_all_cargo_qualified" not in ctx



def test_v3_joint_partition_detects_single_and_multiship_overlap():
    a, b = snapshots()
    # Planet surface residual +7. One ship loses 7 and the second 0:
    # the SINGLE ship and the whole observed multi-ship SUM both match.
    a["ships"] = [
        {**a["ships"][0], "id": 31, "duranium": 9},
        {**a["ships"][0], "id": 32, "duranium": 8},
    ]
    b["ships"] = [
        {**b["ships"][0], "id": 31, "duranium": 2},
        {**b["ships"][0], "id": 32, "duranium": 8},
    ]
    o = profile(a, b)
    j = o["per_mineral_surface_residual_joint_cargo_base"]["duranium"]
    assert j["qualified_surface_residual"] == 1
    assert j["both_single_and_multiship_candidate"] == 1
    assert j["any_exact_opposite_cargo_candidate"] == 1
    assert "single_only_cargo_candidate" not in j
    assert "multiship_only_cargo_candidate" not in j
    assert j["cargo_candidate_positive_surface_residual"] == 1
    planet = o["planet_transition_residual_events_not_independent_actions"]
    assert planet["planet_windows_any_surface_residual"] == 1
    assert planet["residual_mineral_multiplicity_4"] == 1
    assert planet["planet_windows_any_single_cargo"] == 1
    assert planet["planet_windows_any_multiship_cargo"] == 1
    assert planet["planet_windows_any_cargo_candidate"] == 1


def test_v3_joint_separates_multiship_only_and_base_tech_change():
    a, b = snapshots()
    a["ships"] = [
        {**a["ships"][0], "id": 31, "duranium": 9},
        {**a["ships"][0], "id": 32, "duranium": 8},
    ]
    b["ships"] = [
        {**b["ships"][0], "id": 31, "duranium": 6},
        {**b["ships"][0], "id": 32, "duranium": 4},
    ]
    del a["starbases"][0]["ownerid"]
    del b["starbases"][0]["ownerid"]
    b["starbases"][0]["enginetechlevel"] = 4
    o = profile(a, b)
    j = o["per_mineral_surface_residual_joint_cargo_base"]["duranium"]
    assert j["multiship_only_cargo_candidate"] == 1
    assert j["ownerless_planetlinked_tech_changed"] == 1
    assert j["base_tech_change_and_cargo_candidate"] == 1
    events = o["planet_transition_residual_events_not_independent_actions"]
    assert events["planet_windows_any_surface_residual"] == 1
    assert events["planet_windows_any_multiship_cargo"] == 1
    assert events["planet_windows_any_base_tech_change"] == 1
    assert events["planet_windows_base_tech_and_cargo_candidate"] == 1
    # T-1/T observations, no authenticated ship or base orders in output.
    exported = json.dumps(o)
    assert '"planetid"' not in exported and '"ownerid"' not in exported


def test_v3_aggregate_same_frozen_pair_counts_overlap_once():
    class Connection:
        done = False
        def execute(self, query):
            return self
        def fetchmany(self, amount):
            if self.done:
                return []
            self.done = True
            return [(1, 777001, 1, 10, 10), (2, 777001, 1, 11, 11)]
    a, b = snapshots()
    a["ships"] = [
        {**a["ships"][0], "id": 31, "duranium": 9},
        {**a["ships"][0], "id": 32, "duranium": 8},
    ]
    b["ships"] = [
        {**b["ships"][0], "id": 31, "duranium": 2},
        {**b["ships"][0], "id": 32, "duranium": 8},
    ]
    out = analyze_corpus_coverage(
        Connection(), max_games=1, pairs_per_game=1,
        allowed_games={777001}, reconstruct=lambda n: {1: a, 2: b}[n],
    )
    ctx = out["sample"]["surface_residual_context_not_host_verified"]
    j = ctx["per_mineral_surface_residual_joint_cargo_base"]["duranium"]
    assert j["both_single_and_multiship_candidate"] == 1
    assert ctx["planet_transition_residual_events_not_independent_actions"][
        "planet_windows_any_surface_residual"
    ] == 1
    hist = ctx["game_cluster_planet_residual_events_count_buckets"]
    assert hist["planet_windows_any_surface_residual"] == {"1": 1}
    assert hist["planet_windows_any_cargo_candidate"] == {"1": 1}
    assert out["sample"]["owner_current_counts"]["same_owner_planet_id_pairs"] == 1
