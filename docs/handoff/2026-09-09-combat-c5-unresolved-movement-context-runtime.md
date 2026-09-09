# C5 Host combat — focused unresolved movement context runtime

Date: 2026-09-09

GitHub is the source of truth. This checkpoint records the user runtime of the four-row attribution-only gate staged at branch source:

```text
070cb150a7b88e9a406f3ef8ca9f5984b873211e
```

Artifact:

```text
artifacts/combat-c5-position-v3-20260909-234137/unresolved-context.json
```

Runtime result:

```text
tests rc=0
focused-context rc=0

unresolved_rows=4
vcr_start_found=4
exact_scaled_floor_geometry=3
exact_scaled_floor_with_field_crossing=3
single_focused_candidate_family=2
still_unresolved=2
vcr_damage_normal_mine_multiple=2
```

The diagnostic is attribution-only. Observed Chunnel events, battle-turn minefields and factual VCR-start damage are historical differential evidence and must never be fed back as candidate-set predictor inputs.

## Closed normal-mine attributions

### `620694/T62/ship83`

T-1 / movement facts:

```text
hull_id=69
hull_tech=6
damage T-1=0
warp=7
origin=(1744,1460)
waypoint=(1783,1437)
ordinary prediction=(1783,1437)
factual combat site=(1773,1443)
```

The existing low-tech scaled-floor model has exactly one matching slowdown case:

```text
slowdown_hits=1
endpoint=(1773,1443)
major_axis_penalty=10
```

Hostile normal minefields cross the route in both the T-1 and battle-turn snapshots. Factual VCR-start state independently records:

```text
damage=40
T-1 damage=0
delta=40
normal-mine damage quantum=40
```

Therefore this row is attributable to one normal-mine hit plus the already reconstructed low-tech scaled-floor slowdown.

Evidence boundary:

```text
specific historical attribution: CORPUS_OBSERVED + DIFF_VERIFIED
underlying low-tech slowdown rule: use existing movement checkpoint status
candidate-time exact hit location: stochastic / NOT reconstructed here
```

### `680910/T14/ship65`

T-1 / movement facts:

```text
hull_id=1102
hull_tech=6
damage T-1=0
warp=9
origin=(2315,1984)
waypoint=(2312,1924)
ordinary/warp-well prediction=(2312,1921)
factual combat site=(2313,1937)
```

The same existing scaled-floor model has one exact case:

```text
slowdown_hits=1
endpoint=(2313,1937)
major_axis_penalty=13
```

A hostile normal minefield intersects the route in battle-turn state. Factual VCR-start state independently records:

```text
damage=30
T-1 damage=0
delta=30
normal-mine damage quantum=30
```

This is likewise an exact one-hit normal-mine slowdown attribution.

Important predictor boundary: the matching minefield is not present in the T-1 field-crossing set used by this audit. The field may have been created or changed earlier in the same Host turn. The historical attribution is strong, but the precise hit cannot be predicted from the currently reconstructed T-1 movement state. Do not use battle-turn field state as a candidate predictor input.

Evidence boundary:

```text
specific historical attribution: CORPUS_OBSERVED + DIFF_VERIFIED
candidate-time field mutation / random hit: NOT reconstructed
```

## Still unresolved

### `360690/T54/ship26`

```text
origin=(2323,1568)
waypoint=(2384,1532)
ordinary prediction=(2384,1532)
factual site=(1783,1121)
hull_id=52
hull_tech=9
T-1 damage=0
VCR-start damage=0
```

No exact storm, strong mine, observed Tow or route-equivalent observed Chunnel explanation was found. The focused Chunnel population for this game contained 166 observed events, but none matched this ship's pre-Chunnel prediction and factual combat destination.

Status: bounded unresolved. Do not add a case-specific movement rule.

### `511506/T95/ship332`

```text
origin=(2716,1999)
waypoint=(2715,1999)
warp=1
ordinary prediction=(2715,1999)
factual site=(2716,1999)
hull_id=31
hull_tech=7
T-1 damage=58
VCR-start damage=58
```

The one-light-year geometry trivially collides with the empirical scaled-floor endpoint for many hypothetical slowdown counts, and a hostile normal field is present at T-1. However:

- hull tech 7 is outside the low-tech slowdown scope;
- VCR-start damage does not increase from T-1;
- the normal-mine damage quantum is 55;
- no Chunnel, storm or strong-mine attribution matches.

Therefore the geometric coincidence is explicitly rejected as mine evidence.

Status: bounded unresolved. Do not alter damage-limited warp or mine rules to fit it.

## Consequence for the position/candidate pipeline

The two normal-mine rows are historical stochastic movement events. They explain why a purely deterministic T-1 ordinary-movement endpoint can disagree with factual combat position without implying an error in Host major/minor geometry.

The two still-unresolved rows remain outside any validated position source. Candidate-set v2 may only claim differential coverage over independently resolved position rows; these four rows must not be silently patched with factual battle coordinates.
