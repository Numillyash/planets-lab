# C5 post-capture third-party residual — runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
d4f92cff3c7dba90e9a2594da75d93fad5b0ede1
```

PR #28 remained open + draft.

## Tests

```text
........ [100%]
```

## Targeted residual

Target:

```text
game 622476
turn 17
position 1973,1734
ship7 owner5
  -> captured by ship44 owner3 in VCR37
  -> next VCR38 against ship48 owner8
```

T-1 orders:

```text
ship7 owner5:
  mission=1
  PE=8
  FC=qqt
  requests owner8=True

ship44 owner3:
  mission=20
  target ship7
  PE=5
  requests owner5=True
  requests owner8=False

ship48 owner8:
  mission=3 (Kill!)
  PE=0
  FC=800
  requests owner3=True
  requests owner5=True
```

Relations:

```text
3<->5:
  3->5 [1,0,0]
  5->3 [0,1,0]

3<->8:
  3->8 [1,0,0]
  8->3 [0,1,0]

5<->8:
  both [0,0,0]
```

Factual queue:

```text
VCR37: ship7 owner5 LEFT vs ship44 owner3 RIGHT
VCR38: ship7 owner3 LEFT vs ship48 owner8 RIGHT
```

## Interpretation

The sole third-party residual does NOT require old captured-ship orders to survive capture.

Ship48 has an independent T-1 Kill! request against owner3, the captured ship's new owner. Therefore VCR38 is fully compatible with ordinary attack/defense semantics after owner transfer: ship48 attacks an owner3 ship and prize ship7 defends.

Ship7's old PE=8 also independently points at owner8, so this single row cannot distinguish:

1. old ship7 aggression state surviving into the capture list; from
2. the captured ship merely defending against ship48's independent attack.

Do not promote old-order persistence from this row.

The rejected universal invariant remains rejected:

```text
"immediate post-capture opponent is always pre-capture owner"
  false: 22/23 only
```

The refined evidence question is now whether each observed post-capture continuation has an independently attributable initiator under ordinary attack/defense semantics.

## Documentation alignment

Primary Planets.nu Order Of Battle documents:

- one-sided aggression is sufficient because attacked ships defend themselves;
- captured ships may fight for their new owner;
- captured ships receive an additional target/order list set anew when captured.

The corpus residual is therefore consistent with documented behavior without requiring an undocumented persistence rule.
