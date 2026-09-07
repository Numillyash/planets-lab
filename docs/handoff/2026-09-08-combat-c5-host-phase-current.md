# C5 Host combat phase — current handoff — 2026-09-08

GitHub is the only source of truth. Always inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing.

At creation time:

```text
main: 89eb91e5f2c50d2d4ae452b743c97cee5c6db54a
agent/combat-c5-host-phase: 0a292a257cb28ebf2c612c7f16a32e3f73efe177
PR: #28 (draft)
```

The C5 branch has already been merge-synchronized with `main` through `89eb91e5...`. The latest main-only change at that point is `docs/handoff/2026-09-08-intel-fuel-chat-handoff.md`; there is no C5 combat overlap.

## C5 objective

Reconstruct NuHost combat engagement generation and order, not merely replay already-existing VCR payloads. Keep facts, inferred semantics, rules, and simulation state separate. Unknown branches fail closed. Game `591478` remains a separate special/campaign/Horwasp bucket and must not be used to tune ordinary rules.

## 1. Factual combat queue shape

Tool:

```text
tools/diagnostics/combat_host_queue_shape_audit.py
```

12-game runtime:

```text
archives: 12
raw_vcr_observations: 22256
unique_vcrs: 6469
payload_conflicts: 0
combat_sites: 4872
```

Ordinary corpus:

```text
sites: 3132
multi_vcr_sites: 639
ship_only_sites: 829
planet_phase_sites: 2303
ship_vs_ship: 1988
ship_vs_planet: 2406
phase_order_violations: 0
sites_with_repeated_ship_pair: 2
sites_with_pair_over_two_fights: 0
```

Special game `591478` has four sites with one pair fighting more than twice. Ordinary corpus has none.

Evidence: factual `CORPUS_OBSERVED`. Ordinary VCR queues contain no ship-vs-ship battle after planet phase starts, and the ordinary same-pair population respects the documented two-fight maximum.

## 2. Pre-combat orders snapshot alignment

Tool:

```text
tools/diagnostics/combat_host_snapshot_alignment_audit.py
```

Ordinary factual ship sides: `6382`.

`T-1` owner-visible state:

```text
present: 6370 / 6382
owner+hull identity match: 6347 / 6370
hull match: 6370 / 6370
mission present: 6370 / 6370
mission1target present: 6370 / 6370
friendlycode present: 6370 / 6370
```

`T` state is clearly post-Host and much worse:

```text
present: 5612 / 6382
owner+hull identity match: 3655 / 5612
```

Use `T-1` as canonical pre-combat orders source. Do NOT use position as the alignment gate: `T-1` precedes Move whereas VCR coordinates are post-Move.

The 23 ordinary `T-1` owner mismatches with hull identity preserved may include within-queue capture ownership changes and must be handled dynamically later.

## 3. Raw order fields

Tool:

```text
tools/diagnostics/combat_host_order_field_inventory.py
```

Owner-visible ship records: `256780`.

Observed fields:

```text
enemy:          present 256780, always int
mission:        present 256780, always int
mission1target: present 256780, always int
mission2target: present 256780, always int, observed zero
friendlycode:   present 256780, always str
```

Strict three-digit FC `001..999`: `17405` records.

No explicit mission-name catalog was found in raw RST.

## 4. Kill! and Primary Enemy mapping

Tool:

```text
tools/diagnostics/combat_host_kill_pe_evidence_audit.py
```

Ordinary ship-vs-planet VCRs: `2406`.

Clean non-`ATT`/`NUK` causal slices:

```text
enemy == planet owner: 1619
zero enemy:              247
enemy names other owner:  50
```

Mission IDs:

```text
zero enemy:             mission 3 = 247 / 247
enemy names other owner: mission 3 = 50 / 50
```

Therefore ordinary NuHost supports:

```text
mission 3 = Kill!
enemy     = Primary Enemy
```

`mission 3 = Kill!`: documented causal rule + `CORPUS_OBSERVED` numeric mapping.

`enemy = Primary Enemy`: `CORPUS_OBSERVED`, strongly supported by the same causal boundary.

Special game `591478` does not follow this clean mapping and remains separate.

## 5. Isolated single-battle side / standard priority differential

Tool:

```text
tools/diagnostics/combat_host_single_battle_side_order_audit.py
```

Conservative ordinary population:
- single-VCR ship-only sites only;
- clean `T-1` owner+hull identity;
- different owners;
- no mission `7` Priority Intercept;
- baseline excludes `000`, 1-digit and 2-digit numeric FCs;
- exact matching FC excluded.

Runtime:

```text
candidate_single_ship_battles: 631
excluded Priority Intercept:    196
excluded matching FC:            13
excluded T-1 identity mismatch:   1
excluded T-1 missing:             1
comparable:                      420

right_higher_priority: 417
left_higher_priority:    3
```

Initial documented standard-priority model therefore predicts factual right side on `417/420 = 99.29%` of this conservative ordinary subset.

Slices:

```text
numeric_vs_numeric:         right 4
numeric_vs_standard:        right 90, left 1
standard_different_groups:  right 259
standard_same_group:        right 64, left 2
```

Do not equate right side with the simple Kill/PE aggressor. The current simplified `_can_initiate()` found:

```text
right_only: 279
both:       116
left_only:   25
```

This is consistent with Battle Order iteration/initiator being distinct from the side whose Kill/PE creates hostility, and the simplified initiation check also does not yet include diplomacy.

## 6. Three ordinary side residuals

