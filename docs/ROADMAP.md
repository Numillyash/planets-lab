# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries and evidence policy remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `INFERRED` — reconstructed from observations or secondary material;
- `TESTED` — covered by a local deterministic scenario;
- `DIFF_VERIFIED` — matched against real NuHost transitions.

Unknown mechanics fail closed rather than being silently guessed.

## M0 — deterministic skeleton

Status: substantially complete.

- canonical full-information `GameState`;
- immutable turn-order contracts;
- deterministic seeded `HostEngine.step()`;
- baseline tests and scenario infrastructure.

## M1 — minimal sandbox

Status: in progress / largely implemented for the movement subset.

- Planets.nu JSON -> canonical state adapter;
- cargo transfer and colonization primitives;
- ordinary movement, fuel, movement mass and fuel proration;
- warp wells;
- tow / intercept / HYP movement phases;
- pre-movement repair and damage-limited speed;
- resolved ion-storm displacement;
- minimal planet economy;
- golden scenarios for implemented mechanics.

## M2 — economy and planetary host

Status: in progress.

- factories and supplies;
- taxes and happiness;
- natives and growth;
- Cyborg assimilation;
- mining and Trans-Uranium Mutation;
- riots / civil war / Amorphous / Bovinoid behavior;
- starbases;
- ship construction;
- differential validation for each clean planetary transition class.

## M3 — warfare

Status: partial.

- towing;
- minefields and web mines;
- combat;
- missions;
- fighters / torpedoes;
- ground combat;
- combat aftermath and repair interactions.

## M4 — race mechanics

Status: partial.

Race-specific behavior must be implemented through explicit ruleset modules/hooks rather than scattered `if race == ...` conditionals.

Target coverage includes at least Privateer gravitonic / rob behavior, Crystal webs, Cyborg chunnel, Fascist pillage/glory, Bird cloak/super-spy, Rebel RGA and Colonial fighter-sweep behavior.

## M5A — historical NuHost corpus

Status: active.

Build a large empirical corpus from current and completed Planets.nu games. This stage expands differential validation from a few manually inspected games to thousands of real player-turn transitions.

### Sources

Use three trust tiers:

- **Tier A — CURRENT / GOLDEN**: current games and private observations whose contemporary Host behavior is known;
- **Tier B — RECENT FINISHED**: recently completed games, used as the primary large validation sample;
- **Tier C — HISTORICAL**: older completed games, used for rare mechanics and for detecting Host/ruleset changes over time.

Start with the user's and collaborators' finished-game histories, then expand to selected public finished games when additional race/mechanic coverage is useful.

### Acquisition

- discover games with public `/games/list`, including username-based history discovery;
- retain only finished games for the historical corpus unless a command explicitly asks otherwise;
- fetch `/game/loadinfo` for players and the complete game settings object;
- prefer `/game/loadall` for finished games when it reliably returns the documented ZIP containing all turns of all players;
- use historical `/game/loadturn` as a fallback when `loadall` is unavailable or incomplete;
- all Planets.nu network access from the server is proxy-first and must use `PLANETSNU_PROXY_URL`; there is no silent direct-network fallback;
- cache immutable finished-game downloads locally and never download the same artifact repeatedly without an explicit refresh;
- raw corpus/cache data is gitignored; only compact manifests, schemas, tests and validation summaries belong in Git.

### Manifest / provenance

Every game must retain enough provenance to prevent mixing incompatible rulesets:

- game id, name and status;
- creation/end dates and final turn;
- public/private/custom flags, game/scenario/map type and win condition;
- full `loadinfo.settings` payload;
- deterministic settings hash;
- player slots, account ids, usernames, race ids and join/finish information;
- acquisition source and timestamp;
- corpus tier.

Differential reports must carry at least game id, turn, player perspective, entity id, settings hash and reason/classification.

### Indexing and mechanic mining

Normalize downloaded turns into player-perspective streams and consecutive `N -> N+1` transitions. Build classifiers that can retrieve clean samples by mechanic rather than by game, for example:

- ordinary / gravitonic / fuel-limited movement;
- tow, intercept and HYP;
- warp-well and ion-storm contacts;
- normal mines and Crystal web interactions;
- Privateer, Crystal, Cyborg and other race-specific mechanics;
- taxes, mining, native growth, assimilation and other planetary transitions;
- combat and post-combat state changes.

Ambiguous user-order effects must be classified or excluded rather than counted as simulator mismatches.

### Initial acceptance targets

1. Discover finished games for one or more usernames and write deterministic manifests.
2. Probe `/game/loadall` on one finished game through `PLANETSNU_PROXY_URL` and validate that the response is a ZIP before treating it as a corpus artifact.
3. Cache one full finished game and inventory its archive structure.
4. Normalize at least one game into player-turn streams and count consecutive transitions.
5. Produce corpus statistics by game, era, ruleset hash, race and candidate mechanic.
6. Scale discovery to the user's two accounts and two collaborator accounts, then selectively ingest public finished games for missing mechanics.
7. Preserve known real-game mismatches as permanent regression cases.

## M5B — Nu compatibility matrix

Status: started with movement differential validation.

- maintain mechanic-level `MATCH`, `MISMATCH`, `SKIPPED_AMBIGUOUS` and `UNSUPPORTED` outcomes;
- calculate compatibility by mechanic and ruleset/settings hash, not only globally;
- promote rules to `DIFF_VERIFIED` only from clean, causally attributable samples;
- detect version/ruleset splits instead of forcing historical games to match modern behavior;
- keep a compact golden regression subset in Git while the full corpus remains local.

Movement ordinary partial geometry is already validated against real NuHost observations; resolved repair/damage cap, warp-well capture and Class-4 ion-storm displacement are retained as regression evidence.

## M6 — training and AI

Status: future.

- scripted baseline agents;
- player-limited observation environment;
- historical imitation/value models;
- parallel self-play;
- policy/value training;
- use the historical corpus for offline evaluation and representation/value pretraining without leaking hidden information into player observations.
