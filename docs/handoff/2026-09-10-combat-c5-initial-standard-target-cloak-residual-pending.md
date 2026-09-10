# C5 Host combat — initial STANDARD target cloak residual pending

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

Dependency runtime:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-fuel-runtime.md
```

The post-movement zero-fuel hypothesis was rejected for both broad residuals. Do not alter target ordering from those rows.

## Residuals

```text
360690/T83:
  active ship 264
  reconstructed extra target 98
  factual target 190

511506/T94:
  active ship 496
  reconstructed extra target 202
  factual target 332
```

Both extra targets have raw mission `9`.

## Documented clue

Planets.nu documents that Bird ships using `Super Spy` attempt to cloak if their hull can cloak. Cloaked ships are protected from enemy attack, while a cloaked ship may still attack a Primary Enemy ship. Basic cloaking consumes 1 kt per 20 kt hull mass with a minimum of 5 kt; Advanced Cloak has different fuel consumption, so the basic cost is only a reference bound.

Owner slot must not be assumed to equal race. The archive-derived `race_id` and static hull catalog decide whether the Bird + mission9 + cloak-capable signature is even present.

## Focused diagnostic

```text
tools/diagnostics/combat_host_initial_standard_target_cloak_residual_audit.py
tests/test_combat_host_initial_standard_target_cloak_residual_audit.py
```

Schema:

```text
planets-lab.combat-host-initial-standard-target-cloak-residual-audit.v1
```

For active, extra-target and factual-target ships, it prints:

```text
race_id
hull_id / hull_name / hull_mass / hull_can_cloak
mission / Primary Enemy / Friendly Code
T-1 fuel / damage / iscloaked
Bird + mission9 + cloak-capable static signature
documented basic-cloak reference fuel cost
whether T-1 fuel meets that ordinary reference cost
T owner / same-owner / same-hull controls
T iscloaked
scalar T state
```

It also prints scalar top-level/left/right fields for the factual VCR so capture/destruction outcome can be attributed without guessing from T ownership alone.

## Evidence boundary

The static Super Spy signature is **not** effective-cloak reconstruction. It deliberately does not resolve:

- Loki decloak;
- nebula/ion decloak;
- Advanced Cloak vs ordinary cloak type;
- damage-induced cloak failure beyond the printed raw state;
- other dynamic Host effects.

T state and VCR outcome are attribution controls only. They are not fed back into T-1 candidate selection.

The strongest expected residual explanation is:

```text
extra target:
  archive race = Bird
  mission9
  cloak-capable hull
  sufficient cloak conditions
  T control remains same ship/owner and iscloaked=true

factual target:
  not effectively cloaked at combat
  factual VCR occurs / capture outcome attributable
```

If both residuals support this pattern, add a generic tri-state ordinary active-cloak input to pair eligibility and block only directed attacks *against* an effectively cloaked target. A cloaked ship's own Primary Enemy attack request must remain able to initiate combat. Then rerun pair tests, candidate-set v2 and initial-target differential; require the broad target residuals to disappear without damaging factual-positive coverage.

If either residual does not support effective cloak, investigate another pair blocker. Do not invert standard Combat Priority or the target list rule.
