# M2 V2 owner-signed prehost orders — cargo plus base technology

Date: 2026-10-19.

## Baseline checkpoints

M2 V3 frozen 68-game runtime: `runtime-logs/m2-public100-surface-context-v1/20261019T143058Z_1f0721ca1186`. Exit 0 and frozen 136 pairs / unchanged corpus CURRENT. It remains descriptive: 915 surface mineral comparisons, 108 unique opposite ship-cargo associations, 315 unique residual planet windows, 65 cargo-candidate windows, 15 weak-linked base-tech-change windows, only 1 overlap. No observed order or Host scheduling is established.

M2 explicit standard starbase technology purchase is merged via PR #239, source `6b8a072ccb8b49d744b67c791a37251df7f1d11a`, PR CI #1351 and main CI #1352 successful. Server synthetic runtime `runtime-logs/m2-starbase-tech-synthetic-v1/20261019T184141Z_632d83c21ab8`, exit 0, six synthetic checks, cost 7→10 = 2400 MC. This is **internal modeled** evidence only, not historical NuHost parity.

## Evidence gap and separate V2 capture

The legacy owner-scoped `planetary_owner_capture.py` V1 deliberately rejects `StarbaseTechUpgradeOrder` to prevent silently stripping newly supported orders from the signed `ship_orders`-only record.

`planetary_owner_capture_v2.py` adds a **separate schema and HMAC domain** for a complete, locally asserted owner's `ship_orders` and `starbase_tech_orders` in one signed row. V1 is unchanged and never implicitly upgraded. The V2 contract requires:

- exact expected envelope/payload/technology keys, a prestate fingerprint, exact game/turn identity, owner-key trust and SHA256-HMAC on canonical JSON with a separate v2 domain;
- actual owner and planet identity of a base in complete `GameState`, tech targets in the 1–10 range with a positive increase, no duplicate base orders, and unchanged validation for ship transfer payloads;
- an *explicit signed owner record for every declared game player*, including empty rows. Missing owner, unknown key, malformed technology field, wrong state, duplicate, mixed V1/V2 or capture time at/after caller-provided Host start gives ABSTAIN;
- no raw envelope, HMAC keys, player/planet/ship identifiers or private account details in published evidence.

The new `reconcile_owner_observations_v2()` admits an all-player bundle and then invokes the existing conditional full-state comparison only with a complete poststate, explicit technology phase placement and owner-specific standard-tech eligibility caps. Both cargo-transfer placements remain hypothetical, even if a full synthetic state matches. V2 signing does **not** establish server receipt, whether/when NuHost executed the orders, an independently witnessed Host start or premium/custom-campaign pricing; no `DIFF_VERIFIED` label is promoted.

No automatic network collection or historical order inference, and no new public68/public100 corpus processing are introduced. Existing V1 and canonical combat paths remain unchanged.

## Next independent evidence step

A genuine Host differential would require independently witnessed and server-accepted complete pre-Host orders (or a separately proved equivalent), external timestamp provenance, exact owner-current pre/post complete states, and interference-free phase placement. Neither the synthetic HMAC signer nor passing V2 regression tests supplies those observations. Keep all private order envelopes out of `runtime-logs` and the public source tree.
