# Runtime result: c2ng O-layer discriminator — 2026-09-28

## Provenance

Runtime supplied from the WSL archive-host checkout on 2026-09-28.

Research branch at execution:

```text
research/external-engine-analysis
d306edd4984512efbbe29d97f0ad911ebd3285b3
```

Runner:

```text
ARTIFACT_DIR=artifacts/combat-post-capture-c2ng-o-layer \
bash tools/run-combat-post-capture-candidate-discovery.sh
```

Targeted tests passed:

```text
48 passed
```

Runtime population:

```text
ship capture observations: 8
sites: 7
all pair recompositions resolved: 8 / 8
pair phase STANDARD: 8 / 8
pair phase FC invariant: 8 / 8
```

## Side-population result

The runtime confirms the corrected interpretation:

```text
factual prize LEFT   7
factual prize RIGHT  1

external c2ng captured-RIGHT:
  exact     1
  mismatch  7
```

Therefore the audited c2ng/THost captured-side behavior is decisively rejected
as a global NuHost post-capture side rule.

Other existing controls remain unchanged:

```text
opponent_initiator_right          7 / 8
neutral captured orders fresh FC 6 / 8
sticky capture side              4 / 8
frozen T-1 priority              4 / 8
neutral preserved-FC priority    4 / 8
```

## O-layer probe result

The bounded original-order probe reported:

```text
external_c2ng_o_status:resolved       6
external_c2ng_o_status:not_comparable 2
external_c2ng_o_exact                 1
```

The two non-comparable rows are intentionally fail-closed because factual
continuation is not globally adjacent in VCR id:

```text
621896 / T25 second capture: VCR 50 -> 52
622476 / T28:                VCR 105 -> 109
```

Of the six adjacent rows:

- one row is exact under the c2ng original-order cursor;
- five rows have no later captured-RIGHT attacker in the frozen c2ng traversal.

## Exact row: 511506 / T26

Factual:

```text
capture VCR:    54
continuation:   55
captured prize: ship27
captor:         ship102
next opponent:  ship119
factual prize side: RIGHT
```

External frozen order reconstructed from T-1:

```text
[27, 102, 119, 36]
```

External order keys:

```text
27  -> [1010, 27]
102 -> [1010, 102]
119 -> [1010, 119]
36  -> [1015, 36]
```

Capture cursor:

```text
RIGHT index 0 -> ship27
LEFT  index 1 -> ship102
```

Continued cursor:

```text
RIGHT index 0 -> ship27
LEFT  index 2 -> ship119
```

Prediction:

```text
ship27 RIGHT vs ship119 LEFT
```

Factual VCR N+1:

```text
ship27 RIGHT vs ship119 LEFT
```

Result:

```text
pair exact = true
side exact = true
overall exact = true
```

This is the first official-Nu observation in the current capture corpus that
matches the independently reconstructed c2ng/THost original-order cursor
mechanism exactly.

## Five adjacent LEFT rows

The following adjacent rows resolve under the probe but produce:

```text
predicted_prize_continuation = none
reason = no_later_c2ng_captured_right_attacker
```

Rows:

```text
511506 / T33  ship25 -> ship268
511506 / T60  ship32 -> ship180
621896 / T25  first ship34 capture -> ship29
622476 / T14  ship16 -> ship30
622476 / T17  ship7  -> ship48
```

Every one of these factual continuations has the prize on LEFT.

Thus the same external original-order mechanism that exactly explains T26 does
not merely choose the wrong side for these five rows; under its frozen cursor it
does not generate another captured-prize encounter at all.

This is materially stronger than the global 1/8 side-control result.

## Interpretation against primary Nu documentation

Current primary Planets.nu documentation requires two post-capture contexts:

```text
O = captured ship may continue within the existing order
C = captured ship also gets an additional order set anew at capture
```

The runtime result is strongly consistent with the following decomposition:

```text
511506/T26:
  positive candidate for O
  because original frozen cursor independently generates exact pair + side

five adjacent LEFT rows:
  c2ng-like O continuation is positively absent
  therefore a different Nu mechanism is required
  primary documented C order is the leading bounded candidate

two non-adjacent rows:
  not classified yet
  current probe deliberately fails closed
```

Important boundary:

```text
"c2ng O continuation absent" != proof of C
```

Nu's original-order behavior could differ from THost/c2ng. However, the
combination of:

- primary Nu documentation explicitly requiring C;
- exact T26 O-like match;
- five adjacent LEFT rows where the O-like traversal has no continuation at all;

makes O/C decomposition substantially stronger than any single global side
formula currently tested.

## Pair/candidate prerequisites remain exact

The same runtime reconfirms all eight post-capture factual opponents:

```text
active                         8 / 8
candidate-resolved             8 / 8
requests new owner             8 / 8
strict diplomacy permission    8 / 8
requester rank 1               8 / 8
strict rank 1                  8 / 8
```

Special movement residuals remain closed:

```text
tow       1 / 1 exact
intercept 1 / 1 exact
```

Therefore this runtime does not reopen geometry, active membership, opponent
eligibility, diplomacy, or rank. The remaining issue is order-context/side
semantics.

## Next bounded work

### 1. Classify the five adjacent LEFT rows

Build a **Nu capture-generated-order diagnostic**, independent of c2ng, using
only state available at capture plus primary documented behavior.

Required fields:

```text
capture-time owner/race
captured ship post-capture neutral/passive order state
fresh-vs-preserved FC bounds
eligible requester set
requester priority
logical aggressor/opponent
factual side only at final comparator
```

The immediate target is not another global side formula. It is:

```text
Does a newly generated C order independently select the factual opponent and
place the opponent on RIGHT / prize on LEFT for the five O-negative adjacent
rows?
```

### 2. Extend O probe across elapsed intervening VCRs

For:

```text
621896 / T25 VCR50 -> VCR52
622476 / T28 VCR105 -> VCR109
```

use VCRs strictly between N and factual N+1 as already elapsed queue history.
Advance the external frozen cursor through those factual elapsed engagements,
with production mutation after each elapsed VCR, while keeping factual N+1 held
out until final comparison.

This will classify the remaining two rows without weakening the evidence
boundary.

## Evidence effect

```text
global c2ng side model:
  REJECTED by official Nu runtime (1/8)

511506/T26 original-order candidate:
  CORPUS_OBSERVED compatibility with external candidate
  not a canonical Nu mechanic yet

five adjacent LEFT rows:
  c2ng O candidate rejected/absent
  C-order hypothesis strengthened but not yet proven

two non-adjacent rows:
  UNKNOWN for O/C classification

canonical mechanics:
  unchanged
```
