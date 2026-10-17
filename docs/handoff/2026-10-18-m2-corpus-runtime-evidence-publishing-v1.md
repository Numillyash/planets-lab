# M2: return corpus reports to the established runtime-logs workflow

Date: 2026-10-18.

## Why this is a fix

The established tools/run-with-runtime-evidence.sh records gate.log,
metadata.json, and explicitly included artifacts, then publishes
them to the separate runtime-logs branch. Earlier research
runners had dedicated -with-evidence.sh entrypoints. The new M2
public100 coverage scripts accidentally lacked this wrapper, so
the user was unnecessarily asked to paste a large server report.

The original M2 profiler is still read-only and baseline68-only.
No existing mechanics code, DuckDB generation or CURRENT changes.

## Publish the ALREADY-COMPLETED mineral report (no rerun)

On the corpus server:

~~~bash
cd /root/projects/planets-lab
git fetch origin
git switch main
git pull --ff-only origin main
M2_CORPUS_COVERAGE_OUTPUT=artifacts/planetary/m2-public100-mineral-balance-v1/report.json \
  bash tools/run-m2-public100-economy-coverage-v1-with-evidence.sh --publish-existing
~~~

There is NO Docker run, DuckDB read or 26.65-GiB checksum in
this mode. The existing aggregate JSON is checked and published.
The new gate.log reports validation of the existing file, not
a reconstruction of the historic original full stdout.
The original report is unchanged.

After successful publication the wrapper prints the exact branch
and evidence path. These replace manual copy/paste of multi-KB
economic and mass-balance output.

## For NEW runs, publish automatically

Always choose a NEW report path:

~~~bash
M2_CORPUS_COVERAGE_OUTPUT=artifacts/planetary/m2-public100-next-measurement/report.json \
  bash tools/run-m2-public100-economy-coverage-v1-with-evidence.sh
~~~

This mode executes the normal immutable public100 diagnostic and
publishes both its gate.log stdout/stderr and aggregate JSON to
runtime-logs through the established wrapper. As always, the
26.65-GiB SHA256 read precedes bounded baseline68 sampling.

## Evidence publication gates

Only reports at artifacts/planetary/m2-public100-*/report.json
can be included. For --publish-existing the aggregate is
validated BEFORE entering the Git publishing wrapper.

tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py
requires the exact known top-level schema, exact immutable
generation SHA256 and name, read_only true, CURRENT_modified
false, a validated frozen baseline68 manifest, 32 heldout
games excluded from entity sampling, and noncausal/Host-unverified
flags. Nested data MUST be aggregate nonnegative integer
counters, never arrays, text notes, private game objects or
game/player/planet IDs. The one permitted nested model label is
checked against its fixed published name.

Failure prevents report publication, with the local original
file preserved. Source code changes still require GitHub PR+CI.

Synthetic tests cover successful aggregate verification,
unexpected raw records/secret-bearing values, incorrect corpus
SHA, heldout boundary violations, Host causality flag violations,
Bash syntax and unsafe path rejection.
