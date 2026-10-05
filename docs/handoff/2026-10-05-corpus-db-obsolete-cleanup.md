# Corpus DB obsolete-generation cleanup — 2026-10-05

## Decision

The compact1 storage model is accepted and active.

Current active backend:

    generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb

First rollback backend retained:

    generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb

The following generations are obsolete and may be deleted:

    generations/corpus-v1-g233558-20260930T041155Z-8e2e7416675d.duckdb
    generations/corpus-v1typed-g233558-20260930T143229Z-8e2e7416675d.duckdb
    generations/corpus-v1typed-public36-20260930T211714Z-11cd75fa918d.duckdb

Historical recorded sizes:

    v1 game-233558            11869892608 bytes
    typed1 game-233558        3058970624 bytes
    typed1 public36          38931017728 bytes

Total historical obsolete generation bytes:

    53859880960 bytes
    ~50.161 GiB

The exact local freed size may differ slightly if some generations or stale
typed staging files were already absent.

## Guarded cleanup

Use:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db

    bash tools/cleanup-obsolete-corpus-db-generations.sh

The first run is dry-run only. It checks:

- CURRENT is the accepted public68 generation;
- active public68 exists and matches its canonical SHA256;
- compact public36 rollback exists and matches its canonical SHA256;
- only exact obsolete generation names are candidates for deletion;
- old typed staging files and public36/public68 compact schema/parity checkpoints
  are listed separately.

Apply only after reviewing the dry-run output:

    bash tools/cleanup-obsolete-corpus-db-generations.sh --apply

The apply pass re-checks CURRENT and retained-generation existence after cleanup
and prints actual freed bytes.

## Raw archive retention

The user has decided that immutable ZIP/TRN source archives do not need
long-term retention once their replacement compact database has passed full
semantic parity.

However, do not delete the current corpus cache yet.

The pending public100 compact build still reads all 100 source ZIP archives and
performs exact reconstruction parity against them. Deleting the archive cache
before this build would make the current builder unable to construct and prove
public100.

Therefore the cleanup order is:

1. delete obsolete DB generations now;
2. build public100 from the existing 100 archive cache;
3. complete 100/100 exact semantic parity and prospective mechanics validation;
4. only then delete the corresponding ZIP/TRN corpus cache through a separate
   guarded source-cleanup step.

The post-public100 cleanup may also retire compact public36 after public100 is
eventually activated and public68 becomes the retained rollback generation.

Do not delete:

    compact public68 while it is CURRENT
    compact public36 before public100 is activated
    validation/corpus/cache/loadall before public100 parity is complete
