from __future__ import annotations

import json
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "diagnostics" / "combat_predictive_queue_integration_check.py"
SPEC = spec_from_file_location("combat_predictive_queue_integration_check", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_accepts_exact_feature_scope_and_held_out_queue(tmp_path: Path) -> None:
    feature = {
        "exact": True,
        "failures": [],
        "checks": {
            "selector_partition_shared": True,
            "selector_partition_disjoint": True,
            "planet_c4_checkpoint_preserved": True,
            "ship_c3_checkpoint_preserved": True,
            "cluster_partition_preserved": True,
        },
    }
    counts = {}
    for profile in ("strict", "conditional"):
        counts[f"{profile}:transitions_compared"] = 22
        counts[f"{profile}:next_vcr_exact"] = 22
        counts[f"{profile}:next_vcr_mismatch"] = 0
    queue = {
        "summary": {
            "feature_scope": {"profile": "combat-planar-no-horwasp"},
            "acceptance": {"all_profiles_pass": True},
            "counts": counts,
        }
    }
    report = MODULE.run(
        _write(tmp_path / "feature.json", feature),
        _write(tmp_path / "queue.json", queue),
    )
    assert report["exact"] is True
    assert report["failures"] == []


def test_rejects_queue_regression(tmp_path: Path) -> None:
    feature = {
        "exact": True,
        "failures": [],
        "checks": {
            "selector_partition_shared": True,
            "selector_partition_disjoint": True,
            "planet_c4_checkpoint_preserved": True,
            "ship_c3_checkpoint_preserved": True,
            "cluster_partition_preserved": True,
        },
    }
    counts = {}
    for profile in ("strict", "conditional"):
        counts[f"{profile}:transitions_compared"] = 22
        counts[f"{profile}:next_vcr_exact"] = 21
        counts[f"{profile}:next_vcr_mismatch"] = 1
    queue = {
        "summary": {
            "feature_scope": {"profile": "combat-planar-no-horwasp"},
            "acceptance": {"all_profiles_pass": False},
            "counts": counts,
        }
    }
    report = MODULE.run(
        _write(tmp_path / "feature.json", feature),
        _write(tmp_path / "queue.json", queue),
    )
    assert report["exact"] is False
    assert "strict_held_out_next_vcr_exact" in report["failures"]
