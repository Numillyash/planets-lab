# Engine-core internet research pass — 2026-09-28

## Scope and evidence boundary

This pass systematically searched for VGA Planets / PHost / THost / NuHost engine cores, independent rules implementations, historical source/binary archives, simulators, API clients, and old development ecosystems.

**Critical boundary:** third-party code is not NuHost evidence. Every external implementation below is only a candidate-rule / edge-case generator until reconciled against primary Planets.nu documentation and attributable official Nu observations, then covered by deterministic and differential tests.

Repository state checked before this write:

- `planets-lab main`: `5d7489312eacc66772297923322510a4d1d1939b`
- `planets-intel feature/operational-ui`: `d575a8914bcd901878348859e2d7e74f4c3fdd31`

This pass preserves the existing M5/combat-order priorities. It does not promote any mechanics status.

## Executive findings

The most important result is that **PCC2 Next Generation / c2ng is much more than a client**. It is a large, active, BSD-licensed C++ codebase containing independent THost/PHost/NuHost combat simulation plus movement, Tow-aware prediction, Chunnel setup, minefield formulas, ion-storm forecasting, taxation/economy formulas, battle-order helpers, Nu API loading, historical state and extensive tests. For current planets-lab UNKNOWN areas it is the strongest external rules reference found in this pass.

A second important family is **JHOST/JPHost**, an old GPLv2 Java port of PHost 3. Its SourceForge history explicitly describes Host processing stages being implemented. This is potentially closer to a server-side engine than ordinary clients and deserves a full source-tree recovery/audit.

A third engine candidate is **OpenPlanets**, a GPLv3 Java project described as an open-source unofficial VGA Planets successor attempting to mimic PHost4 and VPA. It is old/planning-status, but should be archived and inspected before dismissal.

The original **TimHost/THost source was not found** in this pass. Historical binaries and documentation are, however, still discoverable under exact filenames, including multiple `HST322xx.ZIP` releases and older `vplns314.zip`. These should be archived for executable archaeology and version-differential test generation.

The public PHost site distributes PHost binaries/docs and PDK source, but this pass did **not** find an official full PHost 4 host-core source release. Do not equate PDK with PHost source.

## Priority A — engine/core candidates

### 1. PCC2 Next Generation / c2ng

- Name: PCC2 Next Generation / c2ng
- Repository: https://github.com/stefanreuther/c2ng
- Author: Stefan Reuther and contributors
- Current state: active; GitHub push observed 2026-08-22 during this pass
- Language: C++
- License: BSD 3-clause-style license in `COPYING.txt`; repository metadata reports NOASSERTION/Other, so preserve file-level license review
- Target generations: THost, PHost, NuHost, FLAK; client/server infrastructure for PlanetsCentral
- Source: complete public source
- Evidence authority: **REFERENCE ONLY / independent implementation**
- planets-lab value: **very high**
- planets-intel value: **high** for API/history/prediction/UX architecture

High-value mechanics files found directly in the source tree:

- `game/vcr/classic/hostalgorithm.cpp` — Classic/THost/NuHost-style VCR resolver; explicit `nuFlag`, RNG tables, beam/torpedo/fighter cycle, damage/capture handling
- `game/vcr/classic/pvcralgorithm.cpp` — PHost/PVCR combat path
- `game/vcr/classic/algorithm.cpp`
- `game/vcr/classic/battle.cpp`
- `game/vcr/classic/testapplet.cpp`
- `game/battleorderrule.cpp` — battle-value calculation from friendly code / Kill / PE / fuel / weapons
- `game/map/movementpredictor.cpp`
- `game/map/movementcontroller.cpp`
- `game/map/shippredictor.cpp`
- `game/map/chunnelmission.cpp`
- `game/map/minefieldformula.cpp`
- `game/map/minefieldmission.cpp`
- `game/map/planetformula.cpp`
- `game/map/planetpredictor.cpp`
- `game/actions/taxationaction.cpp`
- `game/nu/loader.cpp`
- `game/nu/turnloader.cpp`
- `game/nu/specificationloader.cpp`

Notable direct clues from `hostalgorithm.cpp`:

