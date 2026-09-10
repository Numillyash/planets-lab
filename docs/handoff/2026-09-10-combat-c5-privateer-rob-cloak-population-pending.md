# C5 Host combat — Privateer Rob cloak population pending

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Dependency runtime:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md
```

The prior focused gate partially closed the two broad initial-target residuals:

```text
511506/T94 extra ship202 -> Bird Super Spy + cloak-capable Red Wind + persistent cloak control
360690/T83 extra ship98  -> Privateer mission9/Rob + cloak-capable Meteor + persistent raw cloak bit, semantics unresolved
```

Raw `T-1 iscloaked=true` is not a generic combat blocker because factual target ship332 also has that bit yet enters VCR728 under current mission2.

## New population diagnostic

```text
tools/diagnostics/combat_host_privateer_rob_cloak_population_audit.py
tests/test_combat_host_privateer_rob_cloak_population_audit.py
```

Schema:

```text
planets-lab.combat-host-privateer-rob-cloak-population-audit.v1
```

The population is restricted to:

```text
ordinary game (591478 excluded)
archive-resolved race_id=5
race-specific mission=9
static hull can_cloak=true
owner-current record at before_turn
```

For the next archive turn it records owner-current state and accepts identity as stable only when:

```text
same owner
same hull / engine / beam / beam-count / torpedo-type / bay-count
same build-turn marker when available
```

Mutable cargo, fuel, torpedo quantity, damage, crew and mission are deliberately excluded from physical identity matching.

Reported cloak transitions on stable rows include:

```text
true_to_true
true_to_false
false_to_true
false_to_false
unknown variants
```

The audit also reports same-turn VCR participation. A particularly useful negative-control bucket is:

```text
stable_before_cloaked_pe_zero_vcr
```

Because Privateer mission9 is not Kill! and PE=0 cannot request combat itself, such rows would show that a prior raw cloak bit did not protect the ship from being selected by an opponent in that Host turn. Conversely, repeated `true_to_true` stable/no-VCR rows would support persistence of the archived state but would still not by themselves prove effective cloak at the combat step.

The exact target residual is reported separately:

```text
360690 before T82 -> battle T83 ship98
```

## Evidence boundary

This gate is attribution-only. It does **not** assert that Privateer Rob creates or preserves cloak, and does not feed T-state back into candidate selection. Same Ship ID alone is explicitly insufficient because post-combat construction can reuse an ID; identity continuity is checked before using the T record.

No `selection.py` or target-order change is allowed from this diagnostic alone.

Interpretation:

- systematic stable `true_to_true` for Privateer Rob may indicate NuHost persistence/timing semantics requiring a dedicated follow-up;
- stable `before-cloaked + PE0 + VCR` rows are direct counterexamples to treating the raw prior cloak bit as a combat blocker;
- an isolated ship98 shape remains bounded unresolved;
- target ordering remains the documented/highest-priority hypothesis, already exact on the clean exact-set population.
