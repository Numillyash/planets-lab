# Post-capture O/C topology candidate — frozen before full public topology census

Date: 2026-10-04

Branch:

```text
research/external-engine-analysis
```

Status:

```text
POST_HELDOUT_STRUCTURE_CANDIDATE
```

Authority:

```text
DOCUMENTED Nu architecture
+ CORPUS_OBSERVED residual geometry
+ EXTERNAL_IMPLEMENTATION order topology comparator
```

This is not a canonical NuHost rule.

## Primary documentation

Current official Planets.nu Help:

```text
https://help.planets.nu/battle-order
retrieved: 2026-10-04
```

The documented architecture says, in substance:

```text
- every ship proceeds through a target list while alive and uncaptured;
- captured ships can fight for their new owners;
- captured ships can fight within the existing order;
- after that they receive an additional combat order set anew when captured.
```

The documentation therefore establishes two capture contexts but does not
specify their exact cursor/reset mechanics:

```text
O = participation / continuation within the existing order
C = additional order set anew at capture
```

## Residual geometry that motivates this candidate

Five isolated post-capture rank/cursor residuals have now been examined with the
same frozen c2ng/THost order topology.

Four have the same shape:

```text
higher static/history competitor
    lies before the already consumed capture-target cursor

factual next opponent
    lies after the capture-target cursor
```

Those four are positionally explained by an O-style continuation.

The remaining row is:

```text
486109/T55
external order:
  198, 450, 467, 448

positions:
  rank1 competitor = 0
  prize            = 1
  factual          = 2
  captor           = 3
```

The O cursor is exhausted after captor 448, but factual ship467 lies after the
prize's own frozen position and before the consumed capture target.

## Frozen topology candidate

For a capture where the prize is currently RIGHT in the frozen external order:

```text
prize index  = R
capture-left = L
```

freeze the following purely positional decomposition.

### O segment

```text
O = target positions strictly after L
```

This is the already-audited original-order continuation shape.

### C-forward segment

If O is exhausted, the documented capture-generated order may restart a target
scan after the prize's own order position:

```text
C-forward = positions strictly after R
```

The informative new subregion is:

```text
R < target_position < L
```

because targets after L were already reachable by O.

This candidate is deliberately weaker than a full C algorithm. It says only:

```text
an additional order may make an earlier-passed target position reachable again
without requiring a target before the prize's own order position.
```

## Competing topology

The direct alternative is a full target-list reset that can also reach positions
before the prize:

```text
C-full-reset:
  target_position may be < R
```

The existing T55 residual does not require this.

## Full public topology census

Before implementing pair eligibility or a new selector, run a position-only
census over every globally adjacent public capture observation whose factual
capture side is RIGHT and whose frozen external order/capture cursor is
reconstructable.

Classify factual N+1 opponent position as:

```text
O_AFTER_CAPTOR
    factual_position > captor_position

C_BETWEEN_PRIZE_AND_CAPTOR
    prize_position < factual_position < captor_position

BEFORE_OR_AT_PRIZE
    factual_position <= prize_position

OTHER_GEOMETRY
    malformed / reversed / nonstandard cursor geometry
```

The key bounded checks are:

```text
forward_union_covered =
    O_AFTER_CAPTOR + C_BETWEEN_PRIZE_AND_CAPTOR

requires_before_prize =
    BEFORE_OR_AT_PRIZE
```

No eligibility or target-choice claim is made by this census.

## Evidence boundary

The order vector is still the pinned c2ng/THost external comparator. It is not
NuHost authority.

This candidate was derived after inspecting both discovery and previously opened
public held-out residuals. Any fit on those populations is fitting/structural
evidence only.

A later predictive C selector must independently reconstruct:

```text
- pair eligibility
- target-list state
- pair occurrence limits
- captured-order priority/state
- LEFT/RIGHT
```

before canonical promotion.
