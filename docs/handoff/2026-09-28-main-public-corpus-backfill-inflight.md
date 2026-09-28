# Main chat transfer — public corpus backfill + capture-side discovery

Date: 2026-09-28

This is the durable handoff for the **primary `main` mechanics/corpus chat**.
It does not replace the separate external-engine research branch.

## Source-of-truth rule

GitHub is authoritative.

A new chat must first inspect the actual current refs and current files rather
than trust SHA values copied from this handoff.

At the time this checkpoint was written:

```text
main
  10a08afdde89ad98587970d81441caf8b6855567
  docs: advance main track to public capture harvest

research/external-engine-analysis
  d306edd4984512efbbe29d97f0ad911ebd3285b3

runtime-logs
  evidence-only orphan branch
```

These SHA values are orientation only. Re-check them.

## Branch responsibilities

### `main`

Owns canonical NuHost reconstruction and official/corpus evidence:

- public corpus acquisition/backfill;
- immutable official Nu archive ingestion;
- FeatureScope / corpus selection;
- capture-side observation harvest;
- discovery/held-out differential work;
- final mechanics promotion.

### `research/external-engine-analysis`

Separate long-lived research branch.

Owns:

- c2ng/c2nu/JHOST/other external engine audits;
- candidate rules and ambiguity maps;
- external provenance/license notes;
- reference-only diagnostic controls.

It must **not** be merged wholesale into `main`.

External implementation remains:

```text
third-party implementation != NuHost evidence
```

Useful findings return to `main` only as bounded candidate hypotheses or
diagnostics that are then tested against official Nu data.

### `runtime-logs`

Evidence publication only.

Do not use it as a development branch.

## Current C5 mechanics state

The ordinary non-capture predictive queue remains closed:

```text
22 / 22 held-out next-VCR transitions exact
0 mismatch
```

Observed ship-capture layers already closed:

```text
capture state/identity continuation          closed
special Tow/Intercept geometry               2 / 2 exact
post-capture candidate graph                 8 / 8 exact
post-capture active membership               8 / 8 exact
post-capture pair eligibility/phase          8 / 8 resolved
pair phase                                   8 / 8 STANDARD
captured-FC phase sensitivity                8 / 8 invariant
```

The current bounded blocker is still:

```text
post-capture ship LEFT / RIGHT side assignment
```

Existing eight-row controls:

```text
opponent_initiator_right                   7 / 8 exact
neutral captured orders + fresh FC         6 / 8 exact
sticky capture side                        4 / 8 exact
frozen T-1 priority                        4 / 8 exact
neutral captured orders + preserved FC     4 / 8 exact
```

Principal current discriminator:

```text
511506 / T26
captured ship27
next opponent ship119
factual prize side RIGHT
```

Do not promote a side rule from these eight rows alone.

Detailed canonical state:

```text
docs/handoff/2026-09-24-combat-capture-runtime.md
docs/handoff/2026-09-28-main-combat-corpus-checkpoint.md
```

## Public validation corpus state

The first independent-public selection targeted 36 large finished games.

The completed second acquisition checkpoint before the current backfill run
had:

```text
selected games      36
compatible/indexed  22
failed              14
snapshots        75,787
transitions      75,463
archive bytes ~5.95 GB
```

The prior broad network-timeout problem had already been solved. The remaining
14 failures at that checkpoint were legacy/binary `.trn` normalization
boundaries.

The acquisition path now supports automatic failed-game backfill from the
already-probed candidate pool:

```text
src/planets_lab/corpus/public_validation_backfill_cli.py
```

Persistent local rejection ledger:

```text
validation/corpus/manifests/public-validation-rejected.json
```

The runner is Docker-based and resumable:

```bash
bash tools/run-public-validation-corpus-with-evidence.sh
```

It reuses:

- discovery manifests/report;
- already downloaded immutable ZIPs;
- prior rejection ledger;
- prior index/stat outputs.

It must not require host Python.

## In-flight local WSL run

The user has **already started** the current acquisition/backfill run from
`main` source commit `10a08afd...`.

Do not ask for the same run to be started again while it is still active.

Observed stdout before this handoff:

```text
PUBLIC VALIDATION CORPUS: BACKFILL PREVIOUS FAILURES

target_games:               36
failed_this_round:          14
rejected_total:             14
successful_before_backfill: 22
replacements_selected:      14
selected_after_backfill:    36

target_by_bucket:
  campaign      19
  championship  6
  finite_fuel   9
  sphere        2

selected_by_bucket_after:
  campaign      19
  championship  6
  finite_fuel   11

missing_bucket_counts:
  sphere        2

replacement_game_ids:
  43082
  441148
  78375
  364412
  658427
  371631
  597910
  396107
  68006
  350094
  416250
  138269
  190004
  190428
```

The run then entered:

```text
PUBLIC VALIDATION CORPUS: DOWNLOAD + INDEX
```

This is **in-flight operator output**, not final published evidence yet.

### What the next chat should do when this run finishes

1. Inspect the newest
   `runtime-logs/public-validation-corpus/...` evidence generated by this run.
