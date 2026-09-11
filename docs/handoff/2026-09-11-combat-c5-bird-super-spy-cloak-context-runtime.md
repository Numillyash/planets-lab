# C5 Host combat — Bird Super Spy cloak context runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded from ordinary promotion.

## Runtime

Source HEAD:

```text
6cf47de46fadcbe1619c6a6eee5731d51866c12e
```

Executed:

```text
tests/test_combat_host_bird_super_spy_cloak_context_audit.py
tests/test_combat_effective_state.py
tests/test_combat_host_privateer_rob_selector_impact_audit.py
tools/diagnostics/combat_host_bird_super_spy_cloak_context_audit.py
```

Result:

```text
21 targeted tests passed
focus_row_found=True
archive_found=True
race_conflicts=0
extra_ship_documented_effective_cloak_supported=True
factual_ship_documented_effective_cloak_supported=False
raw_prior_cloak_control_separates=True
```

Artifact:

```text
artifacts/combat-bird-super-spy-cloak-context.json
```

## Focus residual

```text
game 511506 / battle turn 94
precombat archive turn 93
active ship:        496 owner5/race5 Bloodfang
extra target:       202 owner3/race3 Red Wind
factual target:     332 owner3/race3 Resolute
factual VCR:        728
```

### Extra target ship202

Observed/reconstructed state:

```text
race=3 Bird
hull47 Red Wind Class Carrier
ordinary cloak-capable hull
mission=9 Super Spy
damage=0
fuel=37
ordinary reference cloak cost=5
prior iscloaked=true
```

Independent ordinary normal-movement reconstruction:

```text
effective warp=9
distance=52.15361924162119
fuel required=8
fuel used=8
remaining reference fuel=29
```

Thus fuel remains safely above the ordinary cloak reference cost after reconstructed movement.

Visible decloak context was clear:

```text
ion storm start inside=False
planet Super-Spy Ion Pulse possible=False
active Loki start exposure=False
co-located active POP/TRG Glory=False
```

T-state attribution-only controls:

```text
same owner=True
same hull=True
T iscloaked=True
```

Diagnostic conclusion:

```text
documented_effective_cloak_supported=True
reason=documented_super_spy_ordinary_cloak_supported
```

This closes ship202 as the missing directional STANDARD targetability blocker at the focused residual boundary.

### Factual target ship332 — matched raw-cloak negative control

Observed/reconstructed state:

```text
race=3 Bird
hull31 Resolute Class Battlecruiser
Advanced Cloak hull
mission=2, not Super Spy
damage=0
fuel=480
prior iscloaked=true
```

The ship actually participates in factual combat against ship496. The focused Bird Super Spy model therefore returns:

```text
documented_effective_cloak_supported=None
reason=outside_super_spy_scope
```

This is the required control demonstrating again that raw archived `T-1 iscloaked=true` is not a generic combat blocker.

## Evidence status

Focused Bird Super Spy ordinary-cloak targetability blocker:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED
```

Supporting documented semantics:

- Bird `Super Spy` on a cloak-capable ship attempts to cloak normally;
- inadequate fuel prevents the cloak attempt;
- ordinary cloak fuel follows the documented cloak cost;
- damaged ships cannot maintain/initiate ordinary cloak;
- cloaked ships are protected from ordinary enemy attack;
- Super-Spy ion pulse is a separate decloak context and was explicitly checked here.

The dynamic precombat state is archive/corpus evidence; the official rules are documentation evidence. T-state is attribution-only and is not fed into the candidate.

## Rejected/generalization boundaries

Do **not** promote any of the following from this runtime:

```text
raw T-1 iscloaked => combat blocker
generic Bird mission-independent cloak reconstruction
generic Advanced Cloak combat-state reconstruction
symmetric pair-combat cloak blocker
all cloak mechanics across all Host phases
```

The demonstrated mechanic is directional ordinary-STANDARD targetability for this documented Super Spy state.

## C5 consequence

Both original broad initial-target residuals now have independent closures:

```text
360690/T83 ship98  -> Privateer Rob ordinary-cloak threshold targetability
511506/T94 ship202 -> Bird Super Spy documented ordinary-cloak targetability
```

The next gate is to compose these evidence-scoped states into a generic **directional STANDARD targetability** layer and rerun the complete initial-selector differential over the historical corpus.

Acceptance for that next gate must preserve:

```text
all previously exact initial selectors
zero factual-pair blocking regressions
zero first-selector regressions
Privateer residual fixed in all comparable profiles
Bird residual fixed in all comparable profiles
unknown/out-of-scope effective states fail closed
```

Only after that differential passes should the canonical first STANDARD selector be promoted and C5 move to mutable survivor/destruction state, second-pass orientation, capture continuation and planet/base continuation.
