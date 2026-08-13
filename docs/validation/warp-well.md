# Warp-well validation boundary

Planets.nu documents that planets have warp wells extending three light-years in all directions and that a moving ship above Warp 1 which ends inside the well is pulled into planetary orbit while its waypoint remains unchanged.

Primary sources:

- https://help.planets.nu/warp-wells
- https://help.planets.nu/default-config
- https://help.planets.nu/mis-hyperjump

The documentation describes the well using square grid sectors and inner/outer rings, but does not state the server predicate as an explicit coordinate formula. `planets-lab` therefore does not yet hard-code Euclidean, Chebyshev or other geometry for warp-well capture.

The intended validation is to compare consecutive observed NuHost turns where a ship's normal projected endpoint lies near a planet and determine which integer-grid predicate reproduces capture. Until then, warp-well geometry remains pending `DIFF_VERIFIED`.
