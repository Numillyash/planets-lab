# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This file is now intentionally a compact current pointer rather than a duplicate historical transcript. Detailed prior C5 evidence remains in the dated handoffs and Git history.

## Current objective

Reconstruct the NuHost combat phase that generates VCR engagements, queue order and left/right sides. Facts, inferred semantics and simulator rules remain separate; unknown branches fail closed.

## Stable C5 evidence

- 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.
- Ordinary factual queue: 3,132 sites; ship combat precedes planet combat in all observed ordinary queues.
- Owner-current `T-1` is the pre-combat order source for battle turn `T`; `T` survivor state is post-combat and must not be substituted for priority calculation.
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, raw `enemy = Primary Enemy`.
- Standard battle priority uses documented `001..999`; exact signed three-character FCs are a separate `CORPUS_OBSERVED + DIFF_VERIFIED` extension, not documented.
- Direct isolated standard classification remains 413/413 right-higher after C&I reclassification.
- Factual isolated C&I attacker is 7/7 right.
- Ordinary linked Priority Intercept pairs are 37/37 before regular ship combat and 37/37 with the PIA attacker on the right. Reverse-Ship-ID ordering remains `DOCUMENTED` only because no comparable ordinary multi-attacker site exists.
- Directed T-1 diplomacy was symmetric for both former mission-7 residuals and does not explain them.

Canonical primitives remain in `src/planets_lab/rules/combat/order.py`. Full combat eligibility is intentionally not implemented.

## Latest completed gate

Read first:

- `docs/handoff/2026-09-09-combat-c5-source-context-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-physical-stack-runtime.md`

User-operated physical-stack runtime on source:

```text
74f1d49c978a4cdd4c7222f92ff393bb9b397fb2
```

completed targeted tests and audit successfully with zero payload conflicts.

### Former residual Case 1 — 511506 / T19 / VCR13

This is **not a clean two-ship physical stack**. Although the site has one factual VCR, four owner-current ships survive at `(2565,1729)` on T and five T-1 context candidates are relevant. Extra surviving ships include owner5 Meteors 29 and 102 and owner6 hull17 ship73, in addition to factual combatant Meteor89 and Firecloud80 context.

Therefore Case 1 must not tune pairwise standard side priority. It moves to dynamic stack eligibility / target selection / cloak-state reconstruction. Its factual side order is still unexplained.

### Former residual Case 2 — 621896 / T28 / VCR67

This remains the sole strong physically-two-ship-like residual:

```text
Gorbie62 owner5 race8 hull70
  mission7 target38 PE2 FC001
T-Rex38 owner2 race2 hull23
  mission1 PE5 FCeqe damage24
```

Only Gorbie62 survives at the factual battle coordinate on T; no untracked T survivor demonstrates a larger combat stack. Ship15 shares the Gorbie's T-1 origin but does not waypoint to the battle coordinate.

Official Planets.nu static/race documentation identifies hull75 as Super Star Frigate, not Super Star Cruiser. Intercept Interference is assigned to Super Star Cruiser / Cruiser II, so ship15 is not an observed Intercept Interference source. Do not infer that ability from owner race alone.

The historical old selector still reports `180 right_higher / 2 left_higher`; preserve that count as a property of the one-VCR selector. Only Case 2 remains suitable as a clean-ish pairwise residual after physical-stack inspection.

## Immediate gate

Prepared diagnostic:

```text
tools/diagnostics/combat_host_mission7_matched_control_audit.py
tests/test_combat_host_mission7_matched_control_audit.py
```

It scans ordinary one-ship-VCR sites for structural controls where:

- a non-cloakable mission-7 ship targets the factual opponent;
- its PE matches the opponent owner;
- the opponent has reciprocal PE;
- FCs are supported and nonmatching.

It reports factual interceptor side, canonical standard relation, race/hull population, exact Case-2 order shape (`001` versus symbolic non-Kill), broader numeric-versus-symbolic controls, and bounded T extra-survivor context.

Do not infer an Intercept-specific side rule from counts alone. A zero T extra-survivor count is only a cleanliness signal, not proof that no third ship existed earlier in Host.

## Next order after matched controls

1. decide whether Case 2 is unique/special context or belongs to a reproducible non-cloakable targeted-Intercept side population;
2. move Case 1 into dynamic multi-ship opponent selection / cloak eligibility;
3. resolve exact matching-FC / Harmonic Weapon Modulation boundaries;
4. integrate PIA/C&I pair selection into dynamic queues;
5. handle capture/reinsertion and ownership changes;
6. place between-phase repair before ship-vs-planet combat;
7. keep game `591478` sequence semantics separate.

## Evidence discipline

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. No combat rule, FC parser, PIA eligibility condition or `DIFF_VERIFIED` status was changed by the source-context or physical-stack gates.
