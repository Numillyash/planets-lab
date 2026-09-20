# C5 Host combat phase — current handoff

GitHub is the only source of truth. Verify actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 must remain **open + draft** and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

Progress overview: `docs/handoff/2026-09-20-reverse-progress-assessment.md`.

## Stable C5 layers

Do not reopen absent a direct contradiction:

- deterministic pair composition in `src/planets_lab/rules/combat/selection.py`: `TESTED`;
- direct ordinary STANDARD priority: 413/413 higher static priority on RIGHT;
- normal PIA: 37/37 before regular combat, attacker RIGHT 37/37;
- isolated C&I attacker: 7/7 RIGHT;
- scoped Galactic Power Case2, reciprocal PIA and matching-FC closures;
- plain STANDARD repeated-pair second-pass side reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- owner-current `T-1` is the precombat order/state source;
- `T` is post-Host/postcombat and may reuse Ship IDs; never use it as production precombat state;
- static STANDARD Combat Priority and Friendly Code parser remain unchanged.

## Position / candidate checkpoint

```text
position v3:
  factual ship occurrences=3204
  predicted=1810 exact=1806 mismatch=4 uncovered=1383
  factual pairs exact=678 mismatch=4 unresolved=1304

candidate-set v2:
  factual unique pairs=1986
  candidate-covered=428
  conditional factual eligible=427 unresolved=1 blocked=0
  strict factual eligible=420 unresolved=8 blocked=0
```

## Initial plain-STANDARD selector — CLOSED

Production:

```python
select_initial_plain_standard(...)
```

Evidence order:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Runtime:

```text
docs/handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-runtime.md
```

Differential:

```text
strict:      225/225 broad, 162/162 exact-set
conditional: 234/234 broad, 169/169 exact-set
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Unresolved candidates, eligible pre-standard pairs, unsupported priority or STANDARD side overrides fail closed.

## Directional ordinary-STANDARD targetability — CLOSED

Canonical pair input:

```python
ShipCombatSideInput.standard_targetable_by_opponent: bool | None
```

Semantics:

- affects only the opponent's ordinary STANDARD request;
- is applied after PIA/reciprocal-PIA/C&I classification;
- is directional, not a symmetric pair blocker;
- preserves the potentially cloaked ship's own attack request;
- never encodes cloak as `has_fuel=False`;
- unknown is fail-closed.

Population gate:

```text
supported blocks=10
conflicts=0
blocked factual pair rows=0
potential first-selector regressions=0
baseline mismatch profiles fixed=4/4
unrelated mismatches=0
```

Runtime:

```text
docs/handoff/2026-09-16-combat-c5-directional-targetability-population-runtime.md
docs/handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md
```

## Production precombat effective state — CLOSED for ordinary Privateer/Bird scopes

Privateer ordinary Rob:

```python
privateer_rob_ordinary_cloak_state(...)
```

Scope:

```text
race5 + mission9 Rob + ordinary cloak-capable hull
prior false                          -> effective cloak False
prior true + fuel <= reference cost -> effective cloak False
prior true + fuel >  reference cost -> effective cloak True
advanced cloak                       -> unresolved
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Bird ordinary Super Spy production API:

```python
bird_super_spy_ordinary_cloak_state(...)
standard_targetability_from_effective_cloak(...)
```

Runtime:

```text
docs/handoff/2026-09-16-combat-c5-production-effective-state-runtime.md
```

User runtime source:

```text
6a5e39796e385f4d98dc10697d30c958ad3a8898
41 targeted tests passed
```

Population result:

```text
bird_super_spy_targets_at_factual_sites=30
raw/conditional/strict one-way plain-STANDARD opportunities=8

decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
blocked factual-pair regressions=0
```

Focused residual:

```text
511506/T94 target202 <- attacker496
effective_cloak=True
standard_targetable_by_opponent=False
```

