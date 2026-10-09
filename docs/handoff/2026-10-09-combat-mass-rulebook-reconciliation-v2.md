# Combat Mass Rulebook Reconciliation V2

Date: 2026-10-09.

## Source checkpoint (verified)

    runtime-logs/combat-mass-complete-residuals-v1/
      20261009T164712Z_614b20e04efe

Clean main source `614b20e04efef428ab88173a3ffb98b19aee44c3`,
metadata exit 0, no missing/skipped evidence artifacts.

The source identifies every one of the 67 residual VCR sides,
40 distinct game/turn/ship groups (27 repeated VCR-side records).
22 selected game-turns in 14 games; 40 original identities
plus 27 reconstructed identities.

## Independent official rulebook evidence

Shield Generator:
https://help.planets.nu/abil-shield-generator

The OFFICIAL table has a +1 KT combat-mass bonus for Stardrive 1,
+13 KT for Nova Drive 5 and +27 KT for HeavyNova Drive 6.
Full table, by engine ID 1..9:

    1, 1, 2, 2, 13, 27, 85, 100, 150 KT

It is NOT floor(engine_cost_MC/2) for odd-cost engines.
With two active generators a Stardrive 1 receives +2 KT.
Generator effects require correct ownership and location in
the Host combat phase; two is the per-turn limit, and a
generator cannot boost itself.

The official table supports the NUMERIC ARITHMETIC behind
49 of the original 52 non-Horwasp residual observations:

    Engine 1: 34 VCR-side records
    Engine 5: 12 VCR-side records
    Engine 6:  3 VCR-side records

These are 49 observations but only 24 distinct game/turn/ship
groups across nine games. The generator count and +360
random branch were selected retrospectively by comparing
factual VCR mass, and are NOT independently predicted.
Previously recorded T-1 geometry: 28 cases have site-support
evidence, 11 co-travel-order support, and 10 have neither
proof; no one may infer those ten Host states from the numbers.

NuHost reference hull catalog:
https://help.planets.nu/RaceSheetPlus

The published D19c Nefarious hull ID 1039 has 46 KT mass,
whereas BOTH inspected game-specific catalogs report 96 KT.

    game 217591 T75 V756: 346 = 46 + 2*150
    game 325434 T149 V1075: 48 = 46 + 2*1

This is an important **catalog provenance discrepancy**,
NOT permission to replace per-game NuStaticSpecs with 46 KT
or assume the two generators were operational at combat.
Investigate why archival static import reports mass96 for ID1039;
the official hull ID39 D19b has 96 KT, but that does not by
itself prove misidentification or a static mapping bug.

The remaining non-Horwasp case:

    game617883 T201 V1017, Rush hull94, ship27:
    catalog645, factual795, difference +150
    no T-1 owner ship, engine unknown

A single Transwarp (engine9) Shield Generator could explain
+150 arithmetically, but no owner/engine evidence establishes
this configuration. Keep OPEN.

## Horwasp residuals stay unproven

15 factual VCR-side cases remain outside original Horwasp
full/partial classes. All have at least one *inverse* clan
interval using the unverified interpolation and, where
eligible, a retrospective +360 carrier branch.

Examples include the game217591 Brood mismatch
(game hull117 mass125, reference145), and ships with
T-1 clans no longer matching those required at a later
combat. The inversion takes factual VCR mass as input,
so these are constraints, NOT autonomous mass predictions
or a validated between-battle clan-loss model.

Official Horwasp reference:
https://help.planets.nu/horwasp-ships

## Reproducible evidence tool

    tools/diagnostics/combat_mass_rulebook_reconciliation_v2.py
    tools/run-combat-mass-rulebook-reconciliation-v2.sh
    tools/run-combat-mass-rulebook-reconciliation-v2-with-evidence.sh
    tests/test_combat_mass_rulebook_reconciliation_v2.py

The tool reads frozen local v1 residual JSON only. It
classifies each source VCR side into exactly one of:
documented SG bonus numeric match, external D19c mass
alternative, Horwasp inverse-only, or unresolved/missing
owner. It independently recomputes engine-rulebook
numerics and verifies that the earlier rounded-half
candidates agree. Source/digest identity and count
invariants are checked; source game catalogs are NOT
changed. All 67 records and deduplicated ship-turn
counts are preserved, with each outcome explicitly
labelled non-predictive.

Run on the corpus server (no database scan needed):

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    bash tools/run-combat-mass-rulebook-reconciliation-v2-with-evidence.sh

Output:

    artifacts/combat/mass-rulebook-reconciliation-v2/published/report.json

Runtime evidence:

    runtime-logs/combat-mass-rulebook-reconciliation-v2/

## Follow-up research

(1) Investigate archival static hull ID 1039 (D19c)
catalog provenance and compare game-specific campaign
hull history vs official 46KT reference; do not replace
source specs without independent evidence.

(2) Reconstruct precombat-phase SG location for
positive AND negative engine1/5/6 cases, including
gravity well offsets, plus the Rush ship27.

(3) Recover Horwasp mutable clans by forward replay
of combat attrition, checking N+1 state without using
the next factual VCR mass as input.

No promotion to production or probabilistic Classic
combat evaluator occurs in this checkpoint.
