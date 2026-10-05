# Corpus DB public100 compact runtime — 2026-10-05

## Status

The combined public100 compact generation passed the complete exact-parity
storage gate and is published as an immutable validation generation.

Runtime evidence:

    runtime-logs/corpus-db-public100-compact/
    20261005T021608Z_e8b05935f843

Source commit:

    e8b05935f84336a47105c1025f25cd5de18578f8

## Published generation

    generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb

SHA256:

    3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c

Schema:

    planets-lab.corpus-db.v2.compact1

Corpus fingerprint:

    7578e4b559b46f7a140179d4c4ca2a924bc83409b79cdb058a2df69c05553d22

## Population and exact parity

    source archives                  100
    source archive bytes     16820204641
    source members                224014
    ZIP members                   224014
    decoded semantic JSON    238278126158
    entity rows                541348959

Full semantic parity:

    checked                       224014
    failed                             0
    mismatches                         0

Build runtime:

    import wall seconds        31588.8926
    parity wall seconds        21282.1803
    import peak RSS bytes     25624756224
    parity peak RSS bytes     25880875008

## Physical result

    database bytes             28616175616
    database GiB                  ~26.651

    DB / source ZIP                ~1.701x
    DB / decoded semantic JSON     ~0.1201x
    reduction vs decoded JSON      ~87.99%

Compact invariants:

    entity_rows table               absent
    decoded_payload_zlib column     absent
    secondary indexes               0

## Bounded queries

Game 233558 T-1/T:

    result rows                     19
    wall seconds                    0.093608
    peak RSS bytes                  154374144

Game 233558 VCR/site:

    result rows                      3
    wall seconds                    0.029267
    peak RSS bytes                  125259776

## Shared read gate

The same public100 generation opened concurrently from:

- normal planets-lab reader;
- external research reader.

Result:

    explicit_shared_generation_concurrent_read: PASS

## CURRENT

The build deliberately preserved canonical CURRENT:

    generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb

Public100 is a validated immutable prospective-validation generation. It is not
yet the canonical active backend.

Do not activate public100 before the prospective post-independent capture-side
gate is reviewed.

## Prospective mechanics path

The fresh 32-game population remains sealed for the frozen Kill-sensitive
capture-side candidate.

The validation workflow opens public100 explicitly and does not consult CURRENT:

    tools/run-public-postindependent-prospective-validation-with-evidence.sh

The gate requires:

    zero candidate mismatches
    zero unresolved adjacent rows
    fresh LEFT + numeric group-0 + Kill coverage
    fresh LEFT + numeric group-0 + non-Kill coverage

Possible terminal statuses include:

    FAILED_MISMATCH
    INCOMPLETE_UNRESOLVED
    INSUFFICIENT_DISCRIMINATOR_COVERAGE
    PASS_PROSPECTIVE_VALIDATION

Only PASS_PROSPECTIVE_VALIDATION sets promotion_ready=true.

## Raw source archive policy

The 100 selected source ZIP archives have completed their oracle role: public100
has 224014/224014 exact semantic parity.

The prospective mechanics workflow uses only:

- the small manifest/index metadata;
- the explicit validated public100 DuckDB.

Therefore selected public100 source ZIPs may now be removed with:

    bash tools/cleanup-public100-source-archives.sh
    bash tools/cleanup-public100-source-archives.sh --apply

The cleanup is guarded by the exact public100 SHA256 and deletes only game ZIPs
listed in the exact 100-game combined manifest. It does not remove manifest or
index metadata.

This intentionally accepts loss of local rebuild-from-ZIP capability. Public
games can be reacquired later if a future storage migration requires a new raw
oracle.