All production effective-state acceptance flags passed. Ordinary Bird Super Spy targetability is therefore:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The three unresolved decisive rows remain Advanced Cloak by design.

## Advanced Cloak — historical closure only

Known decisive rows:

```text
620694/T119 ship26 vs74 — expected blocked
620694/T119 ship69 vs74 — expected blocked
680435/T31 ship68 vs26 — factual pair / expected eligible
```

Historical closure:

- ship68: explicit mine hit -> damage55 -> same damage in factual VCR -> combat eligible;
- ship26/69: stable same-owner/same-hull T attribution, damage0, iscloaked=true -> skipped.

Do not promote a generic predictor. Post-Host T/messages are attribution evidence only.

## C3 survivor carry-over — prerequisite for current gate

Existing production in `src/planets_lab/rules/combat/sequence.py`:

```python
carry_ship_to_next_engagement(...)
```

Clean owner-certain same-turn same-location C3 subset:

```text
5 eligible transitions
5/5 exact under carry-over model
old reset baseline only 3/5
```

Captured predecessor transitions were explicitly excluded because ownership/hostility continuation is a separate mechanic.

## MUTABLE SHIP QUEUE — CLOSED

Pending handoff:

```text
docs/handoff/2026-09-16-combat-c5-mutable-ship-queue-pending.md
```

Production module:

```text
src/planets_lab/rules/combat/mutable_queue.py
```

API:

```python
ShipQueueMutationResult
apply_ship_terminal_batch(...)
```

Supported semantics:

```text
destroyed -> remove from active map
survivor  -> require full C3 dynamic vector and carry state
captured  -> unresolved / fail closed
```

Mutation is atomic. Capture, unknown terminal flags, incomplete survivor state or carry failure return the original active map unchanged.

Diagnostic:

```text
tools/diagnostics/combat_host_mutable_ship_queue_audit.py
```

Tests:

```text
tests/test_combat_mutable_queue.py
tests/test_combat_host_mutable_ship_queue_audit.py
```

Required acceptance:

```text
survivor_population_present=True
survivor_membership_exact=True
capture_fail_closed_if_observed=True
destroyed_removal_if_reappearance_observed=True
no_production_mutation_errors=True
no_terminal_flag_unknowns=True
mutable_ship_queue_transition_gate_passed=True
```

Evidence boundary: exact dynamic field carry remains the independent C3 differential's responsibility. This gate tests active membership/continuation only. Absence of destroyed-reappearance rows is not treated as standalone proof of destruction order.

## Next C5 work after mutable membership

If green:

1. compose active membership mutation with initial selector;
2. add pair occurrence state and second-pass eligibility/orientation using the already DIFF_VERIFIED side-reversal helper;
3. validate the second ordinary STANDARD queue step against factual queues;
4. reconstruct capture continuation separately;
5. integrate ship-to-planet / planet-base queue ordering.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct.


## ORDINARY STANDARD QUEUE HISTORY/SECOND OCCURRENCE — CLOSED

Pending runtime:

```text
docs/handoff/2026-09-18-combat-c5-standard-queue-composition-pending.md
```

The first mutable-queue corpus run was contaminated by isolated game `591478`: it ran 12 archives, and all 29 printed destroyed-predecessor reappearances came from that game. The ordinary gate has been repaired to exclude `591478`, matching the other C5 population diagnostics. Do not weaken the hard contradiction acceptance; rerun on the 11 ordinary archives.

New production module:

```text
src/planets_lab/rules/combat/host_queue.py
```

API:

```python
StandardQueueState
StandardQueueStepResult
select_next_plain_standard(...)
select_after_ship_mutation(...)
record_standard_queue_step(...)
```

This layer composes active membership, the canonical selector and pair-occurrence history without recomputing pair mechanics. Pair inputs after a mutation must be supplied freshly by the caller.

Second-occurrence production corpus gate:

```text
tools/diagnostics/combat_host_second_standard_queue_audit.py
```

