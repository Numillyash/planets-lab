# Movement

## Normal speed

Status: `DOCUMENTED`

For normal engines, the maximum nominal movement distance in one turn is the square of the selected warp factor:

```text
max_distance = warp ** 2
```

Examples: Warp 7 -> 49 ly, Warp 9 -> 81 ly.

A Gravitonic Accelerator doubles the normal maximum distance per turn. This modifier is ruleset/hull context and must not be inferred from `warp` alone.

Primary sources:

- `https://help.planets.nu/navigation`
- `https://help.planets.nu/fuel-details`

## Major movement phases

Status: `DOCUMENTED`

The movement stage distinguishes three major phases:

1. towing ships move;
2. most other ships move;
3. intercepting ships move.

The Host Order and Intercept documentation place intercept movement after ordinary movement. Detailed sub-order and special movement interactions require dedicated scenarios.

Primary sources:

- `https://help.planets.nu/host-order`
- `https://help.planets.nu/mis-intercept`
- `https://help.planets.nu/mis-tow`

## Warp wells

Status: `DOCUMENTED`

Planets affect ships ending movement within a three-light-year warp-well region. Warp-well behavior is not part of the first pure-geometry scenario and must be implemented as a separate movement sub-step.

Primary source:

- `https://help.planets.nu/warp-wells`

## Not yet specified

The first movement implementation must not yet guess:

- fuel-limited partial movement;
- engine overdrive effects;
- Gravitonic hull detection;
- Hyperjump;
- tow resolution;
- intercept target visibility and chained intercept;
- mine hits and web interactions;
- ion-storm movement effects;
- wormholes, chunnel or campaign-only movement abilities;
- exact warp-well tie/boundary cases beyond documented standalone scenarios.

Each item above gets its own rule note and golden scenario before entering the engine.
