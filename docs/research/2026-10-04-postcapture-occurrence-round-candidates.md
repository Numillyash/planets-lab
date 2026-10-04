# Post-capture occurrence-round candidates

Date: 2026-10-04

Branch:

```text
research/external-engine-analysis
```

Status:

```text
DISCOVERY_DERIVED_CANDIDATES_FROZEN_BEFORE_FULL_QUALIFIED_POPULATION_TEST
```

Authority:

```text
CORPUS_OBSERVED residual shape + INFERRED candidate
```

This note freezes the next bounded candidates before testing them across the
complete dependency-qualified discovery population.  It is not independent
validation because the candidates were derived from two discovery residuals.

Held-out is not used.

## Residuals that motivate the candidates

The static post-capture strict requester ranking is exact on 13/15 currently
dependency-qualified adjacent discovery rows.

The only two rank>1 residuals are:

```text
486109 / T55 / VCR 191 -> 192
prize=450
static rank1=198
factual rank2=467

486109 / T88 / VCR 518 -> 519
prize=296
static rank1=214
factual rank2=454
```

Both rows share the same history discriminator:

```text
prior occurrences(prize, static-rank1) = 1
prior occurrences(prize, factual-rank2) = 0
```

Detailed histories:

```text
T55:
  VCR189  198 vs 448
  VCR190  198 vs 450   <- rank1/prize first occurrence
  VCR191  448 vs 450   <- capture
  VCR192  factual next is 467 vs 450

T88:
  VCR515  214 vs 412
  VCR516  213 vs 214
  VCR517  214 vs 296   <- rank1/prize first occurrence
  VCR518  296 vs 374   <- capture
  VCR519  factual next is 454 vs 296
```

The factual rank2 attacker had no earlier VCR appearance in either residual,
while the static rank1 attacker had already appeared multiple times.

These two facts create two competing explanations which must be separated.

## Candidate A — pair-occurrence round

Prefer a fresh ship pair over a second occurrence before applying ordinary
static priority.

For every strict attacker candidate against the captured prize:

```text
pair_count = number of factual occurrences of
             unordered {prize, attacker}
             through the capture VCR

if pair_count >= 2:
    pair is exhausted
else:
    candidate key = (pair_count, static_priority)
```

Select the lexicographically smallest key.

Therefore:

```text
all occurrence-1 pairs (prior count 0)
precede
all occurrence-2 pairs (prior count 1)
```

Within one occurrence round, ordinary Nu static priority remains unchanged.

This candidate is compatible with the existing documented/project boundary
that one ship pair may fight at most twice and with the already verified
second-occurrence side reversal.  It changes pair selection order, not the
pair cap or side-reversal rule.

## Candidate B — attacker freshness

The two motivating rows also permit a broader ship-level explanation.

For every strict attacker candidate:

```text
attacker_appearances = number of VCRs containing that attacker
                       through the capture VCR
```

Two frozen variants are tested:

```text
B1 fresh-attacker boolean:
   key = (attacker_appearances > 0, static_priority)

B2 attacker appearance count:
   key = (attacker_appearances, static_priority)
```

These deliberately compete with Candidate A.  If a row exists where an attacker
has fought previously but has never fought the prize, pair-round and
attacker-freshness can diverge.

## Baseline

The current static candidate remains:

```text
key = static_priority
```

It is known to produce:

```text
13 / 15 exact
2 / 15 rank>1 residuals
```

## Required discovery comparison

The next probe must reconstruct every adjacent discovery capture through the
capture VCR and, only for rows where the factual opponent dependency is
qualified, compare:

```text
STATIC_PRIORITY
PAIR_OCCURRENCE_ROUND
FRESH_ATTACKER_BOOLEAN
ATTACKER_APPEARANCE_COUNT
```

Inputs allowed before prediction:

```text
- T-1 independently reconstructed candidate/order state
- elapsed factual VCR history through capture VCR N
- replayed terminal/mutation state through VCR N
```

Forbidden prediction input:

```text
- factual N+1 side
- factual N+1 pair when choosing among candidates
- held-out partition
```

The factual N+1 opponent identity is comparator-only.

## Interpretation boundary

