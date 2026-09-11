# C5 Host combat — Privateer Rob effective-cloak threshold differential runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded from ordinary promotion.

Runtime source:

```text
37ea8fc3a68be3b18737f6a71a2a09bb36226ad5
```

The local shell first attempted `cd /opt/planets-lab`, which did not exist in that environment. The shell remained in `~/projects/planets-lab`; branch checkout/pull then verified the exact expected source HEAD above. The runtime is therefore valid.

Executed:

```text
tests/test_combat_host_privateer_rob_effective_cloak_threshold_audit.py
tools/diagnostics/combat_host_privateer_rob_effective_cloak_threshold_audit.py
```

Runtime result:

```text
tests: 5 passed

audit:
  opportunities=16
  decisive_rows=8
  decisive_match=8
  decisive_mismatch=0
  decisive_unresolved=0
  nondecisive_rows=8

  decisive_matrix:
    expected_eligible:candidate_eligible = 5
    expected_blocked:candidate_blocked   = 3
```

The gate is **TESTED** at its diagnostic boundary.

## Candidate under test

This runtime tested one deliberately scoped candidate only:

```text
prior iscloaked=false
  -> not effectively cloaked

prior iscloaked=true
ordinary cloak hull
fuel <= ordinary cloak reference cost
  -> not effectively cloaked

prior iscloaked=true
ordinary cloak hull
fuel > ordinary cloak reference cost
  -> effectively cloaked

advanced cloak
  -> unresolved / fail closed
```

This is not yet a universal Host cloak solver and is not wired into canonical pair selection.

## Queue-decisive evidence

Only factual initial-queue shapes that genuinely label blocker state were scored:

```text
initial_skip_target_outranks_factual -> expected blocked
initial_pair_vcr                     -> expected eligible
```

All 8 decisive controls match.

### Three expected-blocked controls

All three clean missing-state Privateer Meteors are predicted effectively cloaked:

```text
360690/T57 ship46:
  prior=true, fuel=58, reference=5, margin=+53
  candidate_blocked=true

360690/T57 ship280:
  prior=true, fuel=9, reference=5, margin=+4
  candidate_blocked=true

360690/T83 ship98:
  prior=true, fuel=45, reference=5, margin=+40
  candidate_blocked=true
```

Each strictly outranks the factual first target for the same initial attacker and is factually skipped.

### Five expected-eligible controls

The five factual initial-pair controls are all left eligible:

```text
360690/T56 ship145: prior=false, fuel=5, reference=5
360690/T70 ship46:  prior=false, fuel=3, reference=5
360690/T83 ship190: prior=false, fuel=4, reference=5
360690/T94 ship98:  prior=false, fuel=5, reference=5
620694/T64 ship118: prior=true,  fuel=5, reference=5
```

The most important control is `620694/T64/ship118`:

```text
prior iscloaked=true
fuel == reference cost == 5
candidate_effective_cloak=false
factual initial pair exists
T archived cloak transition=true_to_false
```

This closes the previous apparent contradiction between the three skipped prior-true Meteors and the one fought prior-true Meteor without requiring a ship-specific exception.

## Nondecisive controls

Eight remaining Rob opportunities are retained as controls but are not used as labels because factual queue order does not identify blocker state uniquely.

They are directionally consistent with the candidate:

- prior-false rows remain eligible;
- prior-true ordinary-cloak rows above the threshold are marked blocked;
- the low-fuel prior-true control at `360690/T38/ship116` is marked eligible and has archived `true_to_false` transition;
- `620694/T64/ship118` also remains eligible in its later-pair occurrence.

No nondecisive row is promoted as proof.

## Evidence synthesis

Combined with the preceding attribution runtime:

```text
ordinary-cloak stable prior-true threshold population:
  fuel <= reference cost -> 13/13 true_to_false

queue-decisive Rob combat opportunities:
  8/8 candidate-state matches
  3/3 expected blocked
  5/5 expected eligible
```

This is materially stronger than the earlier raw `iscloaked` correlation. It supports an **evidence-scoped Privateer Rob precombat effective-cloak state model** for ordinary cloak hulls.

It does not establish the exact causal Host phase. In particular, the clean fuel-attribution gate rejected a universal `Rob Ship consumes ordinary cloak fuel` interpretation; the threshold state may be produced by another Host ordering/state transition.

## Promotion boundary

Promoted at diagnostic/model level:

```text
Privateer race5 + mission9/Rob + cloak-capable ordinary-cloak hull + prior archived iscloaked=true:
  fuel > ordinary cloak reference cost  -> evidence supports combat-effective cloak
  fuel <= ordinary cloak reference cost -> evidence supports not combat-effective cloak

status:
  CORPUS_OBSERVED + TESTED
```

Still not promoted:

```text
universal cloak mechanics for all races/missions
advanced-cloak threshold behavior
Rob fuel-consumption causality
Bird Super Spy effective cloak
canonical selection.py blocker wiring
```

## Next gate

The next step is a broader initial plain-STANDARD selector differential using this helper as an overlay while leaving canonical `selection.py` unchanged.

Required acceptance boundary:

1. the Privateer `360690/T83/ship98` broad residual must disappear;
2. all previously exact initial STANDARD sites must remain exact under the scoped overlay;
3. no new first-pair or first-right regression may appear;
4. Bird `511506/T94/ship202` must remain as a separate unresolved Super Spy/effective-cloak residual;
5. advanced cloak and unresolved state must fail closed rather than being guessed.

Only after that broader differential should the helper be considered for canonical candidate/selection composition.
