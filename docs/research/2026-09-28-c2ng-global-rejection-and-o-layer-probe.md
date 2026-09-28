# c2ng global rejection + bounded original-order probe — 2026-09-28

## Correction

The external c2ng capture-side result was initially interpreted in the wrong
orientation.

The canonical planets-lab post-capture diagnostic stores the **captured/prize
ship side**. Its control:

```text
opponent_initiator_right -> prize LEFT
```

is 7/8 exact.

Therefore the current official-Nu population is:

```text
captured/prize LEFT   7 / 8
captured/prize RIGHT  1 / 8

sole RIGHT:
511506 / T26
ship27 -> ship119
```

The audited c2ng/THost path does the opposite for captured ships:
`fl_WasCaptured` explicitly suppresses the captured ship as LEFT. With
random-left/right disabled, a continued captured-ship fight requires the prize
on RIGHT.

Consequently:

```text
c2ng captured-RIGHT global side candidate
  exact     1 / 8
  mismatch  7 / 8
```

This rejects c2ng as a complete/global NuHost post-capture side model.

## Why c2ng is still useful

Current primary Planets.nu documentation explicitly gives a captured ship two
possible post-capture combat contexts:

```text
O = continuation within the existing order
C = an additional order created when capture occurs
```

c2ng implements only a frozen single-order Host traversal and therefore can at
most be a candidate for O.

The sole current side-compatible observation is T26. This motivates one narrow
question:

```text
Can T26 be reached by continuing the original c2ng/THost cursor after the
capture, without creating a new order?
```

Side compatibility alone is not enough to answer yes.

## Diagnostic changes on the research branch

Updated:

`tools/diagnostics/combat_host_post_capture_pair_recomposition_audit.py`

Schema is now:

```text
planets-lab.combat-host-post-capture-pair-recomposition-audit.v3
```

### Explicit external side comparator

Added:

```text
external_c2ng_captured_right = RIGHT
```

The report now also counts:

```text
factual_prize_side:left
factual_prize_side:right
side:external_c2ng_captured_right:exact
side:external_c2ng_captured_right:mismatch
```

This comparator is explicitly documented in code as non-authoritative and must
not be used as a Nu mechanics rule.

### Bounded O-layer probe

Added a research-only field:

```text
external_c2ng_original_order
```

The probe:

1. is limited to `to_vcr_id == from_vcr_id + 1` so it does not need factual
   intervening post-capture history;
2. reconstructs a frozen c2ng THost-simulator battle-order key from T-1 raw
   state;
3. anchors the current nested cursor using factual capture VCR N only;
4. continues RIGHT-outer / LEFT-inner traversal;
5. applies the audited c2ng captured-LEFT suppression;
6. considers only independently reconstructed active ships whose T-1 orders
   strictly permit attacking the prize's new owner;
7. predicts the next **prize encounter** in that external traversal;
8. uses factual VCR N+1 pair/side only for the final comparator.

The probe deliberately does **not** claim to simulate:

- unrelated pair outcomes between cursor positions;
- non-adjacent capture continuations;
- Nu's capture-generated C order;
- complete c2ng or NuHost queue behavior.

## External THost order key used only by the probe

The helper transcribes the c2ng simulator's THost ordering behavior, not the
canonical Nu priority helper.

For the external comparator:

```text
numeric FC -> numeric value
otherwise  -> 1000 base
Kill       -> aggressive base
PE         -> 1010 class when non-Kill
neutral    -> 1015
no fuel    -> numeric priority discarded before non-Kill/PE modifiers
tie        -> ship id
```

In c2ng simulator mode Kill is also treated as having an enemy because its
`agg_Kill` abstraction cannot distinguish Kill-with-PE from Kill-without-PE.

This helper stays inside the diagnostic module; it was not added to
`planets_lab.rules`.

## Tests

Research-branch tests now cover:

- c2ng external order values separately from canonical Nu priority;
- a synthetic T26-shaped cursor:
  `[captor102, prize27, attacker119]`;
- capture cursor `RIGHT=27 / LEFT=102`;
- continued cursor reaches attacker119 against prize27 on RIGHT;
- the T26-shaped comparator is exact;
- captured-RIGHT external side comparator is false for a factual LEFT shape.

The standard repository archive runner already executes
`tests/test_combat_host_post_capture_pair_recomposition_audit.py` and the
pair-recomposition runtime, so no new runner is required.

No archive corpus is available inside this GitHub-only research chat; the
8-row runtime result must therefore be produced on the existing archive-host
environment rather than fabricated here.

## Evidence effect

```text
global c2ng post-capture side rule: REJECTED by current Nu population
T26 original-order c2ng cursor: CANDIDATE / runtime not yet executed
capture-generated C-order semantics: still UNKNOWN beyond primary docs
canonical mechanics: unchanged
```
