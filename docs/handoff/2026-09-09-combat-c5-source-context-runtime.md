# C5 Host combat — source-context runtime and physical-stack next gate — 2026-09-09

GitHub is the source of truth. This handoff records the user-operated WSL/Docker runtime of the targeted source-context audit and the next bounded diagnostic. PR #28 remains draft. Game `591478` remains excluded from ordinary-mechanics tuning.

## Runtime provenance

The user updated local `/root/projects/planets-lab` from `agent/combat-c5-host-phase` and ran:

```text
tests/test_combat_host_residual_source_context_audit.py
 tools/diagnostics/combat_host_residual_source_context_audit.py
```

The supplied output reports:

```text
source-context targeted tests: 5 passed (tests rc=0)
audit rc=0
cases=2
target_vcrs_found=2
payload_conflicts=0
artifact dir: artifacts/combat-c5-source-context-20260909-001211
```

The pasted excerpt does not include the `source.txt` line. The test harness fix required commit `fa9fb2d23054ddaa7d965c0a0fd39066f0d799de`, and that is the current GitHub C5 HEAD at this checkpoint, but do not fabricate a stronger runtime-SHA claim than the supplied output itself contains.

Evidence from the historical rows is `CORPUS_OBSERVED`; helper regressions are `TESTED`. No combat mechanic is promoted to `DIFF_VERIFIED` by this audit.

## Source-context result — gate COMPLETE

### Case 1 — 511506 / battle T19 / VCR13 / ships 80,89

Factual VCR context:

```text
unique VCRs on battle turn: 1
payload conflicts: 0
target VCR found: true
target pair exact: true
relevant VCRs containing ship80/89: 1
relevant locations: 1
battle location: (2565,1729)
```

Owner-current source alignment:

```text
ship80 Firecloud:
  T-2 owner-current: yes
  T-1 owner-current: yes
  T owner-current: no

ship89 Meteor:
  T-2 owner-current: yes
  T-1 owner-current: yes
  T owner-current: yes
```

T-1 reproduces the previously inspected orders exactly:

```text
ship80: mission=3, PE=5, FC=027, fuel=150, damage=0
ship89: mission=7, target=80, PE=0, FC=2eC, fuel=26, damage=0, cloaked=true
```

The Meteor is the only tracked survivor visible at T. Its T record is clearly post-movement/post-combat state rather than a usable pre-combat order snapshot:

```text
position:     (2471,1615) -> (2565,1729)
mission:      7 -> 8
mission1target: 80 -> 0
iscloaked:    true -> false
fuel:         26 -> 17
ammo:         10 -> 2
```

Its factual VCR starts with 10 torpedoes and zero damage; therefore the T ammo=2 value is after battle expenditure. T cannot replace T-1 for side assignment.

No other same-turn VCR appearance of either tracked ship exists. Same-turn queue/capture/reinsertion context is therefore rejected for this row at the VCR level.

### Case 2 — 621896 / battle T28 / VCR67 / ships 62,38

Factual VCR context:

```text
unique VCRs on battle turn: 8
payload conflicts: 0
target VCR found: true
target pair exact: true
relevant VCRs containing ship62/38: 1
relevant locations: 1
battle location: (2247,1837)
```

Owner-current source alignment:

```text
ship62 Gorbie:
  T-2 owner-current: yes
  T-1 owner-current: yes
  T owner-current: yes

ship38 T-Rex:
  T-2 owner-current: yes
  T-1 owner-current: yes
  T owner-current: no
```

T-1 again reproduces the previously inspected orders exactly:

```text
ship62: mission=7, target=38, PE=2, FC=001, fuel=1760, damage=0
ship38: mission=1, target=0, PE=5, FC=eqe, fuel=490, damage=24
```

The Gorbie is the only tracked survivor visible at T. Its T record is post-combat state:

```text
position:       (2264,1854) -> (2247,1837)
mission:        7 -> 0
mission1target: 38 -> 0
fighters/ammo:  105 -> 82
PE:             2 -> 2
FC:             001 -> 001
fuel:           1760 -> 1760
```

The factual VCR begins with 105 fighters, so T ammo=82 is after combat expenditure. Again T is not a valid pre-combat priority snapshot.

The T-Rex's damage=24 already exists at T-1. It arose between T-2 and T-1 and is not evidence of a same-T28 prior VCR. Neither tracked ship appears in any other T28 VCR.

## Combined conclusion

The source-state alignment hypothesis is rejected for both residuals in the narrow sense tested:

- exactly one current owner-visible T-1 record exists for every tracked ship;
- owner/hull/orders/FC/PE/fuel/damage are coherent with the factual VCR identity;
- the factual target VCR exists with the expected pair;
- no VCR payload conflicts exist;
- neither tracked ship appears in another VCR on the same battle turn;
- T survivor state demonstrates that T is post-combat and therefore cannot be substituted for T-1.

This strengthens T-1 as the correct pre-combat order source for these rows. It does **not** explain their left/right side assignment.

The two residuals remain genuine bounded contradictions to the current **classification** as ordinary standard combat. Do not weaken the documented standard priority model: the primary Order of Battle documentation states that after Priority Intercept, standard priority has no other tie/order factors. In particular, case 2 retains FC `001` and PE `2` in the survivor's T state, so a simple mission-reset explanation does not remove its numeric priority.

The leading-integer `2eC -> 2` hypothesis remains `INFERRED` and case-specific; it cannot explain case 2 and must not change the parser.

## Important remaining ambiguity: one VCR is not necessarily a two-ship physical stack

The previous isolated audits define isolation by factual VCR queue size. A site with one VCR can still contain additional ships that never enter a VCR. Such noncombatant stack members can matter to dynamic target selection, matching-FC skipping, diplomacy/eligibility, or other pre-standard context.

Therefore the next bounded gate is to test physical stack context before calling these rows unexplained standard-order exceptions.

Prepared diagnostic:

```text
tools/diagnostics/combat_host_residual_physical_stack_audit.py
tests/test_combat_host_residual_physical_stack_audit.py
```

It uses owner-current prepared records only and emits the same mechanical allowlist as the source-context audit. For each residual it reports:

1. all owner-current T survivors at the factual battle coordinate;
2. whether any such survivor is an untracked third ship;
3. T-1 records for those T survivors;
4. bounded T-1 context candidates that are tracked ships, already at the battle coordinate, waypoint to it, intercept a tracked ship, or start co-located with a tracked ship;
5. unresolved owner-current record counts, fail-closed;
6. factual VCR IDs at the exact site.

Interpretation boundary: T rows are post-combat/end-of-turn. An extra untracked T survivor at the battle coordinate is strong evidence that the one-VCR site was a larger physical stack. No extra T survivor does not exclude a ship removed by an earlier non-VCR Host phase such as a pre-combat special event.

No L1/L2 rebuild is required. No combat rule, FC parser or PIA eligibility code is changed.

## Evidence status

```text
T-1 owner-current alignment for the two rows: CORPUS_OBSERVED
same-turn tracked VCR isolation:             CORPUS_OBSERVED
T survivor post-combat state deltas:         CORPUS_OBSERVED
source-context helper tests:                 TESTED
causal explanation of residual side order:  OPEN / INFERRED hypotheses only
new combat mechanics:                        none
DIFF_VERIFIED promotions:                    none
```

## After physical-stack gate

If an untracked co-located ship is found, reconstruct that site's dynamic eligibility/target list before touching standard side priority.

If both sites are physically two-ship after bounded checks, proceed to matched ordinary controls for the remaining suppressor/pre-standard hypotheses. Only after those are exhausted should the workstream move on to matching-Friendly-Code / Harmonic Weapon Modulation boundaries.
