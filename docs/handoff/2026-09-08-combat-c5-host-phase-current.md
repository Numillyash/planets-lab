# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

This is the compact current pointer; dated handoffs contain full evidence and runtime details.

## Stable C5 layers

- corpus: 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts;
- owner-current `T-1` is the precombat order/state source; `T` is post-Host/postcombat and same Ship ID at T is not automatically the same physical ship because later construction can reuse an ID;
- mission3=Kill!, mission7=Intercept, mission20=Bird Cloak and Intercept, raw `enemy`=Primary Enemy;
- direct isolated ordinary STANDARD: 413/413 higher static priority on RIGHT;
- normal PIA: 37/37 before regular combat, attacker RIGHT 37/37;
- isolated C&I factual attacker: 7/7 RIGHT;
- `src/planets_lab/rules/combat/selection.py` deterministic pair composition: `TESTED`;
- plain STANDARD repeated-pair second-pass side reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- static STANDARD priority remains unchanged.

Do not reopen Galactic Power Case2, reciprocal PIA, matching-FC, diplomacy, physical-stack or repeated-pair gates absent a direct contradiction. Do not weaken Friendly Code parsing or standard Combat Priority to fit queue residuals.

## Position checkpoint

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md
docs/handoff/2026-09-09-combat-c5-unresolved-movement-context-runtime.md
```

Repaired v3 runtime source `14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c`:

```text
ship occurrences: factual=3204 predicted=1810 exact=1806 mismatch=4 uncovered=1383
factual pairs:     total=1986 exact=678 mismatch=4 unresolved=1304
sites:             total=1220 fully position-exact=346 mismatch sites=4
payload_conflicts=0
storm modes: false=10 true=1
```

Six classic-ion-storm residuals are independently exact. Two remaining rows are DIFF_VERIFIED stochastic normal-mine hits and two remain bounded unresolved. No factual endpoint is injected into the predictor.

## Candidate-set v2 — runtime complete

Read `docs/handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md`.

Runtime source `c804575f4275f4454dbb282d9fcfc99fad0700d6`:

```text
factual unique pairs=1986
candidate-covered factual pairs=428
candidate-uncovered factual pairs=1558
candidate pairs=1092
strict factual:      eligible=420 unresolved=8 blocked=0
conditional factual: eligible=427 unresolved=1 blocked=0
conditional eligible nonfactual=331
all factual positions covered sites=242
conditional factual subset of eligible=236
conditional eligible exactly factual=171
payload_conflicts=0
```

No candidate-covered factual pair is conditionally hard-blocked.

## Initial plain STANDARD target-order — runtime complete

Read `docs/handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`.

Runtime source `d7ade79d1344ba21a99f21d3fcc2d3e911dff3c3`:

```text
conditional exact-set: 169/169 first pair exact; 169/169 RIGHT exact
strict exact-set:      162/162 first pair exact; 162/162 RIGHT exact
informative exact-set target-order controls: 15/15 target rank1
```

Strongly supported when the eligible set is correct:

```text
first active ship = highest standard Combat Priority ship having an eligible target
first target      = highest-priority eligible target for that active ship
```

Only two broad residuals remain and both choose the correct active ship:

```text
360690/T83: active264; extra target98; factual target190
511506/T94: active496; extra target202; factual target332
```

Do not invert target ordering.

## Initial blocker evidence

Fuel runtime `docs/handoff/2026-09-10-combat-c5-initial-standard-target-fuel-runtime.md` rejected zero fuel:

```text
ship98 postmove fuel=45
ship202 postmove fuel=29
```

Cloak attribution runtime `docs/handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md`:

```text
ship202: Bird race3 + Red Wind hull47 + mission9/Super Spy + cloak-capable + fuel sufficient
         => strong scoped effective-cloak candidate
ship98:  Privateer race5 + Meteor hull46 + mission9/Rob + raw prior iscloaked=true
         => different mechanism/state source; Rob is not Super Spy
```

Factual `511506/T94/ship332` has raw prior `iscloaked=true`, current mission2 and VCR728 occurs. Raw T-1 `iscloaked` is therefore rejected as a blanket blocker.

## Privateer Rob raw-cloak population — runtime complete

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-population-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-vcr-control-runtime.md
```

Runtime/control extraction:

```text
candidate_rows=2223
stable_identity=2174
stable_vcr_participant=2
before_cloak_true=1433
true_to_true=1378
false_to_true=693
false_to_false=68
true_to_false=35
stable_before_cloaked_pe_zero_no_vcr=1394
stable_true_to_true_pe_zero_no_vcr=1360
stable_before_cloaked_pe_zero_vcr=0
stable_true_to_true_pe_zero_vcr=0
payload_conflicts=0
```

The only two stable VCR participants both have a Primary Enemy equal to the factual opponent owner and can self-initiate combat. The exact ship98 residual is a typical stable PE0 `true_to_true` no-VCR row. This is archive-state persistence evidence, not combat-effective-cloak proof.

## Site-conditioned Privateer Rob attack opportunity — runtime complete

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md
```

Runtime source `bab8689c18d894399448543d3362f1cec288f5b4`, tests/audit rc0:

```text
rob_pe_zero_targets_at_factual_sites=45
raw_attack_opportunities=16
conditional_plain_standard_opportunities=16
strict_plain_standard_opportunities=16

conditional/strict outcomes:
  attacker_fought_other=8
  pair_vcr=7
  neither_vcr=1

prior raw iscloaked:
  true:attacker_fought_other=8
  true:pair_vcr=2
  false:pair_vcr=5
  false:neither_vcr=1
```

The two `true:pair_vcr` rows are the same physical target `620694/T64/ship118`, which fights attackers134 and152. Therefore raw prior `iscloaked=true` is **rejected even as a scoped Privateer-Rob blocker**.

The eight `true:attacker_fought_other` rows are not automatically target-protection evidence: an attacker can fight a different target first and then be removed or otherwise lack a later queue opportunity.

Planets.nu documents ordinary cloak as a separate `Cloak` mission and Privateer `Rob Ship` as a separate pre-movement mission. Bird `Super Spy` explicitly attempts to cloak on cloak-capable hulls. Do not promote Privateer mission9 as cloak-generating.

## Immediate gate — Privateer Rob initial decision / target rank

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_initial_decision_audit.py
tests/test_combat_host_privateer_rob_initial_decision_audit.py
```

It refines the 16 attack opportunities using factual VCR order only after opportunity construction and compares target/factual-opponent `standard_battle_priority_key`.

Strong clean blocker shape:

```text
initial_skip_target_outranks_factual
```

This requires the attacker to participate in the first factual VCR at the site while the skipped Rob target has strictly higher STANDARD target priority than the factual opponent. No previous combat can have mutated the queue in that scope.

Known `360690/T83/ship98` is expected to be exactly this shape from the already-completed initial target audit: active264 first; target98 rank1; factual target190 rank2.

`true:pair_vcr` controls must also be classified as initial vs later. Later-attacker rows are not used to infer targetability until survivor/destruction replay is composed.

No `selection.py` or `queue.py` change before this gate.

Later C5 work: close the last initial candidate blocker; add canonical first selector; mutable survivor/destruction state; compose closed second-pass orientation; capture continuation; ship-to-planet repair boundary; planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
