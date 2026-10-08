# Site precombat dynamic probe v1

Date: 2026-10-07

## Trigger

Terminal replay runtime on source:

    4e6482dc7dbe23395a59bea19df1f094b4e89ae3

failed closed at current VCR 592 with the single mismatch:

    ship=140 side=right field=torpedoes carried=0 factual=20

Runtime evidence:

    runtime-logs/site-combat-terminal-replay-v1/
    20261007T081704Z_4e6482dc7dbe

## Provenance conclusion already established from code/history

The initial carried queue before V592 has no pair occurrence involving ship 140.
Therefore ship 140 has no pre-window combat appearance in the target site
history.

_initial_state_before_window consequently seeds ship 140 from the T-1 prediction
record. Those predictions are built from owner_rows for before_turn=140.

The factual VCR592 start vector belongs to battle turn 141.

Thus the observed 0 -> 20 torpedo difference is a T-1 -> precombat-current-turn
state delta, not a terminal carry failure inside V592+.

This probe exists to identify the current-turn mechanism responsible for that
delta before any rule or anchor is promoted.

## Probe

    tools/diagnostics/combat_site_precombat_dynamic_probe.py

Tracked runner:

    tools/run-site-precombat-dynamic-probe-v1.sh

Evidence wrapper:

    tools/run-site-precombat-dynamic-probe-v1-with-evidence.sh

For both participants of V592 it reports:

- whether initial state came from a pre-window VCR appearance or T-1 prediction;
- prior appearances;
- T-1 prediction source;
- T-1 raw FC/mission/location/resources plus every key containing
  torp/fighter/transfer/ammo;
- carried state immediately before V592;
- factual VCR592 start state;
- torpedo delta;
- explicit MKT friendly-code candidate;
- ships whose T-1 transfertargetid points at the participant, with their
  transfer-related raw fields.

## Evidence boundary

Read-only diagnostic only. It does not seed carried state from V592 and does not
relax the terminal replay exactness check.

The next change depends on evidence:

- if MKT explains +20, implement/promote the needed precombat MKT state update;
- if an explicit ship transfer explains +20, implement the corresponding
  transfer projection;
- if neither is present, classify the missing precombat dependency before
  deciding whether a scoped factual start-window anchor is justified.


## Runtime result

Runtime evidence:

    runtime-logs/site-precombat-dynamic-probe-v1/
    20261008T021649Z_0d08f8819271

V592 participants:

    ship 184:
      source prewindow_vcr_appearance
      carried torpedoes 0
      factual VCR torpedoes 0
      exact

    ship 140:
      source tminus1_prediction
      carried torpedoes 0
      factual VCR torpedoes 20
      T-1 ammo 20
      T-1 torps 2
      T-1 bays implicitly 0 / torpedo ship
      torpedoid 10
      no MKT
      no inbound transfer

This disproves the initial hypothesis of a missing current-turn MKT/transfer
phase for the +20 delta.

The T-1 raw record already contains the correct combat ammunition as Nu
`ammo=20`. The mismatch was caused by _raw_active_ship independently looking
for non-existent raw fields `torpedos/torpedoes` instead of using Nu's
`ammo` field decoded according to fitted launchers/bays.

## Fix direction

_raw_active_ship must use the same Nu ammo semantics already implemented by
planets_lab.data.nu_loadturn._ship_ammo:

- launchers > 0 and bays == 0: ammo -> torpedoes
- bays > 0 and launchers == 0: ammo -> fighters
- both fitted with ammo > 0: unresolved/fail closed

This is an initial-state decoding fix, not a new Host mechanics rule.
