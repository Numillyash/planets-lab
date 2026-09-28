# Handoff: c2ng global side model rejected; T26 O-layer probe ready — 2026-09-28

## External source

```text
stefanreuther/c2ng
master@425d623e5d44b017abea50bae4dc9c668870398d
capture provenance:
76b3eed65bee4506758c258b6fc33e10d1a031ee
license: BSD-style 3-clause
authority: external reference only
```

## Corrected result

The current planets-lab control:

```text
opponent_initiator_right = 7 / 8
```

means the **captured/prize ship is LEFT** in those seven exact rows.

Current factual split:

```text
prize LEFT   7 / 8
prize RIGHT  1 / 8

sole RIGHT:
511506 / T26 / ship27 -> ship119
```

c2ng suppresses a captured ship as LEFT, so its external captured-side invariant
is `prize RIGHT`.

Therefore:

```text
global c2ng captured-side candidate = rejected (1/8 exact)
```

Do not promote or fit it as the Nu post-capture side rule.

## Primary-doc boundary

Official Nu documentation says a captured ship can fight both:

```text
O: within the existing order
C: in an additional order created at capture
```

c2ng has no C-order implementation. Its only remaining relevance is a possible
O-layer mechanism.

## Research-branch diagnostic ready

`combat_host_post_capture_pair_recomposition_audit.py` schema v3 adds:

```text
external_c2ng_captured_right
external_c2ng_original_order
factual_prize_side:left/right counts
```

The O probe is deliberately limited to adjacent VCRs and uses:

- T-1 external c2ng/THost frozen order;
- factual capture VCR N only to anchor the current cursor;
- production post-capture active membership;
- independently reconstructed strict attackers;
- captured-LEFT suppression;
- factual N+1 only as the final comparator.

## Main action

On the archive host, run the existing post-capture discovery/evidence gate from
a checkout containing this research diagnostic, or port only this diagnostic
change into a temporary test branch.

Expected first check:

```text
side:external_c2ng_captured_right:exact     1
side:external_c2ng_captured_right:mismatch  7
```

The consequential output is T26's:

```text
result.external_c2ng_original_order
```

If it predicts ship119 with prize27 RIGHT from the continued original cursor,
retain T26 as an O-layer candidate. If not, reject c2ng even for T26.

Do not classify the seven LEFT cases as C merely by elimination; their
capture-generated-order membership still requires independent reconstruction.

## Evidence effect

```text
canonical main mechanics: unchanged
global c2ng side rule: rejected by existing official Nu observations
T26 O-layer cursor: candidate pending archive runtime
C-order semantics: still unresolved
```

Detailed note:

`docs/research/2026-09-28-c2ng-global-rejection-and-o-layer-probe.md`
