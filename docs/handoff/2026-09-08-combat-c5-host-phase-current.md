# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

This is the compact current pointer; dated handoffs contain full evidence and runtime details.

## Stable C5 layers

- corpus: 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts;
- owner-current `T-1` is the precombat order/state source; `T` is post-Host/postcombat state and same Ship ID is not automatically the same physical ship because later construction can reuse open IDs;
- mission 3 = Kill!, mission 7 = Intercept, mission 20 = Bird Cloak and Intercept, raw `enemy` = Primary Enemy;
- direct isolated ordinary STANDARD relation: 413/413 higher static priority on RIGHT;
- normal PIA linked population: 37/37 before regular combat and 37/37 attacker RIGHT;
- isolated C&I factual attacker: 7/7 RIGHT;
- deterministic pair composition in `src/planets_lab/rules/combat/selection.py`: `TESTED`;
- plain STANDARD repeated-pair second-pass reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; static priority remains unchanged.

Do not reopen Galactic Power Case2, reciprocal PIA, matching-FC, diplomacy, physical-stack or repeated-pair gates absent a direct contradiction. Do not weaken Friendly Code parsing or standard Combat Priority to fit queue residuals.

## Position checkpoint

Read:

```text
docs/handoff/2026-09-09-combat-c5-normal-movement-position-v3-runtime.md
docs/handoff/2026-09-09-combat-c5-unresolved-movement-context-runtime.md
```

Repaired storm-aware v3 runtime source `14ebd6442b6ca705c42c2c5ff4a4e5a2d9b1240c`:

```text
ship occurrences: factual=3204 predicted=1810 exact=1806 mismatch=4 uncovered=1383
factual pairs:     total=1986 exact=678 mismatch=4 unresolved=1304
sites:             total=1220 fully position-exact=346 mismatch sites=4
payload_conflicts=0
storm modes: false=10 true=1
```

Six classic-ion-storm residuals are independently exact. Two remaining rows are DIFF_VERIFIED stochastic normal-mine hits and two remain bounded unresolved; no factual endpoint is injected into the predictor.

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

## Initial plain STANDARD target-order runtime

Read `docs/handoff/2026-09-10-combat-c5-initial-standard-target-runtime.md`.

Runtime source `d7ade79d1344ba21a99f21d3fcc2d3e911dff3c3`:

```text
conditional exact-set: sites=169 first_pair_exact=169 first_right_exact=169
strict exact-set:      sites=162 first_pair_exact=162 first_right_exact=162
exact-set informative target-order sites: 15/15 target rank 1
```

Strongly supported when the eligible set is correct:

```text
first active ship = highest standard Combat Priority ship having an eligible target
first target      = highest-priority eligible target for that active ship
```

Only two broad residuals remain; both already choose the correct active ship and have the factual target eligible:

```text
360690/T83: active264; reconstructed extra target98; factual target190
511506/T94: active496; reconstructed extra target202; factual target332
```

Do not invert target ordering from these rows.

## Residual blocker checkpoints

Fuel runtime `docs/handoff/2026-09-10-combat-c5-initial-standard-target-fuel-runtime.md` rejected zero fuel:

```text
ship98 postmove fuel=45
ship202 postmove fuel=29
```

Cloak attribution runtime `docs/handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md` split the residuals:

```text
511506/T94 ship202:
  owner3 -> race3 Bird
  hull47 Red Wind can cloak
  mission9 Super Spy signature
  T-1 iscloaked=true; fuel sufficient
  T same owner/hull and iscloaked=true
  => strong scoped effective-cloak candidate

360690/T83 ship98:
  owner5 -> race5 Privateer
  hull46 Meteor can cloak
  mission9 / Rob
  T-1 iscloaked=true; fuel45
  T same owner/hull and iscloaked=true; fuel40
  => raw state persistence, not yet combat-effective cloak
```

Factual `511506/T94/ship332` is the key negative control: it also has T-1 `iscloaked=true`, current mission2, and VCR728 occurs. Raw T-1 `iscloaked` is rejected as a blanket blocker.

## Privateer Rob raw-cloak population — runtime complete

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-population-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-vcr-control-runtime.md
```

Runtime source `e0b7f9ac91f99e8006546b80ec4a940ab21e2a6e` plus control extraction source `6ef2c9344b1544a7e60952db50e1d942e352e53e`:

```text
candidate_rows=2223
stable_identity=2174
stable_vcr_participant=2
stable_no_vcr=2172
before_cloak_true=1433

stable transitions:
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

The exact residual `360690/T82->T83/ship98` is a stable PE=0 `true_to_true`, no-VCR row and is typical of this population.

The only two stable Privateer mission9 VCR participants are:

```text
511506/T15 ship89:  PE=6,  true_to_true, VCR7 vs owner6
511506/T22 ship157: PE=11, true_to_true, VCR25 vs owner11
```

Both can initiate combat through their own Primary Enemy. Therefore neither is a PE=0 hostile-targetability counterexample.

Interpretation boundary:

- Privateer mission9 archive `iscloaked` persistence is `CORPUS_OBSERVED + TESTED`;
- there are zero stable prior-cloaked PE0 VCR participants in this population (`CORPUS_OBSERVED`);
- this still does not prove combat-effective cloak because most no-VCR rows do not prove a hostile attack opportunity;
- current Planets.nu Host documentation keeps Cloak and Rob as separate Host steps;
- do not promote Rob as cloak-generating and do not copy raw T-1 `iscloaked` into pair eligibility.

## Immediate gate — site-conditioned Rob attack opportunity

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-attack-opportunity-pending.md
```

Diagnostic:

```text
tools/diagnostics/combat_host_privateer_rob_attack_opportunity_audit.py
tests/test_combat_host_privateer_rob_attack_opportunity_audit.py
```

Require:

```text
ordinary factual battle site
Privateer race5 target
mission9 / Rob
cloak-capable hull
PE=0
target + opponent independently position-resolved at site
opponent Kill!/PE requests combat against Privateer owner
target does not request combat back
canonical conditional pair decision = eligible plain STANDARD
```

Strict scope additionally requires independent diplomacy permission for the attacker's direction.

Key outcome classes:

```text
pair_vcr
attacker_fought_other
target_fought_other
both_fought_other
neither_vcr
```

Known residual must appear as:

```text
360690/T83 target98 / attacker264
prior iscloaked=true
conditional plain-STANDARD opportunity
factual outcome=attacker_fought_other
factual pair [190,264]
```

Any `prior cloak=true + PE0 + pair_vcr` row is a direct counterexample to a blanket raw-bit blocker and must be inspected before promotion. The strongest positive blocker evidence is `prior cloak=true + attacker_fought_other + target skipped`, especially when strict diplomacy is independently resolved.

No `selection.py` or target-order change before this gate.

Later C5 work remains: close the last initial candidate blocker, add canonical initial selector, mutable survivor/destruction state, second-pass composition, capture continuation, ship-to-planet repair boundary, then planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.