Enrichment tool:

```text
tools/diagnostics/combat_host_single_battle_side_residual_audit.py
```

Gorbie forced-left hypothesis was tested and rejected: all three residuals are `no_gorbie`.

Residuals:

### Case 1

```text
game=620694 turn=89 vcr=592
slice=numeric_vs_standard
initiative=right_only

left:  ship=105 hull=94 owner=10 mission=8 enemy=0 fc='125'
       baseline priority=[0,125,105]
right: ship=108 hull=50 owner=5 mission=3 enemy=0 fc='-54'
       baseline priority=[2,108,0]
```

### Case 2

```text
game=620694 turn=53 vcr=254
slice=standard_same_group
initiative=both

left:  ship=262 hull=29 owner=3 mission=9 enemy=5 fc='mkt'
       baseline priority=[3,262,0]
right: ship=448 hull=50 owner=5 mission=1 enemy=3 fc='-52'
       baseline priority=[3,448,0]
```

### Case 3

```text
game=621253 turn=10 vcr=8
slice=standard_same_group
initiative=both

left:  ship=50 hull=37 owner=4 mission=0 enemy=3 fc='wxd'
       baseline priority=[3,50,0]
right: ship=57 hull=29 owner=3 mission=20 enemy=4 fc='osq'
       baseline priority=[3,57,0]
```

Known hull identities from current Race Sheet:
- hull 94: Rush Class Heavy Carrier;
- hull 50: Bloodfang Class Carrier;
- hull 29: Dark Wing Class Battleship;
- hull 37: Ill Wind Class Battlecruiser.

No documented forced-side ability was identified for these hulls. Gorbie hull 70 / Galactic Power is not present in these residuals.

## 7. Current hypothesis gate: signed three-character numeric Friendly Codes

Cases 1 and 2 both contain right-side FCs `'-54'` / `'-52'`.

Baseline parser treats them as symbolic because `str.isdigit()` is false. New read-only hypothesis diagnostic:

```text
tools/diagnostics/combat_host_signed_numeric_fc_hypothesis_audit.py
tests/test_combat_host_signed_numeric_fc_hypothesis_audit.py
```

Current branch HEAD containing this diagnostic:

```text
0a292a257cb28ebf2c612c7f16a32e3f73efe177
```

GitHub CI on this HEAD is green.

Hypothesis only:

```text
exactly three chars matching [+/-][0-9][0-9]
=> parse as signed integer combat priority value
```

If true:

```text
-54 < 125       => Case 1 becomes right-higher priority
-52 < standard  => Case 2 becomes right-higher priority
```

Acceptance criterion is strict: existing ordinary residuals must disappear without creating new ordinary residuals. Do NOT modify the baseline/production parser before this runtime result.

Official current Planets.nu documentation describes numeric combat FCs as `001..999`; therefore signed parsing, if corpus-supported, is an undocumented NuHost behavior and must not be labeled DOCUMENTED.

### Runtime command

```bash
cd ~/projects/planets-lab
set -euo pipefail

git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

echo
echo "===== HEAD ====="
git rev-parse --short HEAD

echo
echo "===== STATUS BEFORE ====="
git status --short

echo
echo "===== SIGNED FC HYPOTHESIS TESTS ====="
docker compose run --rm -T lab \
  pytest -q \
  tests/test_combat_host_signed_numeric_fc_hypothesis_audit.py \
  tests/test_combat_host_single_battle_side_order_audit.py

mkdir -p logs

echo
echo "===== C5 SIGNED NUMERIC FC HYPOTHESIS ====="
docker compose run --rm -T lab \
  python -u tools/diagnostics/combat_host_signed_numeric_fc_hypothesis_audit.py \
    --baseline logs/combat-host-single-battle-side-order.json \
    --example-limit 60 \
    --output logs/combat-host-signed-numeric-fc-hypothesis.json \
  | tee logs/combat-host-signed-numeric-fc-hypothesis.log

echo
echo "===== STATUS AFTER ====="
git status --short
```

Expected HEAD at handoff creation: `0a292a2` or later if only handoff/docs commits were added.

## 8. Likely next residual: diplomacy

If signed-FC parsing cleanly removes Cases 1 and 2 and leaves only Case 3, inspect pre-combat diplomacy for game `621253`, VCR turn `10`, therefore pre-combat orders snapshot turn `9`, owners `4 <-> 3`.

Current simplified `_can_initiate()` ignores diplomacy. Official Order Of Battle says an attacker does not fight a player to whom the attacker grants Safe Passage or higher; asymmetric diplomacy can therefore permit only the opposite side to attack.

Do not guess numeric diplomacy relation values. The API Relations Object includes fields such as:

```text
playerid
playertoid
relationto
relationfrom
conflictlevel
```

First build/read a narrow schema/evidence diagnostic and print raw owner-3/owner-4 relation records for game `621253`, turn `9`; establish numeric relation semantics separately before labeling any relation as Safe Passage.

## 9. Still open in C5

- signed numeric FC hypothesis runtime;
- remaining side residual classification;
- diplomacy / Safe Passage eligibility;
- Priority Intercept qualification and reverse-ID ordering differential;
- exact matching-FC opponent exception handling;
- full multi-ship opponent selection;
- dynamic capture reinsertion / ownership changes;
- ship-to-planet phase transition and between-phase repair integration;
- special game `591478` sequence semantics.

PR #28 must remain draft until standard side/order and subsequent multi-ship ordering evidence are understood.
