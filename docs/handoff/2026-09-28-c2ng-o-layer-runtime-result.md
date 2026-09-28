# Handoff: c2ng O-layer runtime discriminator — 2026-09-28

## Runtime source

Executed on the archive-host WSL checkout from:

```text
research/external-engine-analysis
d306edd4984512efbbe29d97f0ad911ebd3285b3
```

All targeted tests passed before runtime.

Detailed result:

`docs/research/2026-09-28-c2ng-o-layer-runtime-result.md`

## Decisive results

Current official-Nu capture population:

```text
prize LEFT   7 / 8
prize RIGHT  1 / 8
```

External c2ng captured-RIGHT control:

```text
exact     1
mismatch  7
```

So c2ng is rejected as a global post-capture side rule.

## Positive O-layer result

The bounded original-order probe is exact for:

```text
511506 / T26
capture VCR54
ship27 captured by ship102
next factual opponent ship119
factual prize side RIGHT
```

Independently reconstructed external frozen order:

```text
[27, 102, 119, 36]
```

Capture cursor:

```text
RIGHT ship27
LEFT  ship102
```

Continued cursor:

```text
RIGHT ship27
LEFT  ship119
```

Therefore:

```text
predicted pair = factual pair
predicted side = factual side
exact = true
```

## Negative O-layer results

Five other adjacent capture continuations resolve under the same probe but have:

```text
no_later_c2ng_captured_right_attacker
```

Rows:

```text
511506 / T33
511506 / T60
621896 / T25 first capture
622476 / T14
622476 / T17
```

All five factual continuations place the captured prize on LEFT.

Thus T26 is not just the only captured-RIGHT row: it is also the only adjacent
row where the external original-order cursor independently generates the factual
next captured-prize combat.

## Two rows remain unclassified

The current O probe intentionally fails closed for non-adjacent VCRs:

```text
621896 / T25 second capture: VCR50 -> VCR52
622476 / T28:                VCR105 -> VCR109
```

These need elapsed-intervening-VCR cursor advancement before O/C classification.

## Primary-doc interpretation

Nu primary documentation says a captured ship can fight both:

```text
O: within current order
C: in an additional order created at capture
```

Runtime now gives a strong bounded structural hypothesis:

```text
T26:
  positive O candidate

five adjacent LEFT rows:
  c2ng-like O path absent
  documented C order is now the leading mechanism to test

two non-adjacent:
  unresolved
```

Do not promote the five LEFT rows to C by elimination. Build a capture-generated
order diagnostic independently.

## Main-track recommendation

Next mechanics diagnostic should be **order-context first**, not another global
side control.

For adjacent O-negative rows, reconstruct C from capture-time state and ask:

```text
does the newly created capture order independently select the factual opponent,
with logical opponent/aggressor roles predicting opponent RIGHT / prize LEFT?
```

Separately extend the O probe through factual elapsed VCRs strictly before N+1
for the two non-adjacent rows.

All previously closed prerequisites remain exact:

```text
post-capture active membership 8/8
opponent request/permission    8/8
requester rank one            8/8
special tow/intercept geometry exact
pair phase STANDARD           8/8
FC-invariant pair phase       8/8
```

## Evidence effect

```text
global c2ng captured-side rule: rejected
T26 c2ng/THost O compatibility: observed exactly on official Nu
Nu C-order mechanism: still to reconstruct
canonical main rule: unchanged
```
