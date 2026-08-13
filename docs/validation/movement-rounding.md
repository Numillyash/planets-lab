# Movement coordinate differential validation

Planets.nu stores starship positions as integer X/Y coordinate pairs. Intermediate coordinates for a long diagonal waypoint are not produced by independently rounding the continuous endpoint.

Primary Nu documentation:

- https://help.planets.nu/navigation
- https://help.planets.nu/warp-wells
- https://help.planets.nu/ion-storms
- https://help.planets.nu/host-order-commentary

Historical HOST formula reference:

- https://www.donovansvgap.com/help/details.htm

The classic HOST algorithm determines a major and minor axis. It first rounds the movement on the major axis, then derives and rounds the minor-axis movement from that already-integer major-axis result.

For absolute axis distances `major >= minor` and movement allowance `D`:

```text
major_move = INT(D * major / SQRT(major^2 + minor^2) + 0.5)
minor_move = INT(major_move * minor / major + 0.5)
```

Signs are then restored according to waypoint direction.

## Real-game differential evidence

Dataset: Planets.nu game `680933`, exported from private historical observations in `planets-intel`.

The initial continuous-coordinate candidate test over 345 partial movement observations scored:

```text
trunc               70 / 345  (20.29%)
floor               70 / 345  (20.29%)
ceil                80 / 345  (23.19%)
nearest            310 / 345  (89.86%)
host_major_minor   341 / 345  (98.84%)
```

Mismatch diagnostics exposed systematic one-coordinate differences from independent nearest-coordinate rounding. The classic HOST major/minor algorithm reproduced those cases, including game 680933 turn 6 ship 32:

```text
origin      (1577, 2044)
waypoint    (1532, 2174)
warp        9
nearest     (1551, 2121)
NuHost      (1550, 2121)
major/minor (1550, 2121)
```

The four cases not equal to the raw major/minor endpoint were all explained by documented Host context rather than a different ordinary projection rule:

```text
341  ordinary major/minor partial projections
  1  pre-movement supply repair -> damage speed cap
  1  warp-well endpoint capture
  2  Class-4 ion-storm pre-movement displacement
---
345  explained partial-movement observations
```

### Supply repair / damage-limited case

Game `680933`, turn 14, ship 46:

```text
damage       60 -> 38
supplies    113 -> 3
requested warp 9
resolved warp    7
```

The 110-supply decrease accounts exactly for 22 damage points at the documented 5 supplies per repaired damage point. The resulting 38% damage limits an ordinary non-Lizard ship to Warp 7, and the observed movement is approximately 49 ly.

### Warp-well case

Game `680933`, turn 32, ship 28:

```text
major/minor endpoint   (2148, 1707)
planet 117             (2149, 1706)
distance               sqrt(2) = 1.414 ly
NuHost endpoint         (2149, 1706)
```

The projected endpoint is inside the documented planetary warp-well radius and NuHost snaps the ship to the planet.

### Ion-storm cases

The two remaining residuals were independently identified from stored `stellar_cartography_observations`. All three observers reported the same cloudy disturbance rooted at storm 25.

For the turn 33 -> 34 transition, the resolved next storm state has Warp 6 and recalculated heading 102 degrees. The documented Class-4 displacement is 75% of storm speed:

```text
0.75 * 6^2 = 27 ly
heading 102 degrees -> nearest integer delta (+26, -6)
```

Ship 64:

```text
ordinary endpoint   (1746, 1820)
storm delta          (+26, -6)
NuHost endpoint      (1772, 1814)
```

For the turn 40 -> 41 transition, the resolved next storm state has Warp 7 and recalculated heading 102 degrees:

```text
0.75 * 7^2 = 36.75 ly
heading 102 degrees -> nearest integer delta (+36, -8)
```

Ship 94:

```text
ordinary endpoint   (2117, 1842)
storm delta          (+36, -8)
NuHost endpoint      (2153, 1834)
```

The observed storm centers also validate Host ordering: each disturbance first moves using its previous heading, then its heading is recalculated; the recalculated heading is the one used for the current turn's ship displacement.

## Simulator status

`planets-lab` uses major/minor integer projection for ordinary partial movement and has a canonical `IonStorm` representation plus resolved-storm displacement support. External pre-movement displacement is represented by the generic `movement.pre_move_offsets` hook and is added after the ship's own navigation vector has been calculated, before final warp-well capture.

The stochastic ion-storm evolution itself is **not** guessed. `ResolvedIonStormDragPhase` requires an already-resolved post-evolution storm snapshot and fails closed for unsupported contexts such as non-ordinary movement or extreme storm effects.

Evidence status:

- ordinary partial movement geometry: `DIFF_VERIFIED`
- supply repair + damage speed-cap interaction: `DIFF_VERIFIED` on the observed transition
- warp-well endpoint capture: `DIFF_VERIFIED` on the observed transition
- Class-4 ion-storm 75% displacement and use of recalculated heading: `DIFF_VERIFIED` on two independent real-game transitions
- stochastic ion-storm evolution: not implemented / not yet validated
