from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "analyze-postcapture-o-c-topology.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_postcapture_o_c_topology",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_current_partition_metadata() -> None:
    assert MODULE._matches_partition(
        {"partition": "discovery"},
        expected="discovery",
    )
    assert not MODULE._matches_partition(
        {"partition": "heldout"},
        expected="discovery",
    )


def test_legacy_discovery_evidence_status() -> None:
    assert MODULE._matches_partition(
        {
            "schema": "planets-lab.combat-public-capture-o-layer-probe.v1",
            "evidence_status": "DISCOVERY_ONLY_FROZEN_SIDE_CANDIDATE",
        },
        expected="discovery",
    )


def test_legacy_heldout_evidence_status() -> None:
    assert MODULE._matches_partition(
        {
            "schema": "planets-lab.combat-public-capture-o-layer-probe.v1",
            "evidence_status": "HELDOUT_VALIDATION_FROZEN_SIDE_CANDIDATE",
        },
        expected="heldout",
    )


def test_legacy_source_path_fallback() -> None:
    assert MODULE._matches_partition(
        {
            "schema": "planets-lab.combat-public-capture-o-layer-probe.v1",
            "source_discovery": (
                "artifacts/public-capture-side/discovery-capture-side.json"
            ),
        },
        expected="discovery",
    )


def test_topology_classes() -> None:
    assert (
        MODULE._classify(
            prize_position=1,
            captor_position=4,
            factual_position=5,
        )
        == "O_AFTER_CAPTOR"
    )
    assert (
        MODULE._classify(
            prize_position=1,
            captor_position=4,
            factual_position=3,
        )
        == "C_BETWEEN_PRIZE_AND_CAPTOR"
    )
    assert (
        MODULE._classify(
            prize_position=1,
            captor_position=4,
            factual_position=0,
        )
        == "BEFORE_OR_AT_PRIZE"
    )
