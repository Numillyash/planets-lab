# C5 Host combat — Privateer Rob attack-opportunity pending

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Dependencies:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-population-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-vcr-control-runtime.md
```

The transition population established large-scale persistence of the archived `iscloaked` bit for Privateer mission9 ships, but that alone does not prove combat-effective cloak. The two stable VCR participants both had nonzero Primary Enemy and could initiate their own combat, so there is still no PE0 targetability counterexample.

## Diagnostic

```text
tools/diagnostics/combat_host_privateer_rob_attack_opportunity_audit.py
tests/test_combat_host_privateer_rob_attack_opportunity_audit.py
```

Schema:

```text
planets-lab.combat-host-privateer-rob-attack-opportunity-audit.v1
```

## Scope

The diagnostic only considers ordinary factual ship-combat sites and reconstructs the site stack independently from owner-current T-1 state through the same repaired movement/candidate-set-v2 boundary.

A target opportunity requires:

```text
archive-resolved target race_id=5 Privateer
target mission=9
target hull can_cloak=true
target PE=0 or missing/nonpositive
target and opponent independently predicted at factual battle site
opponent owner differs
opponent raw Kill!/PE requests combat against target owner
target does not request combat back
canonical conditional pair decision resolves engagement_eligible=true
canonical conditional phase=STANDARD
```

Visible T-1 foreign mine-route risks fail closed exactly as candidate-set v2 does.

Strict scope additionally requires an independent same-relation-signature diplomacy control for the attacker's direction. Conditional scope remains an upper-bound raw-aggression profile.

## Outcome labels

For each attack opportunity, factual VCRs at that site are held out until after the candidate pair is predicted:

```text
pair_vcr
attacker_fought_other
target_fought_other
both_fought_other
neither_vcr
```

The strongest direct skip shape is:

```text
prior target iscloaked=true
conditional/strict plain-STANDARD attack opportunity exists
attacker_fought_other
target not in any factual VCR
```

The known residual must appear explicitly:

```text
360690/T83 site 2374,2260
target ship98
attacker ship264
factual pair at site [190,264]
expected opportunity outcome before any cloak rule: attacker_fought_other
```

## Controls

The report groups outcomes by raw prior cloak state:

```text
true
false
unknown
```

A useful population differential would be many/most `true` targets skipped while comparable `false` targets are actually fought. Any `true + PE0 + pair_vcr` row is a direct counterexample to a blanket interpretation of the archive bit and must be inspected before promotion.

## Evidence boundary

This diagnostic does not assert that Rob creates cloak, that prior `iscloaked` is combat-effective, or that a skipped candidate was skipped because of cloak. It only establishes hostile attack opportunity versus factual selection under independently reconstructed position and canonical pair composition.

No change to `selection.py`, target ordering, combat priority or Friendly Code parsing is allowed from this gate alone. If the opportunity population gives a clean directional cloak differential, the next step is a separately scoped effective-cloak reconstruction primitive followed by candidate-set v2 and initial-target reruns.