Scope is deliberately narrow: stable-owner, exactly-two, plain-static-comparable repeated pairs from the ordinary corpus. Expected population remains the two existing controls from games 620917 and 621896. Passing this gate promotes production occurrence-history composition only; full post-mutation next-pair selection among a multi-pair stack remains the following gate.


## 2026-09-18 runtime closure

Runtime source HEAD:

```text
87bef989984c909b61e79f86f06fb575cb69c431
```

Durable runtime:

```text
docs/handoff/2026-09-18-combat-c5-mutable-and-second-standard-runtime.md
```

Ordinary mutable queue population after excluding isolated game `591478`:

```text
archives=11
same_location_transitions=1169
survivor_membership_exact=1146/1146
captured_fail_closed_exact=23/23
destroyed_predecessor_reappearances=0
production_mutation_errors=0
terminal_flag_unknowns=0
mutable_ship_queue_transition_gate_passed=True
```

Status:

```text
ordinary mutable ship membership:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Production second STANDARD occurrence:

```text
comparable_repeated_groups=2
production_second_occurrence_exact=2/2
second_standard_queue_gate_passed=True
```

Status:

```text
production occurrence-aware second STANDARD orientation:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## POST-MUTATION NEXT-PAIR DIFFERENTIAL — CLOSED

Pending runtime:

```text
docs/handoff/2026-09-18-combat-c5-post-mutation-next-pair-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_post_mutation_next_pair_audit.py
```

Test:

```text
tests/test_combat_host_post_mutation_next_pair_audit.py
```

The gate composes two existing independent pipelines:

1. owner-current T-1 candidate reconstruction from `combat_host_initial_standard_target_audit.py`;
2. deterministic Classic replay terminal state from `combat_ship_chain_audit.py`.

For exact-set comparable multi-VCR sites only:

```text
initial independently reconstructed pair graph
  -> production first STANDARD selection
  -> factual VCR N terminal replay only
  -> apply_ship_terminal_batch(...)
  -> active membership filter
  -> StandardQueueState occurrence history
  -> canonical next selector
  -> predicted next pair/sides
  -> compare with held-out factual VCR N+1
```

Factual VCR N+1 is not selector input.

Capture predecessors fail closed/exclude the continuation. Game `591478`, planet combat, non-exact-set sites, unresolved/pre-standard candidate sets and dynamic post-combat pair-decision recomputation remain outside this bounded gate.


## 2026-09-18 post-mutation next-pair runtime closure

Runtime source HEAD:

```text
c3cacd9b1f4dfc45595ee51c11b576f47d01a6aa
```

Durable runtime:

```text
docs/handoff/2026-09-18-combat-c5-post-mutation-next-pair-runtime.md
```

For both strict and conditional profiles:

```text
multi_vcr_exact_set_sites=23
site_status:exact=16
site_status:excluded=7
excluded:capture_predecessor=7
transitions_compared=22
next_vcr_exact=22
next_vcr_mismatch=0
transitions_with_inactive_filter=22
all_profiles_pass=True
```

Status:

```text
bounded post-mutation ordinary next-pair selection:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

All compared transitions exercised inactive-pair filtering. The only exact-set continuation hole is capture.

## CAPTURE CONTINUATION — CLOSED

Pending runtime:

```text
docs/handoff/2026-09-18-combat-c5-capture-continuation-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_capture_continuation_audit.py
```

The first pass is descriptive and does not modify production. It measures captured-ship race transfer, hull preservation, terminal-to-next-start combat state, next opponent identity and side orientation. Production capture remains fail-closed until the ordinary corpus result is reviewed.


## 2026-09-20 capture descriptive runtime and production promotion candidate

Descriptive runtime:

```text
docs/handoff/2026-09-20-combat-c5-capture-continuation-descriptive-runtime.md
```

Observed ordinary capture continuation:

```text
capture reappearances=23
hull preserved=23/23
owner/race transfer to captor=23/23
crew terminal0 -> next10=23/23
torpedoes exact=23/23
fighters exact=23/23
damage exact=22/23
raw shield carry exact=22/23
```

Official Planets.nu Combat Basics documents the 10-person prize crew. Official Nu/VGAP differences documentation places Federation shield recharge at the end of each battle. That order explains the only shield residual: a pre-capture Federation ship leaves combat at shield0, recovers to25, and appears in the next VCR under the captor race.

Production now has an explicit capture transfer path:

```python
ShipCaptureTransfer(...)
carry_captured_ship_to_next_engagement(...)
apply_ship_terminal_batch(..., capture_transfers_by_ship_id=...)
```

Capture remains fail-closed without explicit captor metadata.

Production order:

```text
terminal
 -> pre-capture Fed recovery
 -> prize crew10
 -> owner/race transfer
 -> new-owner race bonus flags
 -> prepare next engagement
