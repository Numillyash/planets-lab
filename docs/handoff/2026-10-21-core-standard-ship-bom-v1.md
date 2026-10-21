# Core standard ship construction: exact new-component bill of materials

Date: 2026-10-21. Follows merged PR #254 (ordinary starbase creation, defense posts, fighters).

Official reference: [Building Starships](https://help.planets.nu/building-starship-hulls), [Hull Construction](https://help.planets.nu/hull), [Beam Weapon Construction](https://help.planets.nu/beam-weapon-construction) and [Torpedo Launcher Construction](https://help.planets.nu/torpedo-launch-tube-construction). An ordinary starship consumes one authorized hull, **all required engines**, and the selected counts of fitted beams and torpedo launchers. Installed bays are intrinsic to the hull. Material costs come from the exact immutable-style `NuStaticSpecs` catalog, not guessed or inferred from score residuals.

## Bounded deliverable

`src/planets_lab/sim/standard_ship_component_quote.py` introduces an opt-in `StandardShipBlueprint` and an exact, pure `quote_standard_new_component_ship`:

- Check same-owner planet/starbase, four independently declared tech levels, and an **explicit caller-asserted** set of race-eligible hull IDs. This is a prerequisite: the static catalog alone cannot establish every race's right to build every hull.
- Require valid known components with tech level no greater than the starbase's corresponding level, reject special hulls, overfilled beam/launcher slots, missing/unused weapon IDs, nonpositive engine count and malformed/negative prices.
- Price one hull, exactly `hull.engine_count` new engines, `beam_count` new beam weapons, and `torpedo_launcher_count` new launchers. The source `ResourceCost` fields supply MegaCredits, Duranium, Tritanium and Molybdenum.
- Compare that bill with the current surface stocks and disclose exact **shortfalls**. Not having enough surface material does **not** invalidate a cost quote; it only yields `affordable_from_surface=False`.
- Do **not** spend any resources, create a ship, assign ship ID, reserve queue position or mutate any inputs. The return type explicitly records false flags for independently verified race rights, warehouse inventory, queue/limit, ship-ID assignment and NuHost execution.

This is a *new component price estimate* under explicit `no_warehouse_parts_used_asserted=True`. Reuse of stored hull/engines/weapons, races with unusual build rules, clone discounts, special campaigns, race-specific free components or auto-installation remain unsupported and require additional typed inputs.

## Important boundary before real shipbuilding

The canonical `Starbase` dataclass represents base defense, fighters and tech levels, but **not** stockpiled hulls, engines, beams, torpedo launchers, an actual shipbuilding order, priority points or a build-queue slot. The Planets.nu ship construction pages explain that full ship assembly happens through available stock and the Host's shipbuilding order. A bill-of-materials quote, even if affordable, is not a Host construction operation.

A future core step needs explicit warehouse and build-queue models, race-specific hull eligibility, assigned component provenance, standard ship limit and ID policy, and a corresponding fail-closed assembled-ship state transition. These prerequisites cannot be satisfied by silently creating a ship from a successful price quote. The unrelated user-dependent real NuHost causal experiments remain parked in [#247](https://github.com/Numillyash/planets-lab/issues/247).

## Synthetic tests and safeguards

Tests cover a fictional frigate with two engines, two beams and one launcher, unarmed hull with full engines, shortfalls, tech eligibility, invalid slot counts, unusable/special hulls, unsupported race license, malformed/negative resource prices, and invariance of both game entity inputs and V1/V2 signed `PlayerOrders`. No corpus/heldout32 scan, `CURRENT` mutation, C5 combat or IntelBoard production changes.

`DOCUMENTED`: static build material pricing and tech/slot structure. `TESTED`: local deterministic new-component quote. `DIFF_VERIFIED`: not claimed.
