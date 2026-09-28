# Main public corpus — automatic backfill round 1 runtime

Date: 2026-09-28

This is the durable main-track checkpoint for the public validation corpus run
published after the earlier in-flight handoff.

## Source of truth

GitHub remains authoritative. Re-check current refs before using copied SHA
values.

Runtime evidence:

```text
runtime-logs/public-validation-corpus/20260928T042502Z_10a08afdde89
runtime branch HEAD at inspection: 9fa76d926260162c4d29ac12aeccdd054dd485bd
source branch: main
source commit: 10a08afdde89ad98587970d81441caf8b6855567
exit_code: 1
started: 2026-09-28T04:25:02Z
finished: 2026-09-28T05:27:03Z
```

The current GitHub main had already advanced documentation-only to
`36a4b5bcb734c4e7d77fec4fac2cd4ddb14e060b` when this evidence was inspected.

## Result

The automatic backfill selected 14 replacements for the previous 14 incompatible
games.

Outcome:

```text
previous compatible/indexed     22
replacement attempts            14
replacement successes            8
replacement failures             6
current indexed                 30 / 36
snapshots                    108599
transitions                  108110
archive bytes             7987231325
settings hashes                 30
```

Successful replacements:

```text
441148
364412
658427
371631
597910
396107
350094
416250
```

Failed replacements:

```text
43082
68006
78375
138269
190004
190428
```

Every failed replacement is a legacy/binary normalization boundary of the same
shape:

```text
player1-turn0.trn: turn payload is not UTF-8 JSON
```

The earlier network timeout problem is not the blocker. Game 43082 did require a
network retry first, but its final failure was still the same normalization
boundary.

## Rejection-ledger behavior

The evidence copy of
`public-validation-rejected.json` still lists the *previous* 14 rejected games.

That is expected from runner ordering:

```text
read previous stats
-> add previous failed ids to rejection ledger
-> select replacements
-> ingest replacements and write new stats
```

Therefore the six new failed replacement IDs are not lost. On the next run,
`public-validation-stats.json` supplies them to the backfill CLI, which adds
them to the persistent rejection ledger before selecting another bounded
replacement set.

No rediscovery is required.

## Coverage status

Backfill target:

```text
campaign       19
championship    6
finite_fuel     9
sphere          2
```

Selection after round 1:

```text
campaign       19
championship    6
finite_fuel    11
missing sphere  2
```

So the explicit Sphere *bucket* coverage target remains unclosed.

The raw selected manifest does contain ten games with
`settings.sphere=true`, but `_manifest_bucket()` gives campaign and
championship higher precedence than sphere. That raw setting presence therefore
does not satisfy the intended standalone Sphere bucket target.

Capability metadata is also still absent:

```text
selected games                         36
selected player slots                 594
non-empty activeadvantages slots        0
non-empty activehulls slots             0
```

Campaign-mode breadth is present, but active Campaign capability coverage remains
a separate gap.

## Next bounded action

Repeat exactly the existing resumable acquisition command from current main:

```bash
bash tools/run-public-validation-corpus-with-evidence.sh
```

Do not:

- redo the 160-game discovery;
- delete immutable loadall cache;
- introduce a legacy binary parser merely to rescue these candidates.

The next run should:

1. absorb the six new failed IDs into the rejection ledger;
2. reuse all 30 compatible cached archives;
3. select up to six new candidates from the already-probed pool;
4. publish another immutable runtime checkpoint.

If the selected corpus reaches a useful stable compatible set, move directly to:

```bash
bash tools/run-public-capture-side-discovery-with-evidence.sh
```

Only the discovery partition may be inspected while deriving a side rule. The
held-out partition stays sealed until the rule is frozen.

## Combat boundary unchanged

The canonical C5 blocker remains:

```text
post-capture ship LEFT / RIGHT side assignment
```

No side rule is promoted by this corpus acquisition checkpoint.

The external-engine branch remains candidate-only; c2ng's global captured-RIGHT
model is already rejected by the official eight-row population and may only
supply the bounded T26 original-order cursor hypothesis.

## Operator rerun guard

A later operator rerun exposed a workflow hazard rather than a new corpus result.

The local checkout was still on `research/external-engine-analysis`. The attempted
`git pull --ff-only origin main` correctly refused to fast-forward that research
branch, but the next shell command still launched the corpus runner. Runtime
evidence was therefore published from:

```text
runtime-logs/public-validation-corpus/20260928T085529Z_d306edd49845
source_branch: research/external-engine-analysis
source_commit: d306edd4984512efbbe29d97f0ad911ebd3285b3
```

That run is immutable evidence but **not canonical main corpus evidence** and
does not supersede the 30/36 round-1 checkpoint above. It merely re-indexed the
same selected population and again observed the same six binary normalization
failures.

To prevent another expensive accidental non-main run,
`tools/run-public-validation-corpus-with-evidence.sh` now fails closed unless
the current branch is literally `main`. Intentional diagnostic execution from
another branch requires the explicit override:

```bash
PUBLIC_VALIDATION_ALLOW_NON_MAIN=1 \
  bash tools/run-public-validation-corpus-with-evidence.sh
```

Normal canonical acquisition must not use that override.

