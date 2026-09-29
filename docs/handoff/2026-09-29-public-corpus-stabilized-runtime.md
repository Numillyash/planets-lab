# Public validation corpus stabilized at 36 / 36

Date: 2026-09-29

## Canonical runtime

Published evidence:

```text
runtime-logs/public-validation-corpus/20260929T150456Z_253258f5f870
source_branch: main
source_commit: 253258f5f870d095144b45feefb0f06d82b30156
exit_code: 0
started: 2026-09-29T15:04:56Z
finished: 2026-09-29T15:41:13Z
elapsed: 36m17s
```

The bounded acquisition loop converged before the 24-round cap.

## Final compatible population

The first fourteen replacements in this run did not close the final slot. They
were rejected either by the known legacy/binary non-UTF-8 boundary or by
archive-download timeout. On round 15, game `306971` (Aranumia Sector) was
selected and indexed successfully from the network.

Final corpus:

```text
selected games        36
indexed games         36
failed games           0
snapshots         126418
transitions       125862
embedded consecutive 125698
canonical ok      124514
canonical failed    1904
settings hashes       36
archive bytes  9456773573
```

The final replacement contributed:

```text
game_id             306971
snapshots             3817
transitions            3806
canonical ok           3817
canonical failed          0
source               network
```

The persisted rejected ledger contains 56 game ids after the pre-round-15
backfill state. The final stats contain no failed game ids.

## Coverage notes

The selector's explicit bucket accounting still reports:

```text
target sphere                2
selected sphere bucket       0
missing sphere               2
```

This is still a bucket-precedence issue, not absence of raw Sphere settings.
Nine selected games have `settings.sphere=true` but classify into
higher-precedence campaign/championship/finite-fuel buckets.

Capability metadata also remains absent:

```text
selected player slots                 556
non-empty activeadvantages slots        0
non-empty activehulls slots             0
```

Neither gap blocks the current C5 capture-side research objective.

## Performance result

The same pipeline that previously required multi-hour repeated corpus
derivation now reuses the 35 stable per-game index records. The earlier
six-round validation completed in 2m52s. This converging run took 36m17s because
some replacement archives incurred repeated network timeouts and the successful
round-15 replacement required one real full ingest. No successful cached game
was fully re-derived.

The 24-round default bound is sufficient for this population and should remain
unchanged unless future evidence shows candidate exhaustion or a materially
different failure distribution.

## Acquisition gate

The public validation acquisition gate is now closed for the active C5 task:

```text
PUBLIC VALIDATION CORPUS = 36 / 36 compatible
```

Do not continue backfill merely to increase the archive count.

## Next mechanics action

Proceed to the existing discovery-only post-capture LEFT/RIGHT harvest:

```bash
bash tools/run-public-capture-side-discovery-with-evidence.sh
```

The runner must:

- execute from canonical `main` by default;
- use the stabilized selected manifest and index;
- scan only the deterministic `discovery` partition;
- never inspect or emit held-out rows before a candidate side rule is frozen.

After discovery evidence is published, analyze only the discovery artifact,
derive/freeze a candidate side-assignment rule, and only then run a separate
held-out validation path.
