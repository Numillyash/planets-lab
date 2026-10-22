# PR #270 — late PPQ integer Stage-1: audited ten-ship economic turn

Date: 2026-10-22. Implements `src/planets_lab/sim/late_ppq_integral_stage1_economy.py`. **TESTED conditional model only**, not real NuHost evidence.

## Contract and capacity

The new `simulate_integral_ppq_stage1_economic_turn` reruns the #269 `quote_integral_ppq_regular_stage1` from full before-state and exact complete queue roster. No relaxed case is added for fractional quotas or Stage 2/3 lotteries. Only when every quota is an integer and every selected owner has enough queued eligible bases with an unambiguous RB/heaviest-hull cutoff does the selector yield exactly N selected base IDs. `N=max(10,soft_cap-current_ship_count)`, and Stage 1 may intentionally build past the **soft cap**. See [PPQ help](https://help.planets.nu/queue-ppq) (minimum ten builds even when crossing configured soft limit).

The builder additionally requires an explicit complete `PPQWarehouseBase` for **every** starbase (including idle and unselected queued bases) with independent component warehouses, blueprint and permissible hull rights for all queued bases, and a separate caller-asserted unique new Ship ID **for every selected base only**. The assigned ID **set** must equal the N smallest available IDs from 1..999. The identity assignment is NEVER claimed to be NuHost order. Each queued hull's catalog mass must match the stage-one candidate's asserted mass. Unselected bases cannot secretly build or consume inventory.

The underlying old component assembler has a purely technical `global_ship_limit=999` prelimit admission check. We use this as the absolute PROGRAMMATIC Ship-ID ceiling, **not** as the PPQ soft cap and not as queue or phase proof. Each selected ship has a checked independent hull/engine/weapon demand, warehouse draw/purchase component ledger, source MC/mineral debit, exact fully typed new-ship identity; all old ships and all bases are unchanged. Validate all planet economic resources/events after reversing only purchased components, through the intact **14 economy phases**. Compare two caller hypotheses: builds before or after economy. Complete owner PP ledger is unchanged: selected normal queued builds spend zero PP; no idle-base PP earnings or external PP sources are modeled in this subcase.

## All-or-nothing

Unknown planet or game modifier, custom PP scheme, priorities, cloning, mining stations, movement/combat, id ambiguity, any incomplete owner/ship/base/warehouse inventory, forged receipt, lost event, physical resource shortfall, unmatched owner/hull/mass or unsupported phase causes whole turn `ABSTAIN_LATE_PPQ_STAGE1_ECONOMIC_TURN` with no partial modeled state, purchased inventory or PP sidecars. All source inputs must remain immutable.

Tests include a fictional **12:8 owned-planet** split, 19 old ships and soft cap 20, exact 6:4 selected bases and **ten new ships 20..29** (fleet 29), two economy placements, swapped caller ID attribution, fully pre-stocked zero resource debit, 31 unsupported cases, adversarial Host result mutations. The synthetic fixtures do **not** prove NuHost's actual selected bases, RNG, ID permutation or correct host-time placement.

## Next independent slice

Separate late **PQ** normal queue selection (random choice must be passed as an EXTERNAL caller-selected slot or independently authenticated Host selection) composed with ship BOM+warehouse+14-phase economy. Later consider PPQ owner share fractional rounding Stage 2/3, multi-turn PPQ carry and movement/cargo link. Do not mine sealed heldout32, rebuild public100, alter CURRENT public68, touch unrelated C5 or production IntelBoard, or change signed V1/V2 orders. Accepted Host causal evidence remains issue #247.

Every later PR must include **all** of a fresh full `docs/CONTINUE_HERE.md`, `docs/PR_CHANGELOG.md` with actual PR number, and substantive docs before final PR CI; recheck main after merge.
