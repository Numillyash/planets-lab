# PR #271 — late PQ external-selection regular ship and 14-phase economic ledger

Date 2026-10-22. Code `src/planets_lab/sim/late_pq_external_regular_economy.py`, synthetic tests `tests/test_late_pq_external_regular_economy.py`.

## Scope

The documented [PQ queue](https://help.planets.nu/queue-pq) uses random eligible-starbase choices as ships again open below soft cap. This model deliberately **does not** infer or simulate NuHost RNG. Requires the complete fleet, 2–64 ordinary build-capable bases, at least two queued competing ship builds, exactly ONE vacant soft-cap slot, and one explicit externally **caller-selected** queued base plus the lowest free ship ID. All bases, including idle/unselected queued bases, must provide fully typed complete warehouse; queued bases must supply standard blueprints and hull eligibility. Unsupported mining stations, pbN, clone, other ship movement/combat or custom rules abstain.

`LatePQContext` stores exact `selected_planet_id`, `selected_ship_id`, complete owner PP and full roster, and distinct asserted scope flags. `simulate_late_pq_external_selected_economic_turn` executes only that selected ship using #257 independently audited exact standard BOM, warehouse draw/new component purchases and final hull/engine/weapons/crew, then reconciles intact 14-phase economy either before or after build under explicit hypotheses. The regular queued ship consumes zero PP; other candidates and idle bases never receive PP or warehouse changes in this one-slot model. Owner PP is preserved in a checked complete separate sidecar.

Missing warehouse at ANY base, unknown parts, inconsistent owner, unused base with invalid queue, missing/duplicate PP, wrong free ID, insufficient MC/minerals, undocumented fleet actions, forged ship/resource/event receipt, missing selection assertion -> WHOLE-TURN `ABSTAIN_LATE_PQ_EXTERNAL_REGULAR_TURN` with no partial state or other ledgers. Inputs remain untouched.

## Evidence

This is `TESTED conditional` ONLY; an asserted externally chosen winner is not a NuHost-observed selection. No accepted Host order, actual RNG stream, true ship-ID selection policy, timing or DIFF_VERIFIED. Synthetic tests cover both phase-placement hypotheses, alternate externally selected winning base, stored components and adversarial rejection cases.

## Next

Combine a bounded late PQ sequence of independently caller-selected winners across consecutive turns with warehouse/PP carry and independent economy events, if feasible without inventing random selection. Alternatively compose #270 PPQ Stage-1 with movement/cargo in a strictly defensible interval. Real server accepted orders and independent host boundary remain blocked in issue #247. No sealed heldout32 reads, corpus rebuild, CURRENT changes, unrelated combat or IntelBoard.

Per PR #262, next PR must rewrite entire `docs/CONTINUE_HERE.md`, update `docs/PR_CHANGELOG.md`, another meaningful handoff/roadmap/README, validate exact PR head CI and successful post-merge main CI.
