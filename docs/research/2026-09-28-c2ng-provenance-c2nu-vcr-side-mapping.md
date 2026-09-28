# c2ng provenance + c2nu VCR side-mapping audit — 2026-09-28

## Scope

Follow-up to:

`docs/research/2026-09-28-c2ng-capture-order-left-right-audit.md`

Questions:

1. Where did c2ng's captured-LEFT suppression come from?
2. Was it an arbitrary simulator heuristic or an attempt to reproduce observed Host behavior?
3. Does c2nu preserve or transform Planets.nu `vcr.left` / `vcr.right`?
4. Is an adapter-level LEFT/RIGHT inversion a plausible explanation for the current planets-lab blocker?

External code remains candidate/reference evidence only.

## 1. Provenance of c2ng `fl_WasCaptured`

Pinned current c2ng:

```text
stefanreuther/c2ng
425d623e5d44b017abea50bae4dc9c668870398d
BSD-style 3-clause
```

The relevant behavior was introduced by:

```text
76b3eed65bee4506758c258b6fc33e10d1a031ee
2021-06-06
"Simulator: implement battle order peculiarities"
Fixes #428
```

The commit message explicitly states that in Host a captured ship cannot appear on the left side, identified there as the inner-loop side.

More importantly, the source comment added by that commit gives the claimed reverse-engineering origin:

```text
Host rule (10):
no fight if opponent has mission 0 and 10 crew

comment:
Host code intended to check both but only checks opponent due to
a 'youship' vs 'you' typo.
```

c2ng then implements that asymmetry through a runtime `fl_WasCaptured` flag and:

```cpp
if (!isPHost(type) && (leftShip.getFlags() & Object::fl_WasCaptured) != 0) {
    return false;
}
```

The same commit:

- sets `fl_WasCaptured` on ship capture;
- resets it at simulation start;
- adds Host/PHost battle-order regression cases;
- references `test2.sim` from bug #428 and `c2hosttest/combat/04_order/b`.

### Interpretation

This materially upgrades the **provenance quality of the external candidate**, not its NuHost evidence status.

It is not merely a modern c2ng design convenience. It was deliberately added as a reconstruction of a specific TimHost battle-order peculiarity, apparently based on inspection/knowledge of Host behavior/code.

However:

```text
THost reverse-engineering claim
!= NuHost evidence
```

c2ng reuses the same `simulateHost()` queue path for `VcrHost` and `VcrNuHost`. Therefore its application to NuHost remains an assumption/candidate until tested against official Nu archives.

## 2. External corroboration around bug #428

The public PCC2 version history lists issue/PR 428 under PCC2 2.0.12 (2021-09-29) as:

```text
Simulator: aggressor/opponent distinction lost
```

and describes the release fix as correctly implementing Aggressor/Opponent distinction for PHost.

This public changelog corroborates the timing and battle-order nature of the c2ng change, but does not independently document the captured-ship THost typo.

The c2ng commit itself is the strongest located source for that claim.

## 3. c2nu Planets.nu VCR mapping

Pinned source:

```text
stefanreuther/c2nu
master@18fb95f16200009a7bee96b7f83c8eea428106ff
version in script: 0.4.4
license: MIT
```

Relevant function:

```text
c2nu.pl::rstPackVcrs
```

Input:

```text
$parsedReply->{rst}{vcrs}
```

For every factual Nu VCR, c2nu directly accesses:

```text
$vcr->{left}
$vcr->{right}
```

and serializes participants in:

```text
foreach (qw(left right))
```

order.

It also serializes side-specific scalar fields without swapping:

```text
left mass, right mass
left participant, right participant
left shield, right shield
```

There is no queue generation, battle-order calculation, capture-side inference or participant swap in `rstPackVcrs()`.

### Mapping conclusion

c2nu treats Planets.nu's API labels as authoritative orientation:

```text
Nu API .left  -> legacy VCR first/left participant
Nu API .right -> legacy VCR second/right participant
```

Thus an accidental generic interpretation such as "Nu's left actually means our right" is not supported by this independent adapter.

This is not proof that planets-lab's own parser is correct, but it gives a concrete independent mapping to compare against.

## 4. Historical depth of c2nu mapping

