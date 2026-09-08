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

### Direct isolated phase classification — runtime closed

User runtime on HEAD `34bad43`:

```text
ordinary candidate_single_ship_battles: 631

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

Evidence:

```text
ordinary isolated standard left/right:
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

One ordinary C&I order signature had `left:targets_other_ship`; it did not qualify against the factual isolated opponent. Preserve it for later multi-ship target-selection analysis.

Special game 591478 remains strongly non-ordinary (`standard 75 right / 80 left`) and is not used to tune ordinary standard rules.

## Current gate: Priority Intercept Attack

Official Planets.nu rule:

1. installed cloak or advanced cloak device;
2. mission `Intercept`;
3. positive intercept target;
4. Primary Enemy matching target faction;
5. combat would otherwise occur with target.

The ship need not currently be cloaked. The entire intercepted pair's applicable combats occur before regular combats. Multiple PIA attackers act in reverse Ship ID order. Intercept Interference can demote Priority Intercept to normal combat priority and is a known confounder.

Canonical primitive added:

```text
priority_intercept_order_signature()
```

It checks only the static documented order signature and deliberately does not claim dynamic PIA eligibility.

Current files:

```text
src/planets_lab/rules/combat/order.py
tests/test_combat_order.py
tools/diagnostics/combat_host_priority_intercept_audit.py
tests/test_combat_host_priority_intercept_audit.py
```

The PIA audit reports:

- all owner-visible mission-7 records: target relation, cloak capability and qualifying signature;
- isolated mission-7 factual battles: true PIA vs non-PIA mission-7 orders and factual attacker side;
- PIA-linked unordered pairs, including the target's potential retaliation;
- whether PIA-linked pairs form the ship-combat prefix at each site;
- unique PIA attacker first-occurrence order vs documented reverse Ship ID;
- residual examples without auto-fitting Intercept Interference.

GitHub CI on code HEAD `9d02116fc785724289b6aa02b2e326c712a658e3` passed.

Targeted runtime:

```bash
cd ~/projects/planets-lab
set -euo pipefail

git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

pytest_args=(
  tests/test_combat_order.py
  tests/test_combat_host_priority_intercept_audit.py
  tests/test_combat_host_isolated_phase_classification_audit.py
)

docker compose run --rm -T lab pytest -q "${pytest_args[@]}"

mkdir -p logs

docker compose run --rm -T lab \
  python -u tools/diagnostics/combat_host_priority_intercept_audit.py \
    --example-limit 80 \
    --output logs/combat-host-priority-intercept.json \
  | tee logs/combat-host-priority-intercept.log
```

Acceptance is evidence-driven, not hardcoded. Particularly inspect ordinary:

```text
population.signature
combat.site_counts
combat.pia_attacker_sides
combat.isolated_mission7_classes
combat.isolated_non_pia_standard_priority
combat.multi_attacker_reverse_id
```

Desired clean invariants are PIA attacker on the right, PIA-linked prefix exact, non-PIA mission7 standard battles obeying canonical standard priority, and multi-attacker first-occurrence order matching reverse Ship ID. Any residual is classified before modifying mechanics.

## After Priority Intercept

1. investigate PIA residuals for Intercept Interference / other eligibility suppressors;
2. resolve exact matching-FC exceptions / Harmonic Weapon Modulation boundaries;
3. build dynamic multi-ship opponent selection;
4. handle capture/reinsertion and ownership changes;
5. integrate between-phase repair and ship-vs-planet ordering;
6. keep game 591478 sequence semantics separate.

PR #28 remains draft until ordering/eligibility semantics are sufficiently understood.
