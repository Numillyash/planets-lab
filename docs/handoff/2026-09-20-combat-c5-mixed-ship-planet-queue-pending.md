# C5 mixed ship / planet-base queue ordering — pending

Branch: `agent/combat-c5-host-phase`

GitHub is the source of truth. PR #28 remains open + draft. Game `591478` remains isolated.

## Closed prerequisites

### Ordinary ship queue

Closed:

- canonical initial STANDARD selector;
- directional targetability;
- mutable active membership;
- repeated-pair occurrence history;
- held-out post-mutation next-pair selection.

### Capture state

Closed production differential:

```text
23 capture continuations

owner/race/hull/shield/crew/torpedoes/fighters:
  23/23 exact

damage:
  22/23 exact
  one isolated known replay residual

capture_transition_gate_passed=True
```

### Post-capture initiators

Closed v2 population:

```text
23/23 observed continuations have an independent opponent initiator

ship opponents:
  8/8 Kill!/PE against the prize ship's new owner

planet/base opponents:
  15/15 NUK/ATT

explanation:
  opponent_only=21
  both=2
  captured_old_orders_only=0
  neither=0

required unresolved=0
optional captured-old-order history gaps=2

post_capture_initiator_gate_passed=True
```

Do not invent persistence of captured old mission/PE. It is not required by the observed population.

## Why mixed ship/planet ordering is next

Fifteen of the twenty-three production-validated prize-ship continuations enter planet/base combat immediately.

The ship-only queue is now substantially reconstructed, so the remaining high-value C5 boundary is:

```text
ship queue state
  +
planet/base attack/defense eligibility
  ->
mixed factual VCR ordering
```

## Questions to answer

1. At a site with both eligible ship-vs-ship and ship-vs-planet/base battles, which class is emitted first?
2. How are multiple attacking ships ordered against one planet/base?
3. How does ship STANDARD Combat Priority interact with planet/base combat?
4. Does a survivor/captured ship re-enter ship combat before or after planet/base combat?
5. How do NUK/ATT planet-initiated battles interleave with ship-initiated planet attacks?
6. What are the LEFT/RIGHT side rules for mixed queue steps?
7. How do planet/starbase destruction/capture-like terminal states affect the remaining queue?
8. Can one planet/base appear multiple times in a site queue, and under what termination rule?

## Evidence construction

Prefer a new read-only population audit before production changes.

The first pass should inventory every ordinary site containing both:

- at least one ship-vs-ship VCR; and
- at least one ship-vs-planet/base VCR.

For each site, record:

- factual VCR order;
- ship IDs / owner IDs;
- planet ID / owner ID;
- T-1 ship mission / PE / FC / static battle priority;
- T-1 planet FC, especially NUK/ATT;
- whether each pair is independently eligible under already-closed ship combat logic;
- survivor/capture history entering each mixed step.

Do not use factual queue rank as an input to the predictor.

## Promotion boundary

Do not promote a mixed-order rule from a small anecdotal sample.

The desired eventual gate is:

```text
independent pre-Host site reconstruction
  -> ship candidate graph
  -> planet/base candidate graph
  -> mutable queue state
  -> predicted next mixed VCR
  -> held-out factual next VCR
```

with factual VCR order comparator-only.

## Separate unresolved branches

Keep separate:

- generic Advanced Cloak predictor;
- capture-generated target list contents;
- isolated game `591478`;
- broad candidate-coverage expansion.

These must not be mixed into the first mixed-queue ordering gate.


## 2026-09-20 large-batch workflow

Per user workflow preference, C5 research now groups several related hypotheses into one longer batch rather than requiring one command per micro-gate.

New broad first-pass diagnostic:

```text
tools/diagnostics/combat_host_mixed_ship_planet_queue_batch_audit.py
```

Unit coverage:

```text
tests/test_combat_host_mixed_ship_planet_queue_batch_audit.py
```

One-command runner:

```text
tools/run-combat-c5-mixed-queue-batch.sh
```

Implementation commits:

