"""M2 public100 census: reproducible metadata selection and owner-current guards."""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import zipfile

from planets_lab.corpus.m2_economy_coverage import (
    Member, Pair, census_members, profile_pair, analyze_corpus_coverage,
)
from planets_lab.corpus.corpus_db_compact import import_archive_to_compact_database


ROOT = Path(__file__).resolve().parents[1]


def fixture_payload(*, game=42, player=1, turn=10, supplies=10,
                    owned=True, infoturn=None):
    return {
        "game": {"id": game, "turn": turn},
        "player": {"id": player, "raceid": 1},
        "players": [],
        "settings": {"sphere": False},
        "planets": [{
            "id": 13, "ownerid": player if owned else 2,
            "infoturn": turn if infoturn is None else infoturn,
            "megacredits": 200, "supplies": supplies,
            "neutronium": 10, "duranium": 20,
            "tritanium": 30, "molybdenum": 40,
            "groundneutronium": 50, "groundduranium": 60,
            "groundtritanium": 70, "groundmolybdenum": 80,
            "clans": 300, "nativeclans": 0, "mines": 5,
            "factories": 8, "defense": 2,
            "colonisttaxrate": 2, "nativehappypoints": 80,
            "nativetaxrate": 0,
        }],
        "ships": [{"id": 30, "ownerid": player, "hullid": 5}],
        "starbases": [{"id": 1, "planetid": 13, "ownerid": player}],
        "vcrs": [], "ionstorms": [], "minefields": [], "relations": [],
    }


def test_full_metadata_census_selects_only_unambiguous_adjacent_perspectives():
    rows = [
        Member(1, 42, 1, 10, 10),
        Member(2, 42, 1, 11, 11),
        Member(3, 42, 1, 12, 12),
        Member(4, 42, 2, 10, 10),
        Member(5, 42, 2, 11, 10),   # embedded turn is stale
        Member(6, 43, 1, 10, 10),
        Member(7, 43, 1, 11, 11),
        Member(8, 43, 1, 11, 11),   # duplicate ambiguous turn
        Member(9, 44, 1, 10, 10),
        Member(10, 44, 1, 11, 11),
    ]
    stats, selected = census_members(rows, max_games=3, pairs_per_game=2)
    assert stats["all_games_in_source_metadata"] == 3
    assert stats["all_source_perspective_members"] == 10
    assert stats["metadata_invalid_or_embedded_turn_mismatch"] == 1
    assert stats["ambiguous_duplicate_perspective_turn_keys"] == 1
    assert stats["potential_adjacent_same_perspective_pairs"] == 3
    assert len(selected) == 3
    assert {(x.game, x.after_turn) for x in selected} == {
        (42, 11), (42, 12), (44, 11),
    }
    baseline, frozen = census_members(
        rows, max_games=3, pairs_per_game=2, allowed_games={44},
    )
    assert baseline["all_games_in_source_metadata"] == 3
    assert baseline["games_allowed_for_entity_sampling"] == 1
    assert {(x.game, x.after_turn) for x in frozen} == {(44, 11)}
    assert stats["metadata_frozen_selection_sha256"] == census_members(
        list(reversed(rows)), max_games=3, pairs_per_game=2,
    )[0]["metadata_frozen_selection_sha256"]


def test_owner_current_source_pair_qualifies_but_no_player_action_attribution():
    pair = Pair(42, 1, 11, 1, 2)
    before = fixture_payload(turn=10, supplies=10)
    after = fixture_payload(turn=11, supplies=18)
    result = profile_pair(before, after, pair)
    assert result["same_owner_planet_id_pairs"] == 1
    assert result["qualified_field_families"] == {
        "credits_and_supplies": 1,
        "minerals_surface": 1,
        "minerals_ground": 1,
        "colonists_and_natives": 1,
        "structures": 1,
        "tax_inputs": 1,
    }
    assert result["changed_net_stock_family_rows_not_phase_attribution"] == {
        "credits_and_supplies": 1,
    }
    assert result["section_counts"]["starbases"] == {
        "before": 1, "after": 1,
    }


