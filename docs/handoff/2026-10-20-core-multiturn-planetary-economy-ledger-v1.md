# Standard planetary economy: bounded multi-turn balance contract

Date: 2026-10-20. Builds on merged PR #250, main `3559d33c5f0868b6ef6de109e764ab1d7f19d3ba`, successful main CI #1374. Human-dependent NuHost/C5 studies stay parked in issue #247.

## Goal

Prove internal **multi-turn consistency** of the supported standard planet economy and explicit construction hypotheses on more than one owned planet, not merely one-step arithmetic. A valid local test does **not** prove authentic historical orders or actual Host execution.

New module: `src/planets_lab/sim/planetary_structure_multiturn.py`.

- Accept 1–8 explicit consecutive `StructureTurnPlan` rows. Each contains a complete owner→tuple-of-structure-targets mapping, per-turn opt-in supply-to-MC sale, and an explicit **hypothetical** before-/after-economy structure placement.
- Reuse unchanged `PlanetaryHostPipeline` (14 phases), unchanged `HostEngine`, and the existing PR #249 priority builder and PR #250 conditional building slice. No new `PlayerOrders` fields, V1/V2 signature schemas, side-channel order source, or new Host ordering assertion.
- Compare every modeled step with a strict **per-planet event ledger**, independently adding declared `factory_supplies` production, `tax_collection` income, `standard_structure_build_conditional` spending and sale, `mineral_mining` extraction and `trans_uranium_mutation` deposit additions, plus `structure_decay`. Require equality with actual pre/post state deltas:
  - `Δsupplies = produced − supplies_sold − supplies_built`
  - `ΔMC = taxes_collected + supplies_sold − MC_spent_on_building`
  - `Δsurface_mineral = mined`, `Δground_mineral = −mined + mutated`
  - `Δstructure_family = built_family − decayed_family`
- Extend conditional structure events with purchased counts for each of the three structure families. This supports checking the structural inventory, not just total spent supplies.
- If any inner turn fails, owner coverage is incomplete, an unmodeled operation changes supported inventories, or an event ledger does not explain an actual delta: **ABSTAIN entire sequence** and reveal neither partial end states nor intermediate checkpoints. A noncausal full local run returns turn-by-turn typed checkpoints, synthetic event ledger details, and a final state.
- The identity checks require adjacent turn numbers, unchanged planet/owner roster and stable ownership within this bounded study. A scenario needing an ownership transfer, captured/boarded ship, special mission, starbase, ion storm or campaign modifier is outside this module's supported scope.

## Synthetic test program

Use a fully fictional **two-owner, two-planet, three-turn** scenario, with independent building targets for each player, real 14-phase production/tax/mining and diverse structure placement choices. Check determinism, no source state mutation, exact consecutive turns, per-planet credits/supplies/mineral/structure balance, and no NuHost causal flags.

Additional tests include a repeated no-op target on the next turn, distinguishable factory-production placements, fully specified negative scenarios and **late-turn** resource tampering. An error in turn 2 must discard the valid turn 1 result rather than emitting partial or misleading evidence.

The production, taxes, mining and population models may be internally correct but still differ from NuHost on an undocumented mode or timing. The full event ledger is *model-internal consistency*, not independent parity; unsupported interactions should abstain. Do not turn its successful synthetic execution into `DIFF_VERIFIED`.

## Corpus boundary

Public100 ingestion/storage remains complete (100 games; 224014/224014 snapshots; immutable compact-generation SHA256 `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`). This work does **not** change corpus `CURRENT` (public68), sample fresh32 for M2, process another 26.65 GiB scan, access user sessions, or touch C5/combat/IntelBoard. Frozen M2 136-pair descriptive coverage remains a separate observational fact.

## Follow-on

After passing CI, consider a standard-only **component coverage inventory** listing which remaining mechanics of movement, planet-economy and starbase can compose a complete turn and which require explicit ABSTAIN. Prioritize genuinely missing documented standard operations; defer manually captured Host proofs to issue #247.