```

Active gate remains the capture continuation diagnostic, now v2 and production-wired. Required result is exact owner/race/hull/shield/crew/ammunition state across all 23 rows, with no new damage residual beyond the isolated upstream replay row:

```text
621253/T17 ship84 VCR39->45 damage11->7
```

No capture-repair special case is encoded for that singleton.


## 2026-09-20 production capture runtime closure

Runtime:

```text
docs/handoff/2026-09-20-combat-c5-capture-production-runtime.md
```

User runtime source:

```text
52cd8f07f03afa7eabebf03c8b742859ab11dd9f
```

Production result:

```text
capture_reappearance_transitions=23

owner_id exact=23/23
race_id exact=23/23
hull_id exact=23/23
shield exact=23/23
crew exact=23/23
torpedoes exact=23/23
fighters exact=23/23
damage exact=22/23

known damage residual only:
621253/T17 ship84 VCR39->45 11->7

capture_transition_gate_passed=True
```

Status:

```text
bounded production capture state transition:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Production capture remains fail-closed without explicit `ShipCaptureTransfer`.

## POST-CAPTURE OPPONENT ATTRIBUTION — RESIDUAL OPEN

Pending runtime:

```text
docs/handoff/2026-09-20-combat-c5-post-capture-opponent-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_post_capture_opponent_audit.py
```

The production capture corpus contains exactly:

```text
15 immediate planet/base continuations
8 immediate third-ship continuations
```

This gate determines only whether the opposite side in the immediate next VCR belongs to:

```text
pre_capture_owner
captor
third_party
```

The factual next VCR is observation-only. Specific target selection, post-capture mission/PE/diplomacy and mixed ship/planet queue ordering remain separate future gates.


## 2026-09-20 post-capture opponent population result

User runtime source:

```text
d1c5be4318dbe58a93bab78659f4d79e5b359e0f
```

Population:

```text
capture_continuations=23
next_combat:planet=15
next_combat:ship=8

next_owner_relation:pre_capture_owner=22
next_owner_relation:third_party=1
next_owner_relation:captor=0

payload_conflicts=0
missing next VCR=0
projection unresolved=0
```

The attempted invariant "immediate next opponent is always the pre-capture owner" is false and is not promoted.

Sole residual:

```text
622476/T17 @ 1973,1734
ship7 owner5 -> captured by ship44 owner3
next VCR38: ship7 owner3 vs ship48 owner8
```

This is now the active focused gate:

```text
docs/handoff/2026-09-20-combat-c5-post-capture-third-party-residual-pending.md
tools/diagnostics/combat_host_post_capture_third_party_residual_audit.py
```

The diagnostic inventories the full site queue, T-1 orders/PE/FC/static priority for all participants, request directions against owners 3/5/8 and raw relation signatures. It specifically tests whether ship48 independently requests combat against post-capture owner3. If yes, the residual can be explained as ordinary third-party aggression against the newly transferred prize ship, without assuming captured ship7 retained old orders.


## 2026-09-20 post-capture opponent attribution — universal invariant rejected

