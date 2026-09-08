# C5 Host combat phase — current handoff

GitHub is the only source of truth. Inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

This file is intentionally a compact pointer. Detailed evidence is in dated handoffs and Git history.

## Current objective

Reconstruct the NuHost combat phase that generates VCR engagements, queue order and left/right sides. Facts, inferred semantics and simulator rules remain separate; unknown branches fail closed.

## Stable C5 evidence

- 12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.
- Ordinary factual queue: 3,132 sites; ship combat precedes planet combat in all observed ordinary queues.
- Owner-current `T-1` is the pre-combat order source for battle turn `T`; `T` survivor state is post-combat.
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, raw `enemy = Primary Enemy`.
- Standard battle priority uses documented `001..999`; exact signed three-character FCs are a separate `CORPUS_OBSERVED + DIFF_VERIFIED` extension.
- Direct isolated standard classification remains 413/413 right-higher after C&I reclassification.
- Factual isolated C&I attacker is 7/7 right.
- Ordinary linked Priority Intercept pairs are 37/37 before regular ship combat and 37/37 with the PIA attacker on the right.
- Directed T-1 diplomacy was symmetric for both former mission-7 residuals.

## Latest completed gates

Read first:

- `docs/handoff/2026-09-09-combat-c5-source-context-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-physical-stack-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-mission7-controls-galactic-power.md`

### Former residual Case 1 — 511506 / T19 / VCR13

Not a clean two-ship physical stack. Additional owner5 Meteors and an owner6 ship survive at the battle coordinate. This row is removed from pairwise standard-side tuning and belongs to dynamic multi-ship eligibility / target selection / cloak-state reconstruction.

### Former residual Case 2 — 621896 / T28 / VCR67

Matched-control runtime on source `b1335ea6032a356c12be13be2c4fdb8cbc46b011` completed successfully:

```text
candidate_rows: 41
controls: 40
standard relation:
  right_higher_priority: 40
  left_higher_priority:   1
exact Case-2 order shape:
  right_higher_priority: 2
  left_higher_priority:  1
no-T-extra-survivor subset:
  right_higher_priority: 30
  left_higher_priority:   1
```

The only left-higher contradiction in every relevant slice is the target Gorbie/T-Rex row. Therefore no universal non-cloakable Intercept side override is supported.

Primary Planets.nu documentation supplies the missing specific mechanic: **Galactic Power** forces an Evil Empire-owned Gorbie to fight from the left-hand side, with no special mission or FC required. It is active in new Standard games and optional/disabled-by-default in Campaign.

Target identity exactly matches the documented race/hull signature:

```text
owner race 8 = Evil Empire
hull 70      = Gorbie
factual side = LEFT
```

Evidence status now:

```text
Galactic Power mechanic:             DOCUMENTED
Case2 race/hull/factual side:         CORPUS_OBSERVED
matched-control uniqueness:           CORPUS_OBSERVED
full Galactic Power corpus boundary:  next gate
DIFF_VERIFIED promotion:              not yet claimed
```

## Canonical Galactic Power primitive

`src/planets_lab/rules/combat/order.py` now contains a fail-closed `galactic_power_forces_left(...)` primitive plus race/hull constants. It requires explicit `galactic_power_enabled` state; race8+hull70 alone is not treated as enabled because Campaign may disable the advantage.

New primitive tests and the new corpus audit are committed but not yet user-runtime-validated.

## Immediate gate

Run:

```text
tools/diagnostics/combat_host_galactic_power_audit.py
tests/test_combat_host_galactic_power_audit.py
```

The audit checks all ordinary ship-vs-ship Gorbie appearances, owner-race boundaries, captured/non-Empire negative controls, dual-Gorbie ambiguity, standard-order override cases, and bounded game/player advantage metadata where exposed. It does not invent Campaign enablement.

## Next order

1. close Galactic Power boundary and integrate forced-left into the Host side-assignment layer only with explicit effective advantage state;
2. move Case 1 into dynamic multi-ship opponent selection / cloak eligibility;
3. resolve matching-FC / Harmonic Weapon Modulation boundaries;
4. integrate PIA/C&I pair selection;
5. handle capture/reinsertion and ownership changes;
6. place between-phase repair before ship-vs-planet combat;
7. keep game `591478` separate.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct. Do not merge or mark PR #28 ready yet.
