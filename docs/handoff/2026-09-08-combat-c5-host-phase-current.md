# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft/open and must not be merged or marked ready without explicit instruction. Game `591478` remains isolated from ordinary promotion.

Progress overview: `docs/handoff/2026-09-11-reverse-progress-assessment.md`.

Planning estimate only: combat mechanics knowledge C1-C5 ~70-80%; independently reconstructed ordinary ship-combat candidate coverage ~20-25%; whole NuHost roadmap ~40-50%.

## Stable C5 layers

Do not reopen absent a direct contradiction:

- deterministic pair composition in `src/planets_lab/rules/combat/selection.py`: `TESTED`;
- direct ordinary STANDARD priority: 413/413 higher static priority on RIGHT;
- normal PIA: 37/37 before regular combat, attacker RIGHT 37/37;
- isolated C&I attacker: 7/7 RIGHT;
- scoped Galactic Power Case2, reciprocal PIA and matching-FC closures;
- plain STANDARD repeated-pair second-pass side reversal: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- owner-current `T-1` is the precombat order/state source;
- static STANDARD Combat Priority and Friendly Code parser remain unchanged.

`T` is post-Host/postcombat. Same Ship ID at T is not automatically the same physical ship because construction may reuse a freed ID.

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

No candidate-covered factual pair is conditionally hard-blocked.

## Initial STANDARD target-order checkpoint

```text
conditional exact-set: 169/169 first pair exact; 169/169 RIGHT exact
strict exact-set:      162/162 first pair exact; 162/162 RIGHT exact
informative exact-set target-order controls: 15/15 rank1
```

Strongly supported when the eligible set is correct:

```text
first active ship = highest STANDARD Combat Priority ship with an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not invert target ordering.

The two original broad initial mismatches were:

```text
360690/T83: active264; extra98; factual190
511506/T94: active496; extra202; factual332
```

Both now have independent evidence-scoped blocker explanations.

## Privateer Rob blocker — CLOSED at scoped targetability boundary

Read:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-initial-decision-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-state-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-fuel-attribution-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-effective-cloak-threshold-runtime.md
docs/handoff/2026-09-11-combat-c5-privateer-rob-selector-impact-runtime.md
```

Evidence-scoped state:

```text
Privateer race5 + mission9 Rob + ordinary cloak-capable hull:
  prior false                         -> not effectively cloaked
  prior true + fuel <= reference cost -> not effectively cloaked
  prior true + fuel >  reference cost -> effectively cloaked
  advanced cloak                      -> unresolved / fail closed
```

Queue-decisive differential:

```text
opportunities=16
decisive_rows=8
decisive_match=8
decisive_mismatch=0
decisive_unresolved=0
expected blocked -> candidate blocked: 3/3
expected eligible -> candidate eligible: 5/5
```

Selector-impact differential:

```text
overlay_rows=16
overlay_blocked=7
overlay_eligible=9
blocked_factual_pair_rows=0
potential_first_selector_regression_rows=0
privateer_residual_profiles_projected_fixed=2/2
bird_residual_profiles_overlay_affected=0/2
```

Evidence status:

```text
Privateer Rob ordinary-cloak targetability:
  CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

universal Rob fuel-consumption causality:
  REJECTED

raw prior iscloaked as blanket blocker:
  REJECTED
```

Helper:

```text
src/planets_lab/rules/combat/effective_state.py
```

This establishes a **directional ordinary-STANDARD targetability effect**, not a symmetric blanket pair-combat ban.

## Bird Super Spy blocker — CLOSED at focused targetability boundary

Read:

```text
docs/handoff/2026-09-10-combat-c5-initial-standard-target-cloak-residual-runtime.md
docs/handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-pending.md
docs/handoff/2026-09-11-combat-c5-bird-super-spy-cloak-context-runtime.md
```

Runtime source:

```text
6cf47de46fadcbe1619c6a6eee5731d51866c12e
```

Targeted tests: 21 passed.

Focused residual:

```text
game 511506 / T94
active 496 owner5/race5 Bloodfang
extra  202 owner3/race3 Red Wind, mission9 Super Spy
factual 332 owner3/race3 Resolute, mission2
```

Ship202 resolved:

```text
Bird race3
ordinary cloak-capable Red Wind
mission9 Super Spy
damage=0
fuel=37
ordinary reference cloak cost=5
prior iscloaked=true
reference normal move: warp9, distance 52.153619..., fuel_used=8, remaining=29
ion storm start inside=False
planet Super-Spy Ion Pulse possible=False
Loki start exposure=False
active POP/TRG Glory=False
T same owner/hull and iscloaked=true (attribution only)

documented_effective_cloak_supported=True
reason=documented_super_spy_ordinary_cloak_supported
```

Matched factual control ship332:

```text
Bird Resolute
Advanced Cloak hull
mission2, not Super Spy
prior iscloaked=true
factual VCR with ship496 occurs

documented_effective_cloak_supported=None
reason=outside_super_spy_scope
```

Runtime summary:

```text
focus_row_found=True
archive_found=True
race_conflicts=0
extra_ship_documented_effective_cloak_supported=True
factual_ship_documented_effective_cloak_supported=False
raw_prior_cloak_control_separates=True
```

Evidence status:

```text
focused Bird Super Spy ordinary-cloak targetability blocker:
  DOCUMENTED + CORPUS_OBSERVED + TESTED

raw prior iscloaked as blanket blocker:
  REJECTED

generic Advanced Cloak combat-state reconstruction:
  UNRESOLVED
```

Official documentation basis:

```text
https://help.planets.nu/mis-super-spy
https://help.planets.nu/mis-cloak
```

The diagnostic additionally fails closed for visible ion-storm, Super-Spy planet Ion Pulse, Loki and active Glory decloak contexts.

## Immediate gate — directional STANDARD targetability composition

Both original broad blockers are now closed independently. Do **not** special-case ship IDs.

Next objective:

1. compose the evidence-scoped Privateer and Bird effective-cloak states as **directional STANDARD targetability**;
2. keep pair eligibility, PIA/C&I and other pre-standard phases separate;
3. apply the targetability projection to every reconstructed relevant target opportunity, not only the two historical residual IDs;
4. rerun the initial STANDARD selector differential;
5. require all previously exact first selectors to remain exact;
6. require zero factual-pair blocking regressions and zero first-selector regressions;
7. require both original residuals to project fixed in every comparable strict/conditional profile;
8. unresolved/out-of-scope state must fail closed and must not silently block combat.

Only after that gate passes should the canonical first STANDARD selector be promoted.

Later C5 work: mutable survivor/destruction state; second-pass orientation in the mutable queue; capture continuation; ship-to-planet repair boundary; planet/base participation.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Unknown branches fail closed.