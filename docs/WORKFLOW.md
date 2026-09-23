# Development workflow

This repository is maintained as a personal project. Routine changes use short-lived `agent/**` branches, branch CI, and direct integration into `main`; pull requests are reserved for unusually risky or review-heavy changes.

## Source of truth

GitHub `main` is the source of truth for project state. Do not reconstruct current implementation status or priorities from old chat history when the repository documentation is available.

Before continuing substantial work, read:

1. `README.md`;
2. `docs/ROADMAP.md`;
3. the newest relevant file in `docs/handoff/`;
4. `docs/COMPILED_CORPUS.md` when working on historical-corpus or movement validation.

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
