# M2: authorized full `/game/save` payload capture and field-level differential V1

## Why this changes approach

Six real `/game/save` XHR POSTs were observed by the user in a normal
Planets.nu early-turn session. All six returned HTTP 200 and
`success=true`; four had exactly four unknown URL-encoded request
fields (three numeric-text, one opaque-text) and the other two had five
unknown fields (three numeric-text, two opaque-text). The trace contained
six `game_save_exact` POSTs, followed by one `game_turnready` POST,
followed by two account-route POSTs. No JSON object was identified
among those *unknown* fields by the prior v1.3 shape-only tool.

**Those reports proved only network events.** A critical flaw in our
research approach was hiding ALL non-credential game values, leaving no
way to establish how the client's saves represent a planet's tax rate,
ship cargo, or actual field names. The game is an authorized early-turn,
Home Sector or owner-controlled test environment, and the player explicitly
approved collecting the game's detailed state and instructions while
keeping authentication credentials secret.

The separate browser tool
`tools/client/planets_nu_save_payload_capture_v1.js`
switches from *schema-only* to **game-state data collection** under
the owner's consent. Do not attempt to reconstruct commands from
opaque counts.

## What this tool observes

Only `fetch` or `XMLHttpRequest` operations to a verified
`planets.nu` host with exact `/game/save` path are intercepted
and added to its in-memory report (max 10 recent completions).

It retains **actual game values and arbitrary non-credential field names**.
For form-encoded requests it retains every non-secret field and tries to
parse nested JSON values, including `turn`. That includes ship and
planet IDs, tax rates, cargo amounts, missions, resources, and unknown
game-field names. It records HTTP status and a recursively sanitized
API response, but never HTTP headers or full request URLs.

`diff(indexA, indexB)` computes up to 250 changed leaf values
between the stored save *request* snapshots and returns paths like
`$.request.body.turn.planets[0].colonisttaxrate`, original values
and new values. This path is an example from a **synthetic test**,
not an assertion about the actual Planets.nu save format.

### Secret and safety boundary

Known credential-like JSON/form field names are replaced by
`<REDACTED_CREDENTIAL>` recursively, including `apikey`,
`savekey`, authorization/token/password/cookie/session names,
refresh/access tokens, and nested objects. Query strings and headers
are never exported. The instrument does not read browser cookie
stores, automatically copy/export data, use persistent storage,
modify the saved request, click Ready, or submit any API request.

**Field-name-based filtering cannot guarantee perfect credential
removal in proprietary opaque strings or previously unseen credential
names.** The owner MUST review the report before sharing it.
Never share a raw Network HAR, cookies or an unsanitized cURL request.
The original pure schema-only probe is still available if desired.
Do not run both probes simultaneously.

The capture is from the user's **own authorized session**, and must
remain local or in the private conversation. Do not commit real game
order snapshots to GitHub or evidence branches. CI uses fake accounts,
fake browser objects and synthetic data only.

## How to use

1. In a current, personally controlled Home Sector or custom game,
   open DevTools Console in the game tab. If the old schema observer
   is running, stop it:
   `__planetsM2SaveSchemaProbeV1.stop()`.
2. Open this file in GitHub, review and paste its **full source** once
   into the Console. It will install
   `__planetsM2SavePayloadCaptureV1`.
3. Make an ordinary change that you actually want to save (or a
   controlled reversible tax-rate change). Planets.nu's UI may
   autosave: **there is no standalone Save button** in the observed
   client. The probe records naturally generated requests only.
   Do not toggle Turn Ready solely for research.
4. Make a second intended or reversible change. Check the count:
   `__planetsM2SavePayloadCaptureV1.report().observed_save_calls_retained`.
5. To inspect locally:

   ```javascript
   console.log(JSON.stringify(__planetsM2SavePayloadCaptureV1.report(), null, 2))
   console.log(JSON.stringify(__planetsM2SavePayloadCaptureV1.diff(0, 1), null, 2))
   ```

   `diff(0,1)` needs at least two captured saves. Where only one
   request was sent, use `report()` and don't invent an earlier
   comparison. The capture holds the most recent 10 events, so indices
   refer to entries in the *current* report.
6. Review local output for accidental credential fields or
   untrusted free-text secrets, and share only the approved sanitized
   report and diff. Then run
   `__planetsM2SavePayloadCaptureV1.stop()` to restore fetch/XHR.
   A full reload also clears the observer.

Do not paste auth keys into the chat, source tree, issue tracker or
logs. Avoid sending any actual third-party player's private orders.

## Acceptance conditions and next implementation

The synthetic browser test verifies:

- Real game values and nested JSON inside `turn` survive.
- Save credentials in both form and nested payloads, response, plus
  request-URL query secrets, do NOT appear in the captured report.
- Two otherwise matching tax-rate saves yield one deterministic
  changed leaf with before/after.
- Unrelated endpoints are ignored, no additional network calls
  happen, and `stop()` restores native functions.
- A report is detached from retained observations to prevent
  accidental mutation.

**No real `/game/save` payload has been supplied yet.**
Do not invent the actual save field semantics. After the owner shares
at least one actual redacted capture, examine whether `turn`
contains serialized per-entity game state or commands, and implement
an offline parser of *observed* fields only. Then execute a bounded,
independent test of saved object changes (prefer a controlled Home
Sector) against subsequent turns. Preserve separate labels for
client-request-observed, server-response-observed, owner-attested,
Host-executed, and next-state-observed.

The existing `PlanetaryOrderAwareSlice` and
`planetary_owner_capture.py` stay separate. A successful
`/game/save` response alone still does not establish the NuHost
phase order, the actual submitted `PlanetCargoTransferOrder`,
or causal historical match. No promotion to `DIFF_VERIFIED`.

C5, production `planets-intel`, canonical combat, corpus
`CURRENT`, research branch and draft PR #28 stay untouched.
