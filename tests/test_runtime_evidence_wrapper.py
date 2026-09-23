from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path


WRAPPER_SOURCE = (
    Path(__file__).resolve().parents[1] / "tools" / "run-with-runtime-evidence.sh"
)


def _run(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _prepare_repo(tmp_path: Path, runner_exit: int) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    repo.mkdir()
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "config", "user.name", "test", cwd=repo)
    _run("git", "config", "user.email", "test@example.invalid", cwd=repo)

    tools = repo / "tools"
    tools.mkdir()
    wrapper = tools / "run-with-runtime-evidence.sh"
    shutil.copy2(WRAPPER_SOURCE, wrapper)
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)

    fake = tools / "fake-runner.sh"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "mkdir -p artifacts/demo\n"
        "printf '{\"ok\": true}\\n' > artifacts/demo/result.json\n"
        "echo fake-runtime-output\n"
        f"exit {runner_exit}\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "initial", cwd=repo)
    _run("git", "init", "--bare", str(remote), cwd=tmp_path)
    _run("git", "remote", "add", "origin", str(remote), cwd=repo)
    _run("git", "push", "-u", "origin", "main", cwd=repo)
    return repo, remote


def _runtime_paths(remote: Path) -> list[str]:
    result = _run(
        "git",
        "--git-dir",
        str(remote),
        "ls-tree",
        "-r",
        "--name-only",
        "runtime-logs",
        cwd=remote.parent,
    )
    return [line for line in result.stdout.splitlines() if line]


def _show(remote: Path, path: str) -> str:
    return _run(
        "git",
        "--git-dir",
        str(remote),
        "show",
        f"runtime-logs:{path}",
        cwd=remote.parent,
    ).stdout


def test_runtime_evidence_publishes_log_metadata_and_artifacts(tmp_path: Path) -> None:
    repo, remote = _prepare_repo(tmp_path, runner_exit=0)
    source_head = _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()

    result = _run(
        "bash",
        "tools/run-with-runtime-evidence.sh",
        "demo",
        "--include",
        "artifacts/demo",
        "--",
        "bash",
        "tools/fake-runner.sh",
        cwd=repo,
    )

    assert "runtime_evidence: published" in result.stdout
    assert _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip() == source_head

    paths = _runtime_paths(remote)
    metadata_path = next(path for path in paths if path.endswith("/metadata.json"))
    prefix = metadata_path.rsplit("/", 1)[0]
    assert f"{prefix}/gate.log" in paths
    assert f"{prefix}/artifacts/demo/result.json" in paths

    metadata = json.loads(_show(remote, metadata_path))
    assert metadata["exit_code"] == 0
    assert metadata["source_commit"] == source_head
    assert metadata["requested_artifact_paths"] == ["artifacts/demo"]
    assert "fake-runtime-output" in _show(remote, f"{prefix}/gate.log")


def test_runtime_evidence_preserves_runner_failure_but_still_pushes(tmp_path: Path) -> None:
    repo, remote = _prepare_repo(tmp_path, runner_exit=7)

    result = _run(
        "bash",
        "tools/run-with-runtime-evidence.sh",
        "demo-failure",
        "--include",
        "artifacts/demo",
        "--",
        "bash",
        "tools/fake-runner.sh",
        cwd=repo,
        check=False,
    )

    assert result.returncode == 7
    assert "runtime_evidence: published" in result.stdout

    paths = _runtime_paths(remote)
    metadata_path = next(
        path
        for path in paths
        if "/demo-failure/" in path and path.endswith("/metadata.json")
    )
    metadata = json.loads(_show(remote, metadata_path))
    assert metadata["exit_code"] == 7


def test_runtime_evidence_rejects_non_artifact_include(tmp_path: Path) -> None:
    repo, _remote = _prepare_repo(tmp_path, runner_exit=0)
    (repo / ".env").write_text("SECRET=do-not-copy\n", encoding="utf-8")

    result = _run(
        "bash",
        "tools/run-with-runtime-evidence.sh",
        "demo",
        "--include",
        ".env",
        "--",
        "bash",
        "tools/fake-runner.sh",
        cwd=repo,
        check=False,
    )

    assert result.returncode == 64
    assert "must be under artifacts/" in result.stdout
