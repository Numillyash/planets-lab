# Combat mass D19c static catalog and Rush owner provenance V1

Date: 2026-10-09.

## Verified input

Rulebook reconciliation V2 was published cleanly, exit_code=0:

    runtime-logs/combat-mass-rulebook-reconciliation-v2/
      20261009T171414Z_762a1f1726aa

Exactly 67 source VCR-side observations, only 40 unique
game/turn/ship groups; 49 match official Shield Generator engine
bonus arithmetic, 15 are Horwasp mass inversions, two D19c
hull-catalog conflicts and one Rush with no owner T-1 ship.

D19c official campaign hull sheet:
https://help.planets.nu/RaceSheetPlus
reports id1039 and 46KT. Original typed per-game static
catalog read from first source member produced mass96KT
in game217591 and game325434. Numeric alternative 46+2*150
matches 346 in G217591 T75 V756 and 46+2*1 matches 48
in G325434 T149 V1075. Neither numerical match proves
which original hull collection applied to combat phase.

Rush hull94 ship27 G617883 T201 V1017:
factual mass795 vs catalog645; +150 is compatible with
one Transwarp SG but T-1 owner ship is absent. Do not
assume the missing engine is Transwarp or a generator
was present.

## New research gate

Files:

    tools/diagnostics/combat_mass_catalog_owner_provenance_v1.py
    tools/run-combat-mass-catalog-owner-provenance-v1.sh
    tools/run-combat-mass-catalog-owner-provenance-v1-with-evidence.sh
    tests/test_combat_mass_catalog_owner_provenance_v1.py

On the SHA-verified **immutable** public100:
- verify all three factual VCR mass/hull/owner/side identities;
- compare per-game typed first-member hull catalog against raw
  `hulls` and `hullsall` collections in the first and last source
  members, retaining exact member provenance and source hashes;
- separately inspect archived owner-perspective static `hulls`
  and `hullsall` on T-1 and T, if present;
- retain relevant raw hull fields for IDs 39 (D19b), 1039
  (D19c), 94 (Rush), 1041 (Saber Shield Generator);
- examine up to three owner source members per archived
  turn T−3 through T+1, plus up to three foreign perspectives
  at T-1 and T for the target ship; record if the owner
  source itself was missing, or if the ship was not visible
  in an available owner source;
- recover raw ship engine ID/cost, waypoint, mass/clans,
  and co-located same-owner generators WHERE an archival
  snapshot actually contains the target;
- no extrapolation of the Rush engine or phase-accurate
  generator positions from an absence of a source member.

Critical evidence limits:

A source `hulls` vs `hullsall` difference can indicate
catalog presentation, stale historical static data or a
different game ruleset; it does not yet prove which
collection NuHost used during the actual combat.
Historical T/T+1 snapshots may reflect postcombat state,
so they cannot automatically recover precombat equipment
or activation. Bounded foreign perspectives are
non-exhaustive and might contain stale intel.

No changes to probabilistic.py, Host rules or production
client. Full source-member names and hashes retained
only as provenance keys.

## Run

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-combat-mass-catalog-owner-provenance-v1-with-evidence.sh

Output:

    artifacts/combat/mass-catalog-owner-provenance-v1/published/report.json

Evidence:

    runtime-logs/combat-mass-catalog-owner-provenance-v1/

Next: if the source catalog conflict is confirmed, trace the
actual effective mass projection path with independent
controls (do NOT globally swap 1039 to 46); if Rush
owner snapshots remain unknown, find other source
perspectives or mark the case unresolved. Phase-aware
SG movement and Horwasp attrition are separate gates.
