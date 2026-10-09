# Combat mass: capture phase and time-indexed static controls

Date 2026-10-09.

## Provenance inputs

V2 `runtime-logs/combat-mass-temporal-static-identity-v2/20261009T201443Z_e8ec94542ce9` succeeded (exit0 clean, no skipped evidence); 2 D19c hull-1039 catalog sequences have mass:
- game217591: T0 96, T1..T75 46
- game325434: T0..T32 96, T33..T149 46.

The T−1 owner static 46 is independent evidence in both
combat turns, but does not prove the full Host effective
hull resolver or phase order. The existing research
`_independent_hull_specs` selects the earliest source.

Rush game617883 T201 shipID27 shows two distinct factual VCR starts
at same VCR site [1455,2615]:
- V1016 RIGHT owner5 race5 hull94 Rush mass645, opponent owner4 hull35 ship253.
- V1017 LEFT owner4 race4 hull94 Rush mass795, opponent owner5 hull52 ship167.
So the object ID and hull are stable *between the two VCRs*,
while owner changes 5 → 4 and mass increases +150.

Independent official help:
- https://help.planets.nu/battle-order:
  Captured ships may fight again for their new owner during
  the same Host run, with special queue restrictions.
- https://help.planets.nu/combat-basics:
  ship captures on crew reaching zero and gets 10 prize crew.
- https://help.planets.nu/combat-host:
  postcombat shipbuilding can refill slots freed by battle.
- https://help.planets.nu/abil-shield-generator:
  1 Transwarp Saber may add +150 combat KT if actually active
  and co-located with its own side.

Capture between V1016 and V1017 is the **leading hypothesis**
but is not yet proven from VCR outcome/terminal crew. Historical T201
owner4 snapshot contains ID27 as hull35 Victorious engine9
instead of Rush hull94; do NOT attribute this postcombat
Victorious engine9 to captured Rush or infer a postbattle build
without source evidence.

## Next read-only gate

    tools/diagnostics/combat_mass_capture_phase_controls_v1.py
    tools/run-combat-mass-capture-phase-controls-v1.sh
    tools/run-combat-mass-capture-phase-controls-v1-with-evidence.sh
    tests/test_combat_mass_capture_phase_controls_v1.py

Pin unchanged public100 SHA.
A) Recover full factual VCR *start* participant fields for
V1016/1017, including crew, shields and damage if present;
store only small scalar metadata and field names to identify
available explicit capture/result markers. No terminal VCR
state is fabricated from initial crew.

B) Seek the ORIGINAL owner5 perspective on T200 (missing
from previous owner4-focused audit), including actual engine
ID for Rush27 if archived. Independently enumerate
owner4-owned Saber locations at the VCR site from T200 and
T201, and compare with fixed VCR [1455,2615]. T200
historical site/waypoints are not guaranteed combat-phase
active support. The observed +150 is NOT used to infer
Rush engine or generator count.

C) Scan 12 anomaly-priority game/turn pairs from frozen
80-game digest PLUS the two D19c reference turns. Compare
first-member mass of each hull ID to every available T−1
player-perspective `hulls` catalog. Flag cross-perspective
conflicts and missing sources rather than silently picking
an effective Host ruleset. This is a held-out observational
control, NOT a production-ready resolver.

No changes to production, probabilistic.py or existing
NuHost combat model.

## Server

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-capture-phase-controls-v1-with-evidence.sh

Artifacts:
    artifacts/combat/mass-capture-phase-controls-v1/published/report.json

Evidence:
    runtime-logs/combat-mass-capture-phase-controls-v1/

## Scientific boundary

Captured VCRs may be correlated. A VCR identifier is not
proof of exclusive chronological order. Raw archive fields
may be masked on foreign perspectives. Source static
masses change across turns; do not use VCR mass to select
which static snapshot to trust. Any move toward generative
combat-mass parity needs T−1 external inputs and
held-out combat predictions, not same-case classification.
