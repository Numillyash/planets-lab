# C5 Host combat phase — current handoff — 2026-09-08

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

## Objective

Reconstruct the NuHost combat phase that generates VCR engagements, order and left/right sides. Facts, inferred semantics and simulator rules remain separate; unknown branches fail closed.

## Repository alignment

At the transfer checkpoint:

```text
main:                       030f7489fd94a2af8e60a7da710c9b28b207f152
C5 branch before docs-only transfer commit:
                            8b8f0b43b9d45da4c5b35796e2fa388b6e17fcd9
merge base with current main:
                            89b5b0f1c06869a0d03d04cba76caa78bc4b10ce
```

At that historical transfer checkpoint, the C5 branch was behind `main` by three commits. The delta is movement/fuel-only (`tools/diagnostics/partial_move_fuel_cost_case_audit.py` and `docs/handoff/2026-09-08-intel-fuel-chat-handoff.md`) and has no combat overlap. Do not infer the actual current HEAD from these recorded SHAs; inspect GitHub refs first in a new session. Synchronize deliberately when useful rather than assuming the branch is already current.

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

Runtime on HEAD `34bad43`:

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
CORPUS_OBSERVED + DIFF_VERIFIED 7/7 right
```

One ordinary C&I order signature had `targets_other_ship`; preserve it for later multi-ship target selection.

Special game 591478 remains strongly non-ordinary and is not used to tune ordinary standard rules.

### Priority Intercept Attack — observed ordinary subset CLOSED

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

## Current gate: two non-PIA mission7 residuals inspected; causality OPEN

### Runtime provenance

User-operated WSL/Docker run, source `d608c7d057ddcb38ad4317a879e897b435dead1e`.
Work did not execute the historical archive audit itself. The supplied complete console output reports:

```text
targeted residual-enrichment tests: 3 passed
archives: 12
payload_conflicts: 0
ordinary_residuals: 2
game_591478_residuals: 87
all_residuals: 89
audit rc=0; tee rc=0
```

Local artifacts (not uploaded to GitHub):

```text
artifacts/combat-c5-non-pia-mWCafN7v/source.txt
artifacts/combat-c5-non-pia-mWCafN7v/tests.log
artifacts/combat-c5-non-pia-mWCafN7v/audit.log
artifacts/combat-c5-non-pia-mWCafN7v/report.json
```

Evidence: supplied historical rows are `CORPUS_OBSERVED`; the three diagnostic helper tests are `TESTED`. Selection is reproduced, but neither residual has a causally explained or newly `DIFF_VERIFIED` rule.

### Case 1: 511506 / battle T19 / VCR13 / (2565,1729)

Owner-visible T18 records:

```text
LEFT  ship80 / owner6 / race6 / hull56 Firecloud
      can_cloak=false; mission=3; target1=0; target2=0
      enemy=5; FC=027; iscloaked=false; fuel=150; damage=0
      target_owner=null; pia_class=not_intercept
RIGHT ship89 / owner5 / race5 / hull46 Meteor
      can_cloak=true; mission=7; target1=80; target2=0
      enemy=0; FC=2eC; iscloaked=true; fuel=26; damage=0
      target_owner=6; pia_class=nonqualifying_intercept
```

Current canonical keys:

```text
left  (0,27,80)
right (4,89,0)
```

Firecloud requests hostility by both Kill and PE; Meteor does not request hostility by Kill/PE. Meteor targets the factual opponent and has a cloak device, but lacks the documented matching PE requirement for the current static PIA signature. Neither side is mission20/Bird C&I. FCs are supported and unequal.

`iscloaked=true` belongs to T18; it is not proof of an active cloak in the combat phase after the Intercept order executes.

Open hypotheses, all `INFERRED`, not promoted:
- A leading-integer FC parser would read `2eC` as 2, placing Meteor ahead of 027. This contradicts the documented symbolic-letter FC classification and needs an independent ordinary control population before any parser change.
- A defensive/pre-standard Intercept interaction may differ from the current narrow static signature. The PIA documentation mentions the target's reciprocal combat, but also explicitly requires the interceptor's matching PE; this text does not prove PE=0 eligibility.
- Phase-current state mutation or source-state alignment remains possible.

The subsequent T18 diplomacy audit found symmetric `(1,1,0)` values in both directions (see below). Asymmetric T-1 diplomacy is rejected. Independently, suppressing Firecloud's initiation alone would not explain Meteor initiating this fight under the observed Kill/PE orders: Meteor has neither.

### Case 2: 621896 / battle T28 / VCR67 / (2247,1837)

Owner-visible T27 records:

```text
LEFT  ship62 / owner5 / race8 / hull70 Gorbie
      can_cloak=false; mission=7; target1=38; target2=0
      enemy=2; FC=001; iscloaked=false; fuel=1760; damage=0
      target_owner=2; pia_class=nonqualifying_intercept