Runtime:

```text
docs/handoff/2026-09-20-combat-c5-post-capture-opponent-runtime.md
```

Population:

```text
23 capture continuations
22 immediate opponents owned by pre-capture owner
1 immediate opponent owned by third party
0 immediate opponents owned by captor
15 planet/base continuations
8 ship continuations
```

Therefore "always pre-capture owner" is false and remains unpromoted.

The sole residual `622476/T17 ship7 -> ship48` is separately closed as an explanatory residual:

```text
docs/handoff/2026-09-20-combat-c5-post-capture-third-party-residual-runtime.md
```

T-1 ship48 has Kill! and independently requests combat against the captured ship's new owner3. VCR38 therefore does not require persistence of ship7's old PE/orders. Ship7's old PE also targets owner8, so this row cannot distinguish old-order persistence from pure defense.

## POST-CAPTURE INITIATOR POPULATION — CLOSED

Pending runtime:

```text
docs/handoff/2026-09-20-combat-c5-post-capture-initiator-population-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_post_capture_initiator_population_audit.py
```

For all 23 production-validated capture continuations:

- ship opponents are checked for independent T-1 Kill!/PE aggression against the new owner;
- planet/base opponents are checked for NUK/ATT attack codes;
- captured ship old T-1 orders are reported only as an alternative historical candidate and are not assumed to persist.

The resulting explanation distribution will decide whether observed continuations can be reproduced using ordinary attack/defense semantics alone or whether capture-generated target-list reconstruction is required immediately.


## 2026-09-20 post-capture initiator population — empirical closure pending v2 acceptance rerun

First runtime:

```text
docs/handoff/2026-09-20-combat-c5-post-capture-initiator-descriptive-runtime.md
```

Observed:

```text
capture continuations=23

independent opponent initiator=23/23
  ship Kill!/PE=8/8
  planet NUK/ATT=15/15

explanation:
  opponent_only=21
  both=2
  captured_old_orders_only=0
  neither=0

captured old T-1 orders:
  compatible=2
  incompatible=19
  unavailable=2
```

Therefore no observed post-capture continuation requires persistence of the prize ship's old mission/PE. The documented capture-generated target list remains a real Host mechanic, but its contents are not identifiable from this population because opponent-side aggression already explains every continuation.

The first diagnostic run reported `no_adapter_unresolved=False` only because two optional captured-ship old-order histories were unavailable. This was an acceptance-scope bug. v2 now treats those rows as informational and requires only opponent-side inputs to resolve.

Active rerun gate:

```text
tools/diagnostics/combat_host_post_capture_initiator_population_audit.py
schema v2
```

Required:

```text
no_required_adapter_unresolved=True
all_continuations_have_independent_opponent_attack=True
post_capture_initiator_gate_passed=True
```

After this rerun, do not invent captured-ship old-order persistence. Move to mixed ship/planet queue ordering, because 15/23 observed prize-ship continuations are planet/base combats.


## 2026-09-20 post-capture initiator v2 runtime closure

Runtime:

```text
docs/handoff/2026-09-20-combat-c5-post-capture-initiator-runtime.md
```

User runtime source:

```text
33145c99748642cc75a8f25b1bf819c1f7ba0445
```

Result:

```text
capture_continuations=23

independent opponent initiator=23/23
  ship Kill!/PE=8/8
  planet/base NUK/ATT=15/15

explanation:
  opponent_only=21
  both=2
  captured_old_orders_only=0
  neither=0

required_unresolved_total=0
optional_old_order_unresolved=2

post_capture_initiator_gate_passed=True
```

Status:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

No observed continuation requires persistence of captured old mission/PE.

## ACTIVE GATE — mixed ship / planet-base queue ordering

Pending handoff:

```text
docs/handoff/2026-09-20-combat-c5-mixed-ship-planet-queue-pending.md
```

This is now the main remaining C5 queue boundary.

Immediate questions:

