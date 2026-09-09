# Finite-fuel Tow clean residual shape — runtime result

Date: 2026-09-09

GitHub `main` is the source of truth. This handoff records the completed lightweight clustering pass over the 53 finite-fuel Tow rows that remained clean after the bounded external-context follow-up. It does **not** promote finite-fuel Tow.

## Source runtime

Source gate:

```text
logs/finite-fuel-tow-external-20260909T171801Z-2c5d841f-20098
```

Residual-shape runner output:

```text
logs/finite-fuel-tow-residual-shape-20260909T185636Z-f48264d4-5379
```

All stages completed successfully:

```text
inputs          0 / 0
tooling         0 / 0
residual-shape  0 / 0
```

Input accounting:

```text
clean_residual_input = 53
parsed_clean_cases   = 53
```

## Population

By game:

```text
360690  39
620694   8
511506   6
```

By tower warp:

```text
warp 9  45
warp 8   5
warp 7   2
warp 3   1
```

Route shape:

```text
off_route                  48
same_line_route             4
same_line_beyond_waypoint   1
```

The residual population is therefore not dominated by a simple along-route fuel-proration error.

## Residual-vector structure

Rounded residual norm (`observed - direct Tow geometry`):

```text
27 ly   37
48 ly    5
26 ly    2
 3 ly    1
34 ly    1
31 ly    1
28 ly    1
138 ly   1
45 ly    1
18 ly    1
121 ly   1
312 ly   1
```

The 27-ly and 48-ly families dominate the clean population.

The most repeated exact vector is:

```text
(21, -17)  x5
```

All five rows are in game `360690`, turn `131`, at the same origin / waypoint / factual destination geometry family.

Other repeated vectors include `(25,9)`, `(-27,0)`, `(23,14)`, `(25,11)`, `(6,-26)` and `(26,6)`.

## Storm-vector lead

The clustering pass itself is mechanics-neutral, but the dominant lengths form a specific follow-up lead against the already documented/implemented ion-storm drag arithmetic:

```text
documented Class-4/5 drag distance = 0.75 * storm_warp^2

storm warp 6 -> 27 ly
storm warp 8 -> 48 ly
```

This numerical coincidence is **not attribution**. The previous external-context classifier marked only two of the 56 post-warp-well rows as `ion_storm_drag`, so the clean 53 require an explicit historical storm-vector comparison before any Host-order conclusion is allowed.

The next bounded diagnostic should therefore compare each clean residual vector against the **actual historical root-storm drag vectors** present in the before-turn and after-turn storm snapshots, while separately measuring local Class-4+ voltage at:

- Tow origin;
- direct Tow geometry endpoint;
- factual observed endpoint.

This can distinguish:

1. no actual historical storm vector match;
2. exact vector match but no qualifying local voltage at the currently assumed point;
3. exact vector match with qualification at a different phase point;
4. ambiguous/multiple-storm vector matches.

Only categories 2/3 would justify a new Host-order investigation. They would still not by themselves prove where Tow and ion-storm drag occur relative to each other.

## Status

```text
Move Most + Intercept nominal one-turn basis:
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

finite-fuel Tow nominal-vs-projected basis:
OPEN

post-warp-well residual:                  56
known context / transfer confounder:       3
clean residual clustering population:     53
nominal-vs-projected Tow discriminator: NONE FOUND
```

No `planets-intel` behavior changes follow from this checkpoint.
