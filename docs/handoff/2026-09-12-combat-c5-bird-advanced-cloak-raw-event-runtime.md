# C5 Host combat — Bird Advanced Cloak raw-event runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Runtime source

```text
17dd581be1a2ffc5c99154a24854765e6f839246
```

Targeted tests:

```text
11 passed
```

Diagnostic:

```text
tools/diagnostics/combat_host_bird_advanced_cloak_event_audit.py
```

Local runtime artifact:

```text
artifacts/combat-bird-advanced-cloak-events.json
```

## Decisive finding

The factual Advanced-Cloak control is no longer unexplained.

For `680435/T31 ship68` (Bird Resolute, mission9 Super Spy), the raw Host messages contain an explicit mine-hit report:

```text
RESOLUTE CLASS BATTLECRUISER ID#68 has struck a mine!
Damage is at: 55
(1989, 2273)
```

The Bird owner's perspective also reports that ship68 passed through 21 light-years of mines during the turn.

The factual VCR at `(1984,2266)` then starts the same physical ship with:

```text
objectid=68
hullid=31 Resolute
damage=55
leftownerid=3
```

and it fights Fed Nebula ship26. Thus the precombat sequence is directly observed:

```text
Advanced-Cloak Super Spy ship68
  -> mine hit during movement
  -> damage 55 / cloak broken
  -> ordinary STANDARD combat
```

This is a positive Host-event trace, not an inference from absence.

## Documentation match

Official Planets.nu cloaking documentation states:

- cloaking requires the ship to be undamaged at cloak engagement;
- Advanced Cloak consumes no cloak fuel but still requires at least 1 KT fuel;
- during movement, a cloaked ship that hits a mine becomes uncloaked;
- mine damage can therefore leave the ship unable to cloak again for the remainder of the relevant precombat sequence.

Sources:

```text
https://help.planets.nu/abil-advanced-cloak
https://help.planets.nu/cloak-details
```

The corpus trace matches this documented Host order exactly.

## Skipped Advanced-Cloak controls

The two expected-blocked rows remain:

```text
620694/T119 ship26 vs attacker74
620694/T119 ship69 vs attacker74
```

Both targets are Bird Resolutes on mission9 and both have stable same-owner/same-hull T identity with:

```text
damage=0
iscloaked=true
```

This T state is attribution-only, but it is positive evidence that those physical ships survived the turn still cloaked while attacker74 instead fought Falcon71.

The raw-message scan around `620694` is very noisy because object IDs such as `26`, `69`, and `74` collide with unrelated ship/planet/minefield IDs. Therefore **absence of a mine-hit message is not used as proof** for ship26/69. Only identity-safe positive evidence may close a branch.

## Campaign / setting context

Both games are non-campaign:

```text
campaignmode=False
cloakfail=0
nowarpwells=False
```

No hidden-mine/campaign advantage separator was found. Bird active advantage inventory contains ordinary required/standard abilities including Super Spy; no special hidden-mine explanation is needed for ship68 because the mine hit is explicit.

## Evidence status

```text
Advanced Cloak + mine hit -> uncloaked:
  DOCUMENTED + CORPUS_OBSERVED + TESTED

ship68 factual eligibility after mine hit:
  CORPUS_OBSERVED (explicit Host message + matching VCR damage)

blanket Advanced-Cloak targetability:
  still NOT promoted
```

The dynamic decloak path is now explained, but a production selector must not consume Host messages or postcombat T state. In the future simulator this state must come from the reconstructed precombat movement/mine/Glory/fuel pipeline.

## Next gate

Build a narrow Advanced-Cloak decisive closure diagnostic that uses only positive identity-safe corpus evidence:

```text
ship68 expected eligible:
  explicit target-specific mine-hit message
  positive mine damage
  factual VCR starts the same target with matching positive damage

ship26/69 expected blocked:
  stable physical identity at T
  T iscloaked=true and damage=0 as attribution controls
```

This diagnostic is an evidence closure, not a production predictor. After it passes, return to the combined population-wide directional STANDARD targetability differential. Keep unresolved dynamic Advanced-Cloak states fail-closed unless upstream precombat state is independently reconstructed.
