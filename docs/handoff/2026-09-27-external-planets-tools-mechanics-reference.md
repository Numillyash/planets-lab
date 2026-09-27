# External Planets.nu clients/tools — mechanics and corpus reference catalog

Date: 2026-09-27

Repository: `Numillyash/planets-lab`

This document records external Planets.nu clients, replay tools, simulators,
plugins and analytics sites that may help reverse-engineer NuHost, expand the
historical corpus, or identify candidate edge cases.

It is deliberately stricter than the product-side catalog in
`Numillyash/planets-intel`.

## Evidence policy

External implementations are **candidate generators**, not Host evidence.

A third-party formula, simulation result or plugin behavior does not become
`DOCUMENTED`, `CORPUS_OBSERVED`, `TESTED` or `DIFF_VERIFIED` merely
because another tool implements it.

The admissible path remains:

```text
third-party implementation / UX clue
        |
        v
candidate rule / candidate edge case
        |
        +--> primary Planets.nu documentation, when available
        |
        +--> attributable Planets.nu historical/current observation
        |
        v
deterministic local test
        |
        v
differential verification
```

For corpus discovery:

```text
third-party game index/search result
!= corpus evidence
```

A discovered public game becomes evidence only after our own official
`loadinfo` / `loadall` acquisition, immutable archival and provenance checks.

## Priority source groups

## A. Combat / VCR references

### Kecupo/planets-vcr-sim

URL: https://github.com/Kecupo/planets-vcr-sim

Status observed 2026-09-27: actively developed Godot/GDScript project.

Important files:

```text
Scripts/Combat/combat_engine_thost.gd
Scripts/Combat/combat_rng_thost.gd
Scripts/Combat/combat_simulator_thost.gd
Scripts/Combat/combat_constants.gd
Scripts/Combat/combat_state.gd
Scripts/Combat/classic_vcr.gd
```

Highest-value `planets-lab` use:

- compare constants and per-shot/per-tick state transitions against our Classic
  resolver;
- inspect RNG assumptions and seeding;
- enumerate battle-state fields that another independent implementation found
  necessary;
- identify unsupported battle shapes or stacked-ship assumptions;
- generate candidate regression scenarios for any disagreement.

Do **not** copy formulas into the verified rules layer. First isolate a concrete
difference and find an attributable Nu observation that discriminates it.

No clear repository license was established in the quick review, so treat code
as reference-only.

### ChallengeSY/nu-replayer

URL: https://github.com/ChallengeSY/nu-replayer

Status observed 2026-09-27: actively maintained; Expat/MIT-style license file.

Relevant code areas include:

```text
VCRPlr.bi
NRSim.bi
NREngine.*
ParseData.bas
LoadTurn.*
MassTurn.bas
TestTurn.bas
```

The manual describes:

- complete public-game download/replay;
- arbitrary turn jumps/slideshow;
- a built-in VCR player;
- automatic "what-if" simulation summarized as outcome percentages;
- live Campaign Arena spectatorship using the public subset.

Lab use:

- compare VCR parsing and state normalization;
- inspect repeated-simulation methodology;
- identify combat inputs they vary in "what-if" mode;
- compare result distributions after our deterministic resolver has a bounded
  RNG model;
- mine public completed games as *discovery candidates*, followed by our own
  archive process.

### dcorboy/VGAPViewer

URL: https://github.com/dcorboy/VGAPViewer

Older GPL replay tool using Planets.nu historical turn downloads.

It reconstructs scene-level history for:

- ship movement;
- ship/starbase builds;
- explosions;
- minefields.

Lab use is mostly historical:

- independent evidence that old Nu API exposed per-turn snapshots in a practical
  downloadable form;
- candidate checks for historical endpoint semantics;
- possible event-sequence corpus ideas.

### polendri/nurep

URL: https://github.com/polendri/nurep

Unmaintained Rust completed-game replay viewer. It downloads turn information
from multiple player perspectives to reconstruct ownership history.