def test_non_owner_stale_or_missing_field_abstains():
    pair = Pair(42, 1, 11, 1, 2)
    before = fixture_payload(turn=10, infoturn=9)
    after = fixture_payload(turn=11)
    result = profile_pair(before, after, pair)
    assert result["same_owner_planet_id_pairs"] == 0
    assert result["source_statuses"]["ABSTAIN_OWNER_PLANET_STALE_OR_NO_INFOTURN"] == 1
    assert not result["qualified_field_families"]
    before = fixture_payload(turn=10, owned=False)
    result = profile_pair(before, after, pair)
    assert result["same_owner_planet_id_pairs"] == 0
    before = fixture_payload(turn=10)
    del before["planets"][0]["megacredits"]
    result = profile_pair(before, after, pair)
    assert result["qualified_field_families"]["credits_and_supplies"] == 0
    assert result["qualified_field_families"]["minerals_surface"] == 1


def test_corpus_inventory_uses_metadata_frozen_pair_before_reconstruct():
    class MockConn:
        def __init__(self):
            self.args = None
        def execute(self, sql):
            assert "FROM source_members" in sql
            return self
        def fetchmany(self, n):
            if self.args is None:
                self.args = 1
                return [(1, 42, 1, 10, 10), (2, 42, 1, 11, 11)]
            return []
    snapshots = {
        1: fixture_payload(turn=10, supplies=10),
        2: fixture_payload(turn=11, supplies=18),
    }
    accessed = []
    def restore(n):
        accessed.append(n)
        return snapshots[n]
    report = analyze_corpus_coverage(MockConn(), max_games=100,
                                     pairs_per_game=2, reconstruct=restore)
    assert accessed == [1, 2]
    assert report["metadata"]["metadata_frozen_sample_pairs"] == 1
    assert report["metadata"]["all_source_perspective_members"] == 2
    assert report["sample"]["qualified_planet_field_family_pairs"][
        "credits_and_supplies"
    ] == 1
    assert report["evidence_limits"]["raw_trn_is_submitted_turn_orders"] is False
    assert report["evidence_limits"]["NuHost_ship_build_cost_verified"] is False


def test_wrong_embedded_payload_identity_abstains():
    class Conn:
        def execute(self, query):
            return self
        def fetchmany(self, n):
            if not hasattr(self, "done"):
                self.done = True
                return [(1, 42, 1, 10, 10), (2, 42, 1, 11, 11)]
            return []
    snapshots = {
        1: fixture_payload(turn=10),
        2: fixture_payload(turn=12),  # claims turn 12, not 11
    }
    report = analyze_corpus_coverage(
        Conn(), reconstruct=lambda member_id: snapshots[member_id],
    )
    assert report["sample"]["sample_status_counts"] == {
        "ABSTAIN_PAYLOAD_IDENTITY_INVALID": 1,
    }
    assert report["sample"]["qualified_planet_field_family_pairs"] == {}


