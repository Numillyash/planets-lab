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

Only two broad initial residuals remain and both choose the correct active ship:

```text
360690/T83: active264; extra target98; factual target190
511506/T94: active496; extra target202; factual target332
```

Do not invert target ordering.

## Initial blocker evidence

Fuel runtime `docs/handoff/2026-09-10-combat-c5-initial-standard-target-fuel-runtime.md` rejected zero fuel for the two original residuals.

Cloak attribution runtime `docs/handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md` split them:

```text
ship202: Bird race3 + Red Wind hull47 + mission9/Super Spy + cloak-capable + fuel sufficient
         => strong scoped effective-cloak candidate
ship98:  Privateer race5 + Meteor hull46 + mission9/Rob + raw prior iscloaked=true
         => separate state problem; Rob is not Super Spy
```

Bird ship202 stays separate. Privateer ship98 is the active investigation.

## Privateer Rob population / attack opportunity — runtime complete

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-population-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-vcr-control-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-runtime.md
```

The site-conditioned attack-opportunity runtime produced 16 strict/conditional plain-STANDARD opportunities:

```text
prior true:  attacker_fought_other=8, pair_vcr=2
prior false: pair_vcr=5, neither_vcr=1
payload_conflicts=0
```

Raw T-1 `iscloaked=true` is rejected as a blanket or direct scoped blocker. Later-attacker rows are not used to infer targetability until mutable survivor/destruction state is composed.

## Privateer Rob initial-decision rank — runtime complete

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md
```

Runtime source `7cb29984bc09b241241a8e738f6b6701bc61d5b4`, tests/audit rc0:

```text
opportunities=16
initial_pair_vcr=5
initial_skip_target_not_above_factual=5
initial_skip_target_outranks_factual=3
attacker_no_factual_vcr=1
later_pair_vcr=1
noninitial_attacker_context=1
payload_conflicts=0
```

All three clean `initial_skip_target_outranks_factual` rows have prior `iscloaked=true`:

```text
360690/T83 ship98  vs attacker264
360690/T57 ship46  vs attacker146
360690/T57 ship280 vs attacker146
```

No previous VCR can explain these skips. They are genuine missing precombat eligibility/state residuals.

Two sites provide strong matched visible controls:

```text
360690/T83:
  Meteor98  mission9/PE0 prior true  -> skipped
  Meteor190 mission9/PE0 prior false -> factual [190,264]

360690/T57:
  Meteor46  mission9/PE0 prior true  -> skipped
  Meteor280 mission9/PE0 prior true  -> skipped
  Meteor293 mission9/PE0 prior false -> factual [146,293]
```

The only clean prior-true initial fought control is:

```text
620694/T64 Meteor118 mission9/PE0 prior true -> factual first pair [118,134]
T-1 fuel=5
```

Therefore the next question is not target rank; it is whether ship118 had a documented decloak state transition that the three skipped targets did not.

## Immediate gate — clean prior-true cloak/de-cloak context

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-cloak-context-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_initial_cloak_context_audit.py
tests/test_combat_host_privateer_rob_initial_cloak_context_audit.py
```

It derives exactly the prior-true clean initial skip/control population from the tested initial-decision audit and reports:

```text
T-1 damage/fuel/mission/origin
reference normal-move fuel use and remaining raw fuel
visible foreign ships at Rob origin (fuel-gain uncertainty)
Loki hull7 <=19% damage within 10 ly at T-1 origin
T Loki proximity as attribution-only evidence
stable target T fuel/damage/iscloaked where available
```

Strong discriminator sought:

```text
three skipped targets: no documented decloak context
ship118 fought control: exact fuel exhaustion with no Rob fuel source, Loki, or another bounded documented decloak cause
```

Do not promote mission9 as cloak-generating and do not copy archive `iscloaked` into `selection.py`. If ship118 is not explained by this narrow gate, expand only the documented decloak attribution needed by the control (ion/mine/glory/etc.).

Later C5 work: close Bird ship202 and Privateer ship98 blocker state; add canonical first selector; mutable survivor/destruction state; compose closed second-pass orientation; capture continuation; ship-to-planet repair boundary; planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
