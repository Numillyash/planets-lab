# M2: one-pass full-session Planets.nu HAR capture (no per-action experiments)

## Purpose and scope

The owner reported that repeated manual click/console/reply loops are
too distracting during normal game play. **Replace these loops with
one-time native browser Network logging**, followed by a single
local conversion at the end of the session. Avoid Wireshark for API
payload reconstruction: ordinary HTTPS/TLS traffic is encrypted on
the wire, whereas the browser's own DevTools Network view already
has the request bodies before encryption.

No special API key, proxy certificate, MITM setup, user script, or
turn-ready toggles are needed. This is passive logging of
the owner's authorized game session, not code that sends orders.

## Windows / Chrome or Edge: quick start

**At the start of a normal playing session (one-time setup):**

1. Open the Planets.nu game tab and press **F12**.
2. In **Network**, enable **Preserve log** (important if Planets.nu
   redirects to its home screen after pressing Turn Ready).
3. Confirm Network recording is enabled (red recording indicator);
   optionally clear older requests to keep the HAR smaller.
4. Play normally. Move ships, load/unload cargo, adjust taxes,
   build factories, mark Ready whenever actually ready.
   Do **not** intentionally reproduce tiny test sequences unless desired.
   Keep DevTools open while the capture is running.

**At the end of the session:**

5. In Network, use **Export HAR / Save all as HAR with content**.
   Browser UI wording varies. Preserve request POST bodies if the browser
   offers choices. Do not enable capture of sensitive cookies/headers
   unless strictly needed; the converter does not use them.
6. Keep the original HAR **only on your own machine**. It can contain
   cookies, authorization headers, savekey/apikey, personal browsing
   activity and private game state. **Never upload the raw HAR**.
7. Run the stand-alone stdlib-only converter once. For example in
   PowerShell, with Python 3 installed:

   ~~~powershell
   $Capture = Join-Path $env:USERPROFILE 'Documents\planets_capture'
   New-Item -ItemType Directory -Force -Path $Capture | Out-Null
   $Source = 'https://raw.githubusercontent.com/Numillyash/planets-lab/main/tools/diagnostics/nu_har_save_extract_v1.py'
   Invoke-WebRequest $Source -OutFile (Join-Path $Capture 'nu_har_save_extract_v1.py')
   py -3 (Join-Path $Capture 'nu_har_save_extract_v1.py') --input 'C:\path\to\your_session.har' --output (Join-Path $Capture 'save_bundle_clean.json')
   ~~~

   Replace the sample HAR path with the exact HAR exported by your
   browser. The extractor makes NO outgoing requests and does not need
   your credentials. If Python is available through python instead
   of py -3, use that command.

8. **Review save_bundle_clean.json for any unexpected secrets**
   (especially private text fields with unfamiliar names). Upload
   only that JSON. It contains real game-state data by design,
   as explicitly authorized by the owner. Do not put it into GitHub.

## Extracted format

The extractor reads HAR 1.2 log.entries, selects only **POST** calls
to exact /game/save under planets.nu or its subdomains, and counts
/game/turnready without copying its payload. Unrelated websites,
account operations, other gameplay API calls, URLs, query strings,
HTTP headers and cookies are ignored entirely. Form bodies are
decoded and all noncredential ShipN, PlanetN, StarbaseN field names
and their **actual values** are preserved.

Credential-named values are replaced (including nested
apikey/savekey, auth, password, access/refresh tokens, cookies,
session, secret and other conventional credential names). A legacy
Field:::value|||Field:::value game record is preserved with known
embedded secret-named subfields masked. Response JSON is sanitized;
no raw HTML or arbitrary non-JSON response bodies are emitted. The
converter will not retain the full raw HAR in its output.

The output is a single JSON bundle with schema
planets-lab.har-save-capture-bundle.v1. It contains one
planets-lab.save-payload-capture.v1 session per distinct
(gameid, playerid, turn). Each save record retains the originally
observed form body, HTTP status, sanitized response and HAR
startedDateTime/duration metadata (without a site URL). No **ten
request ring-buffer limit** applies: the entire HAR is processed.

If an entry has an absent or ambiguous POST body or cannot be
associated with a game/player/turn, the extractor **skips it** and
counts it in save_posts_extract_failed, rather than inventing data.
Large form strings and duplicated form keys are rejected.
Existing file output is not silently overwritten (explicit
--overwrite opt-in is available).

## Optional local, repo-backed automatic diff

If the full planets-lab repository is available, the existing
decoder supports the HAR bundle:

~~~powershell
python tools/diagnostics/nu_save_payload_diff_v1.py --input 'C:\Users\...\Documents\planets_capture\save_bundle_clean.json' --output 'C:\Users\...\Documents\planets_capture\save_analysis_private.json'
~~~

The analysis groups each turn separately and compares each ShipN,
PlanetN or StarbaseN against its last preceding included occurrence.
It never interprets an omitted entity as deletion or creates a
Host order from first appearance. The optional analysis output
contains actual game data and must also stay private.

One save_bundle_clean.json is sufficient for subsequent analysis
in the private conversation: the user does **not** need to run this
optional second command or identify individual actions.

## Boundaries and future validation

The HAR demonstrates client-submitted changes and possibly
application-level responses, but no explicit per-order server
acknowledgment, accepted cargo command, NuHost-phase boundary, or
next-turn comparison is independently attested. Automated save
activity should be grouped by observed timestamps, **not assumed**
to correspond one-to-one to each UI action. A clear record of the
user's action can improve causal attribution, but is optional.

CI fixtures use only synthetic game IDs, XHR bodies and fake keys.
They test third-party exclusion, exact origin/path filtering,
JSON and base64 responses, nested credential masking, partial
snapshots, multiple turns and compatibility with the existing
read-only state-differential analyzer. No raw captures, private
keys or live game actions are checked into the repo.

Original HARs and generated data must stay out of public commits,
runtime-logs, draft PR #28, and production IntelBoard. C5 and
the canonical combat engine stay frozen.
