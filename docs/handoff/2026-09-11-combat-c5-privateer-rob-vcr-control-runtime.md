# C5 Host combat — Privateer Rob VCR control runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded from ordinary promotion.

Runtime source:

```text
6ef2c9344b1544a7e60952db50e1d942e352e53e
```

Command reused the already tested population audit with `--example-limit 3000` and filtered stable VCR-participant rows from the generated JSON.

Runtime:

```text
tests rc=0
audit rc=0
payload_conflicts=0

candidate_rows=2223
stable_identity=2174
stable_vcr_participant=2
stable_no_vcr=2172
before_cloak_true=1433
before_cloak_false=790

stable_before_cloaked_pe_zero_no_vcr=1394
stable_true_to_true_pe_zero_no_vcr=1360
stable_before_cloaked_pe_zero_vcr=0
stable_true_to_true_pe_zero_vcr=0
```

Stable cloak transitions:

```text
true_to_true=1378
false_to_true=693
false_to_false=68
true_to_false=35
```

## The two stable VCR participants

Both controls have a nonzero Primary Enemy and therefore can initiate combat themselves. Neither is a PE=0 targetability counterexample.

### `511506/T15 ship89`

```text
Privateer race5
Meteor hull46
mission9
T-1 iscloaked=true
PE=6
stable identity
true_to_true
VCR7 vs ship45 owner6
ship89 fights RIGHT
```

### `511506/T22 ship157`

```text
Privateer race5
Meteor hull46
mission9
T-1 iscloaked=true
PE=11
stable identity
true_to_true
VCR25 vs ship113 owner11
ship157 fights LEFT
```

Therefore these two rows prove only that a Privateer mission9 ship with persistent raw cloak state can still enter combat when its own PE requests that opponent. They do **not** show that a hostile opponent can target an otherwise nonaggressive Privateer Rob ship.

## Target residual remains distinct

`360690/T83 ship98`:

```text
Privateer race5
Meteor hull46
mission9 / Rob
PE=0
T-1 iscloaked=true
T same physical identity and iscloaked=true
true_to_true
no VCR
```

The population contains no stable prior-cloaked PE0 VCR participant. This is strong negative observational evidence, but it is not yet a clean combat-effective-cloak differential because most no-VCR rows may simply lack a hostile attack opportunity.

## Evidence boundary

Current official Planets.nu Host documentation keeps Cloak and Rob as distinct Host steps. The archive `iscloaked` field is therefore not promoted as an automatic current-Host cloak input. Raw T-1 `iscloaked=true` remains rejected as a blanket combat blocker because factual `511506/T94 ship332` has that bit under current mission2 and enters VCR728.

Evidence status:

```text
Privateer mission9 raw cloak persistence: CORPUS_OBSERVED + TESTED
PE0 prior-cloaked VCR counterexamples in this population: 0 CORPUS_OBSERVED
combat-effective targetability rule: NOT PROMOTED
```

## Next gate

Run a site-conditioned hostile attack-opportunity differential. Require:

```text
ordinary factual battle site
Privateer race5 target
mission9
cloak-capable hull
PE=0
target and opponent independently position-resolved at the site
opponent raw Kill!/PE requests combat against Privateer owner
canonical pair composition resolves plain STANDARD in conditional scope
```

Then compare factual VCR participation. The strongest positive shape for a blocker is:

```text
target prior iscloaked=true
attacker has a valid attack opportunity
attacker fights another ship at the same site
target is skipped
```

Do not modify `selection.py` or target order before this gate.
