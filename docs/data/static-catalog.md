# Planets.nu static catalog

Planets.nu documents `/static/all` as the public source for core assets such as races, hulls, beams, engines, torpedoes and advantages.

The first `planets-lab` static-data layer is intentionally lossless and schema-tolerant:

```text
/static/all JSON
      |
      v
import_static_all()
      |
      v
NuStaticCatalog
```

Records are indexed by integer `id` but otherwise remain raw dictionaries. This prevents the simulator from silently guessing undocumented API field names or meanings.

Typed projections such as `HullSpec`, `EngineSpec`, `BeamSpec` and `TorpedoSpec` will be added only after the live record keys are captured and cross-checked.

This catalog is a dependency for interpreting turn fields such as `hullid`, `engineid`, `beamid`, `torpedoid`, `beams`, `torps`, `bays` and `ammo`.
