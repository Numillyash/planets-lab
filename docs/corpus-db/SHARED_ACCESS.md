# Corpus DB shared access contract

The corpus DB is a third storage entity shared by both research containers.

It is not owned by either checkout and must not be duplicated per container.

## Host setup

Example:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    mkdir -p "$PLANETS_CORPUS_DB_ROOT"/{generations,manifests,staging}

Use the same absolute host path from both checkouts.

Inside both containers:

    /corpus-db

## Concurrency

Published generations are immutable/read-only.

The normal mechanics container and external-reference container may query the
same published DB concurrently.

The active generation never has a writer.

Build/publish flow:

    raw ZIP evidence
      -> one writer
      -> /corpus-db/staging/<build>.duckdb
      -> parity/integrity validation
      -> close writer
      -> publish immutable generation
      -> atomically update CURRENT
      -> concurrent read-only consumers

Consumers keep reading the previous generation while a new staging generation
is built.

## Mount policy

Consumer:

    ${PLANETS_CORPUS_DB_ROOT}:/corpus-db:ro

Importer:

    ${PLANETS_CORPUS_DB_ROOT}:/corpus-db:rw

The importer writes only to a new staging path.

The workstream should provide reproducible compose overrides/helpers for both
checkouts.

## Research boundary

Storage conversion may mechanically ingest held-out members for storage parity,
but that does not authorize mechanics inference on sealed held-out data.
DB-backed diagnostics must preserve the same discovery/held-out filters as their
archive-backed equivalents.
