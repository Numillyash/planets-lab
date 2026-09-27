from __future__ import annotations

import shlex
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_validation_wrapper_only_publishes_artifact_paths() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-with-evidence.sh").read_text(
        encoding="utf-8"
    )
    tokens = shlex.split(script.replace("\\\n", " "))
    includes = [
        tokens[index + 1]
        for index, token in enumerate(tokens)
        if token == "--include"
    ]

    assert includes == ["artifacts/public-validation-corpus"]
    assert all(path == "artifacts" or path.startswith("artifacts/") for path in includes)


def test_acquisition_runner_stages_safe_outputs_under_artifacts() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-acquisition.sh").read_text(
        encoding="utf-8"
    )

    assert 'EVIDENCE_DIR="${EVIDENCE_DIR:-artifacts/public-validation-corpus/evidence}"' in script
    for filename in (
        "public-validation-selected.jsonl",
        "public-validation-combined.jsonl",
        "public-validation-games.jsonl",
        "public-validation-stats.json",
    ):
        assert f'$EVIDENCE_DIR/{filename}' in script


def test_acquisition_runner_prefers_python3_and_exports_src_pythonpath() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-acquisition.sh").read_text(
        encoding="utf-8"
    )

    assert "command -v python3" in script
    assert "PYTHON_BIN=python3" in script
    assert 'export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"' in script
    assert '"$PYTHON_BIN" -m planets_lab.corpus.public_finished_discover_cli' in script
    assert '"$PYTHON_BIN" -m planets_lab.corpus.ingest_manifest_cli' in script
