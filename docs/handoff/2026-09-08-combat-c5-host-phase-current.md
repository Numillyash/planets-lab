# C5 Host combat phase — current handoff — 2026-09-08

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

## Objective

Reconstruct the NuHost combat phase that generates VCR engagements, order and left/right sides. Facts, inferred semantics and simulator rules remain separate; unknown branches fail closed.

## Repository alignment

C5 was merge-synchronized with `main=89b5b0f1c06869a0d03d04cba76caa78bc4b10ce`. The synchronized main delta was movement-only and had no combat overlap.

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

### Pre-combat order state

Use owner-visible archive snapshot `T-1` for VCR battle turn `T`.

```text
ordinary factual ship sides: 6382
T-1 present: 6370/6382
T-1 owner+hull identity match: 6347/6370
mission / mission1target / friendlycode present: 6370/6370

T present: 5612/6382
T owner+hull identity match: 3655/5612
```

Do not use T-1 position as an alignment gate; T-1 precedes Move while VCR coordinates are post-Move.

### Established raw/order mappings

Owner-visible order fields are structurally stable:

```text
mission
enemy
mission1target
mission2target
friendlycode
```

Established numeric semantics:

```text
mission 3  = Kill!
mission 7  = Intercept        # existing project convention; full PIA qualification is current gate
mission 20 = Bird Cloak and Intercept
enemy      = Primary Enemy
```

Evidence:
- `mission 3 = Kill!`: documented causal rule + ordinary `CORPUS_OBSERVED` numeric mapping;
- `enemy = Primary Enemy`: ordinary `CORPUS_OBSERVED`;
- `mission 20 = Cloak and Intercept`: 97/97 mission-20 owner records are race 3; ordinary 37/37 race 3, 36/37 positive targets; documented C&I behavior matches the historical signature.

### Friendly Code battle priority

Canonical C5 parser in `src/planets_lab/rules/combat/order.py`:

```text
001..999          -> documented numeric priority
[+/-][0-9][0-9]  -> signed numeric priority, CORPUS_OBSERVED + DIFF_VERIFIED, NOT DOCUMENTED
000 / numeric-looking other lengths -> unsupported / fail closed
symbolic FC       -> standard Kill/PE groups
```

Signed-FC runtime changed the conservative ordinary isolated differential from `417 right / 3 left` to `419 right / 1 left`, removing exactly the `-54` and `-52` residuals with no new residuals.

### Diplomacy hypothesis for the last pre-classification residual — rejected

Game 621253, pre-combat T9, owners 4↔3:

```text
4->3: relationto=1 relationfrom=0 conflictlevel=0
3->4: relationto=1 relationfrom=1 conflictlevel=0
```

No Safe Passage-or-higher relation exists; diplomacy did not explain the residual. Do not canonicalize detailed relation perspective semantics yet.

### Mission 20 / Cloak and Intercept

12-archive mission-20 population:

```text
all records: 97
owner race 3: 97/97
ordinary records: 37
ordinary race 3: 37/37
ordinary positive target: 36/37
```

Prior last standard residual, game 621253 / battle T10 / VCR 8:

```text
right ship 57 / Dark Wing / owner 3
mission=20
mission1target=50
enemy=4
target ship 50 owner=4
```

It is a factual C&I attack and not a regular combat-order residual.

### Direct isolated phase classification — runtime closed

Tool:

```text
tools/diagnostics/combat_host_isolated_phase_classification_audit.py
```

User runtime on HEAD `34bad43` passed all targeted tests.

Ordinary single-VCR ship-only population:

```text
candidate_single_ship_battles: 631

phases:
  standard:                      413
  priority_intercept_unresolved: 196
  matching_fc_unresolved:         13
  cloak_intercept_pre_standard:    7

identity exclusions:
  T-1 mismatch: 1
  T-1 missing:  1
```

Direct standard differential:

```text
standard: 413
right_higher_priority: 413
left_higher_priority:    0
```

Therefore ordinary isolated standard left/right assignment is now:

```text
DOCUMENTED priority model
+ CORPUS_OBSERVED signed-FC extension
+ TESTED canonical primitive
+ DIFF_VERIFIED 413/413
```

Cloak-and-Intercept factual side:

```text
C&I pre-standard isolated battles: 7
C&I attacker right:                7/7
C&I attacker left:                 0
```

This independently supports the documented aggressive/pre-standard right-side behavior.

One ordinary C&I signature had `left:targets_other_ship`; it did not qualify against the factual isolated opponent and did not affect the 7 C&I target fights. Preserve it for later multi-ship target-selection analysis.

Special game 591478 remains strongly non-ordinary:

```text
standard: 155
right_higher_priority: 75
left_higher_priority: 80
C&I pre-standard: 20, all factual C&I attackers right
mixed C&I + mission7 unresolved: 1
```

Do not tune ordinary standard rules from this game.

## Current gate: normal Priority Intercept Attack (`mission=7`)

Official Planets.nu rule requires all of the following for Priority Intercept Attack:

1. installed cloaking or advanced-cloaking device;
2. mission `Intercept`;
3. positive intercept target;
4. Primary Enemy matching the target faction;
5. combat would otherwise occur with that target.

The ship does not need to be cloaked at attack time. If multiple PIA attackers are present, their combats occur in reverse Ship ID order. The target's retaliatory combat against the interceptor is also before regular combats. Intercept Interference can demote Priority Intercept to normal combat priority and must be kept as a possible confounder rather than silently ignored.

Next implementation/audit should:

- add a fail-closed `priority_intercept_order_signature()` primitive to `order.py`, requiring mission 7, positive target, PE=target owner and known cloak capability;
- audit all ordinary owner-visible mission-7 records for target/PE/cloak signature coverage;
- reclassify the 196 ordinary isolated mission-7 battles into true PIA vs non-PIA standard/mismatch cases;
- for uniquely qualified PIA-vs-target isolated cases, count factual attacker side;
- on multi-VCR sites, mark the entire intercepted unordered pair as PIA-linked (up to the documented two fights) and test that PIA-linked fights form the combat prefix;
- where multiple unambiguous PIA attackers exist at one site, test first-attacker ordering against reverse Ship ID;
- report, do not auto-fit, any prefix/order residuals for Intercept Interference analysis.

## After Priority Intercept

1. resolve exact matching-FC exceptions / Harmonic Weapon Modulation boundaries;
2. build dynamic multi-ship opponent selection;
3. handle capture/reinsertion and ownership changes;
4. integrate between-phase repair and ship-vs-planet ordering;
5. keep game 591478 sequence semantics separate.

PR #28 remains draft until ordering/eligibility semantics are sufficiently understood.
