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

On an archive host with `PLANETSNU_PROXY_URL` configured:

```bash
bash tools/run-public-validation-corpus-acquisition.sh
```

The runner performs:

1. one public finished-game listing;
2. deterministic metadata filtering and stratified shortlist construction;
3. paced public `loadinfo` probes;
4. greedy coverage selection against the existing corpus;
5. immutable `/game/loadall` download/validation for selected games;
6. per-game index/statistics generation.

Default outputs:

```text
validation/corpus/manifests/public-validation-candidates.jsonl
validation/corpus/manifests/public-validation-selected.jsonl
validation/corpus/manifests/public-validation-combined.jsonl
artifacts/public-validation-corpus/selection-report.json
validation/corpus/index/public-validation-games.jsonl
validation/corpus/index/public-validation-stats.json
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
