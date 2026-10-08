# Site combat payload provenance v1 — research handoff

Date: 2026-10-08

## Basis: closed terminal replay

    source main 421360cf07b76a794c85300983af7fcae26a5a93
    runtime-logs/site-combat-terminal-replay-v1/
      20261008T024042Z_421360cf07b7

    SITE_STATE_EXACT 3/3
    SITE_TERMINAL_REPLAY_EXACT
    current and next VCR starts 3/3 each

Checkpoint is documented separately in:

    docs/handoff/2026-10-07-site-combat-terminal-replay-v1.md

## Why this probe

The target-window terminal outcome is now produced by deterministic Classic
replay from carried mutable state. Remaining dependencies include current VCR
N's seed, static/effective combat fields, combat rates, weapon catalogs and
RNG mode. Current VCR N still identifies the encounter already elapsed.

We must not call the executor generative while it relies on these facts.

## Read-only observational audit

    tools/diagnostics/combat_site_payload_provenance_v1.py
    tools/run-site-combat-payload-provenance-v1.sh
    tools/run-site-combat-payload-provenance-v1-with-evidence.sh

The probe compares actual current-VCR 592..595 sides with each ship's
T-1 Nu raw state (only candidate source; not the carried mutable state).

Direct candidate mapping:

    VCR hullid          ← raw hullid
    VCR beamid          ← raw beamid
    VCR torpedoid       ← raw torpedoid
    VCR beamcount       ← raw beams
    VCR launchercount   ← raw torps
    VCR baycount        ← raw bays
    VCR mass            ← raw mass  (candidate only)
    VCR torpedos        ← raw ammo decoded by fitted torps/bays
    VCR fighters        ← raw ammo decoded by fitted torps/bays

Each value reports observed_equal, observed_different, unresolved_prior, or
unresolved_vcr. Ambiguous hybrid ammo is NOT zeroed or guessed.

Fields presently requiring independent reconstruction, without a projected
candidate rule:

    beamkillbonus
    beamchargerate
    torpchargerate
    torpmisspercent
    crewdefensepercent

Seed, battle type and combatrng are reported strictly as factual observations.
No seed-progression formula is inferred or promoted.

All VCR cases must match the factual site queue pair. The probe does not use
post-combat terminal state and does not run the executor. Its outputs must never
be wired into a prediction path.

## Interpretation boundary

Observed equality on one historical site does NOT promote a canonical rule.
Observed differences may arise from current-turn host phases, combat
damage/effective weapon counts, capture transfer, or raw-vs-VCR semantics.
Prior T-1 dynamic ammo may naturally differ later in the VCR chain.

The next task, after collecting evidence, is to split immutable ship/catalog
projection, mutable carried state, host-derived modifiers, and RNG progression
into separate independently validated modules. O stays fail-closed and the
immediate-C LEFT/RIGHT research candidate remains unpromoted.

## Server execution

    cd ~/projects/planets-lab
    git fetch origin && git switch main && git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-site-combat-payload-provenance-v1-with-evidence.sh

Evidence target:

    runtime-logs/site-combat-payload-provenance-v1/

Expected marker:

    OBSERVATIONAL_NOT_PROMOTED

This marker means the audit completed, not that payload construction is exact.
