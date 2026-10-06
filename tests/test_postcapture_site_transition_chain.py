from __future__ import annotations

import ast
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools" / "research"
PROBE = TOOLS_DIR / "probe-postcapture-site-transition-chain.py"
RUNNER = TOOLS_DIR / "run-postcapture-site-transition-chain.sh"
WRAPPER = TOOLS_DIR / "run-postcapture-site-transition-chain-with-evidence.sh"


def test_site_transition_scripts_are_syntax_valid() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)
    ast.parse(PROBE.read_text(encoding="utf-8"))

    runner = RUNNER.read_text(encoding="utf-8")
    assert "game400330-t141-v592-595.json" in runner
    assert "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb" in runner
    assert "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c" in runner


def test_probe_keeps_main_runtime_dependency_explicit() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert "connect_compact_generation_read_only" in text
    assert 'MAIN_DIAGNOSTICS = Path("/workspace/tools/diagnostics")' in text
    assert "combat_public_capture_o_layer_probe" in text
    assert "postcapture_site_transition_executor" in text


def test_probe_fails_closed_on_dynamic_owner_recomposition() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert "dynamic_owner_requires_recomposition" in text
    assert "ordinary_pair_recomposition_unresolved" in text


def test_probe_uses_factual_next_only_as_comparator_contract() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert "Factual VCR N+1 is used only" in text
    assert "pair_exact = selected.pair == factual_pair" in text
