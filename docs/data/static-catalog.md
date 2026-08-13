# Planets.nu static catalog

Planets.nu documents `/static/all` as the public source for core assets such as races, hulls, beams, engines, torpedoes and advantages.

The catalog is split into two layers:

```text
/static/all JSON
      |
      v
import_static_all()
      |
      v
NuStaticCatalog        lossless/raw records
      |
      v
NuStaticSpecs          typed simulator-facing projections
```

## Live schema observation

A live `/static/all` response captured through the configured `planets-intel` API proxy on 2026-08-13 contained:

- `hulls`: 211 records;
- `beams`: 10 records;
- `engines`: 9 records;
- `torpedos`: 11 records;
- `torpedosall`: 22 records;
- `races`: 13 records;
- `advantages`: 86 records.

The observed hull schema includes `mass`, `cargo`, `fueltank`, `crew`, `engines`, `beams`, `launchers`, `fighterbays`, `cancloak`, component costs and tech level. Engine records expose `warp1` through `warp9`; beam and torpedo records expose their mass/combat/cost fields.

`torpedos` and `torpedosall` are deliberately kept separate. Turn data references normal component ids (`ship.torpedoid`), while the meaning and identifier space of the larger all-components collection must not silently replace the default set.

## Typed projections

`NuStaticSpecs.from_catalog()` currently produces:

- `HullSpec`;
- `EngineSpec`;
- `BeamSpec`;
- `TorpedoSpec`.

`HullSpec.munition_kind` classifies a hull as `fighters` only when it has fighter bays and no torpedo launchers, and as `torpedoes` only when it has torpedo launchers and no fighter bays. Other cases remain unresolved rather than guessed.

`EngineSpec.fuel_factor(warp)` exposes the observed `warp1..warp9` values for the movement fuel rule.

This static layer is the dependency for interpreting turn fields such as `hullid`, `engineid`, `beamid`, `torpedoid`, `beams`, `torps`, `bays` and eventually `ammo`.

Primary reference: <https://help.planets.nu/API-static-all>.
