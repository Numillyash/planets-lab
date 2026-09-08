# C5 Host combat phase — current handoff — 2026-09-08

GitHub is the only source of truth. Always inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing.

Current durable evidence is split between this high-level handoff and:

- `docs/handoff/2026-09-08-combat-c5-signed-fc-runtime.md`

## Objective

Reconstruct the NuHost combat phase that generates VCR engagements, order and sides. Keep factual VCRs, inferred semantics and simulator rules separate. Unknown branches fail closed. Game `591478` remains a separate special/campaign/Horwasp bucket.

## Current repository alignment

At the latest sync point:

```text
main: 89b5b0f1c06869a0d03d04cba76caa78bc4b10ce
```

C5 has been merge-synchronized with that main commit. The main-only delta was a movement-only zero-cost Move Most diagnostic fix; there was no combat overlap.

## Completed C5 evidence

### Factual queue shape

12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.

Ordinary:

```text
combat sites: 3132
multi-VCR sites: 639
ship-vs-ship VCRs: 1988
ship-vs-planet VCRs: 2406
phase-order violations: 0
repeated ship-pair sites: 2
pair >2 fights: 0
```

Evidence: `CORPUS_OBSERVED`. Ship combat precedes planet combat in all ordinary factual queues; ordinary same-pair population respects the documented maximum two fights.

### Pre-combat orders state

Use owner-visible archive snapshot `T-1` for VCR battle turn `T`.

Ordinary factual ship sides: 6382.

```text
T-1 present: 6370/6382
T-1 owner+hull match: 6347/6370
mission / mission1target / friendlycode present: 6370/6370

T present: 5612/6382
T owner+hull match: 3655/5612
```

Do not use T-1 position as an alignment gate; T-1 precedes Move while VCR positions are post-Move.

### Raw order fields

Owner-visible ship records: 256,780.

Structurally stable fields:

```text
mission
enemy
mission1target
mission2target
friendlycode
```

No explicit mission-name catalog was found in raw RST.

### Kill! / Primary Enemy

Ordinary ship-vs-planet causal evidence establishes:

```text
mission 3 = Kill!
enemy     = Primary Enemy
```

Evidence:
- `mission 3 = Kill!`: documented causal rule + `CORPUS_OBSERVED` numeric mapping;
- `enemy = Primary Enemy`: `CORPUS_OBSERVED`.

### Standard isolated ship side/order

Conservative ordinary single-VCR ship-only subset, excluding normal Priority Intercept, matching FC and broken T-1 identity:

```text
comparable: 420
baseline standard key:
  right higher priority: 417
  left higher priority:    3
```

Exact-three-character signed numeric FC hypothesis `[+/-][0-9][0-9]` was independently tested:

```text
right higher priority: 419
left higher priority:    1
```

The two residuals with right-side FCs `-54` and `-52` disappeared exactly, with no new ordinary residuals.

Evidence:

```text
exact-three-character signed numeric FC parsing:
CORPUS_OBSERVED + DIFF_VERIFIED
NOT DOCUMENTED
```

Do not generalize to arbitrary signed-string lengths.

### Diplomacy hypothesis for the final residual — rejected

Raw pre-combat turn-9 relation records for game 621253 owners 4↔3:

```text
4->3: relationto=1 relationfrom=0 conflictlevel=0
3->4: relationto=1 relationfrom=1 conflictlevel=0
```

The pair has no Safe Passage-or-higher relation. Diplomacy does not explain the residual. Do not yet canonicalize detailed `relationto/relationfrom` perspective semantics; the two raw rows are not simple mirrors.

### Numeric mission 20 = Bird Cloak and Intercept

Tool:

```text
tools/diagnostics/combat_host_mission20_cloak_intercept_audit.py
```

12-archive runtime:

```text
all mission-20 records: 97
race_conflict_games: 0
owner_races: race 3 = 97/97
```

Ordinary population:

```text
records: 37
owner_races: race 3 = 37/37
owner_hulls: {31:16, 27:9, 29:8, 32:3, 26:1}
target positive: 36/37
target other owner: 36/36 applicable
enemy matches target owner: 22
enemy zero: 14
iscloaked: true 26 / false 11
```

Special game 591478 remains separate and also uses mission 20 only on race 3 ships, but is not used to tune ordinary rules.

The only prior ordinary isolated standard-side residual was:

```text
game 621253
battle turn 10
VCR 8

left:
  ship 50 / hull 37 / owner 4
  mission=0 / enemy=3 / FC=wxd

right:
  ship 57 / hull 29 / owner 3
  mission=20 / enemy=4 / FC=osq
```

Pre-combat T-1 record for ship 57:

```text
owner race: 3
hull: 29
mission: 20
mission1target: 50
enemy: 4
target ship 50 owner: 4
targets_expected_opponent: true
```

Official Planets.nu Race Sheet documents Bird `Cloak and Intercept`: cloaking ships may remain cloaked while intercepting, and if Primary Enemy matches the intercept target faction they engage that target before the regular combat phase.

Therefore the evidence supports:

```text
mission 20 = Cloak and Intercept
numeric mapping: CORPUS_OBSERVED
phase semantics: DOCUMENTED
residual classification: CORPUS_OBSERVED + documented rule
```

The prior `419/420` standard-side result should now be interpreted as:

```text
419 ordinary standard comparable cases: 419/419 right-side priority matches
1 prior residual: not a standard battle; C&I pre-standard case
```

This must still be encoded and rerun as a direct differential rather than merely accepted by arithmetic exclusion.

## Current gate: canonical pre-standard vs standard classification

Next implementation should introduce small provenance-preserving C5 order primitives, not a full Host simulator yet:

1. accepted Friendly Code battle-priority parsing, including exact-three-character signed `[+/-][0-9][0-9]` corpus behavior;
2. `mission 3 = Kill!` mapping;
3. `mission 7 = Intercept` existing project convention;
4. `mission 20 = Cloak and Intercept` mapping;
5. standard battle-priority key;
6. classify C&I target/PE match as pre-standard;
7. keep normal Priority Intercept qualification separate until its cloak-capability and target evidence is audited.

Then rerun isolated ordinary battles and require direct accounting:

```text
standard comparable: 419 / 419 explained
C&I pre-standard:       1 / 1 explained
unresolved ordinary isolated residuals: 0
```

Do not treat this as full engagement generation yet.

## After isolated phase classification

1. reconstruct normal Priority Intercept (`mission=7`) qualification and reverse-Ship-ID ordering;
2. handle exact matching-FC exceptions;
3. build dynamic multi-ship opponent selection;
4. handle capture/reinsertion and ownership changes;
5. integrate the repair boundary and ship-vs-planet phase;
6. keep special game 591478 separate.

PR #28 remains draft until ordering/eligibility semantics are sufficiently understood.