Useful for thinking about multi-perspective corpus completeness and completed
game acquisition. Not a mechanics oracle.

## B. API / turn-format references

### stefanreuther/c2nu

URL: https://github.com/stefanreuther/c2nu

MIT adapter between Planets.nu and classic PCC/VPA formats.

Important behavior:

- login/API-key handling;
- public game listing/info;
- arbitrary game/player/turn download;
- raw JSON dump;
- Nu -> classic RST/unpacked/VCR conversion;
- turn upload;
- local server/mock mode;
- explicit comments about structural differences between Nu JSON and classic v3.

High-value lab use:

1. cross-check field semantics when our archive adapter sees an unfamiliar
   shape;
2. compare historical turn-download behavior and fallback assumptions;
3. use its conversion logic to identify Nu fields that do not map cleanly to
   classic state;
4. build small fixture ideas for parser regression tests.

Even though the license is permissive, c2nu is still not a Host authority. A
format conversion assumption must not be promoted to mechanics without factual
validation.

### SteveDraper/Planets-Console

URL: https://github.com/SteveDraper/Planets-Console

Status observed 2026-09-27: very active; MIT.

Product-side value is high, but it also helps the lab because its documented
data model enumerates a broad Planets.nu turn surface and explicitly preserves
unknown/forward-compatible enum handling.

Useful lab tasks:

- compare entity/field inventories against our prepared projection;
- look for settings or Stellar Cartography fields absent from the feature index;
- compare map/reachability candidate semantics only as a discovery list;
- inspect their build-inference inputs as candidate military-score research
  dimensions.

Do not ingest their derived analytics into the evidence layer.

### Kecupo/PMS-Planets.nu

URL: https://github.com/Kecupo/PMS-Planets.nu

Offline client with explicit data classes/services for:

```text
GameConfig
TurnData
PlanetsData
StarshipData
MinefieldData
IonStormData
NebulaData
StarClusterData
RandAIConfig / RandAIPlanner
PlanetMath
PlanetsApi
GameStorage
```

Lab use:

- candidate field inventory;
- Stellar Cartography object semantics;
- planet/economy rule candidates;
- API request/response handling;
- order-generation candidate cases.

License not established in the quick review: reference-only.

## C. Movement / logistics / economy candidate implementations

### drgirasol/nupilot

URL: https://github.com/drgirasol/nupilot

The code contains a surprisingly broad automated ship planner:

- Collector / Distributor / Builder / Alchemy / Expander / Terraformer modes;
- fuel-factor tables;
- warp/engine range;
- gravitonic handling;
- warp-well detection;
- enemy-safety zones;
- cargo capacity and colony demand;
- primary/secondary destination selection;
- automated movement/order updates.

This is valuable because it exposes **edge cases worth testing**, especially:

- Alchemy mass/cargo timing;
- movement/fuel calculations around task automation;
- warp wells;
- gravitonic range;
- terraforming/hull-special detection;
- cargo balancing;
- interactions between current mission and automation.

Do not use its fuel tables or formulas as verified Host rules without our
normal discriminator process.

License caution: the repository root reports MIT, while the inspected
`nupilot.js` header declares GPLv3-or-later. Reference-only until clarified.

### j1o1h1n/vgaplanets-kesselrun

URL: https://github.com/j1o1h1n/vgaplanets-kesselrun

Apache-2.0 freighter-route automation.

Useful candidate behaviors:

- persistent multi-waypoint trade routes;
- per-planet resource target levels;
- load/unload decisions;
- HYP route support;
- Alchemy/gambling-ship handling.

For the lab this is mostly an **agent/planner heuristic reference**, not Host
mechanics. It can later inform scripted baseline agents after the underlying
movement/economy rules are independently verified.

### j1o1h1n/vgaplanets-sitrep

URL: https://github.com/j1o1h1n/vgaplanets-sitrep

Python/Textual situation-report project with modules such as `autotax`,
`econ`, `freighters`, `milint`, `minefields`, `messages` and
`starmap`.