2. Read the published:
   - selection/backfill report;
   - rejection ledger;
   - public validation stats;
   - indexed-game manifest.
3. Determine:
   - how many of the 14 replacements indexed successfully;
   - whether another bounded backfill rerun is required;
   - whether Sphere coverage remains missing;
   - whether any selected player slots finally contain non-empty
     `activeadvantages` / `activehulls`.
4. If the run ends non-zero because some replacements are also incompatible,
   do **not** rediscover the 160-game pool. Pull current `main` if needed and
   rerun the same acquisition command; the rejection ledger/backfill path is
   designed for this.
5. Do not delete local archive cache.

## Public capture-side harvester already exists

Current `main` already contains the discovery-only capture-side harvest:

```text
tools/diagnostics/combat_public_capture_side_harvest.py
tools/run-public-capture-side-discovery.sh
tools/run-public-capture-side-discovery-with-evidence.sh
tests/test_combat_public_capture_side_harvest.py
```

The partition is determined **before combat outcomes are inspected**:

```text
~75% discovery
~25% held out
```

The discovery runner only opens discovery games.

Held-out games are listed but remain sealed until a candidate side rule has
been frozen.

Tracked discovery runner:

```bash
bash tools/run-public-capture-side-discovery-with-evidence.sh
```

Do **not** run the held-out partition during side-rule derivation.

### Main-track next step after acquisition stabilizes

Once the current backfill has produced a useful compatible indexed set:

1. run the discovery-only capture-side harvester;
2. inspect only discovery observations;
3. measure:
   - factual prize LEFT/RIGHT counts;
   - capture-side carry;
   - prior same-pair occurrence counts;
   - simple opponent-initiator-right;
   - ruleset/bucket context;
4. combine those official Nu observations with bounded candidate hypotheses;
5. freeze a candidate rule;
6. only then open held-out validation.

The new corpus is intended to increase the number of post-capture ship
continuations and, especially, the number of RIGHT discriminators.

## Current external-engine research branch state

The research branch has advanced independently beyond its initial handoff.

Current useful bounded findings include:

### Side mapping cross-check

Independent Nu VCR consumers:

- Kecupo/planets-vcr-sim;
- ChallengeSY/nu-replayer;
- c2nu;

all preserve literal supplied LEFT/RIGHT orientation. They do not independently
choose Host sides in the audited paths.

Therefore a generic adapter-level LEFT/RIGHT inversion is now a weak
explanation, but an official raw-Nu mapping assertion remains a useful local
diagnostic.

### c2ng global model rejected

Pinned external source:

```text
stefanreuther/c2ng
master@425d623e5d44b017abea50bae4dc9c668870398d
BSD-style 3-clause
```

c2ng suppresses a captured ship as LEFT in its shared Host/NuHost path, so its
global implication is effectively prize RIGHT.

Official Nu observations are currently:

```text
prize LEFT   7 / 8
prize RIGHT  1 / 8
```

Therefore c2ng is already rejected as a **global** Nu capture-side rule.

Its only remaining relevant candidate is narrower:

```text
Can 511506/T26 be reached by continuing the original pre-capture
battle-order cursor (the documented O-layer / "within current order")?
```

The research branch now contains a bounded O-layer reachability probe for that
question.

Do not merge that research diagnostic into canonical mechanics merely because
it matches external c2ng behavior.

Relevant research handoffs:

```text
docs/handoff/2026-09-28-independent-vcr-side-mapping-crosscheck.md
docs/handoff/2026-09-28-official-nu-capture-order-vs-c2ng.md
docs/handoff/2026-09-28-c2ng-post-capture-cursor-candidate.md
docs/handoff/2026-09-28-c2ng-o-layer-probe-ready.md
```

## Evidence boundary for the next main chat

Use external-engine results only through:

```text
external candidate
-> primary Planets.nu documentation if available
-> attributable official Nu observation
-> deterministic local test
-> differential verification
```

The next main chat should prioritize official public-corpus capture-side
discovery over further broad external-engine browsing.

## Working style

- GitHub is the source of truth.
- Use reversible task branches for code changes.
- Run PR CI before fast-forwarding `main`.
- Check exact-main push CI after fast-forward.
- Use Docker for Python/runtime tooling.
- Preserve `combat-planar-no-horwasp` and other explicit FeatureScope
  boundaries unless evidence justifies a change.
- Facts and inferred state must remain separate.
- Do not ask the user to paste logs that have already been published to
  `runtime-logs`.
- For archive-host/WSL runtime work, prepare one versioned runner and have the
  user execute only that runner.

## Immediate handoff summary

At chat transfer time:

```text
main:
  canonical combat/corpus work
  acquisition backfill currently running locally

research/external-engine-analysis:
  separate research work
  c2ng global side model rejected
  bounded T26 original-order cursor candidate prepared

runtime-logs:
  evidence only

main combat blocker:
  post-capture LEFT/RIGHT

next main action:
  wait for current backfill run to finish
  -> inspect published evidence
  -> stabilize compatible public corpus if needed
  -> run discovery-only capture-side harvest
  -> freeze candidate rule
  -> open held-out only after freeze
```