- interleaving of ship-vs-ship and ship-vs-planet/base VCRs;
- ordering among multiple eligible attackers/defenders;
- interaction with ship Combat Priority;
- survivor/capture re-entry around planet/base combat;
- NUK/ATT planet-initiated battles;
- mixed LEFT/RIGHT semantics.

Keep capture-generated target-list contents, Advanced Cloak production, game 591478 and broad candidate-coverage expansion separate.


## 2026-09-20 workflow change — larger runtime batches

C5 runtime work should now prefer grouped batches over one-hypothesis-per-user-run.

Active batch:

```text
tools/run-combat-c5-mixed-queue-batch.sh
```

Primary new diagnostic:

```text
tools/diagnostics/combat_host_mixed_ship_planet_queue_batch_audit.py
```

The batch keeps running after individual failures, writes per-stage return codes, saves one complete log to `artifacts/combat-c5-mixed-queue-batch.log`, and emits separate JSON artifacts.

Current mixed-order batch tests population shape, S/P phase transitions, planet side orientation, NUK/ATT state, survivor/capture handoff into planet combat, repeated same-planet attacks and a naive STANDARD-priority ordering hypothesis in one execution.

Use focused follow-up diagnostics only after this broad batch identifies actual residuals.


## 2026-09-20 mixed queue batch v1 runtime

Runtime:

```text
docs/handoff/2026-09-20-combat-c5-mixed-queue-batch-runtime-v1.md
```

All six stages passed.

Strong ordinary invariants:

```text
mixed sites=391
ship block before planet block=391/391
P->S=0

planet RIGHT=435/435
planet LEFT=0
```

This aligns with documented Host sequencing:

```text
ship-vs-ship
-> repair/MKT
-> ship-vs-planet
```

Repeated planet attackers:

```text
36 groups
35 naive T-1 priority comparable
34 exact
1 mismatch
1 unresolved
```

The only mismatch is `511506/T48 planet131`, where the lower old T-1 priority ship480 is a post-capture entrant. Old T-1 priority must not be used as its capture-generated order.

Production now contains an explicit mixed phase state machine and an ordinary planet selector in `mixed_queue.py`; post-capture generated-order candidates fail closed.

The active large-batch runner now also measures the ship->planet repair/MKT state boundary before full mixed orchestration is promoted.


## 2026-09-20 mixed queue batch v2 closure

Runtime:

```text
docs/handoff/2026-09-20-combat-c5-mixed-queue-batch-runtime-v2.md
```

All seven batch stages passed.

Ordinary repeated planet order:

```text
27/27 production exact
```

Status:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Post-capture repeated planet groups remain fail-closed:

```text
9 groups
8 captured entrants after ordinary attackers
1 captured entrant interleaved before an ordinary attacker
```

Ship->planet interphase state:

```text
397 transitions
374 ordinary exact carry
8 ordinary damage decreases
15 defeated/captured predecessor reappearances

crew/torpedoes/fighters unchanged=382/382 ordinary survivors
```

The eight damage decreases follow the documented 5 supplies per 1% damage repair surface. Production support now exists in `combat/interphase.py`. T-1 supplies are not treated as guaranteed current interphase supplies because earlier Host repair steps can consume them.

Active v3 batch is now a residual sweep over Horwasp/initiator rows, all capture-containing repeated planet groups, supply-repair production differential and MKT candidates.


## 2026-09-20 mixed queue batch v3 closure

Runtime:

```text
docs/handoff/2026-09-20-combat-c5-mixed-queue-batch-runtime-v3.md
```

All seven stages passed.

Interphase supply repair is now closed in bounded production scope:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Runtime:

```text
397 ship->planet transitions
374 exact carry
8 positive damage repairs
15 defeated/captured predecessor reappearances

382/382 ordinary survivor rows preserve crew/torpedoes/fighters
8/8 observed repair rows preserve shields without recharge
0 hard supply-budget contradictions
interphase_supply_repair_gate_passed=True
```