RIGHT ship38 / owner2 / race2 / hull23 T-Rex
      can_cloak=false; mission=1; target1=0; target2=0
      enemy=5; FC=eqe; iscloaked=false; fuel=490; damage=24
      target_owner=null; pia_class=not_intercept
```

Current canonical keys:

```text
left  (0,1,62)
right (3,38,0)
```

Both ships request hostility by PE against the factual opponent's owner slot. Owner5 is race8; do not substitute race ID for owner slot in PE comparisons. Neither hull can cloak, so the documented PIA mechanism cannot explain this row. There is no matching FC, signed FC or numeric-shape ambiguity here. T-Rex's T27 damage=24 is not evidence of a side-assignment exception.

The asymmetric T-1 diplomacy hypothesis was tested by the subsequent raw audit and rejected: both directed T27 rows contain `(relationto, relationfrom, conflictlevel)=(1,1,0)`. This does not establish a replacement side-assignment rule or rule out an independently evidenced phase-current state mutation.

### Combined interpretation and next runtime gate

Both supplied rows have been inspected. They do not support a universal Intercept-left or Intercept-right rule: the interceptor is on opposite sides in the two cases. Canonical priority arithmetic was independently executed in Work from the unchanged GitHub `order.py` and reproduced both left-higher keys; this is a small implementation check, not historical Host validation.

Combat rules remain unchanged and unknown branches remain fail-closed. The 87 special-game rows do not tune ordinary mechanics.

### Directed T-1 diplomacy gate — COMPLETE, asymmetry rejected

The user ran the existing `tools/diagnostics/combat_host_diplomacy_residual_audit.py` in WSL/Docker for both exact pairs and supplied the complete outputs. Both commands completed successfully. Work did not run these archives itself. The excerpt does not print the run HEAD; do not invent exact runtime SHA provenance. The preceding verified C5 source was `5be8993c57aa0eddc811e13c8231fe724af89612`; the command also writes `source.txt` locally.

```text
511506 / battle T19 / pre-combat archive T18:
  turn_members=11; perspectives_with_relations=11; target_pair_rows=2
  perspective5: id50, playerid5, playertoid6, relationto1, relationfrom1, conflictlevel0
  perspective6: id60, playerid6, playertoid5, relationto1, relationfrom1, conflictlevel0
  directed_unique_values: 6->5 [[1,1,0]], 5->6 [[1,1,0]]
  mirror_consistent=true
  relationto inventory:   0:40, 1:79, 3:2
  relationfrom inventory: 0:40, 1:79, 3:2
  conflictlevel inventory: 0:121

621896 / battle T28 / pre-combat archive T27:
  turn_members=8; perspectives_with_relations=8; target_pair_rows=2
  perspective2: id13, playerid2, playertoid5, relationto1, relationfrom1, conflictlevel0
  perspective5: id34, playerid5, playertoid2, relationto1, relationfrom1, conflictlevel0
  directed_unique_values: 5->2 [[1,1,0]], 2->5 [[1,1,0]]
  mirror_consistent=true
  relationto inventory:   0:25, 1:36, 3:3
  relationfrom inventory: 0:25, 1:36, 3:3
  conflictlevel inventory: 0:64
