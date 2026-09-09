# C5 Host combat — matching Friendly Code / HWM gate pending — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` is reported separately and must not tune ordinary mechanics.

## Preceding closure

The two former mission-7 `left_higher_priority` residuals are no longer standard-priority residuals:

```text
511506/T19/VCR13 -> documented reciprocal Priority Intercept pair/pre-standard phase
621896/T28/VCR67 -> documented Galactic Power forced-left Gorbie
```

See:

- `docs/handoff/2026-09-09-combat-c5-reciprocal-priority-intercept-runtime.md`
- `docs/handoff/2026-09-09-combat-c5-galactic-power-case2-closed.md`

## Primary documented matching-FC rules

Planets.nu documents:

1. ship-vs-ship combat is normally suppressed when both ships have the exact same case-sensitive Friendly Code;
2. ship Friendly Codes `MKT`, `NTP`, and `LFM` are exceptions and do not prevent combat even when the exact FCs match; special-code recognition is case-insensitive;
3. Bird Harmonic Weapon Modulation (HWM), when effectively enabled, allows combat against another player's ship with the same FC and makes the other ship fight without shields;
4. HWM is disabled by default / Campaign-researchable rather than a generic Standard capability.

Primary references:

```text
https://help.planets.nu/friendly-codes
https://help.planets.nu/adv-harmonic-weapon-modulation
https://help.planets.nu/battle-order
https://help.planets.nu/RaceSheetPlus
```

## Canonical primitives — committed, pending runtime

New module:

```text
src/planets_lab/rules/combat/eligibility.py
```

Functions:

```text
matching_ship_friendly_code_blocks_combat(...)
harmonic_weapon_modulation_applies(...)
```

The matching-FC helper is tri-state/fail-closed. It separates exact FC equality from effective Bird HWM state and never infers Campaign advantage activation from race alone.

Regression module:

```text
tests/test_combat_eligibility.py
```

Do not label these primitives `TESTED` before user runtime.

## Positive factual-VCR audit — committed, pending runtime

Added:

```text
tools/diagnostics/combat_host_matching_fc_hwm_audit.py
tests/test_combat_host_matching_fc_hwm_audit.py
```

This first gate deliberately uses **positive factual VCRs only**. It does not infer suppression from absence of combat.

For each ship-vs-ship VCR whose aligned owner-current T-1 Friendly Codes match exactly, it reports:

- ordinary vs special game591478 scope;
- `documented_ship_exception` vs ordinary exact match;
- matching FC;
- owner race on both sides;
- factual VCR start shield on both sides;
- site VCR index / whether this is the first ship combat at the site;
- a bounded HWM observation label.

The strongest factual HWM signature is:

```text
non-special matching FC
not MKT/NTP/LFM
one side is Bird
factual VCR exists
opponent starts first site VCR at shield=0
```

A Bird/non-special matching-FC VCR is only an HWM candidate until effective advantage context is resolved; no Campaign state is invented.

## Why suppression-by-absence is deferred

A missing VCR is not by itself matching-FC evidence. A clean suppression control must also establish post-move co-location, fuel, hostility, diplomacy, cloakability/state and absence of other engagement blockers. That negative-control audit will be built only if the positive factual gate leaves a material unresolved boundary.

## Runtime gate

Run only:

```text
tests/test_combat_eligibility.py
tests/test_combat_host_matching_fc_hwm_audit.py
tools/diagnostics/combat_host_matching_fc_hwm_audit.py
```

Inspect especially:

```text
matching_fc_vcr_rows
ordinary.matching_fc_kind
ordinary.hwm_observation
special_591478.matching_fc_kind
special_591478.hwm_observation
hwm_candidate_rows
hwm_unshielded_first_site_rows
```

If ordinary matching-FC VCRs are entirely explained by MKT/NTP/LFM, that is clean positive evidence for the documented exception boundary but not yet a differential proof of suppression. If a non-special Bird ordinary-exact-match VCR appears, inspect shield/game context before any HWM promotion. If HWM candidates exist only in game591478, keep them in the special/campaign bucket.
