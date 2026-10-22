# Classic PBP — one genuinely contested terminal hard slot (conditional)

Date: 2026-10-22. PR follows #263 (one uncontested priority+standard block) and #264 (multi-turn queue sidecars).

## Documented context and intentional uncertainty

Official [Classic PBP queue](https://help.planets.nu/queue-pbp) says eligible priority builders have at least 21 PBP, and assigns a free slot to the player with the most PBP; the hull costs ceil(mass/50 KT) capped at 20. The [Host Order of Shipbuilding](https://help.planets.nu/starbase-host) warns of **reports** that newer priority ordering may prefer PB codes and player slot before PBP totals. Therefore the simulator **does not assert that any real Host version** implements the selected winner rule. All outcomes remain CONDITIONAL under an explicit **caller-asserted unique-highest-PBP/no-codes ranking hypothesis**.

This model specifically represents **exactly one legal ship ID remaining under a Classic hard cap**. It requires at least two player PBP balances >=21, an unambiguous maximum score (no ties), exactly one queued ship on exactly one base owned by *each* eligible player, a complete known base/player/ship roster, no PB codes or cloning and no other movement/combat/build-window interactions. It does NOT implement multiple available slots, tied high PBP or PB# code precedence, resource depletion followed by second choice, or ranking by game player slot.

## Implemented

\`src/planets_lab/sim/classic_terminal_pbp_last_slot.py\` chooses the unique highest-scoring eligible owner under the declared ranking policy, selects that player's only queued base, allocates the final unused Classic ship ID and executes one locally audited unit/component-warehouse ship build with the existing exact #257 assembler. Only the winner spends the appropriate mass-based PBP and MC/mineral purchases. Other players' PBP totals, queued bases' inventories and the last STANDARD pointer remain unchanged.

Runs the full unchanged 14-phase planet economy either before or after this terminal build, as an explicitly hypothetical phase placement. Independently re-verifies the final ship's blueprint/crew/engine/weapons/empty cargo and every planet's economic resources by removing only the winner's new ship and restoring only the relevant purchased resource costs on a cloned projection. A forged ship, missing mining event, altered stock, tie, unknown owner/queue policy or unsupported action yields whole-turn ABSTAIN without partial output.

## Tests

A fictional 9/10 Classic hard-capped game with two eligible owners (PBP 25 vs 22) has one last slot. The 25-PBP owner conditionally wins ship ID10, pays its documented PBP cost and preserves the saved standard pointer. Reversing points reverses the winning base. A 1111 KT hull costs 20 PBP, capped; stored components cost 0 surface materials. Before/after economy changes affordability when the owner starts one MC below the exact BOM. Negative tests reject PBP ties, extra candidates, phantom/missing base, bad PB code, clone, owner mismatch, wrong slot count, missing asserted rule, phantom warehouse components, and simulated receipt/state corruption.

## Explicit evidence boundaries

This expands **conditional model coverage**, not proven contemporary NuHost ranking or DIFF_VERIFIED compatibility. Authenticated accepted server orders and independent Host execution/timing/pre-post still unavailable: issue #247. No corpus read/rebuild, no changed public68 CURRENT or heldout32 M2 state, no unrelated C5, IntelBoard, or signed PlayerOrders V1/V2 schema modification.

After every PR, update full \`docs/CONTINUE_HERE.md\`, current entry \`docs/PR_CHANGELOG.md\`, and a meaningful scoped handoff/roadmap update in that **same PR**, per #262.
