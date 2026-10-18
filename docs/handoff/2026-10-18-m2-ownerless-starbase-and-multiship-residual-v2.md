# M2 residual-context V2: ownerless starbase planet links and multiship cargo balance

Date: 2026-10-18.

## Grounding: confirmed recovered runtime evidence

Published source: orphan runtime-logs branch,
\`runtime-logs/m2-public100-surface-context-recovered-v1/20261018T171553Z_30c1edc640be/\`
with **exit_code 0**, valid report.json and triage.json.
Source commit \`30c1edc640be56805f07f77b5cfd2c8979e5eaab\`.

Exact immutable public100 SHA256:
\`3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c\`.
Metadata-frozen perspective sample SHA256:
\`b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f\`.
Only baseline68 entity snapshots; heldout32 entity data sealed.

Actual observed outcomes over 13,023 planet×mineral pairs:

| Conditional default-mining comparison | Count |
|---|---:|
| Both predicted deltas exact | 11,813 |
| Only ground exact, surface residual | 915 |
| Only surface exact, ground residual | 33 |
| Neither exact | 262 |

Among the 915 ground-exact/surface-residual pairs, 652 (71.26%)
had an own ship observed at the site's coordinates in both archive
snapshots, versus 3,316/11,813 (28.07%) among fully exact
observations. Exactly 101 mineral observations had ONE co-site,
same-ship-ID cargo delta numerically opposite the modeled
planet surface residual: 46 neutronium, 19 duranium, 19
tritanium, 17 molybdenum. 641 residuals negative and 274 positive.

A large group of 427 residuals have abs magnitude >=101
(422 within 101..1000 and five >1000). These values are
observational, NOT Host-executed orders. Mineral observations
inside a planet/time window are correlated.

## Observed structural gap: missing starbase ownerid

The previous census reports **12,224** starbase rows without
explicit \`ownerid\` across the sampled pre/post archive records.
The original analyzer intentionally abstained from declaring
these bases owned, leaving explicit-starbase-at-planet counts
at zero. It would be incorrect to read those zeros as "no bases."

V2 keeps that STRICT evidence category unmodified and adds a
second, explicitly **weaker provenance** class:

- If \`starbase.planetid\` is a strictly positive integer and
  matches an authenticated owner-current planet in the **same
  perspective at the same turn**, and the base has **no
  ownerid**, record \`ownerless_base_planetlinked_...\`.
- This is merely a co-observed **planet link**. It does NOT
  claim to authenticate the starbase owner's identity or Host
  construction. Missing starbase \`infoturn\` is counted as a
  limitation; explicitly stale info is rejected.
- If \`starbase.ownerid\` explicitly contradicts the source
  perspective owner, abstain. Never overwrite the contradiction
  using the planet's owner.
- Reject ambiguous duplicate \`planetid\` records, including
  mixed explicit/ownerless copies.
- Explicit-owner and ownerless base evidence have separate
  counts; weak-to-strong changes are separately counted.
- Tech-level changes are counted ONLY when the relevant
  numeric fields are available in both linked base records.
  Missing tech fields abstain, never default to zero.

## Multiship cargo aggregation (additional hypothesis)

101 previously observed candidate matches required exactly ONE
same-ID co-site own ship with cargo delta equal to the negative
planet surface model residual. This ignores sites with 2+ ships
whose COMBINED cargo changes may match the residual even when no
single ship does.

V2 adds a distinct candidate, only when:

1. Planet coordinates in both snapshots are available.
2. Ship lists exist in both archived perspectives.
3. The **nonempty set of observed own ship IDs at the site is
   IDENTICAL at both snapshots**, there are 2+ ship IDs, and
   ALL relevant per-ship mineral cargo values are numeric.
4. The sum of their cargo deltas is the **negative** planet
   surface model residual, which must be nonzero.

This is a closed-set check *only among observed own ships*,
not proof that no enemy/cloaked/moving ships interacted, no
transfers via other locations occurred, or the Host executed a
particular order.

Both candidate classes are reported separately; a single
co-site ship cannot be counted as a multiship case. Missing
cargo, arriving/leaving ship IDs, stale ship infoturn,
ambiguous ship IDs and absent ship sections remain
explicit source-quality gates.

## Game-level clustering

In addition to the earlier 68-game aggregate residual histogram,
V2 adds a **zero-inclusive histogram across the same 68 baseline
games** for the following five counts:

- observed own ship at the site at both ends (surface residuals);
- exact opposite single ship cargo candidates;
- exact opposite 2+ ship cargo sum candidates;
- ownerless planet-linked bases at both ends;
- explicitly owned bases at both ends.

Bins: 0, 1, 2..5, 6..20, 21..100, >100.
NO game IDs, player IDs, ship IDs, coordinates, private orders
or per-planet mineral amounts are emitted. These histograms
allow us to assess whether the apparent association is strongly
concentrated in a handful of baseline games.

## Safety and unchanged claims

- A second residual classifier still reconciles exactly to the
  original mining/mutation profiler, fail-closed.
- \`triage.json\` checks internal denominators, provenance,
  and 68-game clustering counts. New weak base and multiship
  counters cannot exceed their qualified parent groups.
- Publication is restricted to aggregate numeric structures by
  \`tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py\`.
- Do not infer any game-specific Host order, mines formula
  correction, confirmed ship cargo transfer, base construction
  or independent statistical significance.
- Corpus database and CURRENT are read-only; C5, IntelBoard
  production, PR #28, and protected holdout32 unchanged.

## One NEW server run after CI and merge

This is NEW instrumentation over the SAME predetermined
136 baseline68 perspective-window sample. Old published V1
report and triage are preserved untouched.

~~~bash
cd /root/projects/planets-lab
git fetch origin
git switch main
git pull --ff-only origin main
M2_CORPUS_COVERAGE_OUTPUT=artifacts/planetary/m2-public100-surface-residual-context-v2/report.json \
  bash tools/run-m2-public100-surface-context-v1-with-evidence.sh
~~~

As before this hashes the existing 26.65-GiB immutable corpus,
decodes only the bounded baseline68 selection and
automatically publishes full gate.log, metadata.json and TWO
aggregated JSON reports to \`runtime-logs\`. No manual JSON
paste is needed.

**Actual V2 base and multiship counts remain UNKNOWN until that
run**; all new unit tests are synthetic and cannot substitute
for server evidence.
