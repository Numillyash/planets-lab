from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_REF_RE = re.compile(r"(?<![A-Za-z0-9_./-])(tests/[A-Za-z0-9_./-]+\.py)")


def test_all_run_scripts_reference_existing_test_files() -> None:
    missing: list[tuple[str, str]] = []

    for script in sorted((ROOT / "tools").glob("run-*.sh")):
        text = script.read_text(encoding="utf-8")
        for match in TEST_REF_RE.finditer(text):
            relative = match.group(1)
            if not (ROOT / relative).is_file():
                missing.append((script.relative_to(ROOT).as_posix(), relative))

    assert missing == [], "runner test references do not exist: " + repr(missing)
