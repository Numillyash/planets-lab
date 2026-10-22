# Late PQ/PPQ: one PP-funded priority ship + 14-phase economy (PR #267)

Date: 2026-10-22. Sources: [PQ](https://help.planets.nu/queue-pq), [PPQ](https://help.planets.nu/queue-ppq), [Ship Limit](https://help.planets.nu/ship-limit). Depends on merged #266 admission and #257's independent warehouse/component/ship auditor.

## New executable capability

`src/planets_lab/sim/late_pq_ppq_priority_ship_economy.py` receives the same strictly complete default PQ/PPQ **single explicit pb1** priority request as #266, plus a model GameState, static specifications and explicitly asserted complete component/race-rights/no-other-action context. The soft ship cap may already be reached; construction is permitted while an ID from **1 through 999** remains available. Distinguish **soft cap** (when late PP builds become relevant) from the **programmatic ID ceiling**. The legacy warehouse assembler accepts a caller-selected prelimit phase; here its limit argument represents **the 999 physical ship-number space only**. Its generic naming does not establish that the server selected a slot.

The #266 quote calculates owner-specific default PP cost = `1 + ceil(min(hull_mass,1000)/50)` (max21 PP). The selected base purchases only missing hull/engine/weapon components from its planet, uses its separately listed warehouse parts, and receives an exactly typed new ship with the lowest unused ID. A new ship cannot alter any previous ship or starbase, and the 14-phase unchanged economy is executed either before or after building as an **explicit hypothetical placement**. The independent audit recomputes BOM and warehouse changes, rechecks the final ship's identity/equipment/crew, and projects away **only** ship materials and the new ship to check all planet resource/event ledgers. PP is kept in an *external sidecar* and independently checked against quoted debit; it is not stored in the canonical GameState or PlayerOrders.

Invalid/lacking PP, missing or competing build, pb2..pb9, cloning, non-default custom rules, missing planet resources, unmodeled ship mission, duplicate IDs, a forged final ship, fabricated mineral/MC, or missing mining event **ABSTAINS** without exposing partial simulated state/PP/receipts.

## Key distinctions / remaining

- This is **one eligible priority build after the soft cap**, not PQ's randomly selected standard build, nor PPQ's percentage-of-owned-planets regular allocation with its ten-or-more minimum, RB# codes or PP rewards for empty selected starbases.
- The priority selector is unambiguous only because every other base is asserted idle and all PP, bases, ships and actual selected conditions are caller inputs. No source independently verifies server-accepted orders or Host timing. No other PP earnings (combat/recycling/glory-device/idle base) are simulated.
- Tests cover PQ and PPQ, both economy placements, free ship ID 9 with initial 8/8, PP/MC and mineral costs, all-stock zero-MC but full PP charge, after-tax funding, 1100KT 21-point cap, and adversarial controls.
- This is local conditional `TESTED`, never `DIFF_VERIFIED`; genuine Host accepted order, full pre/post owner snapshots, or a causal queue witness remain in [issue #247](https://github.com/Numillyash/planets-lab/issues/247).

No public100 corpus rebuild, heldout32 entity sampling, `CURRENT` change (public68), C5 combat, IntelBoard prod or V1/V2 signed owner schema modifications. Follow PR #262 mandatory continuation/changelog/docs rules.
