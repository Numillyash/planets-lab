# M2: Real /game/save schema-only reconnaissance, no submission

## Verified previous checkpoint

`planetary-owner-capture-bundle-v1` server evidence was independently
checked on the `runtime-logs` branch:

- `runtime-logs/planetary-owner-capture-bundle-v1/20261016T214829Z_1f5ee1db6ad8`
- Source: `1f5ee1db6ad82a15791981f3384ef2101d327e1d` / `main`
- Metadata Git blob: `68de96eb53a61708c2fb50bd0dcef2a4cef9765c`
- Report Git blob: `62667e5fc3b415d7d9e22170883727ef94c688f4`
- `exit_code=0`, `source_dirty=false`, `missing_artifact_paths=[]`.
- `complete_bundle_accepted=true`, `missing_player_abstains=true`,
  2 hypothetical phase placements, 8/8 abstention controls, no corpus read.
- `NuHost_orders_authenticated=false`,
  `independent_server_submission_acknowledged=false`,
  `independent_clock_provenance_verified=false`,
  `historical_differential_verified=false`.

This successfully tests *our own* owner-scoped aggregation, not server
acceptance of any genuine player instructions.

## API evidence and previously invalid shortcut

Primary documentation:

- https://help.planets.nu/API lists `/game/save` as a command-saving API
  call and describes general request/response behavior.
- https://help.planets.nu/API-game-loadturn explains `savekey` in the
  private `/game/loadturn` response; **never publish savekey or apikey**.
- https://help.planets.nu/host-order documents the early update of
  client-side actions before other Host phases.
- https://help.planets.nu/transfer describes own-planet cargo transfer
  interactions alongside other transfers.

These references **do not specify** an authenticated, field-level
`/game/save` request/acknowledgement schema for this project's
`PlanetCargoTransferOrder`. A client-side cargo mutation might be
persisted as already-updated ship/planet stock rather than an explicit
Host command. We must not label such a state change as a NuHost order,
nor turn a generic HTTP 200 or `success=true` into definitive
server-accepted-order evidence.

## Implemented opt-in investigation

`tools/client/planets_nu_save_schema_probe_v1.js` is a **browser-only
passive observational schema probe**. An authorized player may paste its
source into the Developer Tools Console of their own currently loaded
Planets.nu game BEFORE using the site's ordinary save action.

It wraps existing fetch/XMLHttpRequest methods only to **observe**
requests whose actual hostname is `planets.nu` or its subdomain and
whose exact path is `/game/save`. It issues NO additional API
calls and does NOT press Save, modify the request, supply keys or edit
any game state.

The in-memory report only records: transport type, method, numeric HTTP
status, up to six structural observations of allowlisted mechanical
JSON/form **field names and value types**, counts of hidden/unlisted
keys, and whether the response explicitly contains `success` boolean.
It **never stores raw requests, raw responses, cargo amounts, object
identifiers, usernames, note text, friendly codes, cookies, credentials,
URL query strings, savekey, apikey, or secrets**. Non-allowlisted keys
are replaced by counts. Embedded JSON in form fields is reduced to
safe shapes. Very large bodies and undecodable responses remain
unparsed. The observer has no persistence, clipboard access, callbacks
to outside services or telemetry.

Browser usage (manual, own authorized game only):

1. Open a current game and DevTools (F12), then Console.
2. Copy the exact **source code** from the linked repository JS file
   and paste it into the console. The observer installs once and prints
   only a short installation message.
3. Use the **ordinary game UI** to save the turn once. Do not execute
   any extra POST requests or run Host.
4. In the Console, inspect
   `__planetsM2SaveSchemaProbeV1.report()`.
   This is only a sanitized *schema* report.
5. Call `__planetsM2SaveSchemaProbeV1.stop()` to restore the original
   browser fetch/XMLHttpRequest methods.

Do NOT paste your raw DevTools Network tab, HAR archive, API responses,
source `loadturn` with `savekey`, cookies or raw `/game/save`
request into GitHub. The sanitized schema can be inspected locally and
shared **only after the player has reviewed it**. Like all browser
instruments, the probe only sees network operations occurring AFTER
its installation and may miss requests that use service workers,
a different JavaScript realm, or a client transport not wrapped here.

## Acceptance and next gate

`tests/js/test_planets_nu_save_schema_probe_v1.cjs` simulates own-user
XHR and fetch saves, structured/encoded bodies, credential-containing
responses, non-save traffic and script removal. The CI runner verifies
no extra send, no private value output, no credential key names and
restoration of original methods. **No real Nu API request is executed
by any test**.

This first browser save schema is solely to identify which data shapes
need subsequent independent study. A future explicit *consensual* adapter
must use independently verified request/response semantics and an actual
server acknowledgement before we promote a submitted command to
`ORDER_AUTHENTICATED`. Distinguish:
(a) client-side planet and ship state changes before Host,
(b) stored save payload,
(c) server acknowledgement,
(d) Host-executed effects,
(e) observed next-turn result.
No new causal NuHost differential until those are separable.

Avoid additional internal synthetic HMAC stages without independent
external input. Keep C5 frozen, draft PR #28 draft, corpus `CURRENT`,
canonical combat, external-engine and production IntelBoard untouched.

## October 17 owner observation: no matching save requests yet

An authorized user installed v1 successfully in the browser and returned:

```json
{"schema":"planets-lab.save-schema-observation.v1",
 "status":"SCHEMA_ONLY_NOT_SERVER_ORDER_ACK_OR_NUHOST_VERIFIED",
 "observed_save_calls":0,"events":[],
 "values_logged":false,"credentials_logged":false,
 "submitted_order_mapping_verified":false,
 "server_order_acknowledgement_verified":false,"host_phase_verified":false}
```

This is **zero qualifying calls observed**, not proof the game didn't
save, not evidence for any NuHost rule or transport format. It remains
unknown whether the regular Save action was performed between installation
and report collection; whether the live site uses another route, a
different transport/realm, or no new HTTP request is also unknown.

The initial v1 probe discarded all requests except the exact
`/game/save` path, so it could not distinguish these outcomes.
The v1.1 diagnostics fix adds **counts only**, under `diagnostics`:

- `planets_requests_total`, `planets_post_requests`,
  `xhr_requests`, `fetch_requests`;
- `route_categories` with fixed enumerated labels
  `game_save_exact`, `game_save_candidate`, `game_turnready`,
  `game_other`, `account_other`, `planets_other`.

The origin remains limited to `planets.nu` and its subdomains.
No actual URL, URL path, query string, credentials, request/response
body, resource values or other origin identifiers are added to reports.
For nonexact paths we count categories only, **without even parsing
their bodies or responses**. Full request/response *schema-only*
extraction remains restricted to the existing exact `/game/save`.
Existing output fields and stop/report interface are backwards-compatible.

Suggested next user-authorized observation: open the game, run current
script, perform **one ordinary UI save** (if available, or wait for its
normal autosave), inspect `report()` BEFORE calling `stop()`.
If `planets_requests_total=0`, the instrumented JavaScript realm has
not observed any Planets.nu fetch/XHR network calls while active. If
some requests but `game_save_exact=0`, use coarse categories to
narrow the route. Do not run artificial POSTs to trigger the instrument.
A page reload loses the injected observer. If ambiguity persists,
inspect only the HTTP **method and pathname** in DevTools Network
after removing queries; never export a raw HAR.

No authenticated private orders or server-acceptance proof have been
obtained from the first zero-observation report. Keep the full NuHost
historical causal comparison `ABSTAIN`.
