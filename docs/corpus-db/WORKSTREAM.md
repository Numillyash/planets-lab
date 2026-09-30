# Corpus DB v1 workstream

Branch:

    feature/corpus-db-v1

Created from main:

    2cc98e3cab3cc0ce0dbdb48f032e9650029f8273

This branch owns storage infrastructure only. Do not promote NuHost mechanics
from it.

## First milestone

Prototype only on game-233558.

Deliver:

1. shared PLANETS_CORPUS_DB_ROOT contract and mounts for both research
   containers;
2. direct ZIP-to-DuckDB importer without full extraction to disk;
3. v1 direct-mirror schema preserving player/perspective/turn/source provenance;
4. lossless handling of unknown/untyped fields;
5. semantic round-trip validator for every TRN member in game-233558;
6. indexes/query helpers for game/player/turn/entity and VCR/site access;
7. disk/time/RSS benchmark report;
8. concurrent read-only test from normal and external containers.

Do not add deltas/dedup in this milestone.

## Acceptance gate

- original ZIP remains untouched;
- every member in game-233558 passes semantic parity;
- same published DB opens read-only from both containers simultaneously;
- active generation requires no writer for normal queries;
- narrow queries avoid whole-game JSON/Python materialization;
- DB footprint, runtime and peak RSS are recorded;
- storage backend alone does not alter mechanics results.

Only then scale to the 36-game public corpus.

Keep ZIP backend available as an oracle during migration.


## Implementation checkpoint

The first v1 prototype implementation is now tracked in:

- `src/planets_lab/corpus/corpus_db.py`;
- `src/planets_lab/corpus/corpus_db_cli.py`;
- `compose.corpus-db.yaml`;
- `tools/run-corpus-db-game233558-prototype.sh`;
- `tools/run-corpus-db-shared-read-check.sh`;
- `tests/test_corpus_db.py`;
- `docs/corpus-db/IMPLEMENTATION_V1.md`;
- `docs/corpus-db/BENCHMARK_GAME_233558.md`.

This does not close the milestone. The canonical archive-host game-233558 run
must still produce zero semantic-parity failures and the required size/time/RSS
and concurrent-reader measurements before any 36-game scale-out.
