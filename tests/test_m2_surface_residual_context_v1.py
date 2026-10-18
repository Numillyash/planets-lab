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
