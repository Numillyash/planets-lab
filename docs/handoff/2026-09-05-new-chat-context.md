# New chat context — movement/corpus investigation

Date: 2026-09-05

GitHub `main` is the only source of truth for project state. Do not reconstruct current state from an old ChatGPT conversation.

This file is the new-chat entry point. The detailed active mechanics handoff is:

- [`2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md`](2026-09-05-normal-mine-single-candidate-immunity-repair-pending.md)

Also read:

- [`../ROADMAP.md`](../ROADMAP.md)
- [`../COMPILED_CORPUS.md`](../COMPILED_CORPUS.md)
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- [`../WORKFLOW.md`](../WORKFLOW.md)

## Operating rules

1. GitHub `main` is source of truth.
2. Before changing code, fetch/pull current `main`, inspect HEAD and dirty state, and read the files above.
3. Raw historical archives, prepared caches and compiled corpus databases are local/gitignored. Do not expect them in Git.
4. Do not weaken privacy-safe corpus projections merely to make diagnostics convenient. Raw `.trn` inspection must remain explicit and privacy-safe.
5. Unknown mechanics fail closed. Separate `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`, `TESTED`, and `DIFF_VERIFIED` evidence.
6. Do not promote a production label from a single attributable transition.
7. After meaningful code/mechanics changes, update durable state in README / ROADMAP / COMPILED_CORPUS / handoff as appropriate so a later chat can recover without the chat history.
8. Do not rebuild L1/L2 unless the active task actually changes compiled semantics. Diagnostics should run against the current verified corpus whenever possible.

## Runtime-verified production baseline

Current verified movement accounting:

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13970
post_external_residual              3924
chunnel_explained                   1421
post_chunnel_residual               2503
horwasp_strong_explained             240
post_horwasp_strong_residual        2263
mine_strong_explained                 37
post_mine_strong_residual           2226
fuel_proration_explained               6
post_fuel_proration_residual        2220
label_issues                           0
```

Generic endpoint:

```text
final_residual_rows       2220
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               763
generic_games               12
generic_hulls               76
```

Largest surviving coarse family:

```text
116  warp7-9 <0.5x observed=other same_line_forward
```

Current schemas:

```text
prepared cache:       planets-lab.prepared-game-cache.v1
L1 movement:          planets-lab.compiled-movement.v3
L1 context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:    planets-lab.compiled-movement-context-labels.v6
```

No schema/cache/accounting change is currently pending.

## Important verified/closed mechanics

Production-verified movement closures include:

- ordinary movement / Host major-minor geometry;
- warp-well ordering;
- route-equivalent owner-visible Tow;
- route-equivalent Chunnel multiplicity;
- classic/cloudy ion storms;
- scoped effective sphere topology for game `591478`;
- strict mine/web interruption v5;
- strict damage-limited maximum warp;
- strict Nu waypoint-distance fuel proration v6.

Red Mite tracking/fallback research is closed absent new evidence.

Recent post-v6 broad leads rejected for the dominant 116-row family:

- outbound submitted fuel transfer;
- standard Cloak fuel burn;
- Privateer Rob Ship;
- Stellar Cartography speed terrain. Refined active inventory found no active Black Hole or wormhole population in the current 12-game corpus.

Crystal Web Drain has one fully attributable `DOCUMENTED + CORPUS_OBSERVED` transition, including historical ownership/era/diplomacy, but remains evidence-only because it is one game/hull.

## Current normal-mine slowdown investigation

An upper-bound route/geometry audit found:

```text
target_short_rows                         116
target_short_normal_mine_route_exposure    10
target_short_deficit_near_10n                2
```

The two geometry candidates were:

```text
game 360690 / turn 155 / ship 447 / hull 23 / deficit 30.575 ly
game 511506 / turn  23 / ship 160 / hull 17 / deficit 21.094 ly
```

The hull-tech gate reduced this to one candidate:

```text
candidate_rows_found       2
tech_eligible_candidates   1
tech_ineligible_candidates 1
```

Rejected:

```text
game 360690 / turn 155 / ship 447 / hull 23
hull tech = 10
```

Documented normal-mine slowdown does not apply to hull tech 7+.

Sole survivor:

```text
game 511506 / turn 23 / ship 160 / hull 17
owner = 3
hull tech = 6
hull mass = 130
planned distance = 43.566 ly
observed distance = 22.472 ly
deficit = 21.094 ly
normal-mine corpus damage quantum = 76
before damage/supplies = 0 / 53
after damage/supplies  = 66 / 3  (after supplies are observational)
```

The damage/supply trace strongly supports exactly one ordinary normal-mine damage quantum followed by supply repair:

```text
before damage = 0
one hit -> 76
53 submitted supplies -> repair 10% using 50 supplies
predicted final damage = 66
predicted remaining supplies = 3
```

Two ordinary damage hits would imply raw damage 152 and do not fit the observed repaired state. Therefore `21.094 ly ~= 2 * 10 ly` is only a geometry clue; do not infer two impacts.

The open question is whether the one-hit attribution is actually allowed by historical mine immunity, and if so what explains the remaining movement-distance discrepancy.

## Active diagnostic — runtime still pending

The next command has been prepared but its runtime output has **not yet been supplied/verified** at the time of this handoff:

```text
tools/diagnostics/normal_mine_single_candidate_immunity_repair_audit.py
```

It evaluates only `game 511506 / turn 23 / ship 160` and checks:

- exact post-decay normal minefields intersecting the planned segment;
- exact route interval inside each intersected field;
- field IDs and owners;
- turn-specific `playerid=target, playertoid=field_owner` relation record;
- direction `relationfrom = field owner -> target`;
- Safe Passage / higher immunity;
- target and field-owner team IDs;
- minefield Friendly Code fields actually exposed by archived perspectives;
- exact ship-to-field FC match;
- structural `MFx` possibility;
- one-hit and two-hit submitted-supply repair predictions.

Immunity logic must fail closed:

- Safe Passage or higher from field owner to target => immune;
- exact field FC matching ship FC => immune;
- unknown/unexposed field FC must not be interpreted as hostile merely because it is absent;
- do not infer mine RNG from geometry alone.

## First runtime action in the new chat

Run this exact block in WSL, without rebuild:

```bash
cd ~/projects/planets-lab
set -euo pipefail

