# C5 directed clan-drop / precombat ownership gate — pending

Branch: `agent/combat-c5-host-phase`

Game `591478` remains isolated from ordinary promotion.

## Why this gate exists

Mixed ship/planet queue ordering itself is now largely closed in the supported ordinary scope.

The remaining planet-combat targetability gap is earlier in Host:

```text
T-1 planet/ship state
  -> foreign cargo drop / ground combat
  -> precombat planet owner
  -> planet combat targetability
  -> already-verified planet attacker ordering
```

The v6 ownership timeline found:

```text
59 unique precombat owner-change planet-turns overall
42 unique positive-owner reversals handled by the current owner/raw adapter
```

For those 42:

```text
future-defender ship co-located at T-1 = 42/42
future-defender ship with onboard clans>0 = 33/42
onboard clans==0 = 9/42
```

The nine zero-onboard-clan rows are not negative controls. Historical ship objects expose explicit directed orders such as:

```text
transferclans > 0
transfertargettype == 1
transfertargetid == factual planet id
```

including rows where the ordinary `clans` field is already zero.

## Production boundary

New module:

```text
src/planets_lab/rules/combat/planet_ownership.py
```

New bounded primitives:

```python
PlanetClanDropOrder
directed_planet_clan_drop(...)
ordered_planet_clan_drops(...)
```

They do only what is independently represented in the T-1 order data:

1. validate a positive clan transfer targeted at a planet;
2. preserve source ship and owner;
3. compose one planet's transfers in ascending Ship ID order.

They do **not** yet implement:

- ground-combat casualty math;
- racial attack/defense multipliers;
- defense-post modifier;
- Shock Troops / Fortress;
- Imperial Assault;
- Horwasp ground mechanics;
- starbase ownership side effects.

## Corpus v2 differential

Updated diagnostic:

```text
tools/diagnostics/combat_host_planet_precombat_owner_source_audit.py
```

For every positive-owner reversal timeline it now records:

- all T-1 ships co-located with the planet;
- all explicit directed clan drops to that exact planet;
- future-defender directed drop count;
- complete directed drop stream in ascending Ship ID order;
- whether first/last drop owner is the factual precombat defender;
- total clans ordered by future-defender ships;
- planet T-1 clans;
- planet ground-combat-related raw fields;
- single-defender-drop controls split by drop amount vs starting planet clans.

Hard source hypothesis:

```text
every currently reconstructed positive-owner reversal has at least one
explicit directed clan drop from the factual future defender owner
```

If this fails, do not patch an exception. Inspect the residual for:

- Imperial Assault representation;
- stale/missing perspective order data;
- another cargo-order encoding;
- race-specific mechanics.

## Ground-combat formula boundary

Official Planets.nu documentation independently states:

- foreign-planet clan drops and Ground Combat occur in ascending Ship ID order;
- each successive surviving wave becomes the current defender for later drops;
- default ground attack ratios include Lizard 30:1 and Fury 15:1;
- default ground defense ratios include Lizard 15:1 and Fury 5:1;
- each defense post adds 0.05 to the defender factor;
- Imperial Assault is a special case in this same Host phase.

The v7 diagnostic intentionally inventories the required planet fields before implementing that casualty reducer.

## v7 large batch

Run:

```bash
cd ~/projects/planets-lab
git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase
bash tools/run-combat-c5-mixed-queue-batch.sh
```

New/changed stage:

```text
PLANET DIRECTED CLAN-DROP SOURCE
MIXED SHIP/PLANET DISCOVERY V7
```

Review especially:

```text
changed_with_defender_directed_clan_drop
changed_without_defender_directed_clan_drop
ordered_drop_stream_length:*
ordered_drop:first_owner_is_defender
ordered_drop:last_owner_is_defender
single_defender_drop_controls
single_drop_vs_planet_clans:*
planet_field_presence_on_changed_timelines
precombat_owner_source_inventory_gate_passed
```

All previous combat queue, capture, planet carry, interphase repair, ownership timeline and all-planet initiator regressions remain in the same one-command batch.