MKT remains outside production; 36 MKT-candidate rows show no torpedo-count delta but T-1 resource state is not current interphase cargo.

Five mixed initiator residuals are now isolated to impossible same-owner VCR planet attribution shapes. V4 uses unique VCR race->player mapping plus T current planet owner as independent context rather than inventing same-owner combat.

Capture V4 hypothesis clears captured old Mission/PE aggression priority while preserving Friendly Code priority, then compares the resulting STANDARD order across every comparable capture-containing repeated planet group.

V4 also adds an all-planet engagement population sweep over the entire ordinary ship-vs-planet corpus.


## 2026-09-20 mixed queue batch v4 closure

Runtime:

```text
docs/handoff/2026-09-20-combat-c5-mixed-queue-batch-runtime-v4.md
```

All eight stages passed.

All ordinary ship-vs-planet population:

```text
2406 VCR rows
1981 ship-only initiator
86 planet-only initiator
337 both
2 unresolved
0 hard residuals
planet_engagement_population_gate_passed=True
```

Important correction: the prior five apparent same-owner residuals were a diagnostic interpretation error. The printed v3 `planet_owner_id` was T-1 planet owner. V4 explicitly shows factual VCR defender owner is foreign in 2406/2406 ordinary rows. No same-owner combat exception exists in this corpus.

The actual remaining production gap is earlier Host planet-ownership mutation before ship-vs-planet combat.

Capture-generated planet priority now has:

```text
8/8 comparable groups exact
0 mismatch
1 fail-closed missing-T-1 group
```

Production now preserves captured Friendly Code priority while clearing old Mission/Primary Enemy aggression for the generated planet-combat order. Eligibility remains independent upstream state.

Next batch adds full `T-1 -> VCR defender -> T` planet ownership timeline and reruns capture-containing groups through the production selector.


## 2026-09-21 mixed queue batch v5 closure

Runtime:

```text
docs/handoff/2026-09-21-combat-c5-mixed-queue-batch-runtime-v5.md
```

All nine stages passed.

Capture-generated planet priority is now production differential verified:

```text
production repeated planet order:
  35/35 exact comparable
capture-generated subset:
  8/8 exact comparable
  1 unresolved missing-T-1 row
  0 mismatch
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Planet ownership timeline narrowed the remaining mixed-queue production gap:

```text
2406 ordinary planet VCRs
2303 unique planet-turn combat timelines
59 unique precombat owner-change timelines
42 change from attacking ship's T-1 ownership to a different factual defender
17 third-party ownership changes
```

Factual VCR defender owner remains attribution/comparator evidence only. Production must reconstruct earlier Host planet ownership mutation before planet-combat candidate composition.

V6 inventories T-1 co-located future-defender ships and clans/order fields across all 59 changed timelines before any ground-combat production rule is introduced.


## 2026-09-21 mixed queue batch v6 closure

Runtime:
`docs/handoff/2026-09-21-combat-c5-mixed-queue-batch-runtime-v6.md`

All ten stages passed.

Production mixed ordering remains fully green in bounded scope:

```text
35/35 repeated planet groups exact comparable
8/8 capture-reset groups exact comparable
0 mismatch
```

The immediate mixed C5 gap has moved upstream into precombat planet ownership reconstruction.

V6 source inventory resolves 42 positive-owner reversal timelines:

```text
co-located future-defender ship=42/42
onboard clans>0=33/42
onboard clans=0=9/42
```

The nine zero-onboard-cargo rows cannot be treated as negative controls because the T-1 ship schema exposes directed cargo orders. Examples include `clans=0` with positive `transferclans` targeting the exact planet.

Next gate must use `transferclans/transfertargetid/transfertargettype`, then replay cargo-drop / ground-combat ownership effects in Ship-ID order.

Updated planning assessment:
`docs/handoff/2026-09-21-reverse-progress-assessment.md`