- fixed 119-entry random tables are present;
- Nu-specific behavior is selected through `nuFlag`;
- Lizard damage-limit handling and Nu planet special handling are explicit;
- capture vs destruction decisions are implemented;
- source contains explicit FIXME comments for uncertain Host behavior, which are valuable as a ready-made ambiguity list rather than evidence.

The project version history documents NuHost-specific simulator work including Fascist Fast Beams, Red Wind cloaked fighter bays, Saber Shield Generator, >10 bays, >100 shields, squadron, double beam/torp recharge, triple beam kill and elusive. It also records prediction fixes for towing, chunnel wrap, intercept chains, PHost mine laying, taxation/Hiss/terraforming, assimilation, ion storms and movement.

#### c2ng subsystem matrix

| subsystem | implemented? | important files | notes |
|---|---|---|---|
| combat | yes | `game/vcr/classic/*` | THost/PHost/NuHost simulation paths |
| battle order | partial/reference | `game/battleorderrule.cpp` | battle-value helper, not proof of full Host queue |
| movement | yes/prediction | `game/map/movementpredictor.cpp`, `movementcontroller.cpp` | independent client prediction |
| fuel | yes/prediction | movement/ship predictor code | audit formulas separately |
| tow | partial/prediction | ship prediction + release history | version history says prediction considers towing |
| intercept | partial/prediction | movement/ship prediction | historical intercept-chain fixes |
| warp wells | likely | movement prediction | inspect exact implementation next |
| mines | yes | `minefieldformula.cpp`, `minefieldmission.cpp` | laying/scooping/decay-related logic |
| web mines | likely | minefield types/formulas | inspect exact branches next |
| cloak | simulator/config support | VCR/spec/hull functions | needs targeted grep/audit |
| Loki | unknown in this pass | — | targeted source audit next |
| Rob | unknown in this pass | — | targeted source audit next |
| Super Spy | unknown in this pass | — | targeted source audit next |
| HYP | partial | movement code | targeted source audit next |
| Chunnel | yes | `game/map/chunnelmission.cpp` | prediction/setup support |
| Glory Device | unknown in this pass | — | targeted source audit next |
| Alchemy | yes/prediction | planet/ship formulas, version history | exact files to locate |
| planet economy | yes | `planetformula.cpp`, `planetpredictor.cpp` | broad prediction layer |
| natives | yes | planet formula/tables | native race/government tables present |
| taxation | yes | `game/actions/taxationaction.cpp` | colonist/native tax, riots, Hiss, Bovinoid handling |
| growth | yes | planet formula/predictor | exact Nu-vs-THost branching to audit |
| starbases | yes/prediction | base task predictor and dialogs | not Host engine |
| diplomacy | yes/client/config | alliance code | not yet audited for combat eligibility |
| friendly codes | yes | battle order/spec code | extensive client knowledge |
| race abilities | yes | hull functions/specification | Nu abilities supported |
| campaign advantages | yes/partial | Nu specification loader + simulator history | audit exact mappings |
| Stellar Cartography | partial | ion storms/map objects; Nu loader | broader objects need audit |
| ion storms | yes | `game/map/ionstorm*.cpp` | forecast/prediction |
| wormholes | unknown in this pass | — | targeted audit next |
| host configuration | yes | config classes + PHost support | broad configurable rule surface |

### 2. JHOST / JPHost

- Project: Vga Planets JHOST / JPHost
- URL: https://sourceforge.net/projects/jphost/
- Historical site: https://jphost.sourceforge.net/
- Author/maintainer shown by SourceForge: soronthar
- Last SourceForge update: 2013-02-21; development news mainly 2002–2004
- Language: Java
- License: GPLv2
- Status: abandoned/alpha
- Target: explicit **port of PHost 3**
- Source: SourceForge CVS/code existed; recovery/audit still required
- Evidence authority: REFERENCE ONLY
- planets-lab value: **high if source can be fully recovered**
- planets-intel value: low

Historical news states that implementation had multiple Host stages, messaging, starbase fighter/defense building and ghost-planet cleanup; the JMaster documentation uses PHost-compatible configuration concepts.

Next action: recover complete CVS snapshot, inventory processing stages/classes, and compare its phase ordering against PHost docs and current Nu UNKNOWN Host-order areas.

