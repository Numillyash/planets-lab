# Movement coordinate differential validation

Planets.nu stores starship positions as integer X/Y coordinate pairs. Intermediate coordinates for a long diagonal waypoint are not produced by independently rounding the continuous endpoint.

Primary Nu documentation:

- https://help.planets.nu/navigation
- https://help.planets.nu/warp-wells

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
trunc      70 / 345
floor      70 / 345
ceil       80 / 345
nearest   310 / 345
```

Mismatch diagnostics exposed 31 `partial_other` cases. The first 29 printed cases all differed from independent nearest-coordinate rounding by exactly one coordinate. Applying the classic HOST major/minor algorithm reproduced all 29/29 displayed NuHost destinations, including game 680933 turn 6 ship 32:

```text
origin      (1577, 2044)
waypoint    (1532, 2174)
warp        9
nearest     (1551, 2121)
NuHost      (1550, 2121)
major/minor (1550, 2121)
```

`planets-lab` therefore uses major/minor integer projection for ordinary partial movement. The validation harness retains the simpler rounding candidates for comparison and adds `host_major_minor` as the simulator candidate.

Evidence status: `DIFF_VERIFIED` for ordinary partial movement geometry on the observed real-game samples. Mine hits, towing, intercept/chunnel/group movement, fuel-limited movement and other special movement contexts remain separate validation problems.