Lab use:

- identify useful derived state features for future scripted agents;
- compare economy/tax heuristic inputs;
- candidate observation features for the future player-limited environment.

It should not influence Host-rule evidence labels.

## D. Message-derived mechanics evidence

### drgirasol/nuWebBounty

URL: https://github.com/drgirasol/nuWebBounty

The plugin detects Crystal Web drain / out-of-fuel messages and records ship,
owner, location and turn information.

This is directly useful to the corpus work because our current movement research
already has a narrow Crystal Web Drain evidence boundary.

Concrete lab use:

- enumerate exact message signatures;
- search immutable turn archives for attributable web-drain reports;
- tie reports to ship/location/turn transitions;
- expand the current single attributable Web Drain transition into a broader
  evidence population if the raw archives support it.

The plugin's parsing logic is a candidate locator only. The archive message is
the evidence.

### drgirasol/nusweepfc

URL: https://github.com/drgirasol/nusweepfc

The plugin inspects mine-scan messages, safe-passage text and the scanning
ship/friendly-code context.

Concrete lab use:

- identify exact mine-scan message signatures;
- search historical messages for Safe Passage / minefield relation evidence;
- correlate message turns with `relations`, minefields and moving ships;
- build bounded cases for diplomacy/mine-sweep interactions.

This may become particularly useful when the Host combat/diplomacy layer reaches
Safe Passage and alliance interactions.

## E. Plugin UX family as mechanics-discovery hints

### McNimble / chmeee.org

Catalog:
https://chmeee.org/#planets.nu

The official Planets.nu plugin documentation references McNimble's ecosystem.
Useful examples include:

- Redraw and Filter;
- Show Messages;
- Show Notes;
- Toolkit;
- FleetManagement.

Kessel Run still depends on Toolkit/FleetManagement, so these abstractions are
not just historical curiosities.

Lab relevance is lower than product relevance, but they can still reveal:

- which game states players repeatedly needed to compute;
- which spatial events/messages expose hidden mechanics;
- which fleet-level operations deserve scenario tests;
- legacy-client object fields that plugins relied on.

Treat all such behavior as a lead only.

## F. Public-history / corpus-discovery tools

### T-Continuum Analyser

URL:
https://analyzerplanetsnu.freeddns.org/

The earlier project review recorded useful capabilities:

- historical game browsing/replay;
- player/race statistics;
- game/corpus filtering by settings/features.

The site was not reliably fetchable by the automated crawler during the
2026-09-27 refresh, so no new unverified features are added here.

Lab use is potentially high for **discovery**:

1. find public games with rare settings or mechanics;
2. note candidate game ids;
3. fetch our own official `loadinfo` metadata;
4. decide whether the game fills a feature-index gap;
5. archive with the normal immutable corpus process.

Never import analyzer-derived values as mechanics evidence.

### derblondehans/player-affinity-tool

URL: https://github.com/derblondehans/player-affinity-tool

Uses public `/game/loadinfo` plus `/games/list`, reconstructs dead/replaced
usernames from join/drop events, and computes shared-game/turn-overlap matrices.

Primary value is in `planets-intel`. Lab value is narrower:

- identity reconstruction when a public historical game has replacement slots;
- participation-interval metadata when selecting perspective/turn coverage;
- avoiding false assumptions that a username occupied one slot for the whole game.

It is not a mechanics source.

## Secondary watchlist

These projects were also found during the GitHub sweep and may be worth
targeted review later:

- `stefanreuther/c2ng` / `PlanetsCentral/c2ng` — mature classic client/engine lineage;
- `cameronhotchkies/PlanuPlanu` / `PlanuKit` — old Planets.nu client/API framework;
- `DamonOehlman/planetoid` — old Planets.nu API helper;
- `wonderbird/planets-nu-scripts` — userscript collection;
- `hijk-planetsnu/NuPlugs` — plugin examples;
- `berapp/Planets.nu-Enemy-Ship-List-Plugin` — last-seen fleet tracking.

