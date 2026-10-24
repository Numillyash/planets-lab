# Repository instructions for AI agents

These rules apply to **every new branch, material change and pull request** in
`Numillyash/planets-lab`. GitHub `main` is the source of truth. Do not treat
a previous chat summary as a replacement for current repo state.

## Language of interaction

**Always communicate with the user in Russian throughout the conversation**, including progress updates, explanations, questions and the final consolidated report. Keep code identifiers, API names, source quotes and conventional technical names in their original language when appropriate. Repository docs and the continuation prompt should remain readily readable in Russian; do not translate executable commands or file paths.

## Before starting work

1. Read `docs/CONTINUE_HERE.md` **first**. It is the standalone, copy-ready
   prompt for resuming work in a new ChatGPT chat.
2. Read `docs/ROADMAP.md`, `docs/WORKFLOW.md`, and the latest relevant
   `docs/handoff/*.md`; check actual HEAD and CI on GitHub.
3. Preserve source/evidence boundaries and scope. No causal NuHost claims
   from local simulations or client save acknowledgements; fail closed with
   `ABSTAIN` for unsupported interactions.

## Mandatory in EACH pull request (no exceptions for small fixes)

The very same PR must add/update **all three categories** of files:

1. **`docs/CONTINUE_HERE.md`** — rewrite the *entire* prompt to reflect
   what this PR actually added, what CI has and has not verified, the
   exact current PR number, open blockers, boundaries and executable
   next task(s). The prompt must be usable without access to any prior
   conversation. Never put private API keys, personal game orders or raw
   captures in it.
2. **`docs/PR_CHANGELOG.md`** — add a concise entry for the current PR
   number, actual changed behavior, testing/evidence level, and next
   work. Record uncertainty rather than inventing passing CI or a merge SHA.
3. **Meaningful project documentation**, e.g. `docs/ROADMAP.md`,
   `README.md`, `docs/WORKFLOW.md`, or a topic-specific
   `docs/handoff/*.md`. The prompt and changelog do **not** count as
   the required project-documentation update. Keep code, conclusions,
   limits and roadmap consistent.

The GitHub PR CI runs `tools/check_pr_handoff.py` against the exact
PR base/head diff and **fails** if any category is missing, if the
continuation prompt is too thin, or if the current PR number is missing
from the prompt or changelog. Do not bypass or weaken that check.

Create the PR early enough to learn its real number, then update the
prompt/changelog to reference it. Do not insert guessed PR numbers or
unverified CI outcomes. Each additional fix in the same PR must keep
those files current before merge.

## After merge

Verify merged PR state, actual `main` HEAD and post-merge CI.
The already-merged prompt must instruct the next session to re-check
live HEAD/CI, because the final squash SHA is unknowable while
preparing the PR. Do not create an endless bookkeeping PR solely to
paste the post-merge SHA into the same prompt.

## Research and operational guardrails

- Signed V1/V2 owner/client capture does not authenticate server-accepted
  order contents or NuHost phase timing.
- `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`, `TESTED`, and
  `DIFF_VERIFIED` must remain separate evidence levels.
- Do not scan/rebuild the immutable public100 corpus or read frozen
  heldout32 entity records merely to complete a coding stage.
  `CURRENT` remains public68 unless deliberately and separately changed.
- Do not touch unrelated C5 combat or IntelBoard production.
- Runtime evidence belongs on `runtime-logs` as sanitized evidence;
  source, conclusions and durable resume instructions live on `main`.
- User-dependent real-Host evidence and acceptance work remain tracked
  in [issue #247](https://github.com/Numillyash/planets-lab/issues/247).
- Favor substantial coherent work and one consolidated final user report;
  don't stop after every tiny commit/PR unless a blocker requires it.

Detailed process: [Development workflow](docs/WORKFLOW.md).
