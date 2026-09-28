# Public validation corpus expansion

Date: 2026-09-27

The existing archive corpus contains a small number of games and is useful for
mechanism discovery, but it is not sufficiently independent or ruleset-diverse
to serve as the final NuHost validation corpus.

Planets.nu documents `/games/list` as a public API that can enumerate finished
public games by status/type/scope. The acquisition path therefore does not need
private account history or an API key.

## Acquisition strategy

Do not choose games only by raw turn count. The selector first filters for
large finished public games and then probes public `/game/loadinfo` metadata
to maximize independent ruleset coverage.

Default discovery bounds:

```text
status=finished
scope=public
types=Classic/Standard/Custom, Team/MvM, Giant Melee, Championship
minimum turn=55
minimum slots=8
loadinfo probes=160
selected archives=36
```

Selection strongly prefers previously uncovered mechanics, especially:

- Campaign games with non-empty per-player `activeadvantages`;
- Campaign games with non-empty per-player `activehulls`;
- Campaign mode generally;
- Championship and unusual game types;
- Sphere and custom maps/rules;
- finite-fuel and modern Standard rulesets;
- settings such as Chained Intercept, Cloak & Intercept, Galactic Power,
  Moscow/SSC Intercept Interference, Quantum Torpedoes, H-Ross transfer,
  Super Transport fuel modifier, scout planet immunity and transfer variants.

The complete settings object is retained in the privacy-minimized manifest.
Player identity fields are not retained. Only the already allowlisted public
player-slot fields are stored, including race, active hulls and active
advantages.

## Runner

On an archive host with `PLANETSNU_PROXY_URL` configured, use the evidence
wrapper so the selection/index summary is published without publishing raw
loadall archives:

```bash
bash tools/run-public-validation-corpus-with-evidence.sh
```

The underlying acquisition runner is
`tools/run-public-validation-corpus-acquisition.sh`.

The runner performs:

1. one public finished-game listing;
2. deterministic metadata filtering and stratified shortlist construction;
3. paced public `loadinfo` probes;
4. greedy coverage selection against the existing corpus;
5. immutable `/game/loadall` download/validation for selected games;
6. per-game index/statistics generation;
7. copies only the safe selected/combined manifests and index/stat summaries
   into `artifacts/public-validation-corpus/evidence/` for runtime publication.

The generic runtime-evidence wrapper intentionally accepts only paths under
`artifacts/`. Raw loadall archives and the canonical validation cache are
therefore never included in the runtime evidence branch.

Default outputs:

```text
validation/corpus/manifests/public-validation-candidates.jsonl
validation/corpus/manifests/public-validation-selected.jsonl
validation/corpus/manifests/public-validation-combined.jsonl
artifacts/public-validation-corpus/selection-report.json
validation/corpus/index/public-validation-games.jsonl
validation/corpus/index/public-validation-stats.json
artifacts/public-validation-corpus/evidence/public-validation-selected.jsonl
artifacts/public-validation-corpus/evidence/public-validation-combined.jsonl
artifacts/public-validation-corpus/evidence/public-validation-games.jsonl
artifacts/public-validation-corpus/evidence/public-validation-stats.json
validation/corpus/cache/loadall/game-<id>.zip
```

The selected-only manifest is kept separate from the existing discovery corpus.
The combined manifest is generated deterministically for later feature-index
and held-out validation work.

## Evidence boundary

Selection of games may use public settings and player capability metadata, but
mechanical rules must not be tuned against every selected archive. Before
further NuHost promotion, split the enlarged corpus into discovery and held-out
validation subsets and keep the held-out subset out of rule reconstruction
until the corresponding rule is frozen.


## Runtime checkpoint — 2026-09-28

Second acquisition runtime source:

\`\`\`text
628ecd24c9df7202407eef3f6cb0ea8153828db0
\`\`\`

Published evidence:

\`\`\`text
runtime-logs/public-validation-corpus/20260928T002225Z_628ecd24c9df
\`\`\`

Network recovery worked. The earlier broad timeout population disappeared:
one archive required a retry and then indexed successfully. The final failures
are now all legacy/binary \`.trn\` normalization failures rather than network
timeouts.

Current compatible public archive population:

\`\`\`text
selected games             36
indexed games              22
failed games               14
snapshots               75787
transitions             75463
archive bytes       5948478285
settings hashes             22
\`\`\`

Successful bucket coverage:

\`\`\`text
campaign        11
finite_fuel      8
championship     3
sphere           0
\`\`\`

Failed bucket coverage:

\`\`\`text
campaign         8
championship     3
finite_fuel      1
sphere           2
\`\`\`

Thus the immediate compatibility gap is not networking; it is replacement of
legacy/binary archives, especially both selected Sphere games.

The 22 compatible games currently contain no non-empty per-player
\`activeadvantages\` / \`activehulls\`. Campaign capability coverage therefore
remains a separate corpus gap even though Campaign-mode coverage is already
large.

## Automatic failed-game backfill

Current acquisition reruns now backfill previous failures before ingest.

The backfill selector:

\`\`\`text
src/planets_lab/corpus/public_validation_backfill_cli.py
\`\`\`

uses the already-probed candidate manifest, preserves the original target bucket
counts, excludes every accumulated rejected game id, and selects untried
replacement games by ruleset novelty/size.

Persistent local rejection ledger:

\`\`\`text
validation/corpus/manifests/public-validation-rejected.json
\`\`\`

Safe evidence additionally includes the rejection ledger and backfill report.

The same command remains the recovery path:

\`\`\`bash
bash tools/run-public-validation-corpus-with-evidence.sh
\`\`\`

If a newly selected replacement is itself legacy/binary, the run may still end
non-zero; rerunning repeats the bounded backfill with that game added to the
rejection ledger. No rediscovery is required.

## Capture-side discovery partition

The current C5 blocker should not consume every new archive for fitting.

Discovery runner:

\`\`\`bash
bash tools/run-public-capture-side-discovery-with-evidence.sh
\`\`\`

The diagnostic deterministically partitions indexed public games by a stable
hash before inspecting combat outcomes:

\`\`\`text
~75% discovery
~25% held out
\`\`\`

The discovery runner scans only the discovery partition. Held-out games are
listed but not opened by the diagnostic.

Tracked output:

\`\`\`text
artifacts/public-capture-side/discovery-capture-side.json
\`\`\`

The report inventories attributable ship-capture continuations, factual
LEFT/RIGHT, capture-side carry, prior same-pair occurrences and relevant
ruleset metadata. It is explicitly labeled:

\`\`\`text
DISCOVERY_ONLY_NOT_PROMOTED
\`\`\`

A side rule must be frozen before the held-out partition is opened.
