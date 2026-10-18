# M2: recover completed surface-context run without reading DuckDB again

Date: 2026-10-18.

## Actual incident, published evidence and source of failure

The corpus server completed the full public100 read-only analysis and
created its aggregate source report. Exact published evidence:

- Runtime branch: `runtime-logs`
- Run: `m2-public100-surface-context-v1/20261018T163513Z_fae172443492`
- Source HEAD: `fae172443492fc186c93b6a683c4a712d364da1f`
- Under the run: `artifacts/planetary/m2-public100-surface-residual-context-v1/report.json`.
- The immutable DB SHA256 and 136-pair frozen selection both matched.
- `CURRENT_unchanged: true` and `aggregate_report_written: true`.

The only failed step was the HOST-side offline
`tools/diagnostics/m2_surface_context_triage_v1.py`. Its
`from planets_lab.corpus.m2_surface_context_triage import ...`
triggered `planets_lab/corpus/__init__.py` which transitively imports
`feature_index.py` requiring third-party `duckdb`, unavailable in
the server's system Python. This is a packaging/bootstrap error, NOT
a corpus or mining-analysis failure. Runtime evidence correctly
published the failed run with `exit_code: 1` and a missing
`triage.json`. Do not call that end-to-end run successful.

## Actual scientific findings already present in the published report

The published `report.json` still confirms the exact disjoint
cross-tab 11,813/915/33/262 from baseline68:

| Covariate | Both ground+surface exact (11,813) | Ground exact, surface residual (915) |
|---|---:|---:|
| Same-site own ship observed before AND after | 3,316 (28.07%) | 652 (71.26%) |
| Structure/tax control change | 4,893 (41.42%) | 545 (59.56%) |
| Exactly one opposite same-ID co-site ship-cargo delta candidate | no nonzero residual to oppose | 101 (11.04%) |

Of 915 surface residuals, **641** are negative and **274**
positive; they are net deviations from modeled mining, not necessarily
negative or positive total surface stock changes. Reported ship
presence is correlated with residuals but NOT proof of transfers.
The candidate 101 includes repeated planet/mineral observations and
has no authenticated pre-Host orders.

The starbase owner guard abstained on 12,224 starbase records with
no explicit `ownerid`; that does not establish that no bases exist.
No starbase causality or build-cost formula can be inferred here.
Observations cluster in the same 68 baseline games (47 games have
at least one ground-exact/surface-residual observation, 21 have none).
No statistical independence is claimed.

## Repair

The CLI now uses only standard-library `runpy.run_path` to execute
the pure repository source `src/planets_lab/corpus/m2_surface_context_triage.py`
WITHOUT importing `planets_lab.corpus` or its DuckDB-requiring
package initialization. A regression test invokes the real CLI with
`python -I -S` (site packages inaccessible); the test must pass.

The existing inner and outer evidence runners both now support
`--complete-existing`. It:

1. Requires the already-written `report.json` and no
   `triage.json`, refuses overwrites.
2. Prevalidates the known aggregate-only report schema, DB SHA,
   heldout32 exclusion and no Host causal claims BEFORE handing
   it to the evidence publisher.
3. **Does not run Docker**, checksum 26.65 GiB, reconstruct
   any archived member, access the game API, or change `CURRENT`.
4. Generates the missing aggregate-only `triage.json` locally
   with the fixed standard-library CLI.
5. Publishes a separate **recovery** run with both aggregate JSONs,
   `gate.log`, `metadata.json` to `runtime-logs`. The old
   failed run and its original evidence stay unchanged.

## One recovery command (after merge)

On the existing corpus server with its already-completed report:

~~~bash
cd /root/projects/planets-lab
git fetch origin
git switch main
git pull --ff-only origin main
bash tools/run-m2-public100-surface-context-v1-with-evidence.sh --complete-existing
~~~

Do NOT call the no-argument variant on the same report path: that
is for new corpus measurements and refuses to overwrite any
existing report.

The server prints the exact `runtime-logs` recovery path.
There is no need to paste large JSON output. The shell and
standalone bootstrap regressions are protected by CI.

No changes to C5, public100/heldout32, canonical combat, corpus
CURRENT, production IntelBoard or draft PR #28.


## Follow-up: auto-detect recovery when the option was omitted

A second server attempt, after PR #233 had been pulled, printed
\`ERROR: existing artifact detected; refusing overwrite\`.
Inspection of the exact shell text found that this message can
only come from the normal no-argument branch; it cannot come from
the explicit \`--complete-existing\` branch. The caller therefore
entered the script without the recovery flag (or invoked a
different command). This is a usability issue, not another
corpus/data error.

Both shell entrypoints now auto-detect **existing nonempty
report.json and absent triage.json** when no arguments are passed.
They automatically select the *same* safely validated
\`--complete-existing\` recovery path. This guarantees that the
accidental bare command is safe and does not initiate a second
26.65-GiB corpus run. If both files exist, or the report is
empty, the fail-closed overwrite guard remains in force.

A regression test runs the actual outer shell entrypoint without
arguments, with a valid existing aggregate report, and intercepts
the evidence shell before any push or heavy work. It also tests
a fresh path and refusal to overwrite an already-present triage.

After merge, **either** of the following works for this precise
incomplete-run situation:

~~~bash
bash tools/run-m2-public100-surface-context-v1-with-evidence.sh
~~~

or

~~~bash
bash tools/run-m2-public100-surface-context-v1-with-evidence.sh --complete-existing
~~~

The explicit second form is clearer, but both automatically
preserve the original report and publish only the recovered
derived triage. No manual JSON output or deletion required.
