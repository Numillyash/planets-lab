# Core: selected one-ship assembly × 14-phase planetary economy

Date: 2026-10-21. Base: #256 merged at \`2435bb27b5aed8ad0a5e338a8ffd67d1b9a21f8a\`.

## Scope of the new actual integration

\`src/planets_lab/sim/standard_ship_economy_turn.py\` composes existing \`assemble_selected_standard_ship\` with the unchanged fourteen-phase \`PlanetaryHostPipeline\`. It returns one modeled **consecutive turn** rather than the intermediate same-turn stage of #256. There are exactly two explicitly hypothetical placements:

1. \`selected_assembly_before_planetary\`: pay for available/new ship components from the initial planetary surface and warehouse, create the ship as an intermediate phase, then run the existing planet economy.
2. \`selected_assembly_after_planetary\`: run the unchanged planetary economy first, then conditionally buy the missing ship components and create the new ship from the resulting tax/mineral stocks.

The order is **not** established NuHost timing; neither state can independently witness a real build queue. Documentation explicitly distinguishes classic PBP standard rotation, PQ, PPQ and other queue systems ([Host Order of Shipbuilding](https://help.planets.nu/starbase-host), [PBP queue](https://help.planets.nu/queue-pbp), [PQ queue](https://help.planets.nu/queue-pq), [Ship Limit](https://help.planets.nu/ship-limit)). No queue-selection arbitration is implemented.

For now, a **single pre-existing ordinary starbase** is admitted; caller must provide all of:
- A selected, nonconflicting **prelimit** \`SelectedBuildSlot\`, with complete global fleet snapshot assertion and a caller-supplied unused ship ID. The one-base scope is a necessary *lack of local competition*, but it is not independent proof that the game selected this starbase.
- Exact four-component warehouse, known static hull/engine/weapons/crew and caller-asserted hull eligibility, no custom rules or game modifiers, no ion storm or active existing ship missions.
- Explicit no-other-ship-or-starbase-orders and uncontested-single-build assertions, without silently changing legacy \`PlayerOrders\` or their owner V1/V2 HMAC capture formats.

A base cannot be created and instantly build a ship through this bounded interface. That requires another explicit phase placement and future full queue admission.

## Two separate conservation ledgers

\`_audit_selected_assembly\` does not trust the implementation-reported material or warehouse counts. From original catalog, blueprint and initial inventory it independently recomputes the exact number of components drawn vs freshly purchased, their unit costs, remaining warehouse by component ID and exact new ship fields (owner, location, engine, installed weapons, crew, empty cargo), while rejecting extra ships, mutated existing ships, base changes, phantom components or mismatched purchase receipts.

It algebraically **adds back only ship purchase costs** to a cloned final planet inventory, then removes the assembled ship from that audit projection so the existing independent per-planet event-ledger from #251 can reconcile all modeled production/taxes/mining/structure changes against the **original preturn state**. The returned game state remains the real cloned, final modeled state with one new ship and its actual paid-for stocks.

A failed assembly, unmodeled phase, malformed type, invalid queue claim, incorrect ledger, or tampered state **abstains the entire simulated turn** with no partial state/event data.

## Synthetic discriminating examples

- A planet with 0 initial Duranium and qualifying remaining MC/other minerals cannot pay for a ship before production, but can do so after its existing mines produce at least the required 9 KT Duranium.
- A planet 1 MC short of the total new-component bill can build only if the conditional placement runs after enough taxes are collected.
- A sufficiently stocked warehouse can produce the same ship while buying no new parts and spending 0 MC/minerals. Partial stocked components correctly reduce, not duplicate, surface purchase cost.

These examples validate *internal model timing effects*; they do not establish which sequence a real NuHost used. The local tests deliberately change purchase receipt/warehouse, new-ship specs, and modeled tax/mineral deltas; all unsupported results must ABSTAIN without partial output.

## Mainline remaining

1. **Build queue arbitration** is still missing for Classic PBP, PQ, PPQ and PLS; particularly remembered Classic round-robin pointer, priority points, cloning, pre- and post-combat windows, simultaneous bases and ship ID allocation. Do not infer such information from the model-selected single slot.
2. Joint standard economy, base creation/upgrades and selected ship assembly with explicit local orders and resource contention; then compose with movement, cargo transfer and ultimately combat/wreck cleanup.
3. A scoped feature/coverage inventory and end-to-end standard turn validation. Evidence requiring real server receipts, independently witnessed Host boundaries or outside-player involvement remains parked in [#247](https://github.com/Numillyash/planets-lab/issues/247).

Corpus public100 remains untouched/immutable. \`CURRENT\` remains public68 and fresh32 M2 entity sampling stays excluded. No private orders or HAR, no C5/combat, no IntelBoard changes, no \`DIFF_VERIFIED\` claims.
