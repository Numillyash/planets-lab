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

## Objective

Validate the pair-level composition across real ordinary ship-vs-ship VCR queues before implementing mutable Host target selection.

This gate deliberately does **not** claim to predict which pairs will fight. Existing factual VCR presence is used as an oracle that a pair reached engagement eligibility. The audit asks only:

- can current C5 mechanics attribute the pair to PIA / reciprocal PIA / C&I / standard phase;
- when side assignment is attributable, does it match factual left/right;
- do resolved pre-standard rows precede resolved standard rows at the site;
- does normal-PIA attacker ordering remain compatible with reverse Ship ID where a multi-attacker site becomes comparable;
- do Case1 and Case2 retain their scoped explanations under the unified API.

## Committed diagnostic — pending successful runtime

```text
tools/diagnostics/combat_host_factual_queue_selection_audit.py
tests/test_combat_host_factual_queue_selection_audit.py
```

Schema:

```text
planets-lab.combat-host-factual-queue-selection-audit.v1
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

## Runtime gate

Run:

```text
tests/test_combat_order.py
tests/test_combat_eligibility.py
tests/test_combat_selection.py
tests/test_combat_host_factual_queue_selection_audit.py
```

then:

```text
tools/diagnostics/combat_host_factual_queue_selection_audit.py
```

Important outputs:

```text
summary.factual_ship_vcr_rows
summary.sites
summary.multi_vcr_sites
summary.strict
summary.conditional
summary.strict_sites
summary.conditional_sites
case1_reciprocal
case2_galactic_power
```

Most important interpretation fields:

```text
side_result.exact / mismatch / unresolved
unresolved_reasons
all_phase_resolved_sites
fully_resolved_prefix_exact
fully_resolved_prefix_violation
known_prefix_violation_any_scope
normal_pia_reverse_id_comparable
normal_pia_reverse_id_exact
normal_pia_reverse_id_mismatch
```

## Promotion rules

- A zero side mismatch count on resolved rows can support the current side composition boundary.
- A zero known pre-standard-prefix violation count supports the current phase layering on attributable rows.
- Unresolved rows are coverage gaps and must not be counted as matches.
- Candidate-set prediction remains open regardless of how clean this gate is.
- Do not implement mutable queue selection until this runtime is understood.
