# C5 Host combat phase — current handoff

GitHub is the only source of truth. Verify actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 must remain **open + draft** and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

Progress overview: `docs/handoff/2026-09-11-reverse-progress-assessment.md`.

## Stable C5 layers

Do not reopen absent a direct contradiction:

- deterministic pair composition in `src/planets_lab/rules/combat/selection.py`: `TESTED`;
- direct ordinary STANDARD priority: 413/413 higher static priority on RIGHT;
- normal PIA: 37/37 before regular combat, attacker RIGHT 37/37;
- isolated C&I attacker: 7/7 RIGHT;
- scoped Galactic Power Case2, reciprocal PIA and matching-FC closures;
- plain STANDARD repeated-pair second-pass side reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- owner-current `T-1` is the precombat order/state source;
- `T` is post-Host/postcombat and may reuse Ship IDs; never use it as production precombat state;
- static STANDARD Combat Priority and Friendly Code parser remain unchanged.

## Position / candidate checkpoint

```text
position v3:
  factual ship occurrences=3204
  predicted=1810 exact=1806 mismatch=4 uncovered=1383
  factual pairs exact=678 mismatch=4 unresolved=1304

candidate-set v2:
  factual unique pairs=1986
  candidate-covered=428
  conditional factual eligible=427 unresolved=1 blocked=0
  strict factual eligible=420 unresolved=8 blocked=0
```

## Initial plain-STANDARD selector — CLOSED

Production:

```python
select_initial_plain_standard(...)
```

Evidence order:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Runtime:

```text
docs/handoff/2026-09-16-combat-c5-initial-standard-canonical-selector-runtime.md
```

Differential:

```text
strict:      225/225 broad, 162/162 exact-set
conditional: 234/234 broad, 169/169 exact-set
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Unresolved candidates, eligible pre-standard pairs, unsupported priority or STANDARD side overrides fail closed.

## Directional ordinary-STANDARD targetability — CLOSED

Canonical pair input:

```python
ShipCombatSideInput.standard_targetable_by_opponent: bool | None
```

Semantics:

- affects only the opponent's ordinary STANDARD request;
- is applied after PIA/reciprocal-PIA/C&I classification;
- is directional, not a symmetric pair blocker;
- preserves the potentially cloaked ship's own attack request;
- never encodes cloak as `has_fuel=False`;
- unknown is fail-closed.

Population gate:

```text
supported blocks=10
conflicts=0
blocked factual pair rows=0
potential first-selector regressions=0
baseline mismatch profiles fixed=4/4
unrelated mismatches=0
```

Runtime:

```text
docs/handoff/2026-09-16-combat-c5-directional-targetability-population-runtime.md
docs/handoff/2026-09-16-combat-c5-directional-targetability-canonical-wiring-runtime.md
```

## Production precombat effective state — CLOSED for ordinary Privateer/Bird scopes

Privateer ordinary Rob:

```python
privateer_rob_ordinary_cloak_state(...)
```

Scope:

```text
race5 + mission9 Rob + ordinary cloak-capable hull
prior false                          -> effective cloak False
prior true + fuel <= reference cost -> effective cloak False
prior true + fuel >  reference cost -> effective cloak True
advanced cloak                       -> unresolved
```

Status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Bird ordinary Super Spy production API:

```python
bird_super_spy_ordinary_cloak_state(...)
standard_targetability_from_effective_cloak(...)
```

Runtime:

```text
docs/handoff/2026-09-16-combat-c5-production-effective-state-runtime.md
```

User runtime source:

```text
6a5e39796e385f4d98dc10697d30c958ad3a8898
41 targeted tests passed
```

Population result:

```text
bird_super_spy_targets_at_factual_sites=30
raw/conditional/strict one-way plain-STANDARD opportunities=8

decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
blocked factual-pair regressions=0
```

Focused residual:

```text
511506/T94 target202 <- attacker496
effective_cloak=True
standard_targetable_by_opponent=False
```

All production effective-state acceptance flags passed. Ordinary Bird Super Spy targetability is therefore:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The three unresolved decisive rows remain Advanced Cloak by design.

## Advanced Cloak — historical closure only

Known decisive rows:

```text
620694/T119 ship26 vs74 — expected blocked
620694/T119 ship69 vs74 — expected blocked
680435/T31 ship68 vs26 — factual pair / expected eligible
```

Historical closure:

- ship68: explicit mine hit -> damage55 -> same damage in factual VCR -> combat eligible;
- ship26/69: stable same-owner/same-hull T attribution, damage0, iscloaked=true -> skipped.

Do not promote a generic predictor. Post-Host T/messages are attribution evidence only.

## C3 survivor carry-over — prerequisite for current gate

Existing production in `src/planets_lab/rules/combat/sequence.py`:

```python
carry_ship_to_next_engagement(...)
```

Clean owner-certain same-turn same-location C3 subset:

```text
5 eligible transitions
5/5 exact under carry-over model
old reset baseline only 3/5
```

Captured predecessor transitions were explicitly excluded because ownership/hostility continuation is a separate mechanic.

## MUTABLE SHIP QUEUE — scope-repair runtime pending

Pending handoff:

```text
docs/handoff/2026-09-16-combat-c5-mutable-ship-queue-pending.md
```

Production module:

```text
src/planets_lab/rules/combat/mutable_queue.py
```

API:

```python
ShipQueueMutationResult
apply_ship_terminal_batch(...)
```

Supported semantics:

```text
destroyed -> remove from active map
survivor  -> require full C3 dynamic vector and carry state
captured  -> unresolved / fail closed
```

Mutation is atomic. Capture, unknown terminal flags, incomplete survivor state or carry failure return the original active map unchanged.

Diagnostic:

```text
tools/diagnostics/combat_host_mutable_ship_queue_audit.py
```

Tests:

```text
tests/test_combat_mutable_queue.py
tests/test_combat_host_mutable_ship_queue_audit.py
```

Required acceptance:

```text
survivor_population_present=True
survivor_membership_exact=True
capture_fail_closed_if_observed=True
destroyed_removal_if_reappearance_observed=True
no_production_mutation_errors=True
no_terminal_flag_unknowns=True
mutable_ship_queue_transition_gate_passed=True
```

Evidence boundary: exact dynamic field carry remains the independent C3 differential's responsibility. This gate tests active membership/continuation only. Absence of destroyed-reappearance rows is not treated as standalone proof of destruction order.

## Next C5 work after mutable membership

If green:

1. compose active membership mutation with initial selector;
2. add pair occurrence state and second-pass eligibility/orientation using the already DIFF_VERIFIED side-reversal helper;
3. validate the second ordinary STANDARD queue step against factual queues;
4. reconstruct capture continuation separately;
5. integrate ship-to-planet / planet-base queue ordering.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct.


## ACTIVE GATE — ordinary STANDARD queue history/composition

Pending runtime:

```text
docs/handoff/2026-09-18-combat-c5-standard-queue-composition-pending.md
```

The first mutable-queue corpus run was contaminated by isolated game `591478`: it ran 12 archives, and all 29 printed destroyed-predecessor reappearances came from that game. The ordinary gate has been repaired to exclude `591478`, matching the other C5 population diagnostics. Do not weaken the hard contradiction acceptance; rerun on the 11 ordinary archives.

New production module:

```text
src/planets_lab/rules/combat/host_queue.py
```

API:

```python
StandardQueueState
StandardQueueStepResult
select_next_plain_standard(...)
select_after_ship_mutation(...)
record_standard_queue_step(...)
```

This layer composes active membership, the canonical selector and pair-occurrence history without recomputing pair mechanics. Pair inputs after a mutation must be supplied freshly by the caller.

Second-occurrence production corpus gate:

```text
tools/diagnostics/combat_host_second_standard_queue_audit.py
```

Scope is deliberately narrow: stable-owner, exactly-two, plain-static-comparable repeated pairs from the ordinary corpus. Expected population remains the two existing controls from games 620917 and 621896. Passing this gate promotes production occurrence-history composition only; full post-mutation next-pair selection among a multi-pair stack remains the following gate.
