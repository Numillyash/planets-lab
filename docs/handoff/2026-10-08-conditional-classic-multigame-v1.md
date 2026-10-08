# Conditional Classic combat ensemble and multigame pilot v1

Date: 2026-10-08.

## Purpose

Move beyond replaying one *known* VCR seed. For a known encounter and
fully supplied **effective precombat side state**, enumerate all
118 conventional Classic VCR start seeds (1..118) and, when eligible,
both anti-carrier mass options (right base or base+360 KT).

The ensemble provides conditional model frequencies for
destroyed/captured/survived, aggregated winner/result signatures, and
expected terminal shields/damage/crew/torpedo ammo/fighter ammo.

This is **not** a recovered NuHost RNG generator or an independent
end-to-end battle simulator. Uniform seed distribution and independence
of the 60% bonus from seed are explicit scenario assumptions.

## Source of truth

- `src/planets_lab/rules/combat/probabilistic.py`: pure evaluator.
- `tools/diagnostics/combat_multigame_conditional_ensemble_v1.py`:
  public100 multigame sampling, oracle-assisted external-field validation.
- `tools/run-multigame-conditional-combat-pilot-v1.sh`: SHA-locked runner.
- `tools/run-multigame-conditional-combat-pilot-v1-with-evidence.sh`:
  evidence publishing.
- Focused tests in `tests/test_combat_probabilistic.py` and
  `tests/test_combat_multigame_conditional_ensemble_v1.py`.

## Critical evidence boundaries

The pure evaluator refuses a `seed` field in input and refuses side
`mass` fields, to prevent accidentally using an observed VCR's seed/mass as
a simulation input. It requires both sides' effective weapons, shielding,
crew, race, ammunition, modifiers and owner identifiers to already be
supplied, plus independent hull catalog masses, a Classic game setting,
and explicit `assumed_no_other_mass_modifiers=True`.

The public100 pilot uses the *current factual VCR* for the other effective
fields. Its source label is:

    ORACLE_ASSISTED_CURRENT_VCR_FIELDS_EXCEPT_SEED_AND_MASS

This is a controlled decomposition test, NOT a fresh reconstruction of
these still-unknown current-VCR fields. The scenario weights are conditional
model assumptions, not calibrated Host probabilities.

The actual seed and mass fields are removed *before* the evaluator is called.
The sampler checks the observed mass against the scenario set *after*
ensemble generation, only as an explicit descriptive coverage metric.
An observed mass outside the modeled candidates remains an out-of-scope
row; it is not dropped or forced to match.

Game `591478` (special/campaign/Horwasp-heavy) is excluded explicitly;
other unusual settings can cause unsupported cases and are reported.
Extended RNG (`combatrng !=0`) and non-ship-vs-ship battles fail closed.
No physical Host state or runtime evidence is mutated and `CURRENT`
is never consulted.

## Expanding the game sample

Instead of working solely with game400330/T141, the pilot automatically
enumerates the compact corpus `vcrs` view and selects up to five *distinct*
games with moderate VCR counts, two eligible ship-vs-ship VCRs per game.
It considers up to 24 games when some are unsupported, reports skipped
cases and game selection provenance, and keeps the previously studied
game400330/T141 as a baseline when available.

Default upper bound: 5 games × 2 VCR × 118 seed × up to 2 masses
= at most 2,360 deterministic Classic replays.

This is a deliberately bounded pilot. Running across the full 100-game
public corpus comes only after runtime demonstrates acceptable performance
and mass/assumption coverage. The observed VCR outcomes are NOT independent
factual terminal-state oracles in this iteration.

## Server command

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-multigame-conditional-combat-pilot-v1-with-evidence.sh

Evidence branch:

    runtime-logs/multigame-conditional-combat-pilot-v1/

Default output artifact:

    artifacts/combat/multigame-conditional-ensemble/public100-pilot-v1.json

Resource tuning after first successful pilot:

    PLANETS_COMBAT_ENSEMBLE_GAMES=5
    PLANETS_COMBAT_ENSEMBLE_CASES_PER_GAME=2
    PLANETS_COMBAT_ENSEMBLE_SCAN_GAMES=24

The wrapper deliberately returns nonzero when fewer than five distinct
supported games can be sampled, while still writing an explanatory JSON and
publishing evidence. No result should be promoted as a global Host rule.