```text
1e9a455c6b3dd1b93baff88150119636e7486424
  combat: add mixed ship-planet queue batch audit

e6f19ee1352d45da9f7afc2238a740569f195d3d
  test: cover mixed ship-planet queue batch audit

c40bc44eaca7551f5dfe25b17bca613d1c3f1394
  tools: add one-command C5 mixed queue batch

8e32455dbc40556283fdc1ff043ce1766e400a3a
  tools: keep mixed queue batch running after failures

a3b24234b07055ef1d3edbf6353ccad00cc47344
  tools: save full mixed queue batch log
```

### What the mixed diagnostic measures in one pass

1. mixed-site population and full factual queue profiles such as `SSPP`, `SPP`, etc.;
2. transition counts:
   - ship->ship;
   - ship->planet;
   - planet->planet;
   - planet->ship;
3. whether all ship combat forms a block before the planet/base block;
4. factual LEFT/RIGHT orientation of planet/base combat;
5. T-1 planet Friendly Code distribution and NUK/ATT population;
6. whether each planet attacker already participated in ship combat at the same site;
7. immediate same-ship ship->planet handoff counts;
8. capture->planet handoff counts;
9. repeated engagement groups against the same planet/base;
10. number of distinct planets per mixed site;
11. a deliberately naive comparison of repeated planet-attacker order against ordinary STANDARD ship Combat Priority.

The three ordering ideas are reported independently under `hypotheses`; a false hypothesis does not invalidate the batch and is expected to identify the next focused mechanic.

### One-command batch contents

The runner continues after individual stage failures and prints a final stage/RC summary.

It executes:

```text
pytest:
  mixed queue audit
  factual queue-shape audit
  planet mechanics + planet-chain audit
  ship post-mutation next-pair regression
  post-capture initiator regression
  host queue / mutable queue regressions

corpus:
  factual queue shape
  planet carry differential
  ship next-pair differential
  post-capture initiator differential
  mixed ship/planet discovery audit
```

Full output is automatically captured to:

```text
artifacts/combat-c5-mixed-queue-batch.log
```

JSON artifacts are written under `artifacts/`.

### Runtime

Use only:

```bash
cd ~/projects/planets-lab
git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

bash tools/run-combat-c5-mixed-queue-batch.sh
```

After completion, the full log file is sufficient for review. No need to manually run each diagnostic separately.


## 2026-09-20 first large-batch runtime — PASSED

Durable runtime:

```text
docs/handoff/2026-09-20-combat-c5-mixed-queue-batch-runtime-v1.md
```

Source HEAD:

```text
209abdad14682cfab8d9bc4729f2b63b4ad9a5a4
```

All six batch stages returned rc=0.

Major factual results:

```text
ordinary mixed sites=391

ship block before planet block=391/391
P->S transitions=0

planet RIGHT=435/435
planet LEFT=0

repeated planet groups=36
naive T-1 STANDARD priority:
  comparable=35
  exact=34
  mismatch=1
  unresolved=1
```

The single comparable mismatch is exactly:

```text
511506/T48 planet131
factual: ship489 -> ship480
naive old T-1 priority: ship480 -> ship489
ship480 is a post-capture candidate
```

Therefore ordinary planet ordering and capture-generated ordering must be separated.

## Production v2 work now committed

New production module:

```text
src/planets_lab/rules/combat/mixed_queue.py
```

It provides:

- strict phase state machine:
  `SHIP -> INTERPHASE_REPAIR_MKT -> PLANET -> COMPLETE`;
- evidence-backed ship LEFT / planet RIGHT projection;
- ordinary planet-attacker selection using standard Combat Priority;
- fail-closed handling for eligible post-capture generated-order candidates.

Tests:

```text
tests/test_combat_mixed_queue.py
```

Production/differential commits:

```text
86e300a697bb0481954b80af31cea441c498a0f0
afc7c8bf5b035b9c7a59c71293c65de75b9ceac3
d9fd97e3f6dd2edef1e2243815a51741de17df43
d5beeeae628bff538f267e60edc00fa84f6a83c6
25b5d0d9381a155662c626066e156520afabf5c4
915538e41c9e7e8319119dee59d94cccc387dd61
6fa40012db02c88f57d1ce50ece8506dc74d667d
3e600cad3a4b30e3c298c896eec7b0ba635f92b3
9334f29b20ca1d773e08e433c5059acc90e6e887
```

