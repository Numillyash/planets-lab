# C5 Host combat — Bird Super Spy cloak context gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded.

## Why this gate exists

The Privateer Rob initial blocker is now closed at its scoped targetability boundary by the selector-impact runtime:

```text
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
privateer_residual_profiles_projected_fixed=2/2
bird_residual_profiles_overlay_affected=0/2
```

The only remaining original broad initial-STANDARD target blocker is:

```text
game 511506 / battle turn 94
active ship:        496 owner5/race5 Bloodfang
extra target:       202 owner3/race3 Red Wind
factual target:     332 owner3/race3 Resolute
```

Baseline strict and conditional profiles both rank ship202 first and the factual ship332 second.

## Existing corpus evidence

The earlier cloak-residual runtime established for ship202:

```text
race_id=3 (Bird)
hull47 Red Wind, cloak-capable
mission9 Super Spy
T-1 iscloaked=true
T-1 fuel=37
ordinary cloak reference cost=5
T same owner/hull and iscloaked=true
```

Ship332 is the crucial matched negative control against treating raw archived cloak as the mechanic:

```text
race3 Resolute, cloak-capable
mission2 (not Super Spy)
T-1 iscloaked=true
factual combat against ship496 occurs
```

Therefore raw `T-1 iscloaked=true` remains rejected as a generic combat blocker.

## Documented semantics

Official Planets.nu Super Spy documentation states that a Bird ship on the `Super Spy` mission which is capable of cloaking attempts to cloak normally for its cloak type; if it has inadequate fuel, cloak does not occur while the Super Spy mission continues.

Official Planets.nu Cloak documentation states that cloaked ships are protected from enemy attack, ordinary cloak consumes `max(5, floor(hull_mass / 20))` KT under the documented formula, Advanced Cloak consumes no fuel, and a damaged ship cannot initiate or maintain cloak.

Sources:

```text
https://help.planets.nu/mis-super-spy
https://help.planets.nu/mis-cloak
```

This gives the Bird residual a stronger DOCUMENTED basis than the Privateer Rob branch; the remaining question is whether the archived precombat dynamic context satisfies the documented cloak conditions without a visible decloak source.

## Active diagnostic

```text
tools/diagnostics/combat_host_bird_super_spy_cloak_context_audit.py
tests/test_combat_host_bird_super_spy_cloak_context_audit.py
```

Schema:

```text
planets-lab.combat-host-bird-super-spy-cloak-context-audit.v1
```

The gate projects both ship202 and factual ship332 and reports:

```text
race / mission / hull cloak capability
cloak type from static special
T-1 damage
T-1 fuel and ordinary reference cost
reference normal-movement fuel remaining
T-1 archived iscloaked
ion-storm start context
Loki start exposure
co-located active Glory context
T owner/hull/iscloaked as attribution-only controls
```

## Conservative candidate boundary

The diagnostic reports `documented_effective_cloak_supported=True` only when all of the following are resolved:

```text
Bird race3
mission9 Super Spy
cloak-capable hull
ordinary (not Advanced) cloak
damage=0
prior archived iscloaked=true
fuel > reference cost
reference normal move resolved
reference remaining fuel > reference cost
not inside archived T-1 ion disturbance
no active Loki start exposure
no co-located active POP/TRG Glory device
```

This is deliberately stricter than the official minimum and is scoped to the observed residual. T-state is never an input.

## Acceptance

A clean closure requires:

```text
extra ship202 documented_effective_cloak_supported=True
factual ship332 documented_effective_cloak_supported=False or unresolved for an explicit non-Super-Spy reason
raw_prior_cloak_control_separates=True
race_conflicts=0
```

If that passes, classify the Bird blocker as `DOCUMENTED + CORPUS_OBSERVED + TESTED` at the focused initial-STANDARD targetability boundary and project removal of ship202 from both baseline profiles. Only then promote a generic directional STANDARD targetability composition; do not introduce a symmetric pair-combat cloak blocker.

If the candidate is unresolved because of movement fuel, damage or a visible decloak context, keep Bird open and investigate that factor directly.
