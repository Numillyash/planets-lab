# Core public corpus mainline — external evidence deferred, standard construction next

Date: 2026-10-20. The intent is to **finish useful standard mechanics** before requesting any further owner-driven Planets.nu experiments. The long chain of M2 passive-save, signed-owner and local synthetic audits is now bounded; it is not itself independent Host execution.

## Separate what is already complete

- **Public corpus ingestion/storage:** exact semantic parity `224014/224014` archived perspective members across **100 games**, with 541348959 typed entity rows, 26.65 GiB immutable compact generation `corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb` and SHA256 `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`. This does **not** mean all mechanics are verified. The normal `CURRENT` remains public68; do not activate public100 just to clear this workstream.
- **M2 observable stock coverage:** baseline68 frozen selection `b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f`; 136 perspective transitions, 3769 same-owner comparable planets. Observed changes by family: MC/supplies 3670, surface minerals 3631, ground minerals 1467, populations 2605, structures 1795, combined tax/happiness 716. These are co-observed net changes, not authenticated orders.
- **Mineral descriptive residual context:** 13023 comparable planet×mineral rows with 11813 both modeled surface/ground exact, 915 only ground exact, 33 only surface exact, 262 neither exact. The 915 belong to 315 distinct planet transitions. 108 mineral comparisons show opposite same-site cargo candidates; just 65 planet transitions have at least one candidate, not independent Host transfer proof.
- **Important holdout nuance:** all fresh32 were already opened for an earlier **capture-side prospective combat candidate** that failed. However fresh32 entity states remain excluded from M2 baseline sampling. Therefore do not label them universally untouched, nor open them for M2 posthoc tuning without a preregistered evaluation plan.

## Parked studies and exit criteria

**Tracking issue [#247](https://github.com/Numillyash/planets-lab/issues/247)** contains the complete list. In particular: independently accepted all-player orders; trustworthy external Host clock and complete pre/post source; M2 cargo/tech phase ordering; C5 prospective post-capture side case; and long-tail Chunnel/Horwasp. Reopen only with a concrete discriminative protocol and genuinely available evidence. Do not treat success-shaped client saves or local HMAC as server receipts.

## Current mainline stage: standard planet structures

The standard Host model already has factory supply, tax, growth and mineral phases but **not explicit construction of mines, factories and planetary defense posts**. The published baseline68 corpus observes a structure-family net difference in 1795/3769 matched planet transitions, making this a material gap. The correct next deliverable is a **separately bounded standard-rule construction calculation**, not to fit or invent unobserved historical player orders.

Official Planets.nu references:

- https://help.planets.nu/planetary-structure-building: each structure costs 1 KT supplies, with standard additional MC costs **mine 4, factory 3, defense 10**.
- https://help.planets.nu/planetary-structure-details: population-dependent construction limits `100 + floor(sqrt(clans - 100))` for factories above 100 clans; `200 + floor(sqrt(clans - 200))` for mines above 200; and `50 + floor(sqrt(clans - 50))` for defense above 50. For lower populations, the corresponding limit is clan count.
- https://help.planets.nu/map-planet?mobile=true: target construction order is defense, factories, then mines; available supplies may be sold for MC if the player runs short of credits. The current **v1 does not attempt the supply-sale or partial funding branch**.

`src/planets_lab/sim/standard_structure_build.py` adds a pure, no-side-effects **fully funded, no-conversion** conditional calculator. It requires known owner, complete numeric resources/clans, valid starting counts, positive or unchanged explicit targets, target<=documented caps, and explicit standard-rule assertion. It debits only supplies and MC for requested positive increments. If any part is outside this bounded standard case, it ABSTAINS without a partial result. Tests cover cap thresholds, mixed costs, untouched inputs, low supplies/credits, downgrade, unsupported owner and unasserted rule eligibility.

This is `DOCUMENTED` for public cost/cap arithmetic and `TESTED` for its local conditional implementation, **not `DIFF_VERIFIED`** for Host outcome timing, partial build ordering, implicit supply-to-cash selling, race/campaign modifiers or owner instructions. There is intentionally **no immediate integration into the canonical 14-phase Host pipeline**, since its exact phase placement relative to production and tax is not yet independently established. A later implementation can introduce explicit opt-in placement and authoritative orders without compromising the current baseline.

## Subsequent autonomous milestones (no player action)

1. Document standard **structure priority, capacity and partial-funding policy**, implement them only when scope and ordering can be stated without inventing unrecorded orders; use pure deterministic test inputs.
2. Add an explicit, bounded structure order to the *research* order-aware slice behind an opt-in placement, with supply/MC conservation ledger; avoid silently treating an unchanged archived structure field as proof of no player order.
3. Extend public68 *observational* structural-change coverage using the already frozen metadata cohort only if there is a new predeclared measure that existing published aggregates cannot recover; never call this causal reconciliation.
4. Maintain ordinary movement and combat C2/C3/C4 regression closures, keep C5 nonstandard mechanics frozen. Prepare one integrated standard turn contract where all unsupported phases ABSTAIN.

Do **not** schedule another 26.65 GiB corpus scan, unseal fresh32 for M2, alter `CURRENT`, upload user HAR, or ask for deliberate game moves at this checkpoint.