```

For both games every member's active player ID matches its filename player, and embedded turn matches the selected archive turn. Only the two involved owners' perspectives contain the target relation rows; other perspectives return no target pair rows. The common relation-key shape is `color, conflictlevel, id, playerid, playertoid, relationfrom, relationto` (121 and 64 total rows respectively).

Evidence: `CORPUS_OBSERVED` symmetric raw relations. This rejects the proposed asymmetric T-1 diplomacy explanation for both residuals without needing to promote numeric relation-level semantics. It does not prove that every possible diplomacy/state mutation throughout Host is absent.

Local WSL repository: `/root/projects/planets-lab`.
Local artifacts remain outside Git:

```text
artifacts/combat-c5-diplomacy-JdlpAJOZ/source.txt
artifacts/combat-c5-diplomacy-JdlpAJOZ/game-511506.json
artifacts/combat-c5-diplomacy-JdlpAJOZ/game-511506.log
artifacts/combat-c5-diplomacy-JdlpAJOZ/game-621896.json
artifacts/combat-c5-diplomacy-JdlpAJOZ/game-621896.log
```

### Immediate next gate — resume in the project chat

The user requested ending Work execution and returning to the project chat because of Work limits. Preserve this checkpoint; do not repeat completed residual-enrichment or diplomacy runs.

Prepare one narrow privacy-safe source-context diagnostic for the two cases only:
1. inspect both ships' owner-visible records around battle T (`T-2, T-1, T`), keeping archive turn, embedded turn, infoturn/freshness and perspective provenance distinct;
2. extract allowlisted mechanical fields from the factual VCR, and check all same-turn VCR appearances of those ship IDs, including different sites, before asserting isolation or excluding capture/reinsertion;
3. compare FC/mission/PE, hull/owner, position, cloak, fuel, damage, supplies and combat equipment/ammunition where actually available; absent facts remain unknown;
4. distinguish snapshot state from combat-phase state and a source-alignment issue from a new Host mechanic.

This source-context diagnostic was proposed but **not written, committed or run** in Work. Choose and verify its actual filename when implementing; there is no ready new script to invoke. Existing enrichment and diplomacy tools remain unchanged.

The `2eC -> 2` leading-integer-FC idea remains `INFERRED` only. It cannot explain the separate Gorbie/T-Rex row. Any future parser promotion needs independent ordinary controls and regression/differential evidence, not fitting this single event. Defensive/pre-standard Intercept interaction is likewise unproven. Unknown branches fail closed; game `591478` stays excluded from ordinary tuning.

After causal inspection of these cases, resume matching-FC/Harmonic Weapon Modulation boundaries and the remaining C5 queue gates listed below. No combat-rule edit or new `DIFF_VERIFIED` claim was made from these results.

### Source alignment at return from Work

Fresh GitHub inspection before this documentation commit:

```text
main: b3cc67dcee669ce84b8ff14a3237a0e69ab10707
C5:   5be8993c57aa0eddc811e13c8231fe724af89612
```

The commit containing this update is newer than the recorded C5 SHA. Inspect actual refs when resuming. No merge, rebase or synchronization with main was performed; PR #28 remains draft. Earlier divergence counts in this document are historical checkpoints.

### Primary documentation checked

- [Order of Battle](https://help.planets.nu/battle-order): numeric/symbolic priority, directed Safe Passage suppression, and dynamic initiation.
- [Priority Intercept Attack](https://help.planets.nu/cloak-intercept): installed cloak, matching PE and reciprocal target-combat wording.
- [Intercept](https://help.planets.nu/mis-intercept): movement phase context; Intercept itself is not blanket combat priority.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinctions. PR #28 remains draft.

## After the two residuals

1. resolve exact matching-FC combat exceptions / Harmonic Weapon Modulation boundaries;
2. build dynamic multi-ship opponent selection;
3. incorporate PIA/C&I pair selection into the dynamic queue;
4. handle capture/reinsertion and ownership changes;
5. integrate between-phase repair and ship-vs-planet ordering;
6. keep game 591478 sequence semantics separate.

PR #28 remains draft until ordering/eligibility semantics are sufficiently understood.
