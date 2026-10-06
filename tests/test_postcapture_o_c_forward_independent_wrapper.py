from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = (
    REPO_ROOT
    / "tools"
    / "research"
    / "run-postcapture-o-c-forward-independent-with-evidence.sh"
)
RUNNER = (
    REPO_ROOT
    / "tools"
    / "research"
    / "run-postcapture-o-c-forward-independent.sh"
)


def test_o_c_forward_independent_evidence_wrapper_is_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)
    text = WRAPPER.read_text(encoding="utf-8")
    assert "postcapture-o-c-forward-independent" in text
    assert (
        "artifacts/external-sources/postcapture-occurrence/fresh32-independent"
        in text
    )
    assert "run-postcapture-o-c-forward-independent.sh" in text



def test_o_c_forward_independent_uses_container_manifest_path() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    text = RUNNER.read_text(encoding="utf-8")
    assert (
        'python - /workspace/validation/corpus/manifests/'
        'public-postindependent-validation-selected.jsonl'
        in text
    )
    assert '"${lab[@]}" python - "$FRESH_MANIFEST"' not in text