### 3. OpenPlanets

- URL: https://sourceforge.net/projects/openplanets/
- Status: Planning / abandoned
- Last update: 2013-04-22
- Language: Java
- License: GPLv3
- Database: MySQL
- Target: unofficial open-source VGA Planets successor; project description says it attempts to mimic PHost4 and VPA
- Source: SourceForge code browser advertised
- Evidence authority: REFERENCE ONLY
- planets-lab value: medium pending source audit
- planets-intel value: low/medium for architecture

Next action: retrieve source snapshot and determine whether an actual Host processing core exists or whether the project never progressed beyond scaffolding.

### 4. `xer0x/vgaphost`

- Repository: https://github.com/xer0x/vgaphost
- Public GitHub repo discovered by repository search
- Size: small (~76 KB repository metadata)
- README: only `hi`
- Status/source/license/implemented subsystems: **unknown**
- Evidence authority: UNASSESSED
- planets-lab value: potentially high solely because the repository name directly claims a VGA host; must inspect tree/history before classification

Next action: full tree + commit-history audit. Do not discard based on README.

### 5. Original TimHost / THost binaries and documentation

No original Host source was found.

Recoverable historical artifacts found:

- `HST32208.ZIP`
- `HST32209.ZIP`
- `HST32214.ZIP`
- `HST32215.ZIP`
- `HST32218.ZIP`
- `HST32221.ZIP`
- `HST32222.ZIP`
- older `vplns314.zip`
- historical references to `hst32222.zip`, `hstsup32.zip`, `host32.txt`

The Finnish Apajalista archive indexes multiple exact Host binaries, and old Donovan/Usenet material preserves filenames and former FTP paths.

Value:

- executable differential archaeology across Host versions;
- recovery of bundled docs/changelogs/config defaults;
- generation of controlled classic test games where legally/practically runnable;
- identifying rule changes that later Nu may have inherited or deliberately changed.

License: proprietary/freeware-era distribution; **REFERENCE/BINARY TEST ONLY** unless accompanying terms say otherwise.

## PHost status

Official PHost pages confirm:

- PHost 4.1h and 3.5g binary distributions;
- PVCR;
- PDK source;
- PUtils;
- extensive online documentation.

This pass did **not** locate an official full PHost host-core source release. PDK is a development kit/interface source, not automatically the host implementation.

Useful adjacent source:

- `phost/contrib` — GPLv2 collection, converted to Git in 2017;
- PDK repository;
- `pfcx`, `peng`, `mfq`, `explmap`, `logvpi`, etc.;
- Randgen source by Thomas Voigt / Dacian Hantig.

These can expose formats, configuration, randomization, minefield tooling and add-on semantics but must not be mislabeled as PHost core.

## Independent combat/simulator references

### PCC2/c2ng simulator

Highest-value source implementation found. See above.

### PVCR / BSIM 2.2

PHost documentation states PVCR implements PHost combat and exposes results for battle simulators. It explicitly names Thomas Voigt's **BSIM 2.2** as a simulator with PVCR built in.

Historical FTP indices also list `NEW-BSIM` / BSIM 2.2 and an older `sim.zip` battle simulator.

Value: historical independent combat behavior and regression generation, particularly useful for separating THost/PHost lineage.

### VPA source

- SourceForge VPA project is active-maintained enough to have 2022/2023 releases.
- Source packages such as `VPASRC-372.ZIP`, `VPASRC-3.70.ZIP`, older source archives are public.
- Language: Pascal
- License: SourceForge reports MPL 1.1
- Targets THost/PHost and, via c2nu, Planets.nu.

VPA is valuable for old formulas, file semantics, movement/combat helpers and historical client assumptions.

### Existing Nu projects already catalogued

Retain existing catalog entries and continue code-level audit rather than rediscovering them:

- Kecupo/planets-vcr-sim
- ChallengeSY/nu-replayer
- SteveDraper/Planets-Console
- stefanreuther/c2nu
- Kecupo/PMS-Planets.nu
- drgirasol/nupilot
- drgirasol/nuWebBounty
- drgirasol/nusweepfc
- j1o1h1n/vgaplanets-sitrep
- j1o1h1n/vgaplanets-kesselrun
- McNimble/chmeee.org
- T-Continuum Analyser
- VGAPViewer
- nurep
- NuPlugs

