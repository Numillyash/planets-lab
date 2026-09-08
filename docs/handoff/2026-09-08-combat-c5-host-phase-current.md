# C5 Host combat phase — current handoff — 2026-09-08

GitHub is the only source of truth. Always inspect actual `main` and `agent/combat-c5-host-phase` HEADs before continuing.

Current durable evidence is split between this high-level handoff and:

- `docs/handoff/2026-09-08-combat-c5-signed-fc-runtime.md`

## Objective

Reconstruct the NuHost combat phase that generates VCR engagements, order and sides. Keep factual VCRs, inferred semantics and simulator rules separate. Unknown branches fail closed. Game `591478` remains a separate special/campaign/Horwasp bucket.

## Completed C5 evidence

### Factual queue shape

12 archives / 22,256 raw VCR observations / 6,469 unique VCRs / 0 payload conflicts.

Ordinary:

```text
combat sites: 3132
multi-VCR sites: 639
ship-vs-ship VCRs: 1988
ship-vs-planet VCRs: 2406
phase-order violations: 0
repeated ship-pair sites: 2
pair >2 fights: 0
```

Evidence: `CORPUS_OBSERVED`. Ship combat precedes planet combat in all ordinary factual queues; ordinary same-pair population respects the documented maximum two fights.

### Pre-combat orders state

Use owner-visible archive snapshot `T-1` for VCR battle turn `T`.

Ordinary factual ship sides: 6382.

```text
T-1 present: 6370/6382
T-1 owner+hull match: 6347/6370
mission / mission1target / friendlycode present: 6370/6370

T present: 5612/6382
T owner+hull match: 3655/5612
```

Do not use T-1 position as an alignment gate; T-1 precedes Move while VCR positions are post-Move.

### Raw order fields

Owner-visible ship records: 256,780.

Structurally stable fields:

```text
mission
enemy
mission1target
mission2target
friendlycode
```

No explicit mission-name catalog was found in raw RST.

### Kill! / Primary Enemy

Ordinary ship-vs-planet causal evidence establishes:

```text
mission 3 = Kill!
enemy     = Primary Enemy
```

Evidence:
- `mission 3 = Kill!`: documented causal rule + `CORPUS_OBSERVED` numeric mapping;
- `enemy = Primary Enemy`: `CORPUS_OBSERVED`.

### Standard isolated ship side/order

Conservative ordinary single-VCR ship-only subset, excluding normal Priority Intercept, matching FC and broken T-1 identity:

```text
comparable: 420
baseline standard key:
  right higher priority: 417
  left higher priority:    3
```

Exact-three-character signed numeric FC hypothesis `[+/-][0-9][0-9]` was independently tested:

```text
right higher priority: 419
left higher priority:    1
```

The two residuals with right-side FCs `-54` and `-52` disappeared exactly, with no new ordinary residuals.

Evidence:

```text
exact-three-character signed numeric FC parsing:
CORPUS_OBSERVED + DIFF_VERIFIED
NOT DOCUMENTED
```

Do not generalize to arbitrary signed-string lengths.

## Remaining isolated residual

```text
game 621253
battle turn 10
VCR 8

left:
  ship 50 / hull 37 / owner 4
  mission=0 / enemy=3 / FC=wxd
  standard priority=[3,50,0]

right:
  ship 57 / hull 29 / owner 3
  mission=20 / enemy=4 / FC=osq
  standard priority=[3,57,0]
```

Gorbie forced-left was tested and rejected.

### Diplomacy hypothesis rejected

Raw pre-combat turn-9 relation records:

```text
4->3: relationto=1 relationfrom=0 conflictlevel=0
3->4: relationto=1 relationfrom=1 conflictlevel=0
```

The pair has no Safe Passage-or-higher relation. Therefore diplomacy does not explain the residual.

Do not yet canonicalize the detailed `relationto/relationfrom` perspective semantics; the two raw rows are not simple mirrors.

## Current gate: numeric mission 20

The remaining right-side ship is a Bird Dark Wing on rare `mission=20`.

Official Planets.nu documentation says Bird `Cloak and Intercept` can fight the intercept target before regular combat when Primary Enemy matches the target faction. This is a strong hypothesis for the residual, but numeric `20 = Cloak and Intercept` is NOT established yet.

Current files:

```text
tools/diagnostics/combat_host_mission20_cloak_intercept_audit.py
tests/test_combat_host_mission20_cloak_intercept_audit.py
```

The tool inventories every owner-visible mission-20 record across all 12 archives and reports ordinary vs game591478 separately:

- owner race/hull;
- mission1target presence;
- target owner resolution;
- same-owner vs other-owner target;
- enemy vs target-owner relation;
- iscloaked when present.

It separately highlights:

```text
game 621253 / archive turn 9 / ship 57
```

and tests whether `mission1target == 50`.

Do not promote the mapping unless the ordinary population exhibits the documented C&I signature. If evidence is mixed, keep mission 20 numeric and retain the residual as unresolved.

Targeted runtime command:

```bash
cd ~/projects/planets-lab
set -euo pipefail

git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

docker compose run --rm -T lab \
  pytest -q tests/test_combat_host_mission20_cloak_intercept_audit.py

mkdir -p logs

docker compose run --rm -T lab \
  python -u tools/diagnostics/combat_host_mission20_cloak_intercept_audit.py \
    --output logs/combat-host-mission20-cloak-intercept.json \
  | tee logs/combat-host-mission20-cloak-intercept.log
```

## After mission 20

If the signature closes the residual:

1. incorporate accepted signed-FC semantics and C&I pre-standard phase into a canonical C5 battle-order model with provenance;
2. verify ordinary isolated standard side assignment becomes 420/420 once pre-standard C&I is excluded/modeled;
3. reconstruct normal Priority Intercept (`mission=7`) qualification and reverse-Ship-ID ordering;
4. handle exact matching-FC exceptions;
5. build dynamic multi-ship opponent selection;
6. handle capture/reinsertion and ownership changes;
7. integrate the repair boundary and ship-vs-planet phase;
8. keep special game 591478 separate.

PR #28 remains draft until ordering/eligibility semantics are sufficiently understood.