# Development workflow

This repository is maintained as a personal project. All material changes use short-lived branches and pull requests targeting `main`. PR CI and post-merge `main` CI are checked; the dedicated `runtime-logs` evidence branch is not a source-code PR workflow. Every PR must carry both a self-contained continuation prompt and a corresponding documentation update.

## Source of truth

GitHub `main` is the source of truth for project state. Do not reconstruct current implementation status or priorities from old chat history when the repository documentation is available.

Before continuing substantial work (especially in a **new chat**), read:

1. `docs/CONTINUE_HERE.md` — canonical standalone next-chat prompt;
2. `README.md` and `docs/ROADMAP.md`;
3. `docs/PR_CHANGELOG.md` and the newest relevant file in `docs/handoff/`;
4. `docs/COMPILED_CORPUS.md` when working on historical-corpus or movement validation.

Verify current `main` HEAD and recent PR/CI **after** reading the handoff; pinned commits in a prepared PR prompt are historical context, not a live-state guarantee.

## Mandatory PR → new-chat continuity contract

**User requirement, effective 2026-10-22:** After **every pull request**, Git must contain both an updated, copy-ready prompt for a new ChatGPT conversation and synchronized repository documentation. The information is committed **as part of that same PR before merge**; otherwise it would not survive loss of chat context and would require an extra follow-up PR.

Every PR, even a tiny fix, refactor, docs-only change or CI change, must:

1. Rewrite `docs/CONTINUE_HERE.md` so it can be pasted directly into a new chat without copying old assistant replies. Include the **actual current PR number**, latest concrete completed/ongoing work, authoritative files, supported and unsupported mechanics, evidence status, blockers, and actionable next steps. Recheck and correct outdated claims when the PR changes during review.
2. Append/prepend an entry for that PR in `docs/PR_CHANGELOG.md` explaining changes, tests, evidence limits, and next action. Include the same actual PR number.
3. Update **at least one additional, relevant** project document (`docs/ROADMAP.md`, `README.md`, `docs/WORKFLOW.md`, or a relevant `docs/handoff/*.md`). The prompt and changelog are not substitutes for substantive documentation of the change.
4. Verify tests and required CI for the exact PR HEAD, merge only after success, then verify actual `main` HEAD and post-merge CI. The continuation prompt must instruct a new chat to re-query HEAD because a squash SHA cannot be known before merging.
5. Keep the documentation/evidence boundary explicit: local `TESTED` models, client success responses and HMAC assertions do **not** independently establish NuHost execution, phase order or `DIFF_VERIFIED`.

The PR CI enforces (1)–(3) using `tools/check_pr_handoff.py`, comparing the actual PR base/head files and checking the current PR number in both continuation and changelog. This gate is run from `.github/workflows/tests.yml` before the main tests; do not bypass it. The PR template at `.github/PULL_REQUEST_TEMPLATE.md` provides a reviewer checklist, and `AGENTS.md` tells future assistants to follow the same process.

**Workflow sequence:**

```text
inspect main / CONTINUE_HERE / roadmap
    → implement and test on branch
    → create PR (obtain real PR number)
    → update CONTINUE_HERE + PR_CHANGELOG + relevant docs IN SAME PR
    → CI on exact head
    → merge
    → check main CI
    → ONE consolidated result to user
```

This is a **per-PR** gate, not a separate commit requirement after each low-level coding commit. Multiple related PRs may be completed before a consolidated user response, but every one of those PRs must ship its own fresh handoff and documentation. The separate runtime-evidence branch is not a PR and should not carry source handoff documents.

## Material-commit state rule

Every material code, mechanics, corpus, validation, or research commit must leave the repository documentation consistent with the state introduced by that commit.

When a commit changes any of the following, update the corresponding state documentation in the same logical change whenever practical:

- implemented or closed mechanics;
- evidence status (`DOCUMENTED`, `INFERRED`, `TESTED`, `DIFF_VERIFIED`);
- runtime-verified corpus counts or residual totals;
- cache/schema semantics;
- current investigation target;
- immediate roadmap priorities;
- durable conclusions that a future chat or agent must not have to rediscover.

Use these files as the durable state surface:

- `README.md` — compact entry point and current headline state;
- `docs/ROADMAP.md` — milestones and immediate priorities;
- `docs/COMPILED_CORPUS.md` — compiled corpus contracts, cache semantics and current invariants;
- `docs/handoff/YYYY-MM-DD-*.md` — detailed investigation/runtime handoff when a material workstream changes state.

A documentation-only maintenance commit does **not** recursively require another handoff update merely because the Git SHA changed. The rule applies to semantic/project-state changes, not to bookkeeping recursion.

## Long orchestration commands

Do not paste large multi-stage shell procedures into chat as the primary execution path.

When a server, corpus, validation or deployment operation is long enough to contain multiple stages, error handling, log capture, repeated commands, or non-trivial parsing, preserve it in Git first and make the chat-facing command short and reproducible.

Repository convention:

- `tools/run-*.sh` — orchestration, server-run, corpus-run and validation-gate scripts;
- `tools/diagnostics/` — focused diagnostic programs and bounded research probes.

A chat should normally invoke an existing tracked runner such as:

```bash
bash tools/run-partial-fuel-historical-gate.sh
```

rather than reproducing the runner body inline. Small inspection commands are fine inline. Generated logs and local evidence stay in their established gitignored locations unless a compact durable summary belongs in Git.

## Post-commit verification

After each material commit is integrated into `main`:

```bash
git pull --ff-only origin main
git rev-parse --short HEAD
git status --short
```

The expected end state is the intended GitHub `main` HEAD and no unexplained tracked/untracked files.

If `git status` reports generated corpus data, inspect it before ignoring or committing it. Raw archives, prepared caches and compiled datasets stay local/gitignored; compact manifests, schemas, tests and durable validation summaries may belong in Git according to `docs/ROADMAP.md` and `docs/COMPILED_CORPUS.md`.

## Commit discipline

Prefer one coherent logical change over chains of tiny commits that leave `main` temporarily self-contradictory. When tooling forces multiple sequential commits, finish the sequence by restoring documentation/runtime consistency before starting the next mechanic or investigation.


## Runtime evidence publication

Long archive-host gates should be executed through the generic evidence wrapper
instead of pasting full logs into chat:

```bash
bash tools/run-with-runtime-evidence.sh \
  RUN_NAME \
  --include artifacts/some-gate-v1 \
  -- \
  bash tools/run-some-gate.sh
```

The wrapper:

- preserves the source checkout and never switches it to the evidence branch;
- captures stdout/stderr even when the gate exits non-zero;
- records minimal metadata without environment variables or full command args;
- accepts only explicit include paths under `artifacts/`;
- creates/updates the orphan `runtime-logs` branch via a temporary worktree;
- stores immutable runs under
  `runtime-logs/<run-name>/<UTC timestamp>_<source SHA>/`;
- retries push races;
- preserves the gate's non-zero exit code after successfully publishing failure
  evidence;
- returns 70 only when the gate itself succeeded but evidence publication failed.

The `runtime-logs` branch is machine evidence only. Do not put source code or
durable conclusions there. Accepted conclusions still belong in
`docs/handoff/*-runtime.md` on `main`.

The current combat capture gate has a convenience launcher:

```bash
bash tools/run-combat-capture-reintegration-with-evidence.sh
```

It publishes the FeatureScope, predictive queue, and capture-reintegration
artifact directories together with the outer full log and metadata.