## Additional mechanics/client/API projects discovered or reconfirmed

### GNOME War Pad

- Repository: https://github.com/ldipenti/GNOME-War-Pad
- Source: public
- Historical VGA Planets client
- README exposes map layers for minefields, ion storms, scanner area, VCR viewer and Python console.
- Value: UX/history/file-format reference; possible formulas require source audit.

### Java VGA-Planets Client

- SourceForge: `jvc-client`
- Java/Swing
- GPLv2
- inactive
- direct CVS source tarball historically available
- Value: file formats and independent client semantics.

### JVPC

- SourceForge project `jvpc`
- Java libraries/basic client plus VPCheck and Blitz
- GPLv2/LGPLv2
- historical site says its authors derived VGA data-file knowledge from Pascal sources and built unpack/maketurn/util tooling.
- Value: file-format/parser cross-check.

### rust-planets-nu

- Repository: https://github.com/polendri/rust-planets-nu
- Rust
- abandoned
- API wrapper with request/parse layers
- explicitly documents incomplete `load_turn` support and lists fields such as maps, ionstorms, nebulas, stars, starbases, stock, relations, messages, notes, VCRs, races, hulls and advantages.
- Value: old API shape/version archaeology.

### Nu Planetary Management

- Repository: https://github.com/dotmanvgap/Nu-Planetary-Management
- Planets.nu planetary-management plugin
- Value: economy UX/formula candidate source; audit before use.

### VGA Planets AI / WOPR

- SourceForge project `vgaplanetsai`
- Python
- old Planets.nu API AI project
- modules include game selection, links/ranges, planet valuation, messages, combatants, planet processing and starbase building.
- Its `createlinks` design explicitly considered one-turn/two-turn/HYP ranges and notes warp wells as a required correction.
- Value: old API semantics and planning ideas, low mechanics authority.

### Planets.nu plugin ecosystem

Official Planets.nu help still links a large external plugin ecosystem. Examples include McNimble map/message/note tools and Gravitonic Connections. GreasyFork still indexes Planets.nu scripts including nuSweepFC, HYP circles, gravity-well movement, clone checking and ion-storm protection.

Value: candidate edge cases, API/client fields, UX precedents. Not Host evidence.

## Classic documentation / archaeology sources

### Donovan's Host help / Infolist

Donovan's help pages explicitly target Host 3.22.047 and preserve formulas and Host order. The Infolist changelog says it replaced tax/growth/overpopulation/happiness information with actual Host formulas and movement/fuel formulas with Host 3.22.026 formulas.

Authority: secondary/historical, not source code; useful for generating discriminators and locating version boundaries.

### Stefan Reuther VGA Planets timeline

The timeline reconstructs Host/PHost/PCC/VPA release histories and specific rule changes. It is particularly useful for identifying when a behavior entered THost and therefore which historical binary versions can discriminate it.

### PlanetsCentral file-format documentation

Maintained file-format documentation includes implementation details and, in places, notes updated from PHost source. It is valuable for binary/API format archaeology.

## Test-suite findings

No standalone official THost/PHost regression suite was found in this pass.

However, c2ng contains a substantial test tree and combat test infrastructure, including `game/vcr/classic/testapplet.cpp`; source comments reference benchmark/test fixtures such as `tests/vcr/vcr2.dat`. The repository should be mined for fixture provenance and expected-output tests.

Historical local test-game workflows are documented for original Host + CPlayers. This makes old Host binaries potentially usable as black-box reference executables for Classic-only differential experiments, subject to licensing/runtime constraints.

## Corpus/data discoveries

- PlanetsCentral remains a live PHost hosting environment and therefore a potential source of public PHost comparison games, but not NuHost evidence.
- T-Continuum and other external game indexes remain discovery-only; official Planets.nu acquisition is still required before a game enters our corpus.
- Historical FTP/file indexes preserve many utility and Host filenames even when original FTP servers are gone. Exact filename search should be used for Wayback/mirror recovery.

## License concerns

