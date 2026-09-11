# C5 Host combat — Privateer Rob initial cloak-context gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Depends on:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md
```

Runtime established exactly three clean prior-true first-decision skips and one clean prior-true first-pair control:

```text
initial_skip_target_outranks_factual=3
initial_pair_vcr prior-true=1
```

The three clean skips are:

```text
360690/T83 ship98 vs attacker264
360690/T57 ship46 vs attacker146
360690/T57 ship280 vs attacker146
```

The clean prior-true fought control is:

```text
620694/T64 ship118 vs attacker134
```

## Strong matched controls already present

Two sites contain same-attacker / same-owner / same-hull / same-Rob-mission visible controls:

```text
360690/T83:
  Meteor98  prior iscloaked=true  -> skipped
  Meteor190 prior iscloaked=false -> factual pair with attacker264

360690/T57:
  Meteor46  prior iscloaked=true  -> skipped
  Meteor280 prior iscloaked=true  -> skipped
  Meteor293 prior iscloaked=false -> factual pair with attacker146
```

The skipped ships strictly outrank the factual first target under the already diff-verified STANDARD target ordering, so ordinary queue rank cannot explain them.

## Relevant documented cloak state transitions

Current official Planets.nu documentation states:

- cloaked ships are protected from enemy attack;
- cloak state is dynamic within Host;
- damage prevents maintaining cloak;
- running out of fuel during movement can uncloak a ship;
- Loki/Tachyon can decloak a non-immune cloaked ship within 10 ly when the Loki has <20% damage;
- ion storms, mine hits and Glory Devices can also remove cloak;
- Rob Ship is a separate Privateer mission executed before movement.

Reference pages:

```text
https://help.planets.nu/cloak-details
https://help.planets.nu/abil-tachyon-device
https://help.planets.nu/mis-rob-ship
https://help.planets.nu/out-of-fuel
```

Important evidence boundary: official documentation also describes all ships as starting a Host turn uncloaked and ordinary cloak as being engaged by the Cloak mission. Therefore this gate must not silently interpret archived prior `iscloaked=true` on mission9/Rob as current effective cloak. The purpose is to identify the state discriminator empirically.

## Diagnostic

```text
tools/diagnostics/combat_host_privateer_rob_initial_cloak_context_audit.py
tests/test_combat_host_privateer_rob_initial_cloak_context_audit.py
```

Schema:

```text
planets-lab.combat-host-privateer-rob-initial-cloak-context-audit.v1
```

Population is derived automatically from the tested initial-decision audit:

```text
target_prior_cloak=true
AND classification in {
  initial_skip_target_outranks_factual,
  initial_pair_vcr
}
```

Expected rows: 4.

For each row the diagnostic reports:

```text
T-1 target damage/fuel/mission/FC/origin
basic ordinary-cloak fuel reference
reference normal-movement fuel_used and raw remaining fuel
visible foreign owner-current ships co-located at Rob origin
T-1 Loki hull7 start proximity to target origin
T Loki proximity to battle site as attribution-only evidence
stable T target identity/fuel/damage/iscloaked where available
```

### Fuel interpretation

The movement fuel calculation uses the same deterministic normal-move planner already used by the repaired C5 position layer.

For a Rob ship it is not automatically causal because Rob executes before movement and can add fuel/cargo. Therefore:

```text
raw_reference_remaining_fuel == 0
AND no visible foreign ship at T-1 origin
```

is much stronger than raw fuel exhaustion alone.

A nonzero foreign-origin population is only Rob exposure; this gate does not reconstruct diplomacy immunity, victim cloak, exact Rob order or the documented 1% failure chance.

### Loki interpretation

Documented ordinary Loki/Tachyon discriminator used by the audit:

```text
hullid=7
Loki damage <= 19%
range <= 10 ly
```

T-1 start proximity is independent precombat evidence. T Loki proximity is clearly labelled attribution-only because T is post-Host/postcombat state and is never fed into combat prediction.

## Decision logic

Strong support for a scoped effective-state blocker would be:

```text
all three clean skips:
  damage=0
  retain positive fuel through reference movement or have no documented decloak context
  no active Loki context

clean fought control ship118:
  has a documented decloak discriminator absent from skips
  e.g. exact fuel exhaustion with no Rob fuel source, or active Loki context
```

If ship118 is cleanly explained, the next step is a larger matched-control population before changing `selection.py`.

If ship118 is not explained, do not promote raw cloak. Expand only the documented decloak attribution boundary needed by that row (ion/mine/glory or other exact context).

No target-order inversion, Friendly Code parser change or generic mission9 cloak rule is allowed from this gate.
