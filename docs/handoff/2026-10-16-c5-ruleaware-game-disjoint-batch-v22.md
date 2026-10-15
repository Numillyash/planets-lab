# C5 V22: one new game-disjoint cohort, three reports, one server command

**Workflow:** After user feedback, avoid one scientific probe per
copy/paste round trip. V22 collects all three studies in one complete
T−1-before-T pass over the same immutable public100. One wrapper,
one evidence upload, three complete reports and manifest.
Production `planets-intel`, corpus `CURRENT`, canonical combat
executor, external-engine branch, and draft PR #28 remain unchanged.

## V21 published ground truth

Evidence `runtime-logs/combat-c5-stabilization-batch-v21/20261015T210552Z_96c3e0c62878`,
verified exit_code=0, main source
`96c3e0c628784d38bc0bdf9c76c96c0603f5723d`.
Git blob SHA1 of published V20 report:
`3d5e1d5aeb6b0138c01bab3ec81185d0685233c0`;
published V17:
`a6256b70dc63b9b7126a211245bc65ce20ece863`.

V21 geometry: G467386/T75 source Firecloud 467 T−1
(1141,1459), target 80 (1126,1439), distance 25LY.
Same-owner Dungeon Class Stargate #446 at (1279,1931),
engine9, radius 550LY, source distance 491.7601LY
(margin +58.2399), target 515.24072LY (margin +34.75928).
Both within documented stabilizer field geometry.
Persistence: Stargate #446 position and engine unchanged
from T−1 to T at G467386/T75 and G467386/T221; another
Stargate #251 persisted G632527/T89 (3/3 instances).
Escorts: G467386/T75 Firecloud #467 and owner-6 ships
#193/#235/#405 ALL end at #80 from one shared T−1 site.
These are *strongly compatible* with official stabilizer
mechanics but do NOT directly prove Host activation.

Official rules:
https://help.planets.nu/abil-chunnel-stabilizer
https://help.planets.nu/mis-warp-chunnel
https://help.planets.nu/short-format

Reminder: ordinary same-owner Warp9 ships can enter a
Chunnel; Warp9 escorts do NOT independently prove Short
Format rules.

## V22 exact new game-disjoint design

Pin V17 and V20 immutable published report blobs. Validate
V17's metadata-only frozen game list: 57 prior V6/V9/V13/
V14 games + 16 V17 games = **73 excluded entire games**.
From remaining eligible public100 games choose 16 games
using fixed sorted game-ID quantiles and THREE adjacent
T−1/T windows per game using fixed archival turn quantiles:
48 new windows, independent of ship outcomes, Chunnel
success, raw VCR or battle events. This is GAME-DISJOINT
from V6/V9/V13/V14/V17 but NOT a newly collected corpus.

Read all 48 exact T−1 owner-current snapshots first:
- identify all unambiguous STOCK Firecloud numeric-code
  pairs and ordinary T−1 conventional gate statuses
  via the established V16 conservative scanner;
- obtain whitelisted scalar short-format rules/race IDs
  and archival Dungeon Stargate hull108 engine,
  position, documented radius; compare actor SOURCE
  distance to field, target distance for context;
- classify T−1 cases by: regular long valid; short
  with field witness; short without documented field
  witness; other one-failed condition; coincident
  non-discriminative source/target;
- preselect all source-colocated ships for long-valid and
  stabilized-short candidate source stacks WITHOUT
  querying any posthost T.

**Only after all 48 T−1 windows freeze** query owner-current
T for all three experiments. Produce:
1. `actors.json`: all eligible stock Firecloud actor
   episodes by gate/field cohort; actor at distinct target,
   source, elsewhere, T owner/hull/unavailable abstention,
   and T fuel delta, with game/window denominators.
2. `stabilizers.json`: every T−1 Dungeon appearance
   and owner-current T identity/position/engine, plus
   safe scalar rules. NO assertion that field was active
   at Chunnel Host phase.
3. `escorts.json`: all source-colocated passengers in
   preselected gate-valid/field-witness episodes, T owner
   identity/coordinates/fuel. Do NOT double count ships
   or multiple ships from one episode as independent
   activations. If zero field-witness exposures, explicitly
   report denominator zero, not validation.

A `manifest.json` records SHA256 of each report, and one
`run-with-runtime-evidence.sh` publishes entire directory
with one server invocation. Fail on missing pinned corpus
or changed original source provenance; distinguish T−1
unknown fields from proven absence of field. A T−1
Stargate candidate does not establish execution at the
later Host phase. No future VCR, mine-hit causality, new
Host queue predictions or canonical executor updates.

## Exact server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-ruleaware-disjoint-batch-v22-with-evidence.sh
```

Reports under
`artifacts/combat/c5-ruleaware-disjoint-batch-v22/published/`:
`actors.json`, `stabilizers.json`, `escorts.json`,
`manifest.json`.
Evidence:
`runtime-logs/combat-c5-ruleaware-disjoint-batch-v22/`.

If no short field exposure is present in new 16 games,
do NOT treat that as short-field invalidity or failure.
Next useful step would be new prospectively acquired
immutable corpus captures with known Dungeon Stargates,
actual Host logs when possible, and benchmark against
time-indexed movement and owner-current coverage.
