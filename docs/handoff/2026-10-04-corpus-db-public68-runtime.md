# Corpus DB public68 compact runtime — 2026-10-04

## Status

The combined public68 compact build gate is closed successfully.

Source runner:

    tools/run-corpus-db-public68-compact.sh

Source manifest:

    validation/corpus/manifests/public-short-expansion-with-public36.jsonl

The build preserved the active public36 CURRENT throughout the gate.

## Published immutable generation

    generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb

SHA256:

    5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a

Schema:

    planets-lab.corpus-db.v2.compact1

Corpus fingerprint:

    09f71721b77cd1875932f75ed515636d9b79720bcc520aff72d6f9dd51f8fbf7

## Corpus gate

    source archives                 68
    source archive bytes            12655376984
    source members                  169569
    ZIP members                     169569
    decoded semantic JSON bytes     179227392513
    entity rows                     407020572

Full semantic parity:

    checked                         169569
    failed                          0
    mismatches                      0

Build runtime:

    import wall seconds             24467.464031526993
    parity wall seconds             16500.98172742303
    peak RSS bytes                  18496663552

## Published size

    database bytes                  17847300096
    database size                   ~16.622 GiB
    compact / decoded JSON          ~9.958%
    compact / source ZIP            ~1.410x

Semantic residual:

    inline top-level JSON bytes     1029774955
    missing residual rows           79501479
    missing residual bytes          1983602099

Largest missing-residual sections:

    planets                         1338296784
    scores                           319730659
    minefields                       189391706
    players                          114608050
    torpedos                          21574900

This remains the same accepted compact1 physical model. The corpus expansion
does not reopen storage-model optimization.

## Physical gate

    entity_rows table               absent
    decoded_payload_zlib column     absent
    secondary indexes               0

## Bounded queries

Game 233558 T-1/T:

    wall seconds                    0.0808044970035553
    peak RSS bytes                  153317376
    result rows                     19

Game 233558 VCR/site:

    wall seconds                    0.02695749799022451
    peak RSS bytes                  119791616
    result rows                     3

## Shared read gate

The same immutable public68 generation opened concurrently from:

- normal planets-lab reader;
- external research reader.

Result:

    explicit_shared_generation_concurrent_read: PASS

## CURRENT state after build

CURRENT remains:

    generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb

This is deliberate. The public68 generation is published and verified but not
active until a guarded activation is run.

## Guarded activation

Use only:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/activate-corpus-db-compact-public68.sh

The activation runner validates:

- exact generation SHA256;
- compact schema id;
- 68 source archives;
- 169569 source members;
- exact corpus fingerprint;
- absence of entity_rows;
- absence of decoded_payload_zlib;
- zero secondary indexes.

It then atomically switches CURRENT and runs the normal + external shared-read
verification. If the post-switch read gate fails, it automatically restores the
previous CURRENT and verifies rollback.

Do not delete the public36 generation after activation. Retain it as the first
rollback backend until the public68 active-runtime checkpoint is closed.
