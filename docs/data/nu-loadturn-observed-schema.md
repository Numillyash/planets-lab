# Observed Planets.nu `loadturn` entity schema

This note records field names observed from a real private-turn snapshot persisted by `planets-intel` in August 2026. It deliberately records schema shape rather than private game values.

## Envelope

The working private-turn path uses:

- `rst.game`
- `rst.player`
- `rst.planets[]`
- `rst.ships[]`
- `rst.starbases[]`

## Planet fields used by the canonical importer

Observed and mapped:

- identity/location: `id`, `x`, `y`, `ownerid`
- surface cargo: `neutronium`, `duranium`, `tritanium`, `molybdenum`, `supplies`, `clans`, `megacredits`
- underground minerals: `groundneutronium`, `groundduranium`, `groundtritanium`, `groundmolybdenum`
- mineral densities: `densityneutronium`, `densityduranium`, `densitytritanium`, `densitymolybdenum`
- structures: `factories`, `mines`, `defense`
- colonists: `colonisthappypoints`, `colonisttaxrate`
- natives: `nativeclans`, `nativetype`, `nativegovernment`, `nativehappypoints`, `nativetaxrate`

Observed but not yet mapped include build-target, readiness, derived/check totals, Horwasp/pod fields and UI-oriented values.

## Ship fields used by the canonical importer

Observed and mapped:

- identity/ownership: `id`, `ownerid`, `hullid`
- components: `engineid`, `beamid`, `torpedoid`
- navigation: `x`, `y`, `targetx`, `targety`, `warp`
- orders: `mission`, `enemy`, `friendlycode`
- cargo/resources: `neutronium`, `duranium`, `tritanium`, `molybdenum`, `supplies`, `clans`, `megacredits`
- condition: `damage`

Observed but deliberately deferred:

- `beams` — installed beam count
- `torps` — torpedo-tube count
- `bays` — fighter-bay count
- `ammo` — ammunition quantity whose interpretation depends on ship/hull weapon context
- `crew`, `mass`, `experience`, `iscloaked`, history and transfer/order helper fields

The importer must not split `ammo` into canonical fighter or torpedo ammunition until static hull/component context is available.

## Starbase fields used by the canonical importer

Observed and mapped:

- `planetid`
- `defense`
- `fighters`
- `hulltechlevel`
- `enginetechlevel`
- `beamtechlevel`
- `torptechlevel`

The observed starbase records contain `raceid` but no `ownerid`; ownership is therefore resolved from the associated planet.

## Policy

Observed field presence is not by itself proof of game-rule semantics. New mappings should be added only when their meaning is unambiguous or supported by the rules/static-data layer.
