"""Unit tests for the repository-wide PR continuity contract."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from check_pr_handoff import (
    CONTINUATION, CHANGELOG, SHA_PATTERN,
    changed_pr_files, is_project_document, validate_pr_files,
)


VALID_HANDOFF = (
    "# Continue planets-lab\n"
    "## Context\n"
    "Repository https://github.com/Numillyash/planets-lab; "
    "read docs/ROADMAP.md and docs/WORKFLOW.md first. "
    "Always check the actual main branch and PR CI, "
    "and do not substitute conversation history for Git.\n"
    "## Verified state\n"
    "Last completed work is fully documented in the canonical "
    "main branch. No unverified external observation is promoted.\n"
    "## Next actions\n"
    "Inspect main HEAD and workflows, continue narrowly scoped research "
    "using new PRs and update the continuation prompt in each PR.\n"
    "## Boundaries\n"
    "No raw private orders or API keys, no access to frozen heldout32, "
    "no unreviewed corpus rebuild, no causal NuHost claim from local tests.\n"
)


def validate(paths, text=VALID_HANDOFF):
    return validate_pr_files(set(paths), text)


def test_required_three_classes_in_one_pr():
    assert validate([
        "docs/CONTINUE_HERE.md",
        "docs/PR_CHANGELOG.md",
        "docs/ROADMAP.md",
        "src/planets_lab/sim/some_phase.py",
    ]) == []


def test_every_pr_must_update_all_three_and_not_just_prompt():
    assert len(validate(["src/planets_lab/sim/phase.py"])) == 3
    failures = validate([CONTINUATION, CHANGELOG])
    assert len(failures) == 1
    assert "meaningful" in failures[0]


@pytest.mark.parametrize("project_doc", [
    "README.md",
    "docs/ROADMAP.md",
    "docs/WORKFLOW.md",
    "docs/ARCHITECTURE.md",
    "docs/handoff/specific-mechanic.md",
    "docs/research/2026-10-22-issue.md",
])
def test_documentation_changes_are_recognized(project_doc):
    assert is_project_document(project_doc)
    assert validate([CONTINUATION, CHANGELOG, project_doc]) == []


@pytest.mark.parametrize("not_doc", [
    CONTINUATION,
    CHANGELOG,
    "src/planets_lab/sim/foo.py",
    ".github/workflows/tests.yml",
    "docs/handoff/data.json",
    "docs/index.txt",
])
def test_prompt_or_changelog_alone_are_not_project_docs(not_doc):
    assert not is_project_document(not_doc)


def test_bad_handoff_is_not_accepted_even_if_three_files_changed():
    files = [CONTINUATION, CHANGELOG, "docs/ROADMAP.md"]
    failures = validate(files, "## Context\nvery short")
    assert any("substantive" in item for item in failures)
    assert any("## Verified state" in item for item in failures)
    assert any("canonical repository" in item for item in failures)
    assert any("roadmap" in item for item in failures)


def test_handoff_missing_specific_section():
    files = [CONTINUATION, CHANGELOG, "README.md"]
    failures = validate(files, VALID_HANDOFF.replace("## Boundaries", "## Plans"))
    assert len(failures) == 1
    assert "## Boundaries" in failures[0]


@pytest.mark.parametrize("sha", [
    "a" * 40,
    "abcd1234" * 5,
])
def test_full_shas_recognized(sha):
    assert SHA_PATTERN.fullmatch(sha)


def test_non_commit_sha_rejected_before_invoking_git():
    with pytest.raises(ValueError):
        changed_pr_files("main", "f" * 40)


def test_empty_hand_off_is_not_passable():
    assert validate([CONTINUATION, CHANGELOG, "docs/ROADMAP.md"], "")


def test_current_pr_number_required_in_both_current_handoff_files():
    changes = [CONTINUATION, CHANGELOG, "docs/ROADMAP.md"]
    current = VALID_HANDOFF + "\nCurrent PR #262 and its continuation state.\n"
    assert validate_pr_files(
        set(changes), current, "PR #262 — new workflow", pr_number=262,
    ) == []
    assert any("CURRENT PR #262" in x for x in validate_pr_files(
        set(changes), VALID_HANDOFF, "PR #262 — new workflow", pr_number=262,
    ))
    assert any("CURRENT PR #262" in x for x in validate_pr_files(
        set(changes), current, "PR #261 — older state", pr_number=262,
    ))


def test_previous_pr_reference_cannot_mask_missing_current_pr_reference():
    changes = [CONTINUATION, CHANGELOG, "README.md"]
    text = VALID_HANDOFF + "Previously completed #261"
    failures = validate_pr_files(set(changes), text, "Completed PR #261", pr_number=262)
    assert len(failures) == 2
