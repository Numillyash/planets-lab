# Handoff: c2ng provenance + c2nu LEFT/RIGHT mapping — 2026-09-28

## External sources

```text
c2ng:
  stefanreuther/c2ng
  current pin 425d623e5d44b017abea50bae4dc9c668870398d
  provenance commit 76b3eed65bee4506758c258b6fc33e10d1a031ee
  BSD-style 3-clause

c2nu:
  stefanreuther/c2nu
  master@18fb95f16200009a7bee96b7f83c8eea428106ff
  historical c2nuvcr commit be4970bbbc9bb03a2feac97cf569eb8ec0184bfc
  MIT
```

Detailed note:

`docs/research/2026-09-28-c2ng-provenance-c2nu-vcr-side-mapping.md`

## Finding 1: capture asymmetry has explicit THost provenance

c2ng commit `76b3eed...` added `fl_WasCaptured` while fixing battle-order
issue #428.

Its source comment claims a concrete Host-code peculiarity:

```text
captured/opponent check intended for both ships
but only opponent is checked because of a 'youship' vs 'you' typo
```

The implementation therefore rejects captured LEFT but not captured RIGHT.

This strengthens the external candidate's provenance, but **does not establish
NuHost behavior**. c2ng applies the same Host queue path to its NuHost mode.

## Finding 2: independent Nu adapter preserves LEFT/RIGHT literally

`c2nu.pl::rstPackVcrs` consumes official Nu `rst.vcrs` and serializes:

```text
Nu .left  -> first/left VCR participant
Nu .right -> second/right VCR participant
```

including masses and shields in the same orientation.

It does not compute battle order, capture continuation or sides.

Therefore a generic LEFT/RIGHT inversion in the interpretation of Nu API labels
is not supported by this independent adapter.

## Immediate official-Nu diagnostics

The side orientation is now explicit:

```text
factual captured LEFT   7 / 8
factual captured RIGHT  1 / 8 (511506/T26)
```

c2ng's captured-LEFT suppression implies captured RIGHT, so it is already
rejected as a global post-capture side rule.

1. Narrow O-layer cursor test:
   reconstruct frozen pre-combat order + RIGHT-outer/LEFT-inner cursor +
   captured-LEFT suppression for the unique side-compatible T26 row. Require
   independent cursor reachability before calling it an original-order case.

2. Adapter invariant:
   on raw official payloads, assert
   `vcr.left.objectid == planets-lab factual LEFT` and
   `vcr.right.objectid == planets-lab factual RIGHT`, especially for
   511506/T26 and the current 1/8 residual.

No canonical mechanics change is justified. Even if T26 is O-reachable, that
would establish only a bounded original-order candidate; c2ng has no model for
Nu's documented capture-generated additional order.
