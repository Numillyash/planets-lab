# PR #290 — isolated standard minefield natural decay: rule implementation and uncertainty

Date: 2026-10-24. This is the next independent standard-mechanics workstream after [the six-game PPQ observational closure](2026-10-23-pq-public-observational-closure-host-readiness-v1.md), NOT a reopening of PPQ evidence or human-dependent Host issue #247.

## Authoritative documented rules

Sources: [Planets.nu Minefields → Mine Decay](https://help.planets.nu/minefields), [Default Configuration → Mines and webmines](https://help.planets.nu/default-config), [Dense Minefields](https://help.planets.nu/adv-dense-minefields). The official minefield page states both regular and web minefields decay by a little over 5% each turn, increasing to 15% when they intersect a Nebula. The published formulas are:

```text
non-Nebula: new_units = round(old_units * 0.95) - 1
Nebula:     new_units = round(old_units * 0.85) - 1
integer radius = floor(sqrt(new_units))
```

For an exhausted field use a zero-unit terminal result and remove that field from the next *isolated* roster, rather than propagating negative mines. Max ordinary radius is 150 LY (22,500 mine units); the documented reduced maximum is 100 LY (10,000 units) in appropriate Campaign games. Dense-minefield advantages can increase density and decay, so they must not be processed under these ordinary rules.

**Rounding uncertainty:** The rule documentation names `round()` but does not explicitly specify the tie-breaking mode at exact `.5`. Python `round()` chooses bankers rounding; assuming it matches NuHost would be unsafe. This module uses exact integer arithmetic for unambiguous fractions, explicitly `ABSTAIN`s on exact half-integer retention, and never fabricates a Host-specific tie decision. Example: old units 10 → documented retained 9.5 before subtraction → ABSTAIN; old units 100 → 94 normal, 84 Nebula. This is a limitation, NOT a claim that NuHost itself abstains.

## Implementation and contracts

`src/planets_lab/rules/mine_natural_decay.py` exports immutable data structures `MinefieldState`, `NaturalDecayEvent`, `NaturalDecayTurn`, `NaturalDecaySequence`, and pure function `simulate_isolated_natural_mine_decay(...)`, guarded by `MineDecayAbstain`.

- Source roster must be **complete and explicitly supplied** (list/tuple), with unique positive integer field IDs, positive owner IDs, positive integer units and exact Boolean `is_web`. No implicit conversion of bool/string to integer. Roster sorted by field ID for deterministic event order; neither source objects nor input containers are mutated.
- Exact per-field Nebula intersection map required, Boolean values with exact roster ID set. In 1–12 isolated turns, current Nebula status is assumed **unchanged** (static field positions and Nebula context, not dynamically inferred geometry). Missing, unknown or extraneous context ABSTAINS the entire sequence.
- Caller must explicitly set `isolated_decay_only_confirmed=True` and `standard_density_confirmed=True`. These are trusted conditional preconditions, **not independent evidence** they were true of an actual game. Normal/web fields use the same natural decay arithmetic. Only max_radius 100 or 150 accepted, and starting units may not exceed cap²; dense/custom/other mechanics are outside scope.
- Each turn emits before/after immutable field tuples and one event per active field: pre/post units, lost units, radius via integer `isqrt`, web and explicit Nebula flags and exhaustion. Destroyed fields vanish on subsequent turns. End-of-turn and entire sequence conserve `before units = after units + natural losses`; any unsupported or tie condition raises `MineDecayAbstain` atomically, **no partial result**.
- This is a stand-alone **natural decay** rule calculator, not a new global `GameState.minefields` layout nor a `HostEngine` phase. Real Host temporal ordering relative to mine laying, sweeping, scooping, mine-hit movement, minefield overlap/counter-mining, friendly code, web drain, storm/sphere features, dense campaign advantages, player diplomacy, and phase-specific Nebula membership remains UNKNOWN. The function must NOT run silently inside an end-to-end turn.
- No global random seed is required because the documented isolated rule is arithmetic; no claims about actual Host source implementation internals.

## Tests and evidence level

`tests/test_mine_natural_decay.py` covers ordinary/web parity, normal/Nebula rates, exact integer radius and depletion, conservation and immutability, deterministic order, fixed context across a bounded multitur​n calendar, max 100/150 LY, half-tie ABSTAIN, malformed/duplicate/overcap source, unknown Nebula and disallowed interaction/dense mode. Gate status is **DOCUMENTED formula + TESTED conditional** once exact-head PR CI has actually passed; no historical Host differential test or controlled accepted orders have been performed, so **NOT CORPUS_OBSERVED or DIFF_VERIFIED for this decay mechanism**.

There is no new Linux host operation in PR #290 because synthetic arithmetic tests run in CI and the current prepared public archives were not read. Consequently no extra `run-*-with-evidence.sh` is necessary **for this PR**. Every *future* on-host corpus/Host experiment must use a committed one-line `bash tools/run-*-with-evidence.sh` and existing `tools/run-with-runtime-evidence.sh`, publishing only sanitized counts/log/exit to separate `runtime-logs`; never publish private raw `.trn` or accepted player orders.

## Next bounded mechanics work

1. Once #290 CI and merge are verified, add a **separately evidenced** mine laying / sweeping or full minefield state import slice, but only after identifying reliable owner/current mine-unit inventory and field coordinates in the canonical game model and precise source stage semantics. Do not join natural decay to movement or collisions yet.
2. If evidence can distinguish tie rounding or actual Nebula membership/Host phase, predeclare a bounded discriminator and use privacy-safe runtime evidence. Until then the exact tie and phase order remain unsupported/ABSTAIN.
3. Do not touch M2 sealed heldout32, prepared public100, `CURRENT` public68, frozen PPQ completed control12, unrelated C5, production IntelBoard, private orders/issue #247. Issue #247 remains explicitly PARKED.
4. Each future PR must include a **full rewritten** `docs/CONTINUE_HERE.md` with that PR number, fresh `docs/PR_CHANGELOG.md`, a substantive docs file, exact green PR CI before merge, and postmerge main CI confirmation.
