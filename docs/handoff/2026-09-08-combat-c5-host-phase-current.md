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

```text
mission 3  = Kill!
mission 7  = Intercept
mission 20 = Bird Cloak and Intercept
enemy      = Primary Enemy
```

Evidence:
- `mission 3 = Kill!`: documented causal rule + ordinary `CORPUS_OBSERVED` numeric mapping;
- `enemy = Primary Enemy`: ordinary `CORPUS_OBSERVED`;
- `mission 20 = Cloak and Intercept`: 97/97 mission-20 owner records are race 3; ordinary 37/37 race 3, 36/37 positive targets; documented C&I behavior matches historical target/PE signatures.

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

Prior last standard residual, game 621253 / battle T10 / VCR 8, is a factual C&I attack:

```text
right ship 57 / Dark Wing / owner 3
mission=20
mission1target=50
enemy=4
target ship 50 owner=4
```

### Direct isolated phase classification — CLOSED

User runtime on HEAD `34bad43`:

```text
ordinary candidate_single_ship_battles: 631

phases:
  standard:                      413
  priority_intercept_unresolved: 196
  matching_fc_unresolved:         13
  cloak_intercept_pre_standard:    7

standard_side_priority:
  right_higher_priority: 413
  left_higher_priority:    0

cloak_intercept_factual_side:
  c_and_i_right: 7
```

Evidence:

```text
ordinary isolated supported standard left/right:
DOCUMENTED priority model
+ CORPUS_OBSERVED signed-FC extension
+ TESTED canonical primitive
+ DIFF_VERIFIED 413/413

ordinary isolated factual C&I attacker side:
CORPUS_OBSERVED 7/7 right
```

One ordinary C&I order signature had `targets_other_ship`; preserve it for later multi-ship target selection.

Special game 591478 remains strongly non-ordinary and is not used to tune ordinary standard rules.

### Priority Intercept Attack — static signature / factual queue evidence

Canonical helper:

```text
priority_intercept_order_signature()
```

It recognizes only the documented static order signature:

```text
mission=7
cloak-capable hull
positive Intercept target
Primary Enemy == target owner
```

It deliberately does not claim dynamic PIA eligibility; Intercept Interference, diplomacy, fuel, matching FC and other suppressors remain separate.

Runtime on HEAD `034f33b`:

```text
summary:
  archives: 12
  mission7_records: 2985
  ship_combat_sites: 1829
  payload_conflicts: 0
```

Ordinary mission-7 population:

```text
records: 1177
hull_can_cloak: false 1069 / true 108
target_relation:
  other_owner: 757
  same_owner: 400
  zero_or_missing: 17
  owner_unresolved: 3
static signature:
  false: 1088
  true:    69
  unknown: 20
```

This independently shows that `mission=7` is not synonymous with Priority Intercept.

Ordinary factual ship-combat queues:

```text
sites: 1220
sites_with_pia_linked_pair: 37
pia_prefix_exact: 37
pia_prefix_violation: 0
pia_attacker_sides:
  attacker_right: 37
```

Evidence on the observed ordinary linked-pair population:

```text
Priority Intercept pair before regular ship combat: CORPUS_OBSERVED + DIFF_VERIFIED 37/37
Priority Intercept attacker on right:              CORPUS_OBSERVED + DIFF_VERIFIED 37/37
```

No ordinary site contains two independently comparable PIA attackers:

```text
multi_attacker_reverse_id: {}
```

Therefore documented reverse-Ship-ID ordering remains `DOCUMENTED`, not `DIFF_VERIFIED` in the current corpus.

Ordinary isolated mission7 factual classes:

```text
mission7_non_pia: 195
pia_right:         26
```

Among supported, nonmatching-FC non-PIA mission7 isolated cases, canonical standard priority gives:

```text
right_higher_priority: 180
left_higher_priority:    2
```

Do not weaken standard ordering to absorb those two rows.

## Canonical C5 rules layer

Current file:

```text
src/planets_lab/rules/combat/order.py
```

It contains only narrow evidence-backed primitives:

- mission constants for Kill / Intercept / Cloak-and-Intercept;
- documented `001..999` and corpus-verified exact signed-three-character FC parsing;
- standard battle-priority key;
- narrow Kill/PE hostility request helper;
- fail-closed C&I order signature;
- fail-closed static PIA order signature.

Full combat eligibility is intentionally not implemented yet.

## Current gate: two non-PIA mission7 standard-side residuals

Diagnostic:

```text
tools/diagnostics/combat_host_priority_intercept_non_pia_residual_audit.py
tests/test_combat_host_priority_intercept_non_pia_residual_audit.py
```

It selects only isolated battles where:

- mission 7 is present;
- neither side has a qualified static PIA signature against the factual opponent;
- PIA signature is not unknown;
- FC parsing is supported and FCs do not match;
- canonical standard key predicts the factual left side has higher priority.

It outputs race, hull name/special/cloak capability, mission targets, PE, FC, target owner, fuel and damage for both sides.

Expected ordinary count from the prior runtime is exactly 2. Classify these rows before proceeding.

GitHub CI on code HEAD `7e2ce445e8919b5978a4ec1a4f6569fd1bb62537` passed.

## After the two residuals

1. resolve exact matching-FC combat exceptions / Harmonic Weapon Modulation boundaries;
2. build dynamic multi-ship opponent selection;
3. incorporate PIA/C&I pair selection into the dynamic queue;
4. handle capture/reinsertion and ownership changes;
5. integrate between-phase repair and ship-vs-planet ordering;
6. keep game 591478 sequence semantics separate.

PR #28 remains draft until ordering/eligibility semantics are sufficiently understood.
