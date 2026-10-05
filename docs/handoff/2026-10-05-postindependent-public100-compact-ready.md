# Post-independent public acquisition runtime and public100 compact decision — 2026-10-05

## Acquisition provenance

Runtime evidence:

    runtime-logs/public-postindependent-validation-acquisition/
    20261004T224830Z_451652986ca3

Source commit:

    451652986ca32483db6b25beab2ada1f801f2dab

Acquisition profile:

    baseline games      68
    fresh selected      32
    combined games     100
    final turn        80..180
    slots              8..16
    loadinfo probes      320

The acquisition completed successfully:

    exit_code             0
    ingest_rc             0
    games_indexed        32
    games_failed          0
    snapshots         54445
    transitions       54099
    canonical_ok      53890
    canonical_failed    555

Fresh selected bucket composition:

    campaign        14
    championship     4
    finite_fuel     11
    sphere           3

## Backfill history

The first ingest pass indexed 19/32 and rejected 13 legacy/binary turn archives.

Round 1 replacements:

    78459
    326221
    94061
    247785
    230354
    172898
    400330
    257908
    296210
    283648
    23864
    169417
    38553

Round 2 replacements:

    62882
    79765
    181660
    172010
    530635
    600032

Round 3 replacements:

    52579
    117234
    290067
    195002

Round 4 replacements:

    27068
    158042
    281994

Round 5 replacements:

    597079
    490865

Final rejected game IDs:

    23864
    27068
    38553
    51327
    52579
    62882
    78459
    79765
    80058
    85894
    89497
    94061
    117234
    134382
    138322
    142157
    158042
    164693
    169417
    171253
    172010
    172898
    181660
    185114
    190434
    195002
    199300
    202362

The fifth round restored the target exactly:

    selected_after_backfill = 32
    missing_bucket_counts   = {}

## Physical-size result

Fresh32 source ZIP total:

    archive_bytes = 4164827657
                  = ~3.879 GiB

The prior compact expansion provides an empirical incremental size coefficient.

public36:

    source ZIP bytes = 9456773573
    compact DB bytes = 13189001216

public68:

    source ZIP bytes = 12655376984
    compact DB bytes = 17847300096

Increment public36 -> public68:

    source ZIP delta = 3198603411
    compact DB delta = 4658298880
    compact / source incremental ratio = ~1.456354x

Applying that observed incremental ratio to the fresh32 acquisition gives:

    projected compact increment = ~6065463428 bytes
                                = ~5.649 GiB

Projected public100 total:

    ~23.913 GB
    ~22.270 GiB

The intended ~5 GiB expansion target is explicitly approximate, not a hard
acceptance threshold. A projected +5.65 GiB is close enough that preserving all
32 independently selected games is preferable to discarding validation breadth
for roughly 0.6 GiB of predicted savings.

Decision:

    KEEP ALL 32 FRESH GAMES

No selected-manifest reduction is warranted before the compact build.

## Public100 compact gate

Tracked runner:

    tools/run-corpus-db-public100-compact.sh

Runtime-evidence wrapper:

    tools/run-corpus-db-public100-compact-with-evidence.sh

The runner checks before the expensive import:

    public68 baseline count              68
    fresh selected count                 32
    combined count                      100
    baseline/selected game-ID overlap     0
    combined == baseline union selected

It requires at least 55 GiB free in the shared corpus root by default. This is a
safety floor for staging + publication, not a predicted final database size.

The build uses:

    validation/corpus/manifests/public-postindependent-validation-with-public68.jsonl

and publishes a new immutable compact1 generation matching:

    generations/corpus-v2compact-public100-*.duckdb

The gate verifies after publication:

    schema = planets-lab.corpus-db.v2.compact1
    source archives = 100
    compact_build_state expected archives = 100
    entity_rows absent
    decoded_payload_zlib absent
    secondary indexes = 0
    T-1/T query works
    VCR/site query works
    normal + external concurrent explicit read works

Critical invariant:

    CURRENT MUST NOT CHANGE

The canonical public68 CURRENT remains active until the prospective
post-independent capture-side validation against the fresh32 population has been
run and reviewed.

## Next runtime

After this checkpoint is merged to main:

    cd ~/projects/planets-lab
    git switch main
    git pull --ff-only origin main
    echo "HEAD:   $(git rev-parse HEAD)"
    echo "REMOTE: $(git rev-parse origin/main)"

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db

    bash tools/run-corpus-db-public100-compact-with-evidence.sh

Do not activate public100 after the build.

The build is resumable. If interrupted before publication, rerun the same
wrapper; the compact staging state and schema checkpoints are reused.

After runtime publication, inspect the new:

    runtime-logs/corpus-db-public100-compact/<run-id>

from GitHub. Record actual DB bytes, source members, fingerprint, SHA256, query
checks, shared-read status and confirmation that CURRENT stayed on public68.

Only then freeze/run the prospective capture-side validation against the
fresh32 population. Do not inspect its capture outcomes before the validation
protocol is fixed.
