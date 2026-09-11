# C5 Host combat — Privateer Rob cloak population pending — superseded

This gate has completed successfully at runtime and is superseded by:

```text
docs/handoff/2026-09-11-combat-c5-privateer-rob-cloak-population-runtime.md
```

Runtime source:

```text
e0b7f9ac91f99e8006546b80ec4a940ab21e2a6e
```

Result:

```text
tests passed
audit rc=0
payload_conflicts=0
candidate_rows=2223
stable_identity=2174
stable_vcr_participant=2
stable true_to_true=1378
stable_before_cloaked_pe_zero_no_vcr=1394
stable_true_to_true_pe_zero_no_vcr=1360
stable_before_cloaked_pe_zero_vcr=0
stable_true_to_true_pe_zero_vcr=0
```

The exact `360690/T82->T83/ship98` residual is a stable Privateer race5 / mission9 / cloak-capable Meteor `true_to_true`, PE=0, no-VCR row.

This population establishes archive cloak-state persistence but does not establish combat-effective cloak because most rows do not prove the presence of a hostile attack opportunity. Current Planets.nu Host documentation keeps Cloak and Rob as distinct Host steps and does not make Privateer Rob a cloak-generating mission.

No `selection.py` or target-order change was promoted from this gate.

Immediate follow-up: classify the two stable VCR-participant rows, then perform a site-conditioned hostile attack-opportunity differential before deciding whether any effective-cloak blocker is safe to encode.
