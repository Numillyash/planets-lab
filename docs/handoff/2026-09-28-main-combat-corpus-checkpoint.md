# Main combat + corpus checkpoint — 2026-09-28

## Source of truth

GitHub `main` is authoritative. New chats must inspect the actual current
HEAD and current documents before using any SHA or counters in this handoff.

This checkpoint separates three workstreams:

1. the primary NuHost mechanics track on `main`;
2. the public validation-corpus acquisition track;
3. external-engine/reference analysis, which must remain evidence-bounded and
   should continue on a separate research branch/chat.

## C5 combat status

The bounded ordinary non-capture predictive queue remains closed:

```text
22 / 22 held-out next-VCR transitions exact
0 mismatch
7 capture-predecessor exclusions
```

The capture path has since advanced substantially beyond the older ROADMAP
wording.

Closed observed ship-capture layers:

```text
capture continuation identity/state       closed
special Tow/Intercept geometry             2 / 2 exact
post-capture candidate graph               8 / 8 exact
post-capture active membership             8 / 8 exact
post-capture pair eligibility/phase        8 / 8 resolved
pair phase                                 8 / 8 STANDARD
captured-FC phase sensitivity              8 / 8 invariant
```

The factual VCR N+1 remains comparator-only in these gates.

### Current combat blocker

The remaining bounded ship-to-ship capture blocker is **LEFT/RIGHT side
assignment after capture**.

Current independent control results:

```text
opponent_initiator_right          7 / 8 exact
neutral captured orders + fresh FC
                                  6 / 8 exact
sticky capture side               4 / 8 exact
frozen T-1 priority               4 / 8 exact
neutral orders + preserved FC     4 / 8 exact
```

The principal discriminator remains:

```text
511506 / T26
captured ship27
next opponent ship119
factual captured-ship side = RIGHT
```

The second-capture ship34 case additionally shows that blindly applying the
ordinary same-pair occurrence reversal to a newly created post-capture combat
order is not sufficient.

Do not promote a side rule from the current eight observations alone. The next
primary mechanics action is to enlarge the independent historical population
and harvest additional ship-capture continuations, especially additional RIGHT
cases.

Durable detailed evidence remains in:

```text
docs/handoff/2026-09-24-combat-capture-runtime.md
```

## Public validation corpus expansion

The repository now contains a Docker-based public acquisition pipeline:

```bash
bash tools/run-public-validation-corpus-with-evidence.sh
```

Discovery uses public finished games, factual `loadinfo` settings and
ruleset/capability diversity. Raw `loadall` archives remain local immutable
cache data and are not published to GitHub runtime evidence.

Current acquisition implementation is resumable:

```text
default loadall timeout         180 s
additional transient retries      2
retry backoff                     2 s, then 4 s
discovery manifests              reused by default
successful immutable ZIP cache   reused
partial index/stats evidence     staged even when some games fail
```

A local run started from an older source commit may continue to completion.
Do not delete its cache. After it finishes, pull current `main` and run the
same command again; current code reuses discovery output and already cached
archives and retries only missing/failed network acquisitions.

Legacy archives whose `.trn` members are binary rather than UTF-8 JSON remain
fail-closed. Do not add a legacy binary parser merely to rescue one public-game
candidate while the current blocker is combat-side population size. Replace
unsupported candidates with compatible games of similar feature coverage.

Detailed corpus policy:

```text
docs/handoff/2026-09-27-public-validation-corpus.md
docs/COMPILED_CORPUS.md
```

## Next main-track sequence

After the public acquisition has produced a useful compatible archive set:

1. build a capture-side coverage report over the new archives;
2. enumerate all attributable ship capture N -> ship-vs-ship N+1 continuations;
3. retain owner/race transition, factual LEFT/RIGHT, prior same-pair history,
   capture-side, opponent-side priority inputs and relevant FeatureScope
   predicates;
4. split those observations into discovery and held-out validation populations;
5. derive candidate side rules only from the discovery population;
6. freeze the rule;
7. open the held-out population and run the differential unchanged.

Do not use all newly downloaded games for fitting.

## External implementation boundary

External projects are valuable as candidate generators only:

```text
third-party implementation
!= NuHost evidence
```

Required path:

```text
external candidate
-> primary Planets.nu documentation where available
-> attributable official Nu observation
-> deterministic local test
-> differential verification
```

The current external catalog and engine-core research pass are:

```text
docs/handoff/2026-09-27-external-planets-tools-mechanics-reference.md
docs/research/2026-09-28-engine-core-internet-research-pass.md
```

The highest-value current external questions are narrowly tied to the active
combat blocker:

- whether c2ng/c2nu or another independent implementation contains an explicit
  post-capture combat-order / LEFT-RIGHT rule;
- whether those implementations expose a candidate discriminator that can be
  tested against official Nu archives;
- whether any independent loader reveals a field-order or side-mapping mistake
  before a new Host rule is invented.

Do not copy third-party mechanics into production solely because an external
engine implements them.

## Branching policy for the parallel research chat

External engine comparison should continue on a dedicated research branch,
starting from the current clean `main` checkpoint. It may add research notes,
source maps, comparison tables, candidate diagnostics and deterministic tests,
but must not promote or merge a mechanics rule without official/corpus evidence.

The main chat remains responsible for:

- public archive acquisition/recovery;
- capture-side corpus harvesting;
- held-out NuHost differentials;
- final promotion into canonical rules.


## Public corpus runtime now available

The second public acquisition pass at source \`628ecd24...\` produced 22
compatible independent games from the selected 36, totaling 75,787 snapshots,
75,463 transitions and about 5.95 GB of immutable archives.

All 14 remaining failures are legacy/binary \`.trn\` normalization boundaries;
the earlier network timeout problem is no longer the blocker.

Current successful bucket counts:

\`\`\`text
campaign=11
finite_fuel=8
championship=3
sphere=0
\`\`\`

Current failed bucket counts:

\`\`\`text
campaign=8
finite_fuel=1
championship=3
sphere=2
\`\`\`

The acquisition runner now automatically replaces failed games from the
already-probed candidate pool while preserving the original bucket target and
maintaining a rejection ledger.

The next main-track mechanics action can proceed in parallel with that backfill:
run the discovery-only public capture-side harvester over the compatible indexed
games. The harvester deterministically keeps roughly one quarter of game ids
sealed as held-out validation before looking at combat outcomes.

Runner:

\`\`\`bash
bash tools/run-public-capture-side-discovery-with-evidence.sh
\`\`\`

Do not inspect the held-out partition until a candidate side rule has been
frozen from discovery observations.
