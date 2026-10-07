from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-site-combat-state-v1.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_site_state_runner_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    source = RUNNER.read_text(encoding="utf-8")
    assert "PLANETS_SITE_STATE_RUNTIME_MODE" in source
    assert "auto|docker|local" in source
    assert "falling back to host Python" in source
    assert "runtime_selected: host-python" in source
    assert "timeout 20s docker info" in source
    assert "pip install --disable-pip-version-check -e" in source
    assert "bootstrap_managed_python" in source
    assert "uv>=0.8" in source
    assert "uv\" python install 3.12" not in source
    assert "\"$BOOTSTRAP_VENV/bin/uv\" python install 3.12" in source
    assert "local Python selection returned an empty executable" in source


def test_auto_runtime_falls_back_when_docker_preflight_fails(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    generations = corpus_root / "generations"
    generations.mkdir(parents=True)
    db = generations / "fake.duckdb"
    db.write_bytes(b"fixture-db")
    sha = hashlib.sha256(db.read_bytes()).hexdigest()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    _write_executable(
        bin_dir / "docker",
        "#!/usr/bin/env bash\nexit 125\n",
    )
    _write_executable(
        bin_dir / "python3",
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-" ]]; then
  cat >/dev/null
  exit 0
fi
printf 'FAKE_LOCAL_GATE %s\n' "$*"
exit 0
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "PLANETS_CORPUS_DB_ROOT": str(corpus_root),
            "PUBLIC100_REL": "generations/fake.duckdb",
            "PUBLIC100_SHA": sha,
            "PLANETS_SITE_STATE_RUNTIME_MODE": "auto",
            "PLANETS_SITE_STATE_RUNTIME_PYTHON": str(bin_dir / "python3"),
            "OUTPUT": str(tmp_path / "out.json"),
        }
    )

    completed = subprocess.run(
        ["bash", str(RUNNER)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    combined = completed.stdout + completed.stderr
    assert "falling back to host Python" in combined
    assert "runtime_selected: host-python" in combined
    assert "FAKE_LOCAL_GATE" in combined
    assert "combat_site_state_differential_v1.py" in combined


def test_explicit_local_runtime_never_invokes_docker(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    generations = corpus_root / "generations"
    generations.mkdir(parents=True)
    db = generations / "fake.duckdb"
    db.write_bytes(b"fixture-db")
    sha = hashlib.sha256(db.read_bytes()).hexdigest()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    marker = tmp_path / "docker-called"
    _write_executable(
        bin_dir / "docker",
        f"#!/usr/bin/env bash\ntouch {marker}\nexit 99\n",
    )
    _write_executable(
        bin_dir / "python3",
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-" ]]; then
  cat >/dev/null
  exit 0
fi
exit 0
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "PLANETS_CORPUS_DB_ROOT": str(corpus_root),
            "PUBLIC100_REL": "generations/fake.duckdb",
            "PUBLIC100_SHA": sha,
            "PLANETS_SITE_STATE_RUNTIME_MODE": "local",
            "PLANETS_SITE_STATE_RUNTIME_PYTHON": str(bin_dir / "python3"),
            "OUTPUT": str(tmp_path / "out.json"),
        }
    )

    subprocess.run(
        ["bash", str(RUNNER)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert not marker.exists()



def test_local_runtime_rejects_configured_python_310(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    generations = corpus_root / "generations"
    generations.mkdir(parents=True)
    db = generations / "fake.duckdb"
    db.write_bytes(b"fixture-db")
    sha = hashlib.sha256(db.read_bytes()).hexdigest()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_python = bin_dir / "python3.10"
    _write_executable(
        fake_python,
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  exit 1
fi
exit 0
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "PLANETS_CORPUS_DB_ROOT": str(corpus_root),
            "PUBLIC100_REL": "generations/fake.duckdb",
            "PUBLIC100_SHA": sha,
            "PLANETS_SITE_STATE_RUNTIME_MODE": "local",
            "PLANETS_SITE_STATE_RUNTIME_PYTHON": str(fake_python),
            "PLANETS_SITE_STATE_RUNTIME_VENV": str(tmp_path / "venv"),
            "OUTPUT": str(tmp_path / "out.json"),
        }
    )

    completed = subprocess.run(
        ["bash", str(RUNNER)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    combined = completed.stdout + completed.stderr
    assert "requires Python >=3.11" in combined


def test_incompatible_cached_venv_is_rebuilt(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    generations = corpus_root / "generations"
    generations.mkdir(parents=True)
    db = generations / "fake.duckdb"
    db.write_bytes(b"fixture-db")
    sha = hashlib.sha256(db.read_bytes()).hexdigest()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "venv-created"

    fake_python = bin_dir / "python3.11"
    _write_executable(
        fake_python,
        f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "${{1:-}}" == "-c" ]]; then
  exit 0
fi
if [[ "${{1:-}}" == "-" ]]; then
  cat >/dev/null
  exit 1
fi
if [[ "${{1:-}}" == "-m" && "${{2:-}}" == "venv" ]]; then
  target="${{3}}"
  mkdir -p "$target/bin"
  cat >"$target/bin/python" <<'PY'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  exit 0
fi
if [[ "${1:-}" == "-" ]]; then
  cat >/dev/null
  exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" ]]; then
  exit 0
fi
printf 'FAKE_REBUILT_GATE %s\n' "$*"
exit 0
PY
  chmod +x "$target/bin/python"
  touch {marker}
  exit 0
fi
exit 0
""",
    )

    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    _write_executable(
        venv / "bin" / "python",
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  exit 1
fi
exit 1
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "PLANETS_CORPUS_DB_ROOT": str(corpus_root),
            "PUBLIC100_REL": "generations/fake.duckdb",
            "PUBLIC100_SHA": sha,
            "PLANETS_SITE_STATE_RUNTIME_MODE": "local",
            "PLANETS_SITE_STATE_RUNTIME_PYTHON": str(fake_python),
            "PLANETS_SITE_STATE_RUNTIME_VENV": str(venv),
            "OUTPUT": str(tmp_path / "out.json"),
        }
    )

    completed = subprocess.run(
        ["bash", str(RUNNER)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    combined = completed.stdout + completed.stderr
    assert "cached venv uses incompatible Python; rebuilding" in combined
    assert marker.exists()
    assert "FAKE_REBUILT_GATE" in combined



def test_missing_python_311_bootstraps_managed_python_312(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    generations = corpus_root / "generations"
    generations.mkdir(parents=True)
    db = generations / "fake.duckdb"
    db.write_bytes(b"fixture-db")
    sha = hashlib.sha256(db.read_bytes()).hexdigest()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    fake_bootstrap = """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  exit 1
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" ]]; then
  target="${3}"
  mkdir -p "$target/bin"
  cat >"$target/bin/python" <<'BOOTPY'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" ]]; then
  cat >"$(dirname "$0")/uv" <<'UV'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--version" ]]; then
  echo "uv 0.9.0"
  exit 0
fi
if [[ "${1:-}" == "python" && "${2:-}" == "install" ]]; then
  target="${UV_PYTHON_INSTALL_DIR}/fake-python/bin"
  mkdir -p "$target"
  cat >"$target/python3.12" <<'MANAGED'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  exit 0
fi
if [[ "${1:-}" == "-" ]]; then
  cat >/dev/null
  exit 0
fi
printf 'FAKE_BOOTSTRAPPED_GATE %s\n' "$*"
exit 0
MANAGED
  chmod +x "$target/python3.12"
  exit 0
fi
if [[ "${1:-}" == "python" && "${2:-}" == "find" ]]; then
  echo "${UV_PYTHON_INSTALL_DIR}/fake-python/bin/python3.12"
  exit 0
fi
exit 1
UV
  chmod +x "$(dirname "$0")/uv"
  exit 0
fi
exit 0
BOOTPY
  chmod +x "$target/bin/python"
  exit 0
fi
exit 0
"""
    for name in ("python3.12", "python3.11", "python3"):
        _write_executable(bin_dir / name, fake_bootstrap)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "PLANETS_CORPUS_DB_ROOT": str(corpus_root),
            "PUBLIC100_REL": "generations/fake.duckdb",
            "PUBLIC100_SHA": sha,
            "PLANETS_SITE_STATE_RUNTIME_MODE": "local",
            "PLANETS_SITE_STATE_BOOTSTRAP_VENV": str(tmp_path / "bootstrap-uv"),
            "PLANETS_SITE_STATE_MANAGED_PYTHON_DIR": str(tmp_path / "managed-python"),
            "PLANETS_SITE_STATE_RUNTIME_VENV": str(tmp_path / "runtime-venv"),
            "OUTPUT": str(tmp_path / "out.json"),
        }
    )

    completed = subprocess.run(
        ["bash", str(RUNNER)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    combined = completed.stdout + completed.stderr
    assert "no compatible host Python found" in combined
    assert "bootstrapping isolated Python 3.12 via uv" in combined
    assert "runtime_selected: host-python" in combined
    assert "FAKE_BOOTSTRAPPED_GATE" in combined
    assert ": command not found" not in combined
    assert "No such file or directory" not in combined
