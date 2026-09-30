# Corpus DB v1 — game-233558 prototype benchmark

Status: runner and measurement hooks implemented; canonical archive-host runtime pending.

This file is intentionally not pre-filled with guessed values. The first accepted result must come from the immutable cached `game-233558.zip` on the archive host and a published v1 generation produced by the tracked runner.

## Required runtime

```bash
cd ~/projects/planets-lab
git switch feature/corpus-db-v1
git pull --ff-only origin feature/corpus-db-v1

export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
bash tools/run-with-runtime-evidence.sh \
  corpus-db-game233558-prototype \
  -- \
  bash tools/run-corpus-db-game233558-prototype.sh
```

The corpus DB itself remains outside Git/runtime-evidence branches. The evidence wrapper captures only command output/metadata unless an explicit safe artifact path is added later.

## Acceptance measurements

Record from the canonical run:

```text
source ZIP bytes:                  PENDING
unpacked decoded JSON bytes:       PENDING
published DuckDB bytes:            PENDING
one-time import wall seconds:      PENDING
one-time importer peak RSS bytes:  PENDING
TRN members parity checked:        PENDING
parity failures:                   PENDING
T-1/T query wall seconds:          PENDING
T-1/T query peak RSS bytes:        PENDING
VCR/site query wall seconds:       PENDING
VCR/site query peak RSS bytes:     PENDING
normal+external concurrent read:   PENDING
```

## Green gate

The game-233558 prototype is green only if all of the following hold:

```text
parity failures == 0
parity checked == every canonical playerN-turnM.trn in the ZIP
archive integrity validation == green
CURRENT points to the newly published immutable generation
normal planets-lab reader == green
external-engine-analysis reader == green
both readers overlap while opening the same generation
```

Size/time/RSS are measurements, not pass/fail thresholds for v1. They are used to decide whether the direct mirror is already sufficient or whether a later storage format iteration is justified.

Until this file contains a canonical green runtime, do not import the 36-game corpus and do not migrate mechanics diagnostics to the DB backend.