# V26: new public8 residual, visibility and passenger clusters in one evidence run

## V25 successful runtime and frozen population

Evidence `runtime-logs/combat-c5-new-game-corpus-batch-v25/20261016T085727Z_4bbbbf75b0f4`;
source main `4bbbbf75b0f4b15aad800cd2133767af404d4188`;
clean, exit_code=0, all three reports and manifest published.

Newly acquired archival game IDs exactly
233802, 290449, 403181, 444043, 469931, 521268, 536676,
608293. Entirely game-disjoint from original public100, but
historical turns, not real-time experimental Host captures.
New immutable generation:
`/root/projects/planets-corpus-db/generations/corpus-v2compact-c5-v25-public8-20261016.duckdb`
SHA256 `af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a`.
Never switch `CURRENT` or rebuild/modify DB.

Pin exact published Git blobs:
- V25 manifest `2c89d5320b31b2f12d9235192a8ac31240549052`
- actors `423e6123496068b8d2987bd27fe0b455fee4c1df`
- fields `b559901540ee1a906811ed4e510629be70aae365`
- passengers `ebe8e812d91a80e4fd3c9ccdbc99df0edcc98145`

V25 metadata selected 192 adjacent T-1/T windows, all original
T-1 contexts available, 33 with stock actor/gate exposure.
106 actors: 58 conventional long (55 at target, 1 elsewhere,
2 owner-current T unavailable), 38 colocated non-discriminative,
10 single failed gate (9 at source, 1 elsewhere), ZERO short
with documentary stabilizer field and ZERO Dungeon Stargates.
22 preselected source-ship stacks, 66 ship appearances,
34 same-owner and 7 foreign-owner ship matches at frozen
destinations. All counts observational.

Important *single* long residual:
G403181/T60 #143→#202, owner1, T-1 source (1509,2683),
target (2326,2181), 958.90 LY, Warp0, pre-fuel51.
T #143 at (2198,1799), net fuel loss **-50**, i.e. T
fuel increased by 50 KT (NOT a normal 50KT depletion).
Could involve other Chunnel, Tow, transfers, owner phase;
do not declare broken activation.

Both long owner-current unavailable:
G521268/T116 #388→#192 owner7, and #577→#240 owner4.
Both expected T-1 targets at (1152,2243), and both return
archive ABSTAIN. Missing owner-current T does not mean dead
or an execution miss; identify *T perspective coverage*.

## Three V26 independently reported descriptive audits

1. `exception_routes.json`: from ALL 33 previously
   selected windows, independently crosscheck T-1 owner/hull,
   original numeric stock Chunnel intent and source/target,
   freeze each actor's mission, Warp, waypoint, fuel and
   bounded Tow requests, all other frozen conventional stock
   Chunnel endpoints and T-1 ship-position inventory.
   After complete 33-window T-1 freeze, replay original
   published T owner-current actor outcomes; for the
   exact 3 original long residuals, check nearby T-1 ships
   at actor observed position, preselected other long
   destinations and T co-location without asserting cause.
   Group positive controls by game-turn episode.
2. `archive_visibility.json`: only AFTER full T-1
   freeze, inspect member_refs metadata for T-1 and T
   perspective-player IDs of both missing G521268/T116
   cases; distinguish absent owner's perspective from
   a ship not in an existing owner's perspective. Do not
   infer whether missing ships were destroyed. Numeric
   perspective IDs only, no account names/raw payload.
3. `passenger_episodes.json`: use exact original V25
   fixed 22 source stacks and 66 owner-current comparisons;
   group 34 same-owner and 7 other-owner arrivals by
   episode/game, distinguish each ship appearance from
   an independent Chunnel activation, retain abstentions.

ONE SHA256 pass of the already-built public8 DB; one
read-only DuckDB connection; full T-1-before-T barrier;
three JSON reports + SHA256 manifest, single
`run-with-runtime-evidence.sh` publication. No new
acquisition or import. V26 is POSTHOC diagnostic of
previously seen V25 outcomes, NOT new holdout evidence.
No N+1 VCR, Host phase inference, combat queue promotions.

## One exact server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-new-corpus-exception-batch-v26-with-evidence.sh
```

Evidence under `runtime-logs/combat-c5-new-corpus-exception-batch-v26/`.
All phase reports under
`artifacts/combat/c5-new-corpus-exception-batch-v26/published/`.

Production `planets-intel`, canonical combat executor,
external engine branch, corpus `CURRENT`, original public100
and draft PR #28 must stay untouched.

Future decisions: explicitly separate true new holdout
mechanism tests from posthoc phase explanations. Because the
new public8 has zero short stabilizer exposures, do NOT
treat it as failure of the short stabilizer rule or
relax the gate to harvest apparent positives.
