# Late PQ / PPQ — strictly bounded priority-point admission (PR #266)

Date: 2026-10-22. Documented inputs: [Production Queue](https://help.planets.nu/queue-pq), [Planetary Production Queue](https://help.planets.nu/queue-ppq), [Build Queues](https://help.planets.nu/queue).

The queue families differ: PQ regularly allocates builds randomly, while PPQ throttled regular builds are related to the share of **owned planets** and may use RB# codes. Neither random arbitration nor PPQ owned-planet regular allocation is implemented here. This unit is **ONLY the priority stage**, explicitly uncontested.

## New executable selector / quote

`src/planets_lab/sim/late_pq_ppq_priority_admission.py` implements `quote_single_late_priority`, deliberately distinct from Classic PBP. With standard default custom settings, priority ship cost is:

```text
1 + ceil(min(hull_mass_KT, 1000) / 50) Priority Points
# 50KT => 2 PP; 60KT => 3 PP; >=1000KT => 21 PP
```

A supported outcome requires: PQ or PPQ mode; explicit global soft cap already reached, global fleet still below **999**; complete asserted owner PP balances and starbase/fleet roster; **one and only one** `pb1`-coded standard queued base; every other base explicitly idle, none cloning or ordering pb2..pb9; known standard hull and sufficient points; exact standard default cost. The selector yields a modeled lowest-free ship ID and owner PP balance after hypothetical charge.

Unknown/competing regular or priority orders, missing owners, custom price, pb2 codes, absent hull mass, disabled assumptions, below-soft-cap phase and full 999 programmatic cap **ABSTAIN**, not guess.

## Boundary

No ship is constructed, no planet resource debit or Host turn runs in PR #266. The quote is a conditional **TESTED model**, **not** independent NuHost queue selection or order acceptance. This differs from PPQ's ten-or-more regular allocations, percentage-based distribution, RB# and potential beyond-limit priority builds. PR #267 or a later separate stage should compose the admitted single priority with the existing BOM/warehouse assembler and intact 14-phase economy while preserving points, cap and full ledger invariants.

Preserve public100, `CURRENT` public68, sealed heldout32, unrelated C5 combat, IntelBoard production and signed owner V1/V2 schemas. External Host attribution stays deferred in [issue #247](https://github.com/Numillyash/planets-lab/issues/247). Every future PR must update a fresh full `docs/CONTINUE_HERE.md`, a current-number entry in `docs/PR_CHANGELOG.md`, and one other meaningful repository doc per PR #262.
