# Classic PBP priority builds: uncontested, one-base phase

Date: 2026-10-21; builds on merged #259–#260.

Official [Priority Build Points](https://help.planets.nu/queue-pbp) documentation specifies a **21-PBP threshold** to be considered for priority builds. A normal starship's priority cost is **one PBP per 50 KT (or fraction) of hull mass, capped at 20 PBPs**. The priority queue is distinct from the persistent standard build pointer in #259, and priority builds spend PBPs whereas standard builds generally do not.

\`src/planets_lab/sim/classic_uncontested_priority_pbp.py\` implements ONLY a single unquestionably uncontested Classic priority build as a **phase-intermediate state**, not a full Host turn. It requires a complete externally asserted roster of bases (with explicit queued/not-queued records), exact PBP count for every declared player, and:
- Exactly one player has at least 21 PBPs. Any other eligible player ABSTAINS (the real ordering depends on PBP ranking/ties).
- Exactly one base owned by that eligible player has a priority-capable queued ship. Any second queued base for that player ABSTAINS (no pbN ordering or circular priority substitution is attempted).
- No pbN codes, cloning, other priority actions, combat/movement or custom rules; the caller must explicitly assert the first precombat priority subphase.
- At least one free ship slot under the strict Classic hard limit, plus a complete canonical fleet roster. The model chooses the lowest free ship ID, but that is **not independently witnessed**.
- Complete typed warehouse and hull-rights inputs; the existing #256–#257 independent exact material+ship auditor is reused. All costs use the same static NuStaticSpecs catalog and cloned state.

The resulting model-phase state includes exactly one new ship, the exact purchased resource cost, remaining warehouse, and the updated per-player PBP balances. The original state and asserted balances are unchanged. Any unsupported order, tie, PBP balance, wrong owner, missing/extra base, insufficient material, missing ID, or invalid hull mass ABSTAINS without partial outputs.

## Critical evidence boundary

This is not a full Classic PBP priority queue: it **does not** rank simultaneous eligible owners, process pbN tie orders, select multiple priority builds, or model the middle-stage PBPs and prior/post-combat ordering. The absolute queue selection, initial PBP balances, real ship IDs and Host timing are caller assertions and retain explicit false verification flags.

The next bounded step is to integrate the PBP cost/unique-candidate stage with the separate #260 standard-pointer selector on the same explicit queue state; model the sequence as priority subphase then standard subphase, with a shared hard ship cap and separate PBP/pointer ledgers. Do not assume a priority build advances the standard pointer.

No public100/fresh32 entity reads, CURRENT changes, combat/C5, production IntelBoard or signed PlayerOrders schema changes. External accepted-order causality remains parked in [#247](https://github.com/Numillyash/planets-lab/issues/247).