- c2ng: BSD-style permissive, but verify file-level exceptions before reuse.
- JHOST: GPLv2 — reference only unless deliberate compatible reuse is desired.
- OpenPlanets: GPLv3 — reference only for this project.
- VPA: SourceForge reports MPL 1.1.
- phost/contrib: GPLv2; individual subprojects may carry their own notices.
- original THost binaries/docs: proprietary/freeware-era; binary/reference use only pending terms.
- old utilities with no clear license: REFERENCE ONLY.

Even permissive code should not be transplanted automatically. Candidate extraction + independent Nu verification remains preferred.

## Dead ends / negative findings

- No verified public NuHost server source was found.
- No verified original THost/TimHost source was found.
- No verified full official PHost host-core source release was found; public PDK/contrib source is not the same thing.
- Generic web search is noisy for the words Host/Planets; repository/source-tree inspection is mandatory.
- Several GitHub repositories have names suggesting VGA Planets but minimal/no README; they need tree inspection before classification.

## Archive/download backlog

Archive locally for future code-level analysis:

1. c2ng repository at a pinned commit plus source release tarball.
2. JHOST/JPHost complete CVS snapshot and documentation.
3. OpenPlanets complete SourceForge source snapshot.
4. VPA latest source plus historically significant source releases.
5. phost/contrib repositories: PDK, randgen, pfcx, mfq, peng, explmap, logvpi.
6. PHost docs for 3.x/4.x plus PVCR documentation.
7. Historical Host binaries: HST32208/209/214/215/218/221/222 and any later 3.22.04x packages found.
8. `vplns314.zip`, `doc314.zip`, `host32.txt`/Host docs.
9. BSIM 2.2 and older `sim.zip` if redistributable/downloadable.
10. old Infolist/Donovan Host-order/formula snapshots.
11. JVPC and Java VGA-Planets Client source tarballs.
12. old Planets.nu API wrappers such as rust-planets-nu.
13. exact source snapshot of `xer0x/vgaphost`.

Store third-party archives outside immutable official-Nu evidence directories and record URL/date/hash/license.

## Top next investigations

1. **Deep-audit c2ng rules tree**: extract exact NuHost branches and build a mechanics-to-file matrix for combat ordering, left/right assignment, capture, movement, Tow, Intercept, HYP, Chunnel, mines/webs, Loki/cloak, Rob/Super Spy, taxation/growth and campaign advantages. Convert only disagreements/unknowns into bounded planets-lab candidate tests.
2. **Recover JHOST source** and map its full Host phase pipeline. It may be the best surviving open server-side PHost-derived implementation.
3. **Audit `xer0x/vgaphost` and OpenPlanets** to determine whether either contains a real processing core.
4. **Build historical THost binary archive** with SHA256 + bundled docs/changelogs and identify versions usable for controlled black-box tests.
5. **Search exact legacy filenames/authors** through Wayback/FTP/CD mirrors: BSIM, SIM, Host packages, CPlayer sources, VPR source, old PHost packages and deleted project tarballs.

## Actionable implications for current planets-lab UNKNOWN areas

- **Combat engagement/order:** c2ng `battleorderrule.cpp` plus simulator object roles can generate candidate battle-value/side/order tests, but full Nu queue behavior still requires official Nu discrimination.
- **Capture/survivor:** c2ng HostAlgorithm has explicit capture/destruction logic and uncertainty comments; compare directly against current C3/C5 corpus rather than importing.
- **Special combat abilities:** c2ng has explicit Nu simulator support for multiple campaign/ship abilities; use it to enumerate missing fixtures.
- **Tow/Intercept/Chunnel:** c2ng's prediction history contains known fixes and edge cases, useful for selecting unresolved topology cases.
- **Economy/natives/tax:** c2ng has executable independent formulas and effectors (Hiss, Bovinoid, riots, terraforming/assimilation support); this is a strong starting point for a future economy corpus pass.
- **Minefields/ion storms:** c2ng exposes formula/prediction modules suitable for differential candidate generation.
- **API/format:** c2ng Nu loader + c2nu + old Rust/Java wrappers can cross-check field semantics and historical API evolution.

No mechanics evidence labels are changed by this document.