Review them only when a concrete unresolved mechanic/format/observation needs
another independent implementation or message signature.

## Cross-repository responsibility

| Topic | planets-intel | planets-lab |
|---|---|---|
| map layers / filtering | product owner | only candidate semantics |
| messages/events on map | product owner | mine message signatures for evidence |
| commander/player history | product owner | identity metadata only |
| API/turn ingestion | production adapter | evidence/corpus adapter and parser validation |
| historical replay | existing Time Machine | corpus/replay validation |
| logistics/freighter planning | advisory/local-draft UX | future scripted-agent heuristics |
| combat simulator | consume only verified subset | mechanics owner / differential validation |
| movement formulas | consume evidence-scoped rules | mechanics owner |
| game/settings discovery | display/use selected facts | feature-index/corpus owner |
| external tool code | license-gated reference | license-gated candidate generator |

## Concrete lab backlog created by this survey

### 1. Combat implementation comparison

Create a **read-only comparison audit**, not a transplant:

- inventory Kecupo VCR simulator constants/state transitions;
- inventory nu-replayer combat inputs and outcome simulation dimensions;
- map each candidate to an existing `planets-lab` rule/test;
- emit three buckets:
  - already equivalent;
  - candidate difference with no discriminator;
  - candidate difference with a historical discriminator available.

Only the last bucket should drive mechanics work.

### 2. Message-signature corpus audit

For immutable archives:

- Crystal Web drain / out-of-fuel signatures from nuWebBounty;
- mine-scan / safe-passage signatures from nuSweepFC;
- explosion/location messages from the wider plugin ecosystem.

Output must cite archive/game/turn/player/message ids and never create a mechanic
label from parser text alone.

### 3. API/format cross-check

Use c2nu and PMS only as independent implementation references to audit:

- historical turn addressing;
- result payload field shapes;
- VCR/state conversion;
- missing/unknown field behavior.

Any discrepancy should become a fixture/test against raw Nu payloads.

### 4. Corpus expansion by feature gap

Use T-Continuum Analyser and public game lists to discover games for missing
Feature Index dimensions.

Selection procedure:

```text
external discovery
-> official loadinfo
-> factual settings/profile classification
-> archive acquisition
-> deterministic feature-index rebuild
-> only then mechanic diagnostics
```

Prioritize rare settings actually blocking current research instead of growing
the corpus blindly.

### 5. Future scripted-agent references

After core Host coverage is sufficient for M6, use:

- nupilot;
- Kessel Run;
- SitRep;
- PMS RandAI/planner

as heuristic baselines for logistics/economy agents. These heuristics belong in
`ai/`, not in Host rules.

## License / authority quick notes

| Source | Quick license state | Lab posture |
|---|---|---|
| Planets-Console | MIT | field/architecture reference |
| nu-replayer | Expat/MIT-style | simulator comparison allowed; still validate mechanics |
| c2nu | MIT | API/format reference |
| Kessel Run | Apache-2.0 | future planner heuristic reference |
| VGAPViewer | GPL | concept/reference unless GPL obligations intentionally accepted |
| nupilot | root MIT vs JS GPLv3 header conflict | reference-only |
| Kecupo PMS | not established | reference-only |
| Kecupo VCR sim | not established | reference-only |
| SitRep | not established | reference-only |
| player-affinity-tool | nonstandard "free to use and modify" wording | reimplement concepts; do not assume standard license |

## Durable conclusion

The strongest new lab opportunities from this survey are:

1. **Kecupo VCR simulator + nu-replayer** for independent combat comparison;
2. **nuWebBounty + nuSweepFC** for message-driven historical evidence mining;
3. **c2nu** for API/turn/VCR conversion cross-checks;
4. **T-Continuum Analyser** for settings-targeted corpus discovery;
5. **nupilot / Kessel Run / SitRep / PMS** later as agent/planner heuristic
   references, not Host evidence.
