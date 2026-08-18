# Primary sources

The simulator specification prefers Planets.nu primary documentation. URLs are recorded explicitly so each implemented rule can point back to its evidence.

- API overview: `https://help.planets.nu/API`
- `/game/loadturn`: `https://help.planets.nu/API-game-loadturn`
- Host Order: `https://help.planets.nu/host-order`
- Annotated Host Order: `https://help.planets.nu/host-order-commentary`
- Navigation: `https://help.planets.nu/navigation`
- Warp Wells: `https://help.planets.nu/warp-wells`
- Fuel Consumption Details: `https://help.planets.nu/fuel-details`
- Tow mission: `https://help.planets.nu/mis-tow`
- Intercept mission: `https://help.planets.nu/mis-intercept`
- Horwasp Mite ability: `https://help.planets.nu/abil-mite`

## Source confidence

The official Host Order documents ordering that is considered known, but also states that some items are missing from the complete list. The Annotated Host Order explicitly warns that much of its detail was reconstructed from played games and should be tested before being treated as authoritative.

For that reason, details sourced only from the annotated page should normally remain `DOCUMENTED`/`INFERRED` until backed by a deterministic local test and, where practical, a NuHost differential result.

Historical corpus evidence may also disagree with a current public rule page. Such disagreement must be preserved explicitly rather than silently forcing old observations to match current documentation.
