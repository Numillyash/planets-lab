# PR #273 — capped late PQ waiting turns: zero builds, checked economy

Date 2026-10-22. Implemented `src/planets_lab/sim/late_pq_capped_no_build_carry.py`, tests `tests/test_late_pq_capped_no_build_carry.py`.

## Distinct situation

Contrary to PR #272's **externally supplied single ship loss that re-opens one vacant soft-cap slot**, this scenario has NO missing ship, no exterior change, and a complete ordinary PQ queue at the **current configured soft ship cap** for multiple consecutive turns. Standard ordinary builds have no available regular vacancies. There may be several queued ship designs (2+ queued real starbases), but NONE are executed. Zero new ships, zero component/warehouse consumption, zero owner PP debit or award. This bounded research model explicitly excludes priority pbN orders, cloning, Mining Stations, custom PP rules, other ship/planet actions and movement/combat. Do not apply it to a genuine priority build beyond the soft cap.

## Executable contract

`CappedPQCarry` retains the soft cap, complete owner PP balances and a warehouse for EVERY starbase, including idle and queued bases. `CappedPQNoBuildTurn` records for EACH consecutive step an explicit complete ordinary base roster with queued/idle and typed hull rights. The model requires at least two real queued ordinary contenders, no priority or special orders declared for each step, and exactly `len(ships) == soft_ship_limit`.

`simulate_soft_capped_pq_no_build_carry` executes 2–8 consecutive, separately audited **14-phase planetary economy** turns using `HostEngine(PlanetaryHostPipeline().phases)`. Every step demands unchanged fleet identity and complete starbase/player/metadata/ion-storm roster, consecutive turn advance and exact typed `_planet_ledgers` resource/event reconciliation. No queued ship is built or charged, no sidecar warehouse or PP is altered, and each step returns its queued base SET and economic ledgers. All changes to planetary resources MUST be explained by the 14 supported economy phases, not by fabricated resource receipts.

If a later step fails its economic ledger, a source has missing owner PP, unknown stock even on an unused base, wrong queued hull/engine ID, a duplicate/unknown starbase, extra ship, custom actions, unaccounted resource change, or any requested priority, the **entire 2–8-turn sequence ABSTAINS atomically** with no partial state, receipts or sidecars. The untouched original `GameState`, warehouse and PP input are never mutated.

## Status and boundaries

This is `TESTED conditional`, not independent NuHost order acceptance, suppression timing or DIFF_VERIFIED. The lack of priority action is a caller assertion. A local economic-only HostEngine step is NOT full NuHost execution, and there is no actual server proof that a queued base waited. The new module does not change the PQ random-seed issue, #272's externally asserted ship loss, #270 PPQ Stage 1, or unrelated C5/combat/IntelBoard. No corpus read/write; `CURRENT` public68 unchanged; sealed heldout32 not used.

Synthetic tests cover a fully populated queue at soft cap10 with changed queued bases across two steps, an eight-turn carry with unchanged warehouses and PP, complete economy receipts, missing/malformed rights/owner/store/roster/cap negative checks and forged ship/planet resource/event outputs.

**Next:** scoped shipyard+movement/cargo interaction on a genuinely modeled interval, or a strictly source-backed stronger PPQ fractional-share case; user-dependent accepted-Host proof remains [issue #247](https://github.com/Numillyash/planets-lab/issues/247). Do not invent RNG, rounding or Host causality.

All PRs including tiny fixes must rewrite whole `docs/CONTINUE_HERE.md`, add current # to `docs/PR_CHANGELOG.md` and change meaningful project docs before required exact PR CI, merge and post-merge main CI; never bypass `tools/check_pr_handoff.py`.
