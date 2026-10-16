# C5 V25 — one command to acquire new public games, build separate DB and run THREE frozen analyses

Canonical repository: `Numillyash/planets-lab`, `main`.
NEVER modify production `planets-intel`, existing compact public100,
`CURRENT`, canonical combat executor, external-engine branch or draft PR #28.

## Why this replaces the repeated posthoc public100 probes

V24 published successful runtime at
`runtime-logs/combat-c5-short-edge-mechanisms-batch-v24/20261016T083619Z_cf67af585095`
on clean main `cf67af585095d8e4b3901d80db965411a92a2201`,
with complete `chains`, `orders`, `stabilizers` and `manifest`.
All 100 original public100 games have now been inspected in some research
sample. Its eight preselected short edges had: five actors at source,
two at downstream targets along independently eligible long Chunnel
chains, one near target at 1 LY (G449095/T141 #547→#229) with a
foreign-owner Dungeon field candidate, Warp0, own waypoint, net -50KT
and no T−1 Tow request. No hidden Host activation is proven.

The explicit scientific priority is now a new **entirely game-disjoint**
public archive cohort, NOT retroactive selection of convenient V24 cases.
The new games are finished *historical* public games: although they are
newly ACQUIRED, they are NOT live prospective Host experiments.

## V25 bounded four-stage single command

1. Preflight: assert existing FULL public100 100-game combined baseline
   `validation/corpus/manifests/public-postindependent-validation-with-public68.jsonl`,
   corpus root, reproducible research Python and at least 12 GiB free
   by default (adjust via `C5_V25_MIN_FREE_GIB` only after checking
   physical space). Save current `CURRENT`.
2. Discover, select and download **eight** finished, public, 8–16
   player games with 55–140 turns, using existing validated public
   discovery, ingest and up to 24 backfill rounds. All
   `public-c5-v25-*` manifests and index reports are namespaced;
   the FULL 100-game baseline excludes prior source IDs.
   Selection is based on public game metadata/settings, NOT future
   ship outcomes, combat VCR, Chunnel endpoint behavior or success.
3. Compile exact-parity checked compact1 generation
   `generations/corpus-v2compact-c5-v25-public8-20261016.duckdb`
   from only these eight new ZIPs. Reusable staging name
   `compact-c5-v25-public8-resume`, explicit new build ID,
   **no `--activate-current`**, check unchanged `CURRENT`.
   Existing public100 remains immutable; never switch `CURRENT`.
   An already published valid DB path can be reused and population
   is checked read-only in the evaluation.
4. ONE SHA256 verification of the NEW explicit DB, verify its
   `source_archives` are EXACTLY eight selected IDs and share NONE
   with original 100. Select up to 24 adjacent T−1/T windows per
   game from `source_members` metadata ONLY. Freeze ALL T−1
   owner-current Firecloud intents, documented Chunnel gates,
   Dungeon field geometry, safe Short Format game setting flags,
   and source-colocated passenger candidates BEFORE reading ANY
   T owner-current positions. Then evaluate and publish:
   - `actors.json`: short/long/single-failed/colocated cohorts,
     T endpoint/fuel by frozen status and distinct game/window
     exposure, zero-exposure is NOT negative validation.
   - `fields.json`: owner-current Dungeon geometry, engine,
     position persistence, whitelisted mechanical settings only.
   - `passengers.json`: preselected source stacks (short exposures
     plus maximum one deterministic long control per window),
     observed T coordinates split by owner, no passenger causal claim.
   - `manifest.json`: three report SHA256 checksums, new DB
     absolute path and SHA256, new game IDs and `CURRENT` policy.

Single evidence wrapper publishes the four reports once. A failure
in acquisition, parity/build or research checks returns nonzero.
Existing acquisition supports resuming, but do not claim that
an unfinished new corpus has been published.

## One exact server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-new-game-corpus-batch-v25-with-evidence.sh
```

Evidence:
`runtime-logs/combat-c5-new-game-corpus-batch-v25/<UTC>_<commit>/`.
Reports:
`artifacts/combat/c5-new-game-corpus-batch-v25/published/`.

**Expect longer physical runtime** than previous V21–V24: it
downloads eight additional full-game archives, validates raw ZIP
semantic parity and imports a new DuckDB. It still needs only ONE
manual command and reports all results together. No asynchronous
assistant work or intervention is assumed.

## Causal boundary

Any T-endpoint match is observational: Host phase activation,
mine hit, successful Tow lock, exact intermediate Chunnel state,
and actual passenger cause remain unproven. A short case without
a T−1 field witness does NOT establish the field was absent;
missing source/target owner-current T is ABSTAIN, not destruction.
No N+1 VCR is read or made into a training label.

Future: evaluate pre-registered genuinely NEW game-disjoint
outcomes and independent Host-phase traces as feasible before
promoting any canonical movement or combat rule.