def test_full_read_only_diagnostic_uses_explicit_pinned_generation(tmp_path):
    # Small actual compact DB to validate CLI end-to-end. No live Nu archives.
    archive = tmp_path / "game-42.zip"
    with zipfile.ZipFile(archive, "w") as container:
        for turn in (10, 11):
            container.writestr(
                f"player1-turn{turn}.trn",
                gzip.compress(json.dumps(fixture_payload(
                    turn=turn, supplies=turn,
                )).encode()),
            )
    root = tmp_path / "corpus-db"
    generations = root / "generations"
    generations.mkdir(parents=True)
    database = generations / "test-compact.duckdb"
    import_archive_to_compact_database(
        archive, database, expected_game_id=42,
        arrow_batch_rows=4, commit_every_members=1,
    )
    (root / "CURRENT").write_text(
        "generations/CURRENT-alternative.duckdb\n", encoding="utf-8",
    )
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    out = tmp_path / "aggregates.json"
    baseline_manifest = tmp_path / "baseline-public68-test.jsonl"
    baseline_manifest.write_text(json.dumps({"game_id": 42}) + "\n", encoding="utf-8")
    script = ROOT / "tools/diagnostics/m2_public_corpus_economy_coverage_v1.py"
    args = [
        sys.executable, str(script),
        "--db-root", str(root),
        "--generation", "generations/test-compact.duckdb",
        "--expected-sha256", digest,
        "--max-games", "1", "--pairs-per-game", "1",
        "--baseline-manifest", str(baseline_manifest),
        "--expected-baseline-games", "1",
        "--output", str(out),
    ]
    proc = subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, timeout=45,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    report = json.loads(out.read_text())
    assert report["metadata"]["all_source_perspective_members"] == 2
    assert report["metadata"]["metadata_frozen_sample_pairs"] == 1
    assert report["sample"]["owner_current_counts"]["same_owner_planet_id_pairs"] == 1
    assert report["sample"]["qualified_planet_field_family_pairs"][
        "credits_and_supplies"
    ] == 1
    assert report["sample"]["individual_numeric_field_directions"]["supplies"] == {
        "qualified": 1, "increased": 1,
    }
    assert report["sample"]["observable_structure_and_tax_controls"] == {
        "qualified": 1, "all_unchanged": 1,
    }
    assert report["generation"]["verified_sha256"] == digest
    assert report["generation"]["CURRENT_modified"] is False
    assert report["baseline_sample_allowlist"]["allowed_game_count"] == 1
    assert report["baseline_sample_allowlist"]["heldout_entity_sampling"] is False
    assert (root / "CURRENT").read_text() == (
        "generations/CURRENT-alternative.duckdb\n"
    )
    # A SHA256 digest may naturally contain the digits "42"; forbid
    # actual labelled game/player identities, not arbitrary hex pairs.
    assert "game_id: 42" not in proc.stdout
    assert '"game_id": 42' not in proc.stdout
    assert "player_id: 1" not in proc.stdout
    out.unlink()
    wrong = list(args)
    wrong[wrong.index("--expected-sha256") + 1] = "0" * 64
    fail = subprocess.run(wrong, cwd=ROOT, capture_output=True, text=True, timeout=45)
    assert fail.returncode != 0
    assert not out.exists()



