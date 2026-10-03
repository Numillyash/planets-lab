from __future__ import annotations

import os
import pathlib
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-public-validation-corpus-acquisition.sh"


def _write(path: pathlib.Path, text: str = "x\n") -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _env(tmp_path: pathlib.Path, *, auto_backfill: bool) -> dict[str, str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text(
        """#!/usr/bin/env bash
set -eu
if [[ "${1:-}" == "info" ]]; then
  exit 0
fi
if [[ "${1:-}" == "compose" && "${2:-}" == "build" ]]; then
  exit 0
fi
if [[ "${1:-}" == "compose" && "${2:-}" == "run" ]]; then
  exit "${FAKE_DOCKER_RUN_RC:-130}"
fi
exit 0
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)

    work = tmp_path / "work"
    baseline = _write(work / "baseline.jsonl")
    candidates = _write(work / "candidates.jsonl")
    selected = _write(work / "selected.jsonl")
    combined = _write(work / "combined.jsonl")
    report = _write(work / "selection-report.json", "{}\n")
    index = _write(work / "games.jsonl")
    stats = _write(work / "stats.json", "{}\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "FAKE_DOCKER_RUN_RC": "130",
            "BASELINE_MANIFEST": str(baseline),
            "CANDIDATES_MANIFEST": str(candidates),
            "SELECTED_MANIFEST": str(selected),
            "COMBINED_MANIFEST": str(combined),
            "REPORT": str(report),
            "INDEX_OUTPUT": str(index),
            "STATS_OUTPUT": str(stats),
            "REJECTED_FILE": str(work / "rejected.json"),
            "BACKFILL_REPORT": str(work / "backfill-report.json"),
            "EVIDENCE_DIR": str(work / "evidence"),
            "REUSE_DISCOVERY": "1",
            "AUTO_BACKFILL": "1" if auto_backfill else "0",
            "MAX_BACKFILL_ROUNDS": "3",
            "DOCKER_PREFLIGHT_TIMEOUT": "2",
        }
    )
    return env


def _run(tmp_path: pathlib.Path, *, auto_backfill: bool) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(RUNNER)],
        cwd=REPO_ROOT,
        env=_env(tmp_path, auto_backfill=auto_backfill),
        text=True,
        capture_output=True,
        check=False,
    )


def test_ingest_sigint_stops_without_retry_loop(tmp_path: pathlib.Path) -> None:
    result = _run(tmp_path, auto_backfill=False)
    output = result.stdout + result.stderr

    assert result.returncode == 130
    assert output.count("PUBLIC VALIDATION CORPUS: DOWNLOAD + INDEX") == 1
    assert "CONTINUE WITH FRESH FAILURE STATS" not in output
    assert "download/index interrupted (rc=130); stopping immediately" in output


def test_backfill_sigint_stops_before_ingest(tmp_path: pathlib.Path) -> None:
    result = _run(tmp_path, auto_backfill=True)
    output = result.stdout + result.stderr

    assert result.returncode == 130
    assert "BACKFILL ROUND 1/3" in output
    assert "PUBLIC VALIDATION CORPUS: DOWNLOAD + INDEX" not in output
    assert "CONTINUE WITH FRESH FAILURE STATS" not in output
    assert "backfill interrupted (rc=130); stopping immediately" in output
