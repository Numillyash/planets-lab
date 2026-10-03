# New chat handoff: post-heldout capture side + short public corpus

Date: 2026-10-03

GitHub is the source of truth. Do not trust SHAs copied from chat without
checking current refs first.

## Repositories / branches

Canonical mechanics / corpus repository:

    Numillyash/planets-lab
    branch: main

External-engine evidence repository workstream:

    Numillyash/planets-lab
    branch: research/external-engine-analysis

Do not merge external-engine implementation evidence into canonical NuHost
mechanics without the normal evidence boundary.

## Shared Corpus DB

Host root:

    /root/projects/planets-corpus-db

Container root:

    /corpus-db

Canonical public corpus is selected by:

    /root/projects/planets-corpus-db/CURRENT

The last known public36 compact generation is:

    generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb

Always read CURRENT at runtime instead of hard-coding the last-known path.

Corpus DB must be opened read-only for mechanics diagnostics. Raw ZIP/TRN
archives remain immutable oracle material and should not be the normal
corpus-wide query backend.

## Capture-side mechanics state

The pre-heldout frozen side candidate was frozen at:

    cd87f9505472e5e396db28a7d6f7c67c561f9c64

Its independent held-out gate failed:

    adjacent heldout rows       29
    exact                       27
    mismatch                     1
    unresolved                   1

True side counterexample:

    game 476380
    turn 223
    capture VCR 903 -> next VCR 904
    captured ship 157
    next opponent 514
    capture prize side LEFT
    factual next prize side RIGHT
    opponent STANDARD priority [0, 24, 514]

Repeated-capture unresolved:

    game 257776
    turn 230
    ship 71
    VCR 1644 -> 1645 -> 1646

That repeated-capture case is explained by the already verified second
occurrence side reversal for pair ship71/ship153; the temporary owner has no
meaningful T-1 state because ownership changed earlier in the same combat phase.

After opening discovery + former heldout, the current post-heldout research
candidate fits all 60 adjacent rows:

    reachable sticky                    20/20
    nonreachable neutral/fresh-FC       38/38
    second-occurrence reversal           1/1
    reachable numeric-opponent override  1/1
                                         -----
                                         60/60

Implementation:

    tools/diagnostics/combat_public_capture_side_postheldout_candidate.py

Status is explicitly:

    POST_HELDOUT_CANDIDATE_NOT_CANONICAL

Do not promote this 60/60 fit as validation. The former heldout directly
informed the last two branches. A new independent population is required.

Key handoffs:

    docs/handoff/2026-10-03-public-capture-side-heldout-result.md
    docs/handoff/2026-10-03-postheldout-capture-side-candidate.md
    docs/handoff/2026-10-03-public-capture-side-residual-reporter.md

## New independent short public corpus

A new bounded public acquisition workstream was added so the next validation
population does not overlap public36 and avoids 300+ turn monsters.

Current default profile:

    selected games     32
    min final turn     55
    max final turn     140
    min slots           8
    max slots          16
    loadinfo probes   240

Runner:

    tools/run-public-short-expansion-with-evidence.sh

Acquisition namespaces:

    validation/corpus/manifests/public-short-expansion-candidates.jsonl
    validation/corpus/manifests/public-short-expansion-selected.jsonl
    validation/corpus/manifests/public-short-expansion-with-public36.jsonl
    validation/corpus/index/public-short-expansion-games.jsonl
    validation/corpus/index/public-short-expansion-stats.json
    artifacts/public-short-expansion/

The public36 selected manifest is used as baseline, therefore old public36 game
IDs are excluded.

The first short-expansion runtime was intentionally interrupted by the user
while download/index was running. Runtime evidence was successfully published:

    runtime-logs/public-short-expansion/
    20261003T185443Z_6b07c0e7e914

Metadata:

    exit_code          130
    interrupted_signal INT

The discovery/selection stage completed before interruption. The selection
report shows:

    listed_games       8680
    eligible_games     5025
    probed_games        240
    successful_loadinfo 240
    selected_games       32
    combined_games       68

The rerun should reuse the existing discovery manifests/report because the
short runner defaults REUSE_DISCOVERY=1. Existing successful ZIP/cache/index
material should also be reused by the acquisition pipeline.

Do not build the new compact DuckDB until acquisition/index completes and real
archive/snapshot totals are known. The intended compact DB size is
approximately five GiB, not a strict threshold.

Compact build runner already exists:

    tools/run-corpus-db-public-short-expansion-compact.sh

It publishes a separate generation under the shared corpus root and checks
that canonical CURRENT is unchanged.

## Immediate next action

First verify current GitHub main independently.

Then on the local WSL checkout:

    cd ~/projects/planets-lab
    git switch main
    git pull --ff-only origin main
    echo "HEAD:   $(git rev-parse HEAD)"
    echo "REMOTE: $(git rev-parse origin/main)"

    bash tools/run-public-short-expansion-with-evidence.sh

Expected behavior on the resumed run:

    discovery: reuse existing manifests/report

Then continue download/index/backfill. Do not start the compact build yet.

After the run completes, inspect the newly published runtime-logs evidence
directly from GitHub rather than asking the user to paste a large log. Determine:

    games_indexed
    games_failed
    totals.archive_bytes
    totals.snapshots
    selected/replacement game IDs
    final selected count

Then choose whether to keep all 32 games or reduce the selected manifest before
building the compact generation to land near the requested ~5 GiB DB size.

## Private prospective corpus

The user also has private game 686764 with a controlled Colony/Gemini-derived
Gemtriot test ship. This is valuable prospective evidence, but private/live
ingestion is not yet implemented.

Do not append private mutable data into immutable public36. Planned design is a
separate private/live corpus generation storing sanitized full loadturn/RST
snapshots so combat VCR/settings/catalog/order context are preserved.

The short public corpus is the immediate priority; private game ingestion can
follow after acquisition is stable.

## Workflow expectations

Work autonomously through GitHub. For repository changes:

1. verify actual refs;
2. branch from actual main;
3. make the bounded change;
4. run PR CI;
5. fast-forward the tested exact SHA into main;
6. verify exact-main push CI.

Only ask the user to run a local command when WSL/Docker/archive runtime is
actually required. Runtime evidence already on runtime-logs should be inspected
from GitHub instead of asking for pasted logs.