def test_corpus_wrapper_exports_implicit_default_path_for_compose():
    """Regression: Compose needs the host root as an EXPORTED variable.

    The failure on the corpus server was that bash resolved DB_ROOT,
    but compose.corpus-db.yaml could not interpolate
    PLANETS_CORPUS_DB_ROOT because the fallback was not exported.
    Exercise the ACTUAL assignment and export lines with env unset.
    """
    import os
    script = ROOT / "tools/run-m2-public100-economy-coverage-v1.sh"
    source = script.read_text(encoding="utf-8")
    dbroot_line = next(
        line for line in source.splitlines() if line.startswith('DB_ROOT="')
    )
    export_line = next(
        line for line in source.splitlines()
        if line.startswith("export PLANETS_CORPUS_DB_ROOT=")
    )
    env = dict(os.environ)
    env.pop("PLANETS_CORPUS_DB_ROOT", None)
    command = "\n".join([
        dbroot_line,
        export_line,
        'test "$PLANETS_CORPUS_DB_ROOT" = /root/projects/planets-corpus-db',
        'bash -c \'test "$PLANETS_CORPUS_DB_ROOT" = /root/projects/planets-corpus-db\'',
    ])
    process = subprocess.run(
        ["bash", "-c", command], cwd=ROOT,
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert process.returncode == 0, process.stderr
    syntax = subprocess.run(
        ["bash", "-n", str(script)], cwd=ROOT,
        capture_output=True, text=True, timeout=10,
    )
    assert syntax.returncode == 0, syntax.stderr



def test_m2_directional_field_counts_are_not_family_change_counts():
    pair = Pair(42, 1, 11, 1, 2)
    before = fixture_payload(turn=10, supplies=10)
    after = fixture_payload(turn=11, supplies=18)
    out = profile_pair(before, after, pair)["numeric_directional_coverage"]
    assert out["per_field"]["supplies"] == {"qualified": 1, "increased": 1}
    assert out["per_field"]["megacredits"] == {"qualified": 1, "unchanged": 1}
    assert out["per_field"]["nativehappypoints"] == {
        "qualified": 1, "unchanged": 1,
    }
    assert out["observable_structure_and_tax_controls"] == {
        "qualified": 1, "all_unchanged": 1,
    }
    for mineral in ("neutronium", "duranium", "tritanium", "molybdenum"):
        assert out["surface_ground_joint_signs_not_mining_attribution"][mineral] == {
            "qualified": 1,
            "ground_unchanged__surface_unchanged": 1,
        }


def test_m2_mineral_joint_signs_mines_stability_cannot_prove_mining():
    pair = Pair(42, 1, 11, 1, 2)
    before = fixture_payload(turn=10)
    after = fixture_payload(turn=11)
    before["planets"][0]["groundduranium"] = 60
    after["planets"][0]["groundduranium"] = 55
    before["planets"][0]["duranium"] = 20
    after["planets"][0]["duranium"] = 25
    profile = profile_pair(before, after, pair)
    mineral = profile["numeric_directional_coverage"][
        "surface_ground_joint_signs_not_mining_attribution"
    ]["duranium"]
    assert mineral == {
        "qualified": 1,
        "ground_decreased__surface_increased": 1,
        "ground_down_surface_up_mines_unchanged": 1,
    }
    assert profile["numeric_directional_coverage"][
        "observable_structure_and_tax_controls"
    ] == {"qualified": 1, "all_unchanged": 1}
    # Another visible intervention changes a control; the mining
    # shortlist must no longer be treated as "unchanged mines".
    after["planets"][0]["mines"] = 6
    profile = profile_pair(before, after, pair)
    mineral = profile["numeric_directional_coverage"][
        "surface_ground_joint_signs_not_mining_attribution"
    ]["duranium"]
    assert mineral["ground_decreased__surface_increased"] == 1
    assert "ground_down_surface_up_mines_unchanged" not in mineral
    assert profile["numeric_directional_coverage"][
        "observable_structure_and_tax_controls"
    ] == {"qualified": 1, "some_changed": 1}


def test_m2_directional_missing_field_or_stale_owner_fails_closed():
    pair = Pair(42, 1, 11, 1, 2)
    before = fixture_payload(turn=10)
    after = fixture_payload(turn=11)
    del after["planets"][0]["supplies"]
    prof = profile_pair(before, after, pair)
    all_fields = prof["numeric_directional_coverage"]["per_field"]
    assert "supplies" not in all_fields
    assert all_fields["megacredits"]["qualified"] == 1

    not_current = fixture_payload(turn=10, infoturn=9)
    prof = profile_pair(not_current, after, pair)
    assert prof["numeric_directional_coverage"]["per_field"] == {}
    assert prof["numeric_directional_coverage"][
        "surface_ground_joint_signs_not_mining_attribution"
    ] == {}


def test_m2_aggregate_field_directions_keep_same_owner_pair_denominators():
    class Conn:
        def __init__(self):
            self.done = False
        def execute(self, q):
            return self
        def fetchmany(self, limit):
            if self.done:
                return []
            self.done = True
            return [(1, 42, 1, 10, 10), (2, 42, 1, 11, 11)]
    states = {1: fixture_payload(turn=10, supplies=10),
              2: fixture_payload(turn=11, supplies=18)}
    out = analyze_corpus_coverage(
        Conn(), max_games=1, pairs_per_game=1,
        reconstruct=lambda idx: states[idx], allowed_games={42},
    )
    sample = out["sample"]
    assert sample["individual_numeric_field_directions"]["supplies"] == {
        "qualified": 1, "increased": 1,
    }
    assert sample["individual_numeric_field_directions"]["megacredits"] == {
        "qualified": 1, "unchanged": 1,
    }
    assert sample["observable_structure_and_tax_controls"] == {
        "qualified": 1, "all_unchanged": 1,
    }
    assert out["evidence_limits"]["ground_down_surface_up_proves_mining"] is False
    assert out["evidence_limits"]["per_field_change_is_host_phase_evidence"] is False
