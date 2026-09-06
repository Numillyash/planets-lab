# Cross-repository combat mechanics inventory

Date: 2026-09-07

This document defines the migration boundary for combat mechanics already developed in `Numillyash/planets-intel` and their intended canonical home in `Numillyash/planets-lab`.

GitHub remains source of truth. Re-check both source refs before implementation because either repository may advance after this checkpoint.

## Source snapshots

`planets-lab` base for this inventory:

```text
main = 1cc81f36f66c5cbcaa38bf720be22e188a4ed05c
```

`planets-intel` inspected source:

```text
branch = feature/operational-ui
HEAD   = 41e52424740aad1af298516eb9f45916f41908c7
```

The latest dashboard HEAD contains later UI work. Combat provenance below therefore names individual historical combat commits where useful, but migration must read the current files at the current source branch before copying code.

## Architectural objective

Combat mechanics must have one canonical pure implementation.

Target dependency direction:

```text
planets-lab pure combat mechanics
        ^
        |
planets-intel adapters / API / DB / UI
```

Do not make `planets-lab` depend on the dashboard service, SQLAlchemy models, HTTP APIs, or database sessions.

Do not initially combine combat-resolution migration with reconstruction of the Host battle-order/engagement-selection phase. These are separate milestones.

## Source classification

### A. Pure Classic VCR core — migrate first

Source:

```text
planets-intel/backend/app/services/vcr_replay.py
```

Current source properties:

- deterministic NuHost Classic VCR replay;
- Python adaptation of the PCC2 Next Generation (`c2ng`) Host/NuHost Classic VCR algorithm;
- stdlib-only imports at module boundary (`copy`, `dataclasses`, `typing`);
- embeds the validated Classic 119-entry random tables;
- owns combat data structures such as `BeamSpec`, `TorpedoSpec`, `CombatObject` and replay-state/result types;
- accepts generic mapping payloads rather than dashboard ORM models;
- explicitly fails unsupported cases through `ReplayUnsupported`;
- does not mutate factual `CombatObservation` data.

This is the strongest candidate for near-verbatim extraction into `planets-lab`.

Proposed destination:

```text
src/planets_lab/rules/combat/__init__.py
src/planets_lab/rules/combat/classic.py
```

If the single module becomes unwieldy during migration, split only along behavior-neutral boundaries after parity is established. First port should minimize semantic edits.

### B. Nu payload / terminal-state adapter — migrate after pure core

Source:

```text
planets-intel/backend/app/services/vcr_replay_nu.py
```

Responsibilities include:

- translating Nu payload/catalog data into Classic resolver inputs;
- resolving terminal state because factual Nu VCR payloads may retain stale post-combat quantities;
- narrow pre-fight shield inference;
- Nu-specific validation and unsupported-case handling.

Classification:

```text
adapter + validation oracle
```

Proposed destination after core parity:

```text
src/planets_lab/validation/combat_nu.py
```

Nu catalog/static-data access should be adapted to `planets-lab.data` rather than importing dashboard services.

### C. Replay trace / differential diagnostics — validation only

Source:

```text
planets-intel/backend/app/services/vcr_replay_trace.py
```

Responsibilities include source-loaded replay state, seed/round tracing, event invariants and independent Nu replay comparison.

Classification:

```text
diagnostic / oracle, not core simulation rule
```

Proposed destination:

```text
src/planets_lab/validation/combat_trace.py
```

Only migrate portions that remain useful once the pure core and Nu adapter exist.

### D. Arbitrary battle / sequence simulator — split before migration

Source:

```text
planets-intel/backend/app/services/battle_simulator.py
```

This file is mixed-purpose. It currently imports:

```text
sqlalchemy.select
app.db.session.SessionLocal
app.models.game_rule_catalog.GameRuleCatalog
battle_simulator_planet
vcr_replay
vcr_replay_nu
vcr_replay_trace
```

It also contains reusable mechanics that should not remain coupled to those dependencies:

- arbitrary ship combatant payload construction;
- explicit Classic seed execution;
- multi-seed odds across Classic seeds;
- queued battle sequences;
- damage/ammunition/crew/shield carry-over;
- Federation between-fight shield recovery;
- Lizard combat handling toggles/context;
- right-side carrier-balance handling;
- Galactic Power side constraint;
- ship-vs-planet sequence integration.

Migration rule:

1. do not copy SQLAlchemy/session/catalog access into `planets-lab`;
2. extract pure sequence/state-transition functions only;
3. replace dashboard catalog lookups with explicit input/static-spec arguments;
4. preserve unsupported/fail-closed boundaries;
5. port special rules with their evidence status rather than treating every simulator option as equally verified.

Proposed destinations:

```text
src/planets_lab/rules/combat/sequence.py
src/planets_lab/data/...                 # only if a small static-data adapter is needed
```

### E. Planet/starbase combat carry-over — migrate after ship sequence parity

Source:

```text
planets-intel/backend/app/services/battle_simulator_planet.py
```

Reusable behavior includes:

- persistent planet/starbase combat state;
- defense loss;
- starbase fighter carry-over;
- generated planet fighters;
- recalculation of planet combat beams/bays/mass;
- multi-wave carry-over where state can be reconstructed.

Important guardrail: current code deliberately fails closed when a surviving damaged starbase does not expose enough information to reconstruct the persistent defense/tech/base-damage split exactly.

Proposed destination:

```text
src/planets_lab/rules/combat/planet.py
```

Do not widen the supported state space during the initial port.

### F. Dashboard-only data/UI layer — do not migrate

Do not copy these categories into the pure simulator:

- SQLAlchemy sessions and queries;
- `GameRuleCatalog` ORM access;
- API route/request/response models;
- `CombatObservation` persistence models;
- dashboard-specific enrichment/rendering/UI state;
- Battle Planner presentation logic.

After `planets-lab` becomes canonical, `planets-intel` should call/adapt the shared pure mechanics rather than maintaining a second resolver implementation.

## Existing regression/evidence assets

The dashboard repository already contains a substantial combat test surface. Relevant families include:

```text
backend/tests/test_combat_corpus_coverage.py
backend/tests/test_combat_chain_regression.py
backend/tests/test_combat_planet_chain_regression.py
backend/tests/test_combat_lizard_regression.py
backend/tests/test_combat_lizard_rule_sensitivity.py
backend/tests/test_combat_federation_regression.py
backend/tests/test_combat_federation_rule_evidence.py
backend/tests/test_combat_right_balance_evidence.py
```

and corresponding scripts including:

```text
backend/app/scripts/combat_corpus_coverage.py
backend/app/scripts/combat_chain_regression.py
```

Combat-corpus provenance includes:

```text
7feb0f044ad356755505a0d7701a1c0e08c6f379
  feat: add factual combat corpus coverage diagnostic

60828352a89517c7d12a7d7ee4aaaebaf0ffb682
  fix: preserve unknowns in combat coverage audit
```

Historical runtime checkpoints previously recorded for this code include a full supported Classic VCR corpus and consecutive survivor-chain matches. These are useful evidence, but the migration acceptance criterion is a fresh parity run against the current accessible corpus, not a hardcoded historical count.

## Evidence status / support boundaries

### Strongly reusable foundation

Classic pairwise VCR resolution has both deterministic tests and historical factual-corpus differential evidence. Treat the migrated resolver as a high-confidence existing implementation subject to parity verification, not as an algorithm to reinvent.

### Sequence carry-over

Historical same-location consecutive-battle regression evidence exists for damage, crew, torpedoes, fighters and shields. Re-run this after migration.

### Lizard

Dedicated regression and sensitivity suites exist. Preserve the existing distinction between rules supported by factual transitions and sensitivity-only behavior.

### Federation

Dedicated regression/evidence suites exist. Historically, the `+3` carrier-bay rule has factual keyed evidence. Other Federation sequence details such as damaged-start weapon continuity and isolated 25% between-fight shield recovery have weaker/limited factual isolation and must remain explicitly marked accordingly until refreshed evidence says otherwise.

### Right-side carrier balance

Keep evidence labeling explicit. A simulator option existing in code is not by itself proof of NuHost semantics. Historical right-balance evidence was weaker than the Classic core evidence.

### Planet/starbase chains

Useful implementation and regression infrastructure exists, but historical factual repeated-planet coverage is substantially thinner than ship-vs-ship coverage. Preserve fail-closed behavior.

### Unsupported combat mode

The current Classic replay implementation does not imply support for every Nu combat RNG/ruleset. Extended/non-Classic combat (`combatrng=1` in existing tests) remains unsupported unless independently implemented and verified.

## Third-party license requirement

`vcr_replay.py` is derived from PCC2 Next Generation (`c2ng`) Classic Host VCR code.