## v2 batch scope

The same one-command runner now additionally validates:

1. production phase boundary;
2. production ordinary planet selector;
3. basic planet fight initiator population:
   - ship Kill!/Primary Enemy;
   - planet NUK/ATT;
4. ordinary repeated planet ordering with post-capture groups excluded;
5. observational insertion shape for capture-containing groups;
6. ship->planet interphase state changes across the documented repair/MKT step.

New interphase diagnostic:

```text
tools/diagnostics/combat_host_ship_planet_interphase_state_audit.py
```

It inventories changes in:

```text
damage
crew
torpedoes
fighters
shield model
```

and adds T-1 supplies/minerals/order context to changed rows.

The audit intentionally does not yet implement repair/MKT mechanics.

## v2 runtime

Still one command:

```bash
cd ~/projects/planets-lab
git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase
bash tools/run-combat-c5-mixed-queue-batch.sh
```

Review the final stage summary plus:

```text
SHIP->PLANET INTERPHASE STATE
MIXED SHIP/PLANET DISCOVERY V2
```

The complete log remains:

```text
artifacts/combat-c5-mixed-queue-batch.log
```


## 2026-09-20 second large-batch runtime — PASSED

Durable runtime:

```text
docs/handoff/2026-09-20-combat-c5-mixed-queue-batch-runtime-v2.md
```

Source HEAD:

```text
3db42c59439226f249e19615197e75582de10590
```

All seven stages returned rc=0.

New closures:

```text
ordinary repeated planet attacker order:
  27/27 production exact
  post-capture groups excluded/fail-closed

ship->planet survivor state:
  374 exact carry
  8 damage decreases
  crew/torpedoes/fighters unchanged in 382/382 ordinary survivor rows
```

The eight damage decreases are compatible with the documented automatic supply-repair rule. Seven consume the full T-1 supply budget; one requires earlier Host supply consumption, which is allowed by earlier repair opportunities.

Production supply-repair primitive:

```text
src/planets_lab/rules/combat/interphase.py
```

Current unresolved mixed-order populations:

```text
planet initiator neither-basic-order=5
planet T-1 unresolved=5
ship T-1 unresolved=1

capture-containing repeated planet groups=9
  captured after all ordinary attackers=8
  captured interleaved before ordinary attacker=1
```

Therefore neither "all planet fights use only the eleven-race basic initiator surface" nor "captured planet attackers always append last" may be promoted yet.

## ACTIVE V3 LARGE BATCH

V3 adds:

- race-aware Horwasp Kill!/NUK equivalents;
- explicit initiator residual examples;
- all nine capture-group examples;
- factual VCR race ids;
- T-1 owner vs VCR owner context;
- production supply repair differential;
- prior-supply-consumption classification;
- MKT candidate inventory.

Still use one command:

```bash
cd ~/projects/planets-lab
git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase
bash tools/run-combat-c5-mixed-queue-batch.sh
```


## 2026-09-20 third large-batch runtime — PASSED

Durable runtime:

```text
docs/handoff/2026-09-20-combat-c5-mixed-queue-batch-runtime-v3.md
```

Source HEAD:

```text
26703b5556e5fe40a0bea2e3ea9c3d9f3378bbc2
```

All seven stages returned rc=0.

New production closure:

```text
ship->planet interphase supply repair gate:
  passed=True
  positive observed repairs=8
  production positive exact=7
  production positive mismatch=0
  hard supply-budget contradictions=0

crew/torpedoes/fighters preserved=382/382 ordinary survivor transitions
repair rows without shield recharge=8/8
```

MKT remains observational only:

```text
MKT candidates=36
torpedo count unchanged=36/36
```

Mixed v3 residuals:

```text
neither-basic-order=5
capture-containing repeated planet groups=9
```

All five initiator residuals have same VCR ship/planet owner but a different VCR planet race. Do not promote same-owner combat. V4 must resolve planet ownership through independent race->player mapping and current-owner confirmation.

Capture-order v4 hypothesis:

