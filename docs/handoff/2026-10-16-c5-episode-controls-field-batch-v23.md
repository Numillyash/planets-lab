# C5 V23: three experiments, one server invocation, no manual round trips

Canonical: `Numillyash/planets-lab`, main. Keep production
`planets-intel`, combat executor, external-engine analysis,
immutable corpus CURRENT and open draft PR #28 untouched.

## Pinned published V22 outcome

Successful runtime:
`runtime-logs/combat-c5-ruleaware-disjoint-batch-v22/20261016T075322Z_f9f973e9cf95`;
`exit_code=0`, no missing artifacts, source main
`f9f973e9cf955494e9fd6b437a74e531cfd5aace`.

Git report blob SHA1:
- `manifest.json`: `ef6ad48b2f8f8e0c054525c2bdc19780f465d92a`
- `actors.json`: `77b76ac6726e8ad08ab505b7ac112c513aeb89e5`
- `escorts.json`: `2174e1e7675296b229674e56b5f68d1f087908f1`
- `stabilizers.json`: `37a2924a705017fbca7b6cbf9177321beb6623a3`

The earlier V6/V9/V13/V14/V17 investigations used 73 unique
games. V22's further 16 have ZERO overlap, so **89
entire games** are excluded from new V23 search.

In V22: 48 completed windows across 16 game-disjoint games.
57 stock Firecloud numeric-intent actor edges: 36 conventional
gate-pass T−1 actor-at-frozen-T success, grouped into 19
game-turn episodes; 13 ordinary one-gate failures and no
actor at frozen target (3 initiation fuel<50, 6 target warp>0,
4 Tow request); 8 start=target tautologies excluded.
No stabilized-short source witness in this sample: denominator
ZERO (not a refutation). Six Dungeon Stargate archival
appearances in two games; all six hold position and engine T−1/T.
Escorts: 36 source episodes, 351 individual ship appearances,
263 at a frozen target T, including 14 different-owner ship
appearances. Ownership and co-location alone cannot prove Host
passenger eligibility or a specific mechanic.

## V23 ONE BATCH: 3 outputs

**1. `episodes.json`**: independently reconstruct V22 57
actor outcomes into game/turn and game clusters, splitting
every gate-fail reason. Preserve fixed 36/13/8 denominators;
report 36 positive *ships* versus only 19 positive *windows*,
never claim 36 independent mechanics trials. No new T data.

**2. `ownership.json`**: independently replay all 36
previously frozen source stacks and 351 ship observations;
group same-owner vs other-owner and observed at-target /
elsewhere / archive abstention by episode. Foreign-owner
arrivals are descriptive only, not automatically Chunnel
passengers. No raw friendly codes or private data.

**3. `field_scan.json`**: detect rare short stabilized
Firecloud exposures in **ENTIRELY UNUSED game IDs** of the
same public100. Exclude all 89 previous research games.
Read only `source_members` metadata to choose remaining
eligible games (up to 16), and choose up to 24 evenly spaced
adjacent archived turn pairs per game, independent of
ship content and outcomes. For each selected window first
read ONLY T−1 owner-current ship archive, identify
unambiguous stock Firecloud pairs, documentary Dungeon
Stargate field geometry + explicit Cyborg Short Format rules.
Preselect all distinct short-distance single failed-gate
pairs with or without field witness plus all ordinary
long gate-pass controls BEFORE reading ANY T archive.
Only afterward compare T ship owner-current positions.
Report exact denominators, windows, games and abstentions;
missing source evidence is NOT proof field was inactive.

ALL THREE are independent reporting/validation tasks in one
repository script and ONE evidence wrapper. After one
immutable public100 SHA256 verification and one read-only
DB opening, reports are published as `episodes.json`,
`ownership.json`, `field_scan.json` and SHA256-indexed
`manifest.json`.

This is additional game-disjoint exploration *within the
same existing corpus*, not a truly new prospectively
acquired dataset; prior case results cannot be counted as
independent tests of the engine. A positive field witness
from T−1 is not proof the field was active during Chunnel.
A zero-exposure scan means insufficient evidence, NOT that
the short-distance rule is false. No combat queue prediction,
VCR N+1, or production resolver changes.

## Exact one-line server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-episode-field-batch-v23-with-evidence.sh
```

Reports under
`artifacts/combat/c5-episode-field-batch-v23/published/`.
Evidence under
`runtime-logs/combat-c5-episode-field-batch-v23/`.

Future: if the remaining unused games lack documented
short-field exposure, use a freshly collected immutable
Planets.nu validation corpus with designed exposure
controls, rather than repeatedly searching the same
historic public100 for post-hoc favorable examples.
