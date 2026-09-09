# C5 Host combat — factual ship queue / pair-selection differential pending runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` is excluded from ordinary promotion.

## Preceding runtime

The canonical pair-level selection composition passed its targeted runtime on source:

```text
7ac5d70a77f592dfd1d3660c237b244e61795305
```

with:

```text
........................................................ [100%]
tests rc=0
```

Therefore `src/planets_lab/rules/combat/selection.py` is `TESTED` at the unit-composition boundary.

See:

```text
docs/handoff/2026-09-09-combat-c5-pair-selection-runtime.md
```

## First factual-queue runtime attempt — harness invariant fixed

User runtime on source:

```text
a6ac305e41ad17f351ff75c8906fb22b8eef2b52
```

passed all targeted tests but the corpus audit stopped before producing mechanics output:

```text
TARGETED TESTS: 66 passed
audit: AssertionError in decide_ship_combat_pair(...)
tests rc=0
audit rc=1
```

The failing assertion required both directed attack permissions to be non-`None` after `_base_engagement()` returned eligible. That invariant was too strong: one known-allowed Kill!/PE requester is sufficient to establish engagement while the opposite direction may legitimately remain unknown.

Scoped fix:

- removed the invalid both-directions-known assertion;
- preserve the opposite `None` into pre-standard classification;
- special branches that actually depend on that unknown direction still fail closed;
- ordinary standard phase may continue when one known requester already proves the factual pair can engage;
- added regression `test_known_aggressor_allows_standard_phase_with_unknown_opposite_diplomacy`.

This failed attempt is **not mechanics evidence**. No factual queue summary was emitted.

## Second factual-queue runtime — first real stack differential

User runtime on source:

```text
104332ee9d93c5de83bea613282b4c9a2d9cd863
```

completed successfully:

```text
TARGETED TESTS: 67 passed
tests rc=0
audit rc=0
payload_conflicts=0
factual_ship_vcr_rows=1968
sites=1216
multi_vcr_sites=348
```

Conditional factual-positive scope:

```text
engagement_eligible: True=1968
phase: standard=1904, priority_intercept=48, unresolved=16
prestandard_kind: normal_priority_intercept=47, reciprocal_priority_intercept=1
side_result: exact=1944, unresolved=19, mismatch=5
```

Strict scope:

```text
engagement_eligible: True=1949, unresolved=19
phase: standard=1885, priority_intercept=48, unresolved=35
side_result: exact=1925, unresolved=38, mismatch=5
```

Site-layer result is strong:

```text
strict all_phase_resolved_sites=1183
strict fully_resolved_prefix_exact=1183
conditional all_phase_resolved_sites=1202
conditional fully_resolved_prefix_exact=1202
known prefix violations=0
```

Case1 remains the intended reciprocal Priority Intercept classification with universal side unresolved. Case2 remains exact under Galactic Power forced-left.

### Three of five side mismatches are a canonical PIA pair-binding bug

Rows:

```text
622476/T25/VCR87: interceptor ship40 mission7 target15, factual opponent72
622476/T26/VCR93: interceptor ship65 mission7 target27, factual opponent54
622476/T28/VCR110: interceptor ship45 mission7 target35, factual opponent42
```

The pair-level `_normal_pia_candidate(...)` used the static mission7/PE/cloak signature but did not additionally require that the considered pair opponent was the actual `mission1target`. This incorrectly promoted an ordinary later combat against another ship of the same target owner into PIA.

Canonical fix committed:

- normal PIA now requires `interceptor.mission_target_id == target.ship_id`;
- regression `test_normal_pia_does_not_apply_to_other_ship_of_same_target_owner` added.

Do not reinterpret the existing `priority_intercept_order_signature(...)`; its role remains the broad order signature. Exact pair binding belongs in the pair-selection layer where the opponent ship ID exists.

### Two standard side residuals remain for queue-history analysis

```text
620917/T7/VCR6
621896/T25/VCR52
```

Both are standard-phase residuals and must not be used to weaken `standard_battle_priority_key(...)` yet. Primary Planets.nu documentation explicitly notes dynamic shifts in complex stacked combat, and classic Host documentation describes repeated same-pair combat after timeout as a side/initiator exception to the static battle-value rule.

Targeted diagnostic committed:

```text
tools/diagnostics/combat_host_factual_queue_side_residual_audit.py
tests/test_combat_host_factual_queue_side_residual_audit.py
```

