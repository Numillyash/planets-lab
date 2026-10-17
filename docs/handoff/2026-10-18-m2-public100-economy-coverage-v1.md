# M2: reuse the existing public100 corpus — coverage V1

## Motivation / provenance

The existing immutable public100 compact DuckDB is not a small HAR
sample: 100 games, 224,014 player-turn perspective snapshots,
541,348,959 typed entity rows, 26.65 GiB. Its exact SHA256:

    generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb
    3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c

Publication independently confirmed 224,014/224,014 exact semantic
parity against original archived TRNs. DO NOT build another database,
redownload hundreds of games, or change the canonical CURRENT.

## Critical: prospective 32-game holdout is SEALED

public100 combines a 68-game established baseline and 32
game-disjoint prospective heldout games. Under our existing
docs/corpus-db/SHARED_ACCESS.md research boundary, reading a heldout
for mechanics inference would contaminate future independent tests.

**This script enumerates only metadata for ALL 100 games**, and
reconstructs individual entity payloads ONLY for game IDs from
the pre-existing baseline 68 manifest:

    validation/corpus/manifests/public-short-expansion-with-public36.jsonl

The manifest MUST exist, have exactly 68 unique valid game IDs,
and its SHA256 is recorded in the output. No sampling is allowed
when the baseline manifest is absent or malformed.

## What the diagnostic measures

1. Verify the 26.65-GiB explicit database SHA256.
2. Open with DuckDB read_only=True; NEVER read or change CURRENT.
3. Read the small source_members metadata table for all games:
   count games, player-turn perspectives, archive/embedded-turn
   mismatches, duplicate ambiguous identities, same-perspective
   adjacent T-1/T pairs.
4. BEFORE decoding entity data, select a bounded deterministic
   across-game, across-time sample FROM BASELINE68 ONLY. Default
   2 T-1/T same-perspective pairs per game, maximum 136 pairs.
5. Decode these original member pairs with the repository's existing
   compact reader. Validate payload game/turn/player identity.
6. Count genuine owner-current planet pairs only if both planets
   have identical planet ID and source player ID as owner, and
   infoturn == actual archive turn. Stale/non-owner/duplicate
   rows are excluded, not silently converted to current facts.
7. Count data availability and mere T-1/T differences in MC,
   supplies, surface and ground minerals, population, structures,
   taxation. Count source ship and starbase section coverage too.

Outputs are aggregate-only, with no game ID, player identity,
notes, chat messages or private orders.

**IMPORTANT:** public archived TRN is a game STATE snapshot, not a
complete, independently authenticated pre-Host TurnOrders record.
The diagnostic is a coverage census, NOT an economic production,
cargo-transfer or build-cost mechanism verification. A net
T-1/T difference includes unobserved player actions AND Host
phases; do not infer causes.

## One-command use on existing server

After PR merge, on the corpus server:

    cd /root/projects/planets-lab &&
    git fetch origin &&
    git switch main &&
    git pull --ff-only origin main &&
    bash tools/run-m2-public100-economy-coverage-v1.sh

The runner uses existing Docker Compose lab service with
compose.corpus-db.yaml, which mounts /corpus-db READ-ONLY. The
importer/writer service is NOT invoked. Output:

    artifacts/planetary/m2-public100-economy-coverage-v1/report.json

The runner verifies CURRENT unchanged and refuses to overwrite an
existing report. SHA256 of 26.65 GiB incurs a full sequential read;
subsequent T-1/T entity sampling is bounded. No network API
requests, no user gameplay changes and no new corpus generation.

Optional fast pilot (still inventories all 100 games in metadata):

    M2_CORPUS_MAX_GAMES=8 M2_CORPUS_PAIRS_PER_GAME=1 bash tools/run-m2-public100-economy-coverage-v1.sh

Use a fresh output path for subsequent invocations; do not remove
prior evidence just to rerun. The sample is not full evaluation
of every game entity: it establishes coverage and admissible
denominators for later scaling, rather than claiming 541M rows
were all individually rescored for economics.

## Next gates

- Study actual sample status counts and source coverage before
  deciding whether and where to expand sampling.
- Build on the earlier public8 observational baseline:
  617 qualified net-stock pairs, 215 all-family exact, 402
  non-exact. None provides independent Host order evidence.
- Maintain separate evidence types for archived owner-current
  snapshots, user-authorized client save/witness streams,
  and Host-executed next-turn results. Never equate them.
- No C5 changes, heldout contamination, corpus CURRENT switch,
  production IntelBoard integration or draft PR #28 mutation.

This is a new M2 corpus coverage tool, not a new simulator formula.
