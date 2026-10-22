# Consecutive Classic standard/PBP turns with explicit carry sidecars

**Date:** 2026-10-22. Depends on merged [#263](https://github.com/Numillyash/planets-lab/pull/263), [#260](https://github.com/Numillyash/planets-lab/pull/260), documented [Classic PBP](https://help.planets.nu/queue-pbp).

## Actual added scope

\`src/planets_lab/sim/classic_bounded_multiturn_carry.py\` composes two distinct **existing** full-turn mechanisms: one uncontested priority+standard Classic build (#263) when exactly one player has >=21 PBP, versus a standard-only saved-pointer turn (#260) when no player has >=21. This is a new **two-to-eight consecutive model-turn** simulation entry point (one turn allowed) with NO outside events between turns.

The complete initial typed \`ClassicQueueCarryState\` contains:
- Hard Classic ship cap, exact last-standard-build planet pointer, per-player PBP totals (one row per player).
- Per-starbase four-component inventories **including idle bases**. Every component must exist in the static catalog; negative/duplicate/unknown components are rejected upfront.

For each subsequent turn the caller must provide a \`ClassicExplicitTurn\` with one entry per existing base: whether a standard ship is queued, the complete \`StandardShipBlueprint\` and allowed hull IDs, or an explicit idle entry. No base missing from the full roster, and no silent appearance of component inventory, PBP rewards, clone orders, combat or ship movement.

The simulator constructs typed priority and standard subphase inputs from the **same** snapshots, dispatches one of the two audited implementations, then carries forward:
1. The **actual model** T+1 GameState including surviving and newly assembled ships;
2. All PBP balances, carrying only explicitly modeled priority expense;
3. The standard last-built pointer, advancing only on a selected standard build;
4. Each base's remaining component warehouse, never replenishing spent parts without explicit new inventory provenance.

If an owner remains PBP-eligible after the single-modeled priority build, multiple owners compete for PBP builds, another Host interleaving/queue state is required, the later turn contains unknown/out-of-catalog inputs, or a later turn fails affordability, the **whole multi-turn computation ABSTAINS**: no partial game, intermediate receipts or durable sidecars are returned.

The model never asserts that a real game paid PBP or selected these build slots. Its \`ClassicCarryTurnReceipt\` sequence gives a transparent synthetic explanation for each turn, with explicit false flags for independent queue verification, PBP provenance and NuHost execution.

## Evidence and boundary

- All models remain \`TESTED\` internal conditionals, not \`DIFF_VERIFIED\`. Complete accepted server orders, independent Host boundary and complete independent player pre/post snapshots are still missing: [issue #247](https://github.com/Numillyash/planets-lab/issues/247).
- This does not simulate replenishment of PBP through ship destruction/combat/recycle, priority PBx tie-breaks, advanced cloning, pre-/post-combat Host double build windows or PQ/PPQ/PLS queue arbitration.
- The same per-turn economy placement (before/after ship builds) is **explicitly provided for each turn as a hypothesis**, not inferred Host timing.
- No production IntelBoard, C5 combat, V1/V2 HMAC schema, \`CURRENT\` public68, sealed heldout32 or existing public100 corpus is changed/read.

## Synthetic discrimination

A Classic game has three bases, two queued and one idle, 8 ships at the start and cap12; Player1 starts on 21 PBP. Turn T: the sole uncontested priority build gets ID9 and consumes one PBP, and the remaining standard build gets ID10. Turn T+1: no player has 21 PBP, so the standard-only pointer path gets IDs11 and12 with PBP still20. A third turn at cap builds no ships and preserves pointer, but still performs its separate 14-phase economic step. Regression tests verify warehouses from T are consumed in T+1 and never automatically replenished. Negative cases include eligible-PBP competition, missing base/warehouse, phantom components at an **idle** base, invalid second-turn hull, malformed pointer, unresolved in-turn priority selection and contradictory source assertions.

## Next incremental work

Address a documented, tightly bounded **Classic PBP contention** case with explicit snapshot and priority rank, if independently supportable; otherwise progress to guarded PQ/PPQ late queue admission and multi-system Host integration. Keep causal Host verification deferred per #247. All PRs must update \`docs/CONTINUE_HERE.md\`, \`docs/PR_CHANGELOG.md\` and one additional meaningful doc in the *same* PR.
