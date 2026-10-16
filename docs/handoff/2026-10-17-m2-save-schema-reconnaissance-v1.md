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

## 2026-10-17 first positive own-client save observation

After PR #214 extended the browser diagnostic categories, one ordinary
user-authorized Planets.nu UI save produced a **positive** redacted
schema observation (the user shared no credentials or resource values):

- `observed_save_calls=1`; `transport=xhr`, `method=POST`,
  exact `/game/save` match, HTTP `200`.
- Allowlisted request names `gameid`, `playerid`, `turn`,
  each with type `string`. **No values/IDs were exposed.**
- `redacted_key_count=2`, `unknown_key_count=1`.
  Neither the names nor values of these three fields are known.
- Response: allowlisted `success` boolean observed `true`, plus
  one unknown response field (not exposed).
- During the probe: four Planets.nu XHR POSTs in total:
  one `game_save_exact`, one `game_turnready`, two `account_other`.
  `game_save_candidate=0`, `game_other=0`.
- `submitted_order_mapping_verified=false`,
  `server_order_acknowledgement_verified=false`,
  `host_phase_verified=false`.

This establishes a **real client request and positive application-level
save response**. It does **NOT** yet attest specific order fields or
that NuHost executed a cargo instruction. The `turnready` call only
proves traffic in that category, not its status or outcome.
Do not reverse-infer private cargo amounts or source orders from post
turn stocks. The remaining unknown request field is the crucial
schema gap.

### Unknown form-field profiling (probe v1.2)

`tools/client/planets_nu_save_schema_probe_v1.js` now emits a bounded
`opaque_field_value_profiles` / `opaque_form_fields` **for exact
`/game/save` only**:

- At most two profiles for unknown field *values*, which contain only
  safe type labels (`string`, `number`, `json_object`,
  `json_array`, etc), and optionally the same strict allowlist of
  nested mechanic field NAMES and their TYPES. This could distinguish
  a serialized ship/planet object from a scalar flag without retaining
  data.
- Arbitrary unknown field names are NEVER output (names themselves
  could contain secrets). String and numerical values, identifiers,
  array lengths, credentials, full URL, HTTP body and nested unlisted
  names remain excluded.
- Input is parsed only in memory and only after a naturally occurring
  save request. No new requests, no interception/replacement of the
  user command, no automatic Ready toggling, no packet captures.
- JSON recognition inside an unknown field does **not** prove a
  submitted command mapping, an independently acknowledged save, or
  temporal NuHost causality.

To obtain an informative next observation, install current JS source
in the same game via DevTools **before** an ordinary save, then call:

```javascript
console.log(JSON.stringify(__planetsM2SaveSchemaProbeV1.report(), null, 2))
```

Review the sanitized report locally before sharing. Call
`__planetsM2SaveSchemaProbeV1.stop()` afterwards. A browser reload
destroys the observer. Do not paste a HAR, raw request, API/savekey,
cookies, or token into any public report.

The next engineering step is to evaluate this new profile and decide
whether the unknown save field contains a serialized state update,
an explicit cargo instruction or something else. A verified field-level
`PlanetCargoTransferOrder` mapping is still out of reach without
separating the client-observed state mutation from server-accepted
instructions. Historical order-aware `DIFF_VERIFIED` stays blocked.

## 2026-10-17 controlled tax-rate edits: four live saves, no separate Save button

The player reported the actual client workflow: on several of their
planets they changed colony tax rates; there is **no independent game
Save button** in that interface. The `Turn Ready` control returns
to the dashboard. We should stop instructing the player to click a
nonexistent Save control.

The same opt-in probe (v1.2) observed:

- `POST /game/save` via XHR **four times**, each HTTP 200 and
  `success:true` in the parsed response.
- One `game_turnready` and two `account_other` XHR POSTs:
  seven Planets.nu POSTs in total, no fetch and no other game routes.
- Four request shapes include string-typed `gameid`, `playerid`,
  `turn` plus two secret-masked form fields and additional unknown
  fields. The actual values were never collected.
- `opaque_form_fields.unknown_field_count` was **5, 5, 4, 4**
  (two sets of otherwise identical safe structures).
- Every unknown value in the *first two sampled positions* was a
  scalar string classified as `not_json`.
- Response `success=true` was observed, and one additional response
  field was anonymous numeric. No per-command acceptance witness was
  independently recorded.
- No per-request timing relative to the UI edits was observed; this
  does **not** prove one save per tax edit or whether readiness also
  forces another autosave. The observations support further testing
  of **automatic/client-triggered persistence**, not a fully proven
  client scheduling rule.

### Diagnostic interpretation bug in v1.2, corrected in v1.3

For URL-encoded form requests, `decodeString()` used a single synthetic
`(unlisted)` property for *all* unknown parameter names. This
artificially produced `request_schema.unknown_key_count=1` and a
phantom `opaque_field_value_profiles=[{"outer_type":"null"}]`.
These two diagnostics should **not** be interpreted as a real null
field or only one unknown parameter. The independent form parser
correctly counted 5 and 4 unknown fields.

V1.3 removes that placeholder for form parsing and presents
`request_schema.unknown_key_count` from the true sanitized
form parameter count. It preserves the first two (redacted) profiles,
but now also reports coarse **encoding histograms for up to 24 unknown
field values** and up to two sanitized structured JSON candidates
located anywhere within those fields, even if they occur after
several scalar fields. An event's `diagnostics.route_sequence` stores
only the order of up to 24 coarse route categories and POST/OTHER
methods, without timestamps, URLs, raw paths or data.

The v1.3 code remains passive: it neither presses `Turn Ready` nor
changes a tax rate, game data, save request or account configuration.
Tests reproduce the historical 5→4 unknown-form-count pattern using
synthetic inputs only and ensure that values, credentials and unknown
field names never appear in reports.

**Scientific status remains observational.** User consent to run a
passive probe on an owned game, four successful-looking save API
responses, and local owner-key signatures do not establish an
authenticated per-field `PlanetCargoTransferOrder` mapping,
the exact position of persistence relative to Host, or causally
verified NuHost economy formulas. Treat those as open and
`ABSTAIN` for historical order-aware differential.

There is no need to reverse readiness or artificially alter
additional game orders now. Wait until the player naturally edits
the next ordinary game turn if further field-shape evidence is needed.