A dedicated c2nuvcr tool was already being generated from c2nu in commit:

```text
be4970bbbc9bb03a2feac97cf569eb8ec0184bfc
2011-12-13
```

Its documentation says the tool imports planets.nu combat data into PCC2/PlayVCR and that PlayVCR 1.99.16 had specific NuHost VCR support.

The documentation is careful about uncertainty in the **combat resolver**:

- Nu/browser rounding differs from Tim-VCR in places;
- exact balancing was unknown;
- it remained to evaluate whether PlayVCR emulation exactly matched NuHost.

It does not flag LEFT/RIGHT mapping as ambiguous.

This means the direct `left -> left`, `right -> right` adapter convention has long historical provenance in the same independent tooling ecosystem, although the current audit has not yet identified the exact first commit that introduced `rstPackVcrs`.

## Comparison table

| category | external location | implementation behavior | planets-lab equivalent/status | candidate difference | discriminator already possible? | next action |
|---|---|---|---|---|---|---|
| C | c2ng commit `76b3eed...` + `game/sim/run.cpp` | captured LEFT suppression intentionally models a claimed Host typo checking only opponent | current Nu population is 7 captured-LEFT / 1 captured-RIGHT | provenance shows asymmetry is deliberate historical reconstruction, but its captured-RIGHT consequence is globally contradicted by Nu | yes | keep only as an O-layer reachability candidate for the unique RIGHT row T26 |
| A/B | c2ng ordinary order tests | bug #428 regression derives order from external `c2hosttest` cases | ordinary non-capture queue already closed | historical THost provenance only | not needed for current ordinary queue | do not reopen ordinary queue |
| A | c2nu `rstPackVcrs` | preserves Nu `left` and `right` labels directly | planets-lab factual VCR side fields are comparator inputs | independent adapter agrees with literal side interpretation | yes | compare planets-lab extraction against raw API on known rows |
| B | c2nu resolver docs | explicitly warns about Nu VCR rounding/balancing uncertainty | not current blocker | uncertainty is resolver-level, not side mapping | no immediate capture discriminator | retain for later combat resolver work |
| A/B | c2nu history from 2011 | dedicated Nu VCR import existed with Nu-specific PlayVCR support | historical provenance only | long-lived direct adapter convention | yes for raw mapping | no mechanics promotion |

## Evidence-bound conclusions

### A. Already equivalent / strongly cross-checked

- Planets.nu exposes factual VCR participants as explicit `left` and `right`.
- c2nu preserves those labels rather than deriving sides.
- c2ng's captured-side asymmetry is intentional, not an accidental consequence of vector traversal.

### B. Candidate/reference only

- c2ng's claim that THost contains a one-sided captured-opponent typo.
- reuse of that THost behavior for NuHost.
- PlayVCR/c2nu assumptions about Nu combat resolver precision.

### C. Immediate official-Nu discriminator

The eight-row population already gives the first result:

```text
c2ng consequence: captured prize RIGHT
factual Nu:       captured prize LEFT 7/8, RIGHT 1/8
```

So c2ng is rejected as a global NuHost post-capture side rule.

Its stronger provenance still matters for one narrower question. The unique
captured-RIGHT row, `511506/T26`, can be tested for **original-order cursor
reachability** under the THost/c2ng candidate:

```text
frozen pre-combat order
+ persistent RIGHT-outer / LEFT-inner cursor
+ no post-capture re-sort/reset
+ captured LEFT suppression
```

Only if that independent cursor reconstruction reaches T26's factual pair should
the model be retained as an O-layer candidate.

## Adapter-level diagnostic

Before inventing any alternative side rule, add/check one very small invariant on existing raw official Nu payloads:

```text
raw rst.vcrs[N].left.objectid  == planets-lab factual LEFT object
raw rst.vcrs[N].right.objectid == planets-lab factual RIGHT object
```

Run it at minimum on:

```text
511506 / T26 capture continuation
and the 1/8 residual of opponent_initiator_right
```

If exact, close generic LEFT/RIGHT adapter inversion as an explanation for the blocker.

## Evidence effect

None by itself.

```text
external implementation/provenance
-> candidate
-> raw official Nu mapping check
-> deterministic cursor diagnostic
-> held-out differential
-> possible promotion
```
