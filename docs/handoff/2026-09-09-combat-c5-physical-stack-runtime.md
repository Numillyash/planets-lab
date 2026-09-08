# C5 Host combat — physical-stack runtime and matched-control gate — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains excluded from ordinary-mechanics tuning. This handoff records the user-operated WSL/Docker physical-stack runtime on C5 HEAD `74f1d49c978a4cdd4c7222f92ff393bb9b397fb2` and the next bounded diagnostic.

## Runtime provenance

The supplied console output reports:

```text
source: 74f1d49c978a4cdd4c7222f92ff393bb9b397fb2
targeted tests: .......... [100%]
physical-stack audit rc=0
payload_conflicts=0
cases=2
cases_with_untracked_t_survivor=1
artifact dir: artifacts/combat-c5-physical-stack-20260909-002317
```

Historical rows are `CORPUS_OBSERVED`; the targeted helper regressions are `TESTED`. No combat rule, FC parser or PIA eligibility rule is promoted by this gate.

## Gate result — one-VCR isolation was not physical isolation

The older mission-7 residual audit defined an isolated site by a one-entry factual ship-combat VCR queue. The physical-stack audit proves that this is not equivalent to a two-ship physical stack.

### Case 1 — 511506 / T19 / VCR13 / Firecloud80 vs Meteor89

Factual battle coordinate: `(2565,1729)`.

```text
site VCRs: 1 ([13])
T owner-current survivors at coordinate: 4
untracked T survivors at coordinate: 3
T-1 context candidates: 5
untracked T-1 context candidates: 3
unresolved owner records: 0 at T-1, 0 at T
```

T survivors at the factual battle coordinate:

```text
ship29  owner5 hull46 Meteor  — untracked
ship73  owner6 hull17          — untracked
ship89  owner5 hull46 Meteor  — tracked factual combatant
ship102 owner5 hull46 Meteor  — untracked
```

Relevant T-1 context:

- ship80 Firecloud is already at the battle coordinate with `mission=3`, `PE=5`, `FC=027`;
- ship89 Meteor starts at `(2471,1615)`, `mission=7`, target ship80, `PE=0`, `FC=2eC`, waypointing to the battle coordinate;
- ship29 Meteor starts at the same `(2471,1615)` point, is cloaked in the T-1 snapshot, has `PE=0`, `FC=ypg`, and waypoints to the battle coordinate;
- ship102 Meteor starts at the same point and is cloaked in the T-1 snapshot, `PE=0`, `FC=roo`; its waypoint is nearby rather than exactly the factual battle coordinate, but it survives at that coordinate on T;
- ship73 owner6 hull17 is already at the battle coordinate and survives there without appearing in the VCR.

Therefore Case 1 must no longer be used as a clean two-ship control for standard side-priority validation. It belongs to the later dynamic physical-stack / eligibility / target-selection reconstruction. The factual side order itself remains unexplained; this gate does not infer why Meteor89 rather than another owner5 ship was selected or why it is on the right.

A plausible future line is that movement/intercept/cloak state makes only a subset of the owner5 stack combat-eligible or visible, but this remains `INFERRED`. T-1 `iscloaked=true` is not sufficient to establish combat-phase cloak state.

### Case 2 — 621896 / T28 / VCR67 / Gorbie62 vs T-Rex38

Factual battle coordinate: `(2247,1837)`.

```text
site VCRs: 1 ([67])
T owner-current survivors at coordinate: 1
untracked T survivors at coordinate: 0
T-1 context candidates: 3
untracked T-1 context candidates: 1
unresolved owner records: 0 at T-1, 0 at T
```

The only T survivor at the coordinate is tracked Gorbie62. T-1 candidates are:

```text
ship62 owner5 hull70 Gorbie: mission7 target38 PE2 FC001
ship38 owner2 hull23 T-Rex: mission1 PE5 FCeqe, waypoint to battle coordinate
ship15 owner5 hull75: shares Gorbie's T-1 origin but does not waypoint to the battle coordinate
```

No untracked survivor demonstrates a larger physical combat stack at the battle coordinate. This is not mathematical proof that no third ship existed earlier in Host, but it leaves Case 2 as the strongest ordinary physically-two-ship-like residual.

The tempting Evil Empire Intercept Interference explanation is rejected at the currently observed T-1 context: official Planets.nu Race Sheet identifies hull75 as **Super Star Frigate**, while Intercept Interference is assigned to Super Star Cruiser / Super Star Cruiser II. Ship15 therefore is not an observed Intercept Interference source. Primary references:

- `https://help.planets.nu/RaceSheetPlus`
- `https://help.planets.nu/abil-intercept-interference`

Do not infer anything from owner5 race8 alone; the protecting hull/advantage context matters.

## Consequence for the former 2-row residual bucket

Keep the historical audit count intact as a statement about its old one-VCR selector:

```text
supported nonmatching-FC mission7 non-PIA one-VCR rows:
  right_higher_priority: 180
  left_higher_priority:    2
```

But do not describe both left-higher rows as clean pairwise-standard residuals anymore:

- Case 1 is now `CORPUS_OBSERVED` stacked physical context and is removed from clean pairwise interpretation;
- Case 2 remains causally open and is the only strong clean-ish row after this gate.

No standard-priority rule is weakened. No `DIFF_VERIFIED` promotion is made.

## Next bounded gate — ordinary matched controls for Case 2

Prepared diagnostic:

```text
tools/diagnostics/combat_host_mission7_matched_control_audit.py
tests/test_combat_host_mission7_matched_control_audit.py
```

It scans ordinary one-ship-VCR sites only and selects a structural control population where:

1. a factual combatant has mission 7;
2. that ship is non-cloakable, so documented Priority Intercept cannot apply;
3. mission1target is the factual opponent;
4. the interceptor's Primary Enemy matches the factual opponent owner;
5. the opponent has reciprocal Primary Enemy back to the interceptor owner;
6. Friendly Codes are supported and nonmatching.

It then reports:

- factual interceptor side;
- canonical standard left/right relation;
- interceptor race/hull population;
- exact Case-2 order shape: interceptor `FC=001`, opponent symbolic FC, opponent non-Kill mission;
- broader numeric-vs-symbolic/non-Kill controls;
- T untracked-survivor counts as a bounded physical-stack cleanliness signal.

The T cleanliness field is explicitly not proof that no third ship existed before combat. The diagnostic is population evidence only and must not directly create a new Intercept side rule.

## Evidence status

```text
Case1 larger physical stack:                     CORPUS_OBSERVED
Case2 no observed untracked T survivor:           CORPUS_OBSERVED
one-VCR != physical-two-ship assumption:          rejected by CORPUS_OBSERVED counterexample
physical-stack helper regressions:                TESTED
Case1 dynamic target/eligibility explanation:     OPEN / INFERRED
Case2 side-order explanation:                     OPEN
new combat mechanics:                             none
DIFF_VERIFIED promotions:                         none
```

## After the matched-control gate

- If Case-2-like controls consistently reproduce standard right-higher ordering and Case 2 remains unique, inspect phase-specific/special context for that exact game/turn rather than changing the universal standard key.
- If a reproducible non-cloakable targeted-Intercept population systematically places the interceptor or target on a special side, isolate and test that rule before implementation.
- Case 1 moves to dynamic multi-ship opponent selection / cloak eligibility work.
- Then resume matching-FC / Harmonic Weapon Modulation boundaries and the remaining C5 queue gates.
