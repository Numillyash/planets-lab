# Observed Planets.nu `loadturn` entity schema

This note records field names and conservative correlations observed from real private-turn snapshots persisted by `planets-intel` in August 2026. It deliberately records schema shape and rule-relevant correlations rather than private game state.

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
- fitted armament counts: `beams`, `torps`, `bays`
- navigation: `x`, `y`, `targetx`, `targety`, `warp`
- orders: `mission`, `enemy`, `friendlycode`
- cargo/resources: `neutronium`, `duranium`, `tritanium`, `molybdenum`, `supplies`, `clans`, `megacredits`
- condition: `damage`

Observed but still deferred include `crew`, `mass`, `experience`, `iscloaked`, history and transfer/order helper fields.

### `ammo` correlation

A live schema/value correlation was performed against the public `/static/all` hull table on 2026-08-13.

The following patterns were observed repeatedly:

- torpedo-only fitted ships: `torps > 0`, `bays = 0`, and `ammo` varies with the carried torpedo quantity;
- carrier fitted ships: `bays > 0`, `torps = 0`, and `ammo` varies with the carried fighter quantity;
- hull weapon-slot capacity is not the same as fitted armament: some hulls with non-zero static `launchers` had `ship.torps = 0` in the turn state;
- `beams`, `torps` and `bays` therefore represent actual fitted counts and must be used for current ship state rather than static hull maxima.

Representative observed rows included:

- hull 33: static `launchers=4`, turn `torps=4`, `bays=0`, non-zero `ammo`;
- hull 35: static `launchers=6`, turn `torps=6`, `bays=0`, non-zero `ammo`;
- hull 52: static `fighterbays=10`, turn `bays=10`, `torps=0`, non-zero `ammo`;
- hull 99: static `fighterbays=8`, turn `bays=8`, `torps=0`, non-zero `ammo`;
- hull 81: static `launchers=2`, while observed turn records had `torps=0`, demonstrating that hull slots are not fitted-count state.

Canonical decoding policy:

- if `bays > 0` and `torps == 0`, map `ammo` to fighters;
- if `torps > 0` and `bays == 0`, map `ammo` to torpedoes;
- if both are positive, or a non-zero `ammo` value cannot be classified, preserve it as unresolved ammunition instead of guessing.

This policy covers ordinary carrier and torpedo ships while explicitly protecting hybrid/special cases such as Horwasp or future campaign mechanics.

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

Observed field presence is not by itself proof of game-rule semantics. New mappings should be added only when their meaning is unambiguous, supported by repeated live correlations, or supported by the rules/static-data layer.
