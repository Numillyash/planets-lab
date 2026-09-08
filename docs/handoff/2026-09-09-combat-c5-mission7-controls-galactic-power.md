# C5 Host combat — mission-7 matched controls and Galactic Power gate — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains excluded from ordinary-mechanics tuning.

## User-operated matched-control runtime

The user updated local `/root/projects/planets-lab` to:

```text
b1335ea6032a356c12be13be2c4fdb8cbc46b011
```

and ran:

```text
tests/test_combat_host_mission7_matched_control_audit.py
tools/diagnostics/combat_host_mission7_matched_control_audit.py
```

The supplied complete console output reports:

```text
targeted tests: 4 passed
archives_considered: 11
payload_conflicts: 0
candidate_rows: 41
target_case_rows: 1
control_rows: 40
standard_relation:
  right_higher_priority: 40
  left_higher_priority:   1
interceptor_side:
  right: 22
  left:  19
exact_case2_shape_relation:
  right_higher_priority: 2
  left_higher_priority:  1
numeric_vs_symbolic_nonkill_relation:
  right_higher_priority: 6
  left_higher_priority:  1
no_t_extra_survivor_relation:
  right_higher_priority: 30
  left_higher_priority:   1
tests rc=0; audit rc=0
artifact dir: artifacts/combat-c5-mission7-controls-20260909-003724
```

Historical rows are `CORPUS_OBSERVED`; the targeted helper regressions are `TESTED`. No Intercept side mechanic is promoted by these counts.

## Matched-control conclusion — universal non-cloakable Intercept side rule rejected

The selected population was intentionally close to the remaining Case-2 order state:

- ordinary one-ship-VCR site;
- non-cloakable `mission=7` ship;
- Intercept target is the factual opponent;
- interceptor PE matches opponent owner;
- opponent has reciprocal PE;
- FCs are supported and nonmatching.

The result is decisive against changing standard side priority for this population:

```text
41 matched rows total
40 conform to canonical standard right-higher side assignment
 1 contradicts it
```

The sole contradiction is exactly the existing target:

```text
game 621896 / battle T28 / VCR67
LEFT  ship62 owner5 race8 hull70 Gorbie
      mission7 target38 PE2 FC001
RIGHT ship38 owner2 race2 hull23 T-Rex
      mission1 PE5 FCeqe damage24
```

The target remains unique even under tighter controls:

- exact `001` versus symbolic non-Kill order shape: `2 right_higher / 1 left_higher`, with the left-higher row again the target;
- broader numeric-versus-symbolic non-Kill: `6 right_higher / 1 left_higher`, again the target;
- no observed untracked T survivor at battle coordinate: `30 right_higher / 1 left_higher`, again the target.

Therefore:

- `mission=7` itself is not a forced-left or forced-right rule;
- non-cloakable targeted Intercept with matching PE is not a general pre-standard side phase in this population;
- FC `001` versus symbolic non-Kill does not explain the target;
- the current standard priority key must not be weakened.

Evidence: `CORPUS_OBSERVED` matched controls. This is a negative differential result, not a new mechanic.

## Causal mechanic discovered — Galactic Power

Primary Planets.nu documentation provides the missing race/hull-specific rule:

- Race Sheet / Evil Empire advantage table: `Galactic Power` — Gorbies always fight from the left-hand side;
- dedicated Galactic Power page: the effect applies to a **Gorbie Class Battlecarrier owned by the Evil Empire**;
- no special Mission or Friendly Code is required;
- the advantage is active in all new Standard games;
- it is disabled in Campaign by default and can be researched/enabled there.

Primary references:

```text
https://help.planets.nu/racesheet
https://help.planets.nu/adv-galactic-power
```

This exactly matches the otherwise unique Case-2 mechanical identity:

```text
owner race = 8 (Evil Empire)
hull       = 70 (Gorbie)
factual side = LEFT
```

The matched-control population makes the attribution especially strong: other structurally similar non-cloakable Intercept cases follow standard side priority, while the unique Gorbie row is the unique residual.

Evidence status at this checkpoint:

```text
Galactic Power rule text:                DOCUMENTED
Case2 race8 / hull70 / factual LEFT:      CORPUS_OBSERVED
matched-control uniqueness of Case2:      CORPUS_OBSERVED
causal attribution to Galactic Power:     DOCUMENTED + CORPUS_OBSERVED, pending explicit effective-advantage context / broader Gorbie differential
DIFF_VERIFIED promotion:                  not yet claimed
```

Do not encode `hull70 => left` globally. The documentation is owner- and advantage-specific.

## Canonical primitive added after the runtime

`src/planets_lab/rules/combat/order.py` now contains:

```text
EVIL_EMPIRE_RACE_ID = 8
GORBIE_HULL_ID = 70
galactic_power_forces_left(...)
```

The helper requires:

```text
owner_race_id
hull_id
galactic_power_enabled
```

Behavior:

- known non-Evil-Empire owner or non-Gorbie hull -> `False`;
- Evil Empire Gorbie + known disabled advantage -> `False`;
- Evil Empire Gorbie + known enabled advantage -> `True`;
- Evil Empire Gorbie + unknown effective advantage state -> `None` / fail closed.

This is a `DOCUMENTED` primitive. Its newly-added tests and the new corpus diagnostic have not yet been user-runtime-validated at the time of this handoff.

## Next bounded gate — Galactic Power corpus boundary

Prepared diagnostic:

```text
tools/diagnostics/combat_host_galactic_power_audit.py
tests/test_combat_host_galactic_power_audit.py
```

It scans ordinary ship-vs-ship VCRs containing hull70 and reports separately:

1. Evil-Empire-owned Gorbie appearances and factual side;
2. non-Evil-Empire/captured Gorbie appearances as negative controls;
3. dual Evil-Empire Gorbie battles as an explicit ambiguous/fail-closed shape;
4. canonical standard relation where T-1 order state is aligned;
5. cases where forcing the Gorbie left is actually required to override the standard relation;
6. bounded allowlisted game metadata (`type`, `gametype`, `scenarioid`, `campaignmode`, `isacademy`, `isprivate`) when present;
7. owner `activeadvantages` values when that field is exposed in prepared player payloads;
8. the exact `621896/T28/VCR67` target row.

The audit does **not** invent Campaign enablement. If the archive does not expose effective Galactic Power state, that remains unknown even if the factual side is consistent with the documented rule.

## Case 1 remains separate

`511506/T19/VCR13` remains a larger physical-stack/dynamic-eligibility problem. Galactic Power does not explain it. Do not put it back into clean pairwise standard-side validation.

## After Galactic Power boundary

If ordinary Evil-Empire Gorbies are consistently left and no contradictory enabled-state row exists, integrate the forced-left override into the Host side-assignment layer with explicit advantage state and close Case 2.

Then proceed to:

1. dynamic multi-ship opponent selection / cloak eligibility for Case 1;
2. matching-FC / Harmonic Weapon Modulation boundaries;
3. PIA/C&I pair selection in the dynamic queue;
4. capture/reinsertion and ownership changes;
5. between-phase repair and ship-vs-planet ordering;
6. game `591478` separately.
