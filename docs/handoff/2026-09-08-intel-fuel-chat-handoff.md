# Intel / finite-fuel movement handoff — 2026-09-08

GitHub `main` is the only source of truth for `Numillyash/planets-lab`.

## Current source checkpoint

At handoff creation, GitHub `main` HEAD is expected to be at or after:

```text
adf3704c043ab5137afd10daef25f39b5b032c15
perf: prefilter partial Move Most fuel audit
```

Always inspect actual `main` before work.

## Finite-fuel Intercept evidence

Historical differential over finite-fuel archives found only three strict snapshot-fuel-limited Intercept cases.

### 620636 / T60 / ship44 — strong support

```text
Hull: Gemini Class Transport
Warp: 8
Snapshot fuel: 1 KT
Candidate full cost: 3 KT
Observed endpoint: (1716, 1599)
Geometry-only endpoint: (1705, 1589)
Fuel-proration endpoint: (1716, 1599)
After fuel: 0
```

The phase-fuel scan found that exactly 1 KT reproduces the observed endpoint. Targeted confounder audit found no strict mine, storm, damage-limited-warp, observed Tow-route or Chunnel-target explanation.

Interpretation: strong evidence that finite-fuel Intercept can use proportional fuel-limited movement.

### 360690 / T69 / ship391 — snapshot fuel is not phase fuel

```text
Hull: Biocide Class Carrier
Warp: 9
Snapshot fuel: 64 KT
Candidate full cost: 66 KT
Observed endpoint = geometry endpoint
Snapshot-fuel prorated endpoint differs
Minimum phase fuel compatible with factual endpoint: 66 KT
After fuel: 171 KT
```

No visible incoming transfer/Tow candidate was found in the owner-visible snapshot, but absence is not proof of no hidden/earlier Host mutation.

Interpretation: do not treat pre-Host `loadturn.neutronium` as guaranteed Intercept-phase fuel.

### 620694 / T73 / ship278 — true partial route / cost-basis discriminator

```text
Hull: Nova Class Super-dreadnought
Warp: 9
Origin: (2758, 2098)
Intercept target final observed: (2717, 2026)
Target distance: ~82.855 ly
Nominal max: 81 ly
Observed endpoint: (2742, 2070)
Snapshot fuel: 29 KT
After fuel: 0
```

No known strict mine/storm/damage/Tow/Chunnel explanation was found.

The previous normal planner reports `insufficient_fuel_partial_waypoint`, but a dedicated model comparison showed:

```text
integer projected one-turn distance ~80.623 -> required cost 71
continuous nominal 81-ly leg            -> required cost 72
full target waypoint cost               -> required cost 72

29/71 rasterizes to (2741,2069)  [not factual]
29/72 rasterizes to (2742,2070)  [factual]
```

This is evidence that true partial-route fuel cost may be based on the continuous nominal leg before Host endpoint rasterization. One case is not enough to promote a production rule.

## Diagnostic correction

Do not equate `NormalMovePlan.partial` with `waypoint_distance > effective max distance`.

`partial` can also be true for a geometrically reachable waypoint shortened due to fuel shortage. A true partial route must be classified geometrically from target distance versus effective max movement.

## Population audit

A broad `partial_move_fuel_cost_population_audit.py` was too slow and insufficiently chatty for routine interactive use.

A faster prefiltered diagnostic was added:

```text
tools/diagnostics/partial_move_fuel_cost_move_most_audit.py
```

Relevant commit:

```text
adf3704c043ab5137afd10daef25f39b5b032c15
perf: prefilter partial Move Most fuel audit
```

It should prefilter in DuckDB and emit progress before expensive per-game processing. Use this instead of the old broad audit.

Run:

```bash
cd /opt/planets-lab

git fetch origin
git pull --ff-only origin main

echo "===== HEAD ====="
git rev-parse HEAD
git symbolic-ref --quiet --short HEAD || true

echo
echo "===== FAST PARTIAL MOVE MOST FUEL COST ====="

docker compose run --rm -T lab \
  python -u tools/diagnostics/partial_move_fuel_cost_move_most_audit.py \
  | tee logs/partial-move-fuel-cost-move-most-audit.log

RC=("${PIPESTATUS[@]}")
echo "audit rc=${RC[0]}"
echo "tee rc=${RC[1]}"
```

If it again runs for several minutes without progress, stop it and optimize the diagnostic before asking the user to wait.

## Promotion policy

Do not change production finite-fuel Intercept/Tow law from these three examples alone.

Desired independent evidence:

- multiple true partial Move Most cases where projected-vs-nominal cost differs;
- preferably cases with post-move fuel reset/consumption evidence;
- no already-verified external movement mechanic explaining the same endpoint;
- consistent preference for one cost basis across independent games/hulls.

Keep unsupported phase-fuel state fail-closed in `planets-intel`.

## Cross-repo context

Companion production/client handoff:

```text
Numillyash/planets-intel
docs/handoff/2026-09-08-chat-handoff.md
```

The production client currently has only unlimited-fuel current games, so do not repeatedly request a current finite-fuel runtime sample. Historical archives here are the evidence source.
