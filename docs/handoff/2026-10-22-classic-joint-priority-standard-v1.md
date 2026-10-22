# Classic PBP: bounded priority + standard build subphases in one turn

**Date:** 2026-10-22. **Sources:** [official Classic Priority Build Points](https://help.planets.nu/queue-pbp), [Host Order of Shipbuilding](https://help.planets.nu/starbase-host). Implementation reuses the distinct #259/260 standard pointer/building and #261 uncontested priority modules.

## What now works, conditionally

\`src/planets_lab/sim/classic_joint_priority_standard_turn.py\` composes **one** ordinary Classic PBP priority build followed by a genuine selected STANDARD subphase. Both use a shared asserted fleet/base/player roster, exact design, warehouses, base owner and hull rights, finite Classic hard cap and lowest available unused ship ID pool.

A candidate priority base owned by the **single** PBP-eligible owner with **exactly one** queued ship is selected by the existing #261 guarded implementation. Hull-mass priority cost is paid from that player's PBP balance. Its component purchases, ship identity, remaining warehouse and resulting state are independently checked against an additional replay with the existing strict #256/257 unit/price/new-ship material auditor.

After that priority build:
- Its base's ordinary-queued flag is cleared for this bounded one-turn model (no second build from the same base). The priority subphase **does not change the last standard pointer**.
- All owner PBP balances must now be **below 21**. Otherwise another genuine priority build could be possible, and this model **ABSTAINS** rather than falsely ending the priority subphase.
- The #259 circular standard pointer selector is run on the *remaining* ships and next queue state, under the same hard limit; ordinary builds are assembled in **pointer order**, with a distinct lowest-free ship ID each, until available hard-cap slots are exhausted.
- The saved standard pointer is updated **only** when a standard build occurs; if priority took the final slot, it stays unchanged. Unselected bases retain warehouse material and cost nothing.

The intact 14-phase planetary economy executes before OR after this complete two-part block as an **explicit model hypothesis**, never an established NuHost phase order. All built ships' final designs, identities, cargo/crew, warehouse and surface costs are reconciled. Remove only newly built ships and restore only the sum of newly purchased component costs on a separate copied final state, then apply #251 independent planet-resource/event ledgers for all owners/planets. Any unexpected mining/tax/resource, ship, priority queue or material state **ABSTAINS the entire turn with no partial ships or receipts**.

## Deliberately excluded, and why

- **PBP >=21 after the first priority build**: the priority subphase could repeat. A naive handoff straight to standard would improperly award regular slots.
- **Multiple eligible PBP owners, competing priority bases, pbN, cloning**: only source-independent, exactly attributable priority candidate is allowed. We do not implement sorting tie-breaks or old TimHost assumptions.
- **Priority middle/late phase boundaries, after-combat second build, PQ/PPQ/PLS**: actual Host sequencing not established and may require additional queue state.
- **Concurrent base tech/defense, cargo transfers, ship movement and combat**: larger Host composition remains separate. Input orders are operator assertions, not independently accepted server receipts.
- Explicit player PBP balance and the standard pointer are sidecar outputs, **not** fields silently inserted into canonical \`GameState\` or signed V1/V2 \`PlayerOrders\`.

## Deterministic test scope

8/10 existing ships and three bases (one idle), initial owner PBP = 21, one owner-priority queued base and another owner's standard queued base. Priority gets ship ID 9, debits 1 PBP and **does not advance the standard pointer**. Standard then gets ID 10, advances pointer to its base and pays its own material bill. With 9/10 starting ships, priority gets last slot and pointer stays unchanged. A fully stocked priority ship spends 0 planetary materials, while ordinary ship pays its own fresh BOM. Before/after economy control the effect of tax revenue on affordability. Negative coverage rejects unbalanced player PBP records, multiple eligible players or priority candidates, mismatched queue components, cloned/fcode, insufficient money, forged final ships, missing mineral events and unaccounted cargo/resource mutations.

This is **TESTED conditional internal consistency**, not real execution parity, not independently witnessed orders, and not \`DIFF_VERIFIED\`. The gap involving actual server acceptance, Host timing and all-owner snapshots remains parked in [#247](https://github.com/Numillyash/planets-lab/issues/247).

## Corpus / repository scope

No scan of 26+ GiB public100, no heldout32 M2 entity reads, \`CURRENT\` remains public68. No unrelated combat C5, IntelBoard or V1/V2 signature schema changes. As required by [WORKFLOW.md](../WORKFLOW.md), this PR also updates [CONTINUE_HERE.md](../CONTINUE_HERE.md), [PR_CHANGELOG.md](../PR_CHANGELOG.md), and the roadmap.