Even a 15/15 fit would be discovery fitting evidence, not validation, because
the occurrence-round candidate was derived from two rows in that population.

A successful pair-round fit would justify a new frozen candidate for future
independent evidence:

```text
post-capture mutable recomposition
-> strict eligible attackers
-> lowest pair-occurrence round
-> static priority within the round
```

It would not by itself establish LEFT/RIGHT behavior.


## Full dependency-qualified discovery differential

The frozen candidate set was evaluated across all currently
dependency-qualified adjacent discovery rows.

Unit tests:

```text
6 passed
```

Population:

```text
adjacent rows:             31
qualified rows:            15
dependency not qualified:  16
```

Result:

```text
STATIC_PRIORITY             13 / 15 exact
STATIC_CAP2                 13 / 15 exact
PAIR_OCCURRENCE_ROUND       15 / 15 exact
FRESH_ATTACKER_BOOLEAN      15 / 15 exact
ATTACKER_APPEARANCE_COUNT   15 / 15 exact
```

Candidate divergence:

```text
PAIR_OCCURRENCE_ROUND vs FRESH_ATTACKER_BOOLEAN:
  divergent selections = 0

PAIR_OCCURRENCE_ROUND vs ATTACKER_APPEARANCE_COUNT:
  divergent selections = 0
```

### Interpretation

The already-supported pair cap alone does not repair the two static-rank
residuals:

```text
STATIC_PRIORITY  13/15
STATIC_CAP2      13/15
```

Therefore the missing factor is ordering among still-available candidates, not
merely exhaustion of pairs that already fought twice.

All three elapsed-history candidates fit the full qualified discovery population
exactly:

```text
15 / 15
```

but discovery contains no row that distinguishes pair-level occurrence history
from broader attacker-level freshness.

Consequently no one of these three mechanics is promoted.

### Next evidence gate

The candidate definitions are now frozen before queue-specific evaluation of
the public held-out partition.

That partition is not pristine at project level because it was previously
opened for LEFT/RIGHT capture-side validation.  However, the present
pair/opponent history selector was derived solely from discovery rows and has
not been fitted to held-out requester ranks or elapsed pair history.

Therefore the next result is classified as:

```text
SECONDARY_HELDOUT_DISCRIMINATOR
not
PRISTINE_INDEPENDENT_VALIDATION
```

The held-out comparison must preserve the exact frozen selectors above.  A
mismatch is recorded as a mismatch; candidate definitions must not be altered
after seeing held-out and then called validated.


## Frozen secondary held-out implementation

The queue-specific held-out implementation was added only after the discovery
result above was committed.

Tracked tools:

```text
tools/research/probe-postcapture-occurrence-round-heldout.py
tools/research/run-postcapture-occurrence-round-heldout.sh
```

The runner reuses the existing canonical held-out capture-side artifact when
present. If it is absent, it rebuilds only that artifact from the canonical
public manifest/index and read-only Corpus DB before evaluation.

The held-out probe:

```text
- re-runs the same six deterministic candidate-selector tests;
- reconstructs post-capture mutable state with canonical main code;
- evaluates only globally adjacent held-out rows;
- qualifies rows using the factual opponent only as a comparability condition;
- predicts opponent identity without using factual N+1 LEFT/RIGHT;
- compares the exact frozen five selectors;
- prints all rows where pair-history and attacker-history selectors diverge;
- prints all selector mismatches;
- does not alter candidate definitions.
```

Evidence label is fixed in advance as:

```text
SECONDARY_HELDOUT_DISCRIMINATOR
```

not pristine independent validation.


## Secondary held-out result

The frozen queue-history candidates were evaluated on the public held-out
partition after the protocol above was committed.

Unit tests:

```text
6 passed
```

Population:

```text
adjacent rows:             29
qualified rows:            12
dependency not qualified:  17
```

Result:

```text
STATIC_PRIORITY             7 / 12 exact
STATIC_CAP2                 7 / 12 exact
PAIR_OCCURRENCE_ROUND       8 / 12 exact
FRESH_ATTACKER_BOOLEAN      8 / 12 exact
ATTACKER_APPEARANCE_COUNT   8 / 12 exact
```

Candidate divergence:

```text
PAIR_OCCURRENCE_ROUND vs FRESH_ATTACKER_BOOLEAN:
  divergent selections = 0

PAIR_OCCURRENCE_ROUND vs ATTACKER_APPEARANCE_COUNT:
  divergent selections = 0

informative divergence rows = 0
```

Thus the held-out population still does not distinguish pair-level occurrence
rounds from attacker-level freshness.

One held-out row independently supports the need for elapsed history over static
priority:

```text
227887 / T25 / VCR 33 -> 34
prize=284
factual=237

STATIC_PRIORITY        -> 166  mismatch
STATIC_CAP2            -> 166  mismatch
all history-aware      -> 237  exact
```

However four qualified rows remain mismatches for every frozen selector:

```text
227887/T183 VCR 714->715 prize=240 factual=397 predicted=261

257776/T52  VCR 96->97   prize=76  factual=264 predicted=257

257776/T251 VCR 1724->1725 prize=325 factual=66  predicted=411

257776/T251 VCR 1739->1740 prize=388 factual=495 predicted=31
```

Therefore all three elapsed-history candidates are rejected as complete general
post-capture opponent selectors on this secondary held-out population.

They remain useful partial discriminators:

```text
STATIC baseline: 7/12
history-aware:   8/12
```

but no history-aware candidate is promoted.

## Important qualification-boundary correction

The current `dependency qualified` predicate proves that the *factual N+1
opponent* is:

```text
active
candidate-resolved
requesting the prize's new owner
strict-diplomacy permitted
rankable
```

It does **not** prove that every higher-ranked competing requester remains a
fully eligible post-capture pair under the complete production pair predicate.

In particular, a competing requester can still differ through pair-specific
mechanics such as:

```text
matching Friendly Code / HWM
pre-standard phase classification
captured-prize FC sensitivity
special side/phase state
other pair-composition blockers already represented by decide_ship_combat_pair
```

Accordingly, the four remaining rows must not yet be interpreted as proof of an
additional mutable queue cursor/order rule.

The next diagnostic is competitor-pair recomposition: for each wrong selected
competitor, reconstruct its pair with the prize under exactly the same
preserved-FC and guaranteed-nonmatching fresh-FC bounds already used by the
canonical post-capture pair-recomposition audit.

Only competitors that remain eligible and phase-resolved under those bounds are
true queue-order residuals.


## Targeted residual pair-recomposition diagnostic

After the 8/12 secondary-heldout result, a new diagnostic was added without
changing any selector:

```text
tools/research/probe-postcapture-heldout-competitor-pairs.py
tools/research/run-postcapture-heldout-competitor-pairs.sh
```

It targets exactly the four rows where all three frozen history-aware selectors
still disagree with factual N+1.

For each row it compares:

```text
predicted higher-ranked competitor vs captured prize
factual N+1 opponent          vs captured prize
```

through production `decide_ship_combat_pair`, using the same captured-prize
order treatment as the established pair-recomposition audit:

```text
captured mission/PE neutralized
captured diplomacy attack direction false
opponent strict attack direction true
preserved captured FC bound
guaranteed-nonmatching fresh symbolic FC bound
production HWM / PIA / C&I / Galactic Power / matching-FC composition
```

The probe also prints elapsed local VCR history through the capture VCR.

Interpretation:

```text
competitor definitely blocked
    -> previous requester ranking over-admitted the competitor;
       not a queue-order residual

competitor FC-sensitive / unresolved
    -> cannot infer queue ordering from this row yet

competitor definitely eligible under both bounds
    -> genuine remaining queue-order residual
```

No selector is changed or fitted by this diagnostic.


## Competitor-pair probe schema correction

The first targeted competitor-pair run did **not** reach
`decide_ship_combat_pair` for any of the four residual rows.

Observed shape:

```text
competitor:fc_sensitive_or_unresolved = 4
factual:fc_sensitive_or_unresolved    = 4

eligible=None
phase=None
reasons=None
```

That combination indicates a pre-decision schema bridge failure rather than an
actual unresolved pair decision.

Cause: the public capture projection contains:

```text
ship_id
captor_ship_id
captor_owner_id
current_opponent_ship_id
from_vcr_id
to_vcr_id
current_side
```

but intentionally does not carry the older archive diagnostic fields:

```text
race_id_after
hull_id_after
```

The targeted probe incorrectly attempted to read those absent fields.

Correction:

```text
captured prize hull after capture
    := prize hull from independently reconstructed ship entry

captured prize race after capture
    := captor race from factual captor appearance in capture VCR
```

The latter is the same factual source used by the canonical capture-transfer
replay to construct `ShipCaptureTransfer`.

The probe now also distinguishes:

```text
predecision_unresolved
fc_sensitive_or_unresolved
definitely_blocked
definitely_eligible
```

and prints explicit pre-decision `status/reason`.

The failed run produced no pair-eligibility evidence and does not alter any
selector conclusion.


## Corrected competitor-pair residual result

After the post-capture identity bridge was corrected, the targeted held-out
pair recomposition reached production `decide_ship_combat_pair`.

Summary:

```text
competitor definitely eligible       3
competitor FC-sensitive/unresolved    1
factual definitely eligible           4
```

Three rows are now genuine queue-order residuals under the currently
reconstructed pair mechanics.

### Genuine residual 1

```text
227887 / T183 / VCR 714 -> 715
prize=240
static/history predicted competitor=261
factual opponent=397

prior prize/261 pair occurrences = 0
prior prize/397 pair occurrences = 0
prior appearances 261 / 397       = 0 / 0

261 <-> prize:
  preserved captured FC: eligible STANDARD
  fresh captured FC:     eligible STANDARD

397 <-> prize:
  preserved captured FC: eligible STANDARD
  fresh captured FC:     eligible STANDARD
```

### Genuine residual 2

```text
257776 / T52 / VCR 96 -> 97
prize=76
static/history predicted competitor=257
factual opponent=264

prior prize/257 pair occurrences = 0
prior prize/264 pair occurrences = 0
prior appearances 257 / 264       = 0 / 0

257 <-> prize:
  preserved captured FC: eligible STANDARD
  fresh captured FC:     eligible STANDARD

264 <-> prize:
  preserved captured FC: eligible STANDARD
  fresh captured FC:     eligible STANDARD
```

The reconstructed strict requester order is:

```text
257, 134, 264
```

so factual opponent 264 is static rank 3 in this row.

### Genuine residual 3

```text
257776 / T251 / VCR 1724 -> 1725
prize=325
static/history predicted competitor=411
factual opponent=66

prior prize/411 pair occurrences = 0
prior prize/66 pair occurrences  = 0
prior appearances 411 / 66       = 0 / 0

411 <-> prize:
  preserved captured FC: eligible STANDARD
  fresh captured FC:     eligible STANDARD

66 <-> prize:
  preserved captured FC: eligible STANDARD
  fresh captured FC:     eligible STANDARD
```

The reconstructed strict requester order is:

```text
411, 66, 175, 181, 265, 317, 581
```

### Not yet a queue-order residual

```text
257776 / T251 / VCR 1739 -> 1740
prize=388
predicted competitor=31
factual opponent=495
```

Factual pair:

```text
eligible STANDARD under both captured-FC bounds
```

Competitor pair:

```text
preserved captured FC:
  engagement unresolved
  reason = right_fuel_unknown

fresh captured FC:
  engagement unresolved
  reason = right_fuel_unknown
```

Therefore this row remains pair-input/fuel unresolved and must not be used to
infer queue ordering.

## Consequence for history hypotheses

The three genuine residuals have:

```text
prior prize/competitor pair occurrences = 0
prior prize/factual pair occurrences    = 0
competitor prior VCR appearances        = 0
factual prior VCR appearances           = 0
```

Hence none of the frozen elapsed-history keys can distinguish the predicted
competitor from the factual opponent.

The remaining blocker is therefore not explained by:

```text
pair cap
pair occurrence round
fresh-attacker boolean
attacker appearance count
full pair eligibility under the current preserved/fresh captured-FC bounds
```

The next bounded discriminator is cursor/continuation state across capture.
A capture may preserve an already advanced queue cursor/order position rather
than restarting selection from the global static minimum.

The already-audited external c2ng original-order cursor is useful here only as
a frozen comparator; it remains EXTERNAL_IMPLEMENTATION evidence and was
already rejected as a general Nu model.
