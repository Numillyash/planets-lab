# Mine/web movement residual — damage rounding follow-up

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **mine/web movement interruption is strongly corpus-observed; Host-order differential runtime-complete; NuHost damage-rounding differential implemented and pending runtime**.

This handoff supersedes `2026-08-24-mine-hit-hostorder-differential-pending.md` for the active movement investigation. No production mine/web label has been added yet.

## Runtime baseline

Current verified L2 accounting remains unchanged:

```text
move_most_candidates              227468
post_external_residual              3938
chunnel_explained                   1421
post_chunnel_residual               2517
horwasp_strong_explained             240
post_horwasp_strong_residual        2277
```

## Host-order differential — runtime result

The second-pass diagnostic was run at clean HEAD `66dcd3f`:

```text
tools/diagnostics/mine_hit_hostorder_differential_audit.py
```

Population consistency:

```text
generic_non_horwasp_warp1_9_rows  718
raw_short_same_line                235
raw_short_non_gravitonic           216
raw_short_gravitonic                19
effective_short_same_line          238
effective_short_non_gravitonic     216
effective_short_gravitonic          22
after_identity_break                 0
same_identity_after                238
```

The earlier 216-vs-235 discrepancy is therefore fully explained by Gravitonic scope. Effective Gravitonic nominal movement adds three more short-forward candidates.

## Web evidence after Host-order guards

```text
web_state_signature                       19
web_after_field_strong                    18
owner_after_visible_web_at_observed      140
persistent_web_at_observed                94
```

The 18 field-backed web-state rows span the three corpus games that contain observed web minefields. Same-identity continuity has zero breaks in the focused population.

The initial literal documentation-rounding check only matched three rows:

```text
web_exact_damage_after_field              3
web_exact_damage_persistent_field         2
web_exact_games            [360690,511506,620694]
web_exact_hulls            {69:1,46:1,5:1}
```

However the non-matching rows show systematic integer values inconsistent with the diagnostic's `ceil(1000/(mass+1))` assumption. Examples:

```text
mass 120: 1000/121 = 8.264... ; observed web damage 8
mass  30: 1000/31  = 32.258...; observed web damage 32
mass 860: 1000/861 = 1.161... ; observed web damage 1
mass 250: 1000/251 = 3.984... ; observed web damage 4
```

Those values are consistent with positive nearest-integer rounding, not unconditional ceiling.

## Normal-mine evidence after Host-order guards

```text
normal_mine_10ly_geometry                 54
normal_after_field_strong                 25
normal_exact_distance_damage               7
normal_exact_damage_after_field             7
normal_exact_damage_persistent_field        2
normal_exact_damage_no_after_field          0
normal_exact_games     [360690,511506,591478,620694]
```

Again, the literal-ceiling subset understates the visible pattern. Several field-backed low-tech examples pair ~10/20 ly slowdown with damage values matching nearest-integer `10000/(mass+1)`:

```text
mass 180: 10000/181 = 55.249... -> observed 55
mass 160: 10000/161 = 62.112... -> observed 62 or 124 for two hits
mass 150: 10000/151 = 66.225... -> observed 66
mass 115: 10000/116 = 86.207... -> observed 86
mass 120: 10000/121 = 82.645... -> observed 83
```

This is a cross-hull pattern rather than one special hull.

## Documentation vs corpus compatibility finding

Primary Planets.nu minefield documentation states both:

```text
Damage % = 10000 / (Hull Mass + 1)
Damage % =  1000 / (Hull Mass + 1)
```

and says that mine-impact damage is always rounded up.

The current historical NuHost corpus appears to disagree with the rounding sentence. Do not change simulator/rules from documentation to nearest-integer yet; first measure `ceil`, `floor` and positive round-half-up directly across field-backed rows.

Evidence status at this point:

- mine/web movement interruption: **DOCUMENTED + CORPUS_OBSERVED**;
- exact Host-order after-field/identity signatures: **CORPUS_OBSERVED**;
- nearest-integer damage rounding: **INFERRED**, pending dedicated differential;
- production classifier: not yet promoted.

## Repair contamination is expected

Planets.nu documentation states that five supplies repair one percentage point of damage. Host Order contains a `Mass check, repair & MKT` after Most Ships Move and before later combat.

Therefore exact post-turn damage is strongest on rows that:

- started undamaged; and
- had fewer than five supplies available for automatic repair.

Rows such as a one-point or several-point deficit from the raw mine quantum may still be compatible with a mine hit followed by repair. Repair-bracket evidence is supportive but not equivalent to exact damage proof.

## New focused diagnostic

```text
tools/diagnostics/mine_hit_damage_rounding_audit.py
```

It compares three candidate integer rules without changing production semantics:

```text
ceil     = ceil(numerator / (mass + 1))
floor    = floor(numerator / (mass + 1))
nearest  = positive round-half-up(numerator / (mass + 1))
```

for both normal mines (`numerator=10000`) and webs (`numerator=1000`).

It reports:

- field-backed exact damage-delta matches by rounding mode;
- undamaged-start exact matches;
- no-repair-supply exact subset;
- hull/game coverage by mode;
- `nearest but not ceil` rows;
- no-after-field negative controls;
- a coarse repair-consistency bracket for normal mine rows.

## Immediate next step

Run only the rounding diagnostic; no corpus rebuild is needed:

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
  tools/diagnostics/mine_hit_damage_rounding_audit.py

echo
echo "===== MINE DAMAGE ROUNDING DIFFERENTIAL ====="
docker compose run --rm -T lab \
  python -u tools/diagnostics/mine_hit_damage_rounding_audit.py \
  | tee /tmp/mine_hit_damage_rounding_audit.log

echo
echo "===== STATUS AFTER ====="
git status --short
```

Priority outputs:

```text
web_ceil_delta_match_after_field
web_floor_delta_match_after_field
web_nearest_delta_match_after_field
web_nearest_not_ceil_delta
web_nearest_control_no_after_field

normal_ceil_from_zero_exact_after_field
normal_floor_from_zero_exact_after_field
normal_nearest_from_zero_exact_after_field
normal_nearest_repair_bracket_from_zero
normal_nearest_not_ceil_from_zero
normal_nearest_control_no_after_field
```

If nearest-integer decisively wins across multiple hulls/games while no-field controls remain sparse, record a NuHost/documentation compatibility discrepancy and then implement a narrow regression-backed mine/web context classifier. If the modes do not separate cleanly, keep mine hits as diagnostic evidence and investigate repair/impact-order details before promotion.
