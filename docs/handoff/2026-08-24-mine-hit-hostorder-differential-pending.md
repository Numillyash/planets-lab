# Mine/web-hit movement residual — Host-order differential pending

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **first mine/web residual audit runtime-complete; exact Host-order/damage differential implemented; second-pass runtime pending**.

This handoff supersedes `2026-08-24-mine-hit-residual-followup.md` for the active movement investigation. Chunnel v4, classic ion storms, scoped sphere topology and Red Mite closure remain unchanged.

## Runtime baseline

Current L2 accounting remains:

```text
move_most_candidates              227468
post_external_residual              3938
chunnel_explained                   1421
post_chunnel_residual               2517
horwasp_strong_explained             240
post_horwasp_strong_residual        2277
```

No production labels were changed by the mine diagnostics.

## First mine/web audit — runtime result

Diagnostic:

```text
tools/diagnostics/mine_hit_residual_audit.py
```

The user ran it at clean `main` HEAD `23ed93d`; syntax check passed and all prepared caches were hits.

Population:

```text
generic_non_horwasp_warp1_9_rows    718
short_same_line_forward               235
damage_increase                       174
post_warp0_waypoint_reset              26
web_state_signature                    19
web_strong                             18
normal_mine_10ly_geometry              55
any_visible_normal_field_crossing      67
normal_mine_strong                     25
```

Minefield schema coverage was unusually clean:

```text
minefield records with explicit radius: 429532 / 429532
parseable records:                    429532 / 429532
```

Observed raw keysets were only:

```text
['friendlycode','id','infoturn','ishidden','isweb','ownerid','radius','units','x','y']
['friendlycode','id','infoturn','isweb','ownerid','radius','units','x','y']
```

Thus radius inference is not needed for this corpus pass.

## Web evidence

`web_state_signature` occurred on 19 rows across 9 hulls and 3 games. Eighteen of those 19 also had a visible enemy web field containing the observed stop point:

```text
web_state_signature  19
web_strong           18
web_strong_games     [360690, 511506, 620694]
```

The repeated hull patterns are already mechanically suggestive. Examples include recurring hull-56 damage changes in 8-point increments, hull-52 one-point damage, hull-51 32 damage, hull-55 11 damage and hull-46 11 damage, all together with Warp-0/waypoint reset and an observed web field.

Primary documentation states:

```text
web damage % = ceil(1000 / (Hull Mass + 1))
```

and that a web hit immediately stops movement and sets speed to Warp 0. The out-of-fuel documentation additionally states that when fuel is exhausted by the web hit the waypoint is set to the current location.

## Normal-mine evidence

The first pass found 25 strong normal-mine candidates across 11 hulls and 7 games:

```text
normal_mine_strong_games =
[360690, 511506, 591478, 620694, 620917, 622476, 680435]
```

The large damage values are not automatically combat contamination. Official mine documentation gives:

```text
normal mine damage % = ceil(10000 / (Hull Mass + 1))
```

and states that hulls below tech 7 lose 10 ly of travel for each mine hit when more than 10 ly remain. The corpus examples show repeated hull-specific damage values together with roughly 10/20 ly loss, which motivates an exact damage-quantum differential rather than treating all damage increase as equivalent.

## Population reconciliation

The earlier fuel audit reported 216 short same-line candidates because it explicitly excluded Gravitonic hulls. The first mine audit included them. Its short-movement hull list contains exactly 19 Gravitonic candidates:

```text
hull 46: 16
hull 45:  3
```

so:

```text
235 total - 19 Gravitonic = 216 non-Gravitonic
```

The apparent 216/235 discrepancy is therefore population scope, not a corpus regression. The second-pass diagnostic reports raw/effective and Gravitonic/non-Gravitonic counts separately.

## Why after-turn minefield state is the stronger proxy

Documented Host Order places these before ordinary movement:

1. lay mines / lay web mines;
2. ion-storm minefield effects;
3. mine sweep/scoop;
4. mine decay;
5. minefield-vs-minefield destruction;
6. web drain;
7. ordinary movement with mine impacts.

The first diagnostic used a union of before-turn and after-turn minefield observations. The second pass instead treats the after-turn field as the stronger Host-order proxy, because the documented field-size-changing phases occur before movement. It also reports same-field before+after persistence separately.

This remains a proxy: mine impacts themselves can remove mine units, hidden/diplomacy/Friendly-Code state is incomplete, and no historical event log is available.

## Same-identity guard

Movement readiness only requires after-turn owner/x/y. A ship slot destroyed and rebuilt during the same Host could in principle contaminate post-state damage/nav checks.

The second pass therefore requires:

- same owner;
- same hull;
- and, when present on both sides, the same raw ship `turn` identity discriminator.

Rows failing continuity are counted and excluded from exact signatures.

## New second-pass diagnostic

```text
tools/diagnostics/mine_hit_hostorder_differential_audit.py
```

It reports:

### Population consistency

- raw short same-line total;
- non-Gravitonic vs Gravitonic split;
- effective-nominal short same-line total;
- same-identity vs identity-break counts.

### Web evidence

- state signature;
- after-turn web field at the stop point;
- owner-perspective after-turn field;
- persistent before+after field identity;
- exact documented web-damage quantum from an undamaged start;
- damage-delta quantum match;
- low-supply exact subset.

### Normal-mine evidence

- low-tech N×10-ly geometry;
- after-turn normal-field corridor crossing;
- persistent field crossing;
- exact `N * ceil(10000/(hull_mass+1))` damage from an undamaged start;
- damage-delta exact match;
- exact-distance/damage rows with no visible after field;
- exact hit-count distribution.

No production mine/web label is added by this commit.

## Immediate next step

Run:

```bash
cd ~/projects/planets-lab
set -o pipefail

git pull --ff-only origin main

echo "===== HEAD ====="
git rev-parse --short HEAD

echo
echo "===== STATUS ====="
git status --short

echo
echo "===== SYNTAX CHECK ====="
docker compose run --rm -T lab \
  python -m py_compile \
  tools/diagnostics/mine_hit_hostorder_differential_audit.py

echo
echo "===== HOST-ORDER MINE DIFFERENTIAL ====="
docker compose run --rm -T lab \
  python -u tools/diagnostics/mine_hit_hostorder_differential_audit.py \
  | tee /tmp/mine_hit_hostorder_differential_audit.log

echo
echo "===== STATUS AFTER ====="
git status --short
```

Priority outputs:

```text
raw_short_non_gravitonic
raw_short_gravitonic
after_identity_break
same_identity_after

web_state_signature
web_after_field_strong
web_exact_damage_after_field
web_exact_damage_persistent_field

normal_mine_10ly_geometry
normal_after_field_strong
normal_exact_distance_damage
normal_exact_damage_after_field
normal_exact_damage_persistent_field
normal_exact_damage_no_after_field
```

If exact web and/or normal-mine signatures remain material across multiple games/hulls after these guards, the next step is a narrow regression-backed context classifier. If exact signatures collapse, mine overlap remains diagnostic context only and generic residual triage resumes.