```text
captured entrant:
  preserve Friendly Code
  clear old Mission/Primary Enemy aggression priority
  recompute STANDARD Combat Priority
```

V4 implementation commits now include:

```text
71a33a171dc0f884a7c8790344d91517909af61d
  combat: add owner repair and capture-reset ordering differential

336b23c05886f9a8aaa3878ac06d79929f9fcc02
  combat: add all-planet engagement population audit

d209ab94ad4b7679e408b0ac1e24f79c0ab51239
  test: cover owner repair and capture-reset planet ordering

9dc73740025ec1f2fb0f548b609b6c2e351e0bb1
  tools: add all-planet owner and initiator sweep to C5 batch

85dae5e96328ad79ba6b11751d3a2aec0077ca28
  diagnostics: include planet owner repair in mixed row output

eca2e00c8b150d13ab599727944cdc1e826b0e5c
  docs: record mixed queue batch v3 runtime
```

### ACTIVE V4 LARGE BATCH

The one-command runner now adds:

```text
ALL PLANET ENGAGEMENT POPULATION
MIXED SHIP/PLANET DISCOVERY V4
```

The all-planet stage covers every ordinary ship-vs-planet VCR and tests:

- raw VCR owner versus race->player owner mapping;
- T-1 and T planet ownership context;
- owner repairs only for impossible same-owner VCR rows;
- ship Kill!/PE initiation;
- planet NUK/ATT initiation;
- Horwasp Kill!/NUK-equivalent initiation;
- hard residual population after owner repair.

Mixed V4 additionally tests capture-reset priority across all capture-containing repeated planet groups.


## 2026-09-20 fourth large-batch runtime — PASSED

Durable runtime:

```text
docs/handoff/2026-09-20-combat-c5-mixed-queue-batch-runtime-v4.md
```

Source HEAD:

```text
f48e39ee46ce5a9f8d7605adbb320d61b3e5883f
```

All eight stages returned rc=0.

### All ordinary ship-vs-planet initiators

```text
ordinary ship-vs-planet VCRs = 2406
ship_only                     = 1981
planet_only                   = 86
both                          = 337
unresolved                    = 2
hard residuals                = 0
planet_engagement_population_gate_passed=True
```

This is a population-attribution closure only. Factual VCR planet-owner identity is not a production precombat input.

### Correction to v3 same-owner interpretation

The v3 residual field `planet_owner_id` was T-1 reconstructed owner, not factual VCR owner.

V4 explicitly showed:

```text
owner_resolution:vcr_owner_foreign = 2406/2406
same-owner VCR rows                 = 0
race-map repair rows                = 0
```

Therefore the five v3 residuals were stale-T-1-owner artifacts. Do not preserve a same-owner combat hypothesis.

The production problem is now narrower and correctly stated:

```text
reconstruct planet owner after earlier Host ownership-changing phases
and before ship-vs-planet combat
```

### Capture-generated planet priority

```text
capture-containing repeated planet groups = 9
comparable capture-reset groups            = 8
exact                                      = 8
mismatch                                   = 0
unresolved                                 = 1
```

The one unresolved group is `622476/T13 planet55`, because captured ship68 lacks T-1 state.

Supported bounded rule:

```text
captured generated order:
  preserve Friendly Code priority
  clear old Mission/Primary Enemy aggression priority
  use STANDARD Combat Priority
```

Production commits after the runtime:

```text
0ea90f55844673f660ea3914207d2d819a2c97c8
  combat: support capture-reset planet priority

6eab133f19e3a161d4c6ba3994a4c81bfc69f686
  test: cover production capture-reset planet priority

eb1845f65bc1d757b98bbf8aa48256552a325336
  diagnostics: diff capture-reset planet priority through production

462fc34890683b79f12bb7520b687b64458db7dc
  test: route capture ordering through production selector
```

The next runtime must promote this from experimental 8/8 to production `DIFF_VERIFIED` if the production selector reproduces the same population.

## ACTIVE V5 LARGE BATCH

V5 adds:

```text
PLANET OWNERSHIP TIMELINE
MIXED SHIP/PLANET DISCOVERY V5
```

New diagnostic:

```text
tools/diagnostics/combat_host_planet_ownership_timeline_audit.py
```

