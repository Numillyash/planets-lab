# PR #288 — paired same-window PPQ template specificity after real existing-ship reference

Date 2026-10-23. Independent actual host evidence: `runtime-logs/pq-existing-ship-template-reference-control12-p1-first48-max8/20261023T135439Z_88759c16285c/artifacts/pq/surveys/control12-ppq-p1-first48-max8.json`, archived in the separate `runtime-logs` branch, source `main` commit `88759c16285c102da329f2d57145be9f953baf9a`. Metadata `exit_code=0`, `interrupted_signal=null`, no missing artifacts.

## Independent source facts verified

All six permitted public PPQ games, perspective slot1, frozen control12, 58 archive-filename adjacent pairs inspected, 48 admitted consecutive **embedded** game turns, five repeats and five forward skips refused. There were 22 newly visible owner-current ship identity observations in five games, zero in 620917. Of 22 posthoc single-ship appearance windows, 17/17 unique current prior base cases have matching configured prior `buildhullid/buildengineid` to the new ship's observed `hullid/engineid`, while five cases ABSTAIN for no unique current base. PP `player.prioritypoints` observed 16 unchanged, six increased, ZERO decreased. These are not 17 authenticated constructions or proof of a PP formula.

NEW actual #287 within-window, *not independently sampled* existing ship reference results:
- In **22 windows with** newly observed own fresh ship ID: 17 windows qualify for a single current base and persistent ship comparison, 5 ABSTAIN base ambiguity; 64 existing ship–window template comparisons across 17 qualified windows, **10 matches / 54 mismatches**.
- In **26 windows without** a new owned ship ID: nine qualify for an existing ship reference, while 14 ABSTAIN because base template was untyped and 3 because unique current base was missing; 33 existing ship–window comparisons in nine windows, **2 matches / 31 mismatches**.
- Across all qualified existing ship–window comparisons: 12/97 match (12.4%), compared to 17/17 new-to-observation ship–window matches in the prior audit. This is a descriptive contrast, not an iid odds ratio or a causal analysis. Ships and bases recur across neighboring windows; controls are *not randomly selected nor independent*. Existing ships themselves may have been built previously by the same base.

## New paired within-one-window diagnostic

New `src/planets_lab/corpus/pq_paired_template_specificity.py` pairs **two preexisting categorical reports from the same immutable two-member approved archive window**. It never reopens or scans extra ZIP members:
1. Existing `ship_appearance_noncausal_correlates`: only a single newly visible own-current ship and a single uniquely current prior base can yield a full hull+engine match, partial/total mismatch, otherwise ABSTAIN.
2. Existing `existing_owned_ship_template_reference`: for typed uniquely owned/fresh ships present at BOTH T−1 and T, compare the persistent ship's **BEFORE** hull+engine with that exact BEFORE base's configured hull+engine. Reference source ambiguity, missing typed specs, duplicate ship IDs or multiple bases fail closed.
3. New `paired_observational_category`: distinguish (a) new ship matches previous base AND no comparable persistent ships match it, (b) new ship matches AND some persistent ships also match, (c) new ship fails full match, or (d) strict source ABSTAIN. Also report only same-window integer typed persistent matches/mismatches and refusal count. A category does not claim Host accepted commands, actual build site, ship construction, PP spending, statistically independent negatives or NuHost phase parity. Only field/category names and counts leave corpus host: no individual IDs, hulls/engine values, PP, resource values, raw orders or private keys.
4. `src/planets_lab/corpus/pq_control_multigame_observation.py` integrates the pairing into existing bounded exploratory posthoc positive windows, adds fixed categorical per-game and total histograms, and marks `paired_categories_are_iid_independent_or_host_causal=false`. Distinct `existing_ship_template_reference_by_stratum` and old candidate / PP histograms remain unchanged.

Testing `tests/test_pq_paired_template_specificity.py` includes paired zero/some matching persistent ships, template mismatch, missing source and negative/boolean inconsistent counts, rejecting promoted causal flags, no-appearance abstain, and fully synthetic frozen-cohort ZIP integration including secret payload suppression. These tests are `TESTED synthetic`; no claim of actual post-PR paired categories before a new on-host report.

## One-command execution

After exact final-head PR CI green, merge and successful main post-merge push CI:

```bash
cd ~/projects/planets-lab
git pull --ff-only origin main && bash tools/run-pq-paired-specificity-with-evidence.sh
```

This tracked one-line launcher reuses prebuilt `docker compose run --rm lab` through `tools/run-pq-control-multigame-gate.sh`, and the unchanged `tools/run-with-runtime-evidence.sh` worktree publisher. It analyzes only the six approved games, perspective1, at most 48 filename adjacent pairs and eight actual embedded consecutive windows per game, reading two selected bounded .trn members at a time. The privacy-minimal JSON/log/status are auto-published under `runtime-logs/pq-paired-template-specificity-control12-p1-first48-max8/<timestamp>_<sourceSHA>/artifacts/pq/surveys/control12-ppq-p1-first48-max8.json` on the separate immutable evidence branch. No manual user terminal paste or raw archival payload in Git.

## Proof boundary and subsequent decision

A large share of newly visible own ships matching a base's configured template when older persistent ships do not would increase observational specificity of the configuration–appearance association. It would **not** show server-accepted build orders or all build components; direct `hulls,engines,beams,torpedoes` keys were absent on 25 checked base rows in previous audit but warehouses might be modeled elsewhere. No independent full owner roster, complete PP ledger, true accepted queue, base-selection evidence, or Host phase timeline is present. True NuHost `DIFF_VERIFIED` and PPQ late stage selection requires controlled authentic orders/snapshots and server execution through [issue #247](https://github.com/Numillyash/planets-lab/issues/247).

No public100 rebuild, no new games outside immutable control12, never open sealed M2 heldout32 entity records, leave `CURRENT` public68, unrelated C5/combat, signed V1/V2 client orders and IntelBoard production untouched. Each future PR must fully rewrite `docs/CONTINUE_HERE.md`, append `docs/PR_CHANGELOG.md`, update topic documentation, check exact-head green CI, then merge and verify main CI, and add a tracked one-command safe automatic evidence script for any new host run.
