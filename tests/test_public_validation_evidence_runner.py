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


def test_acquisition_runner_uses_project_docker_python() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-acquisition.sh").read_text(
        encoding="utf-8"
    )

    assert "docker compose build lab" in script
    assert "docker compose run --rm -T" in script
    assert "-e PYTHONPATH=/workspace/src" in script
    assert '"${lab[@]}" python -m planets_lab.corpus.public_finished_discover_cli' in script
    assert '"${lab[@]}" python -m planets_lab.corpus.ingest_manifest_cli' in script
    assert "command -v python3" not in script
    assert "PYTHON_BIN=" not in script


def test_acquisition_runner_passes_direct_mode_only_when_proxy_is_absent() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-acquisition.sh").read_text(
        encoding="utf-8"
    )

    assert 'lab+=(-e "PLANETSNU_PROXY_URL=${PLANETSNU_PROXY_URL}")' in script
    assert "lab+=(-e PLANETSNU_ALLOW_DIRECT=1)" in script


def test_acquisition_runner_reuses_discovery_and_stages_partial_ingest_evidence() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-acquisition.sh").read_text(
        encoding="utf-8"
    )

    assert 'REUSE_DISCOVERY="${REUSE_DISCOVERY:-1}"' in script
    assert 'discovery:    reuse existing manifests/report' in script
    assert 'ARCHIVE_TIMEOUT="${ARCHIVE_TIMEOUT:-180}"' in script
    assert 'ARCHIVE_RETRIES="${ARCHIVE_RETRIES:-2}"' in script
    assert '--network-timeout "$ARCHIVE_TIMEOUT"' in script
    assert '--download-retries "$ARCHIVE_RETRIES"' in script
    assert "set +e" in script
    assert "INGEST_RC=$?" in script
    assert 'exit "$INGEST_RC"' in script


def test_acquisition_runner_backfills_previous_failures_before_ingest() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-acquisition.sh").read_text(
        encoding="utf-8"
    )

    assert 'AUTO_BACKFILL="${AUTO_BACKFILL:-1}"' in script
    assert "PUBLIC VALIDATION CORPUS: BACKFILL PREVIOUS FAILURES" in script
    assert (
        '"${lab[@]}" python -m '
        "planets_lab.corpus.public_validation_backfill_cli"
    ) in script
    assert '--rejected "$REJECTED_FILE"' in script
    assert '$EVIDENCE_DIR/public-validation-rejected.json' in script
    assert '$EVIDENCE_DIR/public-validation-backfill-report.json' in script


def test_public_capture_side_runner_keeps_heldout_games_unscanned() -> None:
    runner = (ROOT / "tools/run-public-capture-side-discovery.sh").read_text(
        encoding="utf-8"
    )
    wrapper = (
        ROOT / "tools/run-public-capture-side-discovery-with-evidence.sh"
    ).read_text(encoding="utf-8")

    assert "--partition discovery" in runner
    assert "--partition heldout" not in runner
    assert "--include artifacts/public-capture-side" in wrapper
    assert "validation/corpus/cache/loadall" not in wrapper

def test_public_validation_wrapper_fails_closed_off_main_by_default() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-with-evidence.sh").read_text(
        encoding="utf-8"
    )

    assert 'PUBLIC_VALIDATION_ALLOW_NON_MAIN="${PUBLIC_VALIDATION_ALLOW_NON_MAIN:-0}"' in script
    assert 'git symbolic-ref --quiet --short HEAD' in script
    assert '"$SOURCE_BRANCH" != "main"' in script
    assert 'exit 64' in script
    assert 'PUBLIC_VALIDATION_ALLOW_NON_MAIN=1' in script

def test_acquisition_runner_auto_repeats_bounded_backfill_rounds() -> None:
    script = (ROOT / "tools/run-public-validation-corpus-acquisition.sh").read_text(
        encoding="utf-8"
    )

    assert 'MAX_BACKFILL_ROUNDS="${MAX_BACKFILL_ROUNDS:-6}"' in script
    assert 'BACKFILL_ROUND=0' in script
    assert 'while true; do' in script
    assert 'BACKFILL_ROUND=$((BACKFILL_ROUND + 1))' in script
    assert 'CONTINUE WITH FRESH FAILURE STATS' in script
    assert 'reached MAX_BACKFILL_ROUNDS=' in script
    assert 'backfill_rounds:   $BACKFILL_ROUND' in script

