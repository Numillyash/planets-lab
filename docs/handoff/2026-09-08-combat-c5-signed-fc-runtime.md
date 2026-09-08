# C5 signed FC / diplomacy / mission-20 checkpoint — 2026-09-08

GitHub is the source of truth. Read together with:

- `docs/handoff/2026-09-08-combat-c5-host-phase-current.md`

## Signed numeric Friendly Code runtime

The exact-three-character signed FC hypothesis was tested on the conservative ordinary isolated ship-vs-ship population.

Hypothesis:

```text
exactly three-character Friendly Codes matching [+/-][0-9][0-9]
are parsed as signed numeric combat-priority values
```

Runtime:

```text
baseline comparable: 420
baseline right_higher_priority: 417
baseline left_higher_priority:    3

signed comparable: 420
signed right_higher_priority: 419
signed left_higher_priority:    1
```

No new ordinary residuals appeared. The prior `-54` and `-52` residuals disappeared exactly as predicted.

Evidence:

```text
signed exact-three-character FC parsing:
CORPUS_OBSERVED + DIFF_VERIFIED
NOT DOCUMENTED
```

Do not broaden this to arbitrary signed-string lengths without evidence.

## Only remaining ordinary isolated standard-side residual

```text
game=621253
battle turn=10
VCR=8

left:
  ship=50
  hull=37
  owner=4
  mission=0
  enemy=3
  fc='wxd'
  standard priority=[3,50,0]

right:
  ship=57
  hull=29
  owner=3
  mission=20
  enemy=4
  fc='osq'
  standard priority=[3,57,0]
```

The standard key would put lower-ID ship 50 on the right, but factual VCR puts ship 57 on the right.

Gorbie forced-left was tested and rejected; neither side is hull 70.

## Diplomacy / Safe Passage gate — rejected for this residual

Tool:

```text
tools/diagnostics/combat_host_diplomacy_residual_audit.py
```

Pre-combat state is archive turn 9. Raw Relations Object rows for owners 4 and 3:

```text
4->3: relationto=1, relationfrom=0, conflictlevel=0
3->4: relationto=1, relationfrom=1, conflictlevel=0
```

Whole-turn inventory:

```text
relationto:    0:55, 1:24, 3:2
relationfrom:  0:64, 1:14, 2:1, 3:2
conflictlevel: 0:81
```

The target pair has no relation level 2 or higher. Current Nu client conventions identify level 2 as Safe Passage, 3 as Share Intel, and 4 as Full Alliance. Therefore Safe Passage does not explain this VCR residual.

`mirror_consistent=False` also shows that `relationto` / `relationfrom` must not be naively interpreted as duplicated directed graph edges across perspective rows. Numeric relation semantics and perspective semantics remain a separate future diplomacy task.

## Current gate: mission 20 / Cloak and Intercept signature

The remaining residual is notable because the right-side Dark Wing has `mission=20`, a rare mission (97 owner-visible records in the prior inventory).

Official Planets.nu documentation says Birdmen `Cloak and Intercept` can intercept while cloaked and, when Primary Enemy matches the intercept target's faction, fight that target before regular combat. This could explain why ship 57 is on the right despite losing the ordinary standard priority key.

Do not promote the numeric mapping from one residual.

Current diagnostic:

```text
tools/diagnostics/combat_host_mission20_cloak_intercept_audit.py
tests/test_combat_host_mission20_cloak_intercept_audit.py
```

It inventories every owner-visible `mission=20` record across the 12 archives, separately for ordinary corpus and game 591478, including:

- owner race;
- hull;
- `mission1target` presence;
- target owner resolution;
- whether target is another owner's ship;
- whether `enemy == target_owner`;
- `iscloaked` when present.

It also highlights exactly:

```text
game 621253 / archive turn 9 / ship 57
```

and tests whether its `mission1target == 50`.

The diagnostic itself does NOT rename mission 20. Promotion requires corpus evidence that the mission-20 population has the documented Cloak-and-Intercept signature. If the population is mixed or target ownership is insufficiently resolved, keep mission 20 numeric and treat the single residual as unresolved.

## Immediate next actions

1. Run the mission-20 population diagnostic.
2. If ship57 targets ship50 and ordinary mission20 strongly matches Bird/C&I signature, promote the numeric mapping with explicit evidence labels.
3. Re-run/extend the isolated side-order differential with C&I excluded or modeled as a pre-standard combat phase; ordinary standard side assignment should then be checked for 420/420.
4. Continue with normal Priority Intercept (`mission=7`) qualification and reverse-ID ordering.
5. Then move to matching-FC exceptions and multi-ship dynamic opponent selection.

Game `591478` remains a separate special/campaign/Horwasp bucket and must not be used to tune ordinary rules.

PR #28 remains draft.