It reports the full site ship-VCR queue for these two cases plus same-pair occurrence index/count and T-1 standard priority inputs. The purpose is to determine whether either mismatch is a second-or-later encounter of the same pair or otherwise requires mutable queue state.

## Objective

Validate the pair-level composition across real ordinary ship-vs-ship VCR queues before implementing mutable Host target selection.

This gate deliberately does **not** claim to predict which pairs will fight. Existing factual VCR presence is used as an oracle that a pair reached engagement eligibility. The audit asks only:

- can current C5 mechanics attribute the pair to PIA / reciprocal PIA / C&I / standard phase;
- when side assignment is attributable, does it match factual left/right;
- do resolved pre-standard rows precede resolved standard rows at the site;
- does normal-PIA attacker ordering remain compatible with reverse Ship ID where a multi-attacker site becomes comparable;
- do Case1 and Case2 retain their scoped explanations under the unified API.

## Committed diagnostics — pending rerun after target-binding fix

```text
tools/diagnostics/combat_host_factual_queue_selection_audit.py
tests/test_combat_host_factual_queue_selection_audit.py

tools/diagnostics/combat_host_factual_queue_side_residual_audit.py
tests/test_combat_host_factual_queue_side_residual_audit.py
```

Main schema:

```text
planets-lab.combat-host-factual-queue-selection-audit.v1
```

Residual schema:

```text
planets-lab.combat-host-factual-queue-side-residual-audit.v1
```

## Evidence scopes

### strict

The factual VCR still supplies positive engagement existence, but directed diplomacy is resolved only from an **independent** control:

- the candidate T-1 relation signature is unique;
- another factual ship-vs-ship VCR in the same game has the same relation signature;
- that other VCR has exactly one raw Kill!/PE requester, so the permitted aggression direction is attributable without choosing between two simultaneous requesters;
- the control row is not the candidate row itself.

A stronger flag records when such an independent control exists in the same battle turn.

If no independent directed control exists, the relevant side permission remains `None` and selection must fail closed only where that unknown actually matters to the requested classification.

### conditional factual-positive

For a factual VCR only, each raw Kill!/PE request is supplied as allowed so the audit can measure the *upper-bound conditional* phase/side composition once engagement is known to have occurred.

This scope is not candidate-set prediction and must not be described as `DIFF_VERIFIED` engagement eligibility.

## Intercept Interference context

Primary Planets.nu documentation states that Standard games from 2021 onward give the Evil Empire Super Star Cruiser and Super Star Cruiser II Intercept Interference, protecting same-owner ships that began the turn at the same location.

The diagnostic therefore uses T-1 start stacks:

- no same-owner hull 74/1074 at the target start position -> protection `False`;
- source present + previously public-verified Standard game context -> `True`;
- source present + previously public-verified Classic game context -> `False`;
- source present + unknown game context -> `None`.

The prior public game-context gate supplies only this diagnostic mapping:

```text
Classic:  360690 511506 620694
Standard: 621253 621896 680435
```

No generic game-type inference is encoded from those IDs.

## Galactic Power context

The same verified public game mapping is supplied only for Evil-Empire-owned hull70 Gorbies so Case2 and the other previously audited Gorbie rows can receive an attributable effective GP state. Non-Empire/non-Gorbie rows resolve GP to false without needing game context.

## C&I boundary

Observed mission20 establishes the historical C&I order, but T-1 does not independently prove:

- modern Bird-buildable-hull eligibility for an arbitrary captured hull;
- active cloak still present at the later Intercept step.

Those values therefore remain unresolved in this gate. C&I rows may intentionally remain phase-unresolved; this is evidence of missing dynamic state, not an audit failure.

## Next runtime gate

Run the main factual queue audit again after the exact-target PIA fix, plus the narrow side-residual diagnostic.

Expected first-order effect if the fix is correct:

```text
normal_priority_intercept: 47 -> 44
standard: +3
resolved side mismatches: 5 -> at most 2
```

The two remaining standard residuals then determine whether static pair-side assignment needs a queue-history input or a different bounded exception.

## Promotion rules

- A zero side mismatch count on resolved first-occurrence/static-comparable rows can support the current side composition boundary.
- A zero known pre-standard-prefix violation count supports the current phase layering on attributable rows.
- Unresolved rows are coverage gaps and must not be counted as matches.
- Repeated same-pair rows are queue-history dependent and must not be forced into a static pair-side rule.
- Candidate-set prediction remains open regardless of how clean this gate is.
- Do not implement mutable queue selection until this runtime is understood.
