# C5 V24 — eight short candidates, three mechanism audits, one server invocation

Canonical: `Numillyash/planets-lab`, `main`. Keep
production `planets-intel`, external-engine branch,
combat executor, immutable public100 `CURRENT` and draft PR #28
untouched. USER WORKFLOW REQUIREMENT: batch predeclared research
in one evidence wrapper; do not impose one manual run per idea.

## Pinned V23 source

Successful runtime:
`runtime-logs/combat-c5-episode-field-batch-v23/20261016T081308Z_7fa93c3672da`,
`exit_code=0`, clean source main
`7fa93c3672da46733e576f5bf97e696a3244257d`.

Git blobs:
- `field_scan.json`:
  `9d5dab0cdd8969313c795a56efea939de83242b4`
- `manifest.json`:
  `12c0648b5b123caa50ef8d974ed7dc3d2bab4c9b`.

V23 searched 264 adjacent windows from 11 additional games
not in previous 89 game IDs. Exactly 8 geometrically
distinct short-distance single-gate controls and 375 fully
valid long-distance controls; short statuses:
6 with NO documented Tminus1 field witness
(5 actor stayed source, 1 elsewhere), 2 with candidate
Stargate field witness within 550LY (1 at original near
target, 1 elsewhere). Same public100, no new corpus.

CRITICAL NEW graph confound found by inspecting the entire
V23 Tminus1 long comparison inventory:

- G449095/T121 #361->#114 at 1LY has candidate third-party
  Dungeon #238 at 493.82LY, but #114 itself is an eligible
  LONG Chunnel source -> #443 at 1069.23LY. Both #361 and #114
  end at #443 coordinates (1300,2140).
- G449095/T121 #396->#218 at 1LY has **no** documented field,
  but #218 is an eligible LONG source -> #548 at 557.54LY.
  Both #396 and #218 end at #548 coordinates (1276,2810).
- G449095/T141 #547->#229 at 1LY has a candidate third-party
  Dungeon #238 at 368.90LY; observed #547 at its *immediate*
  #229 target, but any one-LY repositioning is a major confound
  and should not be interpreted as proven short Chunnel.

Thus the earlier observation "one short field witness at
target, one elsewhere" is NOT evidence of an activatable
short Chunnel. Both T121 paired short cases appear structurally
explainable as carried passengers of a conventional LONG
Chunnel, regardless of nearby stabilizer.

Official:
https://help.planets.nu/mis-warp-chunnel
https://help.planets.nu/abil-chunnel-stabilizer

## V24 three in one

**chains.json**: Pin complete V23 8-short/375-long report
and SHA256 manifest; on Tminus1 inputs only, build all
short-to-valid-long target/initiator directed edges requiring
matching game/turn, same owner, *exact* coincident intermediate
position. After ALL Tminus1 frozen records, independently
compare archived T positions of first and middle actors
against downstream target. Count by window, never by alleged
short activations.

**orders.json**: In ALL seven affected windows,
independently reconstruct exact Tminus1 owner-current
Firecloud hull, owner, fuel, Warp, waypoint, mission,
Tow requests, collocated ship stack and target Tminus1
position. Cross-check V23 pair identities against conservative
V16 numeric-code scanner; record explicit last-turn
waypoint/warp geometry and independent T owner-current actor
and target observations. Do not infer "ordinary movement"
for Warp0 without a valid movement source; "at short target"
by itself is not a mechanism.

**stabilizers.json**: In those same seven Tminus1 windows
freeze archival Dungeon hull108, engine, owner, position
and documentary stabilization radius. Compute BOTH source
and target signed distance margins separately, including
owner-mismatch. AFTER ALL Tminus1 archive scans,
independently compare Dungeon owner-current T position
and engine, without assuming Host field activation.
Do not read raw FC or private messages into reports.

Single immutable public100 SHA256 check; one read-only
connection, one full Tminus1-before-T barrier, three
complete JSONs + SHA256 manifest, one
`run-with-runtime-evidence.sh` invocation. No fresh
independent validation claim: V24 targets cases already
observed in V23 and must remain posthoc.

## Server one-liner

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-short-edge-mechanisms-batch-v24-with-evidence.sh
```

Reports:
`artifacts/combat/c5-short-edge-mechanisms-batch-v24/published/`
(`chains.json`, `orders.json`, `stabilizers.json`,
`manifest.json`).
Runtime branch:
`runtime-logs/combat-c5-short-edge-mechanisms-batch-v24/`.

Next: do not mine the same public100 repeatedly for new
short-field positives. For stronger mechanism confirmation,
acquire a NEW immutable prospective corpus from games with
known active Dungeon field, explicit ruleset and time-indexed
Host observations. Preserve original game/turn holdouts.
