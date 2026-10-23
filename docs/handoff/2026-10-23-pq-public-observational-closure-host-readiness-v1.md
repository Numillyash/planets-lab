# PR #289 — PPQ public control12 observational closure and independent Host evidence boundary

Date: 2026-10-23. Status: **DESCRIPTIVE_PUBLIC_PPQ_OBSERVATION_CLOSED_NOT_HOST_CAUSAL**.

This handoff marks the **end of the current bounded, observational-only six-game PPQ archive research**, not completion or `DIFF_VERIFIED` of the real NuHost construction/priority-point mechanism. Do not continue producing marginally different correlations from the identical 48 windows without an explicit prospective falsifiable question and justified new evidence.

## Authentic frozen runtime provenance

- Immutable run: [paired PPQ template specificity](https://github.com/Numillyash/planets-lab/tree/runtime-logs/runtime-logs/pq-paired-template-specificity-control12-p1-first48-max8/20261023T145257Z_a0f7ca22ec07).
- Branch `runtime-logs`, source `main` at `a0f7ca22ec0710a2c7fef030bf467ad2e1865ce5`, exactly matching the operator's source SHA. UTC timestamp 2026-10-23T14:52:57Z–14:53:02Z, `exit_code=0`, `interrupted_signal=null`, `missing_artifact_paths=[]`.
- Source report within evidence directory: `artifacts/pq/surveys/control12-ppq-p1-first48-max8.json`; no raw ZIP member or token data in evidence.
- Traceable machine-readable checkpoint (committed source-side, **not a copy of the full runtime report**): `validation/research/pq-public-control12-observational-closure.v1.json`, audited for internally consistent counts, provenance, explicit negative causal/independence flags by `tests/test_pq_public_observational_closure.py`.
- Frozen input scope: existing `validation/corpus/manifests/pq-public-control12-frozen-cohort.v1.json`, public finished PPQ games 591478, 620917, 621253, 621896, 680435, 680910, one selected perspective (slot 1), at most 48 archive candidate pairs and eight accepted T→T+1 embedded-consecutive windows per game. `CURRENT` public68 unchanged; neither prepared public100 (~26 GiB) nor M2 heldout32 entity files were reopened for the closure.

## Quantified source observations

| Measurement | Count |
|---|---:|
| Approved PPQ games represented | 6 |
| Archive filename-adjacent pairs inspected | 58 |
| Qualified embedded-consecutive + typed owner-current windows | 48 |
| Refused repeated embedded turns | 5 |
| Refused skipped-forward embedded turns | 5 |
| Windows with exactly one newly visible owner-current ship ID | 22 |
| Same-window newly visible ship full hull+engine match to unique prior base | 17 |
| Appearance windows with no unique current base (ABSTAIN) | 5 |
| Within the 17 eligible: new matched, **no persistent ship on same window matched** | 8 |
| Within the 17 eligible: new matched, **at least one persistent ship also matched** | 9 |
| Previously observed persistent ship-window comparisons, template matches | 12 / 97 |
| Persistent ship-window matches on windows with new ship appearances | 10 / 64 |
| Persistent ship-window matches on windows without new appearances | 2 / 33 |
| `player.prioritypoints` direction on appearance windows | 16 unchanged / 6 increased / 0 decreased |

Exactly eight matched new ship observations also have at least one qualified persistent reference comparison, with zero persistent template matches; nine match with some persistent matches. The five base-ambiguous cases are **unassessable**, not negative matches.

These are *window comparisons*, not distinct ships, accepted orders, independent game-turn experimental subjects, post-build inventories or a numerical model accuracy score. A ship can be reused across several overlapping windows, so iid-based p-values, confidence intervals or statistical significance claims are not justified. Existing ships are a useful within-window **reference**, not randomly selected non-build controls: some may themselves have been constructed at the same base in prior turns. Zero PP decreases does not establish zero PP expenditures because sources/awards/phase timing are unknown.

Earlier real field census in the same frozen research scope: 22/22 newly visible ship rows contained typed `hullid` and `engineid`; current base-before rows 25/25 contained typed `buildhullid` and `buildengineid`; selected player profile `prioritypoints` is typed before/after in all 22 candidate windows; all 112 own-current planet row observations have typed MC and D/T/M stock fields. The four checked direct starbase keys `hulls`, `engines`, `beams`, `torpedoes` were absent in the 25 base row observations. That **does not** prove where warehouses are or whether the server accepted a build order.

## Interpretation and explicit stopping criterion

**Supported:** Within the small exploratory permitted control12 selection, newly visible owned-current ship configurations correlate strongly with the configured hull+engine of a uniquely current owned prior starbase. The within-window reference makes the full match descriptively nontrivial in eight cases.

**Not supported:** 17 proven NuHost ship builds, PP spent on any individual ship, unique building base on all 22 windows, full own fleet roster, filled shipyard component warehouse, authenticated accepted shipyard order, order resolution at a specific Host phase, PPQ Stage2/Stage3 random selection, causal correctness of simulator, or `DIFF_VERIFIED` parity.

**Research decision:** Mark this bounded six-game public observational slice **complete at CORPUS_OBSERVED**. Do **not** repeat the same six-game source survey or add more posthoc association metrics without an independent, predeclared test that can falsify a mechanism. This is a scope-specific stop, not proof that all public archival data are exhausted.

The canonical human-dependent external-evidence issue is [#247 — independent NuHost / private-user evidence](https://github.com/Numillyash/planets-lab/issues/247), currently **PARKED**. This PR **does not reopen** issue #247, start a live game, or claim that suitable Host data already exist. Continue unrelated core corpus standard-mechanics work where it does not depend on this parked user input.

## Later controlled Host-readiness contract (only when authorized)

Before any prospective experiment, explicitly freeze a *single discriminating question* such as whether a **specific, independently server-accepted** PPQ base order produces a specified hull+engine on an authenticated Host boundary, against the alternative that public ship appearances are merely observations. Require, before looking at outcomes:

1. A consented/authorized isolated test perspective and game with predeclared PPQ rules, unique candidate base or an explicitly modeled competing-base design, controlled foreign interference, ship cap and visibility. Do not use other players' private data without permission.
2. Independently authenticated **server-accepted order contents** with receipt identity and acceptance timing. Client-side `save`, 2xx, `turnready` and local HMAC do **not** establish acceptance.
3. Independent witnessed Host turn-start/end boundary and phase identity, plus noninterfering before-and-after snapshots of **all relevant own** ships, planets, bases, bank/PP and component stock/queues; no partial old-info rows promoted to current.
4. Frozen expected outcome and negative/alternative hypotheses (no-build, build at competing site, ship merely newly visible). Predeclare permitted comparisons, event ordering, count rules and ABSTAIN conditions.
5. Privacy-safe local custody of raw evidence. Do **not** place actual player orders, secrets, API keys, HAR, token-bearing snapshots or raw `.trn` in public Git or `runtime-logs`. Publish only reviewed, typed and sanitized aggregate attestations via an approved one-command `tools/run-*-with-evidence.sh` wrapper when such a run is deliberately implemented.
6. Abort with **ABSTAIN** if any required order, independent receipt, timing, component inventory, relevant owner-fresh row or noninterference condition is untrustworthy. Do not infer missing inputs from observed new ship IDs or the previous 17/17 match.

Neither those independent Host inputs nor a controlled experiment has been provided or executed. There is therefore **no new server command for this closure PR**; the existing one-command runner convention applies once an authorized test is actually designed.

## Continuation and CI

PR #289 adds only a durable, privacy-minimal checkpoint, schema-consistency tests, this interpretation/methodology handoff, updated roadmap and full `docs/CONTINUE_HERE.md`/PR changelog. Check exact final-head CI, merge only green, verify actual post-merge main CI. A new chat should use these durable records rather than rediscovering the same 48 windows. Every later PR still requires complete continuation + changelog + technical docs in the SAME PR.