Required attribution currently recorded in `planets-intel/THIRD_PARTY_NOTICES.md`:

```text
Copyright (c) 2001-2023 Stefan Reuther & contributors
License: BSD 3-Clause
Source project: stefanreuther/c2ng
```

`planets-lab` currently has no `THIRD_PARTY_NOTICES.md` at this checkpoint.

Therefore the first code-migration commit must add a notice carrying the applicable BSD 3-Clause attribution/disclaimer. Do not copy the derived core without that notice.

## Proposed `planets-lab` package layout

The current repository already separates `rules`, `sim`, `validation`, `data`, and `corpus`. Combat should follow that architecture:

```text
src/planets_lab/rules/combat/
    __init__.py
    classic.py          # pairwise deterministic Classic resolver
    sequence.py         # explicit battle-sequence carry-over
    planet.py           # planet/starbase combat carry-over

src/planets_lab/validation/
    combat_nu.py        # Nu payload/catalog adapter and terminal-state comparison
    combat_trace.py     # optional trace/differential diagnostics

THIRD_PARTY_NOTICES.md
```

Host combat orchestration belongs later in `sim` rather than in the pairwise resolver:

```text
src/planets_lab/sim/combat.py
```

That later layer will decide which entities fight, ordering and sides; it must not be smuggled into the resolver migration.

## Migration sequence

### Phase C1 — pure Classic resolver

1. Re-check current `planets-intel/feature/operational-ui` HEAD.
2. Port current `vcr_replay.py` with minimal semantic edits.
3. Add BSD 3-Clause third-party notice.
4. Port exact unit tests that do not require dashboard DB/models.
5. Require green `pytest` in `planets-lab`.

### Phase C2 — Nu adapter + factual corpus parity

1. Adapt Nu payload/static specs to `planets-lab.data`.
2. Port factual VCR corpus diagnostic without dashboard ORM dependencies.
3. Run against the accessible historical corpus.
4. Compare supported/unsupported set and terminal outputs against the current dashboard implementation.
5. Investigate every mismatch; do not weaken assertions to obtain parity.

### Phase C3 — explicit ship battle sequences

1. Extract pure carry-over from `battle_simulator.py`.
2. Port consecutive-survivor chain regression.
3. Preserve Federation/Lizard evidence tags and optional/unsupported boundaries.
4. Require parity with the dashboard implementation for shared supported cases.

### Phase C4 — planet/starbase carry-over

1. Port `battle_simulator_planet.py` mechanics after C3 is stable.
2. Port planet-chain regression/evidence.
3. Preserve fail-closed damaged-starbase ambiguity.

### Phase C5 — make `planets-intel` a consumer

Only after the `planets-lab` implementation has parity:

1. expose a stable pure Python/API boundary as appropriate;
2. replace duplicated dashboard mechanics with an adapter to the canonical implementation;
3. verify Battle Planner behavior did not regress.

### Phase C6 — full Host combat phase

This is new reconstruction work, not part of the migration.

Required topics include:

- engagement eligibility;
- Primary Enemy / Kill mission interaction;
- Friendly Codes;
- diplomacy / Safe Passage / alliances / teams;
- multi-player same-location battle ordering;
- left/right assignment;
- planet/starbase participation and attack eligibility;
- cloak/decloak interaction;
- special combat advantages;
- ordering relative to other Host phases.

## Acceptance criteria for the migration

The migration is complete only when all applicable conditions hold:

1. `planets-lab` owns a pure deterministic Classic resolver with no dashboard/SQLAlchemy dependency.
2. Required c2ng BSD attribution exists in `planets-lab`.
3. Ported deterministic unit tests are green.
4. Fresh factual VCR corpus parity is measured and recorded.
5. Fresh consecutive-battle chain parity is measured and recorded.
6. Planet/starbase support retains existing fail-closed boundaries.
7. Unsupported combat modes remain explicit rather than silently approximated.
8. Federation/Lizard/right-balance rules carry evidence status individually.
9. No Host engagement-order claims are inferred merely from pairwise VCR replay.
10. Only after parity is established may the dashboard implementation be deduplicated.

## Immediate next branch after this inventory

Create a fresh implementation branch from the then-current GitHub `main`, for example:

```text
agent/combat-classic-core
```

Initial scope must be only **C1: pure Classic resolver + license notice + unit-test parity**.

Do not include battle ordering, database adapters, UI changes, planet-chain expansion, or new combat mechanics in that first implementation branch.
