# Main public corpus — automatic backfill round 2 runtime

Date: 2026-09-28

## Canonical runtime

Published evidence:

```text
runtime-logs/public-validation-corpus/20260928T164728Z_ec20195891e9
source_branch: main
source_commit: ec20195891e937a65897a991c405de88c439b036
exit_code: 1
started: 2026-09-28T16:47:28Z
finished: 2026-09-28T17:48:09Z
```

The operator checkout was verified before launch:

```text
branch: main
HEAD:   ec20195891e937a65897a991c405de88c439b036
REMOTE: ec20195891e937a65897a991c405de88c439b036
```

This is canonical main evidence. It supersedes the earlier accidental
noncanonical research-branch rerun for acquisition state.

## Round-2 backfill result

Input state:

```text
compatible before round: 30
failed before round:      6
rejected before selection:20
```

Selected replacements:

```text
22158
124766
164693
633855
476380
76301
```

Successful:

```text
476380
633855
```

Failed as legacy/binary non-UTF-8 `.trn`:

```text
22158
76301
124766
164693
```

Final indexed population:

```text
games_indexed        32 / 36
games_failed          4
snapshots        114209
transitions      113698
canonical_ok     112560
canonical_failed   1649
settings_hashes      32
archive_bytes 8455277299
```

No network error remains as the final cause for any of the four failures.

## Coverage state

The original selector target remains:

```text
campaign       19
championship    6
finite_fuel     9
sphere          2
```

The replacement selection still reports:

```text
campaign       19
championship    6
finite_fuel    11
missing sphere  2
```

This is a selector-bucket gap, not absence of raw Sphere settings. Several
selected records have `settings.sphere=true`, but campaign/championship bucket
precedence classifies them elsewhere.

Capability metadata remains empty:

```text
non-empty activeadvantages slots  0
non-empty activehulls slots        0
```

That remains a separate corpus-coverage gap from the active combat blocker.

## Acquisition orchestration improvement

Discovery already produced 159 successful `loadinfo` candidate records.
Manual one-round reruns therefore add operator latency without adding evidence.

The tracked acquisition runner is changed to perform a bounded automatic loop:

```text
backfill from previous stats, if present
-> ingest
-> if failures remain:
     consume fresh stats
     append new failures to rejection ledger
     select replacements
     ingest again
-> repeat
```

Default bound:

```text
MAX_BACKFILL_ROUNDS=6
```

The loop exits on:

- full ingest success;
- candidate shortfall;
- fatal backfill error;
- `AUTO_BACKFILL != 1`;
- the round cap.

The immutable archive cache remains untouched. Previously successful games are
reused from cache.

## Next action

After this tooling commit reaches main, run the same canonical command once:

```bash
bash tools/run-public-validation-corpus-with-evidence.sh
```

It should absorb the four current failed ids and continue through additional
replacement rounds in the same evidence run if more binary archives are found.

If the selection converges to a useful stable compatible population, proceed
directly to the existing discovery-only capture-side runner:

```bash
bash tools/run-public-capture-side-discovery-with-evidence.sh
```

Held-out capture-side games remain sealed until a candidate rule is frozen.

## Combat mechanics boundary

No C5 mechanic is promoted by this checkpoint.

The active canonical blocker remains post-capture ship LEFT / RIGHT assignment.
External-engine findings remain candidate generators only.