git pull --ff-only origin main

echo "===== HEAD ====="
git rev-parse --short HEAD

echo
echo "===== STATUS ====="
git status --short

echo
echo "===== SYNTAX CHECK ====="
docker compose run --rm -T lab \
  python -m py_compile \
  tools/diagnostics/normal_mine_single_candidate_immunity_repair_audit.py

echo
echo "===== STRICT NORMAL-MINE SURVIVOR AUDIT ====="
docker compose run --rm -T lab \
  python -u tools/diagnostics/normal_mine_single_candidate_immunity_repair_audit.py \
  | tee /tmp/normal_mine_single_candidate_immunity_repair.log

echo
echo "===== STATUS AFTER ====="
git status --short
```

Then inspect at minimum:

```text
===== INTERSECTED FIELD ELIGIBILITY =====
===== REPAIR TRACE =====
===== SUMMARY =====
```

Decision after runtime:

1. If every intersected field is explicitly immune, reject mine attribution.
2. If at least one intersected field is explicitly hostile/non-immune and one-hit repair predicts `66 / 3` exactly, retain a one-hit mine evidence case.
3. If field FC remains unavailable or immunity cannot be resolved, keep the mine attribution unresolved/evidence-only; do not guess hostility.
4. Even if one hit is attributable, do not create a production label from this one transition. Investigate the remaining movement-distance discrepancy separately and look for independent support.
5. Keep production accounting fixed at `2220` until a later change is independently tested and diff-verified.

## Git state at handoff creation

The project state immediately before creating this new-chat handoff was:

```text
main = 49ac4c382c6c6f55d4739fa5b7f2539737bd10cb
```

That commit already contained the strict survivor diagnostic and synchronized README / ROADMAP / COMPILED_CORPUS state. This handoff itself advances `main`, so a new chat must query actual GitHub HEAD instead of assuming the SHA above is still current.