It measures all ordinary:

```text
T-1 planet owner
  -> factual VCR defender owner
  -> T post-Host owner
```

and classifies:

- owner unchanged before combat;
- precombat owner changed;
- precombat owner changed from attacker slot to factual defender slot;
- postcombat defender retained;
- postcombat attacker owns planet;
- neutral/other/unresolved outcomes.

Factual VCR and T remain attribution/comparator evidence only. This stage measures the size of the production ownership-transition subsystem that must be reconstructed; it does not feed factual VCR owner into production.

V5 also routes all comparable capture-containing repeated planet groups through the real production selector.


## 2026-09-21 fifth large-batch runtime — PASSED

Durable runtime:

```text
docs/handoff/2026-09-21-combat-c5-mixed-queue-batch-runtime-v5.md
```

Source HEAD:

```text
8aadffd019fab8017dc149eb7b3fba72097e3068
```

All nine stages returned rc=0.

### Capture-generated planet priority — production closure

```text
production repeated planet order:
  comparable=35
  exact=35
  mismatch=0
  unresolved=1

capture subset:
  comparable=8
  exact=8
  mismatch=0
  unresolved=1
```

The sole unresolved group remains `622476/T13 planet55`, where captured ship68 lacks T-1 ship state.

Status:

```text
capture-generated planet priority:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Bounded rule:

```text
preserve captured Friendly Code priority
clear captured old Mission / Primary Enemy aggression priority
evaluate ordinary STANDARD Combat Priority
```

Eligibility/targetability remains independently composed.

### Planet ownership timeline

```text
ordinary planet VCRs=2406
unique planet-turn timelines=2303
precombat owner changed=60 VCR rows / 59 unique planet-turns
precombat owner unchanged=2334 rows
T-1 owner unresolved=12 rows

changed from attacking ship owner to factual defender:
  43 VCR rows / 42 unique planet-turns

changed between third-party owners:
  17 VCR rows
```

VCR defender is foreign to the attacking ship and race-owner consistent in 2406/2406 rows.

The remaining production gap is not combat ordering. It is reconstruction of planet ownership changes earlier in Host.

## ACTIVE V6 LARGE BATCH

V6 adds:

```text
PLANET PRECOMBAT OWNER SOURCE
MIXED SHIP/PLANET DISCOVERY V6
```

New diagnostic:

```text
tools/diagnostics/combat_host_planet_precombat_owner_source_audit.py
```

It inventories all 59 changed planet-turns for T-1 co-located ships, future-defender ownership and positive clan cargo. It also exposes actual drop/transfer/mission/target fields present on those ship objects.

Official Host order places cargo drop / Imperial Assault / Ground Combat before later combat and processes it in Ship ID order. This is only a hypothesis source for the audit; no ground-combat transition is promoted yet.


## 2026-09-21 sixth large-batch runtime — PASSED

Durable runtime:
`docs/handoff/2026-09-21-combat-c5-mixed-queue-batch-runtime-v6.md`

Source HEAD:
`370ecaf5de029fadfd0acafd1107e1fb35c9cb54`

All ten stages returned rc=0.

Stable production mixed ordering remains:

```text
production repeated planet order=35/35 exact comparable
capture-reset priority=8/8 exact comparable
mismatch=0
```

Precombat ownership source inventory:

```text
positive-owner reversal timelines=42
future-defender ship co-located=42/42
future-defender ship with onboard clans>0=33/42
without onboard clans>0=9/42
```

Correction: V6 did not cover all 59 unique owner-change timelines. The current positive-owner adapter covers 42; the remaining 17 require separate neutral/other owner-state handling.

The key new evidence is explicit directed clan-transfer state on T-1 ships. Rows with `clans=0` may still have `transferclans>0` targeted directly at the planet. Therefore onboard cargo alone is not the correct next criterion.

### ACTIVE NEXT OWNERSHIP GATE

Reconstruct directed planet clan drops using:

```text
transferclans > 0
transfertargettype == planet
transfertargetid == planet_id
```

then evaluate sequential ownership effects in Host Ship-ID order.

No generic ground-combat ownership transition is promoted before that differential.
