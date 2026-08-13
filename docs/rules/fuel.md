# Normal movement fuel

## Evidence status

`DOCUMENTED` — primary Planets.nu documentation, Fuel Consumption Details.

For normal movement, Planets.nu documents:

```text
Fuel Use = TRUNC(
    Fuel Factor
    * TRUNC(Total Mass / 10)
    * TRUNC(Distance Traveled)
    / Max Distance Per Turn
    / 10000
)
```

`Max Distance Per Turn` is the normal `warp²` movement allowance, doubled for a Gravitonic Accelerator.

The movement mass includes the hull/engines, installed beam and torpedo components, ammunition, fighters, fuel, supplies, clans, minerals, and the corresponding mass of a ship being towed.

## Implementation boundary

`movement_fuel_use()` implements only the arithmetic above. It does not yet:

- look up an engine's fuel factor;
- calculate full ship mass from static component data;
- add towed mass;
- handle cloaking/chameleon consumption;
- prorate movement when available fuel is insufficient;
- apply race/ship fuel-economy advantages.

Those remain separate rules with their own evidence and scenarios.